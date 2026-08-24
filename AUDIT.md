# Open Gap Register

Audit date: 2026-08-24 (v0.4.0); second verification pass same day (see "Second-run findings" below). Method: four independent sweeps — semantic completeness against `SRD_CC_v5.2.1.md`, graph/link quality, specification-vs-enforcement, and publication surface. This register contains unresolved findings only; handled findings have been removed.

## Open gaps (registered limitations)

### Graph link coverage (measured, not yet asserted)

- **G1.** ~66% of records have zero outbound links beyond `source`; only eight non-`source` relation predicates are in use corpus-wide. Spells, monsters, magic items, equipment, feats, species, and backgrounds are all in-degree 0 (unreachable by traversal). The graph gate validates expansion fidelity, not link coverage.
- **G2.** ~4,000 latent edges are recoverable from exact string matches: spell names in class spell-list table cells (908, 0 linked), "cast *SpellName*" phrases in magic items (40, 0 linked), "*X* condition" phrases (462 unlinked), background `feat` strings whose feat records exist (4/4 unlinked), monster `gear` tokens resolving to equipment records (86, 0 linked).
- **G3.** The graph is one-directional by construction (only class↔subclass is reciprocal); `systems/context.jsonld` defines no `@reverse` terms, and the one-directionality is undocumented as intentional.
- **G4.** Declared relation vocabulary with zero record-level occurrences outside the new equipment links: `seeAlso`; `relatedRules` is declared in `rule.schema.json` but used by 0 of 738 rules.

### Under-typed content (present, source-faithful, prose-only)

