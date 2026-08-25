"""Fail when a source-anomaly hit lacks an explicit reviewed disposition."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from srdlib import SOURCE_FILE, load_json, sha256_of


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    text = (root / SOURCE_FILE).read_text(encoding="utf-8")
    current_digest = sha256_of(root / SOURCE_FILE)
    registry = load_json(root / "objects/sources/extraction-overrides.json")
    errors = []
    total = 0
    if registry.get("validatedSourceDigest") != current_digest:
        errors.append(f"registry validatedSourceDigest does not match {SOURCE_FILE}")
    for review in registry.get("anomalyReviews", []):
        for required in (
            "observedTokens",
            "proposedFix",
            "rationale",
            "status",
            "affectedCount",
            "preRepairDigest",
            "postRepairDigest",
        ):
            if required not in review:
                errors.append(f"{review.get('id', '<unknown>')}: missing registry field {required}")
        hits = list(re.finditer(review["pattern"], text))
        total += len(hits)
        expected = review["expectedRemaining"]
        if review["status"] not in ("resolved", "false-positive"):
            errors.append(f"{review['id']}: unreviewed status {review['status']!r}")
        if not isinstance(review.get("affectedCount"), int) or review["affectedCount"] < 1:
            errors.append(f"{review['id']}: affectedCount must be a positive integer")
        if len(hits) != expected:
            lines = [text.count("\n", 0, hit.start()) + 1 for hit in hits[:8]]
            errors.append(
                f"{review['id']}: expected {expected} remaining hits, found {len(hits)}"
                + (f" at lines {lines}" if lines else "")
            )
    if errors:
        print("\n".join(errors))
        print("FAIL: anomaly registry is stale or incomplete")
        sys.exit(1)
    print(
        f"anomalies: {len(registry.get('anomalyReviews', []))} reviewed detectors, "
        f"{total} allowed source hits"
    )


if __name__ == "__main__":
    main()
