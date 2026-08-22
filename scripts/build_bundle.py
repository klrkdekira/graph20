"""Bundle every corpus record into a single JSON-LD @graph document."""

from __future__ import annotations

import argparse
from pathlib import Path

from srdlib import (
    BASE,
    BUNDLE_NAME,
    CONTEXT_IRI,
    MANIFEST_NAME,
    dump_json,
    iter_object_files,
    load_json,
)


def build(root: Path) -> None:
    manifest = load_json(root / "objects" / MANIFEST_NAME)
    graph = []
    for _, path in iter_object_files(root):
        record = load_json(path)
        record.pop("@context", None)
        graph.append(record)
    graph.sort(key=lambda r: r["@id"])
    bundle = {
        "@context": CONTEXT_IRI,
        "@id": f"{BASE}objects/{BUNDLE_NAME.removesuffix('.jsonld')}",
        "@type": "SRDSystemData",
        "version": manifest["version"],
        "metadata": manifest["metadata"],
        "@graph": graph,
    }
    dump_json(root / "objects" / BUNDLE_NAME, bundle)
    print(f"bundle: {len(graph)} records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
