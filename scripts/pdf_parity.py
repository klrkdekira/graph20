"""Shared helpers for SRD 5.2.1 PDF/Markdown parity validation.

The checked-in registry is a compact, deterministic transcription of data
whose two-column PDF layout is particularly easy to associate with the wrong
stat block.  The official PDF remains the authority; the registry lets normal
offline builds enforce those values without downloading or vendoring it.
"""

from __future__ import annotations

import bisect
import hashlib
import html
import json
import re
import subprocess
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


OFFICIAL_PDF_URL = (
    "https://media.dndbeyond.com/compendium-images/srd/5.2/"
    "SRD_CC_v5.2.1.pdf"
)
OFFICIAL_PDF_SHA256 = (
    "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87"
)
OFFICIAL_PDF_PAGES = 364
REGISTRY_PATH = Path(__file__).with_name("data") / "srd-5.2.1-pdf-parity.json"
ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")


MARKDOWN_STAT_TABLE_RE = re.compile(
    r"\| STR \| DEX \| CON \| INT \| WIS \| CHA \|\n"
    r"\|[^\n]+\|\n"
    r"\|\s*(\d+)\s*\(([+\N{MINUS SIGN}-]?\d+)\)\s*"
    r"\|\s*(\d+)\s*\(([+\N{MINUS SIGN}-]?\d+)\)\s*"
    r"\|\s*(\d+)\s*\(([+\N{MINUS SIGN}-]?\d+)\)\s*"
    r"\|\s*(\d+)\s*\(([+\N{MINUS SIGN}-]?\d+)\)\s*"
    r"\|\s*(\d+)\s*\(([+\N{MINUS SIGN}-]?\d+)\)\s*"
    r"\|\s*(\d+)\s*\(([+\N{MINUS SIGN}-]?\d+)\)\s*\|\n"
    r"\|\s*Save:\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"\|\s*Save:\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"\|\s*Save:\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"\|\s*Save:\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"\|\s*Save:\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"\|\s*Save:\s*([+\N{MINUS SIGN}-]?\d+)\s*\|"
)

