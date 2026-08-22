# SRD 5.2.1 Corpus Audit and Remediation Backlog

Audit date: 2026-08-22  
Scope: the current local worktree, `AGENTS.md`, `SPECIFICATION.md`, extraction and build scripts, schemas, generated records, aggregate/LLM/search artifacts, and verification gates.

## Conclusion

The mechanical pipeline is reproducible and its current checks pass, but the corpus does not yet meet its source-discipline, graph-fidelity, traceability, LLM-ingestion, or semantic-review acceptance criteria. A green `make check` must not be treated as proof of semantic completeness.

The most urgent issue is source governance: the checked-in source contains values supplied from an external dataset or derived from rules, despite the project rules requiring missing values to remain omitted and external material to have its own source and rights record. The next priorities are loss in JSON-LD expansion, incorrect provenance spans, and source text omitted from LLM/search artifacts.

## Verified baseline

The following results are useful evidence, but do not close the findings below:

- `UV_CACHE_DIR=/tmp/graph20-uv-cache make check` passes: 2,112 records, 14,552/14,552 non-blank content lines inside at least one locator span, 16 unit tests, structural and schema validation, and 2,119 byte-identical artifacts across two clean builds.
- All 2,112 records and the bundle can be expanded with `pyld` when the local context is injected; expansion itself reports no syntax error.
- The required Wizards of the Coast CC-BY-4.0 attribution statement is exact in the authoritative source, source record, manifest, README, and `llms-full.txt`.
- `scripts/repair_source.py` is idempotent against the current source: a temporary-copy run made zero substitutions or table repairs and produced a byte-identical source.
- `make review-stats` reports 1,704 pending, 0 accepted, 0 corrected, and 0 false-positive review signals.

## Priority order

Resolve findings in this order because later verification depends on the earlier data model and source decisions:

1. AUD-001 source boundary and invented values.
2. AUD-002 JSON-LD graph fidelity and node-reference shape.
3. AUD-003 provenance correctness and AUD-005 table semantics.
4. AUD-004 ingestion completeness, AUD-006 anomaly disposition, and AUD-007 typed extraction.
5. AUD-008 review coverage, AUD-009 verification gates, and AUD-010 vocabulary publication.
6. AUD-011 documentation and reporting drift.

## Findings

### AUD-001 — Critical — External and derived values violate source discipline

Evidence:

- `AGENTS.md` requires a separate source/rights record for other SRD material and says truncated cells must stay omitted.
- `scripts/repair_source.py` regenerates 89 damaged ability tables from `scripts/data/srd-2024-creatures.json` and derives missing modifier/save cells for Giant Insect and Draconic Spirit using `floor((score - 10) / 2)`.
- `objects/sources/extraction-overrides.json` and `SPECIFICATION.md` explicitly describe those operations, but the corpus has only one `Source` record: Wizards' local SRD markdown. The cached open5e data has no corresponding `Source` record carrying origin, rights, and attribution metadata.
- The repaired values are now inside the file described as the authoritative, frozen source and flow into generated prose/structured data. This also conflicts with the specification's deferral of automation inferred from prose.

Impact: provenance is inaccurate, missing source values have been invented, and it is no longer possible to distinguish observed SRD content from externally supplied or derived content by inspecting a record.

Required fix:

- Recover the observed pre-repair cells from the recorded pre-repair source or repository history and keep genuinely missing/truncated values omitted.
- Keep safe, approved OCR substitutions separate from value completion. Do not use open5e or a game-rule formula to fill authoritative record fields.
- If open5e remains as audit/comparison input, add a separate source record with origin, version, license, attribution, digest, and explicit links from any retained derived assertion. It must not silently become SRD source text.
- Change schemas and tests so incomplete observed ability entries are allowed and `test_no_invented_ability_scores` verifies source presence, not merely a numeric range. Remove the test requirement that every ability entry has a modifier and saving throw when the source did not provide them.

