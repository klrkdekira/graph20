"""Build and enforce the occurrence-level semantic review ledger."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from srdlib import SOURCE_FILE, dump_json, iter_object_files, iter_text_fragments, load_json

SIGNALS = {
    "formula": re.compile(r"\b\d+d\d+(?:\s*[+-]\s*\d+)?\b"),
    "choice": re.compile(r"\bchoose (?:one|two|three|a|an|any|which)\b", re.I),
    "scaling": re.compile(r"Using a Higher-Level Spell Slot"),
}
PROSE_KEYS = {"rulesText", "description", "value"}
LEDGER = "objects/sources/source-review-ledger.json"
POLICIES = "reviews/semantic-review-policies.json"


def source_positions(lines, locator, token, fragment_text=None):
    positions = []
    if not locator:
        return positions
    if fragment_text and "\n" not in fragment_text:
        token_offsets = [
            match.start() for match in re.finditer(re.escape(token), fragment_text)
        ]
        if token_offsets:
            for line_number in range(locator["lineStart"], locator["lineEnd"] + 1):
                line = lines[line_number - 1]
                cursor = 0
                while True:
                    fragment_column = line.find(fragment_text, cursor)
                    if fragment_column < 0:
                        break
                    positions.extend(
                        (line_number, fragment_column + offset + 1)
                        for offset in token_offsets
                    )
                    cursor = fragment_column + max(1, len(fragment_text))
            if positions:
                return positions
    for line_number in range(locator["lineStart"], locator["lineEnd"] + 1):
        line = lines[line_number - 1]
        cursor = 0
        while True:
            column = line.find(token, cursor)
            if column < 0:
                break
            positions.append((line_number, column + 1))
            cursor = column + max(1, len(token))
    return positions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    policies = load_json(root / POLICIES)
    source_lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    signals = []
    seen = set()
    missing_locations = []

    for _, path in iter_object_files(root):
        record = load_json(path)
        root_locator = record.get("sourceLocator")
        for fragment in iter_text_fragments(record):
            field = re.sub(r".*\.", "", fragment["path"]).split("[")[0]
            if field not in PROSE_KEYS or fragment["path"].endswith("rawText"):
                continue
            text = fragment["text"]
            locator = fragment.get("sourceLocator") or root_locator
            for category, pattern in SIGNALS.items():
                occurrence_by_token = {}
                for match in pattern.finditer(text):
                    token = match.group(0)
                    occurrence = occurrence_by_token.get(token, 0)
                    occurrence_by_token[token] = occurrence + 1
                    positions = source_positions(source_lines, locator, token, text)
                    position = positions[occurrence] if occurrence < len(positions) else None
                    if not position:
                        missing_locations.append(
                            f"{record['@id']} {fragment['path']} {token!r}"
                        )
                        continue
                    identity = (record["@id"], category, token, *position)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    policy = policies["signalCategories"].get(category, {})
                    start = max(0, match.start() - 70)
                    end = min(len(text), match.end() + 70)
                    context = re.sub(r"\s+", " ", text[start:end]).strip()
                    key = hashlib.sha256("|".join(map(str, identity)).encode()).hexdigest()[:16]
                    signals.append(
                        {
                            "key": key,
                            "record": record["@id"],
                            "category": category,
                            "match": token,
                            "path": fragment["path"],
                            "sourceLine": position[0],
                            "sourceColumn": position[1],
                            "context": context,
                            "status": policy.get("status", "pending"),
                            "note": policy.get("note", "No review policy exists for this category."),
                        }
                    )

    overrides = policies.get("signalOverrides", {})
    for signal in signals:
        if signal["key"] in overrides:
            signal.update(overrides[signal["key"]])
    signals.sort(key=lambda s: (s["record"], s["sourceLine"], s["sourceColumn"], s["category"]))
    signal_set_digest = "sha256-" + hashlib.sha256(
        "\n".join(sorted(signal["key"] for signal in signals)).encode("utf-8")
    ).hexdigest()
    if signal_set_digest != policies.get("reviewedSignalSetDigest"):
        for signal in signals:
            if signal["key"] not in overrides:
                signal["status"] = "pending"
                signal["note"] = (
                    "The occurrence set changed after review; update the curated "
                    "signal-set digest only after reviewing added, removed, or moved signals."
                )
    counts = {status: 0 for status in policies["statusDefinitions"]}
    for signal in signals:
        counts[signal["status"]] = counts.get(signal["status"], 0) + 1

    checks = []
    for category, policy in sorted(policies["auditChecks"].items()):
        checks.append({"category": category, **policy})
        counts[policy["status"]] = counts.get(policy["status"], 0) + 1

    dump_json(
        root / LEDGER,
        {
            "statusDefinitions": policies["statusDefinitions"],
            "signalSetDigest": signal_set_digest,
            "statusCounts": counts,
            "reviewChecks": checks,
            "signals": signals,
        },
    )
    pending = counts.get("pending", 0)
    if missing_locations:
        print("\n".join(missing_locations[:20]))
        print(f"FAIL: {len(missing_locations)} review occurrences lack a source location")
        sys.exit(1)
    if pending:
        print(f"FAIL: review-ledger has {pending} pending signals")
        sys.exit(1)
    print(f"review-ledger: {len(signals)} occurrence signals, zero pending ({counts})")


if __name__ == "__main__":
    main()
