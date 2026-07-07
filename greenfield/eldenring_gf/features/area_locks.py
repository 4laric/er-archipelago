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
    "Mountaintops of the Giants": [65000, 65001],
    "Consecrated Snowfield": [65002],
    # --- legacy dungeons / capitals / underground (REGION_ID_MAP.md) ---
    "Stormveil Castle": [10000],
    "Leyndell": [11000, 11050, 35000, 19000],      # Royal + Ashen + Shunning-Grounds + Fractured Marika
    "Farum Azula": [13000],
    "Raya Lucaria Academy": [14000],
    "Miquella's Haligtree": [15000, 15001],        # Elphael + Haligtree
    "Eternal Cities": [12010, 12011, 12012, 12020, 12030, 12070],  # Ainsel/Lake of Rot/Astel/Siofra/Deeproot
    "Mohgwyn Palace": [12050],
    # --- DLC (REGION_ID_MAP.md DLC table) ---
    "Land of Shadow": [6800, 6830, 6840, 20010, 22000],  # Gravesite/Cerulean/Charo/Enir-Ilim/Stone Coffin
    "Belurat": [6820, 20000],                       # Castle Ensis + Belurat Tower Settlement
    "Jagged Peak": [6850, 6851],
    "Abyssal Woods": [6860, 28000],                 # Abyssal Woods + Midra's Manse
    "Scadu Altus": [6900, 6920, 6940, 6950],        # Scadu Altus/Scaduview/Rauh
    "Shadow Keep": [21000, 21001, 21010],
}


@register
class AreaLocks(Feature):
    name = "area_locks"

    def slot_data(self, world):
        """FOLDED 2026-07-06: areaLockFlags is no longer emitted. The play_region geometry
        (REGION_PLAY_IDS) is static/seed-invariant, and every seed-specific input (which regions
        are kept + their open flag) already rides regionOpenFlags, so the client derives the
        kick-watch ranges itself (region.rs derive_area_lock_flags, a mirror of REGION_PLAY_IDS
        below; test_gf_data.py guards the two tables against drift). We keep the table here as the
        mirror authority and still FAIL GEN on a coverage gap: any KEPT region that resolved a
        front-door open flag but has no geometry entry would have its in-game kick-watch silently
        off, so that is a hard error rather than a quiet degrade."""
        missing = [
            r for r in world._kept()
            if REGION_OPEN_FLAGS.get(r) is not None and r not in REGION_PLAY_IDS
        ]
        if missing:
            raise contract.ContractError(
                "area_locks: kept region(s) resolved an open flag but have no REGION_PLAY_IDS "
                "geometry (kick-watch would be silently off): " + ", ".join(sorted(missing)))
        return {}