Acceptance evidence:

- Every emitted ability value maps to an observed local-source token or to an explicitly linked secondary-source assertion outside the authoritative SRD record.
- A fixture with a truncated cell remains omitted through extraction, bundle, LLM output, and rebuild.
- The source/manifest rights metadata enumerates every source that contributes retained material.

### AUD-002 — High — JSON-LD expansion loses data and violates node-reference conventions

Evidence:

- Expanding `objects/classes/barbarian.jsonld` yields `srd:coreTraits` with an empty object. Keys such as `"Primary Ability"` are used as JSON-LD properties under `@vocab`; the invalid/unmapped labels disappear from the expanded graph.
- `systems/context.jsonld` declares `licenseUrl` and `canonicalUrl` with `@type: "@id"`, but source and manifest records emit bare strings. Including the duplicated bundle copies, eight values under IRI-coerced predicates are not `{ "@id": ... }` node references.
- The manifest's `collectionSchemas` map collides with the `classes` and `subclasses` context terms. Those two schema URLs expand as IRIs while the other eleven schema URLs expand as literals.
- The JSON-LD unit test expands only Bless and asserts only its ID, name, and source. It cannot detect loss in class maps or manifest semantics.

Impact: the JSON documents validate, but their RDF graph is not a faithful representation of the structured data and does not follow the repository's relationship convention.

Required fix:

- Remodel `coreTraits` as graph-safe typed entries (for example, objects with stable camelCase predicates) or add an appropriate scoped/index context that preserves every key.
- Emit every IRI-coerced relationship as a node reference and update source/system schemas accordingly, or deliberately model a URL as a literal and remove its `@id` coercion. Do not mix the two shapes.
- Replace arbitrary `collections`/`collectionSchemas` maps with graph-safe collection descriptors or scoped contexts that cannot collide with entity relationship terms.
- Expand every entity type plus the manifest and bundle in tests, and assert that representative structured fields survive with the intended predicate and value kind.

Acceptance evidence:

- Expanded class data contains every core trait and value.
- A raw-shape check reports zero bare strings for all context predicates declared `@type: "@id"`.
- All collection schema links expand uniformly as IRIs and collection membership predicates are intentional.

### AUD-003 — High — Source locators are physically incorrect

Evidence:

- All 12 subclass locators end before their feature headings. Path of the Berserker claims lines 2397–2401 while its features start at 2403 and continue through 2415; the same defect occurs in every subclass.
- 61 of 243 Table records have a `lineStart` that is not an HTML table line. Magic-item tables are extracted from synthetic concatenated text, so synthetic offsets are incorrectly treated as source offsets. Efreeti Bottle points to blank line 15315 instead of table line 15316.
- `scripts/validate.py` checks only `1 <= lineStart <= lineEnd <= source length`. `scripts/build_coverage.py` marks every line inside a claimed span as covered without checking that the record actually represents it.

Impact: entity-to-source traceability, a definition-of-done requirement, is false even though structural validation and coverage pass.

Required fix:

- Carry original block/line metadata through folded spell, monster, class, subclass, and magic-item extraction instead of reconstructing offsets from synthetic strings.
- Extend subclass locators through the last consumed subclass feature, while keeping the parent class locator behavior explicit.
- Validate that ordinary entity locators start at their declared heading, Table/equipment locators point at the source table, and nested feature spans are contained in the owning entity span.

Acceptance evidence:

- Zero entity-heading or table-line locator mismatches across the corpus.
- Fixtures cover a subclass, a magic-item table, a folded monster stat heading, and a table continuation.

### AUD-004 — High — `llms-full.txt` and full-text search omit class content

Evidence:

