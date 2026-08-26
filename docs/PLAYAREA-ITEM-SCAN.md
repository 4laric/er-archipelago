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
   * the **witchy'd MSB directories** (`WitchyBND` the `.msb.dcx` first) — `m??_??_??_??-msb-dcx`
     dirs. WitchyBND does not promise a subdirectory, so **three layouts are accepted** and every
     tool searches them in the same order, stopping at the first that actually holds MSB dirs:

     1. `<artifacts-root>/map/`
     2. `<artifacts-root>/mapstudio/` (also `<artifacts-root>/map/mapstudio/`)
     3. `<artifacts-root>/` itself, when the `m*-msb-dcx` dirs sit directly in it

     A directory counts only if it DIRECTLY contains `m*-msb-dcx` children — an empty `map/` does
     not shadow a populated `mapstudio/`, and unrelated siblings (`_pilot`, `breakgeom`, `m00`…)
     never make a root look like an MSB dir. One implementation, `tools/artifacts_root.py`, shared
     by every tool below; if nothing is found the FATAL names every location it tried.
   * `vanilla_er/vanilla_er/` (or `vanilla_params/`) — the param CSVs, for
     `ItemLotParam_map.csv`, `ItemLotParam_enemy.csv`, `BonfireWarpParam.csv`,
     `PlayRegionParam.csv`.
3. Python 3.11+. No third-party packages; no network.

🛑 **The corpus does not have to live in the checkout.** Every tool below takes
`--path <artifacts-root>`, and it defaults to `elden_ring_artifacts/` beside the repo root — so a
corpus kept anywhere else is a flag, not an edit. `--artifacts` is kept as an alias of `--path` on
the three tools that shipped it first, so every command in this file works with either spelling.
There is deliberately no environment-variable fallback: an invisible input is how a scan reads a
stale corpus and writes a plausible table. One implementation, `tools/artifacts_root.py`, gated by
`test_gf_artifacts_path.py`.

Confirm the corpus is there before anything else — an empty scan that writes a table is the
failure mode this project has already paid for twice. **Pass `--path` here first**: if the check
passes with a flag the scan is then run without, the check was of a different corpus.

```
python tools/datamine_grace_ground.py --path <artifacts-root>      # default: elden_ring_artifacts/
```

Expect `PlayArea volumes: ~497 (m60+m61)` (measured on a comprehensive 1,346-dir export,
2026-08-26 -- PlayAreas exist at play-region boundaries, not on every tile) and
`421 total, ~293+ with a derived ground`.
If it says `FATAL: no witchy'd m60/m61 MSBs`, stop and read the paths it lists: it names every
layout it searched, so either the corpus is not extracted or `--path` is pointed above/below it.

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
python tools/datamine_item_grace_coords.py --enemy --merge --path <artifacts-root>
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

### Step 2 — run the scan

**THE TOOL NOW EXISTS — run it as written, do not re-derive it:** `tools/datamine_item_play_regions.py`
(PR against #1025, gated by `greenfield/eldenring/tests/test_gf_item_play_regions.py`, which
exercises the geometry on synthetic MSB fixtures because CI has no corpus).

```
python tools/datamine_item_play_regions.py --graces --path <artifacts-root>   # step 3 FIRST -- the calibration gate
python tools/datamine_item_play_regions.py --path <artifacts-root>           # report only: counts, and by-source split
python tools/datamine_item_play_regions.py --emit --path <artifacts-root>    # writes greenfield/item_play_regions.tsv
```

`--path` defaults to `elden_ring_artifacts/` beside the repo root and can be dropped when the
corpus is there. Other flags: `--out`, `--artifacts DIR` (the older spelling of `--path`, kept as
an alias), `--coords-repo DIR`,
`--ground PATH` (what `--graces` diffs against), and `--force`, which exists to say a shrink is
DELIBERATE — the help text says so, and passing it to make a red run green destroys the ground
truth the gate is made of.

It does exactly what this section specified:

1. `load_volumes()` once. Assert the count clears the measured floor (~497 on a full export;
   `VOL_FLOOR = 400`); far fewer means a partial witchy export and the scan is worthless -- and
   the `--graces` diff is the decisive partial-export catch either way.
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
   gate goes blind. On the FIRST run there is no committed table to ratchet against, so the floor
   is two-part — `max(committed derived count, MIN_DERIVED_ABS = 2000)`. Raise `MIN_DERIVED_ABS`
   to the measured count once the first real run has one; raise, never lower.
5. Take no network, read no game install, and be deterministic.

Three details the implementation settled that this section had left open:

* the seam step applies to the OVERWORLD too, not only interiors (the order above reads that way
  and it is the right order). `datamine_grace_ground` goes straight from "no volume" to the tile
  default for overworld graces, so `--graces` can legitimately report a *source* delta there. It
  therefore fails on a **bucket** mismatch only, and prints source deltas as findings. A bucket
  delta means the geometry moved; a source delta means this pipeline found ground the older one
  called a default.
* the tile default is looked up for the tile the FOLDED position lands on, not the tile the row
  was authored in — a LOD2 row's authored tile spans 16 fine tiles and only one of them is the
  ground the item stands on. 🛑 **That attribution ROUNDS, it does not floor** — the overworld
  tile's local coordinate frame is CENTRED on the tile, so tile `t` owns
  `[t*256 - 128, t*256 + 128)`. 222 of BonfireWarpParam's 450 overworld grace local axis values are
  negative, which a corner origin cannot produce. `floor` was wrong for 2053 of the 2768 overworld
  item placements, always by exactly one tile index, and it is what made this gate refuse on
  2026-08-26 (graces 76416/76420). It lives in `overworld_fold.fine_tile`, ONE implementation, and
  `datamine_grace_ground` calls the same function — the two derivations cannot drift again.
* the `source` vocabulary is `volume:NAME`, `interior-vol:NAME`, `seam:NAME@Nm`,
  `interior-seam:NAME@Nm`, `tile-default`, `interior-map`, `none`.

### Step 3 — sanity-check it against something already known

Before believing a single item answer, run the scan over the **421 graces** and diff it against
`greenfield/grace_ground.tsv` — `python tools/datamine_item_play_regions.py --graces`, which
exits non-zero on a bucket mismatch. Those answers are already calibrated against two in-game kick
measurements (`76841` → `6840000`, 2026-07-15; `72102` → `6900000/6900010`, 2026-07-21). A scan
that cannot reproduce `grace_ground.tsv` is not ready to be trusted about items.

The half of this gate that is pure table lookup — the tile default, no volume involved — is also
asserted in CI over the whole grace population by `test_gf_grace_tile_frame.py`, out of
`gen_inputs.db`. So a `--graces` refusal on the box is now evidence about the **corpus or the
volumes**, not about the transform; if it names rows whose committed source is `tile-default` or
`none`, CI was already red and the tsv is stale, not the export.

### Step 4 — map play_region → our regions and compare

`REGION_PLAY_IDS` in `greenfield/eldenring/region_play_ids.py` maps play ids (116 of them) onto
our 30 regions. Bucket is `PlayRegionParam.ID // 100`, the kick-watch id space.

```
python tools/msb_region_vote.py            # the heuristic, for the diff (committed tsvs only -- no corpus, no --path)
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
