# SPEC: Boss Attribution — every check belongs to exactly one boss

Status: DESIGN, not started. (Alaric, 2026-06-15)
Extends [SPEC-dungeon-sweep.md](SPEC-dungeon-sweep.md). Where dungeon sweep maps the checks
*inside a dungeon* to that dungeon's mainboss, boss attribution makes the mapping **total**:
every AP location in the seed is attributed to exactly one boss `DefeatFlag`, so the whole world
becomes "kill a boss, claim its territory." Same client mechanism as dungeon sweep — only the
generation of the `{bossDefeatFlag: [apLocId, ...]}` map changes (it grows to cover the overworld).

## Concept

A single attribution function `attribute(check) -> bossDefeatFlag` partitions ALL checks across
bosses. Defeating any boss releases every check attributed to it. Dungeons keep their exact
containment mapping; overworld checks fall to the nearest field boss in their region; anything left
over falls to the region's great-rune / remembrance capstone. No check is ever orphaned.

This reuses the existing runtime path entirely: the client already polls boss `DefeatFlag`s and
sweeps `flagSentLocations`. The attribution just produces a bigger, total `dungeon_sweeps`-shaped
map (rename to `boss_sweeps` to avoid implying dungeon-only). The apworld option grows one value.

## Why this is buildable today (existing inputs)

- **Per-check global coordinates already exist.** The bake dumps `ap_location_coords`
  (`type | key | tileX | tileZ | gx | gy | gz`) for every AP location via
  `EldenCoordinator.ToGlobalCoords`. `tileX/tileZ` encode the world-grid tile and the map layer,
  so underground (Siofra/Ainsel/Nokron) is already separated from the surface.
- **Per-check region already exists.** Each `SlotAnnotation` carries an `Area` (`GetArea()`), and
  `region_centroids.json` lists each region's centroid `(gx, gz)` and check count `n`.
- **Boss positions already computed.** The itemslots `DebugText` already prints "By Godrick the
  Grafted — 4.28 away," i.e. the bake resolves each boss entity's world position. The same
  resolution gives every candidate boss a `(gx, gy, gz)`.
- **Boss roster + flags exist** in `diste/Base/enemy.txt`, classed and each with a `DefeatFlag`:

  | Class           | Count | Role in attribution |
  |-----------------|------:|---------------------|
  | `Boss`          | 52    | Legacy-dungeon mainbosses + great-rune / remembrance capstones (Tier 1 & Tier 4) |
  | `MinorBoss`     | 79    | Minidungeon mainbosses (Tier 1 dungeon triggers) |
  | `Miniboss`      | 41    | Open-world named field bosses — Erdtree Avatar, Omenkiller, Magma Wyrm, Demi-Human Queen, Godskin Apostle, Tibia Mariner, Wormface… (Tier 2 pool) |
  | `DragonMiniboss`| 15    | Field dragons — Agheel, Lansseax, Smarag, Adula, Ekzykes… (Tier 2 pool) |
  | `Evergaol`      | 10    | Alecto, Bols, Onyx Lord, Adan, Godefroy, Ancient Hero of Zamor, Darriwil… (Tier 2 pool) |
  | `NightMiniboss` | 21    | Night's Cavalry, Deathbird, Death Rite Bird, Bell Bearing Hunter (Tier 2 — OPTIONAL, see Q1) |

## Candidate pool (decided)

Tier-2 eligible bosses = **`Miniboss` + `DragonMiniboss` + `Evergaol` + `NightMiniboss`** (87
instances in base `enemy.txt`). Evergaols are folded into the same nearest-boss pool rather than a
separate tier — a nearby evergaol simply competes on distance like any other field boss.

Night bosses are **included** (Alaric, 2026-06-15). Caveat: Night's Cavalry / Deathbird / Death Rite
Bird only spawn at night, so "kill it to sweep its area" is only reachable when the player can force
night. **Dependency:** pair this with an *always-available night boss* tweak (EMEVD/flag so the
night-spawn condition is satisfiable on demand, e.g. via a sleep/round-table rest or a permanent
flag) so a night boss never permanently strands its attributed checks. Until that ships, night-boss
attribution risks soft-locking those checks behind the day/night cycle — track as a blocker on the
`NightMiniboss` portion, not the whole feature.