- `scripts/build_llms_full.py` formats only a fixed set of top-level scalar fields, table rows, and top-level `rulesText`.
- All 232 class/subclass feature bodies (92,349 characters) are absent as exact text from `llms-full.txt`: 174 class features and 58 subclass features. Fifty-five of 88 class core-trait values are also absent as exact text.
- `scripts/build_search_index.py` indexes only `name`, top-level `rulesText`, and `description`, omitting the same 232 feature bodies. The Barbarian document is not posted for `rage`; Path of the Berserker is not posted for `frenzy` or `mindless`.
- Equipment records have no `rulesText`; their damage, mastery, cost, and other structured fields are neither comprehensively formatted nor indexed. A search for a property such as the Longsword's `Slashing` or `Sap` does not return the Longsword record.
- The existing tests prove only that Bless prose is in `llms-full.txt` and that a `fireball` posting points inside the document array.

Impact: the advertised single-file LLM context and explorer's “search everything” feature cannot answer from significant in-scope class/subclass text or structured-only records.

Required fix:

- Build one shared, recursive, source-aware textual projection for LLM output and search indexing.
- Include core traits, features, traits, stat sections, table cells, and relevant structured-only equipment fields without dropping top-level prose or creating accidental duplicate sections.
- Generate useful excerpts from the matched nested content.

Acceptance evidence:

- Every `rulesText`/`description` value at any nesting depth appears in the LLM projection and contributes tokens to its owning search document.
- Corpus-wide tests verify nested-text coverage rather than a single fixture.
- Searches for `Rage Damage`, `Mindless Rage`, and `Longsword` + `Slashing` return the correct records.

### AUD-005 — High — Headerless and continued tables have incorrect semantics

Evidence:

- `parse_html_table` always treats the first `<tr>` as column headers. Nineteen generated tables therefore have zero data rows; 18 are fragments of Wand of Wonder and one is a Bag of Beans fragment.
- At least 25 records promote an apparent numeric data row to `columns`. Efreeti Bottle stores roll `1` and its effect as headers rather than as the first row.
- The source conversion splits the Wand of Wonder Effects table across 18 one-row `<table>` elements, and the extractor emits 18 unrelated zero-row Table records instead of one logical continued table.
- The schemas permit empty `rows`, so schema validation does not flag the problem. The explorer renders the promoted values as table headers.

Impact: table strings may remain somewhere in JSON, but row/header meaning, ordering, display, and reusable table identity are wrong.

Required fix:

- Represent whether a source fragment has an actual header; do not infer that every first row is a header.
- Merge consecutive table fragments that are continuations of the same caption/logical table, preserving each fragment's exact source span.
- Consider preserving raw table text or a source-row representation alongside normalized columns/rows so losslessness can be verified.

Acceptance evidence:

- Wand of Wonder is one ordered logical table with all 18 effects as rows.
- Efreeti Bottle roll `1` is a row, not a column heading.
- No table has zero rows unless a reviewed source fixture intentionally represents a header-only table.

### AUD-006 — High — The source still contains unresolved conversion-anomaly candidates

Evidence:

`SPECIFICATION.md` says all previously recorded conversion damage was fixed, but focused scans still find:

- 26 headings containing `I GP`, `I SP`, or `I CP` and 33 total currency/damage occurrences matching that OCR pattern;
- 11 spell casting times `I minute or Ritual` and 4 durations `I round`;
- 2 class starting-equipment values containing `II GP`;
- glued tokens `castLightning Bolt`, `castPolymorph`, `aBlack Bear`, `aGiant Wasp`, and `aFrog` in Wand of Wonder;
- numbered-heading candidates such as `Step I: Choose Class`; and
- source headers using singular `Component:` for 12 spells, which the typed extractor currently ignores.

These are candidates requiring source comparison and human disposition; the audit does not authorize silently changing them.

Impact: damaged headings become record names/slugs, spell metadata carries likely OCR tokens, and malformed source text propagates into records, bundles, LLM output, and search.

Required fix:

- Review each candidate against the authoritative source rendering.
- Add one registry entry per accepted anomaly class with observed token(s), proposed fix, rationale, status, affected counts, and pre/post digest before changing source text.
- Keep rejected candidates documented so the detector has an explicit allowlist rather than silently ignoring them.

