# SPEC -- Vanilla Placement (`vanilla_placement`)

Status: **RULED + BUILT.** 2026-08-07. Fable ruled D1-D5 (S5); the feature ships as
`vanilla_placement: off|all`. Author: Opus (evidence), Alaric (commission).
Motivating case: Discord, "Kro", 2026-08-07 -- *"me and my friends are wanting to just do a basic
elden ring co-op deathlink run, we dont really want any randomization ... or at least KEY items, like
the dectus, golden seeds, etc being in normal locations."*

---

## 0. The distinction this spec exists to hold

There are **two independent axes** and the project currently has an option on only one of them.

| Axis | Question | Owner today |
|---|---|---|
| **TOPOLOGY** | which region gates which | `features/natural_progression.py` -- BUILT |
| **PLACEMENT** | which item sits on which location | **nothing** -- `item_shuffle` is frozen ON (`defaults.py`: `"item_shuffle": (1, None)`) |

`natural_progression`'s premise is *"vanilla's SHAPE, AP's variety"*: the gate items are **fully
shuffled**. Turning it on for Kro leaves his Dectus halves scattered across the multiworld -- the
opposite of the request on the axis he named. This spec adds the missing axis.

### 0.1 The two cannot be combined

`natural_progression.set_rules` carries a cycle-breaker that forbids each key from the checks of
every region it gates, precisely so fill cannot strand a key behind its own gate. Vanilla placement
removes fill's freedom to honour it, and `GATE_CLAUSES` self-gates immediately:

- `"Stormveil": [("Rusty Key",)]` -- Rusty Key's vanilla home is the Stormveil Rampart Tower.

**CORRECTED 2026-08-07 (Fable, against the data).** The draft also named Shadow Keep/Thorns and
Jagged Peak/Katana; both are misattributions -- Aspects of the Crucible: Thorns' vanilla home is
**Scadu Altus** and the Dragon-Hunter's Great Katana's is **Gravesite**. Only Stormveil self-gates
*directly*. The true picture is worse, not better: a reachability fixpoint over GATE_CLAUSES under
vanilla placement collapses to **4 of 32 regions**, because the Remembrance of the Grafted opens
Liurnia and drops from Godrick, inside the sealed Stormveil -- and nearly everything hangs off
Liurnia transitively. The ruling stands on stronger evidence than the draft cited.

A third instance was found later, by this spec's own acceptance test rather than by inspection:
`legacy_key_gates` gates Lamenter's Gaol on the **Gaol Upper Level Key**, whose vanilla home is a
chest inside that gaol. Every legacy dungeon key has that shape by construction. The option is
FROZEN ON in `defaults.py`, so the guard had to go in the feature.

**RULING (proposed): vanilla placement => NO AP region gating at all.** `num_regions` ignored,
`GATE_CLAUSES` unused, entrance rules all `True`. This is not a loss: **vanilla ER already gates
itself** and ships beatable. The AP lock layer exists to *replace* vanilla gating; when placement is
vanilla, replacing it is exactly the wrong move. Cross-producting the two modes is the
mode-multiplication `er-v01-one-sound-mode` forbids.

---

## 1. Mechanism

`item_ids.LOCATION_ITEM` is `{ap_id: vanilla item name}` and already exists -- it is what
`item_shuffle` builds the pool *from*, so **multiplicities match by construction**: pinning every
location to its own vanilla item is a permutation of a pool that already contains exactly those
items. No pool arithmetic, no count drift.

Measured on `main` @ `6a6f354`:

```
regions 30 - locations 4916 - with LOCATION_ITEM 4849 (98.6%)
distinct vanilla items 1750 - items on >1 location 361 (Rada Fruit x184, Golden Rune [1] x161, ...)
```

The **67 unpinnable locations** are gestures (`Roundtable Hold :: My Lord [f60805]`, ...) and
unnamed `check -` rows: they have no inventory good to pin. They take the existing Rune fallback
that `item_shuffle` already gives them. Documented behaviour, not a gap.

Placement is `place_locked_item` at `pre_fill`. Precedent: the `natural_progression` event locks,
which are placed in **`create_regions`** (~`core.py:1069`), not pre_fill as the draft said.

### 1.1 Region opening, with ZERO client work

`natural_progression` solved the "no lock items but features still ask `has('<R> Lock')`" problem by
placing `"<R> Lock"` as an **AP event** (`code=None` -> never in the pool, never sent to the client)
inside each region, reachable exactly when the region is. Vanilla placement reuses that verbatim,
with the entrance rule `lambda state: True`.

Client side, the mode emits the **existing** contract keys with empty values:
`areaLockFlags: []` (no kick geometry -> nothing to escort you out), `regionOpenFlags: {}`,
`naturalKeyTriggers: {}`. `tick_natural_key_triggers` early-returns on empty (`region.rs:167`), and
`tracker_tables` documents that a key absent from `regionOpenFlags` is "treated as unlocked -- the
same answer `""` would have produced".

