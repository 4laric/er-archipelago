# SPEC — the MSB spatial walk: what it is actually for

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