Acceptance evidence:

- An anomaly detector runs in CI and every hit is either an approved override or an explicit reviewed false positive.
- Generated fixtures assert corrected source-faithful names and spell header fields.

### AUD-007 — High — Typed extraction is incomplete or misleading for advertised fields

Evidence:

- Twelve of 338 spell records lack `components` because the parser recognizes `Components:` but not the source's `Component:` spelling. The spell schema does not require casting time, range, components, or duration even though the scope says spells carry all four.
- Six magic-item headers contain multiple rarity variants, but the extractor keeps only the first rarity. Wand of the War Mage is also marked `requiresAttunement: false` even though its header says it requires attunement by a spellcaster.
- A broad count finds 423 monster action occurrences with a numeric `Attack Roll` bonus but only 381 emitted attack entries; 41 monsters have count mismatches. Common misses include flat damage without dice, `feet` versus `ft.`, recharge names containing an en dash, `+N to hit`, and multiple damage components. Parsed attacks also retain only the first damage component.
- Eleven equipment names contain the literal `&#x27;` markup and their slugs expose `x27` (for example, `alchemist-x27-s-fire`); explorer text uses `textContent`, so the encoded apostrophe is displayed literally.

Impact: typed fields are absent or assert the wrong value while schemas and fixtures still pass.

Required fix:

- Make advertised spell header fields required after supporting source variants.
- Model rarity variants explicitly and parse attunement after the complete rarity expression.
- Broaden attack parsing with paragraph-level fixtures and represent multiple damage components without discarding secondary damage.
- Decode HTML character references in structured display/index fields while retaining source-faithful raw text and documenting the normalization policy.

Acceptance evidence:

- All 338 spells have the four advertised header fields or a reviewed, source-backed exception.
- Every magic-item attunement flag mirrors its header and all rarity variants are retained.
- Every reviewed numeric attack paragraph either has a complete typed representation or an explicit parse-status reason.
- Structured equipment names render apostrophes and produce stable semantic slugs.

### AUD-008 — Medium — The semantic-review ledger is incomplete and untouched

Evidence:

- All 1,704 current signals remain pending; no human disposition has been recorded.
- The scanner reads only top-level `rulesText`. Applying its existing patterns to nested class/subclass features and Table values produces 157 additional unique signal keys: 51 from features and 106 from tables.
- Repeated identical matches are collapsed per record and signals contain no occurrence locator, surrounding context, structured-field comparison, or linked correction/override.
- The ledger does not detect the provenance, table-header, rarity, attack, or JSON-LD semantic failures found in this audit, so clearing its current queue alone cannot establish semantic verification.

Impact: the sole open review mechanism under-reports its scope and cannot substantiate the eventual “semantically verified” claim.

Required fix:

- Reuse the recursive textual projection from AUD-004 and retain occurrence-level paths/source lines and context.
- Add review categories for typed/source mismatches, table shape, anomaly candidates, provenance exceptions, and graph-shape loss.
- Define what `accepted`, `corrected`, and `false-positive` prove and link corrections to scripts/overrides/tests.
- Preserve curated dispositions deliberately in clean-build/determinism workflows instead of relying only on an existing generated file.

Acceptance evidence:

- Zero pending signals after human review, including nested/table signals and all audit-derived review queues.
- A clean rebuild preserves reviewed dispositions and rejects stale keys or unreviewed newly introduced signals.

### AUD-009 — Medium — Verification gates do not cover the acceptance criteria they are used to claim

Evidence:

- `make check` passes with every critical/high finding above present.
- Coverage proves only that a non-blank source line falls inside some locator interval; it does not prove extraction, fidelity, ownership, or locator accuracy.
- Structural validation checks locator bounds but not the source content at those bounds. Schema validation permits semantically incomplete optional fields and zero-row tables.
- Determinism compares two fresh builds to each other, not a clean build to checked-in artifacts. Its pipeline omits `build_vocab.py` and `build_sitemap.py`, and it does not seed or compare curated review dispositions.
- Schema validation covers records and the manifest, not bundle graph semantics or the auxiliary indexes. JSON-LD coverage is a single-record fixture and skips locally when `pyld` is absent.

