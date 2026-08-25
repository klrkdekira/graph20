"""Generate the compact llms.txt corpus entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from srdlib import ATTRIBUTION_STATEMENT, BASE, MANIFEST_NAME, load_json


def build(root: Path) -> None:
    manifest = load_json(root / "objects" / MANIFEST_NAME)
    counts = {
        collection["slug"]: len(collection["members"])
        for collection in manifest["collections"]
    }
    total = sum(counts.values())
    collection_lines = "\n".join(
        f"- {collection['name']}: {len(collection['members'])} {collection['entityType']} "
        f"{'record' if len(collection['members']) == 1 else 'records'}"
        for collection in manifest["collections"]
    )
    text = f"""# SRD 5.2.1 System JSON

> Machine-readable JSON-LD 1.1 reference corpus for the System Reference Document 5.2.1, with JSON Schema Draft 2020-12 validation. {total:,} records preserve source wording, typed indexes, graph links, and physical line provenance.

Attribution: {ATTRIBUTION_STATEMENT}

## Entry points

- [Human-readable explorer]({BASE})
- [Full corpus context]({BASE}llms-full.txt): complete recursive text projection
- [Aggregate manifest]({BASE}objects/{MANIFEST_NAME}): collection membership, schemas, and digests
- [Single-file bundle]({BASE}objects/srd52-system-data.bundle.jsonld): all records in one @graph
- [Search index]({BASE}objects/search-index.json): static inverted token index
- [Collection index]({BASE}objects/collection-index.json): compact browse metadata
- [JSON-LD context]({BASE}systems/context.jsonld)
- [Vocabulary terms]({BASE}vocab/terms.json)

## Collections

Raw records use `objects/<collection>/<slug>.jsonld`; indexable HTML counterparts use `records/<collection>/<slug>/`. Every HTML page declares its JSON-LD alternate, and every JSON-LD record carries `htmlPage`.

{collection_lines}

Typed relations include `listsSpell`, `castsSpell`, `mentionsCondition`, `grantsFeat`, `hasGear`, `summons`, `areaShapes`, `grantsTool`, `grantsEquipment`, `relatedRules`, `relatedTables`, `seeAlso`, and catalog `hasPart` links. Core incoming directions have JSON-LD `@reverse` aliases.

## Documentation

- [README]({BASE}README.md)
- [Technical specification]({BASE}SPECIFICATION.md)
- [Replication checklist]({BASE}CHECKLIST.md)
"""
    (root / "llms.txt").write_text(text, encoding="utf-8")
    print(f"llms.txt: {total} records across {len(counts)} collections")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
