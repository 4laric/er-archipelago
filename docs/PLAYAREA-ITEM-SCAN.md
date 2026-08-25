# PlayArea item scan — the runbook

Replace a 91%-accurate guess with the exact runtime answer, for the checks whose region we have
never confirmed.

This runs on **Alaric's Windows box**, because it needs the extracted MSB corpus and CI does not
have it. Everything below is mechanical: no step is investigative, and every command is exact.

The world-repo half of the region audit (issue #1025, PRs #1027/#1028/#1029) is what asks the
question; this file is how it gets answered.

---

## 1. Why — what this replaces

`greenfield/check_region_second_opinion.tsv` carries two opinions per check:

| column | what it is | how good it is |
|---|---|---|
| `verdict` (`external_regions`) | a public wiki's placement for the vanilla item | silent on 209 of 305 rows: a generic item name cannot name one pickup |
| `msb_vote_region` | **nearest region-attributed Site of Grace**, folded into the overworld frame (`tools/msb_region_vote.py`) | **91.4%** on a 2607-check control set — one row in ten is wrong |

Both are nearest-neighbour derivations, which is the same shape as the `tile_pr()` hop that gave
these 305 checks their regions in the first place. They **cannot fail** (CONTRIBUTING rule 1), so
they rank the work; they do not settle it.

The instrument that settles it already exists and is already calibrated against an in-game
measurement: the **point-in-volume test against `Region/PlayArea`**, which reads
`<PlayRegionID>` — *the exact id the client's kick-watch reads at runtime*. It is what
`tools/datamine_grace_ground.py` runs over the 421 warp graces. This runbook points the same
machinery at **item coordinates** instead.

Scope, in order of value:

* **260 checks** — the coord-bearing rows of the audit set. This is the decisive run.
* **3,966 item flags** — every flag with coordinates in `greenfield/item_grace_coords.tsv`
  (5,122 rows; the surplus is the `_00`/`_10` MSB version pair plus 442 genuinely double-placed
  flags). Optional, and worth doing once: it re-grounds every check, not only the unconfirmed
  ones, and it is the only way to measure the 8.6% error rate of the vote directly.

---

## 2. What runs — the machinery, by name

Everything needed is in `tools/datamine_grace_ground.py`. **Read it before you extend it.**

| name | what it does | reuse as-is? |
|---|---|---|
| `class Vol` | one PlayArea volume: `pr` (`PlayRegionID`), `kind`, centre, `yaw`, `a`/`b`/`h` | yes |
| `Vol.contains(x, y, z, yslack=8.0)` | the point-in-volume test. Box (rotates the delta by +yaw), Cylinder (planar radius), Sphere (3-D radius); ±8 m vertical slack | yes — **do not re-implement** |
| `_shape(el)` | reads `<Shape>`: Box → (Width, Depth, Height), Cylinder/Sphere → Radius, **Composite → the list of child region names** | yes |
| `_load_msb_playareas(d, area, tx, tz)` | every PlayArea volume in ONE witchy'd MSB dir, world-positioned as `tile*256 + local`; resolves Composite shapes to their named children | yes |
| `load_volumes()` | all `m60_*_00-msb-dcx` / `m61_*_00-msb-dcx` overworld volumes, deduped | yes |
| `load_interior_volumes(mtile)` | the same for ONE interior map (`mAA_BB`; world == local, no tile offset), cached | yes |
| `_nearest_face(vols, x, y, z)` | `(planar face-distance, vol)` for the nearest y-compatible volume — 0 when inside in plan | yes, for the seam case |
| `SEAM_SLACK = 8.0` | an interior point inside no volume but within 8 m of a face stands on that face's ground | yes |
| `MEASURED_GROUND` | in-game kick-watch measurements the derivation must AGREE with | keep asserting against it |

🛑 **The overworld transform in `_load_msb_playareas` is `tile*256 + local` and it is only ever
handed fine-grid (`_00`) tiles.** Item coordinates are NOT all fine-grid: some rows are authored
on LOD1/LOD2 tiles, where the pitch is `256 << lod` plus a `(pitch-256)/2` centring term. Fold the
ITEM through `tools/overworld_fold.py::world_xz` before testing it against the volumes — that is
the single shared fold, and re-implementing it is issue #338 all over again.

🛑 **A check's label tile is not always the tile its MSB row lives on.** Three Bestial Sanctum
checks (`1051417000`, `1051417010`, `1051417030`) are labelled `m60_51_41` and their coordinates
are authored in `m60_51_43`. Drive the scan off `item_grace_coords.tsv`'s `map_id`, never off the
label. Those rows carry `vote_note=CROSS-TILE-MSB` today.

---

## 3. Where — the box and its inputs

1. Alaric's Windows checkout of `er-archipelago`.
2. `elden_ring_artifacts/` with, at minimum:
   * `map/` and/or `mapstudio/` — **witchy'd MSB directories** (`WitchyBND` the `.msb.dcx`
     first). `datamine_grace_ground.py` reads `map/`; `datamine_item_grace_coords.py` reads
     `map/`, `mapstudio/`, and the artifacts root.
   * `vanilla_er/vanilla_er/` (or `vanilla_params/`) — the param CSVs, for
     `ItemLotParam_map.csv`, `ItemLotParam_enemy.csv`, `BonfireWarpParam.csv`,
     `PlayRegionParam.csv`.
