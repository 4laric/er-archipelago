# SPEC: Random Start — Roundtable as the Hub (Limgrave demoted to a locked region)

Status: DRAFT 2026-06-19. Supersedes the "First Step anchor" / "Limgrave logic-only lock" sketches
in [SPEC-random-starting-region.md]. Builds on the shipped random-start chain (roll + precollect +
BonfireWarpParam-derived WarpPlayer + Chapel latch) and [[er-region-lock-physical-enforcement]].

## One-liner

Make **Roundtable Hold** the always-open hub/logic-root/KICK-fallback instead of Limgrave. That frees
Limgrave to be a normal **hard-locked region** (own lock + areaLockFlags kick) like everywhere else,
so a random start genuinely begins in the rolled region and Limgrave is just another place you unlock.
You still SPAWN in the rolled region (Caelid); Roundtable is the safe home base you fast-travel back to.

## Why Roundtable is the right anchor

- It is an INTERIOR map (m11_10), not an overworld play-region, so region-lock / KICK enforcement
  never applies to it -> a KICK fallback that warps here can never loop (unlike First Step, which
  sits inside Limgrave's play-region 61000 and would re-kick once Limgrave is lockable).
- Already granted at load (grace 71190, emitted in startGraces).
- Already the services hub (Twin Maidens, Hewg, Enia/great-runes, goal cocoon, Roderika if relocated).
- Already `ALWAYS_OPEN_REGIONS = {"Menu", "Roundtable Hold"}` in region_spine.py and lock-less.

So most of the "make it the hub" work is already true; we mainly re-point Limgrave's privileges onto it.

## Spawn vs anchor (keep these separate)

- SPAWN = the rolled region's grace (Caelid), via the baked WarpPlayer already shipped+fixed
  (bonfireEntityId-1, confirmed in the ap_bake log). UNCHANGED.
- ANCHOR = Roundtable: the logic root the warp graph radiates from, the always-open services hub, and
  the KICK fallback. This is what moves off Limgrave.

## Changes (scoped to random_start_region; normal seeds unchanged)

### apworld

1. **New lock item `Limgrave Lock`** (items.py): a real region lock (progression, `lock=True`),
   created/injected the same way as `Caelid Lock` et al. Do NOT add `'Limgrave': 'Limgrave Lock'` to
   the static `grace_data.REGION_LOCK_ITEM` (that would lock Limgrave for EVERY region-lock seed).
   Instead, inject + wire it CONDITIONALLY in `__init__` only when random_start_region is on.

2. **Gate Limgrave behind it** (__init__ rules): add the Limgrave AP regions
   (Limgrave, Stormhill, and the Limgrave overworld dungeons) to the lock rules keyed on Limgrave Lock,
   exactly like other regions. Under random_start, Limgrave stops being the free sphere-1 region.

3. **Re-root the warp hub Limgrave -> Roundtable** (`_region_lock_warp_access`): the hub is currently
   hardcoded `limgrave = self.get_region("Limgrave")`; point it at `Roundtable Hold` (already
   ALWAYS_OPEN). Bootstrap edge `New Game -> Limgrave` (create_regions) becomes `New Game -> Roundtable
   Hold`, and Limgrave gets a normal `Warp To Limgrave` entrance gated on Limgrave Lock. Roundtable ->
   rolled-region warp is open via the precollected start lock.

4. **Precollect the rolled start lock** (already done) and ensure **Limgrave Lock is in the pool**
   (injected, not precollected) so Limgrave is unlocked like any region.

5. **Emit a Limgrave open flag** in region_lock_sd / regionOpenFlags (mint one in the grace-tail gap,
   e.g. 76993, same scheme as Godrick/Morne) so the baker can author the physical fog/kick. Add
   Limgrave's area_ids to the detection table (see DATA DEPENDENCY).

### baker

6. **KICK fallback -> Roundtable** (RegionFogGates): today the play-region KICK warps to First Step
   (`WARP_DEST_ENTITY 1042361950`, inside Limgrave). When Limgrave is in the locked set (its open flag
   present in regionOpenFlags), resolve the dest from BonfireWarpParam(eventflagId==71190) ->
   GetMapParts (m11_10) + bonfireEntityId-1 instead, so a kick lands in Roundtable. Self-scoping: if
   the Limgrave lock isn't present (normal seeds), keep First Step -> zero behaviour change. Falls back
   to First Step if the 71190 row isn't found. Use Convert.ToInt64 for eventflagId (uint unbox, see
   [[er-random-start-region]] cast bug).

