"""Generate the asserted build-metrics artifact from emitted outputs."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from srdlib import (
    BUILD_METRICS_NAME,
    MANIFEST_NAME,
    SEMANTIC_RELATIONS,
    dump_json,
    iter_object_files,
    load_json,
    project_version,
)


def relation_count(record: dict, field: str) -> int:
    value = record.get(field)
    if value is None:
        return 0
    return len(value) if isinstance(value, list) else 1


def collect_metrics(root: Path) -> dict:
    records = [load_json(path) for _, path in iter_object_files(root)]
    entity_records = [record for record in records if record["@type"] != "Source"]
    manifest = load_json(root / "objects" / MANIFEST_NAME)
    search = load_json(root / "objects/search-index.json")
    coverage = load_json(root / "objects/sources/source-coverage.json")
    review = load_json(root / "objects/sources/source-review-ledger.json")
    vocab = load_json(root / "vocab/terms.json")
    sitemap = ET.parse(root / "sitemap.xml").getroot()
    relation_counts = {
        field: sum(relation_count(record, field) for record in records)
        for field in sorted(SEMANTIC_RELATIONS)
        if any(field in record for record in records)
    }
    linked = sum(
        1 for record in entity_records if SEMANTIC_RELATIONS.intersection(record)
    )
    record_pages = sum(1 for _ in (root / "records").glob("*/*/index.html"))
    return {
        "version": project_version(root),
        "recordCount": len(records),
        "entityRecordCount": len(entity_records),
        "collectionCount": len(manifest["collections"]),
        "collectionCounts": {
            collection["slug"]: len(collection["members"])
            for collection in manifest["collections"]
        },
        "sourceContentLines": coverage["contentLines"],
        "vocabulary": {
            "classCount": len(vocab["classes"]),
            "propertyCount": len(vocab["properties"]),
        },
        "search": {
            "documentCount": len(search["documents"]),
            "tokenCount": len(search["tokens"]),
            "byteSize": (root / "objects/search-index.json").stat().st_size,
        },
        "review": {
            "signalCount": len(review["signals"]),
            "pendingCount": review["statusCounts"]["pending"],
        },
        "llmsFullPhysicalLines": len(
            (root / "llms-full.txt").read_text(encoding="utf-8").splitlines()
        ),
        "sitemapUrlCount": len(sitemap),
        "recordPageCount": record_pages,
        "semanticGraph": {
            "linkedEntityCount": linked,
            "coveragePercent": round(100 * linked / len(entity_records), 1),
            "predicateCount": len(relation_counts),
            "relationCounts": relation_counts,
        },
    }
def build(root: Path) -> None:
    metrics = collect_metrics(root)
    dump_json(root / "objects" / BUILD_METRICS_NAME, metrics)
    print(
        f"metrics: {metrics['recordCount']} records, {metrics['collectionCount']} collections, "
        f"{metrics['semanticGraph']['coveragePercent']}% semantic-link coverage"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
