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
import html
import re
import shutil
from pathlib import Path

from srdlib import (
    BASE,
    CHAPTERS,
    CLASS_NAMES,
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
RARITY_VALUES = (
    "Rarity Varies",
    "Very Rare",
    "Legendary",
    "Uncommon",
    "Artifact",
    "Common",
    "Varies",
    "Rare",
)
RARITIES = "|".join(RARITY_VALUES)
ITEM_START_RE = re.compile(
    r"^(Armor|Potion|Ring|Rod|Scroll|Staff|Wand|Weapon|Wondrous Item)"
    r"(?:\s*\(([^)]*)\))?,\s*(.+)$"
)
RARITY_RE = re.compile(rf"\b({RARITIES})\b(?:\s*\(([^)]*)\))?")
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
GLOSSARY_FAMILIES = {
    "Action": ("actions", "Action"),
    "Area of Effect": ("areas-of-effect", "AreaOfEffect"),
    "Attitude": ("attitudes", "Attitude"),
    "Hazard": ("hazards", "Hazard"),
}
DAMAGE_TYPES = (
    "Acid", "Bludgeoning", "Cold", "Fire", "Force", "Lightning",
    "Necrotic", "Piercing", "Poison", "Psychic", "Radiant", "Slashing",
    "Thunder",
)
NPC_MONSTERS = {
    "Guard", "Guard Captain", "Mage", "Archmage", "Priest Acolyte",
    "Priest", "Warrior Infantry", "Warrior Veteran",
}
ENVIRONMENT_RULES = {
    "Extreme Cold", "Extreme Heat", "Frigid Water", "Heavy Precipitation",
    "High Altitude", "Strong Wind", "Desecrated Ground", "Brown Mold",
    "Green Slime", "Webs",
}


def parse_magic_item_header(header: str):
    """Parse every rarity variant and attunement clause in an item header."""
    match = ITEM_START_RE.match(header)
    if not match:
        return None
    rarities = []
    for rarity, detail in RARITY_RE.findall(match.group(3)):
        if detail.startswith("Requires Attunement"):
            detail = ""
        entry = {"rarity": rarity}
        if detail:
            entry["variant"] = detail
        if entry not in rarities:
            rarities.append(entry)
    if not rarities:
        return None
    attunement = re.search(r"\((Requires Attunement[^)]*)\)", match.group(3))
    return {
        "itemCategory": match.group(1),
        "categoryDetail": match.group(2),
        "rarities": rarities,
        "attunementNote": attunement.group(1) if attunement else None,
    }


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


def parse_named_effects(text: str):
    """Index source-labelled effect paragraphs without replacing prose."""
    effects = []
    for paragraph in re.split(r"\n\s*\n", text):
        match = re.match(r"^([A-Z][^.\n]{1,80})\.\s+(.+)$", paragraph.strip(), re.S)
        if match:
            effects.append({"name": match.group(1), "rulesText": match.group(2).strip()})
    return effects


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
        name = html.unescape(name)
        slug = self.unique_slug(collection, slug_base)
        record = {
            "@context": CONTEXT_IRI,
            "@id": f"{BASE}objects/{collection}/{slug}",
            "@type": type_name,
            "name": name,
            "slug": slug,
            "source": {"@id": SOURCE_ID},
            "sourceLocator": locator,
            "htmlPage": {"@id": f"{BASE}records/{collection}/{slug}/"},
        }
        self.records[collection].append(record)
        return record

    # -- tables ------------------------------------------------------------

    def extract_tables(self, block: Block, locator):
        """Emit Table records for Markdown and HTML tables in a block body.

        Returns (prose_without_table_markup, [table @ids]).
        """
        table_ids = []
        prose_lines = []
        pending_caption = None
        table_index = 0
        idx = 0
        lines = block.body_lines
        while idx < len(lines):
            raw = lines[idx]
            line = raw.strip()
            if line.startswith("|") and line.endswith("|"):
                tbl_lines = [line]
                start_offset = idx
                idx += 1
                while idx < len(lines) and lines[idx].strip().startswith("|") and lines[idx].strip().endswith("|"):
                    tbl_lines.append(lines[idx].strip())
                    idx += 1
                table_index += 1
                caption = pending_caption
                if caption:
                    tail = len(prose_lines) - 1
                    while tail >= 0 and not prose_lines[tail].strip():
                        tail -= 1
                    if tail >= 0 and prose_lines[tail].strip() == caption:
                        prose_lines = prose_lines[:tail]
                pending_caption = None
                name = caption or {
                    ("Robe of Useful Items", 1): "Robe of Useful Items Patches",
                    ("Sphere of Annihilation", 1): "Sphere Interactions",
                }.get((block.title, table_index)) or (
                    block.title
                    if table_index == 1 and not any(item.strip() for item in prose_lines)
                    else f"{block.title} Table {table_index}"
                )
                table = self.new_record(
                    "tables",
                    "Table",
                    name,
                    f"{locator['section'].replace('.', '-')}-{slugify(name)}",
                    dict(
                        locator,
                        caption=name,
                        lineStart=block.line_start + start_offset + 1,
                        lineEnd=block.line_start + idx,
                    ),
                )
                columns, rows = parse_markdown_table(tbl_lines)
                table["columns"] = columns
                table["rows"] = rows
                table["rawText"] = "\n".join(tbl_lines)
                table_ids.append(table["@id"])
            elif line.startswith("<table>"):
                table_index += 1
                caption = pending_caption
                if caption:
                    tail = len(prose_lines) - 1
                    while tail >= 0 and not prose_lines[tail].strip():
                        tail -= 1
                    if tail >= 0 and prose_lines[tail].strip() == caption:
                        prose_lines = prose_lines[:tail]
                pending_caption = None
                name = caption or (
                    block.title
                    if table_index == 1 and not any(item.strip() for item in prose_lines)
                    else f"{block.title} Table {table_index}"
                )
                table = self.new_record(
                    "tables",
                    "Table",
                    name,
                    f"{locator['section'].replace('.', '-')}-{slugify(name)}",
                    dict(
                        locator,
                        caption=name,
                        lineStart=block.line_start + idx + 1,
                        lineEnd=block.line_start + idx + 1,
                    ),
                )
                columns, rows = parse_html_table(line)
                table["columns"] = columns
                table["rows"] = rows
                table["rawText"] = line
                table_ids.append(table["@id"])
                idx += 1
            else:
                if line and not line.startswith("<table>") and not (line.startswith("|") and line.endswith("|")):
                    stripped = line
                    pending_caption = (
                        stripped
                        if len(stripped) < 80 and not stripped.endswith(".")
                        else None
                    )
                prose_lines.append(raw)
                idx += 1
        # Horizontal rules delimit chapters/catalogs in the normalized
        # Markdown; they are document structure, not SRD prose owned by the
        # preceding entity.
        while prose_lines and (not prose_lines[-1].strip() or prose_lines[-1].strip() == "---"):
            prose_lines.pop()
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
        elif not table_ids:
            record["rulesText"] = block.title
            record["headingOnly"] = True
        if table_ids:
            record["relatedTables"] = [{"@id": tid} for tid in table_ids]
        if block.chapter == "Gameplay Toolbox":
            marker = block.first_body_line()
            lowered = f"{block.title}\n{block.body}".lower()
            if marker == "Trap" or " trap" in lowered and "traps" not in lowered:
                record["ruleCategory"] = "Trap"
            elif marker == "Poison" or "poison" in block.title.lower():
                record["ruleCategory"] = "Poison"
            elif marker == "Magical Contagion":
                record["ruleCategory"] = "Disease"
            elif "curse" in lowered:
                record["ruleCategory"] = "Curse"
            elif block.title in ("Fear", "Mental Stress") or "fear" in block.title.lower():
                record["ruleCategory"] = "MentalEffect"
            elif block.title in ENVIRONMENT_RULES:
                record["ruleCategory"] = "EnvironmentalEffect"
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
        text_parts = []
        table_ids = []
        for part_index, part in enumerate([block, *extra_blocks]):
            part_locator = dict(
                locator,
                heading=part.title,
                lineStart=part.line_start,
                lineEnd=part.line_end,
            )
            prose, part_table_ids = self.extract_tables(part, part_locator)
            table_ids.extend(part_table_ids)
            if part_index == 0:
                text_parts.append(prose)
            else:
                text_parts.append(f"{part.title}\n\n{prose}".strip())
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
        if table_ids:
            record["relatedTables"] = [{"@id": table_id} for table_id in table_ids]
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
        parsed = parse_magic_item_header(block.first_body_line())
        record["itemCategory"] = parsed["itemCategory"]
        if parsed["categoryDetail"]:
            record["categoryDetail"] = parsed["categoryDetail"]
        if len(parsed["rarities"]) == 1:
            record["rarity"] = parsed["rarities"][0]["rarity"]
        else:
            record["rarities"] = parsed["rarities"]
        record["requiresAttunement"] = bool(parsed["attunementNote"])
        if parsed["attunementNote"]:
            record["attunementNote"] = parsed["attunementNote"]

        # Extract each physical block independently.  Reconstructing one
        # synthetic string shifts table offsets whenever a heading or leading
        # blank line is folded into the magic item.
        text_parts = []
        table_ids = []
        prose, ids = self.extract_tables(block, locator)
        if prose:
            text_parts.append(prose)
        table_ids.extend(ids)
        for extra in extra_blocks:
            extra_locator = dict(
                locator,
                heading=extra.title,
                lineStart=extra.line_start,
                lineEnd=extra.line_end,
            )
            prose, ids = self.extract_tables(extra, extra_locator)
            if prose:
                text_parts.append(f"{extra.title}\n\n{prose}".strip())
            table_ids.extend(ids)
        if table_ids:
            record["relatedTables"] = [{"@id": tid} for tid in table_ids]
        record["rulesText"] = "\n\n".join(text_parts)
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
        type_match = re.match(
            r"^(?P<size>(?:Tiny|Small|Medium|Large|Huge|Gargantuan)(?:(?: or (?:Tiny|Small|Medium|Large|Huge|Gargantuan))|(?: or Smaller))?)\s+"
            r"(?P<type>[A-Za-z]+)(?:\s*\((?P<tags>[^)]+)\))?$",
            record["sizeAndType"],
        )
        if type_match:
            record["size"] = type_match.group("size")
            record["creatureType"] = type_match.group("type")
            if type_match.group("tags"):
                record["descriptiveTags"] = [
                    value.strip() for value in type_match.group("tags").split(",")
                ]
        else:
            swarm = re.match(
                r"^(?P<size>Tiny|Small|Medium|Large|Huge|Gargantuan) "
                r"(?P<tag>Swarm of (?:Tiny|Small|Medium|Large|Huge|Gargantuan) (?P<type>[A-Za-z]+))$",
                record["sizeAndType"],
            )
            if swarm:
                creature_type = swarm.group("type")
                if creature_type.endswith("s"):
                    creature_type = creature_type[:-1]
                record["size"] = swarm.group("size")
                record["creatureType"] = creature_type
                record["descriptiveTags"] = [swarm.group("tag")]
        record["monsterCategory"] = (
            "Animal" if block.chapter == "Animals"
            else "NPC" if block.title in NPC_MONSTERS
            else "Monster"
        )
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
            # Summoned-creature stat blocks scale with spell level
            # (e.g. "10 + 1 per spell level"); a scalar index would misstate
            # the printed value, so only unconditional ACs are typed.
            digits = re.match(r"^(\d+)\b(?!\s*\+)", record["armorClass"])
            if digits:
                record["armorClassValue"] = int(digits.group(1))
        if "hitPoints" in record:
            # Same rule for HP: size- or spell-level-conditional totals
            # (e.g. "10 (Medium or smaller), 20 (Large)") stay prose-only.
            hp = re.fullmatch(r"(\d+)(?:\s*\(([^)]+)\))?", record["hitPoints"])
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
            {
                "name": extra.title,
                "rulesText": extra.body,
                "sourceLocator": {
                    **locator,
                    "heading": extra.title,
                    "lineStart": extra.line_start,
                    "lineEnd": extra.line_end,
                },
            }
            for extra in section_extras
        ]
        if sections:
            record["statSections"] = sections
        text_parts = [re.sub(r"(?m)^\|.*?\|\s*$", "", re.sub(r"^<table>.*</table>$", "", stat_text, flags=re.M)).strip()]
        for extra in section_extras:
            text_parts.append(f"{extra.title}\n\n{extra.body}".strip())
        record["rulesText"] = re.sub(
            r"\n{3,}", "\n\n", "\n\n".join(p for p in text_parts if p)
        )
        return record


    # -- species / backgrounds / conditions ---------------------------------

    def emit_species(self, block: Block):
        locator = self.locator(block)
        record = self.new_record(
            "species", "Species", block.title, slugify(block.title), locator
        )
        prose, table_ids = self.extract_tables(block, locator)
        for label, field in (
            ("Creature Type", "creatureType"),
            ("Size", "size"),
            ("Speed", "speed"),
        ):
            found = re.search(rf"^{label}: (.+)$", prose, re.M)
            if found:
                record[field] = found.group(1).strip()
        traits = []
        for paragraph in prose.split("\n\n"):
            m = re.match(r"^([A-Z][A-Za-z'’ -]{2,40})\. (.+)$", paragraph, re.S)
            if m and not m.group(1).startswith(("Creature Type", "Size", "Speed")):
                traits.append(
                    {"name": m.group(1), "rulesText": m.group(2).strip()}
                )
            elif traits and not re.match(r"^(Creature Type|Size|Speed):", paragraph):
                traits[-1]["rulesText"] += "\n\n" + paragraph.strip()
        if traits:
            record["traits"] = traits
        if table_ids:
            record["relatedTables"] = [{"@id": table_id} for table_id in table_ids]
        record["rulesText"] = prose
        return record

    def emit_background(self, block: Block):
        locator = self.locator(block)
        record = self.new_record(
            "backgrounds", "Background", block.title, slugify(block.title), locator
        )
        for label, field in (
            ("Ability Scores", "abilityScores"),
            ("Feat", "feat"),
            ("Skill Proficiencies", "skillProficiencies"),
            ("Tool Proficiency", "toolProficiency"),
            ("Equipment", "startingEquipment"),
        ):
            found = re.search(rf"^{label}: (.+)$", block.body, re.M)
            if found:
                record[field] = found.group(1).strip()
        if "abilityScores" in record:
            record["abilityScoreOptions"] = [
                s.strip() for s in record["abilityScores"].split(",")
            ]
        record["rulesText"] = block.body
        return record

    def emit_condition(self, block: Block):
        locator = self.locator(block)
        name = re.sub(r"\s*\[Condition\]\s*$", "", block.title)
        record = self.new_record(
            "conditions", "Condition", name, slugify(name), locator
        )
        record["rulesText"] = block.body
        record["effects"] = parse_named_effects(block.body)
        return record

    def emit_glossary_family(self, block: Block, family: str):
        collection, type_name = GLOSSARY_FAMILIES[family]
        locator = self.locator(block)
        name = re.sub(rf"\s*\[{re.escape(family)}\]\s*$", "", block.title)
        record = self.new_record(collection, type_name, name, slugify(name), locator)
        record["rulesText"] = block.body
        effects = parse_named_effects(block.body)
        if effects:
            record["effects"] = effects
        return record

    # -- classes and subclasses ---------------------------------------------

    LEVEL_FEATURE_RE = re.compile(r"^Level (\d+): (.+)$")

    def emit_class(self, blocks, index):
        """Consume a class span starting at blocks[index]; returns next index."""
        block = blocks[index]
        class_name = block.title
        locator = self.locator(block)
        record = self.new_record(
            "classes", "CharacterClass", class_name, slugify(class_name), locator
        )
        core = []
        tbl_lines = [l.strip() for l in block.body_lines if l.strip().startswith("|") and l.strip().endswith("|")]
        html_table_match = TABLE_RE.search(block.body)
        if tbl_lines:
            columns, rows = parse_markdown_table(tbl_lines)
            pairs = [columns] + [[c["value"] for c in r["cells"]] for r in rows]
            for pair in pairs:
                if len(pair) >= 2 and pair[0] and pair[1]:
                    core.append({"name": pair[0], "value": pair[1]})
        elif html_table_match:
            columns, rows = parse_html_table(html_table_match.group(0))
            pairs = [columns] + [[c["value"] for c in r["cells"]] for r in rows]
            for pair in pairs:
                if len(pair) == 2:
                    core.append({"name": pair[0], "value": pair[1]})
        if core:
            record["coreTraits"] = core
        prose_parts = [re.sub(r"(?m)^\|.*?\|\s*$", "", re.sub(r"^<table>.*</table>$", "", block.body, flags=re.M)).strip()]
        table_ids = []
        features = []
        current_subclass = None
        option_family = None
        subclass_records = []
        index += 1
        while index < len(blocks):
            nxt = blocks[index]
            if nxt.chapter != "Classes" or nxt.title in CLASS_NAMES:
                break
            feature = self.LEVEL_FEATURE_RE.match(nxt.title)
            sub = re.match(rf"^{class_name} Subclass: (.+)$", nxt.title)
            if sub:
                sub_locator = self.locator(nxt)
                current_subclass = self.new_record(
                    "subclasses",
                    "Subclass",
                    sub.group(1),
                    slugify(sub.group(1)),
                    sub_locator,
                )
                current_subclass["parentClass"] = {"@id": record["@id"]}
                current_subclass["parentClassName"] = class_name
                current_subclass["rulesText"] = nxt.body
                current_subclass["features"] = []
                subclass_records.append((current_subclass, nxt))
            elif feature:
                entry_locator = dict(
                    locator,
                    heading=nxt.title,
                    lineStart=nxt.line_start,
                    lineEnd=nxt.line_end,
                )
                prose, ids = self.extract_tables(nxt, entry_locator)
                entry = {
                    "level": int(feature.group(1)),
                    "name": feature.group(2),
                    "rulesText": prose,
                    "sourceLocator": entry_locator,
                }
                if ids:
                    entry["relatedTables"] = [{"@id": t} for t in ids]
                if current_subclass is not None:
                    current_subclass["features"].append(entry)
                    current_subclass["sourceLocator"]["lineEnd"] = nxt.line_end
                else:
                    features.append(entry)
            elif nxt.title == f"{class_name} Spell List":
                # Keep the spell list as its own Rule record and link it.
                rule = self.emit_rule(nxt)
                record["spellList"] = {"@id": rule["@id"]}
                option_family = None
            elif nxt.title in ("Metamagic Options", "Eldritch Invocation Options"):
                option_family = (
                    "metamagic-options"
                    if nxt.title == "Metamagic Options"
                    else "invocations"
                )
                prose_parts.append(f"{nxt.title}\n\n{nxt.body}".strip())
            elif option_family is not None:
                option_locator = dict(
                    locator,
                    heading=nxt.title,
                    lineStart=nxt.line_start,
                    lineEnd=nxt.line_end,
                )
                if option_family == "metamagic-options":
                    option = self.new_record(
                        option_family,
                        "MetamagicOption",
                        nxt.title,
                        slugify(nxt.title),
                        option_locator,
                    )
                    cost = re.search(r"^Cost: (.+)$", nxt.body, re.M)
                    if cost:
                        option["cost"] = cost.group(1)
                        points = re.match(r"(\d+) Sorcery Point", cost.group(1))
                        if points:
                            option["sorceryPointCost"] = int(points.group(1))
                    record.setdefault("metamagicOptions", []).append({"@id": option["@id"]})
                else:
                    option = self.new_record(
                        option_family,
                        "EldritchInvocation",
                        nxt.title,
                        slugify(nxt.title),
                        option_locator,
                    )
                    prerequisite = re.search(r"^Prerequisite: (.+)$", nxt.body, re.M)
                    if prerequisite:
                        option["prerequisite"] = prerequisite.group(1)
                    option["repeatable"] = "Repeatable." in nxt.body
                    record.setdefault("eldritchInvocations", []).append({"@id": option["@id"]})
                option["parentClass"] = {"@id": record["@id"]}
                option["rulesText"] = nxt.body
            elif current_subclass is not None:
                # Prose between subclass features folds into the subclass.
                current_subclass["rulesText"] += (
                    "\n\n" + f"{nxt.title}\n\n{nxt.body}".strip()
                )
                current_subclass["sourceLocator"]["lineEnd"] = nxt.line_end
            else:
                entry_locator = dict(
                    locator,
                    heading=nxt.title,
                    lineStart=nxt.line_start,
                    lineEnd=nxt.line_end,
                )
                prose, ids = self.extract_tables(nxt, entry_locator)
                prose_parts.append(f"{nxt.title}\n\n{prose}".strip())
                table_ids.extend(ids)
            index += 1
        # Class span provenance covers everything consumed above.
        end_block = blocks[index - 1]
        locator["lineEnd"] = end_block.line_end
        for sub_record, sub_block in subclass_records:
            record.setdefault("subclasses", []).append({"@id": sub_record["@id"]})
        if features:
            record["features"] = features
        if table_ids:
            record["relatedTables"] = [{"@id": t} for t in table_ids]
        record["rulesText"] = re.sub(
            r"\n{3,}", "\n\n", "\n\n".join(p for p in prose_parts if p)
        )
        return index


