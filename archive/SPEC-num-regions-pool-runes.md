# SPEC: `num_regions_rune_source` — great runes from the pool, not the regions

Status: DRAFT 2026-06-19. Owner: Alaric. Sub-option of `num_regions` (`SPEC-num-regions.md`).
Builds on the Roundtable-hub re-root (`SPEC-random-start-roundtable-hub.md`) and the random-start
chain shipped in `__init__.py`. This is a design doc; the implementation is already split across
three named patch tracks (see §10) — read those for the byte-level wiring.

## One-liner

Add `num_regions_rune_source: regions | pool` (default `regions`). In `pool` mode the great runes
that open Leyndell are **injected into the item pool as items** instead of being **kept as boss
regions**, which un-couples "how many regions" from "which great runes exist" — so the region roll
becomes uniform over all eight majors and tiny runs (one rolled middle region) become legal.

## 1. Problem — the rune floor biases the roll toward vanilla

Today's `num_regions` (`SPEC-num-regions.md`) keeps a random subset of the Capital SPINE, but the
roller is forced to keep enough great-rune BOSS regions in scope to satisfy Leyndell's gate. The
floor is

```
num_regions_floor = 2 + great_runes_required          # Limgrave hub + Leyndell capstone + rune bosses
```

That single floor is doing **two jobs at once**: it sets the content size AND it guarantees the rune
supply. The side effects:

- **The roll is biased toward great-rune regions.** With `great_runes_required = 2` (the Leyndell
  default), `compute_num_regions_scope` picks 2 rune-boss steps *first* from
  `{Stormveil/Godrick, Liurnia/Rennala, Caelid/Radahn, Mt. Gelmir/Rykard}`. So two of the rolled
  middles are always rune regions, and seeds look "vanilla" — e.g. Limgrave → Liurnia → Altus.
- **The endpoints are fixed.** Limgrave is always the force-kept sphere-1 hub (`SPINE[0]`), Leyndell
  is always the goal, and because the seal renders along the vanilla spine order the chain reads
  like a vanilla spine slice.
- **Small runs are impossible.** `effective = max(num_regions, 2 + great_runes_required)`, so the
  smallest legal Capital run is 4 majors (Limgrave + 2 rune bosses + Leyndell). A genuine sprint —
  spawn, grab two runes, walk into Leyndell, kill Morgott — cannot be expressed.

## 2. The enabling insight — Leyndell's gate is a PURE ITEM COUNT

The Leyndell access rule is, verbatim (`__init__.py` L2189 → `_has_enough_great_runes`, L2825-2830):

```python
self._add_entrance_rule("Leyndell, Royal Capital",
    lambda state: self._has_enough_great_runes(state, self.options.great_runes_required.value))

def _has_enough_great_runes(self, state, runes_required):
    return (state.count_from_list([
        "Godrick's Great Rune","Rykard's Great Rune","Radahn's Great Rune",
        "Morgott's Great Rune","Mohg's Great Rune","Malenia's Great Rune",
        "Great Rune of the Unborn"], self.player) >= runes_required)
```

This is **just a count over seven item names**. There is **no Divine Tower visit, no rune
restoration, no boss-defeat, no region dependency** in the rule. The seven runes are: Godrick's,
Rykard's, Radahn's, Morgott's, Mohg's, Malenia's, and the Great Rune of the Unborn (Rennala).

Therefore a great rune can be supplied as a **pool item** instead of a **boss drop** and the gate is
satisfied with **zero rule changes**. This is exactly symmetric with the existing
region-locks-as-items architecture: a region's *access* is already an item (its lock), so making a
region's *rune* an item too keeps everything in one uniform "progression is items in the pool" model.
The fill solver already understands "place N progression items so the goal is reachable" — we are
just adding the runes to that set instead of pinning them behind a sealed wall.

## 3. Splitting the floor's two jobs

`pool` mode breaks the conflated floor into its two independent pieces:

| Job | `regions` mode (today) | `pool` mode (new) |
|---|---|---|
| **Content size** | `2 + great_runes_required` (min 4) | **1 middle region** (just Roundtable hub + Leyndell are always kept) |
| **Rune supply** | rune-boss regions forced into scope | **deficit injected into the item pool** |

