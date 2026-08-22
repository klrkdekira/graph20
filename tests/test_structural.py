"""Dependency-light structural tests for the SRD 5.2.1 corpus.

JSON-LD expansion tests use pyld when available (installed via the dev
dependency group); they fail loudly in CI if pyld is missing there.
"""

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from srdlib import (  # noqa: E402
    BASE,
    COLLECTIONS,
    MANIFEST_NAME,
    SOURCE_FILE,
    iter_object_files,
    load_json,
    sha256_of,
)
from extract_srd import Block, Emitter, parse_ability_table, parse_markdown_table, run_extraction  # noqa: E402
from build_bundle import build as build_bundle  # noqa: E402
from build_llms_full import build as build_llms_full  # noqa: E402
from build_manifest import build as build_manifest  # noqa: E402


def records_of(collection):
    return [
        load_json(path) for c, path in iter_object_files(ROOT) if c == collection
    ]


def nested_text(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("rulesText", "description") and isinstance(child, str):
                yield child
            yield from nested_text(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_text(child)


class TestProvenance(unittest.TestCase):
    def test_source_digest_matches_source_file(self):
        source = load_json(ROOT / "objects/sources/srd-5-2-1.jsonld")
        self.assertEqual(source["contentDigest"], sha256_of(ROOT / SOURCE_FILE))
        manifest = load_json(ROOT / "objects" / MANIFEST_NAME)
        self.assertEqual(
            manifest["metadata"]["sourceDigest"], source["contentDigest"]
        )

    def test_attribution_statement_present(self):
        source = load_json(ROOT / "objects/sources/srd-5-2-1.jsonld")
        self.assertIn("SRD 5.2.1", source["attributionStatement"])
        self.assertIn(
            "creativecommons.org/licenses/by/4.0", source["attributionStatement"]
        )
        self.assertEqual(source["license"], "CC-BY-4.0")
        self.assertEqual(set(source["licenseUrl"]), {"@id"})
        self.assertEqual(set(source["canonicalUrl"]), {"@id"})

    def test_no_secondary_dataset_contributes_values(self):
        self.assertFalse((ROOT / "scripts/data/srd-2024-creatures.json").exists())
        manifest = load_json(ROOT / "objects" / MANIFEST_NAME)
        source_collection = next(c for c in manifest["collections"] if c["slug"] == "sources")
        self.assertEqual(source_collection["members"], [{"@id": f"{BASE}objects/sources/srd-5-2-1"}])

    def test_reviewed_signal_set_is_current(self):
        ledger = load_json(ROOT / "objects/sources/source-review-ledger.json")
        policies = load_json(ROOT / "reviews/semantic-review-policies.json")
        digest = "sha256-" + hashlib.sha256(
            "\n".join(sorted(signal["key"] for signal in ledger["signals"])).encode()
        ).hexdigest()
        self.assertEqual(digest, ledger["signalSetDigest"])
        self.assertEqual(digest, policies["reviewedSignalSetDigest"])
        self.assertEqual(ledger["statusCounts"]["pending"], 0)


class TestCatalogs(unittest.TestCase):
    def test_collection_counts(self):
        counts = {c: len(records_of(c)) for c in COLLECTIONS}
        self.assertEqual(counts["sources"], 1)
        self.assertEqual(counts["spells"], 338)
        self.assertEqual(counts["feats"], 17)
        self.assertEqual(counts["magic-items"], 258)
        self.assertEqual(counts["monsters"], 332)
        self.assertEqual(counts["classes"], 12)
        self.assertEqual(counts["subclasses"], 12)
        self.assertEqual(counts["species"], 9)
        self.assertEqual(counts["backgrounds"], 4)
        self.assertEqual(counts["conditions"], 15)
        self.assertGreater(counts["equipment"], 120)
        self.assertGreater(counts["rules"], 700)
        self.assertGreater(counts["tables"], 200)

    def test_class_fixture_barbarian(self):
        cls = load_json(ROOT / "objects/classes/barbarian.jsonld")
        core = {trait["name"]: trait["value"] for trait in cls["coreTraits"]}
        self.assertEqual(core["Primary Ability"], "Strength")
        self.assertIn("D12", core["Hit Point Die"])
        rage = [f for f in cls["features"] if f["name"] == "Rage"][0]
        self.assertEqual(rage["level"], 1)
        sub = load_json(ROOT / "objects/subclasses/path-of-the-berserker.jsonld")
        self.assertEqual(sub["parentClass"]["@id"], cls["@id"])
        self.assertEqual(
            [f["name"] for f in sub["features"]][:2], ["Frenzy", "Mindless Rage"]
        )

    def test_equipment_fixture_longsword(self):
        weapon = load_json(ROOT / "objects/equipment/longsword.jsonld")
        self.assertEqual(weapon["equipmentType"], "weapon")
        self.assertEqual(weapon["damageType"], "Slashing")
        self.assertEqual(weapon["damageRoll"]["sides"], 8)
        self.assertEqual(weapon["cost"], {"text": "15 GP", "currency": "GP", "amount": 15})

    def test_equipment_names_decode_conversion_markup(self):
        for equipment in records_of("equipment"):
            self.assertNotIn("&#x27;", equipment["name"])
            self.assertNotIn("x27", equipment["slug"])

    def test_monster_ability_entries_are_source_observed(self):
        source_lines = (ROOT / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
        for monster in records_of("monsters"):
            abilities = monster.get("abilities", {})
            self.assertEqual(len(abilities), 6, monster["name"])
            locator = monster["sourceLocator"]
            source = "\n".join(source_lines[locator["lineStart"] - 1 : locator["lineEnd"]])
            for entry in abilities.values():
                token = str(entry["score"])
                if "modifier" in entry:
                    token += f" ({entry['modifier']:+d})"
                self.assertIn(token, source, monster["name"])

    def test_enrichment_links_resolve_types(self):
        spell = load_json(ROOT / "objects/spells/fireball.jsonld")
        self.assertEqual(spell["savingThrowAbility"], "Dexterity")
        self.assertTrue(spell["scalesWithSlotLevel"])
        self.assertEqual(len(spell["classes"]), 2)
        giant = load_json(ROOT / "objects/monsters/fire-giant.jsonld")
        attack = giant["attacks"][0]
        self.assertEqual(attack["attackBonus"], 11)
        self.assertEqual(attack["damageComponents"][0]["damageRoll"]["expression"], "4d6+7")

    def test_spell_fixture_bless(self):
        spell = load_json(ROOT / "objects/spells/bless.jsonld")
        self.assertEqual(spell["level"], 1)
        self.assertEqual(spell["school"], "Enchantment")
        self.assertEqual(spell["classAvailability"], ["Cleric", "Paladin"])
        self.assertEqual(spell["castingTime"], "Action")
        self.assertEqual(spell["range"], "30 feet")
        self.assertIn("You bless up to three creatures", spell["rulesText"])

    def test_monster_fixture_fire_giant(self):
        monster = load_json(ROOT / "objects/monsters/fire-giant.jsonld")
        self.assertEqual(monster["armorClassValue"], 18)
        self.assertEqual(monster["hitPointsValue"], 162)
        self.assertEqual(monster["hitPointsRoll"]["expression"], "13d12+78")
        self.assertEqual(monster["challengeRating"], "9")
        self.assertEqual(monster["experiencePoints"], 5000)
        self.assertEqual(monster["abilities"]["str"]["score"], 25)
        self.assertEqual(monster["abilities"]["str"]["savingThrow"], 7)

    def test_magic_item_fixture(self):
        item = load_json(ROOT / "objects/magic-items/animated-shield.jsonld")
        self.assertEqual(item["itemCategory"], "Armor")
        self.assertEqual(item["rarity"], "Very Rare")
        self.assertTrue(item["requiresAttunement"])

    def test_magic_item_variants_and_complete_attunement(self):
        wand = load_json(ROOT / "objects/magic-items/wand-of-the-war-mage-1-2-or-3.jsonld")
        self.assertEqual(
            [entry["rarity"] for entry in wand["rarities"]],
            ["Uncommon", "Rare", "Very Rare"],
        )
        self.assertTrue(wand["requiresAttunement"])
        self.assertIn("by a Spellcaster", wand["attunementNote"])

    def test_typed_fields_mirror_source_strings(self):
        for monster in records_of("monsters"):
            if "hitPointsRoll" in monster:
                self.assertIn(
                    monster["hitPointsRoll"]["expression"].split("d")[0],
                    monster["hitPoints"].replace(" ", ""),
                )
            if "challengeRating" in monster:
                self.assertTrue(
                    monster["challenge"].startswith(monster["challengeRating"])
                )

    def test_no_invented_ability_scores(self):
        fixture = """| STR | DEX | CON | INT | WIS | CHA |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 15 (+2) |  | 12 (+1) | 8 (-1) | 10 (+0) | 11 (+0) |
| Save: +2 |  | Save: +1 | Save: -1 | Save: +0 | Save: +0 |"""
        parsed = parse_ability_table(fixture)
        self.assertNotIn("dex", parsed)
        self.assertEqual(parsed["str"], {"score": 15, "modifier": 2, "savingThrow": 2})

    def test_truncated_ability_remains_omitted_through_clean_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = (ROOT / SOURCE_FILE).read_text(encoding="utf-8")
            observed = "| 18 (+4) | 10 (+0) | 18 (+4) | 6 (-2) | 11 (+0) | 12 (+1) |"
            truncated = "| 18 (+4) |  | 18 (+4) | 6 (-2) | 11 (+0) | 12 (+1) |"
            observed_save = "| Save: +4 | Save: +3 | Save: +4 | Save: 2 | Save: +3 | Save: +1 |"
            truncated_save = "| Save: +4 |  | Save: +4 | Save: 2 | Save: +3 | Save: +1 |"
            self.assertEqual(source.count(observed), 1)
            self.assertEqual(source.count(observed_save), 1)
            (root / SOURCE_FILE).write_text(
                source.replace(observed, truncated).replace(observed_save, truncated_save),
                encoding="utf-8",
            )
            run_extraction(root)
            build_manifest(root)
            build_bundle(root)
            build_llms_full(root)
            monster = load_json(root / "objects/monsters/young-white-dragon.jsonld")
            self.assertNotIn("dex", monster["abilities"])
            bundle = load_json(root / "objects/srd52-system-data.bundle.jsonld")
            bundled = next(node for node in bundle["@graph"] if node["@id"] == monster["@id"])
            self.assertNotIn("dex", bundled["abilities"])
            llms = (root / "llms-full.txt").read_text(encoding="utf-8")
            record_text = llms.split("### Young White Dragon", 1)[1].split("\n### ", 1)[0]
            self.assertNotIn("[abilities.dex", record_text)
            first = (root / "llms-full.txt").read_bytes()
            run_extraction(root)
            build_manifest(root)
            build_bundle(root)
            build_llms_full(root)
            self.assertEqual(first, (root / "llms-full.txt").read_bytes())

    def test_folded_monster_stat_heading_keeps_physical_span(self):
        emitter = Emitter(ROOT)
        monster = Block(
            "Fixture Beast",
            100,
            110,
            ["Medium Beast, Unaligned", "", "AC 12", "HP 5", "Speed 30 ft."],
            "Monsters A-Z",
        )
        folded_stat = Block("Resistances Cold", 111, 111, [], "Monsters A-Z")
        actions = Block("Actions", 112, 114, ["Bite. Melee Attack Roll: +2, reach 5 ft. Hit: 1 Piercing damage."], "Monsters A-Z")
        record = emitter.emit_monster(monster, [folded_stat, actions], None)
        self.assertEqual(record["resistances"], "Cold")
        self.assertEqual(record["sourceLocator"]["lineEnd"], 114)
        self.assertEqual(record["statSections"][0]["sourceLocator"]["lineStart"], 112)

    def test_attack_paragraphs_have_complete_dispositions(self):
        candidate_count = parsed_count = unparsed_count = 0
        for monster in records_of("monsters"):
            candidate_count += sum(
                section["rulesText"].count("Attack Roll:")
                for section in monster.get("statSections", [])
            )
            parsed_count += len(monster.get("attacks", []))
            unparsed_count += len(monster.get("unparsedAttacks", []))
        self.assertEqual(candidate_count, parsed_count + unparsed_count)
        self.assertEqual(parsed_count, 423)
        self.assertEqual(unparsed_count, 1)

    def test_table_continuation_and_headerless_regressions(self):
        wand = next(t for t in records_of("tables") if t["name"] == "Wand of Wonder Effects")
        self.assertEqual(len(wand["rows"]), 18)
        self.assertNotEqual([c["value"] for c in wand["rows"][0]["cells"]], wand["columns"])
        efreeti = next(
            t for t in records_of("tables")
            if t["sourceLocator"]["heading"] == "Efreeti Bottle"
        )
        self.assertEqual(efreeti["rows"][0]["cells"][0]["value"], "1")
        columns, rows = parse_markdown_table(
            ["| d100 | Effect |", "| :--- | :--- |", "| d100 | Effect |", "| 01 | Result |"]
        )
        self.assertEqual(columns, ["d100", "Effect"])
        self.assertEqual(len(rows), 1)
        columns, rows = parse_markdown_table(["| 1 | First effect |", "| 2 | Second effect |"])
        self.assertEqual(columns, ["column1", "column2"])
        self.assertEqual([row["cells"][0]["value"] for row in rows], ["1", "2"])

    def test_locator_regressions(self):
        lines = (ROOT / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
        subclass = load_json(ROOT / "objects/subclasses/path-of-the-berserker.jsonld")
        self.assertGreaterEqual(
            subclass["sourceLocator"]["lineEnd"],
            subclass["features"][-1]["sourceLocator"]["lineEnd"],
        )
        for table in records_of("tables"):
            self.assertTrue(lines[table["sourceLocator"]["lineStart"] - 1].strip().startswith("|"))


class TestGraph(unittest.TestCase):
    def test_manifest_references_resolve_and_are_unique(self):
        manifest = load_json(ROOT / "objects" / MANIFEST_NAME)
        ids = {r["@id"] for _, p in iter_object_files(ROOT) for r in [load_json(p)]}
        listed = [ref["@id"] for collection in manifest["collections"] for ref in collection["members"]]
        self.assertEqual(len(listed), len(set(listed)))
        for ref in listed:
            self.assertIn(ref, ids)

    def test_jsonld_expansion_every_entity_type_and_aggregates(self):
        try:
            from pyld import jsonld
        except ImportError:
            self.skipTest("pyld not installed")
        context = load_json(ROOT / "systems/context.jsonld")
        for collection in COLLECTIONS:
            record = records_of(collection)[0]
            record["@context"] = context["@context"]
            expanded = jsonld.expand(record)[0]
            self.assertEqual(expanded["@id"], record["@id"])
            self.assertIn("https://schema.org/name", expanded)
        cls = load_json(ROOT / "objects/classes/barbarian.jsonld")
        cls["@context"] = context["@context"]
        expanded_class = jsonld.expand(cls)[0]
        traits = expanded_class[f"{BASE}vocab/#coreTraits"]
        expanded_text = json.dumps(traits)
        self.assertIn("Primary Ability", expanded_text)
        self.assertIn("Strength", expanded_text)
        for name in (MANIFEST_NAME, "srd52-system-data.bundle.jsonld"):
            document = load_json(ROOT / "objects" / name)
            document["@context"] = context["@context"]
            self.assertTrue(jsonld.expand(document))

    def test_all_iri_coerced_values_are_node_references(self):
        context = load_json(ROOT / "systems/context.jsonld")["@context"]
        iri_terms = {
            key for key, value in context.items()
            if isinstance(value, dict) and value.get("@type") == "@id"
        }
        def check(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in iri_terms:
                        values = child if isinstance(child, list) else [child]
                        self.assertTrue(all(isinstance(item, dict) and set(item) == {"@id"} for item in values), key)
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        for _, path in iter_object_files(ROOT):
            check(load_json(path))
        check(load_json(ROOT / "objects" / MANIFEST_NAME))


class TestLlmsArtifacts(unittest.TestCase):
    def test_llms_full_inlines_record_text(self):
        text = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
        for _, path in iter_object_files(ROOT):
            record = load_json(path)
            for value in nested_text(record):
                self.assertIn(value, text, f"missing {path}")

    def test_search_index_resolves(self):
        index = load_json(ROOT / "objects/search-index.json")
        docs = index["documents"]
        self.assertIn("fireball", index["tokens"])
        for posting in index["tokens"]["fireball"][:5]:
            self.assertLess(posting["document"], len(docs))
            self.assertTrue(posting["excerpt"])

    def test_recursive_search_fixtures(self):
        index = load_json(ROOT / "objects/search-index.json")
        docs = index["documents"]
        names = lambda token: {
            docs[posting["document"]]["name"] for posting in index["tokens"][token]
        }
        postings = lambda token: {posting["document"] for posting in index["tokens"][token]}
        self.assertIn("Barbarian", names("rage"))
        self.assertIn(
            "Barbarian",
            {docs[i]["name"] for i in postings("rage") & postings("damage")},
        )
        self.assertIn(
            "Path of the Berserker",
            {docs[i]["name"] for i in postings("mindless") & postings("rage")},
        )
        self.assertIn(
            "Longsword",
            {docs[i]["name"] for i in postings("longsword") & postings("slashing")},
        )

    def test_vocabulary_covers_project_graph_terms(self):
        vocab = load_json(ROOT / "vocab/terms.json")
        defined = {entry["iri"] for entry in vocab["classes"] + vocab["properties"]}
        self.assertIn(f"{BASE}vocab/#features", defined)
        self.assertIn(f"{BASE}vocab/#damageRoll", defined)
        self.assertIn(f"{BASE}vocab/#rows", defined)
        page = (ROOT / "vocab/index.html").read_text(encoding="utf-8")
        for entry in vocab["classes"] + vocab["properties"]:
            self.assertIn(f'id="{entry["anchor"]}"', page)


if __name__ == "__main__":
    unittest.main()
