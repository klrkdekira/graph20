"""Validate every emitted record against its JSON Schema Draft 2020-12 schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from srdlib import (
    BUILD_METRICS_NAME,
    BUNDLE_NAME,
    CONTEXT_IRI,
    MANIFEST_NAME,
    SCHEMA_FOR_COLLECTION,
    iter_object_files,
    load_json,
)

AUXILIARY_SCHEMAS = {
    BUNDLE_NAME: "bundle.schema.json",
    "search-index.json": "search-index.schema.json",
    "collection-index.json": "collection-index.schema.json",
    "sources/source-coverage.json": "coverage.schema.json",
    "sources/source-review-ledger.json": "review-ledger.schema.json",
    BUILD_METRICS_NAME: "build-metrics.schema.json",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    systems = root / "systems"

    resources = []
    for path in sorted(systems.glob("*.schema.json")):
        schema = load_json(path)
        resources.append((schema["$id"], Resource.from_contents(schema)))
        # Allow relative $ref like "common.schema.json#/..."
        resources.append((path.name, Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)

    validators = {}
    for collection, schema_name in SCHEMA_FOR_COLLECTION.items():
        schema = load_json(systems / schema_name)
        validators[collection] = Draft202012Validator(schema, registry=registry)
    system_validator = Draft202012Validator(
        load_json(systems / "system.schema.json"), registry=registry
    )

    errors = []
    count = 0
    for collection, path in iter_object_files(root):
        record = load_json(path)
        count += 1
        for error in validators[collection].iter_errors(record):
            errors.append(f"{path}: {error.message}")

    manifest = load_json(root / "objects" / MANIFEST_NAME)
    for error in system_validator.iter_errors(manifest):
        errors.append(f"{MANIFEST_NAME}: {error.message}")

    # The bundle envelope has its own schema, while every graph member must
    # also satisfy the exact schema of its source collection. Bundle nodes
    # inherit @context from the envelope, so restore it for record validation.
    bundle = load_json(root / "objects" / BUNDLE_NAME)
    for index, node in enumerate(bundle["@graph"]):
        marker = "/objects/"
        try:
            collection = node["@id"].split(marker, 1)[1].split("/", 1)[0]
            validator = validators[collection]
        except (KeyError, IndexError):
            errors.append(f"{BUNDLE_NAME} @graph[{index}]: cannot resolve collection schema")
            continue
        record = {"@context": CONTEXT_IRI, **node}
        for error in validator.iter_errors(record):
            errors.append(f"{BUNDLE_NAME} @graph[{index}] ({node.get('@id')}): {error.message}")

    auxiliary_count = 0
    for relative, schema_name in AUXILIARY_SCHEMAS.items():
        document = load_json(root / "objects" / relative)
        validator = Draft202012Validator(load_json(systems / schema_name), registry=registry)
        auxiliary_count += 1
        for error in validator.iter_errors(document):
            errors.append(f"{relative}: {error.message}")

    if errors:
        print("\n".join(errors[:40]))
        print(f"FAIL: {len(errors)} schema errors across {count} records")
        sys.exit(1)
    print(
        f"OK: {count} records, manifest, and {auxiliary_count} auxiliary artifacts "
        "validate against Draft 2020-12 schemas"
    )


if __name__ == "__main__":
    main()
