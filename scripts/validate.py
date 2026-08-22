"""Dependency-free structural validation of the emitted corpus.

Checks: JSON syntax, required identity fields, unique @id values, slug and
filename agreement, source-locator line bounds, and that every internal
node reference resolves to an emitted record.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from srdlib import (
    BASE,
    BUNDLE_NAME,
    CONTEXT_IRI,
    MANIFEST_NAME,
    SOURCE_FILE,
    iter_object_files,
    load_json,
)

REQUIRED = ("@context", "@id", "@type", "name", "slug", "source", "sourceLocator")


def collect_references(value, out):
    if isinstance(value, dict):
        if set(value.keys()) == {"@id"}:
            out.append(value["@id"])
        else:
            for key, item in value.items():
                if key != "@id":
                    collect_references(item, out)
    elif isinstance(value, list):
        for item in value:
            collect_references(item, out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    errors = []
    ids = {}
    records = []
    line_count = len(
        (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    )

    for collection, path in iter_object_files(root):
        try:
            record = load_json(path)
        except ValueError as exc:
            errors.append(f"{path}: invalid JSON ({exc})")
            continue
        records.append((collection, path, record))
        rid = record.get("@id", "")
        if rid in ids:
            errors.append(f"{path}: duplicate @id {rid} (also {ids[rid]})")
        ids[rid] = path
        if collection == "sources":
            continue
        for field in REQUIRED:
            if field not in record:
                errors.append(f"{path}: missing {field}")
        if record.get("@context") != CONTEXT_IRI:
            errors.append(f"{path}: wrong @context")
        if not rid.startswith(f"{BASE}objects/{collection}/"):
            errors.append(f"{path}: @id outside collection base: {rid}")
        if rid.rsplit("/", 1)[-1] != record.get("slug"):
            errors.append(f"{path}: slug does not match @id")
        if path.stem != record.get("slug"):
            errors.append(f"{path}: filename does not match slug")
        locator = record.get("sourceLocator", {})
        start, end = locator.get("lineStart", 0), locator.get("lineEnd", 0)
        if not (1 <= start <= end <= line_count):
            errors.append(f"{path}: bad line bounds {start}-{end}")

    for collection, path, record in records:
        refs = []
        collect_references(record, refs)
        for ref in refs:
            if ref.startswith(BASE) and ref not in ids:
                errors.append(f"{path}: unresolved reference {ref}")

    # Manifest and bundle resolve too.
    for name in (MANIFEST_NAME, BUNDLE_NAME):
        doc_path = root / "objects" / name
        if not doc_path.exists():
            errors.append(f"missing {name}")
            continue
        doc = load_json(doc_path)
        refs = []
        collect_references(doc.get("collections", doc), refs)
        for ref in refs:
            if ref.startswith(f"{BASE}objects/") and ref not in ids:
                errors.append(f"{name}: unresolved reference {ref}")

    if errors:
        print("\n".join(errors[:50]))
        print(f"FAIL: {len(errors)} structural errors")
        sys.exit(1)
    print(f"OK: {len(records)} records structurally valid, all references resolve")


if __name__ == "__main__":
    main()
