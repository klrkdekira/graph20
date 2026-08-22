"""Authoritative ground-truth source repair, table, and layout normalization for SRD_CC_v5.2.1.md.

Cross-checks and normalizes MinerU OCR/conversion defects in SRD_CC_v5.2.1.md
using the direct PyMuPDF text-layer ground truth in SRD_CC_v5.2.1.txt,
reformats all tables into clean, well-organized GitHub-Flavored Markdown (GFM)
pipe tables, repairs OCR sidebar splices, class progression table positioning,
and cleans up document layout (hyphenation, bullets, TOC, headings, and stat blocks).

Every repair class is registered in objects/sources/extraction-overrides.json.
This script is completely self-contained and idempotent.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Explicit tables where 2-column page layout in PDF places the table block
# in the adjacent column
EXPLICIT_TABLES = {
    "Adult Bronze Dragon": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 25 (+7) | 10 (+0) | 23 (+6) | 16 (+3) | 15 (+2) | 20 (+5) |\n"
        "| Save: +7 | Save: +5 | Save: +6 | Save: +3 | Save: +7 | Save: +5 |"
    ),
    "Chimera": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 19 (+4) | 11 (+0) | 19 (+4) | 3 (-4) | 14 (+2) | 10 (+0) |\n"
        "| Save: +4 | Save: +0 | Save: +4 | Save: -4 | Save: +2 | Save: +0 |"
    ),
    "Adult Copper Dragon": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 23 (+6) | 12 (+1) | 21 (+5) | 18 (+4) | 15 (+2) | 18 (+4) |\n"
        "| Save: +6 | Save: +6 | Save: +5 | Save: +4 | Save: +7 | Save: +4 |"
    ),
    "Ghast": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 16 (+3) | 17 (+3) | 10 (+0) | 11 (+0) | 10 (+0) | 8 (-1) |\n"
        "| Save: +3 | Save: +3 | Save: +0 | Save: +0 | Save: +2 | Save: -1 |"
    ),
    "Homunculus": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 4 (-3) | 15 (+2) | 14 (+2) | 10 (+0) | 10 (+0) | 7 (-2) |\n"
        "| Save: -3 | Save: +2 | Save: +2 | Save: +0 | Save: +2 | Save: +0 |"
    ),
    "Ice Mephit": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 7 (-2) | 13 (+1) | 10 (+0) | 9 (-1) | 11 (+0) | 12 (+1) |\n"
        "| Save: -2 | Save: +1 | Save: +0 | Save: -1 | Save: +0 | Save: +1 |"
    ),
    "Quasit": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 5 (-3) | 17 (+3) | 10 (+0) | 7 (-2) | 10 (+0) | 10 (+0) |\n"
        "| Save: -3 | Save: +3 | Save: +0 | Save: -2 | Save: +0 | Save: +0 |"
    ),
    "Roper": (
        "| STR | DEX | CON | INT | WIS | CHA |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| 18 (+4) | 8 (-1) | 17 (+3) | 7 (-2) | 16 (+3) | 6 (-2) |\n"
        "| Save: +4 | Save: -1 | Save: +3 | Save: -2 | Save: +3 | Save: -2 |"
    ),
}


def get_ground_truth_monster_table(m_name: str, txt_clean: str) -> str | None:
    if m_name in EXPLICIT_TABLES:
        return EXPLICIT_TABLES[m_name]
    queries = [m_name.replace("'", "’"), m_name.replace("’", "'"), m_name]
    if m_name.endswith("s") and not m_name.endswith("ss"):
        queries.append(m_name[:-1])

    for query in queries:
        for start_pos in [2120000, 800000]:
            pos = start_pos
            while True:
                pos = txt_clean.find(query, pos)
                if pos == -1:
                    break
                snippet = txt_clean[pos : pos + 3000]
                str_match = re.search(
                    r"Str\s+(\d+)\s+([+-]?\d+)\s+([+-]?\d+)\s+Dex\s+(\d+)\s+([+-]?\d+)\s+([+-]?\d+)\s+Con\s+(\d+)\s+([+-]?\d+)\s+([+-]?\d+)",
                    snippet,
                    re.I,
                )
                int_match = re.search(
                    r"Int\s+(\d+)\s+([+-]?\d+)\s+([+-]?\d+)\s+Wis\s+(\d+)\s+([+-]?\d+)\s+([+-]?\d+)\s+Cha\s+(\d+)\s+([+-]?\d+)\s+([+-]?\d+)",
                    snippet,
                    re.I,
                )
                if str_match and int_match:
                    sg = str_match.groups()
                    ig = int_match.groups()
                    header = "| STR | DEX | CON | INT | WIS | CHA |"
                    sep = "| :---: | :---: | :---: | :---: | :---: | :---: |"
                    row1 = f"| {sg[0]} ({sg[1]}) | {sg[3]} ({sg[4]}) | {sg[6]} ({sg[7]}) | {ig[0]} ({ig[1]}) | {ig[3]} ({ig[4]}) | {ig[6]} ({ig[7]}) |"
                    row2 = f"| Save: {sg[2]} | Save: {sg[5]} | Save: {sg[8]} | Save: {ig[2]} | Save: {ig[5]} | Save: {ig[8]} |"
                    return f"{header}\n{sep}\n{row1}\n{row2}"
                pos += len(query)
                if pos >= len(txt_clean):
                    break
    return None


def html_to_gfm_table(table_html: str) -> str:
    """Convert an HTML table into a clean, well-aligned Markdown GFM table."""
    if "MOD" in table_html and "SAVE" in table_html and ("STR" in table_html or "Str" in table_html):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", table_html, re.S)
        clean_cells = [re.sub(r"\s+", " ", c).strip() for c in cells]
        abilities = {}
        for ab in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            for idx, c in enumerate(clean_cells):
                if c.upper() == ab and idx + 3 < len(clean_cells):
                    score = clean_cells[idx + 1]
                    mod = clean_cells[idx + 2]
                    save = clean_cells[idx + 3]
                    abilities[ab] = (score, mod, save)
                    break
        if len(abilities) == 6:
            header = "| STR | DEX | CON | INT | WIS | CHA |"
            sep = "| :---: | :---: | :---: | :---: | :---: | :---: |"
            row1 = f"| {abilities['STR'][0]} ({abilities['STR'][1]}) | {abilities['DEX'][0]} ({abilities['DEX'][1]}) | {abilities['CON'][0]} ({abilities['CON'][1]}) | {abilities['INT'][0]} ({abilities['INT'][1]}) | {abilities['WIS'][0]} ({abilities['WIS'][1]}) | {abilities['CHA'][0]} ({abilities['CHA'][1]}) |"
            row2 = f"| Save: {abilities['STR'][2]} | Save: {abilities['DEX'][2]} | Save: {abilities['CON'][2]} | Save: {abilities['INT'][2]} | Save: {abilities['WIS'][2]} | Save: {abilities['CHA'][2]} |"
            return f"{header}\n{sep}\n{row1}\n{row2}"

    rows_raw = re.findall(r"<tr>(.*?)</tr>", table_html, re.S)
    if not rows_raw:
        return ""

    parsed_rows = []
    max_cols = 0
    for r in rows_raw:
        cells_raw = re.findall(r'<td(?:\s+colspan="(\d+)")?[^>]*>(.*?)</td>', r, re.S)
        row_cells = []
        for colspan, val in cells_raw:
            val_clean = re.sub(r"\s+", " ", val).strip().replace("|", "\\|")
            cp = int(colspan) if colspan else 1
            row_cells.append((val_clean, cp))
        total_cols = sum(cp for _, cp in row_cells)
        if total_cols > max_cols:
            max_cols = total_cols
        parsed_rows.append(row_cells)

    if not parsed_rows:
        return ""

    flat_rows = []
    for r in parsed_rows:
        flat_r = []
        for val, cp in r:
            flat_r.append(val)
            for _ in range(cp - 1):
                flat_r.append("")
        while len(flat_r) < max_cols:
            flat_r.append("")
        flat_rows.append(flat_r)

    col_widths = [3] * max_cols
    for r in flat_rows:
        for c_idx, val in enumerate(r):
            if len(val) > col_widths[c_idx]:
                col_widths[c_idx] = len(val)

    lines = []
    hdr = flat_rows[0]
    hdr_line = "| " + " | ".join(val.ljust(col_widths[i]) for i, val in enumerate(hdr)) + " |"
    sep_line = "| " + " | ".join(":---".ljust(col_widths[i], "-") for i in range(max_cols)) + " |"
    lines.append(hdr_line)
    lines.append(sep_line)

    for r in flat_rows[1:]:
        row_line = "| " + " | ".join(val.ljust(col_widths[i]) for i, val in enumerate(r)) + " |"
        lines.append(row_line)

    return "\n".join(lines)


def repair_source_text(md_content: str, txt_content: str = "") -> str:
    res = md_content

    # 1. Glued words
    glued_replacements = [
        ("castLightning", "cast Lightning"),
        ("castPolymorph", "cast Polymorph"),
        ("aBlack Bear", "a Black Bear"),
        ("aGiant Wasp", "a Giant Wasp"),
        ("aFrog", "a Frog"),
    ]
    for old, new in glued_replacements:
        res = res.replace(old, new)

    # 2. HTML entity &#x27; -> typographic apostrophe
    res = res.replace("&#x27;", "’")

    # 3. Currency OCR 'I' -> '1', 'II' -> '11'
    currency_patterns = [
        (r"\bI\s+GP\b", "1 GP"),
        (r"\bII\s+GP\b", "11 GP"),
        (r"\bI\s+SP\b", "1 SP"),
        (r"\bII\s+SP\b", "11 SP"),
        (r"\bI\s+CP\b", "1 CP"),
        (r"\bII\s+CP\b", "11 CP"),
        (r"\bI\s+EP\b", "1 EP"),
        (r"\bII\s+EP\b", "11 EP"),
        (r"\bI\s+PP\b", "1 PP"),
        (r"\bI5\s+GP\b", "15 GP"),
        (r"\bI2\s+GP\b", "12 GP"),
        (r"# Wyvern Poison \(I,200 GP\)", "# Wyvern Poison (1,200 GP)"),
        (r"# Squalid \(I SP per Day\)", "# Squalid (1 SP per Day)"),
        (r"# Modest \(I GP per Day\)", "# Modest (1 GP per Day)"),
    ]
    for pat, rep in currency_patterns:
        res = re.sub(pat, rep, res)

    # 4. Units of time/measurement OCR 'I' -> '1'
    time_patterns = [
        (r"\bCasting Time:\s*I\s+minute\b", "Casting Time: 1 minute"),
        (r"\bDuration:\s*I\s+round\b", "Duration: 1 round"),
        (r"\bDuration:\s*I\s+minute\b", "Duration: 1 minute"),
        (r"\bDuration:\s*I\s+hour\b", "Duration: 1 hour"),
        (r"\bscore by I,", "score by 1,"),
        (r"\bdeals I Bludgeoning damage\b", "deals 1 Bludgeoning damage"),
        (r"\bdeals I Piercing damage\b", "deals 1 Piercing damage"),
        (r"\bdeals I Slashing damage\b", "deals 1 Slashing damage"),
    ]
    for pat, rep in time_patterns:
        res = re.sub(pat, rep, res)

    # 5. Broken line hyphens across paragraphs/newlines
    broken_line_hyphens = [
        (r"dul-\s*\n\s*cimer", "dulcimer"),
        (r"si-\s*\n\s*phon", "siphon"),
        (r"foot-\s*\n\s*wide", "foot-wide"),
        (r"max-\s*\n\s*imum", "maximum"),
        (r"tar-\s*\n\s*get", "target"),
    ]
    for pat, rep in broken_line_hyphens:
        res = re.sub(pat, rep, res)

    # 6. OCR hyphenation anomalies
    ocr_hyphens = [
        (r"\bUn-armed\b", "Unarmed"),
        (r"\bspell-casting\b", "spellcasting"),
        (r"\bspell-caster\b", "spellcaster"),
        (r"\bspell-casters\b", "spellcasters"),
        (r"\bspell-cast\b", "spellcast"),
        (r"\baddi-tional\b", "additional"),
        (r"\badvan-tage\b", "advantage"),
        (r"\bdisadvan-tage\b", "disadvantage"),
        (r"\bcon-centration\b", "concentration"),
        (r"\bpo-tions\b", "potions"),
        (r"\bex-pending\b", "expending"),
        (r"\bchar-acter\b", "character"),
        (r"\bpro-ficiency\b", "proficiency"),
    ]
    for pat, rep in ocr_hyphens:
        res = re.sub(pat, rep, res)

    # 7. Fraction slash normalization
    res = res.replace("11⁄2 mph", "1 1/2 mph").replace("21⁄2 mph", "2 1/2 mph")

    # 8. Escaped characters cleanup (\- and \*)
    res = re.sub(r"(?m)^\\-\s+", "- ", res)
    res = res.replace(r"\*", "*")

    # 9. Numbered headings and trailing periods
    heading_patterns = [
        (r"^# Step I: Choose Class", "# Step 1: Choose Class"),
        (r"^# Tier I \(Levels I–4\)", "# Tier 1 (Levels 1–4)"),
        (r"^# I: Choose Abilities", "# 1: Choose Abilities"),
        (r"^# Step I: Choose a Difficulty", "# Step 1: Choose a Difficulty"),
        (r"^# Attack Deflection \(Quarterstaff Form Only\)\.$", "# Attack Deflection (Quarterstaff Form Only)"),
    ]
    for pat, rep in heading_patterns:
        res = re.sub(pat, rep, res, flags=re.MULTILINE)

    # 10. Spell header fixes: Component: -> Components:
    res = re.sub(r"(?m)^Component:\s*([VSM])", r"Components: \1", res)

    # 11. Spurious headings in spell blocks and monster blocks
    spurious_headings = [
        (r"(?m)^# Components:\s*([^\n]+)$", r"Components: \1"),
        (r"(?m)^# Resistances Cold$", r"Resistances Cold"),
        (r"(?m)^# Resistances Acid$", r"Resistances Acid"),
        (r"(?m)^# Senses Passive Perception 10$", r"Senses Passive Perception 10"),
    ]
    for pat, rep in spurious_headings:
        res = re.sub(pat, rep, res)

    # 12. Unicode bullet character normalization
    res = re.sub(r"(?m)^•\s+", "- ", res)

    # 13. Sidebar splices repair
    old_rhythm = """This pattern holds during every game session (each time you sit down to play D&D), whether the

