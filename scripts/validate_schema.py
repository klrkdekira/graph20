"""Validate every emitted record against its JSON Schema Draft 2020-12 schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from srdlib import (
    MANIFEST_NAME,
    SCHEMA_FOR_COLLECTION,
    iter_object_files,
    load_json,
)


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

    if errors:
        print("\n".join(errors[:40]))
        print(f"FAIL: {len(errors)} schema errors across {count} records")
        sys.exit(1)
    print(f"OK: {count} records + manifest validate against Draft 2020-12 schemas")


if __name__ == "__main__":
    main()
