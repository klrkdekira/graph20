"""Authoritative ground-truth source repair, table, and layout normalization for SRD_CC_v5.2.1.md.

Cross-checks and normalizes MinerU OCR/conversion defects in SRD_CC_v5.2.1.md
using the direct PyMuPDF text-layer ground truth in SRD_CC_v5.2.1.txt,
reformats all tables into clean, well-organized GitHub-Flavored Markdown (GFM)
pipe tables, and cleans up document layout (hyphenation, bullets, TOC, headings,
and stat block layout).

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


def repair_source_text(md_content: str, txt_content: str) -> str:
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
        (r"\bchar-acter\b", "character"),
        (r"\bpro-ficiency\b", "proficiency"),
    ]
    for pat, rep in ocr_hyphens:
        res = re.sub(pat, rep, res)

    # 7. Fraction slash normalization
    res = res.replace("11⁄2 mph", "1 1/2 mph").replace("21⁄2 mph", "2 1/2 mph")

    # 8. Numbered headings and trailing periods
    heading_patterns = [
        (r"^# Step I: Choose Class", "# Step 1: Choose Class"),
        (r"^# Tier I \(Levels I–4\)", "# Tier 1 (Levels 1–4)"),
        (r"^# I: Choose Abilities", "# 1: Choose Abilities"),
        (r"^# Step I: Choose a Difficulty", "# Step 1: Choose a Difficulty"),
        (r"^# Attack Deflection \(Quarterstaff Form Only\)\.$", "# Attack Deflection (Quarterstaff Form Only)"),
    ]
    for pat, rep in heading_patterns:
        res = re.sub(pat, rep, res, flags=re.MULTILINE)

    # 9. Spell header fixes: Component: -> Components:
    res = re.sub(r"(?m)^Component:\s*([VSM])", r"Components: \1", res)

    # 10. Spurious headings in spell blocks and monster blocks
    spurious_headings = [
        (r"(?m)^# Components:\s*([^\n]+)$", r"Components: \1"),
        (r"(?m)^# Resistances Cold$", r"Resistances Cold"),
        (r"(?m)^# Resistances Acid$", r"Resistances Acid"),
        (r"(?m)^# Senses Passive Perception 10$", r"Senses Passive Perception 10"),
    ]
    for pat, rep in spurious_headings:
        res = re.sub(pat, rep, res)

    # 11. Unicode bullet character normalization
    res = re.sub(r"(?m)^•\s+", "- ", res)

    # 12. Chapter separators
    chapters = [
        "Playing the Game", "Character Creation", "Classes", "Character Origins",
        "Feats", "Equipment", "Spells", "Rules Glossary", "Gameplay Toolbox",
        "Magic Items", "Monsters", "Monsters A-Z", "Animals"
    ]
    for ch in chapters:
        res = re.sub(rf"(?<!---)\n\n# {re.escape(ch)}\n", f"\n\n---\n\n# {ch}\n", res)

    # 13. Table of Contents clean list formatting
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

    # 14. LaTeX Math and Math-mode cleanup
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

    # 15. HTML tables to GFM pipe tables conversion
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

    # 16. Compact monster stat blocks
    res = re.sub(r"(?m)^(AC [^\n]+)\n\n(Initiative [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Initiative [^\n]+)\n\n(HP [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(HP [^\n]+)\n\n(Speed [^\n]+)", r"\1\n\2", res)
    for t1 in ["Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear", "Senses", "Languages"]:
        for t2 in ["Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear", "Senses", "Languages", "CR"]:
            res = re.sub(rf"(?m)^({t1} [^\n]+)\n\n({t2} [^\n]+)", r"\1\n\2", res)

    # 17. Compact spell blocks
    res = re.sub(r"(?m)^(Casting Time: [^\n]+)\n\n(Range: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Range: [^\n]+)\n\n(Components: [^\n]+)", r"\1\n\2", res)
    res = re.sub(r"(?m)^(Components: [^\n]+)\n\n(Duration: [^\n]+)", r"\1\n\2", res)

    # 18. Strip trailing whitespaces from every line
    res_lines = [l.rstrip() for l in res.splitlines()]
    res = "\n".join(res_lines) + "\n"

    # Normalize multiple blank lines
    res = re.sub(r"\n{3,}", "\n\n", res)
    return res


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair, format tables, and normalize layout in SRD_CC_v5.2.1.md against ground truth in SRD_CC_v5.2.1.txt"
    )
    parser.add_argument("--source-md", default="SRD_CC_v5.2.1.md")
    parser.add_argument("--source-txt", default="SRD_CC_v5.2.1.txt")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    md_path = Path(args.source_md)
    txt_path = Path(args.source_txt)

    if not md_path.exists() or not txt_path.exists():
        sys.exit("Source markdown or text file not found.")

    md_content = md_path.read_text(encoding="utf-8")
    txt_content = txt_path.read_text(encoding="utf-8")

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