=> **no new slot_data key, no shape change, no `CONTRACT_HASH` move, no client half, no version
bump.** (`contract.py:488`: adding a client-consumed *option* does not move the hash;
`OPTIONS_SUBKEYS` is not folded in.) To be **verified at build time** by computing `CONTRACT_HASH`
before and after -- a claim, not yet a fact.

### 1.2 Goal

`has_all(locks)` is vacuous with no locks minted, exactly as under `natural_progression`, so the
completion condition takes the same branch: **reach the goal region**, plus `great_runes_required`.
With every region reachable at spawn, the rune count is the only real gate -- see **D4**.

---

## 2. Scope -- and the soundness argument that splits it

**RULED (D1): `vanilla_placement: off | all`. The `keys` scope is NOT built.** S2.2 below is kept
because it is the reason, and the proposal will recur.

It is a Choice rather than a Toggle precisely so `keys` can be ADDED later if a vanilla logic graph
is ever built: adding a Choice value is compat-safe, shipping a dead one is not.

### 2.1 `all` -- pin every location to its own vanilla item

Plays as literal vanilla. Checks still fire, deathlink works, the tracker works.

**It is sound for a trivial reason worth stating explicitly:** every ER location holds an ER item,
so **no foreign item can land in ER and no ER item can leave**. ER becomes fully self-contained.
AP's logic model for ER is now a lie (it believes all 4916 locations are sphere-0), but the lie
touches nothing -- there is no foreign item whose reachability it could mis-promise.

Answers Kro's first two messages exactly. The multiworld is degenerate by design: nobody sends
anybody anything, which is what "we dont really want any randomization" means.

### 2.2 `keys` -- pin the gating set, shuffle the rest

Kro's third message, and the version anyone else would reuse.

**REJECTED (D1). NOT SOUND, and the reason is the interesting part of this spec.**
Pinning ER's own keys makes *ER's* progression vanilla-safe. But S0.1's ruling flattened ER's region
graph, so AP now believes every ER location is sphere-0 and will cheerfully place **another
player's** sphere-0-critical item behind Malenia. ER's logic being a lie stops being harmless the
moment a foreign item is subject to it. `ConfineForeignProgression` (default on) confines foreign
progression to the progression surface, but the surface is `MajorBoss` by default -- deep bosses,
not early ones.

**Proposed containment: `keys` FORCES `local_items` on** (`features/local_items.py`, `LocalItemOnly`
exists), barring foreign progression from ER entirely and keeping ER items in ER. The sphere-0 lie
then only governs ER's own filler, which is harmless because every ER item that gates anything is
pinned. Generation should **fail loudly** if the yaml sets `local_items: false` alongside
`vanilla_placement: keys` rather than silently producing a seed that can strand a partner.

**Fable added a second, decisive objection:** the containment leaks. `local_items.names_to_localize`
covers ITEM_CATALOG + progressives and **not the Rune sentinel**, so the Rune-fallback slots break
the pigeonhole and can still admit a foreign item. Plug that leak and `keys` becomes hermetic --
zero multiworld interaction -- at which point it delivers nothing `all` does not, while carrying an
unauditable hand list. Either way it loses to `all`.

And the pin list can never be argued complete: with the graph flat, AP is structurally blind to
vanilla's doors, so any gating item left off the list can self-strand when shuffled (the Discarded
Palace Key landing inside the chest it opens). Incompleteness here is unwinnable-seed-shaped, which
violates the headline quality gate by construction.

The alternative -- build a real vanilla logic graph for ER so AP can reason about vanilla doors -- is
a large, separate project the codebase has never had (it has always been region-lock based). Out of
scope.

### 2.3 The pinned key set (only meaningful for `keys`)

Under S0.1 there is no AP gating, so "key" means **an item vanilla itself uses to gate something**,
not an item `GATE_CLAUSES` uses. Draft set, for Fable to complete and rule on:

- **Route gates:** Dectus Medallion (Left/Right), Rold Medallion, Academy Glintstone Key, Haligtree
  Secret Medallion (Left/Right), Pureblood Knight's Medal, Rusty Key, Carian Inverted Statue,
  Discarded Palace Key, Imbued Sword Keys x3, Stonesword Keys, Cursemark of Death.
- **Count gates:** all Great Runes (Leyndell's wall wants 2; `great_runes_required` wants N).
- **DLC:** Messmer's Kindling, Storeroom Key, O Mother (a gesture -- **not an inventory item**, so
  unpinnable; see the 67).
- **Kro also named Golden Seeds.** They gate nothing; they are flask upgrades. **See D3.**

Completeness of this set is the entire correctness argument for `keys`, and vanilla ER has a long
tail of soft gates (NPC questlines, Varre's invasions, Ranni's chain). This is the weakest part of
the spec.

---

## 3. Delivery

- `greenfield/eldenring/features/vanilla_placement.py` -- option + `Feature` (a `pre_fill` hook has
  to be added to `registry.Feature`; the protocol currently exposes only `generate_early`,
  `create_items`, `create_regions`, `set_rules`, `slot_data`).
