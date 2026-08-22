"""Deterministic extractor: SRD_CC_v5.2.1.md -> objects/ JSON-LD records.

The SRD markdown (a PDF conversion) uses a single flat `#` heading level.
Chapters are located by an ordered title list (srdlib.CHAPTERS); entity
boundaries inside catalog chapters are detected from body grammar (spell
header lines, magic-item rarity lines, monster size/type lines, feat
category lines), never from heading depth.

Prose fidelity: `rulesText` always carries the verbatim source block (minus
raw HTML table lines, which are preserved structurally as Table records and
linked through `relatedTables`). Structured fields are indexes, not
replacements. Source OCR artifacts (e.g. `Id6` for `1d6`) are preserved
verbatim; known anomalies are documented in SPECIFICATION.md.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from srdlib import (
    BASE,
    CHAPTERS,
    COLLECTIONS,
    CONTEXT_IRI,
    SOURCE_FILE,
    SOURCE_ID,
    dump_json,
    sha256_of,
    slugify,
)

HEADING_RE = re.compile(r"^# (.+?)\s*$")
TABLE_RE = re.compile(r"<table>.*?</table>", re.S)
CELL_RE = re.compile(r"<td(?:\s+colspan=\"(\d+)\")?>(.*?)</td>", re.S)
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)

SPELL_LEVEL_RE = re.compile(r"^Level (\d+) ([A-Za-z]+) \(([^)]+)\)")
CANTRIP_RE = re.compile(r"^([A-Za-z]+) Cantrip \(([^)]+)\)")
FEAT_RE = re.compile(
    r"^(Origin|General|Fighting Style|Epic Boon) Feat(?:\s*\(Prerequisite:\s*(.+?)\))?\s*$"
)
RARITIES = "Common|Uncommon|Rare|Very Rare|Legendary|Artifact|Rarity Varies|Varies"
ITEM_RE = re.compile(
    r"^(Armor|Potion|Ring|Rod|Scroll|Staff|Wand|Weapon|Wondrous Item)"
    r"(?:\s*\(([^)]*)\))?,\s*(" + RARITIES + r")(?:\s*\((Requires Attunement[^)]*)\))?"
)
MONSTER_RE = re.compile(r"^(Tiny|Small|Medium|Large|Huge|Gargantuan)\b[^.]*,")
MONSTER_FOLD_TITLES = {
    "Traits",
    "Actions",
    "Bonus Actions",
    "Reactions",
    "Legendary Actions",
    "Lair Actions",
    "Regional Effects",
    "Gear",
}
# The PDF conversion sometimes promotes a stat-block line to a heading
# (e.g. `# Vulnerabilities Fire`). Fold those back into the stat block.
STAT_LABEL_HEADING_RE = re.compile(
    r"^(Vulnerabilities|Resistances|Immunities|Senses|Languages|Gear|Skills|Speed|Initiative)\b"
)
DICE_RE = re.compile(r"^(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?$")
ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


class Block:
    __slots__ = ("title", "line_start", "line_end", "body_lines", "chapter")

    def __init__(self, title, line_start, line_end, body_lines, chapter):
        self.title = title
        self.line_start = line_start  # 1-based heading line
        self.line_end = line_end  # 1-based inclusive
        self.body_lines = body_lines  # list[str] after the heading
        self.chapter = chapter

    @property
    def body(self) -> str:
        return "\n".join(self.body_lines).strip("\n")

    def first_body_line(self) -> str:
        for line in self.body_lines:
            if line.strip():
                return line.strip()
        return ""


def parse_dice(expression: str):
    match = DICE_RE.match(expression.strip())
    if not match:
        return None
    count, sides, sign, mod = match.groups()
    parsed = {"expression": expression.strip(), "count": int(count), "sides": int(sides)}
    if sign:
        parsed["modifier"] = int(mod) if sign == "+" else -int(mod)
    return parsed


def parse_blocks(lines):
    """Slice the SRD into heading blocks and assign chapters."""
    chapter_starts = []
    cursor = 0
    for title in CHAPTERS:
        found = None
        for idx in range(cursor, len(lines)):
            if lines[idx].rstrip() == f"# {title}":
                found = idx
                break
        if found is None:
            raise SystemExit(f"chapter not found: {title}")
        chapter_starts.append(found)
        cursor = found + 1
    content_start = chapter_starts[0]

    def chapter_of(line_idx):
        current = None
        for chapter, start in zip(CHAPTERS, chapter_starts):
            if line_idx >= start:
                current = chapter
        return current

    blocks = []
    heads = [
        idx
        for idx in range(content_start, len(lines))
        if HEADING_RE.match(lines[idx])
    ]
    for pos, idx in enumerate(heads):
        end = heads[pos + 1] - 1 if pos + 1 < len(heads) else len(lines) - 1
        while end > idx and not lines[end].strip():
            end -= 1
        blocks.append(
            Block(
                HEADING_RE.match(lines[idx]).group(1),
                idx + 1,
                end + 1,
                lines[idx + 1 : end + 1],
                chapter_of(idx),
            )
        )
    return blocks, content_start + 1


class Emitter:
    def __init__(self, root: Path):
        self.root = root
        self.records = {name: [] for name in COLLECTIONS}
        self.used_slugs = {name: set() for name in COLLECTIONS}
        self.section_counters = {}

    def unique_slug(self, collection: str, base: str) -> str:
        slug = base
        counter = 2
        while slug in self.used_slugs[collection]:
            slug = f"{base}-{counter}"
            counter += 1
        self.used_slugs[collection].add(slug)
        return slug

    def locator(self, block: Block, line_end=None):
        chapter_index = CHAPTERS.index(block.chapter) + 1
        key = block.chapter
        self.section_counters.setdefault(key, 0)
        self.section_counters[key] += 1
        return {
            "chapter": block.chapter,
            "section": f"{chapter_index}.{self.section_counters[key]}",
            "heading": block.title,
            "lineStart": block.line_start,
            "lineEnd": line_end if line_end is not None else block.line_end,
        }

    def new_record(self, collection, type_name, name, slug_base, locator):
        slug = self.unique_slug(collection, slug_base)
        record = {
            "@context": CONTEXT_IRI,
            "@id": f"{BASE}objects/{collection}/{slug}",
            "@type": type_name,
            "name": name,
            "slug": slug,
            "source": {"@id": SOURCE_ID},
            "sourceLocator": locator,
        }
        self.records[collection].append(record)
        return record

    # -- tables ------------------------------------------------------------

    def extract_tables(self, block: Block, locator):
        """Emit Table records for HTML tables in a block body.

        Returns (prose_without_table_markup, [table @ids]).
        """
        table_ids = []
        prose_lines = []
        pending_caption = None
        table_index = 0
        for offset, raw in enumerate(block.body_lines):
            line = raw.strip()
            if line.startswith("<table>"):
                table_index += 1
                caption = pending_caption
                name = caption or f"{block.title} Table {table_index}"
                table = self.new_record(
                    "tables",
                    "Table",
                    name,
                    f"{locator['section'].replace('.', '-')}-{slugify(name)}",
                    dict(
                        locator,
                        lineStart=block.line_start + offset + 1,
                        lineEnd=block.line_start + offset + 1,
                    ),
                )
                columns, rows = parse_html_table(line)
                table["columns"] = columns
                table["rows"] = rows
                table_ids.append(table["@id"])
            else:
                if line and not line.startswith("<table>"):
                    stripped = line
                    pending_caption = (
                        stripped
                        if len(stripped) < 80 and not stripped.endswith(".")
                        else None
                    )
                prose_lines.append(raw)
        prose = "\n".join(prose_lines).strip("\n")
        prose = re.sub(r"\n{3,}", "\n\n", prose)
        return prose.strip(), table_ids

    # -- generic prose sections --------------------------------------------

    def emit_rule(self, block: Block):
        locator = self.locator(block)
        prose, table_ids = self.extract_tables(block, locator)
        slug_base = f"{locator['section'].replace('.', '-')}-{slugify(block.title)}"
        record = self.new_record("rules", "Rule", block.title, slug_base, locator)
        record["section"] = locator["section"]
        if prose:
            record["rulesText"] = prose
        if table_ids:
            record["relatedTables"] = [{"@id": tid} for tid in table_ids]
        return record

    # -- spells -------------------------------------------------------------

    def emit_spell(self, block: Block, extra_blocks):
        line_end = extra_blocks[-1].line_end if extra_blocks else block.line_end
        locator = self.locator(block, line_end=line_end)
        record = self.new_record(
            "spells", "Spell", block.title, slugify(block.title), locator
        )
        header = block.first_body_line()
        match = SPELL_LEVEL_RE.match(header)
        if match:
            record["level"] = int(match.group(1))
            record["school"] = match.group(2)
            class_list = match.group(3)
        else:
            match = CANTRIP_RE.match(header)
            record["level"] = 0
            record["school"] = match.group(1)
            class_list = match.group(2)
        record["classAvailability"] = [c.strip() for c in class_list.split(",")]
        text_parts = [block.body]
        for extra in extra_blocks:
            text_parts.append(f"{extra.title}\n\n{extra.body}".strip())
        text = "\n\n".join(part for part in text_parts if part)
        for label, field in (
            ("Casting Time", "castingTime"),
            ("Range", "range"),
            ("Components", "components"),
            ("Duration", "duration"),
        ):
            found = re.search(rf"^{label}: (.+)$", text, re.M)
            if found:
                record[field] = found.group(1).strip()
        record["rulesText"] = text
        return record

    # -- feats ---------------------------------------------------------------

    def emit_feat(self, block: Block):
        locator = self.locator(block)
        record = self.new_record(
            "feats", "Feat", block.title, slugify(block.title), locator
        )
        match = FEAT_RE.match(block.first_body_line())
        record["category"] = match.group(1)
        if match.group(2):
            record["prerequisite"] = match.group(2)
        record["repeatable"] = "Repeatable." in block.body
        record["rulesText"] = block.body
        return record

    # -- magic items ----------------------------------------------------------

    def emit_magic_item(self, block: Block, extra_blocks):
        line_end = extra_blocks[-1].line_end if extra_blocks else block.line_end
        locator = self.locator(block, line_end=line_end)
        record = self.new_record(
            "magic-items", "MagicItem", block.title, slugify(block.title), locator
        )
        match = ITEM_RE.match(block.first_body_line())
        record["itemCategory"] = match.group(1)
        if match.group(2):
            record["categoryDetail"] = match.group(2)
        record["rarity"] = match.group(3)
        record["requiresAttunement"] = bool(match.group(4))
        if match.group(4):
            record["attunementNote"] = match.group(4)
        text_parts = [block.body]
        for extra in extra_blocks:
            text_parts.append(f"{extra.title}\n\n{extra.body}".strip())
        # tables inside item bodies are rare; preserve them structurally
        combined = "\n\n".join(part for part in text_parts if part)
        if "<table>" in combined:
            synthetic = Block(
                block.title, block.line_start, line_end, combined.split("\n"), block.chapter
            )
            combined, table_ids = self.extract_tables(synthetic, locator)
            if table_ids:
                record["relatedTables"] = [{"@id": tid} for tid in table_ids]
        record["rulesText"] = combined
        return record

    # -- monsters ---------------------------------------------------------------

    def emit_monster(self, block: Block, extra_blocks, name_block):
        line_start_block = name_block or block
        line_end = extra_blocks[-1].line_end if extra_blocks else block.line_end
        locator = self.locator(line_start_block, line_end=line_end)
        locator["heading"] = block.title
        record = self.new_record(
            "monsters", "Monster", block.title, slugify(block.title), locator
        )
        header = block.first_body_line()
        record["sizeTypeAlignment"] = header
        parts = header.split(",", 1)
        record["sizeAndType"] = parts[0].strip()
        if len(parts) > 1:
            record["alignment"] = parts[1].strip()

        stat_extras = [
            extra
            for extra in extra_blocks
            if extra.title not in MONSTER_FOLD_TITLES
            and STAT_LABEL_HEADING_RE.match(extra.title)
        ]
        section_extras = [
            extra for extra in extra_blocks if extra not in stat_extras
        ]
        stat_text = "\n".join(
            [block.body] + [f"{e.title}\n{e.body}".strip() for e in stat_extras]
        )
        for label, field in (
            ("AC", "armorClass"),
            ("Initiative", "initiative"),
            ("HP", "hitPoints"),
            ("Speed", "speed"),
            ("Skills", "skills"),
            ("Resistances", "resistances"),
            ("Vulnerabilities", "vulnerabilities"),
            ("Immunities", "immunities"),
            ("Senses", "senses"),
            ("Languages", "languages"),
            ("Gear", "gear"),
            ("CR", "challenge"),
        ):
            found = re.search(rf"^{label} (.+)$", stat_text, re.M)
            if found:
                record[field] = found.group(1).strip()
        if "challenge" not in record:
            # Line-join artifact: CR can follow Languages on the same line.
            found = re.search(r"\bCR ((?:[\d/]+|None) \(.+)$", stat_text, re.M)
            if found:
                record["challenge"] = found.group(1).strip()
        if "armorClass" in record:
            digits = re.match(r"^(\d+)", record["armorClass"])
            if digits:
                record["armorClassValue"] = int(digits.group(1))
        if "hitPoints" in record:
            hp = re.match(r"^(\d+)(?:\s*\(([^)]+)\))?", record["hitPoints"])
            if hp:
                record["hitPointsValue"] = int(hp.group(1))
                if hp.group(2):
                    roll = parse_dice(hp.group(2).replace(" ", ""))
                    if roll:
                        record["hitPointsRoll"] = roll
        if "challenge" in record:
            cr = re.match(
                r"^([\d/]+)\s*\((?:XP ([\d,]+)|([\d,]+) XP)(?:,? or [^;]+)?;\s*PB \+(\d+)\)",
                record["challenge"],
            )
            if cr:
                xp = cr.group(2) or cr.group(3)
                record["challengeRating"] = cr.group(1)
                record["experiencePoints"] = int(xp.replace(",", ""))
                record["proficiencyBonus"] = int(cr.group(4))
        abilities = parse_ability_table(stat_text)
        if abilities:
            record["abilities"] = abilities

        sections = [
            {"name": extra.title, "rulesText": extra.body} for extra in section_extras
        ]
        if sections:
            record["statSections"] = sections
        text_parts = [re.sub(r"^<table>.*</table>$", "", stat_text, flags=re.M).strip()]
        for extra in section_extras:
            text_parts.append(f"{extra.title}\n\n{extra.body}".strip())
        record["rulesText"] = re.sub(
            r"\n{3,}", "\n\n", "\n\n".join(p for p in text_parts if p)
        )
        return record


def parse_html_table(html: str):
    rows_raw = ROW_RE.findall(html)
    parsed_rows = []
    for row in rows_raw:
        cells = []
        for colspan, value in CELL_RE.findall(row):
            cell = {"value": re.sub(r"\s+", " ", value).strip()}
            if colspan:
                cell["colspan"] = int(colspan)
            cells.append(cell)
        parsed_rows.append(cells)
    if not parsed_rows:
        return [], []
    columns = [cell["value"] for cell in parsed_rows[0]]
    rows = [
        {"position": index, "cells": cells}
        for index, cells in enumerate(parsed_rows[1:], start=1)
    ]
    return columns, rows


def normalize_ability_cell(token: str) -> str:
    """Apply the accepted `ability-table-roman-numeral-ocr` override.

    See objects/sources/extraction-overrides.json. Only typed ability
    parsing uses this; verbatim table text is never altered.
    """
    return re.sub(
        r"^([+-]?)(II|I)$",
        lambda m: m.group(1) + ("11" if m.group(2) == "II" else "1"),
        token,
    )


def parse_ability_table(stat_text: str):
    match = TABLE_RE.search(stat_text)
    if not match:
        return None
    # Accepted override `ability-table-latex-labels`: the PDF conversion
    # renders some ability labels as LaTeX (e.g. `$\mathbf{S_{TR}}$`).
    cleaned = re.sub(
        r"\$\\mathbf\{([A-Z])_\{([A-Z]+)\}\}\$",
        lambda m: m.group(1) + m.group(2),
        match.group(0),
    )
    cleaned = re.sub(r"\$\\mathbf\{([A-Z]{3})\}\$", r"\1", cleaned)
    # Glued score tokens, e.g. `CON25` (accepted OCR override).
    cleaned = re.sub(
        r">(STR|DEX|CON|INT|WIS|CHA)\s*(\d+)<",
        lambda m: ">" + m.group(1).upper() + " " + m.group(2) + "<",
        cleaned,
        flags=re.I,
    )
    cells = [
        " ".join(
            normalize_ability_cell(token)
            for token in re.sub(r"\s+", " ", value).strip().split(" ")
        )
        for _, value in CELL_RE.findall(cleaned)
    ]
    abilities = {}
    index = 0
    while index < len(cells):
        token = cells[index]
        parts = token.split()
        if parts and parts[0] in ABILITIES:
            ability = parts[0]
            # Ability scores are unsigned; a signed token is a modifier from
            # a truncated row and must not be misread as the score.
            if len(parts) > 1 and parts[1].isdigit():
                score = int(parts[1])
                cursor = index + 1
            elif index + 1 < len(cells) and cells[index + 1].isdigit():
                score = int(cells[index + 1])
                cursor = index + 2
            else:
                index += 1
                continue
            numbers = []
            while cursor < len(cells) and len(numbers) < 2:
                value = cells[cursor].replace("−", "-")
                if re.fullmatch(r"[+-]?\d+", value):
                    numbers.append(int(value))
                    cursor += 1
                else:
                    break
            entry = {"score": score}
            if len(numbers) >= 1:
                entry["modifier"] = numbers[0]
            if len(numbers) >= 2:
                entry["savingThrow"] = numbers[1]
            abilities[ability.lower()] = entry
            index = cursor
        else:
            index += 1
    return abilities or None


def run_extraction(root: Path):
    source_path = root / SOURCE_FILE
    lines = source_path.read_text(encoding="utf-8").splitlines()
    blocks, content_first_line = parse_blocks(lines)
    emitter = Emitter(root)

    # Source record: license and required CC-BY-4.0 attribution statement.
    from srdlib import ATTRIBUTION_STATEMENT

    source_record = {
        "@context": CONTEXT_IRI,
        "@id": SOURCE_ID,
        "@type": "Source",
        "name": "System Reference Document 5.2.1",
        "slug": "srd-5-2-1",
        "author": "Wizards of the Coast LLC",
        "srdVersion": "5.2.1",
        "license": "CC-BY-4.0",
        "licenseUrl": "https://creativecommons.org/licenses/by/4.0/legalcode",
        "attributionStatement": ATTRIBUTION_STATEMENT,
        "canonicalUrl": "https://www.dndbeyond.com/srd",
        "sourceFile": SOURCE_FILE,
        "contentDigest": sha256_of(source_path),
    }
    emitter.records["sources"].append(source_record)

    index = 0
    while index < len(blocks):
        block = blocks[index]
        chapter = block.chapter
        first = block.first_body_line()

        if chapter == "Spells" and (SPELL_LEVEL_RE.match(first) or CANTRIP_RE.match(first)):
            extras = []
            index += 1
            while index < len(blocks):
                nxt = blocks[index]
                nfirst = nxt.first_body_line()
                if (
                    nxt.chapter != chapter
                    or SPELL_LEVEL_RE.match(nfirst)
                    or CANTRIP_RE.match(nfirst)
                ):
                    break
                extras.append(nxt)
                index += 1
            emitter.emit_spell(block, extras)
            continue

        if chapter == "Feats" and FEAT_RE.match(first):
            emitter.emit_feat(block)
            index += 1
            continue

        if chapter == "Magic Items" and ITEM_RE.match(first):
            extras = []
            index += 1
            while index < len(blocks):
                nxt = blocks[index]
                if nxt.chapter != chapter or ITEM_RE.match(nxt.first_body_line()):
                    break
                if MONSTER_RE.match(nxt.first_body_line()):
                    break
                extras.append(nxt)
                index += 1
            emitter.emit_magic_item(block, extras)
            continue

        if chapter in ("Monsters A-Z", "Animals", "Magic Items") and MONSTER_RE.match(first):
            # The stat block is normally preceded by a duplicate name heading
            # with an empty body; merge it for provenance.
            name_block = None
            prev = blocks[index - 1] if index > 0 else None
            if prev is not None and prev.title == block.title and not prev.body.strip():
                name_block = prev
            extras = []
            index += 1
            while index < len(blocks):
                nxt = blocks[index]
                if nxt.chapter != chapter:
                    break
                if nxt.title in MONSTER_FOLD_TITLES or STAT_LABEL_HEADING_RE.match(
                    nxt.title
                ):
                    extras.append(nxt)
                    index += 1
                    continue
                break
            emitter.emit_monster(block, extras, name_block)
            continue

        # Duplicate empty name heading directly before a stat block: skip it,
        # the monster emitter claims it via name_block.
        nxt = blocks[index + 1] if index + 1 < len(blocks) else None
        if (
            nxt is not None
            and nxt.title == block.title
            and not block.body.strip()
            and MONSTER_RE.match(nxt.first_body_line())
        ):
            index += 1
            continue

        emitter.emit_rule(block)
        index += 1

    # Reset output directories and write records.
    objects_dir = root / "objects"
    for collection in COLLECTIONS:
        directory = objects_dir / collection
        if collection == "sources":
            # objects/sources/ also holds the hand-authored
            # extraction-overrides.json; only clear generated files.
            directory.mkdir(parents=True, exist_ok=True)
            for stale in directory.glob("*.jsonld"):
                stale.unlink()
        else:
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True)
    counts = {}
    for collection in COLLECTIONS:
        for record in emitter.records[collection]:
            dump_json(objects_dir / collection / f"{record['slug']}.jsonld", record)
        counts[collection] = len(emitter.records[collection])

    coverage = {
        "sourceFile": SOURCE_FILE,
        "contentDigest": source_record["contentDigest"],
        "contentFirstLine": content_first_line,
        "excludedPreamble": {
            "lineStart": 1,
            "lineEnd": content_first_line - 1,
            "reason": "Legal Information and Contents navigation preamble; "
            "license and attribution preserved in the source record.",
        },
        "blockCount": len(blocks),
        "recordCounts": counts,
    }
    dump_json(objects_dir / "sources" / "source-coverage.json", coverage)
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    counts = run_extraction(Path(args.root).resolve())
    for collection in COLLECTIONS:
        print(f"{collection}: {counts[collection]}")


if __name__ == "__main__":
    main()
