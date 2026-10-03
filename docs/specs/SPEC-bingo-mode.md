# Elden Ring Archipelago bingo mode

Design specification, 2026-10-03. The final section records the implemented experimental boss-board slice; the broader catalogue, adapters, and multiplayer sections remain proposals.

Give each Elden Ring slot a seeded 5 by 5 board built from Elden Ring bingo objectives, and make those objectives the progression surface: completing a square sends its AP reward. Completing a line can release a larger batch of checks, or end a short run. The recommended first release is an automatically tracked, per-slot board using a documented subset of Season 6 objectives, with a short-run preset and an optional line sweep. A separate referee mode can expose the full catalogue. Shared team boards and competitive lockout follow once synchronization and adjudication exist.

Design direction revised with Alaric on 2026-10-03: the board should drive progression and payouts, rather than act only as a victory overlay on the ordinary location surface. See the implemented slice below for the current scope.

## Square sources and completeness

The [objective implementation audit](DESIGN-bingo-objective-audit.md) ranks all 213 Season 6 templates and all 300 expanded variants by implementation effort, with a [variant ledger](bingo-objective-audit.csv). Its effort estimates are separate from verified detector coverage. Start with persistent encounter facts and counters; collections, source provenance, actions, and restricted combat require further adapters.

The best working source found is the [Elden Ring Bingo Community Tool](https://erb-community-tool.vercel.app/). It has season navigation for Seasons 1 through 6, searchable square descriptions, rules, and downloadable original-format JSON. It is a community archive, so its contents should be checked against the official season files before advertising tournament fidelity.

The following downloads were retrieved and parsed on 2026-10-03:

| Catalogue | Download | Templates | Expanded variants |
|---|---|---:|---:|
| Season 6 base game | [JSON](https://erb-community-tool.vercel.app/squares/season-6/season-6-base.json) | 122 | 177 |
| Season 6 DLC | [JSON](https://erb-community-tool.vercel.app/squares/season-6/season-6-dlc.json) | 91 | 123 |
| Combined | Both files, retaining their separate namespaces | 213 | 300 |

“Template” means one JSON entry. “Expanded variants” means the product of each entry's distinct token substitution arrays, summed over entries. These counts describe these downloads, not a promise that every variant is attainable or automatically detectable in Archipelago. A variable-count objective remains one family when generating a board; its different targets must not occupy several cells.

Snapshot SHA256 values, computed over the locally saved UTF-8 downloads:

- Base: `4578854890ecef28f4174c61e9e515a2d9b04fb88a8f23c3cb17ce5bf58af0c0`
- DLC: `d8b76baddc4a105c49a3a4fd0d7ad70b8d39b0db2e8ed4f98f8f0277e5e0d8cd`

The [base catalogue](https://erb-community-tool.vercel.app/leagues/bingo-brawlers/seasons/season-6-base/squares), [DLC catalogue](https://erb-community-tool.vercel.app/leagues/bingo-brawlers/seasons/season-6-dlc/squares), and [season rules](https://erb-community-tool.vercel.app/leagues/bingo-brawlers/seasons/season-6-base/rules) provide the browsable context. The archive's rule page makes uniqueness, qualifying acquisition, boss encounters, and restricted combat material to objective completion. Archipelago needs explicit adaptations for these conditions.

The primary authority remains [Bingo Brawlers](https://bingobrawlers.com/). [EldenBingo](https://github.com/awsker/EldenBingo) links an [official example JSON](https://bingobrawlers.com/files/bingo-brawlers.json) and documents token substitutions, category constraints, and center placement. That example's season could not be verified: the official host returned Cloudflare 522 during this investigation. Do not label the example as Season 6.

A reproducible older alternative is [Bingosync's Elden Ring generator](https://github.com/kbuzsaki/bingosync/blob/main/bingosync-app/generators/elden_ring_generator.js), containing 111 entries when retrieved. It is a separate catalogue, not the complete current Season 6 list. [ER Bingo DB](https://erbingodb.com/) is another discovery lead, but its application did not finish loading during this investigation.

For implementation, retain source URL, season, retrieval date, content hash, attribution, and redistribution terms with each import. A download link does not establish a licence to bundle the list. Until redistribution is established, support a user-supplied JSON import and ship our own mappings and adapters. Do not copy SoulsRandomizers-derived data into this catalogue.

## Board objectives as the progression surface

Each of the 25 squares owns one new synthetic AP location, named for its resolved objective. Completing it sends that location check exactly once. Its reward is determined by normal generation and can belong to this slot or another game. A square is therefore both a task the player can plan around and a visible progression opportunity. It never counts as a native boss drop or acquisition event merely because its AP check was accepted.

Bingo replaces the tag-based progression surface for this slot. Ordinary exploration checks remain available, but receive non-progression rewards. All progression placed in this ER world's locations, including incoming progression for other players, must land on square reward checks. This also requires an explicit bingo treatment of current exemptions such as Boss Keys and ability Unlock items; do not accidentally inherit exemptions that put progression back into hidden exploration checks. Progression items belonging to this ER slot may still be placed in partner worlds according to the selected progression-sharing policy.

The square surface has a hard capacity of 25. If the selected multiworld policy requires more progression placements here than the board can hold, generation must fail with a useful capacity explanation. It must not reuse the ordinary surface's widening ladder and quietly spill progression onto bosses, shops, or pickups. Future multiple-reward squares could increase capacity, but are outside the first release. Cross-world placement is an option only when the user's sharing policy permits it.

Use a separately reserved AP location ID band for squares, with IDs tied to board cell indices within a seed and the board hash validating identity. Do not reuse a native location ID or change the global native ID ledger. Adding 25 square locations adds 25 declared filler items to the pool; existing progression items move onto the board through constrained fill. This is a count-neutral extension: pool length increases by exactly the number of new randomized locations. Existing native checks retain their identity and can still provide local action evidence.

The gameplay loop is: complete an accessible square, receive or send an unlock, gain access to more candidate objectives, complete a line, and receive its milestone payout or short-run victory. The board must have enough sphere-zero objectives to host the unlocks that bootstrap that loop. A task's reward can never be its own prerequisite, directly or through another square or partner game.

## Player experience and victory

The board lives in a Bingo tab beside the existing tracker. Each cell shows its objective, progress, completion state, and whether it uses automatic detection or referee confirmation. Opening a cell explains qualifying actions, applicable regions, and any adaptation from the source rule. A compact HUD shows marked squares and closest line; an optional spectator view uses the same board state.

The initial win conditions are:

| Setting | Completion rule |
|---|---|
| Line, short-run default | Any row, column, or full diagonal: 12 possible lines |
| Count | At least the configured number of squares, from 1 through 25 |
| Blackout | All 25 squares |

There is no free center. A source center designation selects a real eligible objective. Reveal the board when the fresh save is bound to the seed; tournament reveal timing is a later race feature. Normal AP play starts immediately. Completing bingo sends the slot's Goal status once and keeps square checks, exploration checks, and item delivery available to the rest of the multiworld. Square completion and line rewards dispatch before Goal so the winning square's payout is not lost at the end of a short run.

Bingo replaces the terminal boss requirement. It must not silently retain an additional requirement to collect every region lock, every ability unlock, or the old Great Rune goal. Those items still govern access where appropriate. If a separate combined ending is ever added, expose it as a distinct setting and display both requirements.

Short run means one line is sufficient for this slot's Goal; it does not guarantee that every item needed by partner games has already been sent. Keep the slot playable after Goal, show outstanding outgoing progression on the board, and document that a multiworld may require continued play. Recommend solo or agreed cooperative sessions for the initial short preset. Do not silently collect unfinished squares to finish the other games.

## Line sweep rewards

A line sweep is an optional bonus release of existing native checks when a line is earned. The proposal reuses the mod's idea of a sweep as a batch of AP checks, but bingo completion is a new trigger. A line is not a boss defeat flag and must have its own typed trigger. Do not manufacture a game flag or attach it to an unrelated existing boss sweep.

For the initial release, enable one larger sweep on the first completed line, rather than twelve separate jackpots. This works for both the short preset and a longer count or blackout run. A later per-line mode would need separate budgets and overlap rules; it is not required for the first release.

At generation, reserve a deterministic set of safe native locations in enabled, accessible content. Proposed default: up to 20 previously unreserved checks, fewer when the seed has a smaller eligible pool; show the resolved count before the run. Prefer a spread across the board's regions. Exclude synthetic square checks, missable checks, objective evidence that cannot survive collection, checks reserved by another payout trigger, and any location holding progression for any player. The bonus can provide useful gear, upgrades, or other non-progression rewards. It cannot contain an item required to reach the line that releases it.

Membership is a resolved generation input to logic, the contract, the tracker, and the spoiler log. It is not chosen by the client at the moment of victory. Existing boss or region sweeps must respect this reservation, so the line has a distinct reward budget. Reserved locations may still be collected manually; the line sends only remaining unchecked members. Display both total membership and remaining payout, making early collection visible rather than promising 20 new rewards regardless of play.

Never count a swept location as proof that its native action occurred. For example, sending a location associated with an item does not mean the player collected that item or completed a collection square. Observe the actual delivered item or qualifying local event under the objective's rules. One batch can complete several lines at once; latch the first-line milestone once, union pending check IDs, and retry only unacknowledged checks on reconnect.

This gives the two intended rhythms: **short** rewards five aligned objectives and ends on a line; **extended** uses the first line as a larger reward milestone while the player continues toward a square count or blackout. The sweep remains optional in either rhythm.

## Options and supported combinations

Proposed fields belong to `features/bingo.py` through its `OPTIONS` contribution. Names below are proposed, not existing YAML fields.

| Field | Values and initial default |
|---|---|
| `bingo_mode` | `off` by default; `automatic`; `referee` |
| `bingo_goal` | `line` by default; `count`; `blackout` |
| `bingo_square_count` | 1–25; default 13; used only by `count` |
| `bingo_catalogue` | Versioned S6 base, S6 DLC, or S6 mixed; base initially |
| `bingo_difficulty` | Short, standard, extended; standard initially |
| `bingo_excluded_squares` | Stable template IDs, initially empty |
| `bingo_line_sweep` | `off` or `first_line`; short preset proposes `first_line` |
| `bingo_line_sweep_size` | Proposed range 0–50; default 20; resolve against eligible non-progression checks |

Expose two presets rather than requiring the player to understand every field: Short Run selects a line goal; Extended Board selects a count goal, initially 13 squares. Both select the board progression surface and may enable the first-line sweep. Blackout remains an explicit longer variant. The chosen difficulty changes objective selection, not the number of reward checks.

Base-only and DLC-only seeds filter incompatible content. Mixed boards are explicitly an Archipelago format: they do not claim to reproduce tournament restrictions on crossing between base and DLC. Rolled region sets remain authoritative; the board does not secretly add regions. If fewer than 25 compatible families survive, generation fails with counts, excluded reasons, and suggestions to broaden regions or change catalogue.

The old terminal `goal`, ending condition, and region completion policy must be explicitly made inapplicable by the bingo goal branch. Reject conflicting explicit selections with an actionable OptionError; document how ordinary defaults are superseded. Requirements on abilities should apply to board prerequisites rather than imposing an undisclosed all-abilities ending.

Auto-equip, ability restrictions, synthetic movement modes, enemy substitutions, quest settings, and automatic progression writes can change objective meaning. Filter affected variants using declared capabilities. For example, a weapon-specific challenge cannot be selected when forced equipment prevents choosing that weapon. Never silently weaken a challenge or assume vanilla encounter behaviour under another mode.

## Catalogue normalization and coverage

Implement an offline importer, with no network dependency during generation. Parse the source JSON as data, expand named token choices deterministically, and produce stable template and variant IDs. IDs must survive changes in display wording; hash source identity separately. Reject undefined tokens, empty choices, duplicate IDs, and malformed entries. Preserve source wording separately from the player-facing AP adaptation.

Each mapped variant records its source template, resolved parameters, content set, required regions and capabilities, typed target roster, completion predicate, prerequisites, difficulty estimate, overlap family, detection tier, and exclusion reason. Keep a coverage ledger for every one of the 213 source templates, including unsupported variants. A source count must never be presented as an implementation coverage count.

Detection tiers are `automatic`, `referee`, and `unsupported`. Automatic mode selects only variants with both a reachable mapping and a verified observation path. Referee mode may select mapped challenges that require human evidence, but still excludes objectives impossible in the generated world. Unknown text never acquires a guessed predicate.

## Completion semantics

The following are proposed adapters, not claims that today's client implements these detectors:

| Objective family | AP treatment | Evidence and limits |
|---|---|---|
| Defeat a named boss | Preserve the encounter objective | Local encounter completion; no credit from another player's check or server collect command |
| Defeat several qualifying enemies | Count distinct eligible entities or encounters according to that variant | Explicit rosters and identities; a duo fight and two enemy kills are different units |
| Finish dungeons | Complete the qualifying dungeon objective | Curated dungeon roster and terminal condition; opening a grace is insufficient |
| Obtain distinct item types | AP adaptation counts qualifying items successfully delivered or locally acquired | Persistent acquisition ledger; delivery failures do not count; duplicates and upgrade copies normalize to the same base item |
| Obtain items from a particular source | Preserve source qualification or exclude | A remote grant alone cannot prove an NPC drop, painting reward, merchant exclusion, or transformation drop |
| Restore runes or advance quests | Preserve the actual action | Verified transition with provenance; receiving a rune or quest item alone is insufficient |
| Reach stats, flask strength, or blessing levels | Observe the actual required value | Unbuffed stats where required; fragments received and blessing level attained are different values |
| Craft, consume, duplicate, or intentionally lose resources | Observe the specific action | Inventory snapshots cannot prove that the action happened; referee until event detection exists |
| Hitless, summon restrictions, weapon restrictions, status challenges | Preserve the encounter restriction | Referee first; automatic support requires a complete encounter record, not equipment at death |

Acquisition objectives use an “ever acquired during this run” ledger unless the source explicitly requires current possession. Starting equipment and precollected gifts are displayed but excluded from fresh-run collection progress by default. This is an AP adaptation and must be stated in the cell rules. Consumables spent or items stored after acquisition retain earned collection credit. Restoring a delivered unique key after reload is not a new acquisition. Replaying ReceivedItems packets is not new progress.

A vanilla flag is not automatically proof of player action. Reconciliation, region unlocking, boss suppression, or quest repair may set flags. Audit each mapped flag's writers and derive observations from an action-safe signal. If a seed mode can synthesize the relevant completion flag without the encounter, exclude that objective or require referee evidence. Existing goal handling's local-first design is useful but does not eliminate this provenance problem.

Combat telemetry, when added, needs encounter start/reset/end, damage source and weapon, summon participation, status events, and relevant player-hit events. Lost events or a reconnect in the middle of a restricted encounter leave it unverified. Reset an invalid attempt where the boss is still alive; a permanently defeated boss cannot simply be retried to repair missing evidence.

## Board generation and Archipelago logic

Use a separate deterministic RNG stream so adding bingo does not perturb item placement randomness. Its inputs are AP seed identity, slot identity, catalogue hash, adapter version, and bingo options. Boards sharing a competitive ruleset also need a common board identity.

Generation proceeds as follows:

1. Normalize the catalogue and resolve variants against the final content, region, and capability choices.
2. Remove impossible or unsupported variants and build attainable counters from eligible rosters. Lower targets may remain eligible when larger ones do not; never rewrite a selected target downward.
3. Select 25 distinct template families with explicit caps on overlapping boss, dungeon, item, and quest groups. Avoid placing several objectives completed by the same single action in one line. Difficulty estimates come from AP routes and randomized supply, not vanilla speedrun timings.
4. Build logic predicates for square reward access and the board win rule. Collection requirements that can end the slot must have their needed AP items classified as progression, with sufficient distinct supply. Qualification metadata, including local vanilla sources, must participate in the reachability model. Declare square locations and their compensating filler budget before item creation and fill.
5. Fill with the board as the hard progression surface, honoring each square's prerequisites. Reserve line sweep membership and ensure its members carry no progression. Validate the completed placement and accessible sources. A locally reachable region does not prove a remotely placed item will be delivered without a dependency cycle.

Represent prerequisite action facts in generation logic through reachable event locations with address `None` and corresponding event items. These are logic facts; each square also has its real randomized AP reward location. A square location becomes reachable when its objective predicate is satisfied, and a line predicate requires all five objective facts in any one line. Counters are predicates over eligible facts, not a requirement to acquire every possible contributor. Restricted manual actions use explicit prerequisite proxies in generation and actual referee confirmation at runtime; disclose that action success cannot be proved by AP fill. Never infer objective achievement from having received the square's reward.

Every drawn square should be attainable independently in the full seed, and the selected win rule must be reachable without receiving rewards gated by that win. No bingo completion event may unlock an objective's own prerequisite. For the initial catalogue, omit irreversible quest conflicts and mutually exclusive actions unless a conflict model proves that the required combination can coexist. Blackout requires a simultaneous solution for all 25 objectives; checking them individually is insufficient.

Bound the sampling attempts and fail with diagnostic reasons when constraints cannot be satisfied. Do not select a new board after fill without rerunning logic and fill: it would change the progression classification and completion condition underneath the seed. Export selected objectives, parameters, eligibility exclusions, and prerequisite witnesses to the spoiler log.

## Integration with the current mod

Initial architecture inspection used the provided checkout at `a7c4f463`; it was 27 commits behind `origin/main`, with no commits ahead. On 2026-10-03, `codex/bingo-mode` was created directly from fetched `origin/main` at `6e95a7f0`, preserving the existing dirty client submodule. Progression surface and boss sweep integration were then inspected on that branch. Verify live state again before implementation.

The current feature registry provides generation, region, item, rule, and slot-data hooks. Existing `features/goal_locations.py` emits `goalLocations` and required items; the client's `goal.rs` combines location/flag, item, and rune requirements. `core.py` separately constructs AP's completion condition. A bingo board cannot be squeezed into `goalLocations`: that list expresses a conjunction, while a line goal is a disjunction of conjunctions and many squares are not AP location IDs.

Proposed implementation responsibilities:

- `features/bingo.py`: feature options, catalogue selection, square AP locations, compensating filler, board predicates, eligibility checks, line payout reservations, and slot-data contribution. Keep parsing and board balancing in pure helpers.
- `features/progression_surface.py`: a narrow board-surface provider shared by local and incoming progression placement, with capacity validation and no widening in bingo mode. Current `SweepSlot` nominations are not square rewards and must not leak into the board surface.
- Existing sweep generation: honor line reward reservations and publish an explicit bingo milestone trigger. Preserve ordinary sweep behaviour when bingo is off.
- A narrow explicit goal-kind branch in core and goal-location emission: choose normal or bingo completion coherently; preserve existing behaviour when off. Add a shared post-fill validation seam only if needed; the registry currently has no generic post-fill hook.
- `contract.py`: declare a versioned bingo payload and required client capability. Regenerate the Rust contract and its documentation through the existing workflow.
- `er-logic`: board schema validation, counters, event reduction, line/count/blackout evaluation, and persistence identity rules as pure code.
- `eldenring-archipelago`: game observations, AP receipt reconciliation, tracker presentation, storage, and Goal dispatch through the existing integration seams.

The proposed payload contains goal kind, schema and adapter versions, catalogue and board hashes, resolved 25-cell definitions and square AP IDs, typed predicates, win rule, counting policies, detection modes, progression surface IDs, and first-line payout member IDs. These are contract concepts, not preallocated wire keys or game IDs. Derive all game IDs and flags from pinned project inputs, with references to their provenance. Unknown required schema or predicate kinds cause a clear connection refusal, rather than falling back to a boss ending.

Keep the board independent of terminal-arena gating. A drawn square in a formerly terminal arena must use its documented prerequisites and cannot wait for bingo victory to open that arena. Required Great Runes, locks, and abilities remain access prerequisites only where the board's route actually needs them.

## Persistence and multiplayer

Persist state by seed, slot, board hash, schema version, and bound character identity. Store distinct contributor identities and event sequence information, not just counters. Reconnect replays must be idempotent. A new character or changed board must not inherit progress; a continued save for the same run should. Bind a fresh save before baseline capture and reject a preplayed character in the initial release. Host recovery tools must identify invalidated objectives rather than secretly crediting historical flags.

Per-slot boards work in an ordinary multiworld: received items from other games may help adapted collection squares, while boss and action credit belongs to the acting ER slot. Race fairness is not guaranteed across different multiworld supplies.

Later shared-team boards require explicit membership and the same board hash. Union distinct eligible contributor IDs across members for kill counters, so two members defeating the same named boss count once when uniqueness is required. For collections, define whether uniqueness is across the team or per character in the variant. Do not sum arbitrary client counters. A completed team board can complete participating ER slots under an explicit team policy; it does not finish unrelated games.

Competitive lockout needs an authenticated coordinator that serializes claims and stores authoritative ownership. Arrival order at that coordinator resolves competing claims; client wall clocks do not. Persist corrections and referee decisions with an audit log. AP storage alone is not an adjudicator, and automatic tracking is not an anti-cheat guarantee.

Use independently completable supplies for opposing teams. A losing team's withheld progression must not strand the winner. Competitive victory belongs to the match coordinator; keep AP delivery running after a match loss. Tournament timing, penalties, draw rules, and when to mark squares are a separately pinned ruleset, not assumptions borrowed from an older season.

## Delivery phases and acceptance

1. **Catalogue audit and board prototype.** Import the two verified exports, produce one coverage row per template and variant, inspect redistribution terms, and show a resolved board with rules. Full-catalogue referee play is experimental and only allows objectives compatible with the world.
2. **Automatic per-slot release.** Implement supported boss, dungeon, collection, and state objectives; square reward checks and board progression fill; first-line sweep reservations; goal integration; persistence; and the board UI. Ship only verified detectors. Publish supported templates and variants separately from source totals.
3. **Teams and referee workflow.** Add shared boards, explicit credit policies, referee corrections, and spectator synchronization.
4. **Combat challenges and races.** Add encounter telemetry incrementally, then coordinator-backed lockout with a reviewed race ruleset.

Required verification includes deterministic imports and boards; all 12 winning lines; count and blackout; duplicate normalization; source-restricted acquisitions; reconnect and failed-delivery recovery; synthetic flag writes; save identity; and malformed or unsupported payloads. Verify exactly 25 new square locations and matching pool growth, all local and incoming progression confined to squares, and actionable surface-capacity errors. Test sphere-zero unlock placement, objectives needing items rewarded by other squares, cross-game dependency cycles, first-line payout ordering before Goal, simultaneous lines, manual collection of reserved members, and no repeated checks after reconnect. World tests must cover base, DLC, mixed, small rolled region pools, natural progression, vanilla placement, and relevant feature combinations, yielding clean fills or actionable OptionErrors. Vanilla placement must either implement square reward semantics coherently or be explicitly rejected; do not pretend vanilla-only rewards supply a randomized square surface. Run placement sweeps for collection supply and dependency cycles, plus blackout conflict cases.

Client verification distinguishes pure logic tests, source inspection, Windows compilation, and live game observations. Live acceptance must include a local boss kill, a remote item delivery, sold/stored duplicates, a failed grant, reload, a flag written by reconciliation, and one objective in a gated arena. Referee mode must never show manual confirmation as automatically verified. With bingo off, existing generation, goal payloads, victory behaviour, and item counts must remain unchanged.

The prototype below begins the automatic subset. The full coverage ledger remains necessary before importing the community catalogue; all 300 expanded variants are not implemented. Mapping attainability and trustworthy observations remains the substantial engineering work.


## Implemented experimental slice — 2026-10-03

The `codex/bingo-mode` branches in the world and client implement a 25-square automatic boss board (`ap-boss-board-v1`), square progression rewards, a reserved first-line sweep, line/count/blackout goals, and an F6 board display. Start with `presets/bingo-short.yaml`; use a fresh character and this branch's client. This is an AP boss adaptation, not a claim that the 300 community variants are implemented or licensed for redistribution.

Objectives select the regions. The draw uses the eligible content pool, chooses 25 eligible boss encounters under `bingo_region_limit` (default six, counting prerequisite regions), and retains exactly their owners plus prerequisite closure. `num_regions` is ignored during bingo; named starting regions must have objectives on the board. Ordinary capital/DLC finale force-keeps are omitted. Board randomness is isolated from item fill.

The initial catalogue uses the generated base-game field/catacomb/cave/tunnel defeat-flag table, with legacy and major-rune/festival fights excluded. DLC-only currently fails clearly because this audited table supplies no eligible DLC encounters. Natural progression, vanilla placement, Mario mode, boss keys, and explicit ordinary goals are rejected. Oversubscribed progression rewards fail with the available capacity rather than spilling into native checks. Collection, restricted combat, quests, referee mode, teams, and lockout remain planned work.

Square reports and the first-line bonus are retried through the existing AP reporting queue and deduplicated by checked locations. Local persistent defeat flags reconstruct progress after reload. Server collection alone cannot earn a local victory. The board hash is schema identity metadata, not cryptographic authentication. Fresh-character use is required; live game acceptance and stronger per-board save binding remain outstanding.

The first-line reservation keeps all checks sharing a pickup flag together and excludes boss-defeat flags. The client reconstructs acquisition-flag debt from an earned line after reconnect, so acknowledged checks do not leave dead pickups behind. Goal waits for the reward reports and owed flag flush. Board defeat flags are checked against the resolved per-seed detection table, including Great Rune overrides.

Validation: native Windows optimized client build; 1,552 pure client and 128 DLL library tests; default and profile Clippy; 25/25 final bingo generations; 24/24 existing fill-regression generations. The full world suite was exercised in four batches; its integration failures were corrected and verified in targeted reruns (336 regression tests and 76 final bingo/sweep tests). Live game observations remain unverified.
