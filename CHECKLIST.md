# SRD 5.2.1 → JSON-LD Reference Corpus Checklist

## Source and rights

- [x] `SRD_CC_v5.2.1.md` is the sole contributing content source; source and manifest rights metadata preserve the exact CC-BY-4.0 attribution and source digest.
- [x] The source-normalization event is cross-checked against the official PDF text layer and registered with observed tokens, fixes, rationale, dispositions, counts, and pre/post digests.
- [x] The obsolete external creature cache is removed; extraction never derives missing source values; a truncated ability fixture remains omitted through clean rebuild, bundle, and LLM output.
- [x] Twelve registered anomaly detectors run in CI and reject stale or unreviewed hits.

## Semantic architecture

- [x] JSON-LD 1.1 context, stable canonical IRIs, and Draft 2020-12 schemas cover all 13 collections and aggregate/auxiliary artifacts.
- [x] Every IRI-coerced predicate uses `{ "@id": "..." }` node references.
- [x] Class core traits and manifest collections use graph-safe typed entries; expansion preserves all compact properties and values.
- [x] Every project class/predicate in the expanded graph has a generated vocabulary definition, description, value kind/range, and dereferenceable fragment target.

## Extraction and traceability

- [x] The clean corpus contains 2,092 records: 1 source, 738 rules, 223 logical tables, 12 classes, 12 subclasses, 9 species, 4 backgrounds, 17 feats, 133 equipment, 338 spells, 15 conditions, 258 magic items, and 332 monsters.
- [x] Ordinary entity locators start at their heading; Table/equipment locators start at the physical table; nested feature/stat spans remain inside their owner.
- [x] Tables retain `rawText`, continuation headers are not promoted to rows, Wand of Wonder is one 18-row table, and no table is empty.
- [x] Every spell has casting time, range, components, and duration; all magic-item rarity variants and full-header attunement are retained.
- [x] All 424 monster `Attack Roll:` paragraphs have a disposition: 423 complete typed damaging attacks and one explicit non-damaging Roper Tentacle reason.
- [x] Structured equipment names decode reviewed HTML markup and produce stable semantic slugs.

## Ingestion and semantic review

- [x] One shared recursive textual projection drives LLM, search, and review artifacts, including nested features/traits/stat sections, table cells, core traits, and structured-only equipment.
- [x] Search postings retain matched nested excerpts; corpus-wide tests cover nested prose and Rage/Mindless Rage/Longsword fixtures.
- [x] The occurrence ledger records path, source line/column, context, status, and evidence note. Curated policies and a reviewed signal-set digest live outside generated output, survive clean builds, and make added/removed/moved signals pending.
- [x] The ledger includes typed/source, table-shape, anomaly, provenance, and graph checks and has zero pending signals.

## Verification and publication

- [x] Interval coverage, anomaly disposition, source fidelity, graph expansion, semantic review, structural validation, schema validation, and determinism are separate gates with documented meanings.
- [x] Schemas validate records, manifest, bundle, search index, collection index, coverage report, and review ledger; structural checks also cover sitemap and vocabulary targets.
- [x] Determinism covers two clean builds and checked-in `objects/`, `llms-full.txt`, `vocab/`, and `sitemap.xml`, including curated review-policy inputs.
- [x] `README.md`, `SPECIFICATION.md`, manifest version, inventory counts, generated command summaries, and this checklist agree with the clean v0.3.0 build.