def parse_markdown_table(table_lines: list[str]):
    if not table_lines:
        return [], []
    first_cells = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
    second_cells = (
        [c.strip() for c in table_lines[1].strip().strip("|").split("|")]
        if len(table_lines) > 1
        else []
    )
    has_header = bool(second_cells) and all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in second_cells
    )
    data_lines = table_lines[2:] if has_header else table_lines
    if has_header:
        hdr_cells = first_cells
    else:
        width = max(
            len(line.strip().strip("|").split("|")) for line in table_lines
        )
        hdr_cells = [f"column{index}" for index in range(1, width + 1)]
    rows = []
    for line in data_lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        while len(cells) < len(hdr_cells):
            cells.append("")
        cells = cells[:len(hdr_cells)]
        # PDF page fragments can repeat the logical table header.  The source
        # row remains in rawText, but it is not promoted to a data row.
        if has_header and cells == hdr_cells:
            continue
        rows.append({
            "position": len(rows) + 1,
            "cells": [{"value": html.unescape(c)} for c in cells]
        })
    return [html.unescape(c) for c in hdr_cells], rows


def parse_html_table(html: str):
    rows_raw = ROW_RE.findall(html)
    parsed_rows = []
    for row in rows_raw:
        cells = []
        for colspan, value in CELL_RE.findall(row):
            cell = {"value": html.unescape(re.sub(r"\s+", " ", value).strip())}
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
    # Match markdown table first
    m = re.search(
        r"\|\s*STR\s*\|\s*DEX\s*\|\s*CON\s*\|\s*INT\s*\|\s*WIS\s*\|\s*CHA\s*\|[^\n]*\n\|[^\n]+\n\|([^\n]+)\n\|([^\n]+)",
        stat_text,
        re.I,
    )
    if m:
        row1_cells = [c.strip() for c in m.group(1).strip().strip("|").split("|")]
        row2_cells = [c.strip() for c in m.group(2).strip().strip("|").split("|")]
        abilities_tuple = ("str", "dex", "con", "int", "wis", "cha")
        result = {}
        for i, ab in enumerate(abilities_tuple):
            if i < len(row1_cells) and i < len(row2_cells):
                cell1 = row1_cells[i]
                cell2 = row2_cells[i]
                m1 = re.search(r"(\d+)\s*\(([+-]?\d+)\)", cell1)
                m2 = re.search(r"([+-]?\d+)", cell2)
                if m1 and m2:
                    score = int(m1.group(1))
                    mod = int(m1.group(2))
                    save = int(m2.group(1))
                    result[ab] = {"score": score, "modifier": mod, "savingThrow": save}
        if result:
            return result

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
        "licenseUrl": {"@id": "https://creativecommons.org/licenses/by/4.0/legalcode"},
        "attributionStatement": ATTRIBUTION_STATEMENT,
        "canonicalUrl": {"@id": "https://www.dndbeyond.com/srd"},
        "sourceFile": SOURCE_FILE,
        "contentDigest": sha256_of(source_path),
        "htmlPage": {"@id": f"{BASE}records/sources/srd-5-2-1/"},
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
                    or MONSTER_RE.match(nfirst)
                ):
                    # A stat block for a summoned creature (e.g. Animated
                    # Object) is promoted to its own Monster record below.
                    break
                extras.append(nxt)
                index += 1
            emitter.emit_spell(block, extras)
            continue

        if chapter == "Feats" and FEAT_RE.match(first):
            emitter.emit_feat(block)
            index += 1
            continue

        if chapter == "Classes" and block.title in CLASS_NAMES and first.startswith(
            "Core "
        ):
            index = emitter.emit_class(blocks, index)
            continue

        if chapter == "Character Origins" and first.startswith("Creature Type:"):
            emitter.emit_species(block)
            index += 1
            continue

        if chapter == "Character Origins" and first.startswith("Ability Scores:"):
            emitter.emit_background(block)
            index += 1
            continue

        if chapter == "Rules Glossary" and block.title.endswith("[Condition]"):
            emitter.emit_condition(block)
            index += 1
            continue

        tagged = re.search(r"\[([^]]+)\]\s*$", block.title)
        if chapter == "Rules Glossary" and tagged and tagged.group(1) in GLOSSARY_FAMILIES:
            emitter.emit_glossary_family(block, tagged.group(1))
            index += 1
            continue

        if chapter == "Magic Items" and parse_magic_item_header(first):
            extras = []
            index += 1
            while index < len(blocks):
                nxt = blocks[index]
                if nxt.chapter != chapter or parse_magic_item_header(nxt.first_body_line()):
                    break
                if MONSTER_RE.match(nxt.first_body_line()):
                    break
                extras.append(nxt)
                index += 1
            emitter.emit_magic_item(block, extras)
            continue

        if chapter in ("Monsters A-Z", "Animals", "Magic Items", "Spells") and MONSTER_RE.match(first):
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

    build_equipment(emitter)
    enrich(emitter)

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


