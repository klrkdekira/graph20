"""Build the aggregate JSON-LD manifest from the emitted corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from srdlib import (
    BASE,
    COLLECTIONS,
    CONTEXT_IRI,
    MANIFEST_NAME,
    SOURCE_ID,
    dump_json,
    iter_object_files,
    load_json,
)

SCHEMA_FOR_COLLECTION = {
    "sources": "source.schema.json",
    "rules": "rule.schema.json",
    "tables": "table.schema.json",
    "spells": "spell.schema.json",
    "feats": "feat.schema.json",
    "magic-items": "magic-item.schema.json",
    "monsters": "monster.schema.json",
}


def build(root: Path) -> None:
    collections = {name: [] for name in COLLECTIONS}
    digest = hashlib.sha256()
    source_record = None
    for collection, path in iter_object_files(root):
        record = load_json(path)
        collections[collection].append({"@id": record["@id"]})
        digest.update(
            json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        )
        if collection == "sources" and record["@id"] == SOURCE_ID:
            source_record = record
    if source_record is None:
        raise SystemExit("source record missing; run extract_srd.py first")

    manifest = {
        "@context": CONTEXT_IRI,
        "@id": f"{BASE}objects/{MANIFEST_NAME.removesuffix('.jsonld')}",
        "@type": "SRDSystemData",
        "version": "0.1.0",
        "metadata": {
            "title": "SRD 5.2.1 System JSON",
            "author": source_record["author"],
            "srdVersion": source_record["srdVersion"],
            "license": source_record["license"],
            "licenseUrl": source_record["licenseUrl"],
            "attributionStatement": source_record["attributionStatement"],
            "source": {"@id": SOURCE_ID},
            "sourceDigest": source_record["contentDigest"],
            "corpusDigest": "sha256-" + digest.hexdigest(),
        },
        "collections": collections,
        "collectionSchemas": {
            name: f"{BASE}systems/{schema}"
            for name, schema in SCHEMA_FOR_COLLECTION.items()
        },
    }
    dump_json(root / "objects" / MANIFEST_NAME, manifest)
    print(f"manifest: {sum(len(v) for v in collections.values())} records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
