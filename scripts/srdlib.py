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
    "spells",
    "feats",
    "magic-items",
    "monsters",
]

COLLECTION_TYPES = {
    "sources": "Source",
    "rules": "Rule",
    "tables": "Table",
    "spells": "Spell",
    "feats": "Feat",
    "magic-items": "MagicItem",
    "monsters": "Monster",
}

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
