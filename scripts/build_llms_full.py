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
    iter_text_fragments,
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
    fragments = list(iter_text_fragments(record))
    # A larger source-faithful prose/table fragment already carries any
    # contained nested/scalar value exactly.  Keeping only maximal strings
    # avoids duplicate monster sections and table cells while remaining a
    # complete recursive projection.
    selected = []
    seen = set()
    for fragment in sorted(fragments, key=lambda f: -len(f["text"])):
        value = fragment["text"]
        if value == record["name"] or value in seen:
            continue
        if any(value in existing["text"] for existing in selected):
            continue
        seen.add(value)
        selected.append(fragment)
    selected.sort(key=lambda f: fragments.index(f))
    for fragment in selected:
        value = fragment["text"]
        lines.append("")
        lines.append(f"[{fragment['path']}]")
        lines.append(value)
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
        noun = "record" if len(records) == 1 else "records"
        out.append(f"## Collection: {collection} ({len(records)} {noun})")
        out.append("")
        for record in records:
            out.append(format_record(record))
            out.append("")
    output = "\n".join(out) + "\n"
    (root / "llms-full.txt").write_text(output, encoding="utf-8")
    print(f"llms-full.txt: {len(output.splitlines())} physical lines")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
