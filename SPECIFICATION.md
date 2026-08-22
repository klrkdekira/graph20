# SRD 5.2.1 System JSON — Technical Specification

Status: v0.1.0 structural baseline. Extraction, schema validation, link resolution, LLM artifacts, and build determinism are verified by `make check`. Semantic review of individual records and the deferred typed catalogs (section 3.2) remain open; see `CHECKLIST.md`.

## 1. Objective

Turn the CC-BY-4.0 `SRD_CC_v5.2.1.md` into a modular, machine-readable SRD 5.2.1 rules corpus with:

- JSON-LD 1.1 identifiers and relationships;
- JSON Schema Draft 2020-12 validation;
- one file per reusable game entity;
- an aggregate system manifest and single-file bundle;
- traceability from every extracted entity to its SRD chapter/heading/lines;
- lossless preservation of rules text where normalization would discard meaning.

The repository at `../wwn-system-json` is the structural precedent; this repo follows its `PLAYBOOK.md` replication sequence.

## 2. Source and legal boundary

Primary source: `SRD_CC_v5.2.1.md`, the System Reference Document 5.2.1 by Wizards of the Coast LLC, licensed CC-BY-4.0. Unlike the WWN precedent (CC0), attribution is a **license obligation**: the required attribution statement is preserved verbatim in the source record, the manifest metadata, `README.md`, and `llms-full.txt`. Only material present in the source file is in scope.

## 3. Scope

### 3.1 v0.1.0 corpus

- `sources` — 1 provenance record with SHA-256 content digest.
- `spells` — 338 records: level, school, class availability, casting time, range, components, duration + verbatim prose.
- `feats` — 17 records: category, prerequisite, repeatable + prose.
- `magic-items` — 258 records: item category, rarity, attunement + prose.
- `monsters` — 332 stat blocks (Monsters A-Z, Animals, and two in Magic Items): size/type/alignment, AC, HP (+ typed dice), speed, typed six-ability table, skills/resistances/immunities/senses/languages, CR (+ typed XP/PB), trait/action sections + verbatim prose.
- `rules` — 1,113 records: every remaining heading section in every chapter (Playing the Game, Character Creation, Classes, Character Origins, Equipment, Spells preamble, Rules Glossary, Gameplay Toolbox, Monsters intro, catalog group headers).
- `tables` — 258 records: every HTML table converted to explicit columns/rows with positions; linked from their owning rule via `relatedTables`.

Coverage: every heading block from `# Playing the Game` to end-of-file is consumed by exactly one record. Lines 1–980 (Legal Information + Contents) are the documented exclusion (`objects/sources/source-coverage.json`); the license text itself survives in the source record.

### 3.2 Explicitly deferred

- Typed catalogs for classes/subclasses, species, backgrounds, and mundane equipment (currently faithful Rule + Table records).
- Cross-entity graph enrichment (spell → class nodes, monster → condition nodes).
- Review-signal ledger tooling, vocab page, static explorer, FAIR packaging (datapackage/CITATION/sitemap).
- Executable dice roller/rules engine, character builder, campaign state.

## 4. Architecture decisions

Identical to the WWN precedent unless noted:

| Concern | Decision |
| --- | --- |
| Base IRI | `https://cheeleong.dev/graph20/` |
| Vocabulary | `${BASE}vocab/`, prefix `srd:` |
| Context | `systems/context.jsonld`, JSON-LD 1.1 |
| Schemas | Draft 2020-12, absolute `$id`, `unevaluatedProperties: false` on leaf entities |
| Entity identity | slug-based absolute `@id`, no file extensions |
| Relationships | `{ "@id": ... }` node references only |
| Prose | verbatim in `rulesText`; structured fields are siblings |
| Manifest | `objects/srd52-system-data.jsonld` + `objects/srd52-system-data.bundle.jsonld` |
| Determinism | no timestamps; corpus digest in manifest; `check_determinism.py` gate |

## 5. Source structure and extraction rules

The markdown is a PDF conversion with a **single flat `#` heading level** (2,909 headings) and HTML `<table>` markup. Consequences:

1. **Chapters** are located by an ordered title list (`srdlib.CHAPTERS`), matched sequentially — several chapter titles ("Equipment", "Spells", "Magic Items") also occur as interior section headings.
2. **Entity boundaries** are detected from body grammar, never heading depth:
   - spell: first body line matches `Level N <School> (<classes>)` or `<School> Cantrip (<classes>)`;
   - feat: `<Category> Feat` line;
   - magic item: `<Category>[, detail], <Rarity>[ (Requires Attunement...)]` line;
   - monster: `<Size> ... ,` size/type/alignment line, normally preceded by a duplicate empty name heading (merged for provenance).
3. **Stray headings**: the conversion promotes some interior lines to headings (spell stat lines like `# Components: V`; monster stat lines like `# Resistances Cold`; sub-sections `# Traits`/`# Actions`). These fold back into the owning entity.
4. **Section numbering** is synthesized as `<chapterIndex>.<positionInChapter>` and recorded in `sourceLocator` with heading text and 1-based line bounds.

### Known source anomalies (registry: `objects/sources/extraction-overrides.json`)

- Roman-numeral OCR in ability tables (`I`→1, `II`→11) — accepted normalization for typed fields only.
- LaTeX-wrapped ability labels (`$\mathbf{S_{TR}}$`) — accepted normalization.
- Glued score tokens (`CON25`, `Con22`) — accepted normalization.
- CR line joined onto Languages line; `450 XP` ordering variant — accepted parser tolerance.
- Truncated ability cells in 28 stat blocks — **recorded, not repaired**: typed values omitted.
- `Id6`-style dice OCR in equipment tables — recorded; no typed field depends on them in v0.1.0.

## 6. Validation and verification

`make check` runs, in order: full re-extraction, manifest, bundle, `llms-full.txt`, search index, unit tests, structural validation, schema validation, determinism.

- `scripts/validate.py` (dependency-free): JSON syntax, required identity fields, unique `@id`s, slug/filename agreement, locator line bounds, and 100% node-reference resolution including manifest and bundle.
- `scripts/validate_schema.py`: all 2,317 records + manifest against the Draft 2020-12 schemas.
- `tests/test_structural.py`: source digest match, attribution presence, catalog counts, entity fixtures (Bless, Fire Giant, Animated Shield), typed-fields-mirror-source-strings, no-invented-scores, JSON-LD expansion via pyld (asserts expanded predicate IRIs), llms-full inlining, search-index resolution.
- `scripts/check_determinism.py`: two clean builds in temp dirs, byte-identical output including `llms-full.txt` and the search index.

## 7. Definition of done (v1)

- all in-scope SRD blocks represented or explicitly excluded — **done** (heading-block coverage);
- every entity validates with a stable canonical IRI — **done**;
- every internal relationship resolves — **done**;
- deterministic generation — **done**;
- licensing/attribution metadata present — **done**;
- typed catalogs for the deferred chapters — **open**;
- human semantic review of ambiguous parses and table anomalies — **open**.
