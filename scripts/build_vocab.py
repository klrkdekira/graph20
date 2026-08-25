"""Publish every project-namespace class and predicate used by the corpus."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from srdlib import BASE, COLLECTION_TYPES, MANIFEST_NAME, dump_json, iter_object_files, load_json


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def resolve_term(term, context):
    definition = context.get(term)
    iri = (
        definition.get("@id") or definition.get("@reverse")
        if isinstance(definition, dict)
        else definition
    )
    if not iri:
        return context["@vocab"] + term
    if ":" in iri and not iri.startswith(("http://", "https://")):
        prefix, suffix = iri.split(":", 1)
        return context[prefix] + suffix
    return iri


def humanize(term):
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", term).replace("-", " ")
    return words[:1].upper() + words[1:]


def value_kind(value, iri_coerced):
    if iri_coerced:
        return "IRI node reference"
    if isinstance(value, bool):
        return "boolean literal"
    if isinstance(value, int):
        return "integer literal"
    if isinstance(value, float):
        return "number literal"
    if isinstance(value, str):
        return "string literal"
    if isinstance(value, list):
        return "ordered/set values"
    if isinstance(value, dict):
        return "structured blank node"
    return type(value).__name__


def relation_range(value):
    values = value if isinstance(value, list) else [value]
    ranges = set()
    inverse_types = {collection: entity_type for collection, entity_type in COLLECTION_TYPES.items()}
    for item in values:
        if not isinstance(item, dict) or "@id" not in item:
            continue
        iri = item["@id"]
        marker = BASE + "objects/"
        if iri.startswith(marker):
            collection = iri.removeprefix(marker).split("/", 1)[0]
            ranges.add(inverse_types.get(collection, "Corpus entity"))
        elif iri.startswith(BASE + "systems/"):
            ranges.add("JSON Schema")
        else:
            ranges.add("External IRI")
    return ranges


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    context = load_json(root / "systems/context.jsonld")["@context"]
    vocab_base = context["@vocab"]
    documents = [load_json(path) for _, path in iter_object_files(root)]
    documents.append(load_json(root / "objects" / MANIFEST_NAME))

    observations = {}
    classes = set()
    for document in documents:
        for node in walk(document):
            if not isinstance(node, dict):
                continue
            node_type = node.get("@type")
            if isinstance(node_type, str):
                iri = node_type if "://" in node_type else vocab_base + node_type
                if iri.startswith(vocab_base):
                    classes.add(iri)
            for term, value in node.items():
                if term.startswith("@"):
                    continue
                iri = resolve_term(term, context)
                if not iri.startswith(vocab_base):
                    continue
                definition = context.get(term)
                iri_coerced = isinstance(definition, dict) and definition.get("@type") == "@id"
                entry = observations.setdefault(
                    iri,
                    {"terms": set(), "valueKinds": set(), "ranges": set(), "relationship": iri_coerced},
                )
                entry["terms"].add(term)
                entry["valueKinds"].add(value_kind(value, iri_coerced))
                if iri_coerced:
                    entry["ranges"].update(relation_range(value))

    # Explicit project terms remain documented even when a clean build has no
    # current occurrence.
    for term, definition in context.items():
        if term.startswith("@") or term in ("srd", "schema", "dcterms"):
            continue
        iri = resolve_term(term, context)
        if not iri.startswith(vocab_base):
            continue
        iri_coerced = isinstance(definition, dict) and definition.get("@type") == "@id"
        entry = observations.setdefault(
            iri,
            {"terms": set(), "valueKinds": set(), "ranges": set(), "relationship": iri_coerced},
        )
        entry["terms"].add(term)
        if iri_coerced and not entry["valueKinds"]:
            entry["valueKinds"].add("IRI node reference")

    properties = []
    for iri, data in sorted(observations.items()):
        anchor = iri.removeprefix(vocab_base)
        terms = sorted(data["terms"])
        relationship = data["relationship"]
        properties.append(
            {
                "iri": iri,
                "anchor": anchor,
                "jsonTerms": terms,
                "description": (
                    f"Links the subject using the {', '.join(terms)} relationship."
                    if relationship
                    else f"Carries the {humanize(terms[0]).lower()} value."
                ),
                "valueKinds": sorted(data["valueKinds"] or {"not currently emitted"}),
                "ranges": sorted(
                    data["ranges"]
                    or ({"IRI target (not currently emitted)"} if relationship else {"Literal or structured value"})
                ),
            }
        )
    class_defs = [
        {
            "iri": iri,
            "anchor": iri.removeprefix(vocab_base),
            "description": f"JSON-LD class for {humanize(iri.removeprefix(vocab_base)).lower()} records.",
        }
        for iri in sorted(classes | {vocab_base + "SRDSystemData"})
    ]
    inventory = {"vocabulary": vocab_base, "classes": class_defs, "properties": properties}
    dump_json(root / "vocab/terms.json", inventory)

    property_rows = "\n".join(
        f'<tr id="{html.escape(entry["anchor"])}"><td><a href="#{html.escape(entry["anchor"])}"><code>{html.escape(entry["iri"])}</code></a></td>'
        f'<td><code>{html.escape(", ".join(entry["jsonTerms"]))}</code></td>'
        f'<td>{html.escape(entry["description"])}</td>'
        f'<td>{html.escape(", ".join(entry["valueKinds"]))}</td>'
        f'<td>{html.escape(", ".join(entry["ranges"]))}</td></tr>'
        for entry in properties
    )
    class_rows = "\n".join(
        f'<tr id="{html.escape(entry["anchor"])}"><td><a href="#{html.escape(entry["anchor"])}"><code>{html.escape(entry["iri"])}</code></a></td>'
        f'<td>{html.escape(entry["description"])}</td><td>class</td></tr>'
        for entry in class_defs
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SRD 5.2.1 System JSON Vocabulary</title>
<style>
body {{ font: 15px/1.6 system-ui, sans-serif; max-width: 80rem; margin: 2rem auto; padding: 0 1rem; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ccc; padding: .35rem .6rem; text-align: left; vertical-align: top; }}
code {{ background: #f2f2f2; padding: .05rem .3rem; border-radius: 4px; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>SRD 5.2.1 System JSON Vocabulary</h1>
<p>Every class and predicate used in a clean expanded corpus under
<code>{html.escape(vocab_base)}</code>. Fragment IRIs dereference to this page.
Generated by <code>scripts/build_vocab.py</code>; do not edit by hand.</p>
<h2>Classes</h2>
<table><tr><th>IRI</th><th>Description</th><th>Kind</th></tr>{class_rows}</table>
<h2>Properties</h2>
<table><tr><th>IRI</th><th>JSON term</th><th>Description</th><th>Value kind</th><th>Observed range</th></tr>{property_rows}</table>
</body>
</html>
"""
    out = root / "vocab/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"vocab: {len(properties)} properties, {len(class_defs)} classes")


if __name__ == "__main__":
    main()
