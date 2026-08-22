"""Shared constants and helpers for the SRD 5.2.1 corpus pipeline.

Everything under objects/ is generated from SRD_CC_v5.2.1.md by scripts in
this directory. Determinism rules: no timestamps, no randomness, sorted
listings, fixed JSON formatting.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterator

BASE = "https://cheeleong.dev/graph20/"
CONTEXT_IRI = BASE + "systems/context.jsonld"
SOURCE_ID = BASE + "objects/sources/srd-5-2-1"
SOURCE_FILE = "SRD_CC_v5.2.1.md"
SYSTEM_SLUG = "srd52"
MANIFEST_NAME = f"{SYSTEM_SLUG}-system-data.jsonld"
BUNDLE_NAME = f"{SYSTEM_SLUG}-system-data.bundle.jsonld"

ATTRIBUTION_STATEMENT = (
    "This work includes material from the System Reference Document 5.2.1 "
    "(“SRD 5.2.1”) by Wizards of the Coast LLC, available at "
    "https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the "
    "Creative Commons Attribution 4.0 International License, available at "
    "https://creativecommons.org/licenses/by/4.0/legalcode."
)

COLLECTIONS = [
    "sources",
    "rules",
    "tables",
    "classes",
    "subclasses",
    "species",
    "backgrounds",
    "feats",
    "equipment",
    "spells",
    "conditions",
    "magic-items",
    "monsters",
]

COLLECTION_TYPES = {
    "sources": "Source",
    "rules": "Rule",
    "tables": "Table",
    "classes": "CharacterClass",
    "subclasses": "Subclass",
    "species": "Species",
    "backgrounds": "Background",
    "feats": "Feat",
    "equipment": "Equipment",
    "spells": "Spell",
    "conditions": "Condition",
    "magic-items": "MagicItem",
    "monsters": "Monster",
}

SCHEMA_FOR_COLLECTION = {
    "sources": "source.schema.json",
    "rules": "rule.schema.json",
    "tables": "table.schema.json",
    "classes": "class.schema.json",
    "subclasses": "subclass.schema.json",
    "species": "species.schema.json",
    "backgrounds": "background.schema.json",
    "feats": "feat.schema.json",
    "equipment": "equipment.schema.json",
    "spells": "spell.schema.json",
    "conditions": "condition.schema.json",
    "magic-items": "magic-item.schema.json",
    "monsters": "monster.schema.json",
}

CLASS_NAMES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

# Ordered chapter titles as printed in the SRD body (not the Contents list).
# Chapters are located sequentially: first exact `# <title>` heading after the
# previous chapter's start line. Legal Information and the Contents block are
# excluded legal/navigation preamble (see SPECIFICATION.md).
CHAPTERS = [
    "Playing the Game",
    "Character Creation",
    "Classes",
    "Character Origins",
    "Feats",
    "Equipment",
    "Spells",
    "Rules Glossary",
    "Gameplay Toolbox",
    "Magic Items",
    "Monsters",
    "Monsters A-Z",
    "Animals",
]


def slugify(text: str) -> str:
    text = text.lower().replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unnamed"


def sha256_of(path: Path) -> str:
    return "sha256-" + hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_object_files(root: Path):
    objects = root / "objects"
    for collection in COLLECTIONS:
        directory = objects / collection
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.jsonld")):
            yield collection, path


# Fields that identify or locate a value but are not useful corpus text.
PROJECTION_IGNORED_KEYS = {
    "@context",
    "@id",
    "@type",
    "slug",
    "source",
    "sourceLocator",
    "contentDigest",
    "sourceDigest",
    "corpusDigest",
}


def iter_text_fragments(
    value,
    path: str = "",
    locator: dict | None = None,
) -> Iterator[dict]:
    """Yield every human-meaningful scalar with its structural path.

    This is the shared, recursive textual projection used by LLM output,
    search, and semantic-review tooling.  A nested source locator overrides
    its parent's locator so feature-level review signals retain precise
    provenance.
    """
    if isinstance(value, dict):
        inherited = value.get("sourceLocator", locator)
        for key, child in value.items():
            if key in PROJECTION_IGNORED_KEYS:
                continue
            child_path = f"{path}.{key}" if path else key
            yield from iter_text_fragments(child, child_path, inherited)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_text_fragments(child, f"{path}[{index}]", locator)
    elif isinstance(value, (str, int, float, bool)):
        text = str(value)
        if text:
            yield {"path": path, "text": text, "sourceLocator": locator}


def projected_text(record: dict) -> str:
    """Return a complete plain-text projection of a corpus record."""
    return "\n".join(fragment["text"] for fragment in iter_text_fragments(record))
