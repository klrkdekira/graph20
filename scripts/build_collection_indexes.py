"""Generate objects/collection-index.json: display metadata for the explorer.

One compact entry per record (slug, name, sub-line, group) so index.html can
render grouped, contextual lists without fetching every record.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path

from srdlib import CHAPTERS, COLLECTIONS, dump_json, iter_object_files, load_json

RARITY_ORDER = [
    "Common", "Uncommon", "Rare", "Very Rare", "Legendary", "Artifact",
    "Multiple Rarities", "Rarity Varies", "Varies",
]
FEAT_ORDER = ["Origin", "General", "Fighting Style", "Epic Boon"]


def cr_sort_key(cr: str):
    try:
        return float(Fraction(cr))
    except (ValueError, ZeroDivisionError):
        return -1.0


def entry_for(collection: str, record: dict):
    name = record["name"]
    slug = record["slug"]
    locator = record.get("sourceLocator", {})
    if collection == "spells":
        level = record.get("level", 0)
        group = "Cantrips" if level == 0 else f"Level {level}"
        sub = f"{record.get('school', '')} · {', '.join(record.get('classAvailability', []))}"
        order = (level, name.lower())
    elif collection == "monsters":
        cr = record.get("challengeRating")
        group = f"CR {cr}" if cr else "CR —"
        sub = record.get("sizeTypeAlignment", "")
        order = (cr_sort_key(cr) if cr else 99.0, name.lower())
    elif collection == "magic-items":
        rarity = record.get("rarity")
        group = rarity or "Multiple Rarities"
        detail = record.get("categoryDetail")
        sub = record.get("itemCategory", "") + (f" ({detail})" if detail else "")
        if record.get("requiresAttunement"):
            sub += " · attunement"
        order = (RARITY_ORDER.index(group) if group in RARITY_ORDER else 99, name.lower())
    elif collection == "feats":
        category = record.get("category", "General")
        group = f"{category} Feats"
        sub = record.get("prerequisite", "")
        order = (FEAT_ORDER.index(category), name.lower())
    elif collection == "classes":
        group = "Classes"
        core = {trait["name"]: trait["value"] for trait in record.get("coreTraits", [])}
        sub = f"{core.get('Primary Ability', '')} · {core.get('Hit Point Die', '')}"
        order = (0, name.lower())
    elif collection == "subclasses":
        parent = record.get("parentClassName", "")
        group = parent
        sub = f"{parent} subclass"
        order = (parent, name.lower())
    elif collection == "species":
        group = "Species"
        sub = f"{record.get('size', '')} · {record.get('speed', '')}"
        order = (0, name.lower())
    elif collection == "backgrounds":
        group = "Backgrounds"
        sub = record.get("abilityScores", "")
        order = (0, name.lower())
    elif collection == "conditions":
        group = "Conditions"
        sub = ""
        order = (0, name.lower())
    elif collection == "equipment":
        etype = record.get("equipmentType", "gear")
        if etype == "weapon":
            group = f"{record.get('weaponCategory', '')} {record.get('attackType', '')} Weapons".strip()
            sub = f"{record.get('damage', '')} · {record.get('mastery', '')}"
            order = (0, record.get("weaponCategory", ""), record.get("attackType", ""), name.lower())
        elif etype == "armor":
            category = record.get("armorCategory", "")
            group = "Shield" if category == "Shield" else f"{category} Armor".strip()
            sub = f"AC {record.get('armorClass', '')}"
            order = (1, category, "", name.lower())
        else:
            group = "Adventuring Gear"
            cost = record.get("cost", {}).get("text", "")
            sub = cost
            order = (2, "", "", name.lower())
    elif collection in ("rules", "tables"):
        chapter = locator.get("chapter", "")
        group = chapter
        sub = f"§{locator.get('section', '')}"
        order = (
            CHAPTERS.index(chapter) if chapter in CHAPTERS else 99,
            locator.get("lineStart", 0),
        )
    else:  # sources
        group = "Sources"
        sub = record.get("license", "")
        order = (0, name.lower())
    return order, {"slug": slug, "name": name, "sub": sub.strip(" ·"), "group": group}


def build(root: Path) -> None:
    index = {}
    for collection in COLLECTIONS:
        entries = []
        for c, path in iter_object_files(root):
            if c != collection:
                continue
            entries.append(entry_for(collection, load_json(path)))
        entries.sort(key=lambda pair: pair[0])
        index[collection] = [entry for _, entry in entries]
    dump_json(root / "objects" / "collection-index.json", {"collections": index})
    total = sum(len(v) for v in index.values())
    print(f"collection-index: {total} entries")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
