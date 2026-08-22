"""Semantic review-signal ledger.

Scans every record's prose for signals a human should eventually verify
(dice formulas, player choices, slot-level scaling) and tracks them in
objects/sources/source-review-ledger.json with stable keys so triage
dispositions survive rebuilds.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from srdlib import dump_json, iter_object_files, load_json

SIGNALS = {
    "formula": re.compile(r"\b\d+d\d+(?:\s*[+-]\s*\d+)?\b"),
    "choice": re.compile(r"\bchoose (?:one|two|three|a|an|any|which)\b", re.I),
    "scaling": re.compile(r"Using a Higher-Level Spell Slot"),
}
LEDGER = "objects/sources/source-review-ledger.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    previous = {}
    ledger_path = root / LEDGER
    if ledger_path.exists():
        previous = {s["key"]: s for s in load_json(ledger_path)["signals"]}

    signals = []
    for collection, path in iter_object_files(root):
        record = load_json(path)
        text = record.get("rulesText", "")
        if not text:
            continue
        for category, pattern in SIGNALS.items():
            for match in sorted(set(pattern.findall(text))):
                key = hashlib.sha256(
                    f"{record['@id']}|{category}|{match}".encode("utf-8")
                ).hexdigest()[:16]
                prior = previous.get(key, {})
                signals.append(
                    {
                        "key": key,
                        "record": record["@id"],
                        "category": category,
                        "match": match,
                        "status": prior.get("status", "pending"),
                        **({"note": prior["note"]} if "note" in prior else {}),
                    }
                )
    signals.sort(key=lambda s: (s["record"], s["category"], s["match"]))
    counts = {}
    for signal in signals:
        counts[signal["status"]] = counts.get(signal["status"], 0) + 1
    dump_json(ledger_path, {"statusCounts": counts, "signals": signals})
    print(f"review-ledger: {len(signals)} signals ({counts})")


if __name__ == "__main__":
    main()
