# SPEC: Ruins sweep — extend dungeon-sweep to overworld ruins POIs

Status: **DLC ruins SHIP; overworld-ruins extension PARKED 2026-06-14 (Alaric).** The DLC
ruins that are already their own regions ship now (see below). Extending the sweep to
*overworld* ruins is parked after an enumeration pass showed the candidates don't exist as
discrete objects anywhere in the pipeline (see "Enumeration finding" below). The Route A /
trigger-hierarchy design is retained below as the plan-of-record IF this is ever revived,
but it is NOT being implemented — the cost is bespoke per-ruins hand-authoring with weak
triggers, for low-value POIs. (Alaric, 2026-06-13 / 2026-06-14)

Builds on SPEC-dungeon-sweep.md. Read that first — this only covers the ruins gap.

## Enumeration finding (2026-06-14) — why overworld ruins are parked

Work-item 0 (enumerate candidates from data, don't hand-wave) was run. Result: **overworld
ruins are not modeled as discrete units anywhere.** Evidence, all three pipeline sources:

- **apworld `locations.py`:** ruins checks are neither grouped nor named. Gatefront /
  Mistwood / Dragon-Burnt appear in *zero* check names or descriptions; checks live under
  big region keys (e.g. `"Limgrave"`) behind cryptic sub-area prefixes (`LG/(WR):` =
  Waypoint Ruins). Searching for "Ruins" finds only 7 checks game-wide.
- **Randomizer `diste/Base/annotations.txt`:** of 319 annotation Areas, the ONLY ruins with
  their own area are the DLC ones already shipping (`rauhruins`, `rauhruins_limited`,
  `cerulean_rhia`, `hinterland_dheo`, `scadualtus_miyr`). Zero base-game overworld ruins are
  areas.
- **`diste/Names/MapName.txt`:** every base-game ruins (Tombsward, Waypoint, Seaside,
  Dragon-Burnt, Caelem, Wyndham, Lux, Zamor, Yelough Anix, …) appears only as a *landmark
  sharing an open-world map tile* with unrelated loot — e.g.
  `m60_43_36_00 Limgrave - Agheel Lake, Dragon-Burnt Ruins`. No dedicated cellar map-id, no
  boss DefeatFlag, no grace grouped to the ruins.

Consequences:
- **Route A's map-block heuristic over-includes here:** a ruins check's key resolves to a
  whole open-world tile mixing ruins + field loot — i.e. the open-world sweep the parent
  spec explicitly forbids.
- **Trigger hierarchy bottoms out:** overworld ruins have ~no boss (tier 1 empty) and
  usually no dedicated grace (tier 2 thin), so most would fall to tier 3 (baked full-clear)
  or skip.
- **No candidate list to bucket** — the candidates aren't objects. Any extension means
  hand-authoring each ruins (explicit AP-id member list + hand-picked trigger flag), ruins
  by ruins.

Decision: not worth it. The clean win (DLC ruins as their own regions + remembrance
triggers) already ships. If revived, start from "Hand-curate a short list" (below), not from
a heuristic pass.

---

The rest of this doc is the retained (parked) design. Two orthogonal axes:
- **What fires the sweep (trigger):** the trigger hierarchy below. Most bossless POIs would
  use a native grace-discovery flag; full-clear is a baked last resort.
- **What gets swept (member scoping):** Route A (explicit member list). Parked per the
  finding above — kept as the design-of-record only.

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

So for **bossed** ruins, enabling a sweep is purely a **scoping** problem — the boss flag is
fine; we just need the member set to be "this ruins' checks" and not "the whole overworld
region". For **bossless** ruins it is *also* a **trigger** problem: there is no native flag
that says "this place is done." The trigger hierarchy below resolves that; Route A resolves
scoping for both.

## Trigger hierarchy — what fires the sweep (decided 2026-06-14)

The client only ever polls **one persistent event flag per sweep entry** and dumps the
members when it sets. So every POI needs exactly one such flag. Pick the cheapest one
available, in this order:

1. **Boss `DefeatFlag`** — bossed ruins. Native, persistent, free. Same as legacy/minidungeon
   sweeps; nothing new.
2. **POI grace-discovery flag** — bossless ruins that have a Site of Grace. Grace discovery
   sets a persistent native event flag, exactly the shape the poll loop wants. Semantics:
   "you found this place, take its loot." Zero baker authoring — we just read the grace's
   discovery flag and use it as the trigger. **This is expected to cover most bossless ruins.**
3. **Baked full-clear latch** — true last resort, ONLY for POIs with neither a boss nor a
   grace. The baker authors an EMEVD event that ANDs the death of every killable field enemy
   in the POI and **latches** a synthetic flag (set once, never cleared — trash respawns at
   grace, so the live "all dead" state is transient and useless; we must latch the instant the
   AND first fires). Risks, all on the baker side:
   - **Roster completeness is a footgun.** The latch fires only if every ANDed entity dies.
     One unkillable/despawning/never-spawns entity (scripted helpers, conditional summons,
     invisible trigger entities) → flag never sets → POI never grants. Filter the MSB enemy
     set to genuinely-killable field enemies, per POI, region-scoped (same map-block heuristic
     as Route A membership, applied to enemies instead of checks). Enumerate POST enemy-rando,
     since the baker runs after placement.
   - **EMEVD budget.** ANDing 20–40 death conditions per POI across many POIs — watch the
     condition-register budget; split events if needed.
   - **UX caveat.** Full-clear adds tedium to unlock 1–2 checks, which runs against the whole
     point of sweep (cutting tedium). Prefer not to reach tier 3 unless a POI genuinely has
     neither boss nor grace AND is worth it. A bossless+graceless POI with one check may just
     not be worth sweeping at all.

The client is **unchanged** across all three tiers — it polls a flag and sweeps members. The
tier only changes *which flag id* the baker writes as the trigger. Tier 1/2 are slot_data /
apconfig-only (no client, no EMEVD); tier 3 is the only one needing baker EMEVD authoring.

## Route A — `ruinsboss` tag + explicit member list (CHOSEN — lower blast radius)

Mirror the legacy rule but provide explicit member ids instead of a whole region. Route A
covers **scoping**; the **trigger** for each POI comes from the hierarchy above (boss flag /
grace flag / baked latch), not necessarily a boss — so the tag is named for the POI, not for
a boss.

1. **Tag the POI + its trigger.** Add a `ruinssweep: bool = False` field on `ERLocationData`
   and set it on the location that carries the POI's trigger flag — the boss drop for tier-1
   POIs, or a designated anchor location whose annotation lets us resolve the grace flag for
   tier-2. (Do NOT reuse the existing `*_boss` region tags like
   `fingerruins_boss`/`ancientruins_boss` — those drive the region-boss *gating* feature,
   SPEC-region-boss-gating.md, and group bosses by region, not by POI.) Add `ruinssweep` to
   the prominent-promotion list in `__post_init__`. The trigger flag itself is resolved per
   the hierarchy: boss `DefeatFlag`, else the POI grace-discovery flag, else the baked latch.
2. **Declare members per ruins.** A ruins' member checks are identifiable two ways:
   - **By map block:** location `key`s encode the MSB/map block (e.g.
     `604336,0:1043367020::` → block `1043367020`-family). Checks inside one ruins share
     a block-id prefix. A small helper can collect "every location whose key block
     matches the POI's block" — robust and avoids hand-listing. (The same block heuristic
     feeds the tier-3 enemy roster, if ever needed.)
   - **By explicit id list:** hand-list the AP location ids per ruins (most tedious, most
     precise). Use only where the map-block heuristic over/under-includes.