Impact: green automation is being used as evidence for claims it does not test.

Required fix:

- Add regression tests for every accepted finding before marking it fixed.
- Separate interval coverage, source-text fidelity, typed-field fidelity, graph expansion, and human semantic review into distinct gates with honest names.
- Compare a clean build with checked-in generated artifacts, with an explicit strategy for curated ledger state.
- Include vocab, sitemap, bundle, collection index, search index, and LLM output in artifact validation and determinism scope.

Acceptance evidence:

- Each current defect can be reintroduced in a fixture and causes the appropriate gate to fail.
- `make check` documentation lists exactly what each gate proves and does not imply human semantic verification.

### AUD-010 — Medium — The published vocabulary is incomplete and not demonstrably dereferenceable

Evidence:

- Expansion of the records uses 119 predicates in the project vocabulary namespace, but `build_vocab.py` lists only the 23 explicitly aliased context properties. The audit found 101 used implicit predicates absent from that list, including `features`, `level`, `damageRoll`, `rows`, and `coreTraits`.
- Predicate IRIs are path IRIs such as `https://cheeleong.dev/graph20/vocab/slug`, while the repository generates only `vocab/index.html` with HTML element IDs. There are no corresponding files or routes for the per-term paths.
- The current test verifies that one expanded predicate IRI exists; it does not verify vocabulary completeness or dereference targets.

Impact: the FAIR/dereferenceable-vocabulary completion claim is unsupported, and consumers cannot discover most terms from the vocabulary artifact.

Required fix:

- Make the vocabulary inventory derive from the context plus schemas/expanded graph, or explicitly define every supported term in the context.
- Use fragment IRIs backed by the vocabulary page or generate a resource/redirect for every path IRI.
- Publish descriptions, value kinds, ranges, and relationship semantics for all predicates and classes.

Acceptance evidence:

- Every project-namespace predicate/class present in an expanded clean build has a generated vocabulary definition and a resolvable local publication target.
- CI fails on an undocumented new predicate.

### AUD-011 — Low — Status and reporting documentation has drifted

Evidence:

- The prior specification status said every pipeline phase was complete and that semantic review was the one open item, while its own definition of done also listed an undefined “typed catalogs for the deferred chapters” item as open.
- `SPECIFICATION.md` described schema validation of 2,317 records; the actual corpus and validator report 2,112 records.
- `CHECKLIST.md` listed only human review as open and therefore hid the remediation work above.
- `build_llms_full.py` reports `len(out)` as a line count (4,260 during the audit), while the generated file actually has 38,188 physical lines.

Impact: maintainers and consumers receive contradictory completion signals.

Required fix:

- Keep the specification status, checklist, README, manifest version, and this backlog synchronized as findings close.
- Define or remove the “typed catalogs for the deferred chapters” requirement.
- Correct generated command summaries so reported metrics mean what their labels say.

Acceptance evidence:

- No document describes the corpus as complete or semantically verified while any applicable audit finding or review signal remains open.
- Documentation counts are generated or tested against current artifacts.

## Confirmed strengths

The audit did not find gaps in these checked areas:

- Exact required Wizards CC-BY-4.0 attribution survives in all four mandated artifacts.
- Current record IDs are unique, internal node references resolve, filenames match slugs, and all generated records pass their current Draft 2020-12 schemas.
- All spell class-availability names currently have matching class node references.
- The current repair script is idempotent on the checked-in source.
- Repeated clean builds covered by `check_determinism.py` are byte-identical.

These strengths should be preserved while implementing fixes; they are not substitutes for the open acceptance evidence above.