- **T1.** The Rules Glossary self-labels five typed families; only `[Condition]` has a collection. `[Action]` ×12, `[Area of Effect]` ×6, `[Hazard]` ×5, `[Attitude]` ×3 are generic rules.
- **T2.** 28 Eldritch Invocations and 10 Metamagic options live inside the warlock/sorcerer class `rulesText` (not in `features[]`), with their printed `Prerequisite:` lines unindexed.
- **T3.** The 25 tools (17 Artisan's, 8 Other) are Rule records with the price trapped in the record name; there is no tools table in the source, so they need a prose-heading extraction path. Mounts, tack, vehicles, food/lodging, hirelings, and spellcasting services exist only as table rows. Arcane/Druidic focuses, holy symbols, and the ammunition-storage table rows are likewise not equipment records.
- **T4.** 10 spells still carry inline markdown tables with no Table record or `relatedTables`; species lineage tables (Elven Lineages, Fiendish Legacies, Draconic Ancestry) are raw pipes inside species `rulesText`.
- **T5.** Monster `sizeAndType`, `speed`, `skills`, `senses`, `languages`, `immunities` (damage + condition mixed), `resistances`, `vulnerabilities`, and `gear` are raw strings; no split `size`/`creatureType`/`descriptiveTags`; no NPC/Animal category field; monster spellcasting sections (49 monsters) are untyped prose.
- **T6.** Spells have no typed area-of-effect geometry (85 spells name a shape), no save-DC/save-outcome typing, and `duration`/`range`/`components` are free strings. Condition records carry `rulesText` only. Magic-item charges (~50 items), granted spells (25), attunement restrictions (21), and cursed/sentient flags are untyped. Equipment `weight` is a string while `cost` is typed. Gameplay Toolbox traps, poisons, diseases, environmental effects, fear/mental stress, and curses have consistent internal structure that is not indexed. Backgrounds link skills/tools/equipment by prose strings.
- **T7.** Table cells hold display strings only (no entity references); the 8 class `spellList` links terminate in prose Rule records whose tables name spells as unlinked strings.

### Enforcement residuals

- **E1.** Advertised derived metrics (139 properties / 14 classes, 7,559 tokens, 1,974 signals, 52,580 llms-full lines, 2,106 sitemap URLs) are printed by their builders but not asserted by tests; README badge numbers are hand-maintained. The determinism-first `check` plus CI tree-cleanliness now pins the artifacts themselves, but not the prose that quotes them.
- **E2.** The version string exists in 9 hand-edited files (12 occurrences) with no cross-check.
- **E3.** `llms.txt` is hand-maintained (no builder, no gate). `index.html` has no smoke test.
- **E4.** Bundle `@graph` members are validated as envelopes, not against per-collection schemas (mitigated by `validate_graph.py` expansion and `validate.py` reference checks).
- **E5.** The `sources` record is exempt from `validate.py`/`validate_fidelity.py` structural checks; the attribution statement is substring-checked, not equality-checked, and README/llms.txt attribution text is unchecked.
- **E6.** `sitemap.xml` is validated for well-formedness only; `collection-index.json` has schema validation but no referential check against emitted records.
- **E7.** CI runs a single Python (3.12), floats action versions, and has no `permissions:`/`concurrency:` blocks or scheduled run.
- **E8.** Monster AC/HP/XP/CR and feat/species/background typed fields have no per-record source-fidelity branch (fixture-level tests only).

### Publication residuals

- **P1.** The 2,097 sitemap record URLs point at `.jsonld` documents; there is no per-record HTML and the explorer's hash routes are not crawlable, so no record has an indexable human-readable page. No `<lastmod>` hints.
- **P2.** The Weapons/Armor/Adventuring Gear *table records* still carry the column-flow heading of the block they physically sit in; only the equipment records' headings were corrected (the table locator reflects physical truth by design). Equipment records also still carry the column-flow `section` number alongside the corrected heading (e.g. §6.26 "Weapons"), so their locator pairs a semantic heading with a physical section.
- **P3.** The explorer does not render `unparsedAttacks`, table `rawText`, background `abilityScoreOptions`, monster scalar fact fields (`challengeRating`, `experiencePoints`, `proficiencyBonus`, …), `sourceLocator.heading`, or species connective prose; the record's universal `source` edge is not rendered as a link. First search downloads the full ~18.5 MB index with no size warning.
- **P4.** GitHub Pages serves `.jsonld` without a configured `application/ld+json` MIME type; there is no HTML↔JSON alternate-link pairing or content negotiation.
- **P5.** 58 of 738 rules have no `rulesText` (heading-only sections), rendering near-empty explorer pages.

## Second-run findings (2026-08-24, second audit pass — open)

A verification sweep after the v0.4.0 remediation found more instances of the same defect classes. All were confirmed against the source and remain unresolved.

### Cross-record absorption (Dispel Magic class)

- **S1 (severe).** `# Giant Fly` (source L15750) bisects *Figurine of Wondrous Power*: `magic-items/figurine-of-wondrous-power` retains only 2 of 10 variants (through Ebony Fly), while `monsters/giant-fly` carries the other 8 variants (Golden Lions through Silver Raven, ~3,500 chars of magic-item prose) after its stat block.

### Prose sidebar splices (repair_source step 13 class)

- **S2.** Three more ALL-CAPS sidebar splices bisect sentences: *Making an Attack* → tail (including the 1/2/3 attack-resolution procedure) absorbed by `rules/1-73-unseen-attackers-and-targets`; *The Nine Alignments* → 4 of 9 alignments absorbed by `rules/2-20-unaligned-creatures`; a Wizard Subclass feature sentence absorbed by the adjacent spellbook rule. Also the phantom heading `# Shrub or Awakened Tree in "Monsters."` (L7723) breaks a sentence inside `spells/awaken` (no data loss).

### Malformed headings

- **S3.** `# Curses and` (L13956) + `# Magical Contagions` (L13958) are one printed heading split by a column break, producing the empty phantom record `rules/9-14-curses-and` and a misnamed section that collides with the real `rules/9-22-magical-contagions`.
- **S4.** `# Passive Perception = 10 + ...` (L1128) is a display formula promoted to a heading; it splits *Creating Your Character* and pollutes a table locator heading. `# Casting Time: Action` ×4 (L12467-12513) are spurious headings that survive extraction but leave anomalous blank lines in four spell texts.

### Split / unconverted tables (Travel Terrain class)

- **S5 (severe).** The Trinkets table is typed for only rows 01-34; rows 35-100 are raw prose in two phantom `1d100 Trinket` rule records. The Prismatic Spray ray table has rows 1-4 as pipes and rows 5-8 as prose under a phantom `# 1d8 Ray` heading.
- **S6.** Ten logical tables are split into two Table records each by repeated column-flow headers (Adventuring Gear, Class Overview, Damage Types, XP by CR, Mysterious Deck, and five class spell-list levels) — a consumer reading fragment 1 silently gets a partial table.
- **S7.** The Robe of Useful Items patch table (~17 rows, with an embedded repeated `1d100 Patch` header at L17036) and the Sphere of Annihilation interaction table (3 rows) were never converted to tables and remain raw prose in their magic-item records.

### Wrapped/collapsed stat lines (typed-field corruption)

- **S8.** Ten monsters have truncated typed fields from values wrapped across a blank line: `avatar-of-death` and `animated-rug-of-smothering` lose the tail of `immunities`; eight monsters (ankheg, black-dragon-wyrmling, young-black-dragon, ancient-bronze-dragon, ancient-copper-dragon, white-dragon-wyrmling, ancient-white-dragon, giant-wolf-spider) lose "Passive Perception N" from `senses`.
- **S9.** Three stat blocks print AC and Initiative on one line (green-hag, grick, griffon): `armorClass` swallows the initiative, `initiative` and `armorClassValue` are absent.

### Source-level loss

- **S10 (severe).** `spells/telekinesis` ends mid-sentence at L12155 ("...such as manipulating a simple tool,"); the printed continuation ("opening a door or a container, stowing or retrieving an item from an open container, or pouring the contents from a vial") is absent from `SRD_CC_v5.2.1.md` entirely and must be restored from the official PDF text layer.

### Cosmetic / consumer polish

- **S11.** 14 records' `rulesText` ends with an absorbed `---` chapter separator; 51 Equipment-chapter rules end with a dangling next-table caption; the relocated Fiendish Legacies table carries glued sentence boundaries ("damage.You also know") outside the glued-token detector's pattern.
- **S12.** Explorer: magic-items renders 19 group headings for 8 rarities because multi-rarity items sort non-contiguously ("Multiple Rarities" also defeats the new rarity-word filter); record provenance lines end with a dangling " · " separator; equipment `relatedRules` links render slugs ("6 62 Acid 25 Gp") instead of rule names; no `.catch` on the collection-index/search-index fetches; mixed short+long queries silently drop the short token.
- **S13.** Documentation residue: the equipment `relatedRules` edge is undocumented outside this register (README graph section, SPECIFICATION, llms.txt); `Makefile help` omits four targets; the spell→summoned-monster association severed by the S-promotions has no forward edge (no `summons` term); `repair_source.py` step 21b relocations silently no-op if an anchor string ever drifts (should fail loudly) and the Travel Terrain removal regex lacks a positional guard; the vocab page renders `seeAlso` with a contradictory kind/range pair; `llms-full.txt` prints "1 records" for sources; collection-index labels shields as "Shield Armor".