3. Python 3.11+. No third-party packages; no network.

Confirm the corpus is there before anything else — an empty scan that writes a table is the
failure mode this project has already paid for twice:

```
python tools/datamine_grace_ground.py
```

Expect `PlayArea volumes: <thousands> (m60+m61)` and `421 total, ~293+ with a derived ground`.
If it says `FATAL: no witchy'd m60/m61 MSBs`, stop: the corpus is not extracted.

---

## 4. The sequence

### Step 1 — recover the dropped coords rows

`item_grace_coords.tsv` is missing rows it should have. **8 checks in the audit set carry an MSB
`treasure`/`enemy` provenance in `greenfield/msb_flag_region.tsv` and have NO coordinates row:**

```
1042327100   treasure   m60_42_32   Weeping     Composite Bow                 (audit DISAGREE)
1035497990   enemy      m60_35_49   Liurnia     Somber Smithing Stone [2]
1035547980   enemy      m60_35_54   Mt. Gelmir  Somber Smithing Stone [4]
1042527990   enemy      m60_42_52   Altus       Golden Rune [9]
1043327990   enemy      m60_43_32   Weeping     Golden Rune [6]
1048547990   enemy      m60_48_54   Mountaintops  Rotten Battle Hammer        (audit DISAGREE)
1051357990   enemy      m60_51_35   Caelid      Golden Rune [9]
1051547980   enemy      m60_51_54   Mountaintops  Somber Smithing Stone [7]
```

A further **14** audit checks have only an `event` MSB provenance (`1033417400`, `1033417410`,
`1039437400`, `1042397500`, `1042397700`, `1044327400`, `1044327410`, `1044537300`, `1046367700`,
`1047567700`, `1049577700`, `1049577710`, `1049577720`, `1052557700`). Those are event-script
payouts, not placed objects: they may have no authored position at all, and that is a finding to
record, not a bug to chase. **Do not conclude "the coords tool dropped 22 rows" — establish which
class each is in before you touch anything** (a census column is not a population).

Re-run the coords tool with the enemy pass on, which is the half most likely to be the cause —
`--enemy` is off by default and the enemy-sourced flags above are exactly what it produces:

```
python tools/datamine_item_grace_coords.py --enemy --merge
```

`--merge` UNIONs with the committed tsv (maps scanned this run are refreshed, absent maps carried
forward) so a partial witchy export composes instead of clobbering. The tool refuses a
**degenerate** scan (params missing, zero maps, or far fewer rows than the committed file) unless
`--force` — **do not pass `--force` to make a red run green.**

Then re-check which of the 8 are still missing, and audit WHY for each survivor:

```
python - <<'PY'
import csv, sys
sys.path.insert(0, "tools")
import msb_region_vote as V
items, _ = V.load_coords(".")
for f in ("1042327100 1035497990 1035547980 1042527990 1043327990 "
          "1048547990 1051357990 1051547980").split():
    print(f, "OK" if f in items else "STILL MISSING", items.get(f, ""))
PY
```

Commit the regenerated `greenfield/item_grace_coords.tsv` with the row-count delta in the message.

### Step 2 — write the scan

A new `tools/datamine_item_play_regions.py` (or a `--items` mode on `datamine_grace_ground.py` —
either is fine; the machinery is the same). It must:

