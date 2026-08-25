"""Authoritative ground-truth source repair, table, and layout normalization for SRD_CC_v5.2.1.md.

Cross-checks and normalizes MinerU OCR/conversion defects in SRD_CC_v5.2.1.md
using the owner-keyed official-PDF registry in scripts/data/,
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

from pdf_parity import apply_registered_stat_blocks, format_stat_table, load_registry


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


def repair_source_text(md_content: str) -> str:
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
        (r"\bhand-held\b", "handheld"),
        (r"\bGreat-axes\b", "Greataxes"),
        (r"\bspell-casting\b", "spellcasting"),
        (r"\bspell-caster\b", "spellcaster"),
        (r"\bspell-casters\b", "spellcasters"),
        (r"\bspell-cast\b", "spellcast"),
        (r"\bcan-trip\b", "cantrip"),
        (r"\bMeta-magic\b", "Metamagic"),
        (r"\btab-ard\b", "tabard"),
        (r"\bAc-robatics\b", "Acrobatics"),
        (r"\bir-relevant\b", "irrelevant"),
        (r"\bin-tangible\b", "intangible"),
        (r"\bdemi-plane\b", "demiplane"),
        (r"\bextra-dimensional\b", "extradimensional"),
        (r"\bextradi-dimensional\b", "extradimensional"),
        (r"\botyu-ghs\b", "otyughs"),
        (r"\bmid-size\b", "midsize"),
        (r"\bThunder-wave\b", "Thunderwave"),
        (r"\bthunder-clap\b", "thunderclap"),
        (r"\btrap-door\b", "trapdoor"),
        (r"\bLong-strider\b", "Longstrider"),
        (r"\bEl-dritch\b", "Eldritch"),
        (r"\bwere-boar\b", "wereboar"),
        (r"\bre-roll\b", "reroll"),
        (r"\bre-gains\b", "regains"),
        (r"\bShort-word\b", "Shortsword"),
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
    res = res.replace("be jeweled", "bejeweled")
    res = res.replace("Poisson damage", "Poison damage")
    res = res.replace("level I+ Wizard spell", "level 1+ Wizard spell")
    res = res.replace("(I Copper Piece)", "(1 Copper Piece)")
    res = res.replace("worth I+ CP", "worth 1+ CP")
    res = re.sub(r"\bl-(ounce|pound|inch)\b", r"1-\1", res)
    res = res.replace(
        "any souls the bag is holding are released. The bag can create a new bag",
        "any souls the bag is holding are released. The hag can create a new bag",
    )

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
        registered_stat_blocks = load_registry()["statBlocks"]
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
                if owner in registered_stat_blocks:
                    replacements.append(
                        (
                            start_pos,
                            end_pos,
                            format_stat_table(registered_stat_blocks[owner]),
                        )
                    )
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

    # 21b. Cross-column relocation and wrapped-descriptor repairs (2026-08-24).
    # Registered as `cross-column-splice-repairs-2026-08-24` in
    # objects/sources/extraction-overrides.json.

    # Dispel Magic: the spell descriptor's class parenthetical wraps across a
    # column break, splitting one printed line into two paragraphs and hiding
    # the spell from descriptor detection.
    res = res.replace(
        "# Dispel Magic\n\n"
        "Level 3 Abjuration (Bard, Cleric, Druid, Paladin,\n\n"
        "Ranger, Sorcerer, Warlock, Wizard)",
        "# Dispel Magic\n\n"
        "Level 3 Abjuration (Bard, Cleric, Druid, Paladin, "
        "Ranger, Sorcerer, Warlock, Wizard)",
    )
    if (
        "# Dispel Magic\n\nLevel 3 Abjuration (Bard, Cleric, Druid, Paladin, "
        "Ranger, Sorcerer, Warlock, Wizard)"
        not in res
    ):
        raise RuntimeError("Dispel Magic descriptor repair anchor drifted")

    # Fiendish Legacies: the two-column page layout drops the Tiefling's
    # legacy table into the Human species entry. Restore it to the Tiefling's
    # Fiendish Legacy trait, which references it.
    legacy_anchor = (
        "Intelligence, Wisdom, or Charisma is your spellcasting ability for "
        "the spells you cast with this trait (choose the ability when you "
        "select the legacy).\n\nOtherworldly Presence."
    )
    origins_start = res.find("\n# Character Origins\n")
    origins_end = res.find("\n---\n\n# Feats\n", origins_start)
    origins = res[origins_start:origins_end] if origins_start >= 0 and origins_end > origins_start else ""
    legacy_match = re.search(
        r"\nFiendish Legacies\n\n\| Legacy.*?\n(?=\n# Orc\n)", origins, re.S
    )
    if legacy_match:
        legacy_match = re.search(re.escape(legacy_match.group(0)), res)
    if legacy_match and legacy_anchor in res:
        legacy_table = legacy_match.group(0).strip("\n")
        res = res[: legacy_match.start()] + res[legacy_match.end() :]
        res = res.replace(
            legacy_anchor,
            legacy_anchor.replace(
                "\n\nOtherworldly Presence.",
                f"\n\n{legacy_table}\n\nOtherworldly Presence.",
            ),
        )
    tiefling_start = res.find("\n# Tiefling\n")
    species_end = res.find("\n---\n\n# Feats\n", tiefling_start)
    legacy_pos = res.find("\nFiendish Legacies\n", tiefling_start)
    if not (0 <= tiefling_start < legacy_pos < species_end):
        raise RuntimeError("Fiendish Legacies relocation anchor drifted")

    # Travel Terrain: the same layout artifact drops the Gameplay Toolbox
    # travel table into the "1: Choose Abilities" background-creation step.
    # Restore it to the Travel Pace section, which references it.
    travel_anchor = (
        "as shown in the Maximum Pace column of the Travel Terrain table. "
        "Certain factors can affect a group’s travel pace.\n\n# Good Roads"
    )
    origins_start = res.find("\n# Character Origins\n")
    origins_end = res.find("\n---\n\n# Feats\n", origins_start)
    origins = res[origins_start:origins_end] if origins_start >= 0 and origins_end > origins_start else ""
    travel_match = re.search(
        r"\nTravel Terrain\n\n\| Terrain.*?\n† Characters[^\n]*\n", origins, re.S
    )
    if travel_match:
        travel_match = re.search(re.escape(travel_match.group(0)), res)
    if travel_match and travel_anchor in res:
        travel_table = travel_match.group(0).strip("\n")
        res = res[: travel_match.start()] + res[travel_match.end() :]
        res = res.replace(
            travel_anchor,
            travel_anchor.replace(
                "\n\n# Good Roads",
                f"\n\n{travel_table}\n\n# Good Roads",
            ),
        )
    travel_pace_start = res.find("\n# Travel Pace\n")
    good_roads_start = res.find("\n# Good Roads\n", travel_pace_start)
    travel_table_pos = res.find("\nTravel Terrain\n", travel_pace_start)
    if not (0 <= travel_pace_start < travel_table_pos < good_roads_start):
        raise RuntimeError("Travel Terrain relocation anchor drifted")

    # 21c. Residual cross-record and split-table repairs (2026-08-25).
    # Registered as `residual-structure-repairs-2026-08-25` in
    # objects/sources/extraction-overrides.json.

    # Figurine of Wondrous Power: its accompanying Giant Fly stat block was
    # printed between the Ebony Fly and Golden Lions variant descriptions.
    # Keeping that physical column-flow order makes the heading parser attach
    # every later figurine variant to the monster. Move the verbatim stat block
    # after the final Silver Raven variant so each record owns its prose.
    giant_fly_match = re.search(
        r"\n# Giant Fly\n\nLarge Beast, Unaligned\n\n"
        r"AC 11\nInitiative \+1 \(11\)\nHP 19 \(3d10 \+ 3\)\n"
        r"Speed 30 ft\., Fly 60 ft\.\n\n"
        r"\| STR \| DEX \| CON \| INT \| WIS \| CHA \|.*?"
        r"CR 0 \(XP 0; PB \+2\)\n",
        res,
        re.S,
    )
    golden_lions_pos = res.find("\nGolden Lions (Rare).")
    if giant_fly_match and 0 <= golden_lions_pos > giant_fly_match.start():
        giant_fly_block = giant_fly_match.group(0).strip("\n")
        res = res[: giant_fly_match.start()] + res[giant_fly_match.end() :]
        flame_tongue_anchor = "\n\n# Flame Tongue"
        if flame_tongue_anchor not in res:
            raise RuntimeError("Giant Fly repair anchor '# Flame Tongue' drifted")
        res = res.replace(
            flame_tongue_anchor,
            f"\n\n{giant_fly_block}{flame_tongue_anchor}",
            1,
        )

    # Trinkets: rows 35-100 were converted as plain paragraphs across two
    # column-flow headings. They are already-present source text, so convert
    # only their representation and append them to the existing GFM table.
    trinket_start = res.find("\n\n# 1d100 Trinket\n\n35 ")
    if trinket_start != -1:
        trinket_end_marker = "\n\n---\n\n# Classes"
        trinket_end = res.find(trinket_end_marker, trinket_start)
        if trinket_end == -1:
            raise RuntimeError("Trinkets repair anchor '# Classes' drifted")
        trinket_fragment = res[trinket_start:trinket_end]
        trinket_rows = re.findall(r"(?m)^(\d{2}) (.+)$", trinket_fragment)
        expected_rolls = [f"{value:02d}" for value in range(35, 100)] + ["00"]
        if [roll for roll, _ in trinket_rows] != expected_rolls:
            raise RuntimeError("Trinkets continuation no longer contains rows 35-00")
        rendered_rows = "\n".join(
            f"| {roll} | {text} |" for roll, text in trinket_rows
        )
        res = res[:trinket_start] + "\n" + rendered_rows + res[trinket_end:]
    res = re.sub(r"(?m)^(\| 34 .* \|)\n\n(?=\| 35 \|)", r"\1\n", res)

    # Prismatic Spray: rows 5-8 suffered the same conversion artifact. Fold
    # the four verbatim paragraphs into the preceding Prismatic Rays table.
    rays_start = res.find("\n\n# 1d8 Ray\n\n5 ")
    if rays_start != -1:
        rays_end_marker = "\n\n# Prismatic Wall"
        rays_end = res.find(rays_end_marker, rays_start)
        if rays_end == -1:
            raise RuntimeError("Prismatic Rays repair anchor drifted")
        rays_fragment = res[rays_start:rays_end]
        ray_rows = re.findall(r"(?m)^([5-8]) (.+)$", rays_fragment)
        if [roll for roll, _ in ray_rows] != ["5", "6", "7", "8"]:
            raise RuntimeError("Prismatic Rays continuation no longer contains rows 5-8")
        rendered_rows = "\n".join(
            f"| {roll} | {text} |" for roll, text in ray_rows
        )
        res = res[:rays_start] + "\n" + rendered_rows + res[rays_end:]
    res = re.sub(r"(?m)^(\| 4 .* \|)\n\n(?=\| 5 \| Blue\.)", r"\1\n", res)

    # 21d. Complete the remaining registered source-structure repairs
    # (2026-08-25).  Every transformation below is an ownership/layout repair
    # over text already present in the official PDF; no rules content is
    # synthesized here.

    # Sidebar boxes in the two-column source interrupt their owning sentence.
    # Put each complete prose tail back before the sidebar heading.
    making_attack = re.compile(
        r"(# Making an Attack\n\n.*?fire a Ranged weapon,)\n\n"
        r"# UNSEEN ATTACKERS AND TARGETS\n\n(.*?)\n\n"
        r"(or make an attack roll as part of a spell,.*?instead of damage\.)"
        r"\n\n(?=# Cover\n)",
        re.S,
    )
    res, count = making_attack.subn(
        lambda m: f"{m.group(1)} {m.group(3)}\n\n"
        f"# Unseen Attackers and Targets\n\n{m.group(2)}\n\n",
        res,
    )
    if count > 1 or "fire a Ranged weapon,\n\n# UNSEEN" in res:
        raise RuntimeError("Making an Attack sidebar repair drifted")

    alignments = re.compile(
        r"(# The Nine Alignments\n\n.*?don't take sides,)\n\n"
        r"# UNALIGNED CREATURES\n\n(.*?)\n\n"
        r"(doing what seems best at the time\..*?schemes of vengeance and havoc\.)"
        r"\n\n(?=# Step 5: Character Creation Details\n)",
        re.S,
    )
    res, count = alignments.subn(
        lambda m: f"{m.group(1)} {m.group(3)}\n\n"
        f"# Unaligned Creatures\n\n{m.group(2)}\n\n",
        res,
    )
    if count == 0:
        section_start = res.find("# The Nine Alignments\n")
        sidebar_start = res.find("\n\n# UNALIGNED CREATURES\n\n", section_start)
        tail_start = res.find("\n\ndoing what seems best at the time.", sidebar_start)
        section_end = res.find("\n\n# Step 5: Character Creation Details\n", tail_start)
        if 0 <= section_start < sidebar_start < tail_start < section_end:
            sidebar = res[
                sidebar_start + len("\n\n# UNALIGNED CREATURES\n\n") : tail_start
            ].strip()
            tail = res[tail_start:section_end].strip()
            res = (
                res[:sidebar_start]
                + " "
                + tail
                + "\n\n# Unaligned Creatures\n\n"
                + sidebar
                + res[section_end:]
            )
            count = 1
    if count > 1 or "don't take sides,\n\n# UNALIGNED" in res:
        raise RuntimeError("Nine Alignments sidebar repair drifted")

    wizard_sidebar = re.compile(
        r"(# Level 3: Wizard Subclass\n\n.*?For the rest)\n\n"
        r"# EXPANDING AND REPLACING A SPELLBOOK\n\n(.*?)\n\n"
        r"(of your career, you gain each of your subclass's features that are of your Wizard level or lower\.)"
        r"\n\n(?=# Level 4: Ability Score Improvement\n)",
        re.S,
    )
    res, count = wizard_sidebar.subn(
        lambda m: f"{m.group(1)} {m.group(3)}\n\n"
        f"# Expanding and Replacing a Spellbook\n\n{m.group(2)}\n\n",
        res,
    )
    if count == 0:
        feature_start = res.find("# Level 3: Wizard Subclass\n")
        sidebar_start = res.find(
            "\n\n# EXPANDING AND REPLACING A SPELLBOOK\n\n", feature_start
        )
        tail_start = res.find("\n\nof your career,", sidebar_start)
        feature_end = res.find("\n\n# Level 4: Ability Score Improvement\n", tail_start)
        if 0 <= feature_start < sidebar_start < tail_start < feature_end:
            sidebar = res[
                sidebar_start
                + len("\n\n# EXPANDING AND REPLACING A SPELLBOOK\n\n") : tail_start
            ].strip()
            tail = res[tail_start:feature_end].strip()
            res = (
                res[:sidebar_start]
                + " "
                + tail
                + "\n\n# Expanding and Replacing a Spellbook\n\n"
                + sidebar
                + res[feature_end:]
            )
            count = 1
    if count > 1 or "For the rest\n\n# EXPANDING" in res:
        raise RuntimeError("Wizard subclass sidebar repair drifted")

    # Conversion-only headings promoted from display or wrapped lines.
    res = res.replace(
        '\n\n# Shrub or Awakened Tree in "Monsters."\n\n',
        ' Shrub or Awakened Tree in "Monsters."\n\n',
    )
    res = res.replace(
        "# Curses and\n\n# Magical Contagions",
        "# Curses and Magical Contagions",
    )
    res = re.sub(
        r"(?m)^# (Passive Perception = 10 \+ Wisdom \(Perception\) check modifier)$",
        r"\1",
        res,
    )
    res = re.sub(r"(?m)^# (Casting Time: Action)$", r"\1", res)

    # Join repeated column fragments that are direct continuations of the
    # same GFM table. Differently shaped adjacent tables (for example the two
    # Control Weather tables) remain separate.
    def table_key(line: str) -> tuple[str, ...]:
        return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))

    def is_pipe(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|")

    def is_delimiter(line: str) -> bool:
        return is_pipe(line) and all(
            re.fullmatch(r":?-{3,}:?", cell)
            for cell in table_key(line)
        )

    source_lines = res.splitlines()
    merged_lines = []
    active_header = None
    index = 0
    while index < len(source_lines):
        line = source_lines[index]
        if is_pipe(line):
            if index + 1 < len(source_lines) and is_delimiter(source_lines[index + 1]):
                active_header = table_key(line)
                merged_lines.extend((line, source_lines[index + 1]))
                index += 2
                continue
            merged_lines.append(line)
            index += 1
            continue
        if (
            not line.strip()
            and active_header is not None
            and index + 2 < len(source_lines)
            and is_pipe(source_lines[index + 1])
            and is_delimiter(source_lines[index + 2])
            and table_key(source_lines[index + 1]) == active_header
        ):
            index += 3
            continue
        merged_lines.append(line)
        if line.strip():
            active_header = None
        else:
            active_header = None
        index += 1
    res = "\n".join(merged_lines) + "\n"

    # Two printed roll tables arrived as plain text. Convert only the existing
    # roll/result lines and assert their complete observed sequences.
    robe_match = re.search(
        r"\n1d100 Patch\n\n(?P<body>01-08 Bag of 100 GP.*?97–00 Portable Ram)\n",
        res,
        re.S,
    )
    if robe_match:
        rows = re.findall(r"(?m)^(\d{2}(?:[-–]\d{2})) (.+)$", robe_match.group("body"))
        expected = [
            "01-08", "09–15", "16–22", "23–30", "31–44", "45–51",
            "52–59", "60–68", "69–75", "76–83", "84–90", "91–96", "97–00",
        ]
        if [roll for roll, _ in rows] != expected:
            raise RuntimeError("Robe of Useful Items table rows drifted")
        table = (
            "\n| 1d100 | Patch |\n| :---- | :---- |\n"
            + "\n".join(f"| {roll} | {value} |" for roll, value in rows)
            + "\n"
        )
        res = res[: robe_match.start()] + table + res[robe_match.end() :]

    sphere_match = re.search(
        r"\n1d100 Result\n\n(?P<body>01–50 The sphere is destroyed\..*?86–00 A spatial rift[^\n]+)\n",
        res,
        re.S,
    )
    if sphere_match:
        rows = re.findall(r"(?m)^(\d{2}–\d{2}) (.+)$", sphere_match.group("body"))
        if [roll for roll, _ in rows] != ["01–50", "51–85", "86–00"]:
            raise RuntimeError("Sphere of Annihilation table rows drifted")
        table = (
            "\n| 1d100 | Result |\n| :---- | :----- |\n"
            + "\n".join(f"| {roll} | {value} |" for roll, value in rows)
            + "\n"
        )
        res = res[: sphere_match.start()] + table + res[sphere_match.end() :]

    # Earlier normalized sources may already contain conversion-only captions
    # for these two prose-introduced tables. Their stable record names belong
    # in the structured extraction index, not in the authoritative wording.
    res = res.replace(
        "\nRobe of Useful Items Patches\n\n| 1d100 | Patch |",
        "\n| 1d100 | Patch |",
    )
    res = res.replace(
        "\nSphere Interactions\n\n| 1d100 | Result |",
        "\n| 1d100 | Result |",
    )

    # Wrapped monster stat values are single printed fields; blank lines were
    # introduced by column flow. Three AC/Initiative pairs need splitting.
    res = re.sub(
        r"(?m)^(Immunities [^\n]+,)\n\n([^#\n]+)$",
        r"\1 \2",
        res,
    )
    res = re.sub(
        r"(?m)^(Senses [^\n]+;)\n\n(Passive Perception \d+)$",
        r"\1 \2",
        res,
    )
    res = re.sub(
        r"(?m)^AC (\d+(?: [^\n]*?)?) Initiative ([+\-−]\d+ \(\d+\))$",
        r"AC \1\nInitiative \2",
        res,
    )

    res = res.replace("damage.You also know", "damage. You also know")

    # 21e. Enforce the complete official-PDF stat-table registry after every
    # layout relocation. This is independent of the optional text-layer file,
    # catches wrong-owner associations, and fails if the 336-table set drifts.
    res = apply_registered_stat_blocks(res)

    # The repairs above create newly adjacent stat/header lines after the
    # earlier compaction passes, so compact once more in this same run to keep
    # repair_source.py idempotent.
    res = re.sub(r"(?m)^(Casting Time: [^\n]+)\n\n(Range: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Range: [^\n]+)\n\n(Components: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Components: [^\n]+)\n\n(Duration: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(AC [^\n]+)\n\n(Initiative [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Initiative [^\n]+)\n\n(HP [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(HP [^\n]+)\n\n(Speed [^\n]+)", r"\1\n\2", res)
    for first_label in (
        "Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear",
        "Senses", "Languages",
    ):
        for second_label in (
            "Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear",
            "Senses", "Languages", "CR",
        ):
            res = re.sub(
                rf"(?m)^({first_label} [^\n]+)\n\n({second_label} [^\n]+)",
                r"\1\n\2",
                res,
            )

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
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    md_path = Path(args.source_md)
    if not md_path.exists():
        sys.exit(f"Source markdown {md_path} not found.")

    md_content = md_path.read_text(encoding="utf-8")
    repaired = repair_source_text(md_content)

    if repaired == md_content:
        print("Source file is already clean, normalized, and formatted. No changes made.")
    else:
        if args.dry_run:
            print("Changes detected (dry-run).")
            sys.exit(1)
        else:
            md_path.write_text(repaired, encoding="utf-8")
            print(f"Repaired and reformatted {md_path} successfully.")


if __name__ == "__main__":
    main()
