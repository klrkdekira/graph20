# SRD 5.2.1 System JSON

[![CI](https://github.com/klrkdekira/graph20/actions/workflows/ci.yml/badge.svg)](https://github.com/klrkdekira/graph20/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](https://github.com/klrkdekira/graph20)
[![JSON-LD 1.1](https://img.shields.io/badge/JSON--LD-1.1-blue.svg)](https://www.w3.org/TR/json-ld11/)
[![Content License: CC BY 4.0](https://img.shields.io/badge/Content_License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Code License: MIT](https://img.shields.io/badge/Code_License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Machine-readable JSON-LD 1.1 reference corpus and JSON Schema Draft 2020-12 specifications for the System Reference Document 5.2.1 (D&D 5th Edition rules, CC-BY-4.0). The architecture replicates [wwn-system-json](https://cheeleong.dev/wwn-system-json/) per its replication playbook.

The corpus provides 2,097 source-faithful records across 13 collections, covering rules, logical tables, character classes, subclasses, species, backgrounds, feats, equipment, spells, conditions, magic items, and monster stat blocks. Records carry verbatim SRD prose, structured index fields, graph links where asserted, and line-level physical source provenance tracing back to the authoritative source markdown.

- **Live Web Explorer**: [https://cheeleong.dev/graph20/](https://cheeleong.dev/graph20/)
- **Vocabulary & Ontology**: [https://cheeleong.dev/graph20/vocab/](https://cheeleong.dev/graph20/vocab/)
- **Technical Specification**: [SPECIFICATION.md](SPECIFICATION.md)
- **Replication Checklist**: [CHECKLIST.md](CHECKLIST.md)
- **Gap Register**: [AUDIT.md](AUDIT.md) — fixed and open gaps from the 2026-08-24 corpus audit

---

## Key Entry Points

| Artifact | Location / URL | Description |
| --- | --- | --- |
| **Web Explorer** | [`index.html`](https://cheeleong.dev/graph20/) | Zero-dependency browser interface to search, filter, and inspect records. |
| **Vocabulary Browser** | [`vocab/index.html`](https://cheeleong.dev/graph20/vocab/) | Human- and machine-readable index of 139 properties and 14 classes. |
| **Vocabulary Terms** | [`vocab/terms.json`](https://cheeleong.dev/graph20/vocab/terms.json) | Complete term definitions and descriptions under `https://cheeleong.dev/graph20/vocab/#`. |
| **LLM Context (Full)** | [`llms-full.txt`](https://cheeleong.dev/graph20/llms-full.txt) | 52,000+ line single-file recursive text projection for LLM analysis. |
| **LLM Guide** | [`llms.txt`](https://cheeleong.dev/graph20/llms.txt) | High-level index and entry point for LLM agents. |
| **JSON-LD Manifest** | [`objects/srd52-system-data.jsonld`](https://cheeleong.dev/graph20/objects/srd52-system-data.jsonld) | Aggregate manifest with collection descriptors, member links, and source digests. |
| **Single-File Bundle** | [`objects/srd52-system-data.bundle.jsonld`](https://cheeleong.dev/graph20/objects/srd52-system-data.bundle.jsonld) | Complete 2,097-record graph in a single JSON-LD `@graph` document. |
| **Inverted Search Index** | [`objects/search-index.json`](https://cheeleong.dev/graph20/objects/search-index.json) | Static inverted token search index with fragment excerpts. |
| **Collection Index** | [`objects/collection-index.json`](https://cheeleong.dev/graph20/objects/collection-index.json) | Compact catalog metadata (names, levels, CRs, rarities, groupings) for UIs. |
| **JSON-LD Context** | [`systems/context.jsonld`](https://cheeleong.dev/graph20/systems/context.jsonld) | JSON-LD 1.1 mapping for terms, types, and IRI coercions. |
| **JSON Schemas** | [`systems/*.schema.json`](systems/) | Draft 2020-12 schemas for all 13 collections, bundles, manifest, and indexes. |
| **Data Package** | [`datapackage.json`](datapackage.json) | Frictionless Data Package metadata and resource listings. |
| **Source Review Ledger** | [`objects/sources/source-review-ledger.json`](https://cheeleong.dev/graph20/objects/sources/source-review-ledger.json) | 1,974 reviewed occurrence signals with zero pending items. |
| **Extraction Overrides** | [`objects/sources/extraction-overrides.json`](objects/sources/extraction-overrides.json) | Log of verified source fixes against the official PDF text layer. |
| **Source Coverage** | [`objects/sources/source-coverage.json`](objects/sources/source-coverage.json) | Verification report covering 100% (18,050 lines) of in-scope content. |

---

## Repository Layout

```
graph20/
├── SRD_CC_v5.2.1.md          # Authoritative CC-BY-4.0 source markdown (frozen digest)
├── index.html                # Zero-dependency web explorer (browser UI)
├── llms.txt                  # High-level index for LLM agents
├── llms-full.txt             # Full-corpus recursive textual projection
├── sitemap.xml               # XML sitemap covering all 2,106 entities and pages
├── robots.txt                # Crawler directives
├── datapackage.json          # Frictionless Data Package definition
├── CITATION.cff              # Citation metadata (CFF 1.2.0)
├── SPECIFICATION.md          # Authoritative architecture, rules, and acceptance criteria
├── CHECKLIST.md              # Blueprint with live completion status
├── Makefile                  # Build, validation, and test automation
├── pyproject.toml            # Python environment & dev dependency configuration
├── objects/                  # Generated JSON-LD entities and aggregate indexes
│   ├── backgrounds/          # 4 Character background records
│   ├── classes/              # 12 Core class records (with nested feature locators)
│   ├── conditions/           # 15 Rules glossary condition records
│   ├── equipment/            # 133 Typed weapons, armor, and gear records
│   ├── feats/                # 17 Feat records with prerequisites and benefits
│   ├── magic-items/          # 258 Magic item records with rarity variants & attunement
│   ├── monsters/             # 336 Monster stat blocks with typed attacks & abilities
│   ├── rules/                # 738 General rules and prose section records
│   ├── sources/              # 1 Source record, coverage, overrides, review ledger
│   ├── species/              # 9 Character species records
│   ├── spells/               # 339 Spell records with class links & typed mechanics
│   ├── subclasses/           # 12 Subclass records
│   ├── tables/               # 223 Logical source table records (rawText + structured)
│   ├── collection-index.json # Display metadata for rapid UI lookup and filtering
│   ├── search-index.json     # Static token search index
│   ├── srd52-system-data.jsonld        # Aggregate JSON-LD manifest
│   └── srd52-system-data.bundle.jsonld # Single-file all-entity JSON-LD bundle
├── systems/                  # JSON-LD 1.1 context and JSON Schema Draft 2020-12 schemas
├── vocab/                    # Published vocabulary browser and term index
│   ├── index.html            # Static HTML vocabulary reference
│   └── terms.json            # Machine-readable dictionary of project classes/properties
├── reviews/                  # Curated semantic review policies and occurrence overrides
├── scripts/                  # Deterministic extraction, builders, and validation gates
└── tests/                    # Structural test suite (Python unittest)
```

---

## Corpus Inventory (v0.4.0)

| Collection | Records | Schema | Description |
| --- | ---: | --- | --- |
| `sources` | 1 | `source.schema.json` | Provenance, version, CC-BY-4.0 license, attribution, and SHA-256 digest |
| `rules` | 738 | `rule.schema.json` | Source-faithful general rules, chapters, and glossary entries |
| `tables` | 223 | `table.schema.json` | Logical source tables (headers, rows, raw markdown, and spans) |
| `classes` | 12 | `class.schema.json` | Core traits (`name`/`value`), level progression, nested feature locators |
| `subclasses` | 12 | `subclass.schema.json` | Subclass features, levels, and parent class `@id` links |
| `species` | 9 | `species.schema.json` | Creature type, size, speed, species traits, and prose |
| `backgrounds` | 4 | `background.schema.json` | Ability scores, granted feats, tool proficiencies, and prose |
| `feats` | 17 | `feat.schema.json` | Category, prerequisites, repeatability, benefits, and prose |
| `equipment` | 133 | `equipment.schema.json` | Weapons, armor, gear with typed damage, properties, costs, and weights |
| `spells` | 339 | `spell.schema.json` | Level, school, class links, printed headers, typed saves/damage/scaling |
| `conditions` | 15 | `condition.schema.json` | Glossary condition rules, bulleted effects, and locators |
| `magic-items` | 258 | `magic-item.schema.json` | All rarity variants, attunement clauses/prerequisites, and tables |
| `monsters` | 336 | `monster.schema.json` | Ability scores, 423 typed damaging attacks, 6 explicit unparsed dispositions, condition immunities |
| **Total** | **2,097** | | **100% source line coverage (18,050 non-blank content lines)** |

### Semantic Graph Enrichment

- **Spells**: Linked to class `@id` nodes (`classes`), retaining all 5 printed spell headers (Level & School, Casting Time, Range, Components, Duration) alongside structured fields for saving throws, damage dice, damage types, healing, and upcast scaling.
- **Monsters**: 336 complete stat blocks (including the 6 summoned-creature stat blocks printed in the Spells and Magic Items chapters) with observed ability entries, 423 parsed damaging attacks with typed modifiers/reach/damage components, 6 explicit unparsed attack dispositions (the Roper *Tentacle* plus 5 summon attacks whose bonus scales with the caster), condition-immunity node references, traits, and action sections.
- **Classes & Subclasses**: Graph-safe typed trait entries (`name`, `value`), ordered level progressions, and nested feature structures retaining exact source line spans.
- **Magic Items**: Complete retention of rarity variants, full attunement clauses with prerequisites, and embedded logical tables.
- **Equipment**: Weapons, armor, and gear indexed from source tables with typed damage, damage types, mastery/armor properties, costs, and weights; semantic slugs decoded from conversion HTML markup.
- **Tables**: 223 logical tables preserving physical markdown spans and `rawText`. Continued table headers across pages are consolidated without duplicating data rows.

---

## Data Conventions & Architecture

- **JSON-LD 1.1**: Every entity carries a canonical `@id` under `https://cheeleong.dev/graph20/`, a `@type`, and references the shared context (`systems/context.jsonld`).
- **Strict JSON Schemas**: Every collection, manifest, bundle, index, coverage report, and review ledger is validated against JSON Schema Draft 2020-12, rejecting unevaluated properties on leaf entities.
- **Relational Integrity**: All semantic links use `{ "@id": "..." }` node references. Predicates declared as `@type: "@id"` in the context are never emitted as bare strings.
- **Line-Level Physical Provenance**: Every extracted entity (and every class feature and monster stat section) carries a `sourceLocator` (`chapter`, `section`, `heading`, `lineStart`, `lineEnd`) tracing it directly to `SRD_CC_v5.2.1.md`.
- **Zero Derived Values**: The parser never derives missing values or invents data (e.g. truncated ability modifier table cells stay omitted).
- **Source Fidelity & Normalization**: The source markdown underwent documented normalization passes (`scripts/repair_source.py`) cross-referenced against the official PDF text layer. All observed anomalies and approved fixes are registered in `objects/sources/extraction-overrides.json`.
- **Occurrence Review Ledger**: Occurrence-level review ledger tracks 1,974 semantic signals with policies in `reviews/semantic-review-policies.json`, maintaining zero pending signals across clean builds.
- **Published Vocabulary**: All 139 properties and 14 classes declared by the project context are defined with dereferenceable fragment IRIs under `https://cheeleong.dev/graph20/vocab/#`.

---

## Quickstart & Commands

### Setup

```bash
make install   # sync development dependencies with uv
```

### Full Verification & Build Pipeline

```bash
make check     # full rebuild + test suite + validation gates + determinism
```

`make check` executes all extraction, artifact generation, verification gates, schema validations, and byte-for-byte determinism checks in sequence.

### Available Makefile Targets

| Target | Command | Description |
| --- | --- | --- |
| `install` | `uv sync --group dev` | Synchronize Python dependencies. |
| `extract` | `python scripts/extract_srd.py` | Deterministically extract 2,097 JSON-LD records from `SRD_CC_v5.2.1.md`. |
| `manifest` | `python scripts/build_manifest.py` | Build the aggregate JSON-LD manifest (`objects/srd52-system-data.jsonld`). |
| `bundle` | `python scripts/build_bundle.py` | Build the single-file JSON-LD graph bundle (`objects/srd52-system-data.bundle.jsonld`). |
| `llms-full` | `python scripts/build_llms_full.py` | Generate single-file recursive text projection (`llms-full.txt`). |
| `search-index` | `python scripts/build_search_index.py` | Build the static inverted token search index (`objects/search-index.json`). |
| `collection-index` | `python scripts/build_collection_indexes.py` | Build the compact UI catalog metadata (`objects/collection-index.json`). |
| `vocab` | `python scripts/build_vocab.py` | Rebuild vocabulary documentation and term dictionary (`vocab/`). |
| `sitemap` | `python scripts/build_sitemap.py` | Generate XML sitemap (`sitemap.xml`) for web publishing. |
| `coverage` | `python scripts/build_coverage.py` | Verify 100% interval line coverage of in-scope source markdown. |
| `anomalies` | `python scripts/check_anomalies.py` | Run 12 detector checks against unreviewed OCR/conversion anomalies. |
| `fidelity` | `python scripts/validate_fidelity.py` | Verify locator bounds, table shapes, raw text, and typed field fidelity. |
| `graph` | `python scripts/validate_graph.py` | Expand the complete JSON-LD graph and assert zero data loss or uncoerced IRIs. |
| `review` | `python scripts/build_review_ledger.py` | Rebuild the semantic review ledger and reject any pending signals. |
| `review-stats` | `python scripts/manage_review_ledger.py --stats` | Display occurrence ledger summary statistics. |
| `test` | `python -m unittest discover -s tests -v` | Run the Python unittest test suite. |
| `validate` | `python scripts/validate.py` | Structural validation of identity, bounds, references, and search postings. |
| `schema` | `python scripts/validate_schema.py` | Validate all records and auxiliary files against JSON Schema Draft 2020-12. |
| `determinism` | `python scripts/check_determinism.py` | Assert clean builds are byte-identical with checked-in artifacts. |
| `check` | *(all targets above)* | Full verification pipeline and build gate. |

---

## Static Web Explorer

The repository includes a dependency-free static web application in `index.html` (hosted on GitHub Pages at [https://cheeleong.dev/graph20/](https://cheeleong.dev/graph20/)):

- **Instant Full-Text Search**: Powered by `objects/search-index.json`, providing token matching and excerpt highlighting across rules, features, spells, and stat blocks.
- **Collection Filtering & Browsing**: Filter by collection, spell level/school, monster CR, magic item rarity, or equipment category using `objects/collection-index.json`.
- **Rich Record Inspector**: Formatted views for monster stat blocks, spell descriptions, class trait tables, magic items, equipment stats, logical tables, and rules.
- **JSON-LD & Source Inspector**: Live view of underlying JSON-LD and direct source markdown line range links.

---

## Source, License, and Attribution

Repository-authored code, schemas, and documentation are MIT licensed (see [`LICENSE`](LICENSE)). SRD content is used under CC-BY-4.0 with the required attribution:

> This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.

*This is an independent, unofficial reference project and is not affiliated with, sponsored by, or endorsed by Wizards of the Coast LLC.*