1. `load_volumes()` once. Assert the count is in the thousands; a small number means a partial
   witchy export and the scan is worthless.
2. For each item row in `item_grace_coords.tsv`:
   * overworld (`m60_`/`m61_`): fold with `overworld_fold.world_xz`, then test against the
     overworld volumes with `Vol.contains`. **Fold first, test second.**
   * interior: `load_interior_volumes(map_id)` and test in local coordinates.
   * inside no volume: `_nearest_face` within `SEAM_SLACK`, else the `PlayRegionParam` tile
     default, else `-`. Record WHICH of those four answered, in a `source` column, exactly as
     `grace_ground.tsv` does — the source column is what makes a row falsifiable.
3. Emit `greenfield/item_play_regions.tsv`, same shape as its sibling:
   `flag  map_id  play_region_ids  buckets  source`.
4. Carry a **floor**, like `MIN_DERIVED = 200` next door: refuse to emit a table that derives
   fewer rows than the committed one. A shrinking ground-truth table that writes anyway is how a
   gate goes blind.
5. Take no network, read no game install, and be deterministic.

### Step 3 — sanity-check it against something already known

Before believing a single item answer, run the scan over the **421 graces** and diff it against
`greenfield/grace_ground.tsv`. Those answers are already calibrated against two in-game kick
measurements (`76841` → `6840000`, 2026-07-15; `72102` → `6900000/6900010`, 2026-07-21). A scan
that cannot reproduce `grace_ground.tsv` is not ready to be trusted about items.

### Step 4 — map play_region → our regions and compare

`REGION_PLAY_IDS` in `greenfield/eldenring/region_play_ids.py` maps play ids (116 of them) onto
our 30 regions. Bucket is `PlayRegionParam.ID // 100`, the kick-watch id space.

```
python tools/msb_region_vote.py            # the heuristic, for the diff
```

Expect the exact answer to disagree with the vote on **roughly one row in ten**. Every
disagreement is a row where the worksheet's colour was wrong, and the interesting ones are:

* the **17 rows anchored on grace 73211 "Yelough Anix Tunnel"** — badged `SUSPECT-ANCHOR`,
  because 73211's own region came from a *tile-default* row rather than a volume. They flip
  Mountaintops checks to Consecrated Snowfield as one block. The PlayArea test settles all 17 at
  once, in either direction.
* the **two Weeping checks anchored on 76113 "Seaside Ruins"** (`1042347000`, `1042347030`) which
  the vote flips to Limgrave — the single most common control-set error family (13 occurrences).
* the **3 Bestial Sanctum `CROSS-TILE-MSB` rows**.

### Step 5 — flow the answers back into the audit

1. Commit `greenfield/item_play_regions.tsv`.
2. Teach `tools/msb_region_vote.py` to prefer it: where a flag has an exact answer, the vote
   becomes that answer and `vote_note` becomes **`PLAYAREA-CONFIRMED`** — the heuristic is
   *replaced*, not averaged with. Where there is no exact answer the nearest-grace vote stays,
   with its existing notes.
3. Re-run, in this order:
   ```
   python tools/audit_region_second_opinion.py --offline --markdown greenfield/CHECK-REGION-SECOND-OPINION.md
   python tools/build_region_second_opinion_page.py
   python tools/regen_all.py --check
   ```
4. Update the calibration sentence — `msb_region_vote.CALIBRATION`, which the tsv header and the
   worksheet page both quote verbatim — and re-measure it rather than editing the number:
   ```
   python tools/msb_region_vote.py --calibrate
   ```
5. The page's vote colouring then means something different and must SAY so: a
   `PLAYAREA-CONFIRMED` row is a ruling, and the header caveat must stop applying to it.

---

## 5. What this does not do

* It does not edit `data.py` and it does not change any check's region. A confirmed answer is a
  candidate for `region_overrides.tsv`, adjudicated through the worksheet, like every other row.
* It does not run in CI. `elden_ring_artifacts/` is not in the repo and will not be; the
  committed tsv is the artifact CI sees, and its freshness gate is a row count and a floor, not a
  re-derivation.
* It does not answer for the 14 event-payout checks, or for any check with no authored position.
  Those stay on the heuristic, and the heuristic keeps saying `NO-COORDS`. **Absence of a
  coordinate is not evidence about the region.**