# EXCEPTIONS SUPERSEDE GENERAL RULES

General rules govern each part of the game. For example, the combat rules tell you that melee attacks use Strength and ranged attacks use Dexterity. That's a general rule, and a general rule is in effect as long as something in the game doesn't explicitly say otherwise.

The game also includes elements - class features, feats, weapon properties, spells, magic items, monster abilities, and the like - that sometimes contradict a general rule. When an exception and a general rule disagree, the exception wins. For example, if a feature says you can make melee attacks using your Charisma, you can do so, even though that statement disagrees with the general rule.

adventurers are talking to a noble, exploring a ruin, or fighting a dragon. In certain situations - particularly combat - the action is more structured, and everyone takes turns."""

    new_rhythm = """This pattern holds during every game session (each time you sit down to play D&D), whether the adventurers are talking to a noble, exploring a ruin, or fighting a dragon. In certain situations - particularly combat - the action is more structured, and everyone takes turns.

# Exceptions Supersede General Rules

General rules govern each part of the game. For example, the combat rules tell you that melee attacks use Strength and ranged attacks use Dexterity. That's a general rule, and a general rule is in effect as long as something in the game doesn't explicitly say otherwise.

The game also includes elements - class features, feats, weapon properties, spells, magic items, monster abilities, and the like - that sometimes contradict a general rule. When an exception and a general rule disagree, the exception wins. For example, if a feature says you can make melee attacks using your Charisma, you can do so, even though that statement disagrees with the general rule."""

    res = res.replace(old_rhythm, new_rhythm)

    old_adv = """# Advantage/Disadvantage

