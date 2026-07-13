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

DERIVATION (matt-free): REGION_PLAY_IDS below is the region -> {play_region ids} map, derived
entirely from greenfield's own artifacts:
  * overworld tiles      -- gen_data.py's PLAY2AP grace-anchor table (61xxx/62xxx/63xxx/64xxx/65xxx);
  * legacy/underground   -- elden_ring_artifacts/REGION_ID_MAP.md (authoritative
                            BonfireWarpParam.bonfireSubCategoryId == runtime play_region_id), joined
                            to greenfield region names via gen_data.py's REGION_MAP semantics;
  * DLC sub-areas        -- REGION_ID_MAP.md DLC table, same join.
Every one of the 54 non-system play_region ids in grace_region_map is covered (52 map to the 22
greenfield regions; 11100 Roundtable Hold hub and 18000 tutorial-start are the always-open pair and
are deliberately excluded). No matt/Bedrock apworld data is read. When the region audit resolves a
sub-area's play_region id, add it here (a missing id merely means that sub-area is never kick-gated;
an id can never point at the WRONG region because the map is 1:1 against REGION_ID_MAP.md).

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

# Region -> physical play_region (5-digit subregion) ids. Matt-free; see module docstring for the
# per-id provenance. Ids are the runtime play_region_id numbering (REGION_ID_MAP.md == PLAY2AP).
REGION_PLAY_IDS = {
    # --- overworld (gen_data.py PLAY2AP grace anchors) ---
    "Limgrave": [61000, 61001],
    "Weeping Peninsula": [61002],
    "Liurnia of the Lakes": [62000, 62001, 62002],
    "Altus Plateau": [63000, 63002, 63003],
    "Mt. Gelmir": [63001, 16000, 39200],          # + Volcano Manor + Ruin-Strewn Precipice
    "Caelid": [64000, 64001, 64002],               # core + Dragonbarrow + Swamp of Aeonia
    "Mountaintops of the Giants": [65000, 65001, 65002],   # 65002 = Consecrated Snowfield, folded in
    # --- legacy dungeons / capitals / underground (REGION_ID_MAP.md) ---
    "Stormveil Castle": [10000],
    "Leyndell": [11000, 11050, 35000, 19000],      # Royal + Ashen + Shunning-Grounds + Fractured Marika
    "Farum Azula": [13000],
    "Raya Lucaria Academy": [14000],
    "Miquella's Haligtree": [15000, 15001],        # Elphael + Haligtree
    "Eternal Cities": [12010, 12011, 12012, 12020, 12030, 12070],  # Ainsel/Lake of Rot/Astel/Siofra/Deeproot
    "Mohgwyn Palace": [12050],
    # --- DLC (REGION_ID_MAP.md DLC table, joined via gen_data.py REGION_MAP). The old 'Land of
    # Shadow' catch-all was split (region_spine.py) into Gravesite Plain + Ancient Ruins of Rauh +
    # Enir-Ilim to match gen_data.REGION_MAP; Castle Ensis (6820) folds into Gravesite Plain and
    # Rauh (6950) splits out of Scadu Altus, exactly as the generator now tags those locations. ---
    "Gravesite Plain": [6800, 6820, 6830, 6840, 22000],  # Gravesite/Castle Ensis/Cerulean/Charo/Stone Coffin
    "Belurat": [20000],                             # Belurat Tower Settlement
    "Ancient Ruins of Rauh": [6950],                # Rauh (Romina)
    "Enir-Ilim": [20010],                           # Enir-Ilim tower
    "Jagged Peak": [6850, 6851],
    "Abyssal Woods": [6860, 28000],                 # Abyssal Woods + Midra's Manse
    "Scadu Altus": [6900, 6920, 6940],              # Scadu Altus/Scaduview + Manus Metyr
    "Shadow Keep": [21000, 21001, 21010],
}


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
