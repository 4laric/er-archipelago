# Elden Ring bingo objective implementation audit

Design audit, 2026-10-03. This covers all 122 base-game and 91 DLC Season 6 templates in the snapshots used by the bingo spec: **213 templates and 300 expanded variants**. It ranks the engineering work required to detect each objective and make it attainable in an Archipelago seed. The recommendation is to extend persistent encounter facts and counters first, then collections and state values, then provenance and actions. Restricted combat comes last.

These are implementation estimates based on the existing code and each objective's wording, **not verified automatic coverage counts**. The current implementation draws 25 automatically tracked boss squares from our own catalogue. It does not import or implement all community objectives. Even an E1 row needs its exact signal, qualifying roster, access route and synthetic writers audited before it can ship. No community template in this ledger is marked as fully mapped merely because a similarly named boss is currently supported.

## Catalogue and counting

Source snapshots retrieved on 2026-10-03:

- [Season 6 base JSON](https://erb-community-tool.vercel.app/squares/season-6/season-6-base.json): 122 templates, 177 variants.
- [Season 6 DLC JSON](https://erb-community-tool.vercel.app/squares/season-6/season-6-dlc.json): 91 templates, 123 variants.
- [Base rules](https://erb-community-tool.vercel.app/leagues/bingo-brawlers/seasons/season-6-base/rules) and [DLC rules](https://erb-community-tool.vercel.app/leagues/bingo-brawlers/seasons/season-6-dlc/rules) remain the rule context. These pages could not be reread during this audit; qualifying details and ambiguities below need a pinned rule review before tournament-equivalence claims.

Audit IDs identify the one-based entry position within these hashed snapshots, not a publisher-provided stable ID. If a snapshot changes, reconcile IDs explicitly. Expanded counts are products of substitution arrays; variants in one template are alternatives and must not occupy several cells on a board. Source titles have been lightly rephrased as audit labels. The CSV is a derived assessment, not a replacement source catalogue or an assertion of redistribution permission. Continue using user-supplied originals for any future catalogue import.

SHA256: base `4578854890ecef28f4174c61e9e515a2d9b04fb88a8f23c3cb17ce5bf58af0c0`; DLC `d8b76baddc4a105c49a3a4fd0d7ad70b8d39b0db2e8ed4f98f8f0277e5e0d8cd`.

## Effort tiers and totals

| Tier | Meaning | Main new work |
|---|---|---|
| E1 | Small adapter after mapping proof | A specific persistent boss flag or an actual character value; legacy and DLC access logic may raise the cost |
| E2 | Moderate shared infrastructure | Distinct encounter rosters, dungeon endpoints, or persistent acquisition sets plus attainable supplies |
| E3 | Substantial action or provenance work | Quest/action transitions, local source-qualified acquisition, or ordinary entity kill identity |
| E4 | Largest implementation effort | Reliable, continuous combat events with damage attribution, restrictions and attempt boundaries |

| Tier | Templates by primary tier | Base variants | DLC variants | Combined variants |
|---|---:|---:|---:|---:|
| E1 | 54 | 35 | 26 | 61 |
| E2 | 78 | 91 | 42 | 133 |
| E3 | 60 | 31 | 49 | 80 |
| E4 | 21 | 20 | 6 | 26 |
| Total | 213 | 177 | 123 | 300 |

Two templates straddle tiers. The Valiant Gargoyles alternative in S6-BASE-015 is E1; its broader counts are E2. The Curseblade Labirith alternative in S6-DLC-032 is E1; three unique ordinary assassins is E3. Template counts use the primary tier, while variant counts apply these exceptions. The CSV records all 300 alternatives separately.

E1 and E2 are the first expansion candidates, not a guarantee that every variant fits a six-region short board. E3 is still potentially automatable, but its evidence often does not exist in the current client. E4 can remain referee-only until a reliable encounter event stream exists. No elapsed-time estimate is assigned: mappings and live acceptance have not been measured, and these tiers compare complexity rather than promise delivery dates.

## Evidence already available

- `greenfield/eldenring/features/bingo.py` builds single-boss cells from generated healthbar and sweep-arena mappings, deliberately excluding major-rune/festival fights and legacy content. `tables/boss_healthbars.py` provides named encounter facts; `tables/boss_sweeps.py` supplies arena ownership. A table row is a mapping candidate, not proof that its flag cannot be written by automation.
- `from-software-archipelago-clients/crates/er-logic/src/bingo.rs` currently accepts only one defeat flag per square. Counters, collections, character values and actions need a new typed predicate schema and client feature negotiation, not labels attached to the old flag field.
- Client `core.rs` distinguishes local board evidence from acknowledged AP checks, queues rewards, and reconstructs first-line flag debt. Preserve this distinction: a bonus sweep must never earn objective action credit.
- Client `inventory.rs`, `reconcile_io.rs`, `flask.rs`, `upgrades.rs` and the received-item reconciliation paths supply useful I/O seams. They do not yet constitute a general, durable ever-acquired ledger with source provenance. Observe successful application rather than count received packets.
- Client `boss_fight_probe.rs` samples HP around twice a second for diagnostics. It cannot prove hitless or identify every damage source, summon, parry or status application. A hit followed by healing between samples can be missed.

## Recommended implementation order

### Stage 1 Broaden boss facts and counters

Build a normalized encounter registry with stable identity, local completion signal, owner region, route prerequisites, fight unit and audited flag writers. Add `encounter_complete`, `distinct_encounters_at_least`, conjunctions and category quotas to a versioned bingo predicate contract. A duo has a fight identity as well as entity identities; the source square chooses the counting unit explicitly.

Start with base-game named bosses already represented by trustworthy facts, then simple group and regional counters. Extend legacy and DLC bosses only when quest, festival, terminal-arena and entry conditions are modeled. Verify every selected contributor can coexist and be reached in the final seed. Do not grant an entire counter from one accepted native AP check. Dungeon objectives use their curated terminal condition rather than a grace.

This stage must also fix semantic duplicate normalization: unique flags can still represent two states of one encounter, such as Patches surrender/death. Use one encounter family and never place both as separate square objectives. Cap overlap across cells so one action does not incidentally complete an entire line. Counter targets must be possible without expanding beyond the selected region budget.

### Stage 2 Add durable collections and actual values

Add a ledger keyed by seed, slot, board hash and bound fresh character. It records normalized item identity after a confirmed local acquisition or successfully applied AP grant. Replay, restoration grants and duplicate copies add no new distinct credit. Persist sold, stored and consumed history; handle non-item grants such as flask upgrades by actual achieved state. Explicitly exclude starting equipment/precollected gifts unless a square's published AP rules permit them.

Unrestricted collection rows are E2 **under a disclosed AP adaptation** that accepts qualifying remote items. They are not automatically exact tournament rules. Every row needs a complete normalized roster, including DLC scope, legendary membership, full armor sets and combined key pieces. Source-qualified rows stay E3. Item and category names are not enough to distinguish qualifying merchant, painting or enemy acquisitions.

For stats and upgrades, expose actual character level, base/unbuffed attributes, charge allocation, flask potency and achieved blessing levels. Confirm pinned field names before implementation and live-read them afterward. Artificial blessing floors or auto-state writers must either be declared valid in the AP rule or cause the earned-upgrade square to be excluded. Observability makes these small adapters, but attainability requires the corresponding upgrade/stat supplies in logic.

### Stage 3 Add provenance and player actions

For each quest or one-shot action, enumerate all flag writers in the event corpus and client. Reuse a transition only if it uniquely proves the qualifying player action. Otherwise capture the action and persist it. Memory of Grace requires item-use plus pre-use rune balance; crafting requires a successful craft transaction; duplication requires an actual duplication action; transformation and concoction squares require use, not ownership.

For ordinary enemies, promote E3 rows to E2 when a complete qualifying roster has safe persistent death flags. Otherwise introduce map/entity kill events with stable identities across reloads and respawns. Source acquisition joins the actual local encounter or interaction to its award; a randomized AP location's synthetic flag is insufficient. Reject unavailable vanilla-source supplies or provide a separately named AP adaptation, rather than silently weakening the square.

### Stage 4 Add restricted combat or referee confirmation

Implement encounter start/reset/end, player-hit events, successful parries, summoned participants, inflicted statuses, damage source category and fatal-hit attribution. Include reinforcement levels and allowed weapon/spell provenance at the damaging action, including projectiles and delayed effects. A reconnect or event gap during the winning attempt leaves it unverified. Equipment at boss death cannot establish an only-weapons rule.

Referee confirmation is an explicit alternative predicate with its own UI and audit trail; do not mark it as automatic. Define source-rule ambiguities before building detectors, including blocked hits, allied status application, summoned participation, minimum Rennala summons and qualifying uses of finger items.

## Archipelago logic and board selection

Every objective adapter owns both a runtime predicate and a generation predicate. Counters resolve a reachable roster and required threshold; collection predicates prove enough distinct qualifying supply; quest/actions declare route and state prerequisites. Item supply required to win becomes progression when appropriate. Prove that objective rewards do not gate their own prerequisites, including partner-world cycles. Check that all selected objectives can coexist for blackout; individual reachability is insufficient for mutually exclusive NPC quest branches.

The board selects objectives and retains their regions plus prerequisites. For counters, select a sufficient contributor set within the budget rather than retain every possible contributor globally. Fail with the target, remaining eligible count and region-budget reason if a variant cannot fit. Do not lower targets or replace strict source rules after the draw. Stable template-family uniqueness, overlapping contributor caps and sphere-zero unlock capacity must all be enforced before fill.

Preserve 25 reward locations and the existing first-line non-progression reservation. An objective with several contributors still owns one reward check. Keep action facts separate from reward collection, acquired inventory and synthetic sweep flags.

## Definition of ready for automatic release

An audit row moves from estimated to ready only when it has:

1. Pinned source interpretation and resolved variants, with AP adaptations visible in the square rules.
2. Concrete game signals or confirmed event hooks, every synthetic writer reviewed, and normalized contributor identities.
3. Matching generation logic, supply and region constraints, overlap limits, and a joint blackout compatibility check.
4. Replay/reload/save-binding behavior and pure decision tests, including false-positive cases caused by AP collect, reconciliation and sweeps.
5. Native Windows compilation and live evidence of qualifying action, a non-qualifying action, reload and reconnect. Combat adapters additionally prove complete attempt coverage.

Until then, the tables below are an implementation plan. All 25 objectives on the current boss board use automatic detection; this audit does not certify all 300 community variants.

## Complete template audit

The machine-readable [variant ledger](bingo-objective-audit.csv) contains one row for each of the 300 expanded alternatives, including parameters, effort, evidence and blockers. The tables below cover all 213 source templates once. `K` means an audited boss fact, `S` an achieved state value, `R` a curated encounter/dungeon roster, `I` an acquisition ledger, `A` an action/transition, `P` source provenance, and `N` an ordinary entity death. `C` means full encounter telemetry. These are proposed detectors, not implemented status.

### E1 template assignments

| Source ID | Objective audit label | Variants | Evidence | Main qualification or blocker |
|---|---|---:|---|---|
| S6-BASE-004 | Defeat Morgott | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-005 | Defeat Rykard | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-006 | Defeat an Ancestor Spirit | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-007 | Defeat Magma Wyrm Makar | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-008 | Defeat Mohg, Lord of Blood | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-010 | Defeat Leonine Misbegotten | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-013 | Defeat a Godskin Apostle | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-014 | Defeat Godfrey (Gold Spirit) | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-016 | Defeat Fia's Champions | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-017 | Defeat Mohg, the Omen | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-018 | Defeat Loretta (Blue Spirit) | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-019 | Defeat Commander O'Neil | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-020 | Defeat Grafted Scion (Chapel) | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-023 | Defeat Tree Sentinel Duo | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-024 | Defeat Crucible Knight and Misbegotten Warrior Duo | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-025 | Defeat Elemer of the Briar | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-026 | Defeat Putrid Crystalian Trio Boss | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-027 | Defeat Wormface | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-031 | Defeat a Dragonkin Soldier Boss | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-034 | Defeat a Black Blade Kindred | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-068 | Defeat Fire Giant | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-078 | Collect Sacred Flask +7 | 1 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-BASE-079 | Collect 10 Sacred Flask Charges | 1 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-BASE-096 | Rune Level %num% (num: 55, 60, 65) | 3 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-BASE-097 | 30 Faith | 1 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-BASE-098 | 30 Arcane | 1 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-BASE-099 | 30 Intelligence | 1 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-BASE-100 | Defeat Ancient Dragon Lansseax | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-111 | Defeat Malenia | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-112 | Defeat Borealis | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-115 | Defeat Misbegotten Crusader | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-BASE-117 | Defeat Roundtable Knight Vyke | 1 | K | Use the Roundtable Knight encounter in the Lord Contender Evergaol, not the Festering Finger invasion. |
| S6-DLC-002 | Level %num% Scadu (num: 9, 10, 11) | 3 | S | Actual blessing level is observable, but AP floor/scaling writers may supply it automatically; exclude those configurations for earned-upgrade rules. |
| S6-DLC-003 | Level 5 Revered Spirit Ash | 1 | S | Read achieved Revered Spirit Ash blessing; received fragments are not the same as upgrading. |
| S6-DLC-005 | Defeat the Golden Hippo | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-007 | Defeat Bayle | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-009 | Defeat Midra | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-011 | Defeat Promised Consort Radahn | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-024 | Defeat Ancient Dragon Senessax | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-037 | Defeat Jori, Elder Inquisitor | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-043 | Defeat Lamenter | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-048 | Defeat a Death Knight | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-061 | Defeat Chief Bloodfiend | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-062 | Defeat Putrescent Knight | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-064 | Defeat Scadutree Avatar | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-065 | Defeat Rellana | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-066 | Defeat Metyr | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-067 | Defeat Messmer | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-068 | Defeat the Fallingstar Beast | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-069 | Defeat Romina | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-073 | Defeat the Ancient Dragon-Man | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-076 | Defeat the Death Rite Bird | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |
| S6-DLC-083 | Rune Level %num% (num: 80, 85) | 2 | S | Read actual achieved value, not received item count; define base/unbuffed stats and exclude artificial scaling floors where required. |
| S6-DLC-086 | Defeat Rakshasa | 1 | K | Resolve exact encounter and prerequisite route; audit every synthetic writer. DLC and legacy mappings are not in the current draw. |

### E2 template assignments

| Source ID | Objective audit label | Variants | Evidence | Main qualification or blocker |
|---|---|---:|---|---|
| S6-BASE-011 | Defeat %num% (num: 1 Unique Red Wolf, 2 Unique Red Wolves, 3 Unique Red Wolves) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-015 | Defeat %gargs% (gargs: Valiant Gargoyles, 3 Unique Gargoyles/BBK, 4 Unique Gargoyles/BBK) | 3 | R | Valiant Gargoyles variant is E1; broader unique Gargoyle/Black Blade Kindred counts are E2 and require explicit qualifying encounter units. |
| S6-BASE-030 | Defeat %num% Bosses with "God" in their name (num: 3, 4) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-032 | Defeat %num% (num: 1 Magma Wyrm, 2 Magma Wyrms, 3 Magma Wyrms) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-033 | Defeat %num% (num: 1 Fallingstar Beast, 2 Fallingstar Beasts) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-035 | Defeat %numofbosses% (numofbosses: 1 Omenkiller Boss, 2 Omenkiller Bosses) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-036 | Defeat 2 Deathbirds and 1 Death Rite Bird | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-037 | Defeat %numofbosses% Unique Cemetery Shades (numofbosses: 2, 3) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-039 | Defeat %numofbosses% Misbegotten Bosses (numofbosses: 2, 3) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-040 | Defeat %numofbosses% Unique Watchdogs (numofbosses: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-041 | Defeat %numofbosses% (numofbosses: 1 Duelist Boss, 2 Duelist Bosses) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-042 | Defeat %numofbosses% Unique Black Knife Assassins (numofbosses: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-044 | Defeat %numofbosses% Dragon Heart Bosses (numofbosses: 3, 4) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-045 | Defeat %numofbosses% Unique Erdtree or Putrid Avatars (numofbosses: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-046 | Defeat %numofbosses% Unique Night's Cavalry (numofbosses: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-047 | Defeat %numofbosses% Unique Tibia Mariners (numofbosses: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-048 | Defeat %numofbosses% Bell Bearing Hunters (numofbosses: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-049 | Defeat 3 Duo/Trio Bosses | 1 | R | Curate fight-level duo/trio identities; never infer number of bosses from a display name or number of healthbars. |
| S6-BASE-050 | Defeat 5 Bosses that Ride a Horse | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-051 | Defeat 5 Bosses with "Tree" in their name | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-059 | Defeat %numofbosses% Bosses in Limgrave / Weeping (numofbosses: 4, 5, 6) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-060 | Defeat %numofbosses% Bosses in Liurnia (numofbosses: 4, 5) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-061 | Defeat %numofbosses% Bosses in Caelid / Dragonbarrow (numofbosses: 4, 5) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-062 | Defeat %numofbosses% Bosses in Altus Plateau / Mt. Gelmir (numofbosses: 4, 5, 6) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-063 | Complete %num% Catacombs (num: 2, 3) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-064 | Complete %num% Caves or Grottos (num: 2, 3) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-065 | Complete %num% Tunnels or Precipices (num: 2, 3) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-066 | Complete an Altus Plateau or Mt. Gelmir Hero's Grave | 1 | R | Use the terminal objective for each eligible Hero grave and its access route; a grace or first boss is not automatically completion. |
| S6-BASE-067 | Complete %num% Evergaols (num: 2, 3, 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-069 | Collect Somberstone Bell Bearing [1] and [2] | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-070 | Collect Smithing-Stone Bell Bearing [1] and [2] | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-071 | Collect Grave and Ghost Glovewort Bell Bearings [1] | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-072 | Collect Grave and Ghost Glovewort Bell Bearings [2] | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-073 | Collect Margit's and Mohg's Shackles | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-080 | Collect 10 Cracked Pots | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-081 | Collect 5 Ritual Pots | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-082 | Collect %talisman% (talisman: 10 Unique Talismans, 3 Legendary Talismans) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-083 | Collect Both Scarseal Talismans | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-086 | Collect the Fingerslayer Blade | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-094 | Collect 12 Unique Sorceries | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-095 | Collect 14 Unique Incantations | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-105 | Collect 6 Unique Staves | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-108 | Collect %num% Memory Stones (num: 3, 4, 5) | 3 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-110 | Collect the Full Haligtree Medallion | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-113 | Defeat Both Astel Bosses | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-BASE-114 | Defeat 4 NPC Bosses | 1 | R | Curate NPC boss encounters rather than assume every invading NPC is a boss; missing stable flags promote individual contributors to E3. |
| S6-BASE-116 | Collect the Moon of Nokstella | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-120 | Collect %num% Imbued Sword Keys (num: 2, 3) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-121 | Collect %num% Whetstone Knives (num: 3, 4) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-BASE-122 | Collect %num% Unique Seals (num: 3, 4) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-001 | Collect %num% Hanging Pot Bell Bearings (num: 2, 3) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-008 | Complete 2 Catacombs | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-015 | Defeat 3 Dragon Bosses | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-019 | Collect %num% Kindred Cookbooks (num: 2, 3, 4) | 3 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-020 | Complete 2 Gaols | 1 | R | Gaol completion uses curated terminal encounter identities and route constraints. |
| S6-DLC-021 | Defeat %num% (num: 1 Dancing Lion, 2 Dancing Lions) | 2 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-022 | Collect Commander Gaius's Pants | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-025 | Collect Jolan Summon | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-026 | Defeat %num% (num: 1 Red Bear, 2 Red Bears, all 3 Red Bears) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-028 | Defeat 3 NPC Bosses | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-033 | Collect 3 DLC Ashes of War | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-034 | Collect 3 DLC Spirit Ashes | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-035 | Collect 2 Dragon Hearts | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-036 | Collect the %talisman% Talisman (talisman: Two-Handed Sword, Two-Headed Turtle) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-039 | Collect the Scorpion Stew | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-040 | Collect the Golden Braid | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-046 | Collect a Leda Rune | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-050 | Collect %num% Full DLC Armor Sets (num: 2, 3) | 2 | I | Normalize armor pieces to curated complete sets and prove all required pieces can coexist in this seed; individual-piece counts are insufficient. |
| S6-DLC-053 | Collect %num% Hefty Pots (num: 4, 5) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-057 | Collect Igon's Furled Finger | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-058 | Complete %num% Nameless Mausoleums (num: 2, 3, all 4) | 3 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-070 | Defeat %num% in the DLC (num: 1 Unique Base Game Boss, 2 Unique Base Game Bosses) | 2 | R | Qualifying roster contains base-game boss types encountered in DLC; regions and type membership must both match. |
| S6-DLC-071 | Defeat 3 Bosses with "Knight" in their name | 1 | R | Pin qualifying roster and count unit; multi-enemy fights count under explicit rules; retain enough reachable contributors and prerequisite closure. |
| S6-DLC-074 | Collect the Full Gravebird Armor Set | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-075 | Collect Death Mask Helm, Winged Serpent Helm, and Salza's Hood | 1 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-077 | Collect %num% Blessings of Marika (num: 2, 3) | 2 | I | AP adaptation: local acquisitions or successful remote grants; normalize IDs; exclude starting gifts; retain sold/stored/spent credit; prove item supply and classify required supply as progression. |
| S6-DLC-080 | Collect %num% Unique Max Upgrade Materials (num: 2, 3) | 2 | I | Normalize material identities and base/DLC scope; repeated copies do not increase distinct-material count. |
| S6-DLC-082 | Defeat 1 Boss of each: Bear / Lion / Hippo | 1 | R | Three independent category predicates: at least one qualifying Bear, Lion and Hippo encounter; no single fight can satisfy several categories by accident. |

### E3 template assignments

| Source ID | Objective audit label | Variants | Evidence | Main qualification or blocker |
|---|---|---:|---|---|
| S6-BASE-038 | Defeat %numofbosses% Unique Abductor Virgins (numofbosses: 2, 3) | 2 | N | Unique Abductor Virgins may include non-healthbar entities; settle qualifying roster and duo-unit rules before treating as a boss counter. |
| S6-BASE-043 | Defeat %numofbosses% Unique Crucible Knights (numofbosses: 2, 3, 4) | 3 | N | Unique Crucible Knights may include ordinary enemies; do not substitute a healthbar-only roster without an explicit adaptation. |
| S6-BASE-074 | Restore Godrick's Great Rune | 1 | A | Restoration requires the actual Divine Tower activation; possession of a randomized Great Rune or a defeat flag is not restoration. |
| S6-BASE-075 | Restore Radahn's Great Rune | 1 | A | Restoration requires the actual Divine Tower activation; possession of a randomized Great Rune or a defeat flag is not restoration. |
| S6-BASE-076 | Restore Rykard's Great Rune | 1 | A | Restoration requires the actual Divine Tower activation; possession of a randomized Great Rune or a defeat flag is not restoration. |
| S6-BASE-077 | Restore Morgott's Great Rune | 1 | A | Restoration requires the actual Divine Tower activation; possession of a randomized Great Rune or a defeat flag is not restoration. |
| S6-BASE-084 | Take Rya's hand to Volcano Manor | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-BASE-085 | Return Thops's Academy Key | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-BASE-087 | Defeat Magnus the Beast Claw | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-BASE-088 | Duplicate a Remembrance | 1 | A | Record an actual duplication transaction; a second copy or restoration grant does not prove duplication. Randomized supplies may block it. |
| S6-BASE-089 | Memory of Grace with 100k+ Runes | 1 | A | Observe Memory of Grace use and rune balance immediately before use; death, balance snapshots, or item possession do not prove this action. |
| S6-BASE-090 | Defeat 4 NPC Invaders | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-BASE-091 | Defeat 3 Friendly NPCs (No Hermit Merchants) | 1 | N | Curate friendly NPC identities and exclude Hermit Merchants; reject route sets conflicting with another square or required quest. |
| S6-BASE-092 | Defeat Gurranq | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-BASE-101 | Defeat Preceptor Miriam | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-BASE-102 | Give Hyetta 3 Shabriri Grapes | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-BASE-103 | Give Millicent her Prosthetic Arm | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-BASE-104 | Defeat 3 Unique Tree Spirits | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-BASE-106 | Collect %num% Larval Tears from Transforming Enemies (num: 3, 4) | 2 | P | Link qualifying transformation encounter to Larval Tear acquisition; raw tear count or synthetic location flags cannot prove this source. |
| S6-BASE-107 | Collect %num% Dropped Ashes of War (num: 4, 5, 6) | 3 | P | Define which enemy/NPC drops qualify; randomized source pickup may not deliver an Ash of War. Keep strict and AP-adapted modes separate. |
| S6-BASE-109 | Collect 3 Painting Rewards | 1 | P | Require the painting puzzle and its local reward interaction, not possession of a randomized reward item. |
| S6-BASE-118 | Defeat the Sleeping Golem in Leyndell | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-BASE-119 | Defeat %num% Unique Elder Lions (num: 2, 3, 4) | 3 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-004 | Defeat %num% (num: 1 Furnace Golem, 2 Furnace Golems) | 2 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-006 | Defeat 2 Hippos | 1 | N | The larger Hippo roster includes non-healthbar encounters; verify individual persistent death evidence before promotion to E2. |
| S6-DLC-010 | Collect 2 Painting Rewards | 1 | P | Observe both qualifying painting rewards; randomized inventory alone cannot establish painting provenance. |
| S6-DLC-013 | Collect the Kindred Cookbook from Moore | 1 | P | Require the actual Moore gift/acquisition event, with quest branch and item identity; any remotely received Kindred cookbook is insufficient. |
| S6-DLC-014 | Put Florissax to Sleep | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-DLC-016 | Complete 2 Forges | 1 | A | Forges have no interchangeable terminal boss signal; pin each forge completion interaction and its action-safe evidence. |
| S6-DLC-017 | Give an Iris of Grace | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-DLC-018 | Give an Iris of Occultation | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-DLC-023 | Defeat 3 Ulcerated Tree Spirits | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-027 | Defeat 3 Unique NPC Invaders | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-029 | Defeat Black Knight Garrew | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-030 | Collect %num% Enemy/NPC Dropped Talismans (num: 3, 4) | 2 | P | Remote grant alone does not establish source; correlate actual local action/source with acquisition and persist it; randomized loot may require a disclosed rule adaptation. |
| S6-DLC-031 | Defeat Moonrithyll, Carian Knight | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-032 | Defeat %num% (num: 3 Unique Curseblade Assassins, Curseblade Labirith) | 2 | N | Curseblade Labirith variant is E1; three unique ordinary Curseblade Assassins is E3 without stable entity-death evidence. |
| S6-DLC-038 | Defeat Queelign in Belurat | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-041 | Defeat the Rolling Giant Lightning Ram | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-042 | Defeat Madding Hand | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-044 | Duplicate a Remembrance %num% (num: 1 time, 2 times, 3 times) | 3 | A | Count actual duplication transactions at distinct allowed sites under pinned rules; duplicate inventory or AP grant replay never counts. |
| S6-DLC-045 | Memory of Grace with 500k+ Runes | 1 | A | Observe Memory of Grace use with at least 500,000 runes immediately before the action; do not infer from a subsequent balance drop. |
| S6-DLC-047 | Collect 3 NPC Dropped Weapons | 1 | P | Remote grant alone does not establish source; correlate actual local action/source with acquisition and persist it; randomized loot may require a disclosed rule adaptation. |
| S6-DLC-049 | Collect %num% Non-Merchant Perfume Bottles (num: 3, all 4) | 2 | P | A source rule: exclude merchant acquisition even for a qualifying perfume item; bought and remote copies cannot prove eligibility. |
| S6-DLC-051 | Collect %num% Non-Merchant Sorceries (num: 2, 3) | 2 | P | Non-merchant sorceries need source-qualified acquisition; a spell learned from a random grant cannot meet the strict rule. |
| S6-DLC-052 | Collect %num% Non-Merchant Incantations (num: 5, 6) | 2 | P | Non-merchant incantations need source-qualified acquisition; a spell learned from a random grant cannot meet the strict rule. |
| S6-DLC-054 | Defeat Leda and her Allies | 1 | A | Leda encounter depends on quest/finale transitions and participants; verify endpoint and route rather than assume one death flag proves the whole fight. |
| S6-DLC-055 | Burn the Sealing Tree | 1 | A | Observe the player burn action; a reconciliation-opened barrier cannot prove the Sealing Tree was burned. |
| S6-DLC-056 | Drain the Water in the Church District | 1 | A | Audit the actual Church District drainage transition and its flag writers; synthetic access state is insufficient. |
| S6-DLC-063 | Use a Transformation | 1 | A | Observe transformation activation, not possession of the transformation item. |
| S6-DLC-072 | Defeat 3 Trolls | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-078 | Craft %num% Unique Hefty Pots (num: 2, 3) | 2 | A | Record successful craft transactions and normalized output types; acquiring or holding pots does not prove crafting. |
| S6-DLC-079 | Defeat %num% Unique Horned Warriors (num: 3, 4, 5) | 3 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-081 | Defeat the Colossal Fingercreeper | 1 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-084 | Drink Thiollier's Concoction | 1 | A | Record consuming the concoction, including consumption failure/reload; possession and an arbitrary death are insufficient. |
| S6-DLC-085 | Blow a Finger | 1 | A | Pin the source rule interpretation for finger use; then observe the qualifying horn action, not inventory ownership. |
| S6-DLC-087 | Give the Secret Rite Scroll to Ansbach | 1 | A | Item possession and AP check acknowledgement do not prove the action; identify an action-safe transition and exact prerequisites; exclude repair/reconciliation writes. |
| S6-DLC-089 | Defeat %num% (num: 1 Unique Divine Bird Warrior, 2 Unique Divine Bird Warriors) | 2 | N | Inspect each qualifying entity for a stable death flag; otherwise add kill events with map/entity identity and distinctness; do not count unloads, respawns, or synthetic sweeps. |
| S6-DLC-090 | Defeat %num% (num: 1 Demi-Human Swordmaster, 2 Demi-Human Swordmasters) | 2 | N | Some swordmaster candidates may be ordinary entities; resolve the roster and stable flags before assigning all variants to boss counters. |
| S6-DLC-091 | Defeat Crucible Knight Devonia | 1 | N | Devonia is not assumed to have a persistent boss-healthbar completion flag; verify entity death identity before promotion. |

### E4 template assignments

| Source ID | Objective audit label | Variants | Evidence | Main qualification or blocker |
|---|---|---:|---|---|
| S6-BASE-001 | Defeat Godrick while Summoning Nepheli Loux | 1 | C | Track Nepheli participating during the winning encounter; summoned once or present at death alone is insufficient without pinned rule interpretation. |
| S6-BASE-002 | Defeat Rennala after she Summons 4 Spirits | 1 | C | Count Rennala summon events in the successful phase/attempt, including attribution and reset boundaries. |
| S6-BASE-003 | Defeat Radahn without Status Effects and Summons | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-009 | Defeat Margit with %strategy% (strategy: 6+ Parries, a +0 Weapon Only) | 2 | C | Parry-count variant needs attributed successful parries; +0-only variant needs every damage source and reinforcement level, not just equipped weapon at death. |
| S6-BASE-012 | Defeat Godskin Noble (Volcano Manor) without Status Effects | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-021 | Defeat Soldier of Godrick with Bare Fists Only | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-022 | Defeat %starter% with a +0 Weapon Only (starter: Tree Sentinel (Limgrave), Agheel) | 2 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-028 | Defeat Darriwil while Summoning Blaidd | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-029 | Defeat Greyoll without Status Effects | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-052 | Defeat a Remembrance Boss Hitless | 1 | C | HP polling cannot prove hitless: healing between samples can conceal a hit. Define whether blocked damage or zero-damage hits invalidate the attempt. |
| S6-BASE-053 | Defeat a Remembrance Boss with Whips Only | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-054 | Defeat a Remembrance Boss with Daggers Only | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-055 | Defeat a Remembrance Boss with Bows Only | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-056 | Defeat a Remembrance Boss with %magic% Only (magic: Sorceries, Incantations) | 2 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-057 | Defeat a Remembrance Boss with Remembrance Weapons Only | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-BASE-058 | Finish off a Boss with the Explosive Physick | 1 | C | Attribute the fatal damage event to the explosive Physick effect, including delayed damage; an active buff at death is insufficient. |
| S6-BASE-093 | Defeat 10 Sheep with AoW Lightning Ram Only | 1 | C | Track distinct eligible sheep deaths and Lightning Ram damage attribution; respawning/reloaded actors must not create duplicate credit. |
| S6-DLC-012 | Defeat a Remembrance Boss Hitless | 1 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-DLC-059 | Defeat a Remembrance Boss with Remembrance Weapons Only | 1 | C | Attribute every damage contribution to allowed Remembrance weapons, including skills, consumables, allies and summons. |
| S6-DLC-060 | Defeat a Boss with %magic% Only (magic: Incantations, Sorceries) | 2 | C | Require uninterrupted encounter coverage with damage/action attribution, resets and reload handling; fail closed if events are lost; AP victory/check state alone is insufficient. |
| S6-DLC-088 | Defeat a Boss after Inflicting %num% Unique Status Effects (num: 3, 4) | 2 | C | Track distinct status applications during the successful boss attempt, attributable under the source rules; equipment/buff presence is insufficient. |



## E1 implementation (2026-10-03)

`bingo_catalogue: e1` enables adapters for all 61 E1 audit variants: 47 boss
variants and 14 native-state thresholds. Source alternatives are one board family;
ambiguous boss families resolve to a labelled concrete encounter. The draw mixes
these with the original boss pool and ordinary DLC encounters to fit 25 squares
within the region cap. This is an AP adaptation, not strict tournament adjudication.
The original catalogue remains the default; existing v1 seeds still load.

State observations are rune level; base Faith, Arcane and Intelligence; total flask
allocation and flask potency; earned Scadutree and Revered Spirit Ash blessing.
Temporary stat buffs do not count. Completion is latched in the client sidecar,
keyed by board hash and native save slot. The existing character binding clears
that slot's ledger for a fresh/recreated character or a rolled-back play-time stamp.
Respec, reconnect and client restart retain earned state squares. Server collect
alone earns nothing. Victory still requires local evidence plus server acknowledgement.

Only one supply-heavy state square is drawn. Flask squares require progressive
flasks, raise that feature's supply floor and classify the required copies as
progression. +7 needs 14 copies; 10 charges needs 11. Scadutree 9/10/11 needs
17/20/23 units, supplied as 9/10/12 x2 progression drops. Revered Spirit Ash 5
needs nine units (upgrade costs 1+2+2+2+2). All extra supplies displace filler;
progression stays on the 25 squares. Unused Great Runes retain useful supply,
because bingo replaces the rune ending. Level/stat squares assume repeatable
native rune farming in their owner region, with no required finite rune item count.

Scadutree squares are excluded when global or catch-up blessing modes manufacture
the observed level. Use `presets/bingo-e1.yaml` for earned vanilla DLC blessings.
Base-only and DLC-only draws omit objectives outside their eligible content.
Boards that cannot fit the region cap reject with an option error.
Ordinary capacity validation rejects configurations exceeding the square budget.

Boss rules inherit their native reward checks' final access rules, including legacy
keys. Chapel explicitly keeps Liurnia plus Stormveil and requires an Imbued Sword
Key; Metyr keeps Scadu Altus, Cerulean and Shadow Keep. Duo/trio goals use the
encounter's terminal flag, and multi-phase bosses use the mapped terminal encounter.
AP flag writers are prevented from asserting any board defeat flag; native polling
still reports boss reward checks normally.

Map for Goblins continues highlighting boss targets. Its pinned boss catalogue
contains 45 of the 53 concrete E1 encounter candidates. Labirith, Jori, Lamenter,
both Death Knights, Chief Bloodfiend, the dungeon Ancient Dragon-Man and Rakshasa
have no boss-marker row in that version. These and all state squares remain visible
in the F6 board. Marker expansion is separate work; no marker is fabricated at an
unverified coordinate.

Evidence: generated `boss_healthbars`, `boss_sweeps`, `boss_reward_lots`; EMEVD
terminal events (including m31_11's three-way death condition and Redmane's duo);
locked fromsoftware-rs `af8f38c` PlayerGameData fields; GoodsName.fmg rows
1000..1025 / 1050..1075 for current flask potency; `scadu_supply.SCADU_CUM`.
The [Revered Spirit Ash upgrade table](https://eldenring.fandom.com/wiki/Revered_Spirit_Ash)
corroborates its cumulative nine-unit floor. Native reads are restricted to a live,
living player in their own world. Automated checks verify generation and threshold
logic; a live E1 gameplay run is still required to validate native observations.


### Bingo travel correction (2026-10-03)

Bingo mints no Region Lock items and precollects none. Each selected region is
reachable from the hub immediately; internal reached events preserve the existing
feature logic without putting lock tokens in the item pool or network stream.
`areaLockFlags` is explicitly empty, including for omitted regions, so the client
has no kick enforcement. `start_regions` and `start_region_pool` do not restrict
bingo starts. All generated safe graces for the selected regions are startup grants,
with their region-open witnesses for the tracker. `regionGraces` and attunement are
empty because travel is granted at startup. Board rewards remain the progression
surface for equipment, keys and objective supplies.

The community tool's Season 6 base rules API was retrieved on 2026-10-03
(`/api/leagues/bingo-brawlers/seasons/season-6-base/rules`, published version 2).
It covers both base and DLC rulings but contains no startup grace manifest. The
square JSON also contains no startup configuration. The official Season 6 mod is
[distributed separately on Nexus](https://www.nexusmods.com/eldenring/mods/9972).
Its exact startup grace list remains unverified; these generated AP bundles are our
own travel policy, not a claim to reproduce that mod's list. The public Nordgaren
ERBingoRandomizer repository last changed in 2024 and is not Season 6 evidence.
