# Random-Start Warp: status (data-driven; capture RESOLVED)

The forced entry warp is now DATA-DRIVEN -- `RegionFogGates.ApplyRandomStartEntry`
(`patch_baker_random_start_warp_v2_datadriven.py`) derives the destination at bake time from
`BonfireWarpParam`, keyed by the grace `eventflagId` the apworld emits as `startWarpGrace`. No
per-region capture / static table is needed (the old `RANDOM_START_DEST` table is gone).

Proven by mining `ap_grace_flags_*.txt`: `GetMapParts(row)` = `[areaNo, gridXNo, gridZNo, 0]` gives
`61/46/40/0` for Gravesite (= the old hardcoded `ApplyDlcEntry` constants) and `60/42/36` for The
First Step (eventflagId 76101, bonfireEntityId 1042361951). Map is therefore correct by construction.

## Remaining (NOT capture -- code/test)

1. VERIFY the dest entity in-game (one-time): the DLC warp used a player-warp POINT entity
   (`2046402020`), which differs from the grace's `bonfireEntityId`. If `WarpPlayer` to
   `bonfireEntityId` lands you at the grace, done. If it no-ops, the spawn-point entity is minable
   from each tile's MSB by the bonfire's position (witchy/SoulsFormats) -- but try bonfireEntityId
   first; warping to the bonfire asset usually works.
2. CLIENT latch: the runtime client must `SetEventFlag(RANDOM_START_FLAG = 76969, ON)` once on a
   fresh save while in the Chapel of Anticipation (mirror the dlc_only `dlcEntryWarpFlag` latch).
   Without it the baked event never fires. The apworld already emits `startRegion` + `startWarpGrace`.
3. gen + bake-test a `random_start_region: overworld` seed; confirm you wake up in the rolled region.

NOTE: even without the forced warp, the apworld-granted start graces already let the player
fast-travel into the rolled region manually -- the warp is the "wake up there" polish.