Sometimes a D20 Test is modified by Advantage or Disadvantage. Advantage reflects the positive circumstances surrounding a d20 roll, while Disadvantage reflects negative circumstances.

You usually acquire Advantage or Disadvantage through the use of special abilities and actions. The

# HEROIC INSPIRATION

Sometimes the GM or a rule gives you Heroic Inspiration. If you have Heroic Inspiration, you can expend it to reroll any die immediately after rolling it, and you must use the new roll.

Only One at a Time. You can never have more than one instance of Heroic Inspiration. If something gives you Heroic Inspiration and you already have it, you can give it to a player character in your group who lacks it.

Gaining Heroic Inspiration. Your GM can give you Heroic Inspiration for a variety of reasons. Typically, GMs award it when you do something particularly heroic, in character, or entertaining. It's a reward for making the game more fun for everyone playing.

Other rules might allow your character to gain Heroic Inspiration independent of the GM's decision. For example, Human characters start each day with Heroic Inspiration.

GM can also decide that circumstances grant Advantage or impose Disadvantage."""

    new_adv = """# Advantage/Disadvantage

Sometimes a D20 Test is modified by Advantage or Disadvantage. Advantage reflects the positive circumstances surrounding a d20 roll, while Disadvantage reflects negative circumstances.

You usually acquire Advantage or Disadvantage through the use of special abilities and actions. The GM can also decide that circumstances grant Advantage or impose Disadvantage.

