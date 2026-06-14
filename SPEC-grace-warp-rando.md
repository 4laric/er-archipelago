# SPEC: Grace warp randomization (fast-travel unlocks as AP items)

Status: FUTURE PROJECT, not started. (Alaric, 2026-06-11)

## Concept

Touching a site of grace = an AP location check. The ABILITY to fast-travel to a grace
= an AP item ("Grace: Church of Elleh"). Resting/respawning at a physically-touched
grace stays local and ungated; only the map-warp unlock travels through the multiworld.
Bonus: a "Grace: Gravesite Plain" progression item becomes a second logical entrance
into the DLC, breaking the single Mohg->cocoon chokepoint.

## Why this stack makes it cheap

- Every grace's warp unlock is a single event flag: BonfireWarpParam row ->
  `eventflagId` (the 7xxxx family). The fork's dead `opt["bonfire"]` debug block
  already demonstrates mass-setting them.
- Our client already READS flags per tick (PollLocationFlags) and WRITES them
  (er_ap::game::SetEventFlag). Both primitives are proven live.
- Grace checks are flag-only: no physical item container, so the STATIC RANDOMIZER IS
  COMPLETELY UNINVOLVED — no bake changes, no regulation changes. The apworld ships
  two slot_data maps and the client does the rest:
  - `"graceLocationFlags": { ap location id: grace flag }` — client merges into its
    locationFlags poll table (check fires when the player touches the grace).
  - `"graceItems": { ap item id: grace flag }` — on receive, client calls
    SetEventFlag(flag) instead of an item gib (same special-casing pattern as the
    99999 lock sentinel).
  - CE-style flag warping into the DLC map layer (m61) is community-proven: the warp
    works on flag state alone, no cocoon trigger needed.

## Two tiers — build Lite first

**Tier 1, "Lite" (no suppression):** graces unlock naturally as in vanilla AND grace
items from the pool unlock remote warps early. Touching any grace sends its check.
Zero risk: nothing vanilla breaks, no flag-clearing races. The multiworld gains ~40-80
flag-only checks and warp-unlock items that act as soft progression accelerants
(and the DLC side-door). Most of the value, tiny client diff.

**Tier 2, "Full" (warp-gated):** natural discovery no longer unlocks the warp — the
item is the only way. Requires SUPPRESSION: the client clears grace flags the player
has touched but not received (poll loop: flag set && item not received -> clear).
Hazards to resolve before building:
- Respawn anchoring: verify death-respawn uses the rest anchor, not the warp flag
  (expected, but test).
- Map "discovered grace" icons share the flag — clearing hides them; acceptable?
- Race: clearing the flag during the rest/menu UI; throttle to "not while menuing"
  or accept cosmetic flicker.
- Stranded states: player warps somewhere, dies, has no unlocked grace nearby —
  softlock-ish by design (roundtable warp always available? verify Roundtable's
  flag is excluded from gating).

## Item/location set: CURATED, not exhaustive

ER has 300+ graces; do not randomize them all.
- LOCATIONS (checks): liberal — any grace with a stable flag can be a check (they're
  free). Reuse the apworld's region tables to name them ("LG/(CE): Grace - Church of
  Elleh").
- ITEMS (warp unlocks): curated ~30-50, roughly one per region/subregion (like maps:
  one item per map fragment region). Avoid:
  - WORLD-STATE graces: Ashen Capital (post-Maliketh world swap), post-Radahn Caelid
    changes, Wailing Dunes, anything whose map layer doesn't exist in the default
    world state. Granting those flags early is undefined behavior — this directly
    addresses the "no early Ashen Capital" requirement: those graces simply aren't
    items; their regions stay gated by their normal logic.
  - Quest-state graces (Three Fingers, Mohgwyn via Varre quest is FINE as an item —
    that's the point).
- DLC entrance: "Grace: Gravesite Plain" classified progression; apworld entrance
  rule: Gravesite Plain reachable via (Mohg path) OR (grace item). Under region_lock,
  combine with Gravesite Lock as designed (lock AND (path OR grace)).

## Logic

- Each warp item adds an OR-entrance to its region: `region reachable if normal route
  OR has("Grace: X")`. Always a relaxation, never a constraint -> can't brick seeds.
- Tier 2 additionally REMOVES free traversal assumptions only if we ever model
  warp-required traversal (we don't today — apworld logic is walk-based). So even Full
  tier keeps logic sound without rewrites.
- Respect soft_logic expectations (don't let a Mountaintops grace item put Fire Giant
  in sphere 1 expectations — classify most warp items as useful, only the deliberate
  side-doors as progression).

## Client work items (shared by both tiers)

1. Parse graceLocationFlags -> merge into locationFlags after apconfig load (key
   collision impossible: distinct AP location ids).
2. Parse graceItems; in GiveNextItem, intercept (same place as the 99999 sentinel):
   if item id maps to a grace flag, SetEventFlag(flag, true), log, skip gib.
3. Tier 2 only: suppression loop + Roundtable exclusion + the hazard tests above.

## apworld work items

1. Grace location data per region — GROUNDWORK DONE (2026-06-12): see
   `elden_ring_artifacts/grace_flags.tsv` (all 422 graces incl. 93 DLC: rowId,
   warp-unlock flag, map tile, world position, PlaceName text id; harvested from the
   vanilla param dump at elden_ring_artifacts/vanilla_er). Positions allow geometric
   region matching during curation. Names resolve via PlaceName FMG textIds at
   implementation time. NB row 0 (flag 200) and similar oddballs need the curation
   filter. Map-piece side note: WorldMapPieceParam confirmed the DLC map reveal flags
   62080-62084 used by the client's kMapUnlockFlags.
2. Curated item list + classifications; entrance OR-rules; DLC side-door rule.
3. Options: `grace_rando: none / lite / full` (full hidden/experimental until Tier 2
   hazards are cleared); emit the two slot_data maps.

## Open questions

- Check density: 300 free checks would dwarf other location types and skew fill;
  probably cap location set to the same curated list as items (+ maybe legacy dungeon
  graces). Decide with playtest feel.
- Does warping into m61 pre-cocoon skip intro state that later cutscenes assume?
  Community CE experience says it's fine; verify Leda/NPC intro triggers still fire.
- Interaction with dungeon sweep: grace checks inside swept dungeons just sweep like
  everything else — no special handling.
