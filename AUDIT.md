# Gap Register

Audit date: 2026-08-24 (v0.4.0). Method: four independent sweeps — semantic completeness against `SRD_CC_v5.2.1.md`, graph/link quality, specification-vs-enforcement, and publication surface — followed by remediation of every confirmed data-loss and pipeline-integrity finding. Items marked **fixed** shipped in v0.4.0; items marked **open** are known, registered limitations.

## Fixed in v0.4.0

### Data loss and provenance (extraction)

1. **Fixed — `Dispel Magic` was missing from the corpus.** Its descriptor line wrapped across a column break (`Level 3 Abjuration (Bard, Cleric, Druid, Paladin,` / `Ranger, Sorcerer, Warlock, Wizard)`), so descriptor detection failed and the spell's full text was folded into the preceding *Dispel Evil and Good* record. Repaired at the source (`scripts/repair_source.py` step 21b, registered as `cross-column-splice-repairs-2026-08-24`). Spells: 338 → 339.
2. **Fixed — the Tiefling's Fiendish Legacies table was spliced into the Human species entry** by the two-column page layout. The table is relocated to the Tiefling's Fiendish Legacy trait, which references it.
3. **Fixed — the Travel Terrain table was spliced into the "1: Choose Abilities" background-creation step.** Relocated to the Travel Pace section that references it; its record is now `objects/tables/9-2-travel-terrain.jsonld` with correct heading provenance.
4. **Fixed — four summoned-creature stat blocks in the Spells chapter (Animated Object, Otherworldly Steed, Giant Insect, Draconic Spirit) were raw prose inside spell records** while the two stat blocks in the Magic Items chapter had been promoted. All four are now Monster records. Monsters: 332 → 336. Spell-level-scaling AC/HP values are intentionally left untyped (a scalar index would misstate the printed value); their five attack paragraphs use non-numeric bonuses ("Bonus equals your spell attack modifier") and are recorded as explicit unparsed dispositions alongside the Roper's Tentacle.
5. **Fixed — all 133 equipment records carried a wrong `sourceLocator.heading`** (the column-flow heading the table physically sat under: "Vex", "One at a Time", "Ammunition (Varies)"). The heading is now the owning table's caption ("Weapons", "Armor", "Adventuring Gear").
6. **Fixed — the 82 gear records and their prose descriptions were severed twins.** Each gear item now carries `relatedRules` linking to the Equipment-chapter Rule record that describes it (82/82 matched deterministically after apostrophe normalization and price-parenthetical stripping).

### Pipeline and enforcement

7. **Fixed — `make check` neutered the determinism gate.** The in-place regeneration targets ran before `determinism`, so the "checked-in artifacts match a clean build" comparison always saw freshly rewritten files. `determinism` now runs first, and CI additionally fails on a dirty tree after `make check`.
8. **Fixed — headline record counts were unenforced.** `tests/test_structural.py` now pins every collection exactly and asserts the 2,097 total; equipment/rules/tables previously used `assertGreater`, letting records vanish silently.
9. **Fixed — the `typed-source` review-check note claimed equipment fidelity that did not exist.** `scripts/validate_fidelity.py` now verifies equipment `name`, `cost`, `damage`, `armorClass`, `weight`, and `mastery` against the source table span, and verifies the spell Level & School descriptor (the fifth printed header, previously unchecked) against each spell's span. The note is now accurate.

### Publication surface

10. **Fixed — README documented `startLine`/`endLine`; the fields are `lineStart`/`lineEnd`.**
11. **Fixed — seven `file:///Users/...` local links in README** replaced with repository-relative links.
12. **Fixed — README described five spell headers as "all 4".**
13. **Fixed — `llms.txt` listed 12 of 13 collections** (sources omitted, so its counts contradicted its own total) and omitted the vocabulary; both corrected.
14. **Fixed — the explorer's "View source lines" GitHub link was broken for every record** (`#L` anchors need `?plain=1` on rendered markdown).
15. **Fixed — the explorer's list filter ignored `group`**, so the advertised spell-level / monster-CR / rarity / equipment-category filtering matched nothing.
16. **Fixed — search UX false negatives**: a query of only short tokens (e.g. "AC") reported "No matches anywhere" instead of explaining the 3-character minimum, and result counts over 300 displayed as exactly "300 results" with no truncation notice.
17. **Fixed — stale size labels** ("about 4 MB" bundle, "about 1.5 MB" llms-full) and the version chip.
18. **Fixed — `CITATION.cff` gaps**: added `repository-code`, `date-released`, and the dual CC-BY-4.0 + MIT license list; author naming aligned ("Chee Leong Chow") across `CITATION.cff`, `datapackage.json`, and `index.html`; Wizards of the Coast's Frictionless role corrected from `wrangler` to `author`.
19. **Fixed — `datapackage.json` omitted published artifacts**: added `vocab/terms.json`, `systems/context.jsonld`, `llms.txt`, `sitemap.xml`, and the three `objects/sources/*` verification artifacts, plus a `repository` link.

## Open gaps (registered limitations)

### Graph link coverage (measured, not yet asserted)

