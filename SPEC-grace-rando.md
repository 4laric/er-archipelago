# SPEC — Grace Rando

**Goal.** Stop giving a region's Sites of Grace away with its lock. Instead:

1. Receiving a region's lock item lights **one random grace** in that region (the warp-in point).
2. Every *other* grace in the region becomes an **individual AP item**, dropped as a check
   **strictly inside that same region**, found by exploring.
3. Grace items are a **count-neutral filler swap** (no pool growth → no FillError).
4. Granting a grace marks it **already touched** (no walk-up activation animation).
5. Grabbing a grace shows the **grace's place name in the native ticker** (FMG piece — the one open
   research item).

Opt-in via a new `grace_rando` option. Only meaningful under region gating (`world_logic < 3`).
Inverts the current behavior in [[er-region-fusion]] / TODO #13; reuses that plumbing.

---

## Current behavior (what we're replacing)

`__init__.py` ~L5061–5128 (the `region_graces` block, `world_logic < 3`): for each region in
`grace_data.REGION_GRACE_POINTS`, `_spread(points, graces_per_region)` picks the spatially-spread
graces and bundles **all of them** under the region's lock item
(`region_graces[lock] = [warp flags]`). Client sets every flag at once on lock receipt.

Client side (mapped, Dark-Souls-III-Archipelago-client/archipelago-client/):
- `Core.h:128` — `regionGraces`, `pendingGraceFlags`, `graceFlagsSetThisSession`.
- `ArchipelagoInterface.cpp` slot handler ~L133 — parses `regionGraces` from slot_data.
- `ArchipelagoInterface.cpp` items_received ~L325 — matches lock **by item name** → queues its flags.
- `Core.cpp:997` `FlushPendingGraceFlags()` — drains queue → `er_ap::game::SetEventFlag(flag,true)`.
- `er_gamehook_win.cpp:215` `SetEventFlag(uint32_t,bool)` — the flag-set primitive to reuse.

Key fact: region-lock items are **AP-only name tokens** (no in-game item id), recognized by name.
Grace items follow the identical model.

---

## Design

### A. apworld — items + pool + slot_data (`patch_apworld_grace_rando_*.py`)

**A1. Option.** Add `GraceRando` (Toggle, default off) in `options.py`; field on the options dataclass.
Gate everything below on `grace_rando AND world_logic < 3`.

**A2. Grace items.** One `ERItemData` per gracifiable grace flag, mirroring lock tokens:
`er_code=None, category=GOODS, classification=filler, inject=True`, new marker `grace=True` (add the
field to `ERItemData` like `lock`/`map`). AP id auto-assigns from the 69000 pool.
- **Name** = disambiguated place name, e.g. `"Grace: Smoldering Church (Caelid)"`. Place-name string
  resolution = the open item in §E; until then name as `"Grace: <Region> #<warpFlag>"` so the feature
  works headlessly and names get prettified later.
- Source set per region = `REGION_GRACE_POINTS[region]` **minus** the `_SKIP_GRACE_FLAGS`
  (boss/border, already defined ~L5088–5090) **minus** the 1 random freebie (§B).

**A3. Freebie (the random grace).** In the `region_graces` build, when `grace_rando` is on, replace
`_spread(points, graces_per_region)` with `[self.random.choice(eligible_flags)]` per region — exactly
one, random, never a boss/border flag. That single flag stays bundled on the lock (warp-in). Leave the
bundle-lock / Limgrave-start / DLC-map special cases (~L5110–5128) **unchanged**.

**A4. In-region placement, count-neutral.** For each region, candidate locations =
`location_tables[region]` entries that will hold **filler** (skip progression / priority / already
locked placements). Use `_LOC_REGION` (L71) / `location_tables` (already imported). Place
`min(len(region_grace_items), len(candidate_filler))` grace items via `place_locked_item` at those
locations (mirror the bell-bearing/map placements ~L2087–2255). create_items stays count-neutral
because each pre-filled location no longer draws a pool item (established pattern, see the demand-drop
comments ~L1477/L1508). Graces beyond available in-region filler are **dropped** (graces are pure
convenience — capping at available filler is acceptable and self-bounding; large regions like Liurnia
will simply not gracify every point under lean pools).

**A5. slot_data.** Emit `graceItems = { item_name: warp_flag }` for all placed grace items, alongside
`regionGraces` in `fill_slot_data`. (Map item-name → single flag; client keys by name like locks.)

### B. client — grant + touched (`patch_client_grace_items_*.py`)

- `Core.h`: add `std::unordered_map<std::string,uint32_t> graceItems;`
- `ArchipelagoInterface.cpp` slot handler (~L150, after `regionGraces`): parse `graceItems`.
- `ArchipelagoInterface.cpp` items_received (~after L333): on name match in `graceItems`,
  `pendingGraceFlags.push_back(flag)` (reuses the existing flush path — zero new flag plumbing).
- **Touched (§4).** Setting `warpUnlockFlag` already registers + lights the grace (the current bundle
  system makes graces selectable on the map without ever visiting → strong signal it counts as
  discovered). v1 sets only the warp flag and we **playtest** whether any kneel/discovery animation
  remains. If it does, also set the grace's activation companion flag (candidate: derived from the
  `grace_flags.tsv` `rowId` / BonfireWarpParam) — identify via [[er-keyitem-obtained-flags]] method
  (set→readback probe). Tracked as a fast-follow, not a v1 blocker.

### C. gen-test

New yamls under `gen-test/` (region_lock × grace_rando, lean + full pools) + wire into
`run_fill_regression.ps1`. Verify: generates with no FillError; `graceItems` present in slot_data;
each lock bundles exactly 1 grace; grace items land only at in-region locations; pool count unchanged.
Reuse the `ER_DUMP_FILL` / sphere-count diags ([[er-filldiag-tool]]).

---

## D. Phase 2 — redundant-grace prune (stretch)

"If a grace can leave the item list without hurting check access, that's a win." Graces don't gate
logic, so 'access' here = travel convenience to nearby checks. Reuse
`tools/build_location_remoteness.py` / `LOC_GRACE_DIST`: a grace whose nearby checks are all already
covered (within X m) by the freebie or another kept grace is a prune candidate → drop it from the
item set (frees its filler slot back to junk). Pure optimization; ship after v1 works.

## E. Open item — ticker place-name (the "fmg change")

`MapName.txt` is keyed by map-id, **not** by the grace's `placeNameTextId`; the grace's on-screen name
lives in the game's **PlaceName FMG**. Two candidate mechanisms:
- **(a) Name-in-AP-item (preferred, no runtime FMG):** resolve `placeNameTextId → string` offline from
  the PlaceName FMG, bake into `grace_data.py`, name the AP item with it → native ticker shows the AP
  item name automatically. No in-game FMG authoring; just needs the PlaceName FMG dump.
- **(b) Runtime native banner:** trigger ER's area-name reveal off `placeNameTextId` on receipt. The
  client's on-screen banner is currently a **log-only stub** (`GameHook.cpp:127 showBanner`), and the
  incoming on-screen banner was previously parked in favor of the native ticker
  ([[er-notify-banner-task-b]]) — so (b) is more RE.
- **Recommendation:** go (a). Decide the PlaceName FMG extraction path before building names; v1 ships
  with placeholder `Grace: <Region> #<flag>` names so nothing blocks.

---

## Build order

1. apworld patch (§A) → gen-test (§C) — backbone, no game build needed.
2. client patch (§B) → client rebuild → bake → playtest grant + touched.
3. Ticker names (§E, path a) once PlaceName FMG resolution is settled.
4. Phase-2 prune (§D).
