# SPEC -- Core Fill features that replace our cross-world pre-fill passes (#1459)

Status: **DRAFT.** 2026-09-07. Author: Fable (research + draft), Alaric (commission, #1459).
Scope: a design note naming the four gaps in core Archipelago Fill that our foreign pre-fill passes
work around, with the measurement behind each and the smallest core change that would close it.
The upstream issues and any PR are downstream of this note; nothing here changes Elden Ring code.

Measured against Archipelago **0.6.7** (`.ap-test`, upstream `debe4cf0`).

---

## 0. The finding that reorders the plan

#1459 leads with shape (a), "a documented post-pre-fill hook", as the cheapest upstream change.
**Core already has it.** `fill_hook` / `stage_fill_hook` is called from
`distribute_items_restrictive` (`Fill.py:517`) with the three classified pools and the shuffled
open-location list, after every world's `pre_fill` and `stage_pre_fill` (`Main.py:194`), and after
`distribute_early_items` (`Fill.py:503`). It is documented in `docs/world api.md:545` as the hook
for modifying placement "during" the regular fill, and it is in production use for exactly the
shape we need:

| World | What its `stage_fill_hook` does |
|---|---|
| A Link to the Past | trash-fills Ganon's Tower from `filleritempool`, removes from `fill_locations` |
| Pokémon Red/Blue | cross-slot placement |
| Sonic Adventure 2 Battle | cross-slot placement |
| Oracle of Seasons | reorders `progitempool` |

Core also has a test for the contract (`test/general/test_fill.py:628`,
`test_can_remove_locations_in_fill_hook`): a hook may place items and remove the placed items and
locations from the lists it was handed.

Consequences for #1459:

- **Both v0.6.0.2 fixes are consequences of the wrong hook, not of missing core features.**
  At `fill_hook` time every partner has finished its own pre-fill (#1457's hazard is gone by
  construction, no `players_still_prefilling` heuristic) and the early-items pass has already run
  (#1456's declared-early copies are already on sphere-1 locations, no per-name skip).
- **Shape (a) is not an upstream feature request.** It becomes a documentation PR: say in
  `world api.md` that `stage_pre_fill` runs in class-name order and is for a world's own
  locations, and that a world which must place onto foreign locations should do so in
  `stage_fill_hook`. Plus the migration on our side (section 4).
- The remaining upstream work is (b), (c), (d), each its own issue with its measurement.

What `fill_hook` does **not** give us, stated so nobody rediscovers it:

- It is per-algorithm. `flood` (`Fill.py:673`) never calls it. `balanced` is the default and the
  only algorithm our passes have ever run under, so this is a documentation line, not a blocker.
- Stage hooks still run in class-name order (`AutoWorld.call_stage`, `:219`). Between two worlds
  that both place onto foreign locations in `fill_hook`, the order is still alphabetical and
  still undocumented. Nobody else does that today; we would be the first, and we should say so
  in the doc PR rather than ask core to add an ordering mechanism nobody has asked for.
- A `fill_hook` placement must mutate the lists it is handed (`progitempool`, `fill_locations`)
  and must not touch `multiworld.itempool`; that list is dead after `Fill.py:500`. Our passes
  currently pop from `multiworld.itempool`; that is the mechanical change in section 4.

---

## 1. The four gaps, with their measurements

| # | Gap | What we built instead | Measurement that motivates it | Core shape |
|---|---|---|---|---|
| 1 | A curated progression surface below 100% | `progression_surface` confine (own items) + `confine_foreign_progression` item rules (partners' items), `progression_surface.py` | confine curve, section 1.1 | (b) graded location priority |
| 2 | A per-partner-game share of outgoing progression | `cross_game_progression: auto`, the "Elden Ring Progression Share -> game" pass, `place_released_locks` | #703 / #927, section 1.2 | (c) per-game balance in the progression fill |
| 3 | A useful-tier export that survives `remaining_fill` | `export_reservation.reserve_useful_exports` | #918, section 1.3 | (d) `remaining_fill` fairness |
| 4 | A safe moment to place onto foreign locations | `stage_pre_fill` + `players_still_prefilling` + declared-early skip | #1456, #1457, section 1.4 | (a) already exists: `stage_fill_hook`; document it |

### 1.1 Curated surface (gap 1)

`priority_locations` is the only lever core offers and it is binary: a PRIORITY location takes
any world's advancement first, one item per player per pass (`Fill.py:551`), and the retry passes
drop `one_item_per_player` and `allow_partial` until every priority location holds *something*
advancement-classified. There is no "prefer, do not require", and no way to say which advancement.

Measured with `tools/gf_export_profile.py`, 2 seeds a cell, 2xER + 2xHollow Knight, only the
yaml varying (the confine curve, 2026-08-10):

| confine | ER->HK items | useful% | foreign prog into ER | of that, on-surface |
|---|---|---|---|---|
| 100 | 332 | 0.0 | 82 | 100.0% |
| 95 | 376 | 0.0 | 132 | 58.3% |
| 90 | 444 | 5.2 | 201 | 35.8% |
| 75 | 551 | 23.2 | 309 | 16.8% |
| 50 | 686 | 38.3 | 445 | 7.4% |

The on-surface column decays as slot counts predict: below 100 the surface is ~170 checks in a
world of thousands, so an unconfined item lands on-surface at roughly the surface's share of open
slots. There is no setting of the current tools that gives "most progression on the starred
checks, never on a merchant slot, the rest scattered". We approximate it with a per-item
Bernoulli draw (`_confine_draw`) that decides *which items* are confined, because core gives us
no way to weight *where* they go.

### 1.2 Per-game share (gap 2)

Ordinary fill spreads a world's advancement in proportion to open locations. In the motivating
three-game seed (#927, spoiler `j6A5CHH7TFqu65X9NFdyiA`) Elden Ring had eleven fill-visible
progression items; the aggregate pass sent four abroad and general fill split them 2/2, leaving
seven at home. Earlier (#703): **0 Region Locks reached a Hollow Knight slot across four
configurations**, including a 2xER + 1xHK seed where 15 of 28 Locks travelled and every one went
to the other Elden Ring world, because our own surfaces have four times the room they need and
absorb everything. The intended shape is per source game *and* per destination game, N counted
in games not slots: 11 items at a three-game table go 4/4/3.

### 1.3 Useful-tier export (gap 3)

At the shipped `confine_foreign_progression: 100`, a Hollow Knight partner received **0 useful
items in 498 placements** across three seeds (weapons, armour, talismans all absent), while a
second Elden Ring slot in the same seeds received 43.1% useful. Per-class export rate measured
filler 26.4% vs useful 1.6%, a 16x suppression no option asked for. A live player reported it
before any gate did (boblerrr, "dont think ive seen any of those items being global").

**The mechanism in `export_reservation.py` needs re-verification before (d) is filed.** The
module says the useful tier drains "from the front of the location list" before any partner slot
is reached. But `distribute_items_restrictive` shuffles `fill_locations` at `Fill.py:498` and
the per-class buckets preserve that order, so at `remaining_fill` the partner's remaining
locations are uniformly mixed in, not at the back. `remaining_fill` (`Fill.py:257`) does pop
items from the end of `filleritempool + usefulitempool`, so useful genuinely goes first, and it
has no per-player balancing at all; but "first into a shuffled list" should still yield the
partner's proportional share. Candidate real causes, to be distinguished by the core-only
reproduction in section 3:

1. The partner's own progression saturates its locations during the progression fill (confine
   pushes it home), leaving few open partner slots, and the 498 filler placements come from a
   late swap/retry path rather than from the main scan.
2. `inaccessible_location_rules` (`Fill.py:395`) attaches `forbid_important_item_rule` to
   locations unreachable from the post-progression state, which refuses useful *and*
   advancement. If the partner's late-game locations count as unreachable at that moment, they
   can only take filler.
3. Partner-side item rules refusing foreign useful items.

The 0/498 number is solid; the explanation is not. The upstream issue for (d) must carry the
mechanism, not the symptom, or it will be closed as a world-side problem.

### 1.4 A safe moment (gap 4)

Two production failures from placing in `stage_pre_fill`:

- **#1457**: 2xER + Oracle of Seasons 20.1.13, seeds 1-4: `auto` failed 4/4, `never` failed
  2/4, in Oracle's `stage_pre_fill_dungeon_items` with "No more spots to place 8 items". Our
  hook sorts before `OracleOfSeasonsWorld` and locked ~48 of its ~280 open locations uniformly;
  its dungeons hold 11-15 and confine 5-8 each.
- **#1456**: an APQuest `Key` declared in `early_items` was locked on a deep Elden Ring check
  in 4/4 seeds with 262 sphere-1 locations open, because our reservation ran before
  `distribute_early_items` and the early pass can only place what is still in the pool.

Both are closed by moving to `stage_fill_hook` (section 0).

---

## 2. Proposed core shapes

### (a) Document `stage_fill_hook` as the foreign-placement hook

A documentation PR to `docs/world api.md`, no code:

- `pre_fill` / `stage_pre_fill`: for a world's **own** locations. Stage hooks run once per world
  class in class-name order (`AutoWorld.call_stage`); a world must not assume any other world's
  stage hook has or has not run.
- `fill_hook` / `stage_fill_hook`: runs after every pre-fill and after early items, before the
  priority and progression fills, `balanced` algorithm only. A world that needs to place onto
  another world's locations does it here, from the pools it is handed, and removes what it
  placed from those lists and from `fill_locations`. Skip filled, locked and EXCLUDED locations;
  respect `item_rule`; use `fill_restrictive` with a real state for advancement.
- Cite the existing test (`test_can_remove_locations_in_fill_hook`) as the contract.

Optionally one code line: a `logging.debug` of the stage order in `call_stage`, so a failing seed
log says who ran first. Low value; drop it if it draws review friction.

### (b) Graded location priority

Smallest shape that expresses the confine curve: a per-location integer weight,
`Location.priority_weight: int = 0`, consulted only in the progression fill.

- `LocationProgressType.PRIORITY` stays as it is (weight = mandatory). Weight is orthogonal to
  progress type; EXCLUDED still wins.
- In `distribute_items_restrictive`, before the progression `fill_restrictive`
  (`Fill.py:586`), stable-sort `defaultlocations` by descending weight with the existing shuffle
  as the tie-break. `fill_restrictive` already walks `locations` in order and takes the first
  reachable legal spot, so a sort is the entire mechanism; no new algorithm.
- A world sets weights in `create_regions` or `set_rules`; a yaml-facing option is the world's
  business, not core's.

What this does not do: it does not let a world say which *items* prefer the surface. "Only my
own Locks, not Boss Keys" stays a world-side split (we already do it via `is_restricted_progression`).
A per-item weight is a second issue if the first one lands.

Story for what counts as progression: the advancement flag, unchanged. A world that wants a
narrower predicate reorders `progitempool` in `stage_fill_hook`, which Oracle of Seasons
already does.

### (c) Per-game progression balance

Where: `distribute_items_restrictive`, after `fill_hook`, before the priority fill. A
multiworld-level setting (host.yaml `generator.progression_balance_per_game: bool`, default
off) or a per-world class attribute `balance_progression_across_games = True`.

Mechanism: for each source world with the flag, take its `progitempool` items that are not
local-only and not declared early, compute near-even quotas per destination *game* (remainders
to partner games first, deterministic under `multiworld.random`), and run one
`fill_restrictive(..., allow_partial=True, one_item_per_player=True)` per destination game
onto that game's open default locations. Leftovers rejoin `progitempool`. Cap at the
destination's open count with a warning, never a FillError, for the same reason our pass does
(Clique ships one location).

This is `place_released_locks` with the Elden Ring surface logic removed. It is the largest
change of the four and the one most likely to be rejected as policy ("AP fill is intentionally
asymmetric"). Lead with the 0-Locks-to-HK and the 2/2/7 measurements and ask for the opt-in.

### (d) `remaining_fill` fairness

Blocked on the mechanism (section 1.3). If the reproduction confirms the useful tier reaches a
partner below its open-slot share for a reason inside `remaining_fill`, the fix shape is: place
`usefulitempool` with `one_item_per_player`-style round-robin across destination players, then
filler. If the cause is `inaccessible_location_rules` or the progression-fill saturation, it is a
different issue (or a world-side fix) and (d) is withdrawn.

---

## 3. Core-only reproductions (before posting)

All in `test/general/test_fill.py` style, two `TestWorld`-derived classes, no Elden Ring.

**R-a, the ordering hazard.** `WorldA` (sorts first) has a `stage_pre_fill` that locks its own
advancement uniformly onto every empty, unlocked, non-excluded location in the multiworld.
`WorldB` (sorts later) has ten locations in one "dungeon" region and a `stage_pre_fill` that
must place eight `get_pre_fill_items()` there. Assert: generation raises FillError with A in
`stage_pre_fill`; passes when A's placement is moved to `stage_fill_hook`. This is the test that
goes with the (a) doc PR, and it doubles as the regression test for our own migration.

**R-d, the useful-tier share.** `WorldA` with a pool that is 40% useful and many locations;
`WorldB` with few locations and enough own advancement to fill most of them. Run
`distribute_items_restrictive` and count A's useful items on B's locations versus B's share of
open locations at the moment `remaining_fill` starts. Instrument the three candidate causes in
section 1.3 by toggling each: no partner advancement (rules out 1), all B locations reachable
(rules out 2), no item rules (rules out 3).

**R-b and R-c** need no reproduction; they are feature requests with the measurements attached.

---

## 4. Migration on our side (does not wait for upstream)

Move the whole foreign tail of `GreenfieldEldenRingWorld.stage_pre_fill` (`core.py:1714`) to
a new `stage_fill_hook`:

| Pass (in current order) | Today | After |
|---|---|---|
| `progression_surface.place_released_locks` (outgoing share) | pops from `multiworld.itempool`, `stage_pre_fill` | takes from `progitempool`, removes placed locations from `fill_locations` |
| `incoming_progression.reserve_incoming_progression` | same | same; **delete** the `_declared_early` skip (#1456): early copies are already placed |
| `preferred_placement.reserve_foreign_share` / `place_on_surface` (blessing fragments) | same | takes from the class pool the fragments sit in |
| `export_reservation.reserve_useful_exports` | same | takes from `usefulitempool` |
| `keep_out_of_shops.finalize_rules` + `reserve_forbidden_items` | last, in `stage_pre_fill` | **moves too.** `finalize_rules` (`keep_out_of_shops.py:306`) sizes capacity against the remaining grid and reads the owner's items from `multiworld.itempool` (`:335`); after the move it must read them from the three pools it is handed, since `multiworld.itempool` is dead inside `fill_hook` |

Delete `players_still_prefilling` (#1457) and the comment in `place_released_locks` explaining
why `stage_pre_fill` and not `pre_fill`; replace with two lines citing this note. The own-surface
confinement in `progression_surface.apply` (per-world `pre_fill`) is unaffected: it places our
own items onto our own locations, which is what `pre_fill` is for.

Verification, same table as #1457 so the numbers are comparable: 2xER + Oracle of Seasons
20.1.13, seeds 1-4, `auto` and `never`, expect 8/8 with no "still holds N pre-fill item(s)"
line; plus the #1456 APQuest early-Key seed, expect the Key in the start region; plus
`tools/gf_export_profile.py` at confine 100 to confirm the useful share is unchanged by the move.

Risk: `fill_restrictive` inside `fill_hook` sees `multiworld.state` after early items and after
every pre-fill, which is a *later* state than our passes see today. Reachability can only be
more permissive, so no placement that was legal before becomes illegal; the reverse can happen
and is fine.

---

## 5. Posting upstream

Read before posting: `docs/contributing.md`, `docs/world api.md`, #ap-world-dev. There is no
AI-contribution norm in the repo as of 2026-09-07; Aquaria's PR #6389 adds a voluntary "AI usage
disclosure" to its world docs and is the model. Anything we send that was drafted with assistance
carries the same disclosure in the PR body.

Order and dependencies:

1. **(a) doc PR** with R-a as its test. Small, self-contained, no policy. Post first; it also
   establishes the vocabulary the next three issues use.
2. **(c) issue** with #703/#927 numbers. Independent of (a).
3. **(b) issue** with the confine curve. Independent.
4. **(d) issue** only after R-d names the mechanism. If R-d points at
   `inaccessible_location_rules` or at progression-fill saturation, retitle accordingly.

Each links back to #1459.

---

## 6. Acceptance (restating #1459 against the finding)

- [x] This note, naming the four gaps with measurements and a core shape for each.
- [ ] R-a written and passing in a core checkout; (a) posted as a docs PR, not a feature issue.
- [ ] Our passes moved to `stage_fill_hook`; `players_still_prefilling` and the declared-early
      skip deleted; the #1457 and #1456 verification tables re-run. This is the one item that
      does not depend on upstream and should be its own PR here.
- [ ] Upstream issues for (b) and (c) posted with their measurements.
- [ ] R-d run and (d) posted or withdrawn on its result.

## 7. Open questions for Alaric

1. Do we keep `cross_game_progression: aggregate` through the migration, or is the move the
   moment to drop the legacy one-batch path? It is dead weight in `fill_hook` form.
2. Is (c) worth posting as an opt-in given the "AP fill is intentionally asymmetric" stance, or
   should it wait for (a) and (b) to land and the maintainers to have seen our name?
