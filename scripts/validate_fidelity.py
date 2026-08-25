"""Validate physical provenance and typed/source fidelity.

This gate is intentionally distinct from interval coverage: it checks that a
record owns the source it claims and that advertised structured values are
actually printed inside that span.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from extract_srd import parse_magic_item_header, parse_weight_pounds
from srdlib import (
    ATTRIBUTION_STATEMENT,
    MANIFEST_NAME,
    SOURCE_FILE,
    SOURCE_ID,
    iter_object_files,
    load_json,
    sha256_of,
)


def source_span(lines, locator):
    return "\n".join(lines[locator["lineStart"] - 1 : locator["lineEnd"]])


def observed(needle, haystack):
    return re.sub(r"\s+", " ", str(needle)).strip() in re.sub(r"\s+", " ", haystack)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    errors = []
    records = []
    by_id = {}

    for collection, path in iter_object_files(root):
        record = load_json(path)
        records.append((collection, path, record))
        by_id[record["@id"]] = record
        if collection == "sources":
            if record.get("contentDigest") != sha256_of(root / SOURCE_FILE):
                errors.append(f"{path}: content digest does not match the source bytes")
            if record.get("attributionStatement") != ATTRIBUTION_STATEMENT:
                errors.append(f"{path}: attribution statement is not exact")
            continue
        locator = record["sourceLocator"]
        first = lines[locator["lineStart"] - 1].strip()
        if collection == "tables" or (collection == "equipment" and "fromTable" in record):
            if not first.startswith("|"):
                errors.append(f"{path}: locator does not start at a source table row")
        elif first != f"# {locator['heading']}":
            errors.append(
                f"{path}: locator starts with {first!r}, expected heading {locator['heading']!r}"
            )

        for nested_record in record.get("features", []) + record.get("statSections", []):
            nested = nested_record["sourceLocator"]
            if not (
                locator["lineStart"] <= nested["lineStart"] <= nested["lineEnd"] <= locator["lineEnd"]
            ):
                errors.append(f"{path}: nested section {nested_record['name']!r} is outside its owner span")
            if lines[nested["lineStart"] - 1].strip() != f"# {nested['heading']}":
                errors.append(f"{path}: nested section {nested_record['name']!r} misses its source heading")

        if collection == "tables":
            source_table = "\n".join(
                line.strip()
                for line in lines[locator["lineStart"] - 1 : locator["lineEnd"]]
                if line.strip().startswith("|")
            )
            if source_table != record["rawText"]:
                errors.append(f"{path}: rawText does not match its physical source span")
            if not record["rows"]:
                errors.append(f"{path}: table has no data rows")
            for row in record["rows"]:
                if [cell["value"] for cell in row["cells"]] == record["columns"]:
                    errors.append(f"{path}: repeated header was promoted to a data row")

        span = source_span(lines, locator)
        if collection == "spells":
            descriptor = (
                f"{record['school']} Cantrip ("
                if record["level"] == 0
                else f"Level {record['level']} {record['school']} ("
            )
            if descriptor not in span:
                errors.append(f"{path}: level/school descriptor is not printed in its source span")

        if collection == "equipment":
            for field in ("name", "damage", "armorClass", "weight", "mastery"):
                value = record.get(field)
                observed_value = value.removeprefix("Spellcasting Service: ") if field == "name" else value
                if value and observed_value not in span:
                    errors.append(f"{path}: {field} is not printed in its source table span")
            if "cost" in record and record["cost"]["text"] not in span:
                errors.append(f"{path}: cost is not printed in its source table span")
            if "weightPounds" in record and parse_weight_pounds(record.get("weight", "")) != record["weightPounds"]:
                errors.append(f"{path}: weightPounds is not derived from the printed weight")
            for field in ("ability", "utilize", "craft"):
                if record.get(field) and not observed(record[field], span):
                    errors.append(f"{path}: {field} is not printed in its source span")

        if collection == "spells":
            for label, field in (
                ("Casting Time", "castingTime"),
                ("Range", "range"),
                ("Components", "components"),
                ("Duration", "duration"),
            ):
                if f"{label}: {record[field]}" not in span:
                    errors.append(f"{path}: {field} is not printed in its source span")

        if collection == "magic-items":
            header = next(
                (line.strip() for line in lines[locator["lineStart"] : locator["lineEnd"]] if line.strip()),
                "",
            )
            parsed = parse_magic_item_header(header)
            if not parsed:
                errors.append(f"{path}: source magic-item header is not parseable")
            else:
                expected_attunement = bool(parsed["attunementNote"])
                if record["requiresAttunement"] != expected_attunement:
                    errors.append(f"{path}: attunement flag differs from the complete header")
                expected_rarities = parsed["rarities"]
                actual = record.get("rarities") or [{"rarity": record["rarity"]}]
                if actual != expected_rarities:
                    errors.append(f"{path}: rarity variants differ from the complete header")
            if record.get("attunementRestriction") and not observed(record["attunementRestriction"], span):
                errors.append(f"{path}: attunementRestriction is not source-observed")
            if record.get("isCursed") and not re.search(r"\bcurse(?:d|s)?\b", span, re.I):
                errors.append(f"{path}: isCursed is not supported by its source span")
            if record.get("isSentient") and "sentient" not in span.lower():
                errors.append(f"{path}: isSentient is not supported by its source span")
            if record.get("charges") and "charge" not in span.lower():
                errors.append(f"{path}: charge structure is not supported by its source span")

        if collection == "monsters":
            for field in (
                "sizeTypeAlignment", "armorClass", "initiative", "hitPoints", "speed",
                "skills", "resistances", "vulnerabilities", "immunities", "senses",
                "languages", "gear", "challenge",
            ):
                if record.get(field) and not observed(record[field], span):
                    errors.append(f"{path}: {field} is not printed in its source span")
            if not record.get("size") or record["size"] not in record.get("sizeTypeAlignment", ""):
                errors.append(f"{path}: typed size is not derived from sizeTypeAlignment")
            if not record.get("creatureType") or record["creatureType"] not in record.get("sizeTypeAlignment", ""):
                errors.append(f"{path}: typed creatureType is not derived from sizeTypeAlignment")
            if not record.get("armorClass", "").startswith(str(record.get("armorClassValue", ""))):
                errors.append(f"{path}: armorClassValue differs from printed armorClass")
            if not record.get("hitPoints", "").startswith(str(record.get("hitPointsValue", ""))):
                errors.append(f"{path}: hitPointsValue differs from printed hitPoints")
            if record.get("challengeRating") and not record.get("challenge", "").startswith(record["challengeRating"]):
                errors.append(f"{path}: challengeRating differs from printed challenge")
            if record.get("experiencePoints") is not None:
                xp = f"XP {record['experiencePoints']:,}"
                if xp not in record.get("challenge", ""):
                    errors.append(f"{path}: experiencePoints differs from printed challenge")
            if record.get("proficiencyBonus") is not None:
                pb = f"PB {record['proficiencyBonus']:+d}"
                if pb not in record.get("challenge", ""):
                    errors.append(f"{path}: proficiencyBonus differs from printed challenge")
            if record.get("passivePerception") is not None and str(record["passivePerception"]) not in record.get("senses", ""):
                errors.append(f"{path}: passivePerception differs from printed senses")
            for ability, entry in record.get("abilities", {}).items():
                score_mod = f"{entry['score']} ({entry['modifier']:+d})" if "modifier" in entry else str(entry["score"])
                if score_mod not in span:
                    errors.append(f"{path}: {ability} score/modifier is not an observed source token")
                if "savingThrow" in entry:
                    save = entry["savingThrow"]
                    if not re.search(rf"Save:\s*\+?{save}\b", span):
                        errors.append(f"{path}: {ability} saving throw is not an observed source token")
            candidates = sum(
                section["rulesText"].count("Attack Roll:")
                for section in record.get("statSections", [])
            )
            represented = len(record.get("attacks", [])) + len(record.get("unparsedAttacks", []))
            if candidates != represented:
                errors.append(f"{path}: {candidates} attack paragraphs but {represented} parse dispositions")
            for attack in record.get("attacks", []):
                if not any(attack["sourceText"] in section["rulesText"] for section in record.get("statSections", [])):
                    # Some source conversion split one sentence with blank
                    # lines; whitespace-normalized containment is equivalent.
                    needle = re.sub(r"\s+", " ", attack["sourceText"])
                    if not any(
                        needle in re.sub(r"\s+", " ", section["rulesText"])
                        for section in record.get("statSections", [])
                    ):
                        errors.append(f"{path}: parsed attack sourceText is not source-observed")

        if collection == "feats":
            for field in ("category", "prerequisite"):
                if record.get(field) and not observed(record[field], span):
                    errors.append(f"{path}: {field} is not source-observed")
            if "repeatable" in record and record["repeatable"] != ("Repeatable" in span):
                errors.append(f"{path}: repeatable flag differs from source")

        if collection == "species":
            for field in ("creatureType", "size", "speed"):
                if record.get(field) and not observed(record[field], span):
                    errors.append(f"{path}: {field} is not source-observed")
            for table in record.get("relatedTables", []):
                if table["@id"] not in by_id:
                    errors.append(f"{path}: related lineage table does not resolve")

        if collection == "backgrounds":
            for field in (
                "abilityScores", "feat", "skillProficiencies", "toolProficiency",
                "startingEquipment",
            ):
                if record.get(field) and not observed(record[field], span):
                    errors.append(f"{path}: {field} is not source-observed")
            for option in record.get("abilityScoreOptions", []):
                if option not in record.get("abilityScores", ""):
                    errors.append(f"{path}: abilityScoreOptions value is not printed")

    manifest = load_json(root / "objects" / MANIFEST_NAME)
    source_members = next(c["members"] for c in manifest["collections"] if c["slug"] == "sources")
    source_ids = {ref["@id"] for ref in source_members}
    contributing = {record["source"]["@id"] for collection, _, record in records if collection != "sources"}
    if contributing != source_ids or contributing != {SOURCE_ID}:
        errors.append(
            f"manifest/source rights boundary mismatch: contributing={sorted(contributing)}, sources={sorted(source_ids)}"
        )

    if errors:
        print("\n".join(errors[:50]))
        print(f"FAIL: {len(errors)} source-fidelity errors")
        sys.exit(1)
    print(f"fidelity: {len(records)} records have source-aligned spans and typed values")


if __name__ == "__main__":
    main()
