# SRD 5.2.1 System JSON

Machine-readable reference data for the System Reference Document 5.2.1 (D&D fifth edition rules), using JSON-LD 1.1 and JSON Schema Draft 2020-12. The architecture replicates [wwn-system-json](https://cheeleong.dev/wwn-system-json/) per its replication playbook.

## Layout

- `SRD_CC_v5.2.1.md` — the authoritative CC-BY-4.0 source markdown (frozen; SHA-256 asserted by tests).
- `objects/` — one JSON-LD file per entity: rules, tables, spells, feats, magic items, monsters, plus source provenance, the aggregate manifest, the single-file bundle, and the static search index.
- `systems/` — JSON-LD 1.1 context and Draft 2020-12 schemas.
- `scripts/` — deterministic extraction, manifest/bundle/llms/search-index builders, and validators.
- `tests/` — structural test suite.
- `SPECIFICATION.md` — authoritative architecture, extraction rules, and audit baseline.
- `CHECKLIST.md` — replication blueprint with live completion status.

## Quickstart

```bash
make install   # sync dev dependencies with uv
make check     # full rebuild + tests + structural/schema validation + determinism
```

## Corpus inventory (v0.1.0)

| Collection | Records | Schema |
| --- | --- | --- |
| sources | 1 | `source.schema.json` |
| rules | 1,113 | `rule.schema.json` |
| tables | 258 | `table.schema.json` |
| spells | 338 | `spell.schema.json` |
| feats | 17 | `feat.schema.json` |
| magic-items | 258 | `magic-item.schema.json` |
| monsters | 332 | `monster.schema.json` |
| **total** | **2,317** | |

## Conventions

Every entity has an absolute canonical `@id` under the base IRI `https://cheeleong.dev/graph20/`, a JSON-LD `@type`, a slug, a source reference, and a `sourceLocator` (chapter, section, heading, line bounds) tracing it to the SRD markdown. Source wording is preserved verbatim in `rulesText`; structured fields (spell level/school, monster stats, item rarity, ...) are indexes, never replacements. Source OCR anomalies are handled only through the reviewed registry in `objects/sources/extraction-overrides.json`.

## Source, license, and attribution

Repository-authored code, schemas, and documentation are MIT licensed (see `LICENSE`). SRD content is used under CC-BY-4.0 with the required attribution:

> This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.

This is an independent, unofficial project, not affiliated with, sponsored by, or endorsed by Wizards of the Coast.
