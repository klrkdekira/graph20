"""Paragraph-level source coverage ledger.

Maps every non-blank line of the content region (first chapter onward) to
the records whose sourceLocator spans consume it, and fails when any line
is uncovered. Writes objects/sources/source-coverage.json.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from srdlib import CHAPTERS, SOURCE_FILE, dump_json, iter_object_files, load_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    first_chapter = next(
        i for i, l in enumerate(lines) if l.rstrip() == f"# {CHAPTERS[0]}"
    )
    content_start = first_chapter + 1  # 1-based

    covered = [0] * (len(lines) + 2)
    per_collection = {}
    total_records = 0
    for collection, path in iter_object_files(root):
        record = load_json(path)
        locator = record.get("sourceLocator")
        if not locator:
            continue
        total_records += 1
        per_collection[collection] = per_collection.get(collection, 0) + 1
        for line in range(locator["lineStart"], locator["lineEnd"] + 1):
            if line <= len(lines):
                covered[line] += 1
        # Feature/trait/statSection sub-spans are inside the record span.

    uncovered = [
        i
        for i in range(content_start, len(lines) + 1)
        if lines[i - 1].strip() and not covered[i]
    ]
    report = {
        "sourceFile": SOURCE_FILE,
        "contentFirstLine": content_start,
        "excludedPreamble": {
            "lineStart": 1,
            "lineEnd": content_start - 1,
            "reason": "Legal Information and Contents navigation preamble; "
            "license and attribution preserved in the source record.",
        },
        "contentLines": sum(
            1 for i in range(content_start, len(lines) + 1) if lines[i - 1].strip()
        ),
        "uncoveredLines": uncovered,
        "recordCounts": per_collection,
        "recordsWithLocators": total_records,
    }
    dump_json(root / "objects/sources/source-coverage.json", report)
    if uncovered:
        preview = ", ".join(str(i) for i in uncovered[:20])
        print(f"FAIL: {len(uncovered)} uncovered source lines (first: {preview})")
        sys.exit(1)
    print(
        f"coverage: {report['contentLines']} content lines fully covered "
        f"by {total_records} records"
    )


if __name__ == "__main__":
    main()