3. **Emit.** In the `dungeon_sweep == 2` path, add a `ruins_groups` pass:
   for each `ruinssweep` POI, resolve its trigger flag (hierarchy), compute members via the
   block heuristic (filtered to the POI's own region so a stray cross-region block can't
   leak), then `add_sweep`.
4. No client change — same flag-poll + `flagSentLocations` dedupe as every other sweep.

## Route B — give each ruins its own region (PARKED — alternative only)

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
- **Ruins with no boss:** handled by the trigger hierarchy — tier 2 (grace flag) for ruins
  with a Site of Grace, tier 3 (baked full-clear latch) only for boss-less AND grace-less POIs.
- **Ruins with neither boss nor grace nor enough checks to matter:** don't sweep it. Not every
  POI is worth a sweep entry.

## Work items (Route A + trigger hierarchy) — PARKED

**Status: not being done.** Item 0 was run and killed the heuristic approach (see
"Enumeration finding"). If revived, the only viable entry is the **hand-curate** path:
pick a short list of marquee overworld ruins worth the manual cost, and for each
hand-author (a) the explicit AP-location-id member set and (b) a trigger flag — boss
DefeatFlag if one exists, else a nearby grace-discovery flag, else accept it's not
sweepable. No heuristic; no auto-enumeration. Items 1–5 below assume that hand-built
input.

0. ~~Enumerate candidates from data and bucket by tier.~~ DONE 2026-06-14 — no enumerable
   candidates exist (overworld ruins aren't discrete objects). See "Enumeration finding".
1. apworld: add `ruinssweep` field + prominent promotion; tag each candidate POI's trigger
   location (boss drop for tier 1, grace anchor for tier 2).
2. apworld: trigger resolution — boss `DefeatFlag` (tier 1) / POI grace-discovery flag
   (tier 2). Tier 3 deferred (no graceless POIs confirmed worth it yet).
3. apworld: `ruins_groups` pass in the `dungeon_sweep == 2` branch (block heuristic,
   region-filtered) → `add_sweep`, using the resolved trigger flag. Regen required
   (slot_data only; no client, no EMEVD for tiers 1–2).
4. Test: a tier-1 ruins (kill boss) and a tier-2 ruins (discover grace), each with 2+
   unchecked members — verify burst send scoped to the POI (NOT the parent overworld
   region), reconnect, no resend.
5. (Only if a tier-3 POI turns out to be worth it) baker: author the full-clear latch EMEVD
   + killable-enemy roster filter; that's a separate, larger effort with its own test pass.
