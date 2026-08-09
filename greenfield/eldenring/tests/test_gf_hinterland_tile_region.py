"""A FIELD BOSS HAS NO BOSS-AREA ROW, SO NOTHING NOTICED IT STANDS IN ANOTHER REGION.

Scaduview (play_region 6920, the Hinterland) was FOLDED into Shadow Keep on 2026-07-19
(region_groups.py). Two Tree Sentinels stand in it, within sight of each other:

    2050470800  m61_50_47   <- the tile holds NO grace
    2050480860  m61_50_48   <- anchored by the Hinterland graces 76935 / 76960

`_m61_tile_region()` regions a DLC overworld tile by majority vote of the graces standing ON it and
nearest-neighbours the tiles that hold none. For m61_50_47 THREE anchors tie at distance 1 --
(50,48)=6920 Shadow Keep to the south, (51,47)=6900 and (49,47)=6900 Scadu Altus east and west --
and `min()` breaks that tie by ANCHOR61's iteration order, i.e. by grace_flags.tsv ROW ORDER, not by
evidence. It came down 6900. So the northern sentinel's legacy divvy dealt it 28 SCADU ALTUS checks
while its twin one tile south correctly read Shadow Keep.

MOTIVATING CASE (Alaric, 2026-08-09): "the two tree sentinels in hinterlands ... they're both right
next to each other in Hinterland which we absorbed into shadow keep."

WHY IT BITES: a seed that keeps Scadu Altus WITHOUT Shadow Keep ships a sweep group whose TRIGGER
the player can never reach -- the kick-watch ejects them from the Hinterland before the fight -- so
28 Scadu Altus checks are unobtainable by sweep. That is the Golden Hippopotamus case (#445) with
the regions swapped, and features/boss_locks already drops such a group... but ONLY where
SWEEP_ARENA_REGION has an entry, and a field boss has no PlayRegionParam boss-area overlay, so it
had none. `boss_area_regions.tsv` is a LOWER BOUND, and this is what living inside it looks like.

THE SHAPE OF THE FIX MATTERS. The members stay in SCADU ALTUS on purpose: m61_50_47 legitimately
STRADDLES the border -- its two item checks (2050477010 / 2050477020) are nearest to 76905 Church
District Highroad, a Scadu Altus grace. Moving the whole tile with M61_TILE_CURATED was tried first
and grew a 56th straddling grace (minority share 4.44% -> 4.49%), which test_gf_grace_straddle
refuses by design ("find which side is wrong -- do NOT raise the pin"). Only the ARENA is Hinterland.
"""
import unittest

from ..boss_sweeps import DUNGEON_SWEEPS, SWEEP_ARENA_REGION, SWEEP_REGION

# The two Tree Sentinel healthbar heads (boss_healthbars.py). Same map m61_50, DIFFERENT arenas, so
# the (map, arena) merge that collapses a two-healthbar fight does not apply: two real fights.
_NORTH = 2050470800   # m61_50_47, the graceless tile -- the coin landed Scadu Altus
_SOUTH = 2050480860   # m61_50_48, anchored by the Hinterland graces

_ARENA = "Shadow Keep"   # where you STAND: the Hinterland, folded into the Keep 2026-07-19


class TestHinterlandSentinelArenas(unittest.TestCase):

    def test_north_sentinel_arena_is_recorded(self):
        """The motivating case: the arena must not be UNAUDITED, and it must be the Keep."""
        self.assertIn(_NORTH, SWEEP_ARENA_REGION,
                      f"Tree Sentinel {_NORTH} has no arena region -- back to UNAUDITED, so the "
                      f"arena/member mismatch drop in features/boss_locks cannot see it and its "
                      f"28 members go unreachable on a Scadu-Altus-without-Shadow-Keep seed.")
        self.assertEqual(_ARENA, SWEEP_ARENA_REGION[_NORTH])

    def test_both_sentinels_are_fought_in_the_same_region(self):
        """The invariant that made the bug visible, stated as a relation.

        Written this way so it still fails if a future re-fold moves BOTH sentinels somewhere new
        but only carries one of them across."""
        arenas = {SWEEP_ARENA_REGION.get(_NORTH), SWEEP_ARENA_REGION.get(_SOUTH, _ARENA)}
        self.assertEqual(
            1, len(arenas),
            f"the two Hinterland Tree Sentinels are fought in {sorted(str(a) for a in arenas)} -- "
            f"two bosses within sight of each other cannot stand in two regions.")

    def test_north_sentinel_members_stay_in_scadu_altus(self):
        """The fix is ARENA-scoped. If the members moved, someone re-tiled a straddling tile."""
        self.assertEqual(
            "Scadu Altus", SWEEP_REGION.get(_NORTH),
            f"sentinel {_NORTH}'s members moved out of Scadu Altus. m61_50_47 straddles the border; "
            f"its checks are nearest to 76905 Church District Highroad. Moving them grows a "
            f"straddling grace -- see test_gf_grace_straddle, which refuses that.")

    def test_the_mismatch_is_visible_to_boss_locks(self):
        """A guard is worthless unless the consumer can act on it (CONTRIBUTING rule 11).

        features/boss_locks drops a group whose arena region differs from its members' region. That
        can only fire if BOTH halves are present and they actually differ."""
        self.assertNotEqual(
            SWEEP_ARENA_REGION.get(_NORTH), SWEEP_REGION.get(_NORTH),
            "arena and members now agree, so the mismatch drop never fires for this group -- if "
            "that is deliberate, this whole file is stale and the curation should go.")
        self.assertTrue(DUNGEON_SWEEPS.get(_NORTH),
                        f"sentinel {_NORTH} sweeps nothing at all -- nothing left to protect.")


if __name__ == "__main__":
    unittest.main()
