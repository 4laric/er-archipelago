"""A shop row that is not STOCKED yet may not carry progression.

Alaric, 2026-07-12:
    "more and more roundtable checks become available over progress. we just need to make sure the
     progression_surface row at twin maiden husks is something that's there at the start."

AP models a shop check's reachability as "is the REGION open?". For a shop that is necessary but NOT
SUFFICIENT. `ShopLineupParam.eventFlag_forRelease` is the flag that makes the row EXIST in the menu:

    release == 0  -> stocked the moment you can reach the merchant.
    release != 0  -> the row is NOT THERE until an event fires -- a bell bearing handed to the Twin
                     Maidens, a boss killed, an NPC quest advanced.

252 of the 679 derived shop checks (37%) are gated this way, and the logic has no idea when any of them
opens. So the shop can be wide open and the row simply not on the shelf.

The sharp edge is the Roundtable, because it is the START region (random-start hub re-root). Of its 171
shop checks, 72 are release-gated -- and ALL 49 of Enia's block 1015 are, several behind flag 9107, which
is ENDGAME. A seed that puts a key item on one of those has placed a progression item behind the very
progression it gates. That is the DEFAULTED_REGION softlock in a different hat, so it gets the same
answer: gated rows stay CHECKS, but they may never be REQUIRED (SHOP_RELEASE_GATED_APS -> item_rule).

Ground truth for every number here: ShopLineupParam.csv -> greenfield/shop_rows.tsv (release_flag column),
via tools/datamine_shop_rows.py. No hand lists.
"""
import csv
import os
import unittest

from ..location_tags import SHOP_RELEASE_GATED_APS
from ..data import LOCATIONS, HUB

# shop_rows.tsv is gen_data's INPUT: in the SOURCE tree it sits beside the package (GREENFIELD/), and
# the world-install step copies it INTO the installed package (GF_PKG/) so this gate also runs in the
# installed-world pytest (which is what CI runs). Resolve from either -- first existing wins. Same
# convention as test_gf_boss_sweeps' region_map.csv; hardcoding one path makes the test pass in the dev
# tree and silently vanish in CI, which is the worst of both.
_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_GREENFIELD = os.path.dirname(_GF_PKG)
_TSV = next((p for p in (os.path.join(_GF_PKG, "shop_rows.tsv"),
                         os.path.join(_GREENFIELD, "shop_rows.tsv")) if os.path.isfile(p)),
            os.path.join(_GF_PKG, "shop_rows.tsv"))

# The Twin Maiden Husks are shop BLOCK 1018 (the block holds the White/Blue Cipher Rings, Spirit Calling
# Bell, Flask of Wondrous Physick, Crafting Kit and Memory Stone -- their inventory exactly).
_TWIN_MAIDENS_BLOCK = "1018"
# Enia's block. Every one of its 49 rows is release-gated.
_ENIA_BLOCK = "1015"

# Alaric: "Finger Seal is for sure one that's there from start." The param agrees -- row 101871,
# eventFlag_forRelease = 0. It is the canonical member of the start-available surface, so it is the
# canonical thing this guard must NOT bar.
_FINGER_SEAL_ROW = 101871


def _rows():
    with open(_TSV, encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))