### client

7. No spawn change (still warps to rolled region). The KICK flag path is unchanged.

## DATA DEPENDENCY (blocks HARD enforcement only)

`map_region_data.REGIONS` has NO Limgrave entry and Limgrave's area_id band is unconfirmed (the 61xxx
prefix guess was shown WRONG elsewhere; First Step is "definitely play-region 61000", Weeping=61002,
so Limgrave proper is ~61000-61001 but UNCONFIRMED). To HARD-lock Limgrave (areaLockFlags kick) we need
its area id(s) captured in-game (the client logs area id on entry; same workflow as REGIONLOCK-areaid-
capture.md). UNTIL captured: ship Limgrave as a LOGIC-ONLY lock (rules gate it; no areaLockFlags entry
-> no kick). The fill still treats Limgrave as a locked sphere (safe); you just aren't physically
walled out. Add the area_ids entry + open flag to flip it to hard once 61000/61001 is confirmed.

## Interactions / risks

- **region_count / Capital spine**: region_spine assumes step 1 = Limgrave, lock-less. Giving Limgrave
  a lock breaks that assumption. v1: FORBID random_start_region + region_count>0 (warn+skip), same as
  the existing seal-goal guards. (Long-term: teach the spine to treat Limgrave as a normal step.)
- **Roundtable reachability for the KICK**: kicks only happen once you're in a locked region, which
  requires hub access, so Roundtable is always reachable by then. WarpPlayer into m11_10 on a kick is
  mid-game (not cold-save) and Roundtable is a standard fast-travel interior -> should stream. VERIFY.
- **Great runes / goal**: Enia + cocoon live in Roundtable (already granted), so the goal path is
  hub-anchored regardless of which region you start in. Good.
- **Stormveil**: already locked (Stormveil Lock) + reachable via warp; unaffected by Limgrave's demotion.

## Build order

1. apworld: Limgrave Lock item + conditional gate + hub re-root + open flag (logic-only first).
2. baker: KICK fallback retarget (self-scoping on the Limgrave open flag).
3. gen-test (Alaric, Windows): each overworld start; assert solvable, Limgrave Lock in pool, hub =
   Roundtable, no orphaned Limgrave checks. Forbid region_count combo.
4. CAPTURE Limgrave area id (61000/61001) in-game -> add areaLockFlags entry -> flip to hard lock.
5. bake + playtest: start in Caelid, confirm Roundtable hub travel, get kicked from a locked region ->
   land in Roundtable (no loop), receive Limgrave Lock -> Limgrave opens.

## Effort

apworld re-root ~1 day (new item + conditional wiring + hub swap; the precollect + grace bundle already
exist). KICK retarget ~half day (self-contained, data-driven). Capture + hard-lock flip ~minor once the
area id is in hand. Cost is the gen-test matrix, not the code.

---

## ADDENDUM 2026-06-19 — most of this is already built; see HANDOFF-num-regions-random-start.md

Re-audit against HEAD (`02864706`) found Bucket A (Roundtable re-root, Limgrave Lock, areaLockFlags,
baker KICK retarget) and the num_regions/chain machinery already implemented. Under
`num_regions` + `num_regions_chain` + `num_regions_rune_source=pool`, the chain's **link 0 is already a
randomly-rolled overworld region** with its lock precollected — so the original Bucket B (spine surgery
to demote Limgrave) is unnecessary. The remaining work shrank to three small changes (emit
`startRegion`/`startWarpGrace`, run the existing warpflags patch, and point the chain spawn at link 0
instead of fixed Roundtable). Full corrected plan + the ⛔ `git restore` prerequisite (working-tree
`__init__.py` is currently truncated) are in **HANDOFF-num-regions-random-start.md**. Treat the
Changes/Build-order sections above as historical.