COST_RE = re.compile(r"^([\d,/]+) (CP|SP|EP|GP|PP)$")
DAMAGE_RE = re.compile(r"^(\d+(?:d\d+)?) ([A-Za-z]+)$")


def parse_cost(text: str):
    match = COST_RE.match(text.strip())
    if not match:
        return None
    amount = match.group(1).replace(",", "")
    value = float(amount) if "/" not in amount else None
    if "/" in amount:
        num, den = amount.split("/")
        value = int(num) / int(den)
    cost = {"text": text.strip(), "currency": match.group(2)}
    cost["amount"] = int(value) if value == int(value) else value
    return cost


def parse_weight_pounds(text: str):
    match = re.fullmatch(r"(?:(\d+) )?(\d+)/(\d+) lb\.|(\d+(?:\.\d+)?) lb\.", text.strip())
    if not match:
        return None
    if match.group(4):
        value = float(match.group(4))
    else:
        value = int(match.group(1) or 0) + int(match.group(2)) / int(match.group(3))
    return int(value) if value == int(value) else value


def split_outside_parens(text: str):
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def build_equipment(emitter: Emitter):
    """Emit typed equipment records from the Weapons, Armor, and Adventuring
    Gear tables (already preserved verbatim as Table records)."""

    def find_tables(name):
        return [
            t
            for t in emitter.records["tables"]
            if t["name"] == name and t["sourceLocator"]["chapter"] == "Equipment"
        ]

    def new_item(name, table, equipment_type):
        locator = dict(table["sourceLocator"])
        # Preserve the physical heading/section pair and carry the semantic
        # table caption separately.
        locator["caption"] = table["name"]
        record = emitter.new_record(
            "equipment", "Equipment", name, slugify(name), locator
        )
        record["equipmentType"] = equipment_type
        record["fromTable"] = {"@id": table["@id"]}
        return record

    def add_weight(record, text):
        if text not in ("", "-", "—", "Varies"):
            record["weight"] = text
            pounds = parse_weight_pounds(text)
            if pounds is not None:
                record["weightPounds"] = pounds

    def add_cost(record, text):
        parsed = parse_cost(text)
        if parsed:
            record["cost"] = parsed

    def add_attributes(record, columns, values, skip=(0,)):
        attributes = []
        for index, (column, value) in enumerate(zip(columns, values)):
            if index in skip or not value or value in ("-", "—"):
                continue
            attributes.append({"name": column, "value": value})
        if attributes:
            record["attributes"] = attributes

    for table in find_tables("Weapons"):
        group = None
        for row in table["rows"]:
            cells = [c["value"] for c in row["cells"]]
            if len(cells) == 1 or (len(cells) == 6 and not any(cells[1:])):
                group = cells[0]
                continue
            if len(cells) != 6:
                continue
            name, damage, properties, mastery, weight, cost = cells
            record = new_item(name, table, "weapon")
            if group:
                words = group.split()  # e.g. "Simple Melee Weapons"
                record["weaponCategory"] = words[0]
                record["attackType"] = words[1]
            record["damage"] = damage
            dm = DAMAGE_RE.match(damage)
            if dm:
                record["damageType"] = dm.group(2)
                roll = parse_dice(dm.group(1))
                if roll:
                    record["damageRoll"] = roll
            if properties and properties not in ("—", "-"):
                record["properties"] = split_outside_parens(properties)
            record["mastery"] = mastery
            add_weight(record, weight)
            add_cost(record, cost)

    for table in find_tables("Armor"):
        group = None
        note = None
        for row in table["rows"]:
            cells = [c["value"] for c in row["cells"]]
            if len(cells) == 1 or (len(cells) == 6 and not any(cells[1:])):
                m = re.match(r"^(.*?)\s*(?:\((.+)\))?$", cells[0])
                group, note = (m.group(1), m.group(2)) if m else (cells[0], None)
                continue
            if len(cells) != 6:
                continue
            name, ac, strength, stealth, weight, cost = cells
            record = new_item(name, table, "armor")
            if group:
                record["armorCategory"] = group.replace(" Armor", "")
            if note:
                record["donDoffTime"] = note
            record["armorClass"] = ac
            if strength not in ("—", "-"):
                record["strengthRequirement"] = strength
            if stealth not in ("—", "-"):
                record["stealthEffect"] = stealth
            add_weight(record, weight)
            add_cost(record, cost)

    for table in find_tables("Adventuring Gear"):
        for row in table["rows"]:
            cells = [c["value"] for c in row["cells"]]
            if len(cells) != 3 or cells[0] == "Item":
                continue
            name, weight, cost = cells
            record = new_item(name, table, "gear")
            add_weight(record, weight)
            add_cost(record, cost)

    # Tool headings are prose entries rather than source-table rows. Their
    # printed price, ability, weight, Utilize, Craft, and Variants labels are
    # indexed while the complete source text remains in the linked Rule.
    rules_by_name = {rule["name"]: rule for rule in emitter.records["rules"]}
    tool_start = rules_by_name.get("Artisan's Tools", {}).get("sourceLocator", {}).get("lineStart", 0)
    tool_end = rules_by_name.get("Adventuring Gear", {}).get("sourceLocator", {}).get("lineStart", 0)
    for rule in list(emitter.records["rules"]):
        line_start = rule["sourceLocator"]["lineStart"]
        match = re.fullmatch(r"(.+) \(((?:[\d,/]+ (?:CP|SP|EP|GP|PP))|Varies)\)", rule["name"])
        if not (match and tool_start < line_start < tool_end):
            continue
        locator = dict(rule["sourceLocator"])
        record = emitter.new_record(
            "equipment", "Equipment", match.group(1), slugify(match.group(1)), locator
        )
        record["equipmentType"] = "tool"
        record["fromRule"] = {"@id": rule["@id"]}
        record["relatedRules"] = [{"@id": rule["@id"]}]
        add_cost(record, match.group(2))
        body = rule.get("rulesText", "")
        ability = re.search(r"\bAbility: ([A-Za-z]+)", body)
        weight = re.search(r"\bWeight: ([^\n]+?)(?=\s+(?:Utilize|Craft|Variants):|$)", body)
        utilize = re.search(r"^Utilize: (.+)$", body, re.M)
        craft = re.search(r"^Craft: (.+)$", body, re.M)
        variants = re.search(r"^Variants: (.+)$", body, re.M)
        if ability:
            record["ability"] = ability.group(1)
        if weight:
            add_weight(record, weight.group(1).strip())
        if utilize:
            record["utilize"] = utilize.group(1)
        if craft:
            record["craft"] = craft.group(1)
        if variants:
            record["variants"] = [value.strip() for value in split_outside_parens(variants.group(1))]

    # Additional Equipment-chapter tables describe purchasable physical
    # items and services. Emit one typed record per logical row/item.
    simple_tables = {
        "Mounts and Other Animals": "mount",
        "Tack, Harness, and Drawn Vehicles": "gear",
        "Airborne and Waterborne Vehicles": "vehicle",
        "Hirelings": "service",
        "Arcane Focuses": "focus",
        "Druidic Focuses": "focus",
        "Holy Symbols": "focus",
    }
    for table_name, equipment_type in simple_tables.items():
        for table in find_tables(table_name):
            for row in table["rows"]:
                values = [cell["value"] for cell in row["cells"]]
                if not values or not values[0] or values[0] in table["columns"]:
                    continue
                record = new_item(values[0], table, equipment_type)
                add_attributes(record, table["columns"], values)
                for column, value in zip(table["columns"], values):
                    if column == "Weight":
                        add_weight(record, value)
                    elif column == "Cost":
                        add_cost(record, value)

    for table in find_tables("Food, Drink, and Lodging"):
        for row in table["rows"]:
            values = [cell["value"] for cell in row["cells"]]
            for offset in (0, 2):
                if offset + 1 >= len(values) or not values[offset] or not values[offset + 1]:
                    continue
                record = new_item(values[offset], table, "service")
                add_cost(record, values[offset + 1])
                record["attributes"] = [{"name": "Cost", "value": values[offset + 1]}]

    for table in find_tables("Spellcasting Services"):
        for row in table["rows"]:
            values = [cell["value"] for cell in row["cells"]]
            if len(values) != 3 or not values[0]:
                continue
            record = new_item(f"Spellcasting Service: {values[0]}", table, "service")
            record["serviceLevel"] = values[0]
            add_attributes(record, table["columns"], values, skip=())
            add_cost(record, values[2])

    for table in find_tables("Ammunition"):
        if table["columns"][:3] != ["Type", "Amount", "Storage"]:
            continue
        for row in table["rows"]:
            values = [cell["value"] for cell in row["cells"]]
            if len(values) != 5:
                continue
            record = new_item(values[0], table, "ammunition")
            record["quantity"] = values[1]
            record["storage"] = values[2]
            add_weight(record, values[3])
            add_cost(record, values[4])
            add_attributes(record, table["columns"], values)


