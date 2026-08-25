# SRD 5.2.1 → JSON-LD Reference Corpus Checklist

## Source and rights

- [x] `SRD_CC_v5.2.1.md` is the sole contributing content source; source and manifest rights metadata preserve the exact CC-BY-4.0 attribution and source digest.
- [x] The source-normalization event is cross-checked against the official PDF text layer and registered with observed tokens, fixes, rationale, dispositions, counts, and pre/post digests.
- [x] The obsolete external creature cache is removed; extraction never derives missing source values; a truncated ability fixture remains omitted through clean rebuild, bundle, and LLM output.
- [x] Twelve registered anomaly detectors run in CI and reject stale or unreviewed hits.

## Semantic architecture

- [x] JSON-LD 1.1 context, stable canonical IRIs, and Draft 2020-12 schemas cover all 19 collections and aggregate/auxiliary artifacts.
- [x] Every IRI-coerced predicate uses `{ "@id": "..." }` node references.
- [x] Twenty-two typed relations connect spell lists/casting, conditions, origin grants, equipment, summons, areas, option catalogs, related rules/tables, and catalog members without replacing display strings; core incoming directions have reverse aliases.
- [x] The graph gate asserts at least 55% outbound semantic-link coverage, at least 20 emitted predicates, and incoming semantic edges for every non-source collection.
- [x] Class core traits and manifest collections use graph-safe typed entries; expansion preserves all compact properties and values.
- [x] Every project class/predicate in the expanded graph has a generated vocabulary definition, description, value kind/range, and dereferenceable fragment target.

## Extraction and traceability

- [x] The clean corpus contains 2,226 records across 19 collections; exact totals are generated and recomputed through `objects/build-metrics.json`.
- [x] Tagged glossary actions, areas, attitudes, and hazards; Warlock invocations; Sorcerer Metamagic options; species lineage tables; tools; mounts; vehicles; services; focuses; ammunition; and food/lodging are typed records rather than latent prose/tables.
- [x] Ordinary entity locators start at their heading; Table/equipment locators start at the physical table; nested feature/stat spans remain inside their owner.
- [x] Tables retain `rawText`, continuation headers are not promoted to rows, Trinkets is one 100-row table, Prismatic Rays is one 8-row table, Wand of Wonder is one 18-row table, and no table is empty.
- [x] Every spell has casting time, range, components, and duration; all magic-item rarity variants and full-header attunement are retained.
- [x] Spell range/component/duration/save/area mechanics, condition effects, magic-item charges/restrictions/curse/sentience flags, equipment weights/tool structures, origin grants, toolbox categories/DCs/damage, and decomposed monster identity/movement/senses/languages/spellcasting are typed source-backed indexes.
- [x] All 429 monster `Attack Roll:` paragraphs have a disposition: 423 complete typed damaging attacks and 6 explicit unparsed dispositions (the Roper Tentacle plus 5 caster-scaling summon attacks).
- [x] Structured equipment names decode reviewed HTML markup and produce stable semantic slugs.

## Ingestion and semantic review

- [x] One shared recursive textual projection drives LLM, search, and review artifacts, including nested features/traits/stat sections, table cells, core traits, and structured-only equipment.
- [x] Search postings retain matched nested excerpts; corpus-wide tests cover nested prose and Rage/Mindless Rage/Longsword fixtures.
- [x] The occurrence ledger records path, source line/column, context, status, and evidence note. Curated policies and a reviewed signal-set digest live outside generated output, survive clean builds, and make added/removed/moved signals pending.
- [x] The ledger includes typed/source, table-shape, anomaly, provenance, and graph checks and has zero pending signals.

## Verification and publication

- [x] Interval coverage, anomaly disposition, source fidelity, graph expansion, semantic review, structural validation, schema validation, and determinism are separate gates with documented meanings.
- [x] Schemas validate records, every bundle member, manifest, bundle envelope, search index, collection index, build metrics, coverage report, and review ledger; structural checks recompute metrics and exact index/sitemap projections.
- [x] Source identity/digest/attribution and the sole-contributor boundary are exact gates; `pyproject.toml` version is cross-checked against every published version carrier.
- [x] Every record has a crawlable HTML counterpart with canonical, embedded JSON-LD, alternate raw JSON-LD, provenance, and attribution metadata; deterministic sitemap `lastmod` values and a weekly production MIME check cover publication integrity.
- [x] The explorer surfaces typed mechanics, unparsed attack dispositions, raw tables, background/species prose and choices, relation names/edges, semantic/physical table provenance, a search-index download warning, and explicit short-query errors.
- [x] CI uses pinned actions, read-only permissions, concurrency cancellation, a Python 3.12/3.13 matrix, and the scheduled production check.
- [x] Determinism covers two clean builds and checked-in `objects/`, `records/`, `llms.txt`, `llms-full.txt`, `vocab/`, and `sitemap.xml`, including curated review-policy inputs.
- [x] `README.md`, `SPECIFICATION.md`, manifest version, inventory counts, generated command summaries, and this checklist agree with the clean v0.4.0 build.
