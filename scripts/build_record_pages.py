"""Generate crawlable, human-readable HTML pages for every corpus record."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

from srdlib import ATTRIBUTION_STATEMENT, BASE, iter_object_files, load_json


def render_table(record: dict) -> str:
    if not record.get("columns"):
        return ""
    head = "".join(f"<th>{html.escape(column)}</th>" for column in record["columns"])
    rows = []
    for row in record.get("rows", []):
        rendered_cells = []
        for cell in row["cells"]:
            colspan = f' colspan="{cell["colspan"]}"' if cell.get("colspan") else ""
            rendered_cells.append(f'<td{colspan}>{html.escape(cell["value"])}</td>')
        cells = "".join(rendered_cells)
        rows.append(f"<tr>{cells}</tr>")
    return f"<div class=tablewrap><table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def render_relations(record: dict) -> str:
    links = []
    def walk(value):
        if isinstance(value, dict):
            if set(value) == {"@id"}:
                yield value["@id"]
            else:
                for child in value.values():
                    yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
    for iri in walk(record):
        if iri in (record.get("source", {}).get("@id"), record.get("htmlPage", {}).get("@id")):
            continue
        marker = BASE + "objects/"
        if iri.startswith(marker):
            collection, slug = iri.removeprefix(marker).split("/", 1)
            href = f"../../../records/{collection}/{slug}/"
            links.append(f'<li><a href="{html.escape(href)}">{html.escape(collection)} / {html.escape(slug)}</a></li>')
    return f"<section><h2>Connected records</h2><ul>{''.join(dict.fromkeys(links))}</ul></section>" if links else ""


def render_record(collection: str, record: dict) -> str:
    slug = record["slug"]
    raw_href = f"../../../objects/{collection}/{slug}.jsonld"
    canonical = record["htmlPage"]["@id"]
    locator = record.get("sourceLocator")
    provenance = ""
    if locator:
        provenance = (
            f'<p class=meta>SRD 5.2.1 · {html.escape(locator["chapter"])} '
            f'§{html.escape(locator["section"])} · {html.escape(locator["heading"])} · '
            f'lines {locator["lineStart"]}–{locator["lineEnd"]}</p>'
        )
    prose = record.get("rulesText") or record.get("description") or record.get("attributionStatement") or ""
    prose_html = f"<section><h2>Source text</h2><div class=prose>{html.escape(prose)}</div></section>" if prose else ""
    structured = []
    ignored = {"@context", "@id", "@type", "name", "slug", "source", "sourceLocator", "htmlPage", "rulesText", "description", "columns", "rows", "rawText"}
    for key, value in record.items():
        if key in ignored or isinstance(value, (dict, list)):
            continue
        structured.append(f"<dt>{html.escape(key)}</dt><dd>{html.escape(str(value))}</dd>")
    facts = f"<section><h2>Indexed facts</h2><dl>{''.join(structured)}</dl></section>" if structured else ""
    json_text = json.dumps(record, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(record['name'])} · SRD 5.2.1</title>
<meta name="description" content="Human-readable SRD 5.2.1 {html.escape(record['@type'])} record for {html.escape(record['name'])}." />
<link rel="canonical" href="{html.escape(canonical)}" />
<link rel="alternate" type="application/ld+json" href="{html.escape(raw_href)}" />
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/legalcode" />
<script type="application/ld+json">{json_text}</script>
<style>body{{font:16px/1.65 system-ui,sans-serif;max-width:70rem;margin:2rem auto;padding:0 1.2rem;color:#241c17;background:#fbf5e7}}a{{color:#76242b}}h1,h2{{font-family:Georgia,serif}}h1{{font-size:2.4rem;margin-bottom:.2rem}}h2{{margin-top:2rem;border-bottom:1px solid #c9b68f}}.meta{{color:#66594d}}.prose{{white-space:pre-wrap;max-width:75ch;font:1.15rem/1.75 Georgia,serif}}dl{{display:grid;grid-template-columns:minmax(10rem,auto) 1fr;gap:.35rem 1rem}}dt{{font-weight:700}}dd{{margin:0}}.tablewrap{{overflow:auto}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #c9b68f;padding:.45rem;text-align:left}}footer{{margin-top:3rem;padding-top:1.5rem;border-top:1px solid #c9b68f;color:#66594d;font-size:.85rem}}</style></head>
<body><nav><a href="../../../">Corpus explorer</a> · <a href="{html.escape(raw_href)}">Raw JSON-LD</a></nav>
<main><h1>{html.escape(record['name'])}</h1><p class=meta>{html.escape(record['@type'])}</p>{provenance}{facts}{render_table(record)}{prose_html}{render_relations(record)}</main>
<footer>{html.escape(ATTRIBUTION_STATEMENT)}</footer></body></html>
"""


def build(root: Path) -> None:
    output = root / "records"
    if output.exists():
        shutil.rmtree(output)
    count = 0
    for collection, path in iter_object_files(root):
        record = load_json(path)
        destination = output / collection / record["slug"] / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_record(collection, record), encoding="utf-8")
        count += 1
    print(f"record-pages: {count} crawlable HTML pages")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
