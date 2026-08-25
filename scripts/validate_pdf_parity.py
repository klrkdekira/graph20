#!/usr/bin/env python3
"""Validate the Markdown source against the official SRD 5.2.1 PDF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pdf_parity import (
    REGISTRY_PATH,
    build_registry,
    extract_raw_pdf_text,
    load_registry,
    parse_markdown_stat_blocks,
    parse_pdf_stat_blocks,
    semantic_metrics,
    verify_pdf,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-md", default="SRD_CC_v5.2.1.md")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument(
        "--write-registry",
        action="store_true",
        help="Regenerate the checked parity registry from the verified official PDF",
    )
    args = parser.parse_args()

    markdown = Path(args.source_md).read_text(encoding="utf-8")
    raw_text = None
    extractor_version = None
    if args.pdf:
        verify_pdf(args.pdf)
        raw_text, extractor_version = extract_raw_pdf_text(args.pdf)

    if args.write_registry:
        if raw_text is None or extractor_version is None:
            parser.error("--write-registry requires --pdf")
        payload = build_registry(markdown, raw_text, extractor_version)
        REGISTRY_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"Wrote {REGISTRY_PATH} with {len(payload['statBlocks'])} stat blocks."
        )
        return

    registry = load_registry()
    expected = registry["statBlocks"]
    markdown_blocks = parse_markdown_stat_blocks(markdown)
    if markdown_blocks != expected:
        missing = sorted(set(expected) - set(markdown_blocks))
        extra = sorted(set(markdown_blocks) - set(expected))
        changed = sorted(
            name
            for name in set(expected) & set(markdown_blocks)
            if expected[name] != markdown_blocks[name]
        )
        raise SystemExit(
            "Markdown/PDF stat-block parity failed: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )

    if raw_text is not None:
        pdf_blocks = parse_pdf_stat_blocks(raw_text)
        if pdf_blocks != expected:
            raise SystemExit("Verified PDF no longer matches the checked parity registry")
        metrics = semantic_metrics(markdown, raw_text)
        if metrics != registry["semanticMetrics"]:
            raise SystemExit(
                "Markdown/PDF semantic parity metrics drifted:\n"
                + json.dumps(
                    {
                        "expected": registry["semanticMetrics"],
                        "actual": metrics,
                    },
                    indent=2,
                )
            )
        print(
            "Official PDF digest, page count, semantic metrics, and "
            f"{len(expected)} stat blocks match."
        )
    else:
        print(f"Markdown matches all {len(expected)} registered PDF stat blocks.")


if __name__ == "__main__":
    main()
