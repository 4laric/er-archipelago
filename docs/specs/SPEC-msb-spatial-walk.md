# SPEC — the MSB spatial walk: what it is actually for

> ## 🛑 STATUS: CLOSED 2026-07-26 (Alaric). Do not reopen without reading §0.
>
> The walk was RUN, the cheap slices landed, and the remainder is measured unreachable. Check
> locations went **3192 → 3912 of 4856 (65.7% → 80.6%)** and stopped there for reasons that are not
> effort-shaped. §0 records where it stopped and what would justify restarting.

## 0. Where it ended, and what would reopen it

**Done and shipped:**
- `--enemy` was opt-in and had never been used: +61 enemy-source, +102 of 111 treasure, +36 others.
  202 checks, one flag.
- merchant positions folded in (`5afecc4`, `663111f`): **+518 checks**, one row per (check, merchant
  instance) — 378 of them on more than one map, max 7. The one-to-many model, populated.
- descriptors: bare checks **608 → 126**, raw-tile locales **43 → 2**.

**Measured DEAD — do not re-attempt without a new input:**
- **event-source checks: 20 of 517 resolve (3.9%).** The treasure/enemy part join does not reach
  them. The handoff predicted this slice was "most likely to collapse"; it collapsed.
- **the 944 with no position at all** are `400xxx` key-item flags, 6-digit common-event flags, the
  gestures and 40 unnamed-merchant shop rows. No lot placement, so NO spatial method reaches them —
  including check-to-check, which cannot compute a distance for a thing with no coordinates.
- **check-to-check k-NN** (Alaric's idea, and the machinery already exists in
  `build_nearest_grace._normalize`/`_dist`, `world = tile*256 + local`, 2000 m cap): of 558
  positioned graceless-tile checks, **541 already have a nearest grace**; the 17 that do not are
  >2000 m from the nearest anchored check as well. It would inherit the same reach for ~17 checks.
- tile anchoring: both routes dead (see `test_gf_tile_anchor_coverage`), and 🛑 the premise that a
  256 m tile has ONE region is FALSE — anchored tiles straddle regions MORE often (9%) than
  graceless ones (5%). A tile→region table is the wrong arity.

**What would reopen it:** a new INPUT, not more effort. Specifically (a) whatever actually positions
an event-source award, or (b) a spatial oracle independent of graces — which is the only thing that
can break the `test_gf_grace_straddle` circularity that blocks grace-first regioning. Check-to-check
is a candidate for (b) *as a referee*, not as coverage.

### 2026-07-27 — a candidate (a) arrived, and it is worth +59. Alaric's call, not built.

`gen_inputs.py` now globs the params dir (14 → 239 CSVs), which brought in **`GameAreaParam`** →
`greenfield/game_areas.tsv`: 216 boss arenas with `defeatBossFlagId` and a **position, without the
MSBs**. Event-source awards are explicitly *"BOSS drops (remembrances, great runes, boss rewards)"*
(`datamine_msb_item_regions` docstring), so an arena is a candidate anchor for exactly this slice.

Measured, not estimated:

| join | yield |
|---|---|
| check flag **is** a boss defeat flag | **0** — boss rewards carry their own acquisition flag |
| check is in a map that *has* an arena | 465 of 496 — **too loose to use**, a map holds several arenas |
| ⭐ the awarding **EMEVD block** also references a GameAreaParam defeat flag | **59 of 496 (12%)** |

Only the third is principled: the same event that awards the lot waits on that boss's defeat, so the
reward is *at* that boss. It would take the event-source slice from **20/517 (3.9%) → ~79 (15%)**,
and overall coverage 3912 → 3971 of 4875 (**80.6% → 81.4%**).

🛑 Two reasons this is a decision and not an obvious yes:
- **+59 checks.** A 3× improvement on a slice that is 4% of the corpus is still 1% overall.
- The position is the **ARENA, not the item's own spot** — derived, not measured. It must land in a
  distinguishable column (`via=boss_arena`), never mixed into the same column as an MSB-measured
  position. A "near X" descriptor is arguably improved by it; a distance computation is not.

The other 437 remain what §0 already says they are: awarded by script with no lot placement, and no
spatial method reaches them.

---

**Original spec below, written before the walk ran. §1 was right and is why the walk was cheap.**

**Status: teed up, not started. Written 2026-07-26 after measuring which questions it does and does
not answer.** Read §1 before starting it, because the obvious reason to do this walk is the wrong one.

---

## 1. 🛑 It does NOT unblock tile anchoring. Measured.

The tempting framing is "walk the MSBs, get each tile's region spatially, and the 87 graceless tiles
stop being nearest-neighboured." That is not where the blocker is.

