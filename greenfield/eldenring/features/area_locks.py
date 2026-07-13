"""SPEC-PARITY Track B -- areaLockFlags: arm IN-GAME region locking (the num_regions marquee mode).

The client's region-lock enforcer (kick-watch) needs to know, per region, which physical
play_region ids belong to that region, so it can tell which region the player is standing in and
whether that region is still sealed. Without this the connect log reads "0 ranges" / "NO lock range
covers it" and area_locks=0 -- enforcement is silently OFF.

CLIENT CONTRACT (read-only shape, crates/eldenring-archipelago/src/region.rs):
  areaLockFlags = [[lo, hi, open_flag], ...]  -- inclusive 5-digit subregion (play_region) ranges;
  a range is LOCKED while its open_flag is off. parse_triples() (region.rs) reads exactly three
  i64s per row. kick_decision() (crates/er-logic/src/region_lock.rs) reduces a 7-digit overworld
  play_region id to its 5-digit subregion (pr >= 1_000_000 -> pr/100), then kicks if the current
  sub is inside ANY range whose open_flag is off. The open_flag is set on lock receipt by the SAME
  region.rs region_open_flags path core.py already feeds via regionOpenFlags -- so a region unlocks
  (stops kicking) exactly when its "<Region> Lock" is received. We emit ONE triple per play_region
  id belonging to a kept region (lo == hi), keyed to that region's REGION_OPEN_FLAGS value.

DERIVATION (matt-free): REGION_PLAY_IDS is GENERATED into eldenring/region_play_ids.py by
gen_data.py as the inverse of greenfield/region_groups.py (THE bucket->region spine, curated
against elden_ring_artifacts/REGION_ID_MAP.md -- BonfireWarpParam.bonfireSubCategoryId == the
runtime play_region_id). All 54 non-system buckets are covered; 11100 (Roundtable HUB) and 18000
(tutorial spawn) are excluded from geometry on purpose (region_groups.KICK_EXCLUDED_PLAY_IDS) --
gating either would eject the player from home/spawn. No matt/Bedrock apworld data is read.

Only KEPT regions get ranges: a sealed (non-kept) region is never created and has no Lock item, so
it never appears here -- consistent with core.py's regionOpenFlags (kept-only). A kept region is
locked until its "<Region> Lock" is received, exactly mirroring the hub->region access rule.
"""
from ..registry import Feature, register
from .. import contract
try:
    from ..region_spine import DLC_REGIONS
except Exception:  # pragma: no cover
    DLC_REGIONS = frozenset()

# DLC world-map reveal flags (Land of Shadow map pieces) -- mirrors the client's
# startgrants.rs MAP_REVEAL_FLAGS_DLC. Emitted per DLC-region Lock via lockRevealFlags so the DLC
# map is revealed when you UNLOCK a DLC region, not only at start (reveal_all_maps + enable_dlc).
_DLC_MAP_REVEAL_FLAGS = (62080, 62081, 62082, 62083, 62084)

try:
    from ..region_open_flags import REGION_OPEN_FLAGS
except Exception:  # not yet generated -> no open flags -> no ranges (regions stay unlocked)
    REGION_OPEN_FLAGS = {}

# Region -> physical play_region ids. GENERATED (eldenring/region_play_ids.py, emitted by
# gen_data.py as the inverse of greenfield/region_groups.py -- THE spine). The hand table that
# lived here drifted from PLAY2AP exactly as hand copies always do (it still carried
# 'Raya Lucaria Academy'/'Leyndell' keys from before those were regions, and had 6940/6950
# bucketed backwards); one source now.
try:
    from ..region_play_ids import REGION_PLAY_IDS
except Exception:  # not yet generated -> no geometry -> no ranges (regions stay unlocked)
    REGION_PLAY_IDS = {}


@register
class AreaLocks(Feature):
    name = "area_locks"

    def slot_data(self, world):
        """areaLockFlags IS emitted, and slot_data is what the client enforces from. (This
        docstring once claimed the opposite -- a FOLDED 2026-07-06 note said the client derives
        the ranges itself via a region.rs mirror. That described a client that never shipped:
        region.rs parses `areaLockFlags` as-is and derives nothing when slot_data speaks. The
        fold was reverted 2026-07-08 -- see UN-FOLD below -- but the paragraph survived, lying.)

        Division of labor as of 2026-07-12 (bedrock interop):
          * OUR seeds: this method ships the fully-resolved ranges; the client consumes them
            verbatim. slot_data always WINS.
          * FOREIGN apworlds that emit neither areaLockFlags nor regionOpenFlags: the client
            falls back to a GENERATED copy of REGION_PLAY_IDS + REGION_OPEN_FLAGS baked into
            er-logic (region_locks.rs, emitted by tools/gen_region_locks.py from these same
            tables, drift-gated in CI) keyed by which "<Region> Lock" item names the seed
            carries -- so region lock works with zero slot_data support. Hand-written client
            mirrors stay forbidden (test_gf_data.py); the generated one cannot drift.

        Either way this feature still FAILS GEN on a coverage gap: any KEPT region that resolved
        a front-door open flag but has no geometry entry would have its in-game kick-watch
        silently off, so that is a hard error rather than a quiet degrade."""
        missing = [
            r for r in world._kept()
            if REGION_OPEN_FLAGS.get(r) is not None and r not in REGION_PLAY_IDS
        ]
        if missing:
            raise contract.ContractError(
                "area_locks: kept region(s) resolved an open flag but have no REGION_PLAY_IDS "
                "geometry (kick-watch would be silently off): " + ", ".join(sorted(missing)))
        # UN-FOLD (2026-07-08 dead-drop fix): emit areaLockFlags for ALL regions, not just kept ones.
        # KEPT regions use their open flag (unlocks when the "<Region> Lock" is received via the
        # regionOpenFlags path). SEALED (non-kept) regions ALSO get a range keyed to their open flag --
        # which is NEVER received (no Lock in the pool) and NEVER lit (the player is kicked before they
        # can reach the grace) -> the range stays locked -> the kick-watch permanently ejects the
        # player. Without this a sealed region has NO range and the client treats it as open, so you
        # can walk into a sealed sub-area (e.g. Ruin-Strewn Precipice under a sealed Mt. Gelmir), where
        # vanilla-suppress fires by item-id but there's no active check to grant -> DEAD DROPS. The
        # client honors a non-empty areaLockFlags as-is (region.rs), so no client change is needed.
        ranges = []
        for _region, _ids in REGION_PLAY_IDS.items():
            _flag = REGION_OPEN_FLAGS.get(_region)
            if _flag is None:
                continue  # no resolved open flag -> can't gate this region (left open, prior behavior)
            for _pid in _ids:
                ranges.append([_pid, _pid, _flag])
        # lockRevealFlags (2026-07-08): grant the DLC world-map reveal on DLC-region unlock. The
        # start-time path (startgrants.rs) only fires the DLC pieces at connect gated on enable_dlc;
        # tying them to the Lock reveals the Land-of-Shadow map exactly when the region opens. Each
        # kept DLC region reveals the whole DLC map (idempotent) so ANY DLC unlock covers it, even a
        # rolled draw that keeps Scadu Altus but not the Gravesite Plain entry. Client consumer LIVE
        # (region.rs lock_reveal_flags); this key was contract-declared but previously unemitted.
        reveal = {f"{r} Lock": list(_DLC_MAP_REVEAL_FLAGS)
                  for r in world._kept() if r in DLC_REGIONS}
        return {contract.AREA_LOCK_FLAGS: ranges, contract.LOCK_REVEAL_FLAGS: reveal}
