"""Generate sitemap.xml listing every record URL plus top-level pages."""

from __future__ import annotations

import argparse
from pathlib import Path

from srdlib import BASE, iter_object_files, load_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    urls = [
        BASE,
        BASE + "llms.txt",
        BASE + "llms-full.txt",
        BASE + "vocab/",
        BASE + "objects/srd52-system-data.jsonld",
        BASE + "objects/srd52-system-data.bundle.jsonld",
        BASE + "objects/search-index.json",
        BASE + "objects/collection-index.json",
    ]
    for _, path in iter_object_files(root):
        record = load_json(path)
        urls.append(record["@id"] + ".jsonld")

    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    (root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n",
        encoding="utf-8",
    )
    print(f"sitemap: {len(urls)} URLs")


if __name__ == "__main__":
    main()
