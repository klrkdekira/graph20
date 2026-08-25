# SRD 5.2.1 System JSON — Technical Specification

Status: v0.4.0. The source-boundary, graph-fidelity, physical-provenance, table, recursive-ingestion, typed-extraction, review, verification, vocabulary, and documentation requirements are implemented and enforced by `make check`.

## 1. Objective

Turn the local CC-BY-4.0 `SRD_CC_v5.2.1.md` into a modular, machine-readable SRD 5.2.1 corpus with JSON-LD 1.1 identity and relationships, JSON Schema Draft 2020-12 contracts, one file per reusable entity, aggregate artifacts, physical source traceability, and source-faithful prose.

The corpus is reference data. Executable rules engines, character builders, campaign state, and automation inferred from prose remain out of scope.

## 2. Source and legal boundary

`SRD_CC_v5.2.1.md` is the sole content source. It represents the System Reference Document 5.2.1 by Wizards of the Coast LLC under CC-BY-4.0. The required attribution statement is preserved exactly in the source record, manifest, README, and `llms-full.txt`.

Each source-normalization event was compared directly with the official PDF text layer. Observed tokens, fixes, rationale, disposition, affected classes, and pre/post digests are registered in `objects/sources/extraction-overrides.json`. The obsolete open5e comparison cache was removed and no external dataset contributes retained assertions. Extraction never derives a missing ability modifier or saving throw: incomplete observed cells remain omitted, as verified through extraction, bundle generation, LLM projection, and repeated rebuilds.

The repair step has exact preconditions and postconditions for every cataloged conversion anomaly, including column splices, sidebars promoted to headings, phantom headings, split tables, compacted monster stat lines, and glued sentences. It is idempotent and fails if an expected observed token changes. The Telekinesis sentence ending at “manipulating a simple tool” was checked on page 167 of the official SRD 5.2.1 PDF and is recorded as an upstream anomaly, not silently completed from another rulebook.

## 3. Corpus scope

The v0.4.0 clean build contains 2,226 records:

| Collection | Count | Content |
| --- | ---: | --- |
| sources | 1 | Origin, version, license, attribution, canonical IRI, and SHA-256 digest |
| rules | 708 | Source-faithful general rules and untagged prose sections |
| actions / areas-of-effect / attitudes / hazards | 12 / 6 / 3 / 5 | Tagged Rules Glossary entity families and named effects |
| tables | 224 | Logical source tables with semantic captions, columns, ordered rows, raw source table text, and physical spans |
| classes / subclasses | 12 / 12 | Graph-safe core-trait entries, nested feature text and locators, and class relationships |
| invocations / metamagic-options | 28 / 10 | Typed class option catalogs, costs, prerequisites, and relationships |
| species / backgrounds | 9 / 4 | Typed origin fields plus source prose |
| feats | 17 | Category, prerequisite, repeatability, and prose |
| equipment | 227 | Weapons, armor, gear, tools, mounts, vehicles, services, focuses, ammunition, food, and lodging |
| spells | 339 | Level, school, classes, printed headers, parsed range/components/duration/saves/areas, and prose |
| conditions | 15 | Rules Glossary conditions |
| magic-items | 258 | Complete rarity variants, complete-header attunement, tables, and prose |
| monsters | 336 | Decomposed identity/stats, movement, senses, languages, spellcasting, 423 parsed damaging attacks, six explicit unparsed dispositions, sections, and prose |

The 224 Table records represent logical tables rather than PDF page fragments, including tables nested in spell, species, and magic-item records. `sourceLocator.heading` preserves the physical owner while optional `caption` carries the semantic table name. Repeated continuation headers remain in `rawText` but are not promoted to data rows. Trinkets is one ordered 100-row table, Prismatic Rays is one ordered 8-row table, Wand of Wonder is one ordered 18-row table, Robe of Useful Items and Sphere of Annihilation roll tables are structured, and no emitted table is empty.

## 4. Data architecture

| Concern | Decision |
| --- | --- |
| Base IRI | `https://cheeleong.dev/graph20/` |
| Vocabulary | Fragment IRIs under `https://cheeleong.dev/graph20/vocab/#` |
| Context | `systems/context.jsonld`, JSON-LD 1.1 |
| Schemas | Draft 2020-12; leaf entities reject unevaluated properties |
| Identity | Stable lowercase-kebab-case canonical `@id` values |
| Relationships | `{ "@id": "..." }` node references only; never bare strings under IRI-coerced predicates |
| Prose | Source wording in `rulesText`/`description`; structured fields remain indexes |
| Class traits | Typed `{ "name", "value" }` entries, not arbitrary JSON-LD property maps |
| Manifest | Graph-safe collection descriptors with member and schema node references |
| Aggregates | Manifest, member-validated JSON-LD bundle, generated LLM guides, recursive search index, exact collection index, build metrics, vocabulary, crawlable record pages, and sitemap |

