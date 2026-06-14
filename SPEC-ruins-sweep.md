# SPEC: Ruins sweep — extend dungeon-sweep to overworld ruins POIs

Status: PARTIAL. The DLC ruins that are already their own regions ship now (see below);
the overworld-ruins route below is NOT started. (Alaric, 2026-06-13)

Builds on SPEC-dungeon-sweep.md. Read that first — this only covers the ruins gap.

## What already ships (2026-06-13)

Two DLC ruins were added to `legacy_groups` in `__init__.py` because they satisfy the
existing legacy rule with zero new machinery: each is its own region (or a small set of
its own regions) AND its deepest boss drops a **remembrance**, which the legacy loop uses
as the sweep trigger.

- `["Finger Ruins of Miyr", "Finger Ruins of Rhia", "Finger Ruins of Dheo"]` →
  trigger = Remembrance of the Mother of Fingers (Metyr). All three finger-ruins regions
  sweep on the Metyr kill.
- `["Ancient Ruins of Rauh", "Rauh Ruins Limited"]` →
  trigger = Remembrance of the Saint of the Bud (Romina).

Requires a regen (slot_data change only — no randomizer/client work), same as any
`dungeon_sweep` group edit. `dungeon_sweep` must be set to `all` for these to emit.

## The actual problem with OVERWORLD ruins

The sweep map is keyed by `parent_region.name`: the legacy/minidungeon code gathers
`regions_to_locs[region]` and dumps the whole region on the boss flag. That works for
catacombs/caves (each is its own region) and for the DLC ruins above. It does **not**
work for most overworld ruins, because they are **folded into the surrounding overworld
region** — their checks share a `parent_region` with the open-world loot around them.
Sweeping on the ruins boss would clear half the zone, which SPEC-dungeon-sweep.md
explicitly forbids ("Open-world regions: explicitly OUT").

So enabling a ruins sweep is a **scoping** problem, not a trigger problem. The boss flag
is fine; we just need the member set to be "this ruins' checks" and not "the whole
overworld region".

## Route A — `ruinsboss` tag + explicit member list (recommended, lower blast radius)

Mirror the legacy rule but provide explicit member ids instead of a whole region.

1. **Tag the trigger.** Add a `ruinsboss: bool = False` field on `ERLocationData` and set
   it on the ruins' boss drop location(s) in `locations.py`. (Do NOT reuse the existing
   `*_boss` region tags like `fingerruins_boss`/`ancientruins_boss` — those drive the
   region-boss *gating* feature, SPEC-region-boss-gating.md, and group bosses by region,
   not by POI.) Add `ruinsboss` to the prominent-promotion list in `__post_init__`.
2. **Declare members per ruins.** A ruins' member checks are identifiable two ways:
   - **By map block:** location `key`s encode the MSB/map block (e.g.
     `604336,0:1043367020::` → block `1043367020`-family). Checks inside one ruins share
     a block-id prefix. A small helper can collect "every location whose key block
     matches the boss's block" — robust and avoids hand-listing.
   - **By explicit id list:** hand-list the AP location ids per ruins (most tedious, most
     precise). Use only where the map-block heuristic over/under-includes.
3. **Emit.** In the `dungeon_sweep == 2` path, add a `ruins_groups` pass:
   for each `ruinsboss` trigger, compute members via the block heuristic (filtered to the
   trigger's own region so a stray cross-region block can't leak), then `add_sweep`.
4. No client change — same flag-poll + `flagSentLocations` dedupe as every other sweep.

## Route B — give each ruins its own region (cleaner long-term, more invasive)

Promote each ruins to its own `location_table` key (its own `parent_region`) in
`locations.py`, wire it into `region_order` and the entrance graph, then tag its boss with
a minidungeon-class tag so the EXISTING tag detector sweeps it for free. This is the
"correct" model but touches region wiring and entrance rules (and every seed's region
graph), so it's a bigger change and a bigger test surface. Prefer Route A unless a ruins
needs real logic separation anyway.

## Enumerating candidates (don't hand-wave the list)

Which overworld ruins actually have a single clear boss is an empirical question — answer
it from the data, not memory. Query `locations.py` for boss-class locations
(`boss`/`altboss`/`overworldboss`) whose name prefix is a ruins POI and whose
`parent_region` is a large overworld region (i.e. NOT already its own region). That set is
the Route-A worklist. Verify each has exactly one boss before tagging (multi-boss ruins
need the same mainboss-only rule as legacy dungeons).

## Edge cases (same spirit as the parent spec)

- **Boss already dead at adoption:** first poll tick sweeps retroactively. Fine.
- **Shared map block:** if a ruins' block heuristic pulls in an adjacent POI's checks,
  fall back to an explicit id list for that ruins.
- **Missable/quest checks inside a ruins:** included (un-missables them), per parent spec.
- **Ruins with no boss:** out of scope — sweep needs a trigger flag.

## Work items

1. apworld: add `ruinsboss` field + prominent promotion; tag overworld ruins bosses.
2. apworld: `ruins_groups` pass in the `dungeon_sweep == 2` branch (block heuristic,
   region-filtered) → `add_sweep`. Regen required (slot_data only).
3. Test: a ruins with 2+ unchecked members behind its boss — kill boss, verify burst send
   scoped to the ruins (NOT the parent overworld region), reconnect, no resend.
