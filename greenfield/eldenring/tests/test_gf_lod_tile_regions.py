"""A COARSE LOD TILE INDEX IS NOT A FINE TILE. Refuse to snap it to the nearest region.

The overworld ships LOD variants of each tile -- m60_XX_YY_00 is the fine grid, _01 is 2x coarser,
_02 is 4x coarser. At LOD 2, `m60_10_09_02` has indices (10, 09) that are NOT fine tile coordinates;
the fine block it covers is roughly (40..43, 36..39).

Two places used to parse `m60_(\\d\\d)_(\\d\\d)` off such a string / filename and hand the result to
`tile_pr()`, whose nearest-neighbour search will ALWAYS return something -- so a coarse index got
snapped to the closest real anchor and produced a confident, WRONG region:

  * gen_data._region_of_raw   -- from the region_map.csv region column ('Overworld m60_10_09_02')
  * gen_data._gt_region       -- from the MSB datamine's map id (the LOD *filename*)

PLAYTEST (Alaric, 2026-07-11, seed AP_55352390472076588352):
    the Flail (flag 1042377060) sits at Gatefront Ruins -- LIMGRAVE.
    Both paths resolved it to WEEPING PENINSULA.
Weeping was SEALED in that seed, so the check was culled with its region, so its flag never entered
the client's `locationFlags`. He walked to it in Limgrave, picked it up, got the VANILLA Flail, and
the client logged NOTHING. A silent dead check -- no send, no vanilla suppression, no AP item.

(The mirror case is worse: mis-assign a check INTO an open region while the item really lives in a
sealed one, and AP asserts a reachability it does not have -- see DEFAULTED_REGION_APS.)

THE FIX is that the flag ID already encodes the true fine tile. ER's overworld convention is
10 XX YY nnnn:
    1042377060 -> 10|42|37|7060 -> m60_42_37 -> Limgrave     [correct]
so `_overworld_tile_of()` prefers `_recover_tile(flag)`, and `_is_fine_tile()` bound-checks any tile
index against the real anchor grid so a coarse LOD index is REJECTED rather than snapped.
"""
import unittest

from ..data import LOCATIONS


# The six checks whose region column carries a LOD-suffixed tile. Region here is GROUND TRUTH:
# Alaric confirmed the Flail/Lordsworn's in-game ("it's not in weeping it's in limgrave").
_LOD_CHECKS = {
    1042377060: ("Limgrave", "Flail -- Gatefront Ruins; was Weeping Peninsula"),
    1042377070: ("Limgrave", "Lordsworn's Greatsword -- Gatefront; was Weeping Peninsula"),
    1042397010: ("Limgrave", "Lance; was Weeping Peninsula"),
    1045527000: ("Altus Plateau", "Gravity Stone Fan"),
    1048557900: ("Mountaintops of the Giants", "Flowing Curved Sword"),
    1049547900: ("Mountaintops of the Giants", "St. Trina's Torch"),
}


class TestLodTileRegions(unittest.TestCase):

    def _region_of_flag(self, flag):
        for region, locs in LOCATIONS.items():
            for (_name, _ap, fl) in locs:
                if fl == flag:
                    return region
        return None

    def test_lod_tile_checks_land_in_their_real_region(self):
        """The flag ID encodes the fine tile; the coarse LOD index must never win."""
        for flag, (want, why) in _LOD_CHECKS.items():
            got = self._region_of_flag(flag)
            self.assertIsNotNone(got, f"flag {flag} ({why}) vanished from LOCATIONS entirely")
            self.assertEqual(
                want, got,
                f"flag {flag} ({why}) is in {got!r}, expected {want!r}. A coarse LOD tile index was "
                f"snapped to the nearest anchor instead of being rejected. If its real region is "
                f"sealed in a seed, the check is culled, never reaches the client's locationFlags, "
                f"and the pickup silently hands out the VANILLA item.")

    def test_no_check_lands_in_weeping_via_a_lod_tile(self):
        """Direct regression on the reported bug: the Gatefront trio must not be in Weeping."""
        for flag in (1042377060, 1042377070, 1042397010):
            self.assertNotEqual("Weeping Peninsula", self._region_of_flag(flag),
                                f"flag {flag} is back in Weeping Peninsula -- the LOD guard regressed")


if __name__ == "__main__":
    unittest.main()
