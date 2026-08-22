"""CLI for triaging review-ledger signals.

Usage:
  manage_review_ledger.py --stats
  manage_review_ledger.py --list pending [--limit 20]
  manage_review_ledger.py --set KEY accepted|corrected|false-positive [--note TEXT]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from srdlib import dump_json, load_json

LEDGER = Path(__file__).resolve().parent.parent / "objects/sources/source-review-ledger.json"
POLICIES = Path(__file__).resolve().parent.parent / "reviews/semantic-review-policies.json"
STATUSES = ("pending", "accepted", "corrected", "false-positive")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--list", dest="list_status", choices=STATUSES)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--set", nargs=2, metavar=("KEY", "STATUS"))
    parser.add_argument("--note")
    args = parser.parse_args()

    ledger = load_json(LEDGER)
    signals = ledger["signals"]

    if args.stats or (not args.list_status and not args.set):
        counts = {}
        for signal in signals:
            counts[signal["status"]] = counts.get(signal["status"], 0) + 1
        for status in STATUSES:
            print(f"{status}: {counts.get(status, 0)}")
        return

    if args.list_status:
        shown = 0
        for signal in signals:
            if signal["status"] == args.list_status:
                print(f"{signal['key']}  {signal['category']:8} {signal['match']!r:24} {signal['record']}")
                shown += 1
                if shown >= args.limit:
                    break
        return

    key, status = args.set
    if status not in STATUSES:
        raise SystemExit(f"status must be one of {STATUSES}")
    hit = False
    selected = None
    for signal in signals:
        if signal["key"] == key:
            selected = signal
            hit = True
    if not hit:
        raise SystemExit(f"no signal with key {key}")
    policies = load_json(POLICIES)
    override = {"status": status}
    if args.note:
        override["note"] = args.note
    else:
        override["note"] = selected.get("note", "Occurrence-level reviewer disposition.")
    policies.setdefault("signalOverrides", {})[key] = override
    dump_json(POLICIES, policies)
    print(f"{key} -> {status}; saved in reviews/semantic-review-policies.json (run make review)")


if __name__ == "__main__":
    main()
