"""Expand the complete JSON-LD corpus and reject compact/graph data loss."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyld import jsonld

from srdlib import (
    BASE,
    BUNDLE_NAME,
    COLLECTION_TYPES,
    MANIFEST_NAME,
    iter_object_files,
    load_json,
)


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def compact_properties(value):
    found = set()
    for node in walk(value):
        if isinstance(node, dict):
            found.update(key for key in node if not key.startswith("@"))
    return found


def expanded_properties(value):
    found = set()
    for node in walk(value):
        if isinstance(node, dict):
            found.update(key for key in node if not key.startswith("@"))
    return found


def expanded_values(value):
    return [node["@value"] for node in walk(value) if isinstance(node, dict) and "@value" in node]


def literal_values(value, parent_key=None):
    values = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("@context", "@id", "@type"):
                continue
            values.extend(literal_values(child, key))
    elif isinstance(value, list):
        for child in value:
            values.extend(literal_values(child, parent_key))
    elif isinstance(value, (str, int, float, bool)):
        values.append(value)
    return values


def resolve_term(term, context):
    definition = context.get(term)
    iri = definition.get("@id") if isinstance(definition, dict) else definition
    if not iri:
        iri = context["@vocab"] + term
    if ":" in iri and not iri.startswith(("http://", "https://")):
        prefix, suffix = iri.split(":", 1)
        iri = context[prefix] + suffix
    return iri


def validate_node_shapes(value, iri_terms, path=""):
    errors = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in iri_terms:
                values = child if isinstance(child, list) else [child]
                if not all(isinstance(item, dict) and set(item) == {"@id"} for item in values):
                    errors.append(f"{child_path}: IRI-coerced value is not a node reference")
            errors.extend(validate_node_shapes(child, iri_terms, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(validate_node_shapes(child, iri_terms, f"{path}[{index}]"))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    context = load_json(root / "systems/context.jsonld")["@context"]
    iri_terms = {
        term
        for term, definition in context.items()
        if isinstance(definition, dict) and definition.get("@type") == "@id"
    }
    errors = []
    documents = [(str(path), load_json(path)) for _, path in iter_object_files(root)]
    documents.extend(
        (name, load_json(root / "objects" / name))
        for name in (MANIFEST_NAME, BUNDLE_NAME)
    )
    seen_types = set()
    seen_project_terms = set()
    vocab_base = context["@vocab"]

    for label, document in documents:
        errors.extend(f"{label}: {error}" for error in validate_node_shapes(document, iri_terms))
        compact = dict(document)
        compact["@context"] = context
        try:
            expanded = jsonld.expand(compact)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"{label}: JSON-LD expansion failed: {exc}")
            continue
        if not expanded:
            errors.append(f"{label}: JSON-LD expansion produced no graph")
            continue
        expanded_keys = expanded_properties(expanded)
        seen_project_terms.update(key for key in expanded_keys if key.startswith(vocab_base))
        for term in compact_properties(document):
            expected = resolve_term(term, context)
            if expected not in expanded_keys:
                errors.append(f"{label}: compact property {term!r} was lost during expansion")
        values = expanded_values(expanded)
        for literal in literal_values(document):
            if literal not in values:
                errors.append(f"{label}: literal value {literal!r} was lost during expansion")
        for node in walk(expanded):
            if isinstance(node, dict):
                seen_types.update(node.get("@type", []))
                seen_project_terms.update(
                    item for item in node.get("@type", []) if item.startswith(vocab_base)
                )

    expected_types = {
        context["@vocab"] + type_name
        for type_name in set(COLLECTION_TYPES.values()) | {"SRDSystemData"}
    }
    missing_types = expected_types - seen_types
    if missing_types:
        errors.append(f"entity types not represented in expanded graph: {sorted(missing_types)}")

    vocab = load_json(root / "vocab/terms.json")
    defined_terms = {
        entry["iri"] for entry in vocab.get("classes", []) + vocab.get("properties", [])
    }
    undocumented = seen_project_terms - defined_terms
    if undocumented:
        errors.append(f"expanded project terms missing vocabulary definitions: {sorted(undocumented)}")

    if errors:
        print("\n".join(errors[:50]))
        print(f"FAIL: {len(errors)} JSON-LD graph-fidelity errors")
        sys.exit(1)
    print(
        f"graph: expanded {len(documents) - 2} records, manifest, and bundle; "
        f"all {len(iri_terms)} IRI-coerced terms use node references"
    )


if __name__ == "__main__":
    main()
