"""Generate llms-full.txt: single-file LLM ingestion context for the corpus.

Inlines the complete source-faithful text of every entity with its canonical
@id so an LLM can answer rules questions from this one file. Never hand-edit.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from srdlib import (
    ATTRIBUTION_STATEMENT,
    BASE,
    COLLECTIONS,
    MANIFEST_NAME,
    iter_object_files,
    load_json,
)


def format_record(record) -> str:
    lines = [f"### {record['name']}", f"id: {record['@id']}"]
    locator = record.get("sourceLocator")
    if locator:
        lines.append(
            f"source: {locator['chapter']} §{locator['section']} "
            f"(lines {locator['lineStart']}-{locator['lineEnd']})"
        )
    for key in (
        "level",
        "school",
        "classAvailability",
        "castingTime",
        "range",
        "components",
        "duration",
        "category",
        "prerequisite",
        "itemCategory",
        "rarity",
        "requiresAttunement",
        "sizeTypeAlignment",
        "armorClass",
        "hitPoints",
        "speed",
        "challenge",
    ):
        if key in record:
            value = record[key]
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"{key}: {value}")
    if "columns" in record:
        lines.append("columns: " + " | ".join(record["columns"]))
        for row in record.get("rows", []):
            lines.append("row: " + " | ".join(c["value"] for c in row["cells"]))
    if record.get("rulesText"):
        lines.append("")
        lines.append(record["rulesText"])
    return "\n".join(lines)


def build(root: Path) -> None:
    manifest = load_json(root / "objects" / MANIFEST_NAME)
    out = [
        "# SRD 5.2.1 System JSON — full corpus context",
        "",
        "Machine-readable JSON-LD 1.1 reference corpus for the System Reference "
        "Document 5.2.1 (D&D fifth edition rules, CC-BY-4.0).",
        f"Base IRI: {BASE}",
        f"Manifest: {BASE}objects/{MANIFEST_NAME}",
        f"Source digest: {manifest['metadata']['sourceDigest']}",
        f"Corpus digest: {manifest['metadata']['corpusDigest']}",
        "",
        "Attribution: " + ATTRIBUTION_STATEMENT,
        "",
    ]
    for collection in COLLECTIONS:
        records = [
            load_json(path)
            for c, path in iter_object_files(root)
            if c == collection
        ]
        out.append(f"## Collection: {collection} ({len(records)} records)")
        out.append("")
        for record in records:
            out.append(format_record(record))
            out.append("")
    (root / "llms-full.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"llms-full.txt: {len(out)} lines")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