## The four tiers (applied in order; first match wins)

1. **Dungeon containment (exact).** If the check's `Area` is a legacy dungeon or minidungeon,
   attribute to that area's mainboss `DefeatFlag` — the existing dungeon-sweep mapping, unchanged.
   (Legacy areas use their `Event` mainboss; minidungeons have a single `MinorBoss`.)
2. **Nearest field boss in the same region, within a distance cap.** For an overworld check, among
   Tier-2 pool bosses whose region == the check's region, attribute to the **nearest by world
   distance** `dist = hypot(gx_check - gx_boss, gz_check - gz_boss)`, **provided that distance is
   within `MAX_FIELD_DIST`** (decided: a cap is wanted — Liurnia is geographically huge, so a check
   in the far corner shouldn't get yanked onto a boss across the lake). If the nearest in-region
   boss is beyond the cap, the check falls through to Tier 4. Region equality is the guard that
   stops cross-cliff / cross-layer mis-assignment (Siofra checks can't grab a Caelid dragon
   overhead, because Siofra River is its own region). Tune `MAX_FIELD_DIST` against the dry-run
   (≈800 world-units catches ~98% of in-region checks; lower it to push more far-flung scraps to
   the capstone).
3. **(Folded into Tier 2.)** Evergaols are Tier-2 candidates, so "nearest evergaol" is automatic
   when an evergaol is the closest in-region boss. No separate pass.
4. **Region capstone fallback (guarantees totality).** If the check's region has no Tier-2 boss
   (small sub-areas, hub regions, underground pockets with no field boss), attribute to that
   region's great-rune / remembrance capstone boss from the table below.

Distances use 2-D `(gx, gz)`; height `gy` is ignored for ranking but the region guard already
encodes layer. No distance cap is needed because Tier 2 is region-bounded and Tier 4 catches the
remainder (a cap would only create orphans).

## Region → capstone table (Tier-4 fallback) — DRAFT, review on first bake

Best-effort, in the same spirit as dungeon sweep's "verify region coverage on first use." Keyed by
the overworld region (and folded sub-areas), valued by the capstone boss whose `DefeatFlag` catches
its leftovers.

| Region(s) | Capstone boss | Note |
|-----------|---------------|------|
| Limgrave, Stormhill, Coastal Cave, Church of Dragon Communion | Godrick the Grafted | Limgrave great rune |
| Weeping Peninsula | Leonine Misbegotten | no great rune; Castle Morne boss (or fold to Godrick) |
| Liurnia of The Lakes, Bellum Highway, Moonlight Altar | Rennala | Liurnia great rune |
| Caelid, Dragonbarrow, Greyoll's plateau | Starscourge Radahn | Caelid great rune |
| Altus Plateau | Morgott / Tree Sentinel duo | no own rune; route to capital |
| Mt. Gelmir | Rykard | Gelmir great rune |
| Capital Outskirts, Leyndell (Royal/Ashen) | Morgott, the Omen King | Leyndell great rune |
| Subterranean Shunning-Grounds | Mohg, Lord of Blood (the Omen) | under-capital |
| Mountaintops of the Giants, Flame Peak, Forbidden Lands | Fire Giant | remembrance |
| Consecrated Snowfield | Astel (Yelough) / Malenia | review |
| Miquella's Haligtree, Elphael | Malenia, Blade of Miquella | remembrance |
| Siofra River, Nokron Eternal City | Regal Ancestor Spirit / Mimic Tear | underground |
| Ainsel River, Lake of Rot | Astel, Naturalborn of the Void | remembrance |
| Deeproot Depths | Lichdragon Fortissax / Fia's Champions | review |
| Mohgwyn Palace | Mohg, Lord of Blood | remembrance |
| Roundtable Hold, Menu | (special — see edge cases) | hub, no boss |

DLC regions (Gravesite Plain, Scadu Altus, Belurat, Shadow Keep, Enir-Ilim, Stone Coffin…) extend
the same way: field-boss pool from the DLC `enemy.txt` entries, capstones = Messmer (Shadow Keep),
Bayle (dragon pit), Radahn Consort (Enir-Ilim), etc. Build the DLC half only when `enable_dlc`.

## Data flow (delta from dungeon sweep)

1. **Bake.** After computing `ApLocationFlags` and the existing dungeon-sweep area map, run the
   attribution pass:
   - Build the Tier-2 boss list `(DefeatFlag, region, gx, gz)` from `enemy.txt` classes
     {Miniboss, DragonMiniboss, Evergaol} using each boss entity's resolved world position and its
     region (derive the boss's region the same way checks get theirs — entity map/position →
     annotation area / centroid bucket).
   - For each AP location not already claimed by Tier 1: look up its region + `(gx, gz)` from the
     `ap_location_coords` data, find the nearest in-region Tier-2 boss (Tier 2), else the region's
     capstone (Tier 4).
   - Emit `boss_sweeps: { "<DefeatFlag>": [apLocId, …], … }` into `apconfig.json` next to
     `location_flags` (superset of today's `dungeon_sweeps`; keep the old key as an alias or fold).
2. **Client.** No new code beyond what dungeon sweep already needs — parse `boss_sweeps`, extend
   the 2 s flag-poll tick, reuse `flagSentLocations` dedupe and the items_handling=7 echo path.
3. **apworld.** The `dungeon_sweep` option grows a value (see below); slot_data passthrough flag
   tells the bake to emit the *total* map vs the dungeon-only map. Generation logic untouched
   (sweep only makes items arrive earlier than logic's conservative estimate — always safe; do NOT
   add `OR can_beat_boss` disjunctions).

## Option surface (apworld)

The existing `DungeonSweep(Choice)` already ships `none` / `minidungeons` / `all` (where `all` =
minidungeons + legacy dungeons + self-contained castle regions). Add one value on top:

```yaml
dungeon_sweep:
  none: 50          # current behavior
  minidungeons: 0   # catacombs/caves/tunnels/graves/gaols (existing)
  all: 0            # minidungeons + legacy dungeons + castle regions (existing Tier-1 full)
  bosses: 0         # TOTAL attribution: Tier 1 (= "all") + overworld Tier 2/4 (this spec)
# optional sub-toggle if Q1 wanted:
# boss_sweep_include_night: false   # add NightMiniboss to the Tier-2 pool
```

`bosses` is a strict superset of `all`: it keeps the exact dungeon containment and adds the
overworld attribution on top.

## Edge cases

- **Hub / no-boss regions (Roundtable Hold, Menu).** No sensible capstone. Options: (a) leave their
  checks un-attributed (never swept — they're shop/NPC checks the player visits anyway), or
  (b) attribute to the seed's first great rune (Godrick). Recommend (a): don't sweep the hub.
- **Roaming bosses** (Tibia Mariner moves, Night's Cavalry patrols). Their `enemy.txt` position is a
  spawn anchor; fine for nearest-by-anchor attribution even though they wander.
- **Multiple instances of one boss** (two Lansseax, several Erdtree Avatars). Each instance is a
  distinct entity with its own `DefeatFlag` and position — they compete independently; a check just
  takes whichever instance is nearest in-region. Good (kill *that* avatar, clear *that* corner).
- **Region with checks but its only field boss is itself a dungeon boss.** Tier 1 already claimed
  the dungeon's checks; the overworld remainder falls to Tier 4 capstone. Acceptable.
- **Boss already dead at option-adoption time.** First poll tick sweeps retroactively (same as
  dungeon sweep). Harmless.
- **Burst sends.** Total attribution means a great-rune kill can dump a *large* region's leftovers
  at once. Same AP-legal behavior as dungeon sweep, but bigger — call it out in the option text.
- **Underground verticality.** Handled by the region guard (separate regions per layer); no special
  `gy` logic needed.

## Resolved decisions (Alaric, 2026-06-15)

1. **NightMiniboss IN the pool** — included, with the always-available-night dependency above.
2. **Weeping / Altus keep their local remembrance-ish boss** — Weeping → Leonine Misbegotten,
   Altus → the Tree Sentinel duo (not folded into Godrick/Morgott).
3. **Tier-2 distance cap: yes** (`MAX_FIELD_DIST`, ≈800 units start) — Liurnia is huge, so far
   outliers go to the capstone rather than a distant field boss.
4. **One superset key `boss_sweeps`** in `apconfig.json`, with the `dungeon_sweep` option value
   deciding how much of it is populated (`all` = dungeons only; `bosses` = total).

## Dry-run results (2026-06-15, base game, 3202 located checks)

Prototype `boss_attribution_dryrun.py` partitions the bake's `ap_location_coords` dump. Tier split:

| Tier | Checks | Share |
|------|-------:|------:|
| 1 — legacy dungeons | 709 | 22.1% |
| 1 — minidungeons | 410 | 12.8% |
| 2 — field bosses | 1704 | 53.2% |
| 4 — region capstone | 379 | 11.8% |

Field-boss hauls (Tier 2): **median 19, mean 25, max 81** checks per boss instance; 69 of 71
positioned field bosses catch ≥1 check. Lumpiest are open-underground / sparse-region bosses that
own a whole layer (Dragonkin Soldier in Nokron = 81; Night's Cavalry in Ainsel = 77) and the big
overworld names (Tibia Mariner 65, Wormface 65, Adula 66). Heaviest Tier-1 dungeon bosses are the
legacy mainbosses (Morgott 143, Godrick 122, Malenia 104, Maliketh 95, Rykard 88, Rennala 86).
Capstone catch-alls: Mohg the Omen 106 (Shunning-Grounds), Fire Giant 48, Lichdragon Fortissax 41.

Caveats baked into these numbers (all improve in the real C# bake): boss positions are approximated
from their own drop-check coords or map-tile centre; "same region" uses nearest region centroid;
legacy mainboss picked as lowest-id `Boss` in the area's maps. A few rough edges to clean up in the
real implementation: `limgrave_murkwatercave` (Patches ambush) found no in-map boss (7 checks);
Roundtable Hold has no capstone (34 checks — should stay **un-swept**, it's the hub); Redmane needs
an explicit capstone→Radahn entry. See `boss-attribution-dryrun.csv` for the full 139-bucket table.

## Grace-sweep complement (layered, first-trigger-wins) — Alaric 2026-06-15

Boss attribution alone leaves sparse-region checks on a distant capstone. **Add a second trigger
layer keyed on Sites of Grace**, and let a check fire on **whichever of its triggers happens
first** — boss killed OR grace lit. This drops the strict 1-boss partition in favour of a
**many-to-many** map: an apLocId may appear under several flags, and the client (which already
dedupes via `flagSentLocations`) sends it the first time *any* of them sets.

Why it's almost free: a grace's "lit" state is an event flag (`BonfireWarpParam.eventflagId`, which
the bake's `EldenCoordinator` already reads with positions). So `boss_sweeps` just generalises to
`sweep_flags: { "<flag>": [apLocId, ...] }` where `<flag>` is a boss `DefeatFlag` **or** a grace
flag. No new client code — the poll tick already handles arbitrary flags.

Assignment: each check also gets its **nearest grace in the same region within `GRACE_CAP`**
(≈160 world-units in the dry-run). Modes (option value):

- `off` — boss layer only.
- `complement` — add a grace trigger **only** where the boss layer is weak: checks that are
  capstone-bound or whose nearest field boss is beyond a threshold. Targets exactly the sparse
  gap, keeps dense regions boss-driven.
- `full` — every check also gets its nearest-grace trigger (graces sweep the world as you light
  them; boss kills still short-circuit).

Measured value (dry-run, GRACE_CAP=160u): 306 of 422 graces catch ≥1 check; **median 7
checks/grace** (mean 9, max 140 at a hub grace). **85%** of all checks have a grace within cap, and
crucially **91% of capstone checks and 74% of far-from-boss (>300u) checks are grace-covered** — so
the complement layer rescues almost all the sparse-region leftovers the boss layer handles poorly.

### Tuned thresholds (from `tune_complement.py`)

Distance reality: nearest-grace distances are tight (P50 87u, **P90 179u**, P99 272u) while
field-boss distances are loose (P50 218u, P75 351u, P90 493u). Graces are the dense layer, bosses
the sparse one — which is why grace makes a good complement. Two knobs:

- **`GRACE_CAP` (grace association): 180u.** This is the P90 of nearest-grace distance — "as close
  as a grace usually is." Going to 240u erases nearly all leftovers but lets a grace sweep checks a
  long way off (looser than feels right for a Site of Grace).
- **`FIELD_GOOD` (boss-coverage radius): ~300u.** A Tier-2 check whose field boss is within ~300u
  is already well served; only checks *beyond* that (or capstone-bound) are "weak" and get a grace
  trigger added.

At `FIELD_GOOD=250–400, GRACE_CAP=180` complement adds a grace trigger to ~600–950 of the 2083
open-world checks (the genuinely far/capstone ones), rescuing ~87% of the weak set and leaving only
~90–150 checks (~5–7%) on their original distant/great-rune trigger — and those are *not* stranded,
they still send when the capstone falls. For contrast, **`full` mode adds ~1800 grace triggers**
(every open check) — it works but trivialises exploration, so `complement` is the right default.
Recommended defaults: **`complement`, `GRACE_CAP=180`, `FIELD_GOOD=300`.**

### Nearest-grace-per-check is worth emitting regardless (hint metadata)

Independent of sweeping: record **each check's closest Site of Grace (name + distance)** at bake
time and ship it as hint metadata. When a player hints a location in AP, "near the *Stormhill
Shack* Site of Grace, ~40m" is far more actionable than a raw location name. This is a pure add —
no gameplay change — and reuses the same grace coordinate table. The dry-run now emits the full
form with **names** in `check-nearest-grace.csv` (e.g. "Gateside Chamber", "Rampart Tower"), joined
via `diste/Names/BonfireWarpParam.txt` (the dump's grace key == BonfireWarpParam row id). 100% of
the 3202 checks resolve a named nearest grace. The real bake gets the same names straight from the
place-name FMG (the `BonfireNameId` lookup `EldenCoordinator.TestBonfireCoords` already does).

## Work items (when implemented)

1. apworld: add `dungeon_sweep: bosses` value (+ optional night sub-toggle) + slot_data passthrough.
2. Randomizer bake: attribution pass (Tier-2 boss roster build + nearest-in-region + Tier-4 table);
   emit `boss_sweeps` into `apconfig.json`. Reuse `EldenCoordinator` + `ap_location_coords`.
3. Build + review the region→capstone table against a real bake (dump an attribution report:
   per-boss check counts, and a list of any region with 0 field bosses).
4. Client: parse `boss_sweeps`; extend poll tick; reuse `flagSentLocations`. (Likely already done by
   dungeon sweep — verify the map key name.)
5. Test: kill a field boss (Agheel) with 2+ overworld checks nearby → burst send + own-item echo;
   kill a great rune with region leftovers → capstone sweep; reconnect → no resend; hub checks
   never swept.
6. Grace layer: generalise `boss_sweeps` → `sweep_flags` (boss DefeatFlags + grace eventflagIds in
   one map; a check may appear under several). Add the `grace_sweep: off|complement|full` option;
   `complement` only adds grace triggers for capstone-bound / far-from-boss checks. Light-a-grace
   test: lighting a grace with 2+ nearby unchecked locations sweeps them; a boss kill still
   short-circuits a check that also has a grace trigger.
7. Hint metadata (independent): emit per-check nearest-grace **name + distance** at bake (join
   `BonfireNameId` FMG) into apconfig/hint data, so AP location hints read "near <Grace>, ~Nm".