- `presets/vanilla-deathlink.yaml` -- the thing Kro actually gets.
- `progression_surface` must skip pinned items (nothing left to `fill_restrictive`).
- CHANGELOG line in the same commit (Rule 14). **No version bump** (never in a feature PR).

---

## 4. Acceptance tests (Rule 11 -- the motivating case IS the test)

1. **Kro's case:** a seed with `vanilla_placement: all` places every pinnable location's own vanilla
   item on it; assert `LOCATION_ITEM[ap_id] == placed_item.name` for all 4849, Rune for the 67.
2. **Self-gating regression:** `vanilla_placement` + `natural_progression` is rejected with an
   actionable `OptionError` naming Stormveil/Rusty Key -- never a `FillError`.
3. **Containment:** `keys` + `local_items: false` raises; `keys` alone yields zero foreign
   advancement items on ER locations.
4. **Contract stability:** `CONTRACT_HASH` byte-identical to `main`'s.
5. **No-seal:** slot_data emits empty `areaLockFlags` / `regionOpenFlags` / `naturalKeyTriggers`.
6. Option matrix + seed sweep (`gen_sweep.ps1`, `run_fill_regression.ps1`) -- clean gen or graceful
   rejection on every combination. Suite run **five times** (draw-dependent assertions).

---

## 5. DECISIONS -- RULED (Fable, 2026-08-07)

- **D1. RULED: ship `all` only.** `keys` is deferred indefinitely -- its pin list is unauditable and
  its containment leaks through the Rune sentinel (S2.2). Option is a Choice so `keys` can be added
  later without a compat break.
- **D2.** Under `all`, every item round-trips through the AP **receive** path -- which carries open
  defects (one bad foreign item drops the whole batch; the stall guard re-arms forever; the pot cap
  ate nine owed copies). A **passthrough** design (don't suppress the vanilla drop; AP records the
  check only) dodges all of them and is *more* faithfully vanilla -- but it needs a client-side
  suppress switch, which moves `CONTRACT_HASH`, forces the client half and version lockstep. Is the
  receive-path risk worth that cost for a group whose entire ask is "nothing should change"?
  **RULED: no passthrough.** Under `all` the world is HERMETIC by construction -- no foreign item
  is ever in the receive stream -- so F4 cannot fire at all. The remaining defects (pot cap, stall
  guard) are own-item defects every existing seed already carries; this mode adds zero new
  exposure and they get fixed on their own track. A suppress switch would be a second delivery
  mode for one system, and the zero-client-work property is this mode's best feature.
- **D3. RULED: moot** -- `all` pins Golden Seeds along with everything else, which is what Kro gets.
  For the record if `keys` ever returns: seeds SHUFFLE. "Pin the gates" is the only stable boundary;
  "pin what players feel is theirs" has no edge and dissolves into `all`, which already exists.
- **D4. RULED: force nothing, the premise was off.** `great_runes_required` is not alone --
  `goalLocations` still gates on beating the terminal boss (vanilla's own ending), with the rune
  count ANDed on top, and `goalRequiredItems` is empty because `kept_lock_names()` returns `[]`.
  The in-game Leyndell wall is vanilla's native rune gate and nothing clamps it with no seals
  emitted. `goal` stays live exactly as today.
- **D5. RULED: ignore, with a gen-log line and a docstring sentence. Never reject.** `NumRegions`
  DEFAULTS to 6 and AP cannot distinguish an explicit 6 from the default, so loud rejection would
  reject the plain default yaml -- the dumbest possible violation of "every combination generates
  cleanly". `natural_progression` is the shipped precedent for a documented ignore; the log line
  keeps it out of silent-no-op territory.


---

## 6. WHAT SHIPPED (2026-08-07)

`greenfield/eldenring/features/vanilla_placement.py` (option + `generate_early` guard + `apply`),
plus mode branches in `core.py` (`generate_early`, `kept_lock_names`, `create_items`,
`create_regions`, `set_rules`, `pre_fill`, `post_fill`, `_base_slot_data`), `features/area_locks.py`
(the born-softlocked fix), `features/graces.py`, `features/finale.py`, `features/legacy_key_gates.py`.
Tests in `tests/test_gf_vanilla_placement.py`. Preset `presets/vanilla-deathlink.yaml` via
`tools/dump_options_metadata.py`. CHANGELOG under v0.3.7. **No `pre_fill` hook was added to
`registry.Feature`** after all -- core calls `vanilla_placement.apply` directly, which is one seam
rather than a new protocol method for a single caller.

**VERIFIED:** `CONTRACT_HASH` is byte-identical to main (`d7d3a58e...`); no client change; no
version bump. Full AP suite green.

**Guards that the acceptance test found, not the design:** `legacy_key_gates` (above), the
progressive-flask substitution renaming a pinned Golden Seed to "Progressive Flask Upgrade", and
`regionOpenFlags` still being emitted for flags nothing can ever set.