class TestShopReleaseGate(unittest.TestCase):

    def setUp(self):
        self.rows = _rows()
        self.assertTrue(self.rows, "shop_rows.tsv missing/empty -- the gate degrades SILENTLY without it")

    def test_release_flag_column_is_present(self):
        """Without this column gen_data cannot see the gate at all and every row looks start-available."""
        self.assertIn("release_flag", self.rows[0],
                      "shop_rows.tsv has no release_flag column -- regenerate with "
                      "tools/datamine_shop_rows.py, or the gate silently bars nothing.")

    def test_finger_seal_is_start_available_and_may_carry_progression(self):
        """The row Alaric named. It must survive the guard -- over-barring is its own failure mode."""
        fs = [r for r in self.rows if int(r["row_id"]) == _FINGER_SEAL_ROW]
        self.assertEqual(1, len(fs), f"Finger Seal row {_FINGER_SEAL_ROW} vanished from shop_rows.tsv")
        self.assertEqual("0", fs[0]["release_flag"].strip(),
                         "Finger Seal is stocked from the start (eventFlag_forRelease == 0)")
        flag = int(fs[0]["stock_flag"])
        aps = [ap for locs in LOCATIONS.values() for (_n, ap, f) in locs if f == flag]
        self.assertTrue(aps, f"Finger Seal (flag {flag}) is not a location at all")
        for ap in aps:
            self.assertNotIn(ap, SHOP_RELEASE_GATED_APS,
                             "Finger Seal is on the shelf at start -- it must stay progression-capable")

    def test_every_gated_row_that_is_a_location_is_barred(self):
        """The guard must be COMPLETE, not a sample. Any gated row still able to hold a key item is a
        potential softlock."""
        gated_flags = {int(r["stock_flag"]) for r in self.rows if r["release_flag"].strip() not in ("", "0")}
        leaked = [(reg, n, ap) for reg, locs in LOCATIONS.items() for (n, ap, f) in locs
                  if f in gated_flags and ap not in SHOP_RELEASE_GATED_APS]
        self.assertEqual([], leaked,
                         f"{len(leaked)} release-gated shop check(s) can still carry progression, e.g. "
                         f"{leaked[:3]} -- regenerate location_tags.py")

    def test_enia_block_is_entirely_barred(self):
        """All 49 of block 1015 are gated, several behind ENDGAME flag 9107. Not one may be required."""
        enia = [r for r in self.rows if r["shop_block"] == _ENIA_BLOCK]
        self.assertTrue(enia, "Enia's block 1015 vanished from shop_rows.tsv")
        self.assertTrue(all(r["release_flag"].strip() not in ("", "0") for r in enia),
                        "block 1015 is supposed to be 100% release-gated -- the param changed under us")
        flags = {int(r["stock_flag"]) for r in enia}
        for reg, locs in LOCATIONS.items():
            for (n, ap, f) in locs:
                if f in flags:
                    self.assertIn(ap, SHOP_RELEASE_GATED_APS,
                                  f"Enia row {n} can carry progression, but her shop does not stock it "
                                  f"until an endgame flag fires")

    def test_twin_maidens_still_have_a_start_available_progression_surface(self):
        """THE POINT. The hub is the START region. If the guard barred every Twin Maidens row, the start
        would have no shop progression surface at all -- so this asserts the guard did not over-reach."""
        free = {int(r["stock_flag"]) for r in self.rows
                if r["shop_block"] == _TWIN_MAIDENS_BLOCK and r["release_flag"].strip() == "0"}
        self.assertTrue(free, "Twin Maiden Husks have NO start-available rows -- param read is wrong")
        surface = [(n, ap) for locs in LOCATIONS.values() for (n, ap, f) in locs
                   if f in free and ap not in SHOP_RELEASE_GATED_APS]
        self.assertTrue(
            surface,
            "Twin Maiden Husks have zero progression-capable checks that are stocked at the start. "
            "The start region's shop surface is empty -- the guard has over-reached.")

    def test_hub_has_a_progression_surface_at_all(self):
        """Broader backstop: whatever else is barred, the START region must retain checks that can hold
        progression, or fill has nowhere to seed sphere 0."""
        from ..location_tags import DEFAULTED_REGION_APS
        barred = frozenset(SHOP_RELEASE_GATED_APS) | frozenset(DEFAULTED_REGION_APS)
        usable = [n for (n, ap, _f) in LOCATIONS.get(HUB, []) if ap not in barred]
        self.assertTrue(usable, f"start region {HUB!r} has NO progression-capable location left")


if __name__ == "__main__":
    unittest.main()
