"""One-time deliberate source repair for SRD_CC_v5.2.1.md (Phase 1 cleanup).

Repairs documented PDF-to-markdown conversion damage. Every repair class is
registered in objects/sources/extraction-overrides.json. Ability tables are
regenerated from open5e's CC-BY-4.0 srd-2024 dataset
(scripts/data/srd-2024-creatures.json) and cross-validated against every
intact cell of the original table; any disagreement aborts the run.

Idempotent: re-running on a repaired file makes no changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from srdlib import SOURCE_FILE

ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
SHORT = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
CELL_RE = re.compile(r"<td(?:\s+colspan=\"(\d+)\")?>(.*?)</td>", re.S)
HEADING_RE = re.compile(r"^# (.+?)\s*$")


def signed(value: int) -> str:
    return f"{value:+d}"


def canonical_table(creature: dict) -> str:
    header = (
        '<tr><td colspan="2"></td><td>MOD</td><td>SAVE</td>'
        '<td colspan="2"></td><td>MOD</td><td>SAVE</td>'
        '<td colspan="2"></td><td>MOD</td><td>SAVE</td></tr>'
    )
    rows = []
    for triple in (ABILITIES[:3], ABILITIES[3:]):
        cells = []
        for ability in triple:
            cells.append(
                f"<td>{SHORT[ABILITIES.index(ability)]}</td>"
                f"<td>{creature['scores'][ability]}</td>"
                f"<td>{signed(creature['mods'][ability])}</td>"
                f"<td>{signed(creature['saves'][ability])}</td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table>" + header + "".join(rows) + "</table>"


def parse_existing_scores(table_html: str) -> dict:
    """Best-effort parse of intact score cells for cross-validation."""
    cells = []
    for _, value in CELL_RE.findall(table_html):
        token = re.sub(r"\s+", " ", value).strip()
        token = re.sub(r"\$\\mathbf\{([A-Z])_\{([A-Z]+)\}\}\$", r"\1\2", token)
        token = re.sub(r"\$\\mathbf\{([A-Z]{3})\}\$", r"\1", token)
        cells.append(token)
    scores = {}
    index = 0
    while index < len(cells):
        parts = cells[index].replace("Con", "CON").split()
        joined = re.match(r"^(STR|DEX|CON|INT|WIS|CHA)\s*(\d+|I{1,2})$", cells[index].replace("Con", "CON"), re.I)
        label = None
        raw = None
        if joined:
            label, raw = joined.group(1).upper(), joined.group(2)
        elif parts and parts[0].upper() in SHORT and len(parts) == 1:
            label = parts[0].upper()
            if index + 1 < len(cells):
                raw = cells[index + 1]
        elif parts and parts[0].upper() in SHORT and len(parts) == 2:
            label, raw = parts[0].upper(), parts[1]
        if label and raw is not None:
            if raw == "I":
                scores[label] = 1
            elif raw == "II":
                scores[label] = 11
            elif raw.isdigit():
                scores[label] = int(raw)
        index += 1
    return scores


def parse_columns(table_html: str):
    """Parse a stat table into {LABEL: {score, mod, save}} where available.

    Tolerates joined label-score cells ('DEX 16'), the roman-numeral and
    LaTeX glossary artifacts, and truncated rows. Returns None if no
    ability labels are found.
    """
    tokens = []
    for _, value in CELL_RE.findall(table_html):
        token = re.sub(r"\s+", " ", value).strip()
        token = re.sub(r"\$\\mathbf\{([A-Z])_\{([A-Z]+)\}\}\$", r"\1\2", token)
        token = re.sub(r"\$\\mathbf\{([A-Z]{3})\}\$", r"\1", token)
        token = re.sub(
            r"^([+-]?)(II|I)$",
            lambda m: m.group(1) + ("11" if m.group(2) == "II" else "1"),
            token,
        )
        glued = re.match(r"^(STR|DEX|CON|INT|WIS|CHA)\s*(\d+|I{1,2})$", token, re.I)
        if glued:
            raw = glued.group(2)
            score = {"I": "1", "II": "11"}.get(raw, raw)
            tokens.extend([glued.group(1).upper(), score])
        else:
            tokens.append(token)
    columns = {}
    index = 0
    while index < len(tokens):
        if tokens[index].upper() in SHORT:
            label = tokens[index].upper()
            column = {}
            cursor = index + 1
            if cursor < len(tokens) and tokens[cursor].isdigit():
                column["score"] = int(tokens[cursor])
                cursor += 1
                for field in ("mod", "save"):
                    if cursor < len(tokens) and re.fullmatch(r"[+-]?\d+", tokens[cursor]):
                        column[field] = int(tokens[cursor])
                        cursor += 1
                    else:
                        break
            columns[label] = column
            index = cursor
        else:
            index += 1
    return columns or None


def repair(root: Path) -> None:
    source_path = root / SOURCE_FILE
    text = source_path.read_text(encoding="utf-8")
    creatures = json.loads(
        (root / "scripts/data/srd-2024-creatures.json").read_text(encoding="utf-8")
    )
    report = {}

    # -- 1. Glossary substitutions (scripts/data/sanitization-glossary.json) -
    glossary = json.loads(
        (root / "scripts/data/sanitization-glossary.json").read_text(encoding="utf-8")
    )
    for entry in glossary["substitutions"]:
        flags = re.M if "m" in entry["flags"] else 0
        text, n = re.subn(entry["pattern"], entry["replacement"], text, flags=flags)
        report[entry["id"]] = n

    # -- 2. Regenerate damaged monster ability tables from authoritative data
    lines = text.split("\n")
    last_heading = None
    regenerated = 0
    untouched_ok = 0
    problems = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            last_heading = m.group(1)
            continue
        if not (line.startswith("<table>") and ">MOD<" in line and ">SAVE<" in line):
            continue
        name = last_heading
        columns = parse_columns(line)
        clean = columns is not None and all(
            all(k in col for k in ("score", "mod", "save")) for col in columns.values()
        ) and len(columns) == 6
        if clean:
            untouched_ok += 1
            continue
        creature = creatures.get(name)
        if creature is not None and all(
            1 <= creature["scores"][a] <= 30 for a in ABILITIES
        ):
            existing = parse_existing_scores(line)
            mismatch = False
            for label, score in existing.items():
                authoritative = creature["scores"][ABILITIES[SHORT.index(label)]]
                if score != authoritative:
                    problems.append(
                        f"{name}: source {label}={score} disagrees with srd-2024 {authoritative}"
                    )
                    mismatch = True
            if mismatch:
                continue
            lines[i] = canonical_table(creature)
            regenerated += 1
            continue
        # No authoritative record (spell/item-summoned stat blocks): fill the
        # truncated modifier/save cells from the score. In every intact
        # column of these tables save equals the ability modifier, and the
        # modifier is floor((score - 10) / 2) by rule.
        if columns is None or len(columns) != 6 or any("score" not in c for c in columns.values()):
            problems.append(f"{name}: damaged table but no authoritative data")
            continue
        derived = {"scores": {}, "mods": {}, "saves": {}}
        for label, col in columns.items():
            ability = ABILITIES[SHORT.index(label)]
            mod = col.get("mod", (col["score"] - 10) // 2)
            derived["scores"][ability] = col["score"]
            derived["mods"][ability] = mod
            derived["saves"][ability] = col.get("save", mod)
        lines[i] = canonical_table(derived)
        report["ability-tables-derived"] = report.get("ability-tables-derived", 0) + 1
    if problems:
        print("\n".join(problems))
        print("FAIL: cross-validation mismatches; nothing written")
        sys.exit(1)
    report["ability-tables-regenerated"] = regenerated
    report["ability-tables-untouched"] = untouched_ok
    text = "\n".join(lines)

    source_path.write_text(text, encoding="utf-8")
    for key, value in report.items():
        print(f"{key}: {value}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    repair(Path(args.root).resolve())


if __name__ == "__main__":
    main()