Exact source-name matches produce typed relations without replacing their printed strings. Twenty-two emitted predicates cover class spell lists, active casting clauses, condition phrases and immunities, background grants, monster gear and spellcasting, summons, areas, option catalogs, table/rule provenance, explicit related-rule references, and catalog membership. IRI-coerced predicates always carry node-reference objects. Core incoming directions also have documented JSON-LD `@reverse` aliases. The graph gate enforces at least 55% outbound semantic-link coverage, at least 20 used predicates, and an incoming edge for every non-source collection.

Every nested class/subclass feature and monster stat section carries or inherits a physical source locator. Ordinary entity locators start at their declared heading; Table and equipment locators start at their physical source table. Parent spans contain every nested feature span.

## 5. Extraction rules

The normalized Markdown has a flat `#` heading structure. Chapter starts are matched sequentially using `srdlib.CHAPTERS`; repeated interior titles do not start a new chapter. Catalog entities are recognized from body grammar:

- spells: printed level/school/class header;
- feats: printed feat category header;
- magic items: complete category, all rarity variants, and complete attunement clause;
- monsters: size/type/alignment line, with reviewed stat/action headings folded into the owner;
- classes: printed core-trait table followed by level features and one in-scope subclass;
- equipment: printed Weapons, Armor, Adventuring Gear, Tools, Mounts, Vehicles, Tack, Focuses, Ammunition, Hirelings, Food/Lodging, and Spellcasting Services structures.

Tables preserve their physical source span and `rawText`. The parser filters repeated continuation headers from normalized rows. Attack parsing is paragraph-based, accepts `ft.`/`feet`, optional `to hit`, conditional bonuses, flat damage, and multiple damage components, and records a source-text path and `parseStatus`. Any unmatched attack paragraph must carry an explicit reason.

Structured display names decode reviewed HTML character references while source prose remains source-faithful. The anomaly registry and `make anomalies` prevent new unreviewed OCR/conversion candidates.

## 6. Recursive text and review

`srdlib.iter_text_fragments` is the shared recursive projection for `llms-full.txt`, full-text search, and review. It covers nested features/traits/stat sections, table cells, core traits, and structured-only equipment fields. LLM rendering suppresses redundant contained fragments without dropping their exact text. Search postings carry an excerpt from the matched nested fragment.

The occurrence-level ledger records stable keys, structural paths, source line/column, surrounding context, status, and note. Curated category policies, a reviewed signal-set digest, and occurrence overrides live in `reviews/semantic-review-policies.json`, outside generated output, so clean builds preserve them. Status meanings are published in the generated ledger. Any added, removed, or moved occurrence changes the digest and becomes pending until the set is reviewed. `make review` rejects unknown/new pending signals; the current ledger has zero pending occurrences and includes audit checks for typed/source fidelity, table shape, provenance, anomaly disposition, and graph shape.

## 7. Verification

`make check` rebuilds every artifact and runs distinct gates. `pyproject.toml` is the single project-version source; structural validation cross-checks it against the manifest, bundle, metrics, data package, citation metadata, README, specification, and explorer.

- `coverage`: interval coverage only; currently all 18,016 non-blank content lines from line 29 onward are inside at least one locator. It does not claim ownership or fidelity.
- `anomalies`: every detector hit must have a reviewed registry disposition.
- `fidelity`: headings/table starts, nested containment, raw tables, observed spell/equipment/feat/species/background/monster/magic-item values, attack dispositions, and contributing-source rights metadata.
- `graph`: expands every record, manifest, and bundle; rejects lost compact properties/literals, bare IRI-coerced strings, missing entity types, undocumented terms, inadequate link density, absent incoming collection edges, and missing reverse aliases.
- `review`: regenerates occurrence-level signals and rejects pending or unlocatable occurrences.
- `test`: regression fixtures for source boundaries, truncated ability cells, folded monster headings, subclass/table spans, continued tables, complete typed headers, recursive LLM/search, and vocabulary targets.
- `validate`: identity, bounds, exact source rights/digest, version agreement, reference resolution, exact collection/sitemap projections, record pages and JSON-LD alternates, explorer smoke structure, recomputed metrics, search postings, and vocabulary targets.
- `schema`: every record, every bundled graph member, manifest, bundle envelope, search index, collection index, metrics, coverage report, and review ledger against Draft 2020-12 schemas.
- `determinism`: compares two clean builds with each other and with checked-in `objects/`, `records/`, both LLM artifacts, `vocab/`, and `sitemap.xml`, preserving curated review policy input.

Every record publishes `htmlPage`, and every generated HTML counterpart contains canonical, JSON-LD alternate, embedded JSON-LD, source provenance, and attribution metadata. The sitemap contains those HTML URLs with the deterministic SRD publication date as `lastmod`. Production currently serves `.jsonld` files as `application/ld+json`; a weekly CI probe detects hosting regressions. CI uses pinned actions, least-privilege permissions, concurrency cancellation, and Python 3.12/3.13 checks.

`objects/build-metrics.json` is generated after all other artifacts and schema-validated. It is the asserted source for record/collection totals, source coverage, vocabulary size, search size, review status, LLM lines, sitemap/page counts, relation counts, and semantic coverage; structural validation recomputes the file rather than trusting documentation prose.

These automated gates establish the repository acceptance criteria; they do not make the project official or expand the source/legal scope.
