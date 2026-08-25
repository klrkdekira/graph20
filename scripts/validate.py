"""Dependency-free structural validation of the emitted corpus.

Checks: JSON syntax, required identity fields, unique @id values, slug and
filename agreement, source-locator line bounds, and that every internal
node reference resolves to an emitted record.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from srdlib import (
    ATTRIBUTION_STATEMENT,
    BASE,
    BUILD_METRICS_NAME,
    BUNDLE_NAME,
    CONTEXT_IRI,
    MANIFEST_NAME,
    SOURCE_FILE,
    SOURCE_ID,
    iter_object_files,
    load_json,
    project_version,
    sha256_of,
)
from build_collection_indexes import entry_for
from build_metrics import collect_metrics
from build_sitemap import LASTMOD

REQUIRED = ("@context", "@id", "@type", "name", "slug", "source", "sourceLocator")


def collect_references(value, out):
    if isinstance(value, dict):
        if set(value.keys()) == {"@id"}:
            out.append(value["@id"])
        else:
            for key, item in value.items():
                if key != "@id":
                    collect_references(item, out)
    elif isinstance(value, list):
        for item in value:
            collect_references(item, out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    errors = []
    ids = {}
    records = []
    line_count = len(
        (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    )

    for collection, path in iter_object_files(root):
        try:
            record = load_json(path)
        except ValueError as exc:
            errors.append(f"{path}: invalid JSON ({exc})")
            continue
        records.append((collection, path, record))
        rid = record.get("@id", "")
        if rid in ids:
            errors.append(f"{path}: duplicate @id {rid} (also {ids[rid]})")
        ids[rid] = path
        expected_html = f"{BASE}records/{collection}/{record.get('slug', '')}/"
        if record.get("htmlPage") != {"@id": expected_html}:
            errors.append(f"{path}: htmlPage does not match its record route")
        if collection == "sources":
            continue
        for field in REQUIRED:
            if field not in record:
                errors.append(f"{path}: missing {field}")
        if record.get("@context") != CONTEXT_IRI:
            errors.append(f"{path}: wrong @context")
        if not rid.startswith(f"{BASE}objects/{collection}/"):
            errors.append(f"{path}: @id outside collection base: {rid}")
        if rid.rsplit("/", 1)[-1] != record.get("slug"):
            errors.append(f"{path}: slug does not match @id")
        if path.stem != record.get("slug"):
            errors.append(f"{path}: filename does not match slug")
        locator = record.get("sourceLocator", {})
        start, end = locator.get("lineStart", 0), locator.get("lineEnd", 0)
        if not (1 <= start <= end <= line_count):
            errors.append(f"{path}: bad line bounds {start}-{end}")

    for collection, path, record in records:
        refs = []
        collect_references(record, refs)
        for ref in refs:
            if ref.startswith(f"{BASE}objects/") and ref not in ids:
                errors.append(f"{path}: unresolved reference {ref}")
            if ref.startswith(f"{BASE}records/"):
                expected_path = root / ref.removeprefix(BASE) / "index.html"
                if not expected_path.is_file():
                    errors.append(f"{path}: missing HTML counterpart {expected_path.relative_to(root)}")

    # Manifest and bundle resolve too.
    for name in (MANIFEST_NAME, BUNDLE_NAME):
        doc_path = root / "objects" / name
        if not doc_path.exists():
            errors.append(f"missing {name}")
            continue
        doc = load_json(doc_path)
        refs = []
        collect_references(doc.get("collections", doc), refs)
        for ref in refs:
            if ref.startswith(f"{BASE}objects/") and ref not in ids:
                errors.append(f"{name}: unresolved reference {ref}")

    search = load_json(root / "objects/search-index.json")
    document_count = len(search.get("documents", []))
    for token, postings in search.get("tokens", {}).items():
        for posting in postings:
            index = posting.get("document", -1)
            if not 0 <= index < document_count:
                errors.append(f"search-index.json: token {token!r} has bad document index {index}")

    try:
        sitemap_root = ET.parse(root / "sitemap.xml").getroot()
    except (ET.ParseError, OSError) as exc:
        errors.append(f"sitemap.xml: {exc}")
        sitemap_root = None
    if sitemap_root is not None:
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        sitemap_entries = {
            node.findtext("sm:loc", namespaces=namespace):
            node.findtext("sm:lastmod", namespaces=namespace)
            for node in sitemap_root.findall("sm:url", namespace)
        }
        expected_urls = {
            BASE,
            BASE + "llms.txt",
            BASE + "llms-full.txt",
            BASE + "vocab/",
            BASE + "vocab/terms.json",
            BASE + f"objects/{MANIFEST_NAME}",
            BASE + f"objects/{BUNDLE_NAME}",
            BASE + "objects/search-index.json",
            BASE + "objects/collection-index.json",
            *(record["htmlPage"]["@id"] for _, _, record in records),
        }
        if set(sitemap_entries) != expected_urls:
            errors.append("sitemap.xml: URL set differs from published artifacts and record pages")
        if any(value != LASTMOD for value in sitemap_entries.values()):
            errors.append(f"sitemap.xml: every URL must use deterministic lastmod {LASTMOD}")
    vocab = load_json(root / "vocab/terms.json")
    vocab_page = (root / "vocab/index.html").read_text(encoding="utf-8")
    for entry in vocab.get("classes", []) + vocab.get("properties", []):
        if f'id="{entry["anchor"]}"' not in vocab_page:
            errors.append(f"vocab/index.html: missing target #{entry['anchor']}")

    # Collection indexes are a lossless, exact projection of emitted records.
    collection_index = load_json(root / "objects/collection-index.json")["collections"]
    for collection in collection_index:
        expected = []
        for current, _, record in records:
            if current == collection:
                expected.append(entry_for(collection, record))
        expected.sort(key=lambda pair: pair[0])
        if collection_index[collection] != [entry for _, entry in expected]:
            errors.append(f"collection-index.json: {collection} entries differ from records")

    # Source identity, digest, and attribution are exact invariants—not a
    # schema exemption—and the attribution survives every public entry point.
    source = next((record for collection, _, record in records if collection == "sources"), None)
    if source is None:
        errors.append("source record missing")
    else:
        expected_source = {
            "@id": SOURCE_ID,
            "slug": "srd-5-2-1",
            "@type": "Source",
            "sourceFile": SOURCE_FILE,
            "srdVersion": "5.2.1",
            "license": "CC-BY-4.0",
            "attributionStatement": ATTRIBUTION_STATEMENT,
            "contentDigest": sha256_of(root / SOURCE_FILE),
        }
        for field, value in expected_source.items():
            if source.get(field) != value:
                errors.append(f"source record: {field} differs from the required value")
        manifest = load_json(root / "objects" / MANIFEST_NAME)
        if manifest.get("metadata", {}).get("attributionStatement") != ATTRIBUTION_STATEMENT:
            errors.append(f"{MANIFEST_NAME}: attribution statement is not exact")
        for filename in ("README.md", "llms.txt", "llms-full.txt"):
            normalized = re.sub(r"\s+", " ", (root / filename).read_text(encoding="utf-8"))
            if ATTRIBUTION_STATEMENT not in normalized:
                errors.append(f"{filename}: exact attribution statement is missing")

    # pyproject.toml is the sole version source; every published carrier must agree.
    version = project_version(root)
    version_values = {
        MANIFEST_NAME: load_json(root / "objects" / MANIFEST_NAME).get("version"),
        BUNDLE_NAME: load_json(root / "objects" / BUNDLE_NAME).get("version"),
        BUILD_METRICS_NAME: load_json(root / "objects" / BUILD_METRICS_NAME).get("version"),
        "datapackage.json": load_json(root / "datapackage.json").get("version"),
    }
    for carrier, value in version_values.items():
        if value != version:
            errors.append(f"{carrier}: version {value!r} differs from pyproject {version!r}")
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    if not re.search(rf'^version:\s*["\']?{re.escape(version)}["\']?\s*$', citation, re.M):
        errors.append("CITATION.cff: version differs from pyproject")
    for filename in ("README.md", "SPECIFICATION.md", "index.html"):
        if f"v{version}" not in (root / filename).read_text(encoding="utf-8"):
            errors.append(f"{filename}: published version v{version} is missing")

    metrics = load_json(root / "objects" / BUILD_METRICS_NAME)
    if metrics != collect_metrics(root):
        errors.append(f"{BUILD_METRICS_NAME}: values differ from recomputed build artifacts")

    # HTML application and record pages need basic smoke-test structure and
    # paired canonical/JSON-LD discovery metadata.
    explorer = (root / "index.html").read_text(encoding="utf-8")
    if "\x00" in explorer:
        errors.append("index.html: contains a NUL byte")
    for element_id in ("nav", "items", "detail", "filter", "global-search"):
        if f'id="{element_id}"' not in explorer:
            errors.append(f"index.html: missing required #{element_id} application target")
    for collection, _, record in records:
        page = root / "records" / collection / record["slug"] / "index.html"
        if not page.is_file():
            continue
        markup = page.read_text(encoding="utf-8")
        raw = f"../../../objects/{collection}/{record['slug']}.jsonld"
        if f'<link rel="canonical" href="{record["htmlPage"]["@id"]}"' not in markup:
            errors.append(f"{page}: missing canonical record URL")
        if f'<link rel="alternate" type="application/ld+json" href="{raw}"' not in markup:
            errors.append(f"{page}: missing JSON-LD alternate")

    if errors:
        print("\n".join(errors[:50]))
        print(f"FAIL: {len(errors)} structural errors")
        sys.exit(1)
    print(
        f"OK: {len(records)} records and auxiliary indexes structurally valid; "
        "all references and vocabulary targets resolve"
    )


if __name__ == "__main__":
    main()