PDF_STAT_TABLE_RE = re.compile(
    r"(?m)^Str\s*(\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"Dex\s*(\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"Con\s*(\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*\n"
    r"Int\s*(\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"Wis\s*(\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*"
    r"Cha\s*(\d+)\s*([+\N{MINUS SIGN}-]?\d+)\s*([+\N{MINUS SIGN}-]?\d+)"
)


def _groups_to_abilities(
    groups: tuple[str, ...]
) -> dict[str, list[int | str]]:
    return {
        ability: [
            int(groups[index]),
            groups[index + 1].replace("\N{MINUS SIGN}", "-"),
            groups[index + 2].replace("\N{MINUS SIGN}", "-"),
        ]
        for ability, index in zip(ABILITY_KEYS, range(0, 18, 3), strict=True)
    }


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_stat_table(abilities: dict[str, list[int | str]]) -> str:
    score_cells = []
    save_cells = []
    for ability in ABILITY_KEYS:
        score, modifier, save = abilities[ability]
        score_cells.append(f"{score} ({modifier})")
        save_cells.append(f"Save: {save}")
    return "\n".join(
        (
            "| STR | DEX | CON | INT | WIS | CHA |",
            "| :---: | :---: | :---: | :---: | :---: | :---: |",
            "| " + " | ".join(score_cells) + " |",
            "| " + " | ".join(save_cells) + " |",
        )
    )


def parse_markdown_stat_blocks(
    markdown: str,
) -> dict[str, dict[str, list[int | str]]]:
    parsed: dict[str, dict[str, list[int | str]]] = {}
    for match in MARKDOWN_STAT_TABLE_RE.finditer(markdown):
        headings = list(re.finditer(r"(?m)^# (.+)$", markdown[: match.start()]))
        if not headings:
            raise ValueError("Ability table has no owning Markdown heading")
        name = headings[-1].group(1)
        if name in parsed:
            raise ValueError(f"Duplicate Markdown ability table owner: {name}")
        groups = match.groups()
        ordered = (
            groups[0], groups[1], groups[12],
            groups[2], groups[3], groups[13],
            groups[4], groups[5], groups[14],
            groups[6], groups[7], groups[15],
            groups[8], groups[9], groups[16],
            groups[10], groups[11], groups[17],
        )
        parsed[name] = _groups_to_abilities(ordered)
    return parsed


def apply_registered_stat_blocks(
    markdown: str, registry: dict[str, Any] | None = None
) -> str:
    registry = registry or load_registry()
    expected = registry["statBlocks"]
    matches = list(MARKDOWN_STAT_TABLE_RE.finditer(markdown))
    replacements: list[tuple[int, int, str]] = []
    owners: list[str] = []
    for match in matches:
        headings = list(re.finditer(r"(?m)^# (.+)$", markdown[: match.start()]))
        if not headings:
            raise RuntimeError("Ability table has no owning Markdown heading")
        owner = headings[-1].group(1)
        owners.append(owner)
        if owner not in expected:
            raise RuntimeError(f"Unregistered ability table owner: {owner}")
        replacements.append(
            (match.start(), match.end(), format_stat_table(expected[owner]))
        )

    if len(owners) != len(set(owners)):
        duplicates = sorted(name for name in set(owners) if owners.count(name) > 1)
        raise RuntimeError(f"Duplicate ability table owners: {duplicates}")
    missing = sorted(set(expected) - set(owners))
    extra = sorted(set(owners) - set(expected))
    if missing or extra:
        raise RuntimeError(
            f"Ability-table registry drift: missing={missing}, extra={extra}"
        )
    for start, end, replacement in reversed(replacements):
        markdown = markdown[:start] + replacement + markdown[end:]
    return markdown


def parse_pdf_stat_blocks(raw_text: str) -> dict[str, dict[str, list[int | str]]]:
    lines = raw_text.splitlines(keepends=True)
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line)

    parsed: dict[str, dict[str, list[int | str]]] = {}
    for match in PDF_STAT_TABLE_RE.finditer(raw_text):
        line_index = bisect.bisect_right(starts, match.start()) - 1
        type_index = None
        for index in range(line_index - 1, max(-1, line_index - 18), -1):
            if re.match(
                r"^(?:Tiny|Small|Medium|Large|Huge|Gargantuan)"
                r"(?: or Smaller)?\b",
                lines[index].strip(),
            ):
                type_index = index
                break
        if type_index is None:
            raise ValueError(f"PDF ability table near line {line_index + 1} has no type")

        name = None
        for index in range(type_index - 1, max(-1, type_index - 8), -1):
            candidate = lines[index].strip()
            if (
                candidate
                and candidate != "System Reference Document 5.2.1"
                and not candidate.isdigit()
            ):
                name = candidate.replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
                break
        if name is None:
            raise ValueError(f"PDF ability table near line {line_index + 1} has no name")
        if name in parsed:
            raise ValueError(f"Duplicate PDF ability table owner: {name}")
        parsed[name] = _groups_to_abilities(match.groups())
    return parsed


def verify_pdf(pdf_path: Path) -> None:
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if digest != OFFICIAL_PDF_SHA256:
        raise ValueError(
            f"Official PDF digest mismatch: expected {OFFICIAL_PDF_SHA256}, got {digest}"
        )
    info = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    page_match = re.search(r"(?m)^Pages:\s+(\d+)$", info)
    if not page_match or int(page_match.group(1)) != OFFICIAL_PDF_PAGES:
        raise ValueError(f"Official PDF page-count mismatch: {page_match}")


def extract_raw_pdf_text(pdf_path: Path) -> tuple[str, str]:
    version = subprocess.run(
        ["pdftotext", "-v"],
        check=True,
        capture_output=True,
        text=True,
    ).stderr.splitlines()[0]
    with tempfile.TemporaryDirectory(prefix="graph20-pdf-parity-") as temp_dir:
        output = Path(temp_dir) / "srd.txt"
        subprocess.run(
            [
                "pdftotext", "-raw", "-enc", "UTF-8",
                str(pdf_path), str(output),
            ],
            check=True,
        )
        return output.read_text(encoding="utf-8"), version


def _semantic_tokens(text: str) -> list[str]:
    return re.findall(
        r"[a-z]+|\d+", unicodedata.normalize("NFKC", text).lower()
    )


def _ngram_hits(reference: list[str], candidate: list[str], size: int) -> int:
    reference_ngrams = {
        tuple(reference[index : index + size])
        for index in range(len(reference) - size + 1)
    }
    hit = bytearray(len(candidate))
    for index in range(len(candidate) - size + 1):
        if tuple(candidate[index : index + size]) in reference_ngrams:
            hit[index : index + size] = b"\1" * size
    return sum(hit)


def semantic_metrics(markdown: str, raw_pdf_text: str) -> dict[str, int]:
    if "# Playing the Game" not in markdown:
        raise ValueError("Markdown content boundary not found")
    markdown = markdown[markdown.index("# Playing the Game") :]
    markdown = MARKDOWN_STAT_TABLE_RE.sub(" ", markdown)
    markdown = html.unescape(markdown)
    markdown = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", markdown)
    markdown = re.sub(
        r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$", " ", markdown
    )
    markdown = re.sub(r"(?m)^\s*#{1,6}\s*", "", markdown)
    markdown = re.sub(r"(?m)^\s*[-*+]\s+", "", markdown)

    pages = raw_pdf_text.split("\f")
    if len(pages) < OFFICIAL_PDF_PAGES:
        raise ValueError(f"Expected {OFFICIAL_PDF_PAGES} extracted PDF pages")
    pdf = "\f".join(pages[4:])
    pdf = re.sub(
        r"([A-Za-z])[-\N{SOFT HYPHEN}][ \t]*\n[ \t]*([a-z])",
        r"\1\2",
        pdf,
    )
    pdf = PDF_STAT_TABLE_RE.sub(" ", pdf)
    pdf = re.sub(r"(?m)^(?:MOD SAVE\s*)+$", " ", pdf)
    pdf = re.sub(
        r"(?mi)^\s*(?:\d+\s+)?System Reference Document 5\.2\.1\s*$", " ", pdf
    )
    pdf = re.sub(r"(?m)^\s*\d+\s*$", " ", pdf)

    markdown_tokens = _semantic_tokens(markdown)
    pdf_tokens = _semantic_tokens(pdf)
    markdown_counter = Counter(markdown_tokens)
    pdf_counter = Counter(pdf_tokens)
    counter_hits = sum((markdown_counter & pdf_counter).values())
    ngram_size = 5
    return {
        "ngramSize": ngram_size,
        "markdownTokens": len(markdown_tokens),
        "pdfTokens": len(pdf_tokens),
        "counterHits": counter_hits,
        "pdfNgramTokenHits": _ngram_hits(markdown_tokens, pdf_tokens, ngram_size),
        "markdownNgramTokenHits": _ngram_hits(pdf_tokens, markdown_tokens, ngram_size),
    }


def build_registry(
    markdown: str, raw_pdf_text: str, extractor_version: str
) -> dict[str, Any]:
    return {
        "officialPdf": {
            "url": OFFICIAL_PDF_URL,
            "sha256": f"sha256-{OFFICIAL_PDF_SHA256}",
            "pages": OFFICIAL_PDF_PAGES,
            "textExtraction": f"{extractor_version}; -raw -enc UTF-8",
        },
        "semanticMetrics": semantic_metrics(markdown, raw_pdf_text),
        "statBlocks": dict(sorted(parse_pdf_stat_blocks(raw_pdf_text).items())),
    }
