"""Dependency-light structural tests for the SRD 5.2.1 corpus.

JSON-LD expansion tests use pyld when available (installed via the dev
dependency group); they fail loudly in CI if pyld is missing there.
"""

from __future__ import annotations

import json
import sys
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


def records_of(collection):
    return [
        load_json(path) for c, path in iter_object_files(ROOT) if c == collection
    ]


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


class TestCatalogs(unittest.TestCase):
    def test_collection_counts(self):
        counts = {c: len(records_of(c)) for c in COLLECTIONS}
        self.assertEqual(counts["sources"], 1)
        self.assertEqual(counts["spells"], 338)
        self.assertEqual(counts["feats"], 17)
        self.assertEqual(counts["magic-items"], 258)
        self.assertEqual(counts["monsters"], 332)
        self.assertGreater(counts["rules"], 1000)
        self.assertGreater(counts["tables"], 200)

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
        for monster in records_of("monsters"):
            for entry in monster.get("abilities", {}).values():
                self.assertGreaterEqual(entry["score"], 1)
                self.assertLessEqual(entry["score"], 30)


class TestGraph(unittest.TestCase):
    def test_manifest_references_resolve_and_are_unique(self):
        manifest = load_json(ROOT / "objects" / MANIFEST_NAME)
        ids = {r["@id"] for _, p in iter_object_files(ROOT) for r in [load_json(p)]}
        listed = [
            ref["@id"]
            for refs in manifest["collections"].values()
            for ref in refs
        ]
        self.assertEqual(len(listed), len(set(listed)))
        for ref in listed:
            self.assertIn(ref, ids)

    def test_jsonld_expansion(self):
        try:
            from pyld import jsonld
        except ImportError:
            self.skipTest("pyld not installed")
        context = load_json(ROOT / "systems/context.jsonld")
        spell = load_json(ROOT / "objects/spells/bless.jsonld")
        spell["@context"] = context["@context"]
        expanded = jsonld.expand(spell)[0]
        self.assertEqual(expanded["@id"], f"{BASE}objects/spells/bless")
        self.assertIn("https://schema.org/name", expanded)
        source = expanded["http://purl.org/dc/terms/source"][0]
        self.assertEqual(source["@id"], f"{BASE}objects/sources/srd-5-2-1")


class TestLlmsArtifacts(unittest.TestCase):
    def test_llms_full_inlines_record_text(self):
        text = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
        self.assertIn("You bless up to three creatures", text)
        self.assertIn(f"{BASE}objects/monsters/fire-giant", text)

    def test_search_index_resolves(self):
        index = load_json(ROOT / "objects/search-index.json")
        docs = index["documents"]
        self.assertIn("fireball", index["tokens"])
        for posting in index["tokens"]["fireball"][:5]:
            self.assertLess(posting, len(docs))


if __name__ == "__main__":
    unittest.main()