- **G1.** ~66% of records have zero outbound links beyond `source`; only nine relation shapes exist corpus-wide. Spells, monsters, magic items, equipment, feats, species, and backgrounds are all in-degree 0 (unreachable by traversal). The graph gate validates expansion fidelity, not link coverage.
- **G2.** ~4,000 latent edges are recoverable from exact string matches: spell names in class spell-list table cells (908, 0 linked), "cast *SpellName*" phrases in magic items (40, 0 linked), "*X* condition" phrases (462 unlinked), background `feat` strings whose feat records exist (4/4 unlinked), monster `gear` tokens resolving to equipment records (86, 0 linked).
- **G3.** The graph is one-directional by construction (only class↔subclass is reciprocal); `systems/context.jsonld` defines no `@reverse` terms, and the one-directionality is undocumented as intentional.
- **G4.** Declared relation vocabulary with zero record-level occurrences outside the new equipment links: `seeAlso`; `relatedRules` is declared in `rule.schema.json` but used by 0 of 738 rules.

### Under-typed content (present, source-faithful, prose-only)

- **T1.** The Rules Glossary self-labels five typed families; only `[Condition]` has a collection. `[Action]` ×12, `[Area of Effect]` ×6, `[Hazard]` ×5, `[Attitude]` ×3 are generic rules.
- **T2.** 31 Eldritch Invocations and 10 Metamagic options live inside the warlock/sorcerer class `rulesText` (not in `features[]`), with their printed `Prerequisite:` lines unindexed.
- **T3.** The 26 tools (17 Artisan's, 9 Other) are Rule records with the price trapped in the record name; there is no tools table in the source, so they need a prose-heading extraction path. Mounts, tack, vehicles, food/lodging, hirelings, and spellcasting services exist only as table rows. Arcane/Druidic focuses, holy symbols, and the ammunition-storage table rows are likewise not equipment records.
- **T4.** 10 spells still carry inline markdown tables with no Table record or `relatedTables` (the 4 stat-block cases were resolved by promotion); species lineage tables (Elven Lineages, Fiendish Legacies, Draconic Ancestry) are raw pipes inside species `rulesText`.
- **T5.** Monster `sizeAndType`, `speed`, `skills`, `senses`, `languages`, `immunities` (damage + condition mixed), `resistances`, `vulnerabilities`, and `gear` are raw strings; no split `size`/`creatureType`/`descriptiveTags`; no NPC/Animal category field; monster spellcasting sections (49 monsters) are untyped prose.
- **T6.** Spells have no typed area-of-effect geometry (85 spells name a shape), no save-DC/save-outcome typing, and `duration`/`range`/`components` are free strings. Condition records carry `rulesText` only. Magic-item charges (56 items), granted spells (25), attunement restrictions (21), and cursed/sentient flags are untyped. Equipment `weight` is a string while `cost` is typed. Gameplay Toolbox traps, poisons, diseases, environmental effects, fear/mental stress, and curses have consistent internal structure that is not indexed. Backgrounds link skills/tools/equipment by prose strings.
- **T7.** Table cells hold display strings only (no entity references); the 8 class `spellList` links terminate in prose Rule records whose tables name spells as unlinked strings.

### Enforcement residuals

- **E1.** Advertised derived metrics (139 properties / 14 classes, 7,559 tokens, 1,974 signals, 52,580 llms-full lines, 2,106 sitemap URLs) are printed by their builders but not asserted by tests; README badge numbers are hand-maintained. The determinism-first `check` plus CI tree-cleanliness now pins the artifacts themselves, but not the prose that quotes them.
- **E2.** The version string exists in 7 hand-edited locations with no cross-check.
- **E3.** `llms.txt` is hand-maintained (no builder, no gate). `index.html` has no smoke test.
- **E4.** Bundle `@graph` members are validated as envelopes, not against per-collection schemas (mitigated by `validate_graph.py` expansion and `validate.py` reference checks).
- **E5.** The `sources` record is exempt from `validate.py`/`validate_fidelity.py` structural checks; the attribution statement is substring-checked, not equality-checked, and README/llms.txt attribution text is unchecked.
- **E6.** `sitemap.xml` is validated for well-formedness only; `collection-index.json` has schema validation but no referential check against emitted records.
- **E7.** CI runs a single Python (3.12), floats action versions, and has no `permissions:`/`concurrency:` blocks or scheduled run.
- **E8.** Monster AC/HP/XP/CR and feat/species/background typed fields have no per-record source-fidelity branch (fixture-level tests only).

### Publication residuals

- **P1.** The 2,097 sitemap record URLs point at `.jsonld` documents; there is no per-record HTML and the explorer's hash routes are not crawlable, so no record has an indexable human-readable page. No `<lastmod>` hints.
- **P2.** The Weapons/Armor/Adventuring Gear *table records* still carry the column-flow heading of the block they physically sit in; only the equipment records' headings were corrected (the table locator reflects physical truth by design).
- **P3.** The explorer does not render `unparsedAttacks`, table `rawText`, background `abilityScoreOptions`, monster scalar fact fields (`challengeRating`, `experiencePoints`, `proficiencyBonus`, …), `sourceLocator.heading`, or species connective prose; the record's universal `source` edge is not rendered as a link. First search downloads the full ~18.5 MB index with no size warning.
- **P4.** GitHub Pages serves `.jsonld` without a configured `application/ld+json` MIME type; there is no HTML↔JSON alternate-link pairing or content negotiation.
- **P5.** 58 of 738 rules have no `rulesText` (heading-only sections), rendering near-empty explorer pages.