# Heroic Inspiration

Sometimes the GM or a rule gives you Heroic Inspiration. If you have Heroic Inspiration, you can expend it to reroll any die immediately after rolling it, and you must use the new roll.

Only One at a Time. You can never have more than one instance of Heroic Inspiration. If something gives you Heroic Inspiration and you already have it, you can give it to a player character in your group who lacks it.

Gaining Heroic Inspiration. Your GM can give you Heroic Inspiration for a variety of reasons. Typically, GMs award it when you do something particularly heroic, in character, or entertaining. It's a reward for making the game more fun for everyone playing.

Other rules might allow your character to gain Heroic Inspiration independent of the GM's decision. For example, Human characters start each day with Heroic Inspiration."""

    res = res.replace(old_adv, new_adv)

    old_hp = """# Hit Points

Hit Points represent durability and the will to live. Creatures with more Hit Points are more difficult to kill. Your Hit Point maximum is the number of

# RESTING

Adventurers can't spend every hour adventuring. They need rest. Any creature can take hour-long Short Rests in the midst of a day and an 8-hour Long Rest to end it. Regaining Hit Points is one of the main benefits of a rest. “Rules Glossary” provides the rules for Short and Long Rests.

Hit Points you have when uninjured. Your current Hit Points can be any number from that maximum down to 0, which is the lowest Hit Points can go.

Whenever you take damage, subtract it from your Hit Points. Hit Point loss has no effect on your capabilities until you reach 0 Hit Points.

If you have half your Hit Points or fewer, you're Bloodied, which has no game effect on its own but which might trigger other game effects."""

    new_hp = """# Hit Points

Hit Points represent durability and the will to live. Creatures with more Hit Points are more difficult to kill. Your Hit Point maximum is the number of Hit Points you have when uninjured. Your current Hit Points can be any number from that maximum down to 0, which is the lowest Hit Points can go.

Whenever you take damage, subtract it from your Hit Points. Hit Point loss has no effect on your capabilities until you reach 0 Hit Points.

If you have half your Hit Points or fewer, you're Bloodied, which has no game effect on its own but which might trigger other game effects.

# Resting

Adventurers can't spend every hour adventuring. They need rest. Any creature can take hour-long Short Rests in the midst of a day and an 8-hour Long Rest to end it. Regaining Hit Points is one of the main benefits of a rest. “Rules Glossary” provides the rules for Short and Long Rests."""

    res = res.replace(old_hp, new_hp)

    # 14. Broken sentence cuts across paragraphs
    broken_sentence_joins = [
        (r"(?m)(your)\n\n(choice of Acid)", r"\1 \2"),
        (r"(?m)(and the)\n\n(target takes)", r"\1 \2"),
        (r"(?m)(The)\n\n(target must succeed)", r"\1 \2"),
        (r"(?m)(returns to)\n\n(the creature's body)", r"\1 \2"),
        (r"(?m)(see through the)\n\n(image, and its other)", r"\1 \2"),
        (r"(?m)(against the)\n\n(target\.)", r"\1 \2"),
        (r"(?m)(succeed on a)\n\n(Dexterity saving throw)", r"\1 \2"),
        (r"(?m)(any creature that)\n\n(hears you and knows)", r"\1 \2"),
        (r"(?m)(speak the)\n\n(creature's name)", r"\1 \2"),
        (r"(?m)(steps on the)\n\n(trap)", r"\1 \2"),
        (r"(?m)(Any effect that)\n\n(cures the Poisoned)", r"\1 \2"),
        (r"(?m)(over your)\n\n(head as a)", r"\1 \2"),
        (r"(?m)(that)\n\n(is within 5 feet)", r"\1 \2"),
        (r"(?m)(or)\n\n(if the space is)", r"\1 \2"),
        (r"(?m)(Bonus Action to)\n\n(cause the armor)", r"\1 \2"),
        (r"(?m)(creates an)\n\n(extradimensional hole)", r"\1 \2"),
        (r"(?m)(the)\n\n(caster must make a saving throw)", r"\1 \2"),
        (r"(?m)(used in a)\n\n(location that has no)", r"\1 \2"),
        (r"(?m)(make the)\n\n(blade disappear\.)", r"\1 \2"),
        (r"(?m)(to)\n\n(a maximum of 30\.)", r"\1 \2"),
        (r"(?m)(A monster with)\n\n(a class tag after its)", r"\1 \2"),
        (r"(?m)(Bludgeoning damage, and)\n\n(the target has the Prone)", r"\1 \2"),
        (r"(?m)(Verbal component and)\n\n(takes 7 \(2d6\) Thunder damage)", r"\1 \2"),
        (r"(?m)(the target has the)\n\n(Prone condition, and the allosaurus)", r"\1 \2"),
        (r"(?m)(each of the toad's turns\. The)\n\n(toad can have only one)", r"\1 \2"),
    ]
    for pat, rep in broken_sentence_joins:
        res = re.sub(pat, rep, res)

    # 15. Relocate Class Feature tables to # <Class> Class Features
    classes_to_relocate = [
        "Barbarian", "Bard", "Cleric", "Druid", "Fighter",
        "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard"
    ]
    for cls in classes_to_relocate:
        tbl_name = f"{cls} Features"
        m = re.search(rf"\n({re.escape(tbl_name)}\n\n\|.+?\n\n)", res, re.S)
        if not m:
            m = re.search(rf"\n({re.escape(tbl_name)}\n\|.+?\n\n)", res, re.S)
        if m:
            full_table = m.group(1).strip()
            target_heading = f"# {cls} Class Features"
            target_pos = res.find(target_heading)
            # Only relocate if table is currently after the target heading's first section
            if target_pos != -1 and m.start(1) > target_pos + len(target_heading) + 300:
                res = res[:m.start(1)] + res[m.end(1):]
                end_para = res.find("\n\n", target_pos + len(target_heading) + 2)
                if end_para != -1:
                    insert_pos = end_para + 2
                    res = res[:insert_pos] + full_table + "\n\n" + res[insert_pos:]

    cleanups = [
        ("As a Bonus Action, you can enter a Rage if you aren't wearing Heavy armor.\n\nWhile active, your Rage follows the rules below.",
         "As a Bonus Action, you can enter a Rage if you aren't wearing Heavy armor. While active, your Rage follows the rules below."),
        ("That creature gains\n\none of your Bardic Inspiration dice.",
         "That creature gains one of your Bardic Inspiration dice."),
        ("Guidance, Sacred Flame, and Thaumaturgy are recommended.\n\nWhen you reach Cleric levels 4 and 10",
         "Guidance, Sacred Flame, and Thaumaturgy are recommended. When you reach Cleric levels 4 and 10"),
        ("The rules below describe\n\nhow you use those rules with Druid spells",
         "The rules below describe how you use those rules with Druid spells"),
        ("up to the maximum amount remaining in\n\nyour pool.",
         "up to the maximum amount remaining in your pool."),
        ("The rules below describe\n\nhow you use those rules with Ranger spells",
         "The rules below describe how you use those rules with Ranger spells"),
        ("Once per turn, you can deal an extra 1d6 damage to one creature you hit with an attack\n\nroll if you have Advantage on the roll",
         "Once per turn, you can deal an extra 1d6 damage to one creature you hit with an attack roll if you have Advantage on the roll"),
        ("The Sorcerer Features table shows how many spell slots you have to cast your level 1+\n\nspells. You regain all expended slots when you finish a Long Rest.",
         "The Sorcerer Features table shows how many spell slots you have to cast your level 1+ spells. You regain all expended slots when you finish a Long Rest."),
        ("replace it with another invocation for which you\n\nqualify.",
         "replace it with another invocation for which you qualify."),
        ("Light, Mage Hand, and Ray of Frost are recommended.\n\nWhen you reach Wizard levels 4 and 10",
         "Light, Mage Hand, and Ray of Frost are recommended. When you reach Wizard levels 4 and 10"),
    ]
    for old_s, new_s in cleanups:
        res = res.replace(old_s, new_s)

    # 16. Chapter separators
    chapters = [
        "Playing the Game", "Character Creation", "Classes", "Character Origins",
        "Feats", "Equipment", "Spells", "Rules Glossary", "Gameplay Toolbox",
        "Magic Items", "Monsters", "Monsters A-Z", "Animals"
    ]
    for ch in chapters:
        res = re.sub(rf"(?<!---)\n\n# {re.escape(ch)}\n", f"\n\n---\n\n# {ch}\n", res)

    # 17. Table of Contents clean list formatting
    toc_start = res.find("# Contents")
    toc_end = res.find("---\n\n# Playing the Game")
    if toc_start != -1 and toc_end != -1:
        new_toc = """# Contents

- [1. Playing the Game](#playing-the-game)
- [2. Character Creation](#character-creation)
- [3. Classes](#classes)
- [4. Character Origins](#character-origins)
- [5. Feats](#feats)
- [6. Equipment](#equipment)
- [7. Spells](#spells)
- [8. Rules Glossary](#rules-glossary)
- [9. Gameplay Toolbox](#gameplay-toolbox)
- [10. Magic Items](#magic-items)
- [11. Monsters](#monsters)
  - [Monsters A–Z](#monsters-a-z)
  - [Animals](#animals)

"""
        res = res[:toc_start] + new_toc + res[toc_end:]

    # 18. LaTeX Math and Math-mode cleanup
    latex_patterns = [
        (r"\$1\+\$", "1+"),
        (r"\$2\+\$", "2+"),
        (r"\$C\$", "C"),
        (r"\$R\$", "R"),
        (r"\$M\$", "M"),
        (r"\$\s*10\s*\+\s*2\s*\+\s*2\s*\$", "10 + 2 + 2"),
        (r"\$\s*10d6\s*\+\s*40\s*\$", "10d6 + 40"),
        (r"\$\s*1d4\s*\+\s*1\s*\$", "1d4 + 1"),
        (r"\$\s*1d4\s*\+\s*3\s*\$", "1d4 + 3"),
        (r"\$\s*2d4\s*\+\s*2\s*\$", "2d4 + 2"),
        (r"\$\s*1d6\s*\+\s*6\s*\$", "1d6 + 6"),
        (r"\$\s*1d6\s*\+\s*1\s*\$", "1d6 + 1"),
        (r"\$\s*3d10\s*\\times\s*10\s*\$", "3d10 × 10"),
        (r"\$\s*1d10\s*\\times\s*10\s*\$", "1d10 × 10"),
        (r"\$\s*1\\mathrm\{d\}10\s*\\times\s*10\s*\$", "1d10 × 10"),
        (r"\$\s*2\\mathrm\{d\}8\s*\+\s*2\s*\$", "2d8 + 2"),
        (r"\$\s*1d4\s*\\times\s*10\s*\$", "1d4 × 10"),
        (r"\$\s*50\s*\\times\s*4\s*\$", "50 × 4"),
        (r"\$\s*225\s*\\times\s*5\s*\$", "225 × 5"),
        (r"\$\s*7,800\s*\\times\s*6\s*\$", "7,800 × 6"),
        (r"\$\^\{†\}\$", "†"),
        (
            r"\$\$\n\\begin\{array\}\{l\}.*?\\end\{array\}\n\$\$",
            "Melee attack bonus = Strength modifier + Proficiency Bonus\n\nRanged attack bonus = Dexterity modifier + Proficiency Bonus",
            re.S,
        ),
        (r"\$\s*\\frac\{1\}\{2\}\s*\$", "1/2"),
        (r"\$\s*1\\frac\{1\}\{2\}\s*\$", "1 1/2"),
        (r"\$\s*2\\frac\{1\}\{2\}\s*\$", "2 1/2"),
        (r"\$\s*3\\frac\{1\}\{2\}\s*\$", "3 1/2"),
        (r"\$\s*4\\frac\{1\}\{2\}\s*\$", "4 1/2"),
        (r"\$\s*5\\frac\{1\}\{2\}\s*\$", "5 1/2"),
        (r"\$\s*6\\frac\{1\}\{2\}\s*\$", "6 1/2"),
        (r"\$\s*10\\frac\{1\}\{2\}\s*\$", "10 1/2"),
        (r"\$\s*58\\frac\{1\}\{2\}\s*\$", "58 1/2"),
    ]
    for item in latex_patterns:
        if len(item) == 3:
            pat, rep, flags = item
            res = re.sub(pat, rep, res, flags=flags)
        else:
            pat, rep = item
            res = re.sub(pat, rep, res)

    # 19. HTML tables to GFM pipe tables conversion
    if "<table>" in res:
        txt_clean = txt_content.replace("−", "-").replace("\t", " ")
        all_tbl_matches = list(re.finditer(r"<table>.*?</table>", res, re.S))
        replacements = []
        for t_match in all_tbl_matches:
            t_text = t_match.group(0)
            start_pos = t_match.start()
            end_pos = t_match.end()
            if "MOD" in t_text and "SAVE" in t_text:
                m = re.findall(r"# ([^\n]+)", res[:start_pos])
                owner = m[-1] if m else "Unknown"
                if owner in [
                    "Traits",
                    "Actions",
                    "Bonus Actions",
                    "Reactions",
                    "Stat Block Overview",
                    "Parts of a Stat Block",
                ]:
                    for h in reversed(m):
                        if h not in [
                            "Traits",
                            "Actions",
                            "Bonus Actions",
                            "Reactions",
                            "Stat Block Overview",
                            "Parts of a Stat Block",
                        ]:
                            owner = h
                            break
                truth_tbl = get_ground_truth_monster_table(owner, txt_clean)
                if truth_tbl:
                    replacements.append((start_pos, end_pos, truth_tbl))
                else:
                    gfm = html_to_gfm_table(t_text)
                    if gfm:
                        replacements.append((start_pos, end_pos, gfm))
            else:
                gfm = html_to_gfm_table(t_text)
                if gfm:
                    replacements.append((start_pos, end_pos, gfm))

        for sp, ep, gfm_tbl in reversed(replacements):
            res = res[:sp] + gfm_tbl + res[ep:]

    # 20. Compact monster stat blocks
    res = re.sub(r"(?m)^(AC [^\n]+)\n\n(Initiative [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Initiative [^\n]+)\n\n(HP [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(HP [^\n]+)\n\n(Speed [^\n]+)", r"\1\n\2", res)
    for t1 in ["Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear", "Senses", "Languages"]:
        for t2 in ["Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear", "Senses", "Languages", "CR"]:
            res = re.sub(rf"(?m)^({t1} [^\n]+)\n\n({t2} [^\n]+)", r"\1\n\2", res)

    # 21. Compact spell blocks
    res = re.sub(r"(?m)^(Casting Time: [^\n]+)\n\n(Range: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Range: [^\n]+)\n\n(Components: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Components: [^\n]+)\n\n(Duration: [^\n]+)", r"\1\n\2", res)

    # 22. Replace all em-dashes context-sensitively
    res_lines_em = []
    for line in res.splitlines():
        if "—" not in line:
            res_lines_em.append(line)
            continue
        if line.strip().startswith("|"):
            cells = line.split("|")
            new_cells = []
            for c in cells:
                c_strip = c.strip()
                if c_strip == "—":
                    pad_len = len(c)
                    new_cell = " - ".center(pad_len) if pad_len > 3 else " - "
                    new_cells.append(new_cell)
                elif "—" in c:
                    c_rep = c.replace("——", "--").replace("—", "-")
                    new_cells.append(c_rep)
                else:
                    new_cells.append(c)
            res_lines_em.append("|".join(new_cells))
        else:
            line_rep = re.sub(r"\s*—\s*", " - ", line)
            res_lines_em.append(line_rep)
    res = "\n".join(res_lines_em) + "\n"

    # 23. Strip trailing whitespaces from every line
    res_lines = [l.rstrip() for l in res.splitlines()]
    res = "\n".join(res_lines) + "\n"

    # Normalize multiple blank lines
    res = re.sub(r"\n{3,}", "\n\n", res)
    return res


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair, format tables, and normalize layout in SRD_CC_v5.2.1.md"
    )
    parser.add_argument("--source-md", default="SRD_CC_v5.2.1.md")
    parser.add_argument("--source-txt", default="SRD_CC_v5.2.1.txt")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    md_path = Path(args.source_md)
    txt_path = Path(args.source_txt)

    if not md_path.exists():
        sys.exit(f"Source markdown {md_path} not found.")

    md_content = md_path.read_text(encoding="utf-8")
    txt_content = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""

    repaired = repair_source_text(md_content, txt_content)

    if repaired == md_content:
        print("Source file is already clean, normalized, and formatted. No changes made.")
    else:
        if args.dry_run:
            print("Changes detected (dry-run).")
        else:
            md_path.write_text(repaired, encoding="utf-8")
            print(f"Repaired and reformatted {md_path} successfully.")


if __name__ == "__main__":
    main()
