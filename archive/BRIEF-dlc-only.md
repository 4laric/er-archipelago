# BRIEF: DLC-only mode (Shadow of the Erdtree) — yaml-gated, Option A "transit base"

Repo: **apworld** `Archipelago/worlds/eldenring` (Python). Single-track and **independently
testable** — see "Why this is apworld-only" below. Design is fully specced in `SPEC-dlc-only.md`
(decisions locked); this brief is the buildable cut. Memory: [[er-dlc-only-spec]].

## Goal (one sentence)
Add a yaml setting `dlc_only` that makes the AP check pool **only the Land of Shadow (~1,171–1,207
DLC checks)** with base game kept for traversal only (no base checks) — the inverse of `enable_dlc`,
which *adds* DLC on top of base.

## Why this is apworld-only (so you can test it independently)
DLC-only changes only GENERATION (pool + logic). It forces `enable_dlc` on, and the bake already
loads/keeps DLC under `enable_dlc` (no DLC-strip), so **no randomizer or client change is needed to
gen-test it**. Flip the yaml, run `build.ps1 -Generate` (or a full bake), play. The contract bump
(below) is only a bookkeeping step for SHIPPING to a synced multiworld — not required to test alone.

---

## Task 1 — the yaml gate (`options.py`)

Add a `dlc_only` toggle (default OFF) so a single yaml line turns the mode on:

```python
class DLCOnly(Toggle):
    """Restrict the check pool to the Shadow of the Erdtree DLC only (base game kept for
    traversal, but holds no checks). Forces Enable DLC on. Inverse of enable_dlc."""
    display_name = "DLC Only"
```
Register it in the options dataclass next to `enable_dlc` (`options.py:419`) and `dlc_timing` (`:423`).

> SPEC note: a 3-way `{base, base_and_dlc, dlc_only}` enum would make the illegal `dlc_only &&
> !enable_dlc` state unrepresentable. We use a toggle instead because it's the simplest "one setting
> I flip to test" and we FORCE `enable_dlc` in Task 3 — but if you'd rather not have a forced-implied
> option, switch to the enum. Pick one; don't ship both.

## Task 2 — invert the pool to DLC-only (Option A) (`__init__.py`)

Option A keeps the region graph unchanged (base regions stay for transit; DLC regions already build
under `enable_dlc` at `create_regions` `__init__.py:205`/`:211`). **Only the location-pool filters
change** — that's the whole reason Option A is the low-risk first ship.

Two existing predicates gate DLC content; invert their sense when `dlc_only`:
- `__init__.py:2480` — `if data.dlc and not self.options.enable_dlc: continue` (availability).
- `__init__.py:2525` — `... and (not data.dlc or bool(self.options.enable_dlc))` (pool inclusion).

Cleanest: add one helper and use it in BOTH spots so the rule lives in one place, e.g.
```python
def _content_in_scope(self, data) -> bool:
    if self.options.dlc_only:
        return bool(data.dlc)      # DLC-only: keep ONLY dlc-flagged locations
    return (not data.dlc) or bool(self.options.enable_dlc)   # existing behavior
```
Then `:2480` becomes `if not self._content_in_scope(location.data): continue` and `:2525` uses
`self._content_in_scope(data)`. This keeps the **36 Roundtable DLC-flagged checks** (Enia
remembrance weapons + DLC boss armor) because they carry `dlc=True` even though they live in a base
region — matching the locked 1,207 target. (For "pure Land of Shadow" 1,171, additionally exclude
non-`region_order_dlc` regions; default is 1,207.)

Item pool follows the location pool automatically (items are created from unfilled locations,
`create_items` `:522`), so dropping base checks drops base items. Base progression/key items needed
only for Option-A transit stay as locked-vanilla via the existing region locks — verify gen doesn't
demand a base item that's no longer in the pool (see Test plan deadlock check).

## Task 3 — force enable_dlc, set the goal + Messmer spine (`__init__.py`)

- **Force `enable_dlc`** at the earliest world hook (`generate_early`, or top of `create_regions`):
  if `dlc_only` and not `enable_dlc`, set `self.options.enable_dlc.value = 1` and `warning(...)` so
  the rest of the DLC-gated code (regions, maps, Enir Ilim gate) lights up. dlc_only must never run
  with DLC off.
- **Goal = Promised Consort Radahn (default).** `ending_condition` final-boss + `enable_dlc` already
  completes on `EI/GD: Circlet of Light` (post-PCR) — see `__init__.py:1010`. Recommend the test
  yaml use that goal; optionally default `ending_condition` to it when `dlc_only` (don't hard-force —
  all-remembrances/all-bosses DLC goals are valid too, via the existing `Remembrance DLC` / `Boss
  Reward DLC` groups).
- **Messmer's Kindling shard gate = the progression spine.** The PCR route passes Enir Ilim, already
  gated at `__init__.py:955/957` (`messmer_kindle` ON → N shards; OFF → single Kindling). Recommend
  defaulting `messmer_kindle` ON under `dlc_only` so the ~1,200-check pool has a real gate. Orthogonal
  option, so it's a default nudge, not new logic.

---

## Independent test plan

Ready-to-paste yaml fragment (drop into `Archipelago/Players/EldenRing.yaml`, solo):
```yaml
  enable_dlc: true
  dlc_only: true
  ending_condition: 0        # PCR (final boss) goal
  messmer_kindle: true       # shard-gate Enir Ilim
  messmer_kindle_required: 5
  messmer_kindle_max: 10
  location_pool: all         # or 'lean'; see pruning note
  world_logic: region_lock
```

1. `build.ps1 -Generate` (gen only — fastest loop; no bake/Windows needed to validate the pool).
2. **Count check**: the generated locations should be ~**1,170–1,207** (1,171 pure + 36 Roundtable).
   A quick assert: count locations with `dlc=True` ∪ `region ∈ region_order_dlc`. Far off ⇒ filter
   bug.
3. **Completability / deadlock**: generation must succeed and be beatable to PCR. If fill fails with
   "unreachable", a base item the transit still needs got cut from the pool — keep it as locked
   vanilla. Watch the volcano_town loop too (orthogonal bake bug, TODO #7) if you bake.
4. **Base has no checks**: spot-check the spoiler — no base-region locations in the pool (only transit).
5. Toggle `dlc_only: false` ⇒ identical behavior to today (regression guard).

## Out of scope (follow-ups)
- **Option B "DLC start"** (root the graph at Gravesite, bypass base entirely): needs apworld
  re-rooting + bake DLC-start un-bypass + a starting kit. The "proper" version; ship A first.
- **Pruning to ~500** (SPEC §"Pruning"): a DLC-scoped `location_pool: lean` variant. Optional dial,
  not required for the mode to work.
- **Contract bump (only when SHIPPING, not for solo testing):** `dlc_only` rides in the slot_data
  `options` dict, so per the beta lockstep it's a contract change → bump apworld `versions`
  beta.3 → **beta.4** (and the client's `ER_CLIENT_CONTRACT_VERSION`) when you sync it to a real
  multiworld. It has **no runtime consumer** (forcing `enable_dlc` covers the bake's DLC-unstrip), so
  the bump is bookkeeping — which is exactly why solo gen-testing needs none. Treat the bump as a
  serialized change (run it alone, like `BRIEF-contract-map-reveal`) if/when you ship.