A content floor of **1** is explicitly the point — a legal one-region sprint: spawn at the hub, warp
to the single rolled region, collect the two injected runes there/along the way, walk into Leyndell,
kill Morgott. With the rune supply moved out, the region roll becomes **uniform over all eight
majors** (Limgrave is no longer force-kept), which removes the rune bias entirely.

## 4. The `pool`-mode algorithm

Implemented as `region_spine.compute_num_regions_scope_pool()` (a sibling of
`compute_num_regions_scope`, the `regions`-mode function, which is left untouched) plus a resolution
block in `__init__.py`'s `num_regions` branch.

### 4a. Content floor + uniform roll

```
NUM_REGIONS_POOL_STEPS = [1] + NUM_REGIONS_MIDDLE_STEPS    # Limgrave (1) + the seven middles = all 8 majors
max_total = len(NUM_REGIONS_POOL_STEPS)                    # 8
effective = clamp(num_regions, 1, max_total)              # NO rune floor; floor of 1 is legal
picked    = rng.sample(NUM_REGIONS_POOL_STEPS, effective) # uniform over all 8 majors, no forced SPINE[0]
```

`effective` is now the count of rolled **middle** majors (≥ 1), NOT counting the always-kept
Roundtable hub or Leyndell capstone. There is no rune floor and no Altus force — the runes ride the
pool and warp ignores adjacency, so a sealed Limgrave and/or a sealed Altus are both fine.

Always-kept content: `ALWAYS_OPEN_REGIONS` (Menu, Roundtable Hold) ∪ `GOAL_CAPSTONE_REGIONS`
(Leyndell / Morgott). Limgrave is **not** in the kept set unless it rolls. Sealing then proceeds via
the unchanged `_spine_*` machinery (sealed locks pulled from the pool, sealed-region checks
downgraded to locked-vanilla events, sealed names removed from the randomized pool).

### 4b. Deficit calculation (with dedup + Morgott exclusion)

The runes that need to be injected are exactly the ones whose boss did NOT happen to land in a kept
region:

```
deficit = great_runes_required − (rune-boss steps whose lock is in the kept set)
```

The step → great-rune-item map (`region_spine.NUM_REGIONS_STEP_GREAT_RUNE`) covers the four
base-spine pre-Leyndell rune bosses, and **deliberately omits Morgott's Great Rune**:

| SPINE step | Region (boss) | Great-rune item |
|---|---|---|
| 3 | Stormveil (Godrick) | `Godrick's Great Rune` |
| 4 | Liurnia / Raya Lucaria (Rennala) | `Great Rune of the Unborn` |
| 5 | Caelid (Radahn) | `Radahn's Great Rune` |
| 8 | Mt. Gelmir / Volcano Manor (Rykard) | `Rykard's Great Rune` |

A step counts as "kept" iff its lock is in `_kept_l` (the kept-locks set), tested via the
step → lock map. The injection candidates are the runes whose step is **sealed**, walked in sorted
step order; `deficit` of them are taken, with dedup so a rune is never injected twice. Rules:

- **Exclude Morgott's Great Rune.** It is the goal-side Leyndell mainboss drop and must stay where
  the goal logic expects it — never injected, never double-counted. (It is absent from the step map,
  so it cannot be selected.)
- **No duplicate of a reachable boss-drop rune.** Because candidates are drawn only from SEALED
  steps, an injected rune can never duplicate a rune still obtainable from a kept boss.
- **Mohg's / Malenia's are not injection sources** — they are DLC-adjacent / Haligtree runes outside
  the base pre-Leyndell spine and are not in the step map; they remain wherever their normal logic
  puts them.

If the candidate pool can't cover the deficit (e.g. `great_runes_required` exceeds the available
sealed base runes), a warning fires naming the shortfall — but see §7, `great_runes_required` is
capped at 4 (`MAX_PRE_LEYNDELL_RUNES`), so for the four base runes minus zero-or-more kept ones the
candidate pool always suffices in practice.

### 4c. Count-neutral injection

