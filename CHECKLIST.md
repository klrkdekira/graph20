# SRD 5.2.1 → JSON-LD Reference Corpus Checklist

Replication of the `wwn-system-json` pipeline (see its `PLAYBOOK.md`) for the System Reference Document 5.2.1. Unchecked items are open work, not omissions by accident.

## Phase 1: Source preparation & provenance

- [x] Freeze source (`SRD_CC_v5.2.1.md`) and record SHA-256 digest in the source record; digest asserted by tests.
- [x] Source metadata record with CC-BY-4.0 license and the required attribution statement (`objects/sources/srd-5-2-1.jsonld`).
- [ ] Source cleanup pass (heal `Id6` OCR dice, flat-heading hierarchy) — deliberately NOT done in v0.1.0; the file is kept byte-frozen and anomalies are handled via the override registry instead.

## Phase 2: Semantic architecture & schemas

- [x] Base IRI `https://cheeleong.dev/graph20/`; JSON-LD 1.1 context (`systems/context.jsonld`).
- [x] Draft 2020-12 schemas: common, source, rule, table, spell, feat, magic-item, monster, system; `unevaluatedProperties: false` on leaf entities.

## Phase 3: Extraction pipeline

- [x] Chapter/heading block parser with line provenance (`scripts/extract_srd.py`).
- [x] Specialized emitters: spells (338), feats (17), magic items (258), monsters (332).
- [x] Generic emitters: rules (1,113) and HTML-table conversion to Table records (258) for full block coverage.
- [ ] Typed catalogs for classes, subclasses, species, backgrounds, mundane equipment, Rules Glossary conditions.

## Phase 4: Anomaly tracking

- [x] `objects/sources/extraction-overrides.json` with observed/proposed/status/rationale entries (roman-numeral OCR, LaTeX labels, glued scores, CR line joins, truncated cells, dice OCR).
- [ ] Review-signal ledger (`build_review_ledger.py` / `manage_review_ledger.py`).

## Phase 5: Coverage & traceability

- [x] Every heading block from the first chapter onward consumed by exactly one record; excluded legal preamble documented (`objects/sources/source-coverage.json`).
- [ ] Paragraph-level coverage ledger with unit-to-record mapping.

## Phase 5b: Graph enrichment

- [ ] Spell → class nodes, monster → condition nodes, bidirectional links, further typed stat siblings (attack routines, speeds, senses).

## Phase 6: Aggregates

- [x] Manifest with collection indexes + corpus digest (`objects/srd52-system-data.jsonld`).
- [x] Single-file bundle (`objects/srd52-system-data.bundle.jsonld`).

## Phase 7: Verification & CI

- [x] `validate.py`, `validate_schema.py`, `check_determinism.py`, `tests/test_structural.py` (12 tests), unified `make check`.
- [x] GitHub Actions CI running `make check`.

## Phase 8: LLM-native & FAIR metadata

- [x] `llms-full.txt` (generated, inlines every record) and `objects/search-index.json` (generated inverted index).
- [x] `llms.txt` curated sitemap.
- [ ] `datapackage.json`, `CITATION.cff`, Schema.org/DCAT snippet, `robots.txt`, `sitemap.xml`, static explorer `index.html`, vocab page.

## Phase 9: Living documentation

- [x] `SPECIFICATION.md`, `AGENTS.md`, this checklist.