ATTACK_HEADER_RE = re.compile(
    r"^(?P<name>.+?)\.\s+"
    r"(?P<attackType>Melee or Ranged|Melee|Ranged) Attack Roll:\s*"
    r"(?P<attackBonus>[+-]\d+|Automatic hit)(?:\s+to hit)?(?:\s*\([^)]*\))?,\s*"
    r"(?P<targeting>.*?)\.\s*Hit:\s*(?P<hit>.+)$",
    re.S,
)
DAMAGE_COMPONENT_RE = re.compile(
    r"(?P<average>\d+)(?:\s*\((?P<roll>\d+d\d+(?:\s*[+-]\s*\d+)?)\))?\s+"
    r"(?P<damageType>[A-Za-z]+) damage"
)
SAVE_RE = re.compile(
    r"(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) saving throw"
)
SPELL_DAMAGE_RE = re.compile(r"\b(\d+d\d+(?: ?[+-] ?\d+)?) ([A-Z][a-z]+) damage")


def link_gear_rules(emitter: Emitter):
    """Link each gear item to the Equipment-chapter Rule describing it.

    The gear tables carry stats only; the prose descriptions were emitted as
    separate Rule records whose names carry a trailing parenthetical (e.g.
    "Torch (1 CP)", "Ammunition (Varies)"). Only those rules are candidates:
    bare-named Equipment-chapter rules are shared concepts (e.g. the
    "Ammunition" weapon property), not item descriptions. Names are matched
    after normalizing typographic apostrophes, on the rule name with its
    parenthetical stripped, then with the item's own variant parenthetical
    stripped too. Ambiguous matches are never linked.
    """

    def strip_paren(text):
        return re.sub(r"\s*\([^)]*\)$", "", text)

    base_names = {}
    for rule in emitter.records["rules"]:
        if rule["sourceLocator"]["chapter"] != "Equipment":
            continue
        norm = rule["name"].replace("’", "'")
        base = strip_paren(norm)
        if base == norm:
            continue
        base_names.setdefault(base, []).append(rule["@id"])
    for item in emitter.records["equipment"]:
        if item["equipmentType"] != "gear":
            continue
        name = item["name"].replace("’", "'")
        for candidates in (
            base_names.get(name, []),
            base_names.get(strip_paren(name), []),
        ):
            if len(candidates) == 1:
                item["relatedRules"] = [{"@id": candidates[0]}]
                break