For each selected rune, flip `item_table[name].inject = True`. The existing `create_items`
demand-drop machinery (`injectable_mandatory_count` → drop one small Golden Rune / filler slot per
injectable, the same mechanism `num_regions` already relies on to fit region locks into a too-small
world) then frees exactly **one filler slot per injected rune**. The pool stays **count-neutral**
with no manual filler bookkeeping in the resolution block.

## 5. The Roundtable-hub un-defer

`pool` mode reaches its non-contiguous random set the same way a random start does — by **warp from
an always-open hub**. The Roundtable-hub re-root is already implemented in `__init__.py`:

```python
_hub = "Roundtable Hold" if self._random_start_region else "Limgrave"
```

It injects a `Limgrave Lock`, gives Limgrave a normal `Warp To Limgrave` entrance, and re-roots the
warp graph at Roundtable. **But it is currently DEFERRED for spine-seal goals** — the
`random_start_region` block prints `"...region-seal goal (capital/region_count/messmer/godrick) is
active; ignoring it for now."` whenever `_spine_active` is set.

`pool` mode **un-defers exactly this combination**. Because the deferral keys on
`_random_start_region` being truthy, the resolution block:

1. Records intent (`_num_regions_pool_reroot = True`) inside the `num_regions` branch.
2. **After** the unconditional `self._random_start_region = None` reset (which would otherwise
   clobber it), sets `self._random_start_region = "Roundtable Hold"` and flips
   `item_table["Limgrave Lock"].inject = True`.

`_region_lock_warp_access`, `create_regions`, and the start-grace block all treat
`_random_start_region` purely as a truthy re-root flag plus a `REGION_GRACE_POINTS` lookup that
harmlessly returns `[]` for `"Roundtable Hold"`. The standard `random_start_region` option block is
skipped because its YAML option is `0` on these seeds, so it never re-clobbers the flag.

Net effect: Roundtable becomes the spawn/warp hub, and Limgrave becomes a normal rollable/sealable
region reached (when kept) by `Warp To Limgrave` on its `Limgrave Lock`.

## 6. Restore-on-grant (client side)

An injected rune is a held rune with no defeated boss and no Divine Tower visit. The Leyndell logic
gate doesn't care (§2), but for the item to be **usable** in-game it must be **restored** when
received. The client auto-restores any received great rune so it is immediately active without a
Divine Tower trip. The flavour of holding an un-restored-looking rune without having killed its boss
is **accepted as fine** — this is a short, deliberately-gamey Capital sprint, not a lore run.

## 7. The sub-option

```python
class NumRegionsRuneSource(Choice):
    display_name = "Num Regions Rune Source"
    option_regions = 0      # default — UNCHANGED behaviour (rune floor in region selection)
    option_pool    = 1      # decouple — inject deficit runes into the pool, Roundtable hub
    default = 0
```

Field: `num_regions_rune_source: NumRegionsRuneSource` (after `num_regions: NumRegions`). Only
meaningful with `num_regions > 0` + `ending_condition: capital` + region-lock world logic — same
gate as `num_regions` itself.

## 8. Worked example — floor-1 pool run

`num_regions = 1`, `num_regions_rune_source = pool`, `great_runes_required = 2`. Suppose Altus rolls
as the single middle:

| Region | Role | Notes |
|---|---|---|
| Roundtable Hold | hub (always open) | spawn / services / Enia / goal cocoon; warp graph root |
| Altus | the one rolled middle | reached by `Warp To Altus` on Altus Lock; hosts the 2 injected runes |
| Leyndell | goal capstone (always kept) | opens once `count_from_list(runes) >= 2`; Morgott |

