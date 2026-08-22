# SRD 5.2.1 System JSON — Technical Specification

Status: v0.2.0 audit remediation. The mechanical pipeline passes `make check`, but that gate does not prove the source-discipline, graph-fidelity, traceability, table, LLM/search, or semantic-review requirements. `AUDIT.md` is the current evidence-backed remediation backlog. The corpus must not be described as complete or semantically verified until every applicable audit finding and review signal is closed.

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

### 3.1 v0.2.0 corpus (2,112 records)

- `sources` — 1 provenance record with SHA-256 content digest and the CC-BY attribution statement.
- `classes` — 12: core traits (primary ability, hit die, proficiencies, starting equipment), level features, subclass and spell-list links + prose. `subclasses` — 12: parent-class link + level features.
- `species` — 9: creature type, size, speed, named traits. `backgrounds` — 4: ability scores, feat, proficiencies, starting equipment.
- `feats` — 17: category, prerequisite, repeatable (complete — the SRD intentionally includes 7 of the PHB's 10 Epic Boons).
- `equipment` — 133 typed records from the Weapons/Armor/Adventuring Gear tables: damage dice + type, properties, mastery, AC, don/doff, weight, structured costs; each links its source Table.
- `spells` — 338: level, school, class availability (names + class node refs), casting time/range/components/duration, typed save ability, damage rolls, concentration/ritual/slot-scaling flags + verbatim prose.
- `conditions` — 15 from the Rules Glossary `[Condition]` entries.
- `magic-items` — 258: category, rarity, attunement + prose.
- `monsters` — 332 stat blocks: size/type/alignment, AC, HP (+ typed dice), speed, complete typed six-ability blocks, CR (+ typed XP/PB), condition-immunity node refs, parsed attack routines (bonus, reach/range, damage dice + type), trait/action sections + verbatim prose.
- `rules` — 738 and `tables` — 243: everything else, with tables linked via `relatedTables`.

Coverage: `scripts/build_coverage.py` asserts every non-blank line from `# Playing the Game` to end-of-file is inside at least one record's span (currently 14,552/14,552). Lines 1–980 (Legal Information + Contents) are the documented exclusion; the license text survives in the source record.

### 3.2 Explicitly deferred

- Executable dice roller/rules engine, character builder, campaign state.
- Rule automation inferred from prose.

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

### Source anomalies and the repair event (registry: `objects/sources/extraction-overrides.json`)

All previously recorded OCR/conversion damage was fixed in a single deliberate, idempotent repair pass (`scripts/repair_source.py`) driven by the substitution glossary `scripts/data/sanitization-glossary.json`:

- OCR dice (`Id6`→`1d6`, 131 fixes), `+I` bonuses, the Blowgun's `I Piercing`, the `Rolling 20 or I` heading, `Level I/II` feature headings (62 fixes), CR line joins and `n XP` ordering.
- 89 damaged monster ability tables regenerated from open5e's srd-2024 dataset (CC-BY-4.0, cached in `scripts/data/srd-2024-creatures.json`) with cross-validation against every intact source cell; 2 spell-summoned stat blocks absent from that dataset had truncated modifier/save cells derived from the printed score (`floor((score-10)/2)`); 245 intact tables untouched. One open5e data error (Octopus) was caught by the cross-validation and is recorded.

Pre- and post-repair digests are recorded in the overrides registry. The parser retains the same normalizations as inert safety nets.

**Completeness verified**: monsters check out against the SRD's own Index of Stat Blocks (330/330 present, plus Avatar of Death and Giant Fly printed inside the Magic Items chapter); the 17 feats (7 Epic Boons) match the official SRD 5.2 inclusion list — the PHB's remaining boons are intentionally not in the SRD.

## 6. Validation and verification

`make check` runs, in order: full re-extraction, manifest, bundle, `llms-full.txt`, search index, unit tests, structural validation, schema validation, determinism.

- `scripts/validate.py` (dependency-free): JSON syntax, required identity fields, unique `@id`s, slug/filename agreement, locator line bounds, and 100% node-reference resolution including manifest and bundle.
- `scripts/validate_schema.py`: all 2,112 records + manifest against the Draft 2020-12 schemas.
- `tests/test_structural.py`: source digest match, attribution presence, catalog counts, entity fixtures (Bless, Fire Giant, Animated Shield), typed-fields-mirror-source-strings, no-invented-scores, JSON-LD expansion via pyld (asserts expanded predicate IRIs), llms-full inlining, search-index resolution.
- `scripts/check_determinism.py`: two clean builds in temp dirs, byte-identical output including `llms-full.txt` and the search index.

## 7. Definition of done (v1)

- all in-scope SRD blocks represented or explicitly excluded — **open** (interval coverage passes, but `AUDIT.md` identifies fidelity and table-shape gaps);
- every entity validates with a stable canonical IRI — **done**;
- every internal relationship resolves — **done**;
- deterministic generation — **partially verified** (the current determinism script's artifact scope is incomplete);
- licensing/attribution metadata present — **open** for secondary-source provenance; the required Wizards attribution is present;
- typed catalogs for the deferred chapters — **open and requires a scope decision**;
- human semantic review of ambiguous parses and table anomalies — **open**.