def named_node_references(text, name_ids, flags=0):
    """Return longest, non-overlapping exact-name references in source order."""
    candidates = []
    search_text = text.replace("’", "'")
    for name, node_id in name_ids.items():
        search_name = name.replace("’", "'")
        pattern = rf"(?<![A-Za-z]){re.escape(search_name)}(?![A-Za-z])"
        for match in re.finditer(pattern, search_text, flags):
            candidates.append((match.start(), -len(name), match.end(), name, node_id))

    occupied = []
    references = []
    seen_ids = set()
    for start, _negative_length, end, _name, node_id in sorted(candidates):
        if any(start < used_end and end > used_start for used_start, used_end in occupied):
            continue
        occupied.append((start, end))
        if node_id not in seen_ids:
            references.append({"@id": node_id})
            seen_ids.add(node_id)
    return references


def record_strings(value):
    """Yield record strings that can carry exact source-name mentions."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in ("@context", "@id", "source", "sourceLocator"):
                yield from record_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from record_strings(child)
    elif isinstance(value, str):
        yield value


def parse_range_details(text: str):
    details = {"text": text}
    normalized = text.strip()
    if normalized == "Self" or normalized.startswith("Self ("):
        details["kind"] = "Self"
    elif normalized == "Touch":
        details["kind"] = "Touch"
    elif normalized == "Sight":
        details["kind"] = "Sight"
    elif normalized in ("Unlimited", "Special"):
        details["kind"] = normalized
    else:
        match = re.match(r"([\d,]+) (feet|mile|miles)$", normalized)
        details["kind"] = "Distance" if match else "Special"
        if match:
            value = int(match.group(1).replace(",", ""))
            details["distanceFeet" if match.group(2) == "feet" else "distanceMiles"] = value
    return details


def parse_duration_details(text: str):
    details = {"text": text, "concentration": text.startswith("Concentration")}
    normalized = re.sub(r"^Concentration,\s*", "", text)
    if normalized == "Instantaneous":
        details["kind"] = "Instantaneous"
    elif normalized in ("Until dispelled", "Until Dispelled"):
        details["kind"] = "UntilDispelled"
    elif normalized == "Special":
        details["kind"] = "Special"
    else:
        match = re.fullmatch(r"(up to )?(\d+) (round|rounds|minute|minutes|hour|hours|day|days)", normalized)
        details["kind"] = "Timed" if match else "Special"
        if match:
            details["upTo"] = bool(match.group(1))
            details["value"] = int(match.group(2))
            details["unit"] = match.group(3).rstrip("s")
    return details


def parse_component_details(text: str):
    details = {
        "text": text,
        "verbal": bool(re.search(r"(?:^|, )V(?:,|$)", text)),
        "somatic": bool(re.search(r"(?:^|, )S(?:,|$)", text)),
        "material": bool(re.search(r"(?:^|, )M(?:\s|,|$)", text)),
    }
    material = re.search(r"\bM \((.+)\)$", text)
    if material:
        details["materialText"] = material.group(1)
        details["consumed"] = "consumes" in material.group(1)
        cost = re.search(r"worth ([\d,]+)\+? (CP|SP|EP|GP|PP)", material.group(1))
        if cost:
            details["materialCost"] = parse_cost(f"{cost.group(1)} {cost.group(2)}")
    return details


def parse_area_effects(text: str, area_ids: dict[str, str]):
    effects = []
    seen = set()
    for paragraph in re.split(r"\n\s*\n", text):
        for shape, node_id in area_ids.items():
            if not re.search(rf"\b{re.escape(shape)}\b", paragraph):
                continue
            sentence_match = re.search(
                rf"[^.!?\n]*\b{re.escape(shape)}\b[^.!?\n]*[.!?]?",
                paragraph,
            )
            source_text = (sentence_match.group(0) if sentence_match else paragraph).strip()
            key = (shape, source_text)
            if key in seen:
                continue
            seen.add(key)
            entry = {
                "shape": shape,
                "areaShape": {"@id": node_id},
                "sourceText": source_text,
            }
            radius = re.search(r"(\d+)-foot-radius", source_text)
            length = re.search(r"(\d+)-foot-(?:long|long,)\s*", source_text)
            width = re.search(r"(\d+)-foot-wide", source_text)
            height = re.search(r"(\d+)-foot-(?:high|tall)", source_text)
            generic = re.search(rf"(\d+)-foot\s+{re.escape(shape)}\b", source_text)
            if radius:
                entry["radiusFeet"] = int(radius.group(1))
            if length:
                entry["lengthFeet"] = int(length.group(1))
            if width:
                entry["widthFeet"] = int(width.group(1))
            if height:
                entry["heightFeet"] = int(height.group(1))
            if generic and shape in ("Cube", "Cone", "Emanation"):
                entry["sizeFeet"] = int(generic.group(1))
            effects.append(entry)
    return effects


def parse_saving_throws(text: str):
    entries = []
    seen = set()
    for paragraph in re.split(r"\n\s*\n", text):
        for match in SAVE_RE.finditer(paragraph):
            key = (match.group(1), paragraph)
            if key in seen:
                continue
            seen.add(key)
            entry = {"ability": match.group(1), "sourceText": paragraph.strip()}
            dc = re.search(r"\bDC (\d+)\b", paragraph)
            if dc:
                entry["fixedDC"] = int(dc.group(1))
            outcomes = []
            lowered = paragraph.lower()
            if "successful save" in lowered or "on a success" in lowered or "success:" in lowered:
                if "half" in lowered:
                    outcomes.append("HalfDamage")
                elif "no damage" in lowered or "no effect" in lowered:
                    outcomes.append("Negates")
                else:
                    outcomes.append("Partial")
            if "failed save" in lowered or "on a failed" in lowered or "failure:" in lowered:
                outcomes.append("FailureEffect")
            if outcomes:
                entry["outcomes"] = sorted(set(outcomes))
            entries.append(entry)
    return entries


def parse_monster_spellcasting(monster: dict, spell_ids: dict[str, str]):
    profiles = []
    references = []
    seen_refs = set()
    for section_index, section in enumerate(monster.get("statSections", [])):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section["rulesText"]) if p.strip()]
        index = 0
        while index < len(paragraphs):
            paragraph = paragraphs[index]
            spellcasting_header = re.match(r"^(?P<label>[^.\n]*Spellcasting[^.\n]*)\.\s*", paragraph)
            if not spellcasting_header:
                index += 1
                continue
            parts = [paragraph]
            cursor = index + 1
            while cursor < len(paragraphs) and re.match(
                r"^(?:At Will|\d+/(?:Day|Week)(?: Each)?):", paragraphs[cursor]
            ):
                parts.append(paragraphs[cursor])
                cursor += 1
            source_text = "\n\n".join(parts)
            profile = {
                "section": section["name"],
                "sourceText": source_text,
                "path": f"statSections[{section_index}].rulesText",
                "entries": [],
            }
            ability = re.search(r"using ([A-Z][a-z]+) as the spellcasting ability", paragraph)
            save_dc = re.search(r"spell save DC (\d+)", paragraph)
            attack = re.search(r"([+\-]\d+) to hit with spell attacks", paragraph)
            if ability:
                profile["ability"] = ability.group(1)
            if save_dc:
                profile["saveDC"] = int(save_dc.group(1))
            if attack:
                profile["attackBonus"] = int(attack.group(1))
            for part in parts[1:]:
                frequency, spell_text = part.split(":", 1)
                refs = named_node_references(spell_text, spell_ids, flags=re.I)
                entry = {
                    "frequency": frequency,
                    "spellsText": spell_text.strip(),
                }
                if refs:
                    entry["spells"] = refs
                profile["entries"].append(entry)
                for ref in refs:
                    if ref["@id"] not in seen_refs:
                        references.append(ref)
                        seen_refs.add(ref["@id"])
            if not profile["entries"]:
                refs = named_node_references(paragraph, spell_ids, flags=re.I)
                if refs:
                    profile["entries"].append({
                        "frequency": spellcasting_header.group("label"),
                        "spellsText": paragraph,
                        "spells": refs,
                    })
                    for ref in refs:
                        if ref["@id"] not in seen_refs:
                            references.append(ref)
                            seen_refs.add(ref["@id"])
            profiles.append(profile)
            index = cursor
    return profiles, references


ACTIVE_ITEM_CAST_RE = re.compile(
    r"\byou\b[^.!?\n]{0,120}?\bcast(?:s|ing)?\b|"
    r"\b(?:the )?orb\b[^.!?\n]{0,80}?\bcasts?\b|"
    r"\bto cast\b",
    re.I,
)


def link_magic_item_spells(emitter: Emitter, spell_ids):
    """Link spells an item explicitly lets its bearer or the item cast."""
    for item in emitter.records["magic-items"]:
        references = []
        seen_ids = set()
        sentences = re.split(r"\n\n|(?<=[.!?])\s+", item["rulesText"])
        for sentence in sentences:
            for active_cast in ACTIVE_ITEM_CAST_RE.finditer(sentence):
                for reference in named_node_references(
                    sentence[active_cast.end() :], spell_ids, flags=re.I
                ):
                    if reference["@id"] not in seen_ids:
                        references.append(reference)
                        seen_ids.add(reference["@id"])
        if references:
            item["castsSpell"] = references


def link_class_spell_tables(emitter: Emitter, spell_ids):
    """Link the spell-name cells in the eight printed class spell lists."""
    for table in emitter.records["tables"]:
        if (
            table["sourceLocator"]["chapter"] != "Classes"
            or table.get("columns", [])[:3] != ["Spell", "School", "Special"]
        ):
            continue
        references = []
        seen_ids = set()
        for row in table["rows"]:
            if not row["cells"]:
                continue
            for reference in named_node_references(row["cells"][0]["value"], spell_ids):
                if reference["@id"] not in seen_ids:
                    references.append(reference)
                    seen_ids.add(reference["@id"])
        if references:
            table["listsSpell"] = references


def link_background_feats(emitter: Emitter, feat_ids):
    """Resolve the printed background feat, retaining its display string."""
    names = sorted(feat_ids, key=len, reverse=True)
    for background in emitter.records["backgrounds"]:
        printed = background["feat"]
        for name in names:
            if re.match(rf"^{re.escape(name)}(?:\s|\(|$)", printed):
                background["grantsFeat"] = {"@id": feat_ids[name]}
                break


def link_background_proficiencies(emitter: Emitter, equipment_ids):
    """Index printed background skills, tools, and starting equipment."""
    for background in emitter.records["backgrounds"]:
        background["skillProficiencyOptions"] = [
            value.strip()
            for value in background.get("skillProficiencies", "").split(",")
            if value.strip()
        ]
        tool_refs = named_node_references(
            background.get("toolProficiency", ""), equipment_ids
        )
        if tool_refs:
            background["grantsTool"] = tool_refs
        equipment_refs = named_node_references(
            background.get("startingEquipment", ""), equipment_ids
        )
        if equipment_refs:
            background["grantsEquipment"] = equipment_refs


def link_summoned_monsters(emitter: Emitter):
    """Restore forward edges from spells to their promoted source stat blocks."""
    spells = sorted(
        emitter.records["spells"], key=lambda record: record["sourceLocator"]["lineStart"]
    )
    summoned = [
        monster for monster in emitter.records["monsters"]
        if monster["sourceLocator"]["chapter"] == "Spells"
    ]
    for monster in summoned:
        line = monster["sourceLocator"]["lineStart"]
        owners = [spell for spell in spells if spell["sourceLocator"]["lineStart"] < line]
        if not owners:
            continue
        owner = owners[-1]
        next_spells = [spell for spell in spells if spell["sourceLocator"]["lineStart"] > owner["sourceLocator"]["lineStart"]]
        if next_spells and line > next_spells[0]["sourceLocator"]["lineStart"]:
            continue
        owner.setdefault("summons", []).append({"@id": monster["@id"]})


def link_explicit_see_also(emitter: Emitter):
    """Resolve explicit 'See also' clauses, never incidental name mentions."""
    name_candidates = {}
    rule_ids = set()
    for collection, records in emitter.records.items():
        if collection == "sources":
            continue
        for record in records:
            name_candidates.setdefault(record["name"], []).append(record["@id"])
            if collection in ("rules", "actions", "areas-of-effect", "attitudes", "hazards"):
                rule_ids.add(record["@id"])
    unique_names = {
        name: ids[0] for name, ids in name_candidates.items() if len(ids) == 1
    }
    for collection, records in emitter.records.items():
        if collection == "sources":
            continue
        for record in records:
            explicit = []
            for value in record_strings(record):
                explicit.extend(
                    match.group(0)
                    for match in re.finditer(r"See also\b[^\n]*", value, re.I)
                )
            if not explicit:
                continue
            refs = named_node_references("\n".join(explicit), unique_names, flags=re.I)
            refs = [ref for ref in refs if ref["@id"] != record["@id"]]
            if refs:
                record["seeAlso"] = refs
                related = [ref for ref in refs if ref["@id"] in rule_ids]
                if related:
                    record["relatedRules"] = related


def link_catalog_members(emitter: Emitter):
    """Link printed catalog headings to the entity records they introduce."""
    catalogs = {
        "Background Descriptions": "backgrounds",
        "Species Descriptions": "species",
        "Magic Items A-Z": "magic-items",
    }
    for heading, collection in catalogs.items():
        parent = next(
            (rule for rule in emitter.records["rules"] if rule["name"] == heading),
            None,
        )
        if parent:
            parent["hasPart"] = [
                {"@id": record["@id"]} for record in emitter.records[collection]
            ]


def link_monster_gear(emitter: Emitter, equipment_ids):
    """Resolve comma-delimited monster gear, including printed quantities."""
    for monster in emitter.records["monsters"]:
        references = []
        seen_ids = set()
        for token in monster.get("gear", "").split(", "):
            name = re.sub(r"\s+\(\d+\)$", "", token)
            candidates = [name]
            if name.endswith("s"):
                candidates.append(name[:-1])
            for candidate in candidates:
                node_id = equipment_ids.get(candidate)
                if node_id and node_id not in seen_ids:
                    references.append({"@id": node_id})
                    seen_ids.add(node_id)
                    break
        if references:
            monster["hasGear"] = references


def link_condition_mentions(emitter: Emitter, condition_ids):
    """Link exact '<Name> condition' phrases without inferring their effect."""
    for collection, records in emitter.records.items():
        if collection == "sources":
            continue
        for record in records:
            text = "\n".join(record_strings(record))
            references = []
            for name, node_id in condition_ids.items():
                if re.search(
                    rf"(?<![A-Za-z]){re.escape(name)} condition\b", text
                ):
                    references.append({"@id": node_id})
            if references:
                record["mentionsCondition"] = references


def enrich(emitter: Emitter):
    """Cross-link entities and add typed micro-format fields."""
    class_ids = {r["name"]: r["@id"] for r in emitter.records["classes"]}
    condition_ids = {r["name"]: r["@id"] for r in emitter.records["conditions"]}
    spell_ids = {r["name"]: r["@id"] for r in emitter.records["spells"]}
    feat_ids = {r["name"]: r["@id"] for r in emitter.records["feats"]}
    equipment_ids = {r["name"]: r["@id"] for r in emitter.records["equipment"]}
    area_ids = {r["name"]: r["@id"] for r in emitter.records["areas-of-effect"]}

    link_gear_rules(emitter)
    link_magic_item_spells(emitter, spell_ids)
    link_class_spell_tables(emitter, spell_ids)
    link_background_feats(emitter, feat_ids)
    link_background_proficiencies(emitter, equipment_ids)
    link_monster_gear(emitter, equipment_ids)
    link_summoned_monsters(emitter)

    for spell in emitter.records["spells"]:
        refs = [
            {"@id": class_ids[name]}
            for name in spell.get("classAvailability", [])
            if name in class_ids
        ]
        if refs:
            spell["classes"] = refs
        save = SAVE_RE.search(spell["rulesText"])
        if save:
            spell["savingThrowAbility"] = save.group(1)
        saving_throws = parse_saving_throws(spell["rulesText"])
        if saving_throws:
            spell["savingThrows"] = saving_throws
        damages = []
        for dice, dtype in SPELL_DAMAGE_RE.findall(spell["rulesText"]):
            entry = {"damageType": dtype}
            roll = parse_dice(dice.replace(" ", ""))
            if roll:
                entry["damageRoll"] = roll
            else:
                entry["expression"] = dice
            if entry not in damages:
                damages.append(entry)
        if damages:
            spell["damage"] = damages
        spell["scalesWithSlotLevel"] = (
            "Using a Higher-Level Spell Slot" in spell["rulesText"]
        )
        spell["concentration"] = spell.get("duration", "").startswith("Concentration")
        spell["ritual"] = "Ritual" in spell.get("castingTime", "")
        spell["rangeDetails"] = parse_range_details(spell["range"])
        spell["durationDetails"] = parse_duration_details(spell["duration"])
        spell["componentDetails"] = parse_component_details(spell["components"])
        areas = parse_area_effects(spell["rulesText"], area_ids)
        if areas:
            spell["areasOfEffect"] = areas
            spell["areaShapes"] = list({entry["areaShape"]["@id"]: entry["areaShape"] for entry in areas}.values())

    for monster in emitter.records["monsters"]:
        linked = []
        immunities = monster.get("immunities", "")
        for name, cid in sorted(condition_ids.items()):
            if re.search(rf"\b{re.escape(name)}\b", immunities):
                linked.append({"@id": cid})
        if linked:
            monster["conditionImmunities"] = linked
        movement = []
        for match in re.finditer(
            r"(?:(Burrow|Climb|Fly|Swim) )?(\d+) ft\.(?: \((hover)\))?",
            monster.get("speed", ""),
        ):
            entry = {
                "mode": match.group(1) or "Walk",
                "feet": int(match.group(2)),
            }
            if match.group(3):
                entry["hover"] = True
            movement.append(entry)
        if movement:
            monster["movement"] = movement
        skills = []
        for name, bonus in re.findall(r"([A-Za-z ]+?) ([+\-−]\d+)(?:,|$)", monster.get("skills", "")):
            skills.append({"name": name.strip(), "bonus": int(bonus.replace("−", "-"))})
        if skills:
            monster["skillBonuses"] = skills
        passive = re.search(r"Passive Perception (\d+)", monster.get("senses", ""))
        if passive:
            monster["passivePerception"] = int(passive.group(1))
        senses = []
        for name, distance in re.findall(
            r"(Blindsight|Darkvision|Truesight|Tremorsense) (\d+) ft\.",
            monster.get("senses", ""),
        ):
            senses.append({"name": name, "rangeFeet": int(distance)})
        if senses:
            monster["senseModes"] = senses
        languages = [
            value.strip()
            for value in re.split(r"[,;]", monster.get("languages", ""))
            if value.strip() and value.strip() != "None"
        ]
        if languages:
            monster["languageList"] = languages
        for field, target in (
            ("immunities", "damageImmunities"),
            ("resistances", "damageResistances"),
            ("vulnerabilities", "damageVulnerabilities"),
        ):
            values = [
                damage_type for damage_type in DAMAGE_TYPES
                if re.search(rf"\b{damage_type}\b", monster.get(field, ""))
            ]
            if values:
                monster[target] = values
        gear_items = []
        for token in monster.get("gear", "").split(", "):
            if not token:
                continue
            quantity = re.search(r"\((\d+)\)$", token)
            gear_items.append({
                "name": re.sub(r"\s+\(\d+\)$", "", token),
                **({"quantity": int(quantity.group(1))} if quantity else {}),
            })
        if gear_items:
            monster["gearItems"] = gear_items
        spellcasting, spell_refs = parse_monster_spellcasting(monster, spell_ids)
        if spellcasting:
            monster["spellcasting"] = spellcasting
        if spell_refs:
            monster["castsSpell"] = spell_refs
        attacks = []
        unparsed_attacks = []
        for section_index, section in enumerate(monster.get("statSections", [])):
            if section["name"] not in ("Actions", "Bonus Actions", "Legendary Actions", "Reactions"):
                continue
            source_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section["rulesText"]) if p.strip()]
            paragraphs = []
            for paragraph in source_paragraphs:
                if paragraphs and (
                    paragraph.startswith(("Melee Attack Roll:", "Ranged Attack Roll:"))
                    or (paragraph.startswith("Hit:") and "Attack Roll:" in paragraphs[-1])
                    or (
                        paragraph.endswith("damage.")
                        and "Attack Roll:" in paragraphs[-1]
                        and "Hit:" in paragraphs[-1]
                        and not re.search(r"\b[A-Za-z]+ damage\b", paragraphs[-1])
                    )
                ):
                    paragraphs[-1] += " " + paragraph
                else:
                    paragraphs.append(paragraph)
            for paragraph_index, paragraph in enumerate(paragraphs):
                if "Attack Roll:" not in paragraph:
                    continue
                normalized = re.sub(r"\s+", " ", paragraph).strip()
                m = ATTACK_HEADER_RE.match(normalized)
                if not m:
                    unparsed_attacks.append({
                        "sourceText": paragraph,
                        "path": f"statSections[{section_index}].rulesText.paragraphs[{paragraph_index}]",
                        "parseStatus": "unparsed",
                        "reason": "attack paragraph did not match the supported header grammar",
                    })
                    continue
                components = []
                for damage in DAMAGE_COMPONENT_RE.finditer(m.group("hit")):
                    component = {
                        "averageDamage": int(damage.group("average")),
                        "damageType": damage.group("damageType"),
                    }
                    if damage.group("roll"):
                        roll = parse_dice(damage.group("roll").replace(" ", ""))
                        if roll:
                            component["damageRoll"] = roll
                    components.append(component)
                attack = {
                    "name": m.group("name").strip(),
                    "attackType": m.group("attackType"),
                    "damageComponents": components,
                    "sourceText": paragraph,
                    "path": f"statSections[{section_index}].rulesText.paragraphs[{paragraph_index}]",
                    "parseStatus": "parsed",
                }
                if m.group("attackBonus") == "Automatic hit":
                    attack["automaticHit"] = True
                else:
                    attack["attackBonus"] = int(m.group("attackBonus"))
                targeting = m.group("targeting")
                reach = re.search(r"\breach (\d+) (?:ft\.?|feet)\b", targeting)
                if reach:
                    attack["reachFeet"] = int(reach.group(1))
                range_match = re.search(
                    r"\brange (\d+)(?:/(\d+))? (?:ft\.?|feet)\b", targeting
                )
                if range_match:
                    attack["rangeFeet"] = {"normal": int(range_match.group(1))}
                    if range_match.group(2):
                        attack["rangeFeet"]["long"] = int(range_match.group(2))
                if not components:
                    unparsed_attacks.append({
                        "sourceText": paragraph,
                        "path": attack["path"],
                        "parseStatus": "unparsed",
                        "reason": "attack hit clause contained no recognized damage component",
                    })
                    continue
                attacks.append(attack)
        if attacks:
            monster["attacks"] = attacks
        if unparsed_attacks:
            monster["unparsedAttacks"] = unparsed_attacks

    for item in emitter.records["magic-items"]:
        text = item["rulesText"]
        capacity = re.search(
            r"\b(?:has|have|holds?|maximum of) (\d+d\d+(?:\s*[+\-]\s*\d+)?|\d+) charges?\b",
            text,
            re.I,
        )
        recharge = re.search(
            r"[^.!?\n]*\bregains?\b[^.!?\n]*\bcharges?\b[^.!?\n]*[.!?]",
            text,
            re.I,
        )
        if capacity:
            charges = {"capacityText": capacity.group(1)}
            roll = parse_dice(capacity.group(1).replace(" ", ""))
            if roll:
                charges["capacityRoll"] = roll
            elif capacity.group(1).isdigit():
                charges["capacity"] = int(capacity.group(1))
            if recharge:
                charges["rechargeText"] = recharge.group(0).strip()
            item["charges"] = charges
        item["isCursed"] = bool(
            re.search(r"\b(?:is cursed|cursed item|curse\.)", text, re.I)
        )
        item["isSentient"] = bool(re.search(r"\bsentient\b", text, re.I))
        if item.get("attunementNote") and item["attunementNote"] != "Requires Attunement":
            class_refs = named_node_references(item["attunementNote"], class_ids)
            if class_refs:
                item["attunementClasses"] = class_refs
            item["attunementRestriction"] = item["attunementNote"]

    for option in emitter.records["invocations"]:
        refs = []
        seen = set()
        for sentence in re.split(r"\n\n|(?<=[.!?])\s+", option["rulesText"]):
            if not re.search(r"\bcast\b", sentence, re.I):
                continue
            for ref in named_node_references(sentence, spell_ids, flags=re.I):
                if ref["@id"] not in seen:
                    refs.append(ref)
                    seen.add(ref["@id"])
        if refs:
            option["castsSpell"] = refs

    for rule in emitter.records["rules"]:
        if not rule.get("ruleCategory"):
            continue
        text = rule.get("rulesText", "")
        fixed_dcs = []
        for match in re.finditer(r"\bDC (\d+)\b", text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 100)
            source_text = re.sub(r"\s+", " ", text[start:end]).strip()
            entry = {"dc": int(match.group(1)), "sourceText": source_text}
            ability = re.search(
                r"(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)",
                source_text,
            )
            if ability:
                entry["ability"] = ability.group(1)
            if entry not in fixed_dcs:
                fixed_dcs.append(entry)
        if fixed_dcs:
            rule["fixedDCs"] = fixed_dcs
        damages = []
        for dice, damage_type in SPELL_DAMAGE_RE.findall(text):
            entry = {"damageType": damage_type}
            roll = parse_dice(dice.replace(" ", ""))
            if roll:
                entry["damageRoll"] = roll
            if entry not in damages:
                damages.append(entry)
        if damages:
            rule["damage"] = damages

    link_condition_mentions(emitter, condition_ids)
    link_explicit_see_also(emitter)
    link_catalog_members(emitter)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    counts = run_extraction(Path(args.root).resolve())
    for collection in COLLECTIONS:
        print(f"{collection}: {counts[collection]}")


if __name__ == "__main__":
    main()