Resolution: `effective = 1`. No rune boss rolled (Altus step 7 holds no rune), so
`deficit = 2 − 0 = 2`. Inject 2 runes from the sealed base candidates in sorted step order →
`Godrick's Great Rune` (step 3) + `Great Rune of the Unborn` (step 4). Pool drops 2 filler slots to
stay count-neutral. Roundtable re-root armed; `Limgrave Lock` injected (Limgrave is sealed this seed,
so it never opens — fine, it didn't roll). Play: spawn at Roundtable → warp to Altus → collect the 2
runes there/in-logic → walk into Leyndell → kill Morgott.

Chain reads `Roundtable → Altus(+2 runes) → Leyndell → Morgott`.

## 9. Interactions / edge cases

- **`great_runes_required` must stay ≤ 4** (`MAX_PRE_LEYNDELL_RUNES`). Only four base pre-Leyndell
  great-rune bosses exist (Godrick / Rennala / Radahn / Rykard); Morgott's is goal-side and Mohg's /
  Malenia's are not injection sources. With required ≤ 4 the deficit is always coverable.
- **Other consumers of `_has_enough_great_runes`.** `great_runes_final_boss` (Erdtree, L2192) and
  `great_runes_mountaintops` (L2194) use the same pure-count rule. Injected runes count toward all of
  them automatically — usually moot for a Capital seed (those regions are sealed), but worth noting
  if a future variant keeps the Erdtree tail or Mountaintops in scope.
- **`num_regions_chain` interaction is UNTESTED.** Chain mode breadcrumbs locks into a 1..N ladder
  and pins Altus last as the great-rune-gated capstone tail (`SPEC-num-regions-chain.md` §5). Pool
  mode moves the runes off Altus into the pool and seals Limgrave/Altus freely, so the chain's
  "great runes collectable in the unlocked prefix" assumption changes. Combining the two is plausible
  (breadcrumb the injected runes along the chain) but **not yet wired or tested** — treat as a
  follow-up; for v1, use pool mode with chain OFF.
- **`region_access` is forced to warp** by the parent `num_regions` block — unchanged and required
  (a non-contiguous random subset has no zero-item geographic route).
- **DLC**: as with the rest of `num_regions`, DLC regions are sealed wholesale; the Capital goal
  ignores them. Mohg's / Malenia's DLC-adjacent runes are not injection sources.

## 10. Tracks (parallel)

This feature is split across three files; cross-reference all three.

- **Track A — apworld** — `patch_apworld_num_regions_pool_runes.py`. Adds the `NumRegionsRuneSource`
  Choice + field (`options.py`), `compute_num_regions_scope_pool()` + `NUM_REGIONS_POOL_STEPS` +
  `NUM_REGIONS_STEP_GREAT_RUNE` (`region_spine.py`), and the pool-mode resolution + deficit injection
  + Roundtable re-root blocks (`__init__.py`). CRLF-safe, idempotent, anchor-checked. WRITTEN.
- **Track B — client** — `patch_client_restore_great_runes.py`. Auto-restores received great runes so
  injected runes are usable without a Divine Tower visit (§6). Needs a `-Client` rebuild.
- **Track C — this spec** — `SPEC-num-regions-pool-runes.md`.

## 11. Gen-test + verification checklist

Apply Track A on Windows (`python ..\..\..\..\patch_apworld_num_regions_pool_runes.py` from the
eldenring apworld dir), rebuild the apworld, then:

1. **Gen-test, `regions` mode unchanged**: `num_regions=4`, `rune_source=regions` → identical scope /
   spoiler to pre-patch `num_regions` (the default path is byte-untouched).
2. **Gen-test, `pool` floor-1**: `num_regions=1`, `rune_source=pool`, `great_runes_required=2`,
   `ending_condition=capital`, region_lock. Assert: solvable; exactly 2 great runes injected into the
   pool; pool count-neutral (2 filler dropped); Roundtable is the hub; `Limgrave Lock` in the pool;
   Morgott's Great Rune NOT injected; Leyndell reachable; no orphaned sealed-region checks.
3. **Roll uniformity**: across several seeds confirm the single middle is drawn uniformly from all 8
   majors (Limgrave appears as a rollable/sealable middle, not a forced hub).
4. **Deficit edge**: `num_regions=3` where 1 rune boss happens to roll → deficit 1, one rune injected,
   one filler dropped; and a seed where 2 rune bosses roll → deficit 0, no injection.
5. **`great_runes_required` cap**: required=5 → rejected by `num_regions_floor` / `MAX_PRE_LEYNDELL_RUNES`.
6. **Bake + playtest** (after Track B): spawn at Roundtable, warp to the rolled region, receive the
   injected runes (confirm they restore and are usable), warp/walk into Leyndell, kill Morgott,
   complete. Confirm a kick from a sealed region lands in Roundtable (no loop), not Limgrave.