**244 of the 303 live checks on graceless tiles (80.5%) ALREADY have a `nearest_grace.tsv` row**, and
that grace's `play_region` is read straight off `BonfireWarpParam` via `grace_region_map.tsv` — no
inference at all. A per-check metric nearest-grace, capped at 2000 m, is a strictly better oracle than
"whichever neighbouring 256 m tile happens to hold a grace". The data to region those checks without
any tile guess **is already committed**.

What stopped it is not data. `ea5ccd7` reverted grace-first regioning because it made the straddle
oracle **circular**: `test_gf_grace_straddle` validates a check's region by comparing it to its
nearest grace's region, so regioning BY that grace means the screen can never disagree and validates
nothing. Its own docstring also records that `nearest_grace` is itself a nearest-neighbour and the
GRACE can be the wrong one.

So the anchoring blocker is: **we have a good primary source and no INDEPENDENT validator.**

⭐ **That is the walk's real value for this question — not as the answer, as the referee.** MSB
spatial containment is derived from geometry, not from graces, so it can disagree with the grace join.
With an independent oracle in hand, grace-first regioning can be wired and *checked*.

Routes already measured DEAD, do not re-walk them (see `test_gf_tile_anchor_coverage`):
- more graces reaching the join — all 166 m60 graces already resolve, zero lost;
- `PlayRegionParam.gridXNo/gridZNo` — 86 cells, covers 12 of 87 tiles, and is a THIRD id space
  (tile (37,47) is grace play_region 62000, PlayRegionParam says 3202001);
- `PlayRegionParam.posX/Y/Z` — only 215 of 593 rows are non-zero and the range (-690..1899) is
  MAP-LOCAL, not world space. It cannot place a tile.

## 2. What the walk IS for: precise XYZ

`item_grace_coords.tsv` holds map-local XYZ for 3192 of 4856 live checks. `check_maps.tsv` now gives a
MAP for 1498 more, but a map is not a position. The walk closes the difference:

| slice | n | what it needs from the MSB |
|---|---|---|
| merchant-placed shop checks | 517 | `Part/Enemy` position for the merchant npc, per (row, merchant instance) — the ONE-TO-MANY case: 11 named merchants stand on several maps |
| `msb_flag_region` source=event | 500 | ⚠️ **MEASURE FIRST** — an event award may have no part at all. Do not promise these until the join is proven |
| source=treasure | 111 | `Event/Treasure` → `TreasurePartName` → `Part/Asset` → `<Position>` |
| source=enemy | 61 | `Part/Enemy` → `<Position>` |

`tools/datamine_item_grace_coords.py` already implements the treasure and enemy joins. **Find out why
the 111 + 61 have no row today before writing anything new** — they are the cheapest, most certain
slice and the pipeline for them exists.

## 3. Ground rules for whoever runs it

- **Windows / a real box.** `elden_ring_artifacts/mapstudio` is 2.2 GB, 1347 `*-msb-dcx` dirs. The
  agent sandbox is disk-capped and its bash calls are hard-capped at 45 s — a full walk cannot finish
  in one call and cannot be backgrounded (`&` dies with the call).
- **Chunk with a state file.** `tools/datamine_msb_gated_treasures.py --state` is the working pattern.
- **Copy OUT before reading, and verify.** Mount reads can truncate; check counts AND byte totals.
- **Schema, OBSERVED not guessed:** `<map>-msb-dcx/{Event,Part,Region,Route,Model}/` +
  `_witchy-msbe.xml`. `Event/Treasure/*.xml` → `ItemLotID` + `TreasurePartName` →
  `Part/Asset/<name>.xml` → `<Position>`. `_99` map variants exist for 32 maps and carry `Part/Asset`
  but ZERO `Treasure`.
- **Positions are MAP-LOCAL** — the frame `arena_graces` and `item_grace_coords` already use. Do not
  compare across maps without an explicit tile→world offset.
- **One row per (check, position).** A check on N maps gets N rows; never collapse to one.
- Emit as its own tracked tsv, Tier 2 (manual `--emit`, never in a `.ps1`), report-only by default,
  tally every skip, and FATAL on a collapsed join.

## 4. Definition of done

1. The 111 treasure + 61 enemy checks have XYZ, or a counted reason why not.
2. A MEASURED answer for how many of the 500 event-source checks resolve to a part.
3. Merchant XYZ per (row, merchant instance), joined to `merchant_shops.tsv`.
4. An independent tile→region oracle good enough to referee the grace join — at which point
   `tile_pr`'s guesses can be replaced by grace-first regioning with a real check behind it, and the
   445 checks currently barred by `d4fc247` can be re-examined.
