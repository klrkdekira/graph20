# SRD 5.2.1 System JSON

[![CI](https://github.com/klrkdekira/graph20/actions/workflows/ci.yml/badge.svg)](https://github.com/klrkdekira/graph20/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](https://github.com/klrkdekira/graph20)
[![JSON-LD 1.1](https://img.shields.io/badge/JSON--LD-1.1-blue.svg)](https://www.w3.org/TR/json-ld11/)
[![Content License: CC BY 4.0](https://img.shields.io/badge/Content_License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Code License: MIT](https://img.shields.io/badge/Code_License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A source-faithful, machine-readable edition of the **System Reference Document 5.2.1**. The repository turns the CC-BY-4.0 source Markdown into 2,107 modular records across 13 collections, with:

- JSON-LD 1.1 identity and graph relationships;
- JSON Schema Draft 2020-12 contracts;
- the original SRD prose alongside typed fields for discovery and filtering; and
- line-level provenance back to the authoritative source.

This is a reference corpus, not a rules engine or character builder.

[Explore the corpus](https://cheeleong.dev/graph20/) · [Read the vocabulary](https://cheeleong.dev/graph20/vocab/) · [Technical specification](SPECIFICATION.md) · [LLM guide](llms.txt)

## Start here

The repository is published as static files, so consumers do not need an API key, database, or runtime.

| I want to… | Start with |
| --- | --- |
| Browse and search the SRD | [Web explorer](https://cheeleong.dev/graph20/) |
| Fetch one record | [`objects/<collection>/<slug>.jsonld`](objects/spells/fireball.jsonld) |
| Load the complete graph | [`objects/srd52-system-data.bundle.jsonld`](https://cheeleong.dev/graph20/objects/srd52-system-data.bundle.jsonld) |
| Discover collections and record IDs | [`objects/srd52-system-data.jsonld`](https://cheeleong.dev/graph20/objects/srd52-system-data.jsonld) |
| Build a search or browse UI | [`objects/search-index.json`](https://cheeleong.dev/graph20/objects/search-index.json) and [`objects/collection-index.json`](https://cheeleong.dev/graph20/objects/collection-index.json) |
| Give the corpus to an LLM | [`llms-full.txt`](https://cheeleong.dev/graph20/llms-full.txt) |
| Resolve classes and properties | [`vocab/terms.json`](https://cheeleong.dev/graph20/vocab/terms.json) |
| Validate an integration | [`systems/`](systems/) |

For example, fetch a single spell or the complete bundle:

```bash
curl -fsSL https://cheeleong.dev/graph20/objects/spells/fireball.jsonld
curl -fsSL https://cheeleong.dev/graph20/objects/srd52-system-data.bundle.jsonld -o srd52.jsonld
```

Record files use the path `objects/<collection>/<slug>.jsonld`. Inside a record, the canonical `@id` omits the file extension:

```json
{
  "@context": "https://cheeleong.dev/graph20/systems/context.jsonld",
  "@id": "https://cheeleong.dev/graph20/objects/spells/fireball",
  "@type": "Spell",
  "name": "Fireball",
  "source": {
    "@id": "https://cheeleong.dev/graph20/objects/sources/srd-5-2-1"
  },
  "sourceLocator": {
    "chapter": "Spells",
    "section": "7.154",
    "heading": "Fireball",
    "lineStart": 9321,
    "lineEnd": 9334
  },
  "level": 3,
  "school": "Evocation",
  "classes": [
    { "@id": "https://cheeleong.dev/graph20/objects/classes/sorcerer" },
    { "@id": "https://cheeleong.dev/graph20/objects/classes/wizard" }
  ]
}
```

The example is abbreviated. The full record also retains `rulesText`, printed spell headers, and typed mechanics.

## Published artifacts

| Artifact | Purpose |
| --- | --- |
| [`objects/srd52-system-data.jsonld`](https://cheeleong.dev/graph20/objects/srd52-system-data.jsonld) | Manifest containing corpus metadata, source and corpus digests, collection descriptors, member links, and schema links. |
| [`objects/srd52-system-data.bundle.jsonld`](https://cheeleong.dev/graph20/objects/srd52-system-data.bundle.jsonld) | All 2,107 records in one JSON-LD `@graph`. |
| [`objects/search-index.json`](https://cheeleong.dev/graph20/objects/search-index.json) | Static inverted index over all records and nested text fragments. |
| [`objects/collection-index.json`](https://cheeleong.dev/graph20/objects/collection-index.json) | Compact display and filter metadata such as spell level, monster CR, and item rarity. |
| [`systems/context.jsonld`](https://cheeleong.dev/graph20/systems/context.jsonld) | Shared JSON-LD context, including IRI coercion rules. |
| [`systems/*.schema.json`](systems/) | Draft 2020-12 schemas for records, aggregates, and verification reports. |
| [`vocab/terms.json`](https://cheeleong.dev/graph20/vocab/terms.json) | Definitions for the 14 classes and 144 properties in the project vocabulary. |
| [`llms.txt`](https://cheeleong.dev/graph20/llms.txt) / [`llms-full.txt`](https://cheeleong.dev/graph20/llms-full.txt) | LLM-oriented entry point and full recursive text projection. |
| [`objects/sources/source-coverage.json`](objects/sources/source-coverage.json) / [`source-review-ledger.json`](objects/sources/source-review-ledger.json) | Machine-readable coverage and semantic-review reports. |
| [`datapackage.json`](datapackage.json) | Frictionless Data Package metadata and resource listing. |

## Corpus inventory

The v0.4.0 build contains:

| Collection | Records | What is represented |
| --- | ---: | --- |
| `sources` | 1 | Source identity, version, rights, attribution, and SHA-256 digest |
| `rules` | 736 | General rules, chapters, and glossary prose |
| `tables` | 235 | Logical tables with ordered rows, raw Markdown, and physical spans |
| `classes` | 12 | Core traits, level progression, and nested features |
| `subclasses` | 12 | Subclass features and parent-class links |
| `species` | 9 | Creature type, size, speed, traits, and prose |
| `backgrounds` | 4 | Ability scores, feats, proficiencies, and prose |
| `feats` | 17 | Category, prerequisites, repeatability, benefits, and prose |
| `equipment` | 133 | Weapons, armor, and gear indexed from source tables |
| `spells` | 339 | Printed headers, class links, typed mechanics, and prose |
| `conditions` | 15 | Rules Glossary conditions and their effects |
| `magic-items` | 258 | Rarity variants, attunement clauses, tables, and prose |
| `monsters` | 336 | Stat blocks, traits, actions, attacks, and ability scores |
| **Total** | **2,107** | **18,047 in-scope, non-blank source lines covered** |

## Data model and guarantees

The project is designed for source-backed reference and retrieval workloads:

- **Stable identity.** Every entity has a lowercase-kebab-case canonical `@id` under `https://cheeleong.dev/graph20/` and an `@type` defined by the shared context.
- **Graph-safe links.** Semantic relationships use `{ "@id": "…" }` node references. `$ref` is reserved for JSON Schema composition.
- **Source-backed relations.** Class spell-list tables use `listsSpell`; magic items use `castsSpell`; exact condition phrases use `mentionsCondition`; backgrounds use `grantsFeat`; and monster gear uses `hasGear`. Display strings remain alongside every link.
- **Source-faithful prose.** `rulesText` and `description` preserve source wording. Typed sibling fields are indexes, not replacements for the prose.
- **Physical provenance.** `sourceLocator` identifies the source chapter, section, heading, and inclusive line range. Nested class features and monster sections are locatable too.
- **No invented values.** Extraction does not fill gaps in the source. A truncated table cell remains omitted rather than inferred.
- **Reviewed normalization.** Source-conversion fixes are recorded in [`objects/sources/extraction-overrides.json`](objects/sources/extraction-overrides.json), including observed text, disposition, rationale, and affected records.
- **Deterministic output.** Clean builds contain no timestamps or random ordering and must reproduce the checked-in artifacts byte for byte.

The build currently reports 100% interval coverage of the 18,047 in-scope, non-blank source lines. Coverage means every line falls within at least one record locator; the separate fidelity, graph, schema, anomaly, and review gates test stronger claims.

See [SPECIFICATION.md](SPECIFICATION.md) for the source boundary, extraction grammar, architecture, and acceptance criteria. [CHECKLIST.md](CHECKLIST.md) tracks the replication blueprint, and [AUDIT.md](AUDIT.md) records resolved and open audit findings.

## Development

### Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

Install the locked development environment and run the full verification pipeline:

```bash
make install
make check
```

`make check` first verifies that checked-in generated artifacts are reproducible, then rebuilds the corpus and runs every validation gate. CI also requires the working tree to remain clean after the pipeline.

Generated files under `objects/` must not be edited by hand, except for `objects/sources/extraction-overrides.json`. Change the extraction or build scripts, then regenerate the affected artifacts.

For the common extraction path:

```bash
make extract manifest bundle llms-full search-index
make test validate schema
make determinism
```

### Make targets

| Target | Result |
| --- | --- |
| `install` | Synchronize the locked development dependencies with uv. |
| `extract` | Re-extract modular records from `SRD_CC_v5.2.1.md`. |
| `manifest` / `bundle` | Rebuild the aggregate manifest and single-file graph. |
| `llms-full` | Regenerate the recursive LLM text projection. |
| `search-index` / `collection-index` | Rebuild full-text search postings and compact browse metadata. |
| `coverage` | Check interval coverage of in-scope source lines. |
| `review` / `review-stats` | Rebuild or summarize the occurrence-level semantic review ledger. |
| `vocab` / `sitemap` | Rebuild vocabulary documentation and the published sitemap. |
| `anomalies` | Reject unreviewed source-conversion anomaly candidates. |
| `fidelity` | Check locator ownership, table shape, and typed/source fidelity. |
| `graph` | Expand JSON-LD and reject data loss or invalid IRI values. |
| `test` | Run the structural regression suite. |
| `validate` | Check identities, bounds, references, indexes, sitemap, and vocabulary targets. |
| `schema` | Validate records and auxiliary artifacts against their JSON Schemas. |
| `determinism` | Compare clean builds with each other and with checked-in output. |
| `check` | Run the complete build and verification gate. |

Run `make help` for the short command reference. Every Python target executes through `uv run` using the locked environment.

## Repository layout

```text
graph20/
├── SRD_CC_v5.2.1.md       # Authoritative in-scope CC-BY-4.0 source
├── objects/               # Generated records, manifest, bundle, and indexes
│   └── sources/           # Source metadata and extraction/review reports
├── systems/               # JSON-LD context and JSON Schema contracts
├── vocab/                 # Vocabulary browser and machine-readable terms
├── reviews/               # Curated semantic-review policy input
├── scripts/               # Deterministic extraction, build, and validation tools
├── tests/                 # Structural regression tests
├── index.html             # Dependency-free static web explorer
├── llms.txt               # LLM-oriented corpus guide
├── llms-full.txt          # Full recursive text projection
├── SPECIFICATION.md       # Source of truth for architecture and acceptance
└── Makefile               # Build and verification entry points
```

## Scope

`SRD_CC_v5.2.1.md` is the sole content source. Material from rulebooks, wikis, other SRD versions, or external datasets is not mixed into the corpus. Executable rules interpretation, campaign state, character building, and automation inferred from prose are intentionally out of scope.

The architecture follows the replication approach established by [wwn-system-json](https://cheeleong.dev/wwn-system-json/).

## License and attribution

Repository-authored code, schemas, and documentation are available under the [MIT License](LICENSE). SRD content is used under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) with the required attribution:

> This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.

Project citation metadata is available in [`CITATION.cff`](CITATION.cff).

This is an independent, unofficial reference project and is not affiliated with, sponsored by, or endorsed by Wizards of the Coast LLC.
