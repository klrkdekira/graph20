# SRD 5.2.1 → JSON-LD Reference Corpus Checklist

Replication of the `wwn-system-json` pipeline (see its `PLAYBOOK.md`) for the System Reference Document 5.2.1.

## Phase 1: Source preparation & provenance

- [x] Source metadata record with CC-BY-4.0 license and the required attribution statement (`objects/sources/srd-5-2-1.jsonld`); digest asserted by tests.
- [x] Source cleanup pass (`scripts/repair_source.py`, glossary-driven via `scripts/data/sanitization-glossary.json`): OCR dice (`Id6`→`1d6`), `+I` bonuses, `Level I/II` headings, CR line joins, and 91 damaged ability tables regenerated from open5e srd-2024 (CC-BY-4.0) with cell-level cross-validation. Idempotent; pre/post digests recorded in `extraction-overrides.json`.

## Phase 2: Semantic architecture & schemas

- [x] Base IRI `https://cheeleong.dev/graph20/`; JSON-LD 1.1 context (`systems/context.jsonld`).
- [x] Draft 2020-12 schemas for all 13 collections: common, source, rule, table, class, subclass, species, background, feat, equipment, spell, condition, magic-item, monster, system; `unevaluatedProperties: false` on leaf entities; `if/then` guards on the equipment union.

## Phase 3: Extraction pipeline

- [x] Chapter/heading block parser with line provenance (`scripts/extract_srd.py`).
- [x] Specialized emitters: spells (338), feats (17), magic items (258), monsters (332), classes (12), subclasses (12), species (9), backgrounds (4), conditions (15), equipment (133 typed from the Weapons/Armor/Adventuring Gear tables).
- [x] Generic emitters: rules (738) and HTML-table conversion to Table records (243) for full coverage of everything else.

## Phase 4: Anomaly tracking

- [x] `objects/sources/extraction-overrides.json` with observed/proposed/status/rationale entries; repairs applied to source carry `status: applied-to-source` with pre/post digests.
- [x] Review-signal ledger (`build_review_ledger.py`, `manage_review_ledger.py`): dice formulas, player choices, slot scaling — triage states survive rebuilds.

## Phase 5: Coverage & traceability

- [x] Paragraph-level coverage (`build_coverage.py`): every non-blank content line maps to ≥1 record; 0 uncovered lines; legal preamble exclusion documented.

## Phase 5b: Graph enrichment & typed stats

- [x] Spells → class node references; typed save ability, damage rolls, concentration/ritual/slot-scaling flags.
- [x] Monsters → condition-immunity node references; typed six-ability blocks, HP rolls, CR/XP/PB, parsed attack routines (bonus, reach/range, damage dice + type).
- [x] Equipment → typed damage/properties/mastery/AC/costs; classes ↔ subclasses ↔ spell-list links.
- [x] All typed fields are siblings of verbatim source strings, produced only by the extraction scripts.

## Phase 6: Aggregates

- [x] Manifest with collection indexes + corpus digest; single-file bundle.

## Phase 7: Verification & CI

- [x] `validate.py`, `validate_schema.py`, `check_determinism.py` (includes coverage + review ledger), `tests/test_structural.py` (16 tests), unified `make check`, GitHub Actions CI.

## Phase 8: LLM-native & FAIR metadata

- [x] `llms.txt`, generated `llms-full.txt`, `objects/search-index.json`, `objects/collection-index.json`.
- [x] `datapackage.json`, `CITATION.cff`, Schema.org Dataset snippet, `robots.txt`, generated `sitemap.xml` (all record URLs), `.nojekyll`, generated `vocab/index.html` (dereferenceable predicate IRIs).

## Phase 9: Living documentation

- [x] `SPECIFICATION.md`, `AGENTS.md`, this checklist, static explorer `index.html`.

## Open (requires human judgment, not tooling)

- [ ] Semantic review: disposition the pending signals in `objects/sources/source-review-ledger.json` (`make review-stats`).
