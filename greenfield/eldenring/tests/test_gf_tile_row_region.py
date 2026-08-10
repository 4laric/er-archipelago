"""A graceless overworld tile is regioned by PlayRegionParam's OWN ROW, not by a hop to a neighbour.

THE DEFECT, reported by a player on Nexus (2026-08-09): *"items said to be in a certain region when
they're actually in another, like ghostflame call being in Cerulean Coast when it should belong to
Charo's hidden grave."* He was right.

`ANCHOR` / `ANCHOR61` only know tiles that CONTAIN A GRACE -- 151 of the 325 overworld tiles bearing
checks have none -- and `tile_pr()` nearest-neighbours the rest onto whichever neighbour happens to
hold one. Tile `m61_47_39` holds no grace, so its nine checks were hopped onto the Cerulean Coast
graces next door. `greenfield/play_region_buckets.tsv` has carried a row for that exact tile the
whole time: bucket **68400**, and 68400 is Charo's. That table is not an inference and not a
neighbour's opinion -- it is PlayRegionParam, in the same id space `er_logic::region_lock::
kick_decision` compares against. `gen_data.TILE_ROW_REGION` now consults it.

WHY IT MATTERS BEYOND A LABEL. A check is CREATED from its assigned region (`core._add_locations`
walks `[HUB] + kept`) and REACHED from the ground it stands on. Cerulean-without-Charo's created
seven locations behind a kick; Charo's-without-Cerulean never created them at all, on a region that
ships twenty checks in total.

CONTRIBUTING RULE 11: the motivating case is the acceptance test, asserted through the FINISHED
pipeline, one stage at a time so a failure says WHICH stage regressed --
  1. the DATAMINE still names the tile and its single bucket (play_region_buckets.tsv);
  2. the SPINE still owns that bucket (region_groups.PLAY_REGION_GROUPS);
  3. the SHIPPED corpus puts the check in that region (data.LOCATIONS) -- and does so with no
     per-flag pin behind it, which is the half that was true for two of the nine checks before and
     is why the other seven went unnoticed.

🛑 Keyed on EVENT FLAGS. ap-ids are positional and renumber on any regen that adds a check.
"""
import importlib.util
import os
import unittest

try:                                   # pytest (package context)
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                    # direct `python test_gf_tile_row_region.py`
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)          # installed: <ap>/worlds/eldenring ; source: greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)    # source tree only
REPO = find_repo_root(HERE)


def _first(*cands):
    return next((p for p in cands if os.path.isfile(p)), None)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUCKETS_TSV = _first(os.path.join(GF_PKG, "play_region_buckets.tsv"),
                     os.path.join(GREENFIELD, "play_region_buckets.tsv"))
SPINE = _first(os.path.join(GF_PKG, "region_groups.py"),
               os.path.join(GREENFIELD, "region_groups.py"))
DATA = os.path.join(GF_PKG, "data.py")

# The tile the report is about, and every check the datamine places on it. All nine were Cerulean
# before 2026-08-09 except the two that carried a hand pin (68710, 2047397040) -- listed here TOGETHER
# so the fix cannot regress into "the pinned two are fine and the rest drifted back" a second time.
CHAROS_TILE = "m61_47_39"
CHAROS_BUCKET = "68400"
TILE_47_39_FLAGS = {
    530855,       # Ash of War: Ghostflame Call  <- THE REPORTED CHECK
    2047397000,   # Spirit Sword
    2047397050,   # Ghostflame Bloom
    2047397070,   # Scadutree Fragment - At Fissure Cross
    2047397080,   # Grave Glovewort [9]
    2047397090,   # Smithing Stone [6]
    2047397995,   # Starlight Shards
    68710,        # Greater Potentate's Cookbook [14]   <- was pinned in FLAG_REGION_OVERRIDE
    2047397040,   # Grave Glovewort [9]                 <- was pinned in FLAG_REGION_OVERRIDE
}
# Retired 2026-08-09 because the derivation reproduces them. A redundant manual override is a
# failure (CONTRIBUTING), and these two are also the evidence the derivation was missing.
RETIRED_PINS = (68710, 2047397040)

# A tile claimed by TWO buckets in two regions may NOT be resolved -- the join is tile-level and
# bucket volumes are 3-D. m61_47_44 is the one such overworld tile today, and the check standing on
# it is the KNOWN_AMBIGUOUS row in test_gf_check_ground_regions.
AMBIGUOUS_TILE = "m61_47_44"


def _tile_buckets():
    out = {}
    with open(BUCKETS_TSV, encoding="utf-8") as fh:
        for ln in fh:
            if ln[:1] == "#" or ln.startswith("bucket"):
                continue
            p = ln.rstrip("\n").split("\t")
            if len(p) < 3 or not p[0].isdigit():
                continue
            for tile in p[2].split(";"):
                if tile.startswith(("m60_", "m61_")):
                    out.setdefault(tile, set()).add(p[0])
    return out


class TileRowRegion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if BUCKETS_TSV is None or SPINE is None:
            raise unittest.SkipTest(
                "play_region_buckets.tsv / region_groups.py are not beside the package -- the "
                "derivation this suite guards is UNVERIFIED here, and this skip is that fact.")
        cls.tiles = _tile_buckets()
        cls.rg = _load(SPINE, "gf_region_groups_trr")
        cls.data = _load(DATA, "gf_data_trr")
        cls.region_of = {fl: reg for reg, items in cls.data.LOCATIONS.items() for (_n, _ap, fl) in items}

    # ---- stage 1: the datamine -------------------------------------------------------------
    def test_stage1_the_datamine_still_names_the_tile_and_one_bucket(self):
        got = self.tiles.get(CHAROS_TILE)
        self.assertEqual(got, {CHAROS_BUCKET},
                         "play_region_buckets.tsv no longer puts %s in exactly bucket %s (got %r). "
                         "Re-emit changed the input under the derivation; the region move below is "
                         "no longer supported by it." % (CHAROS_TILE, CHAROS_BUCKET, got))
        # WITNESS: the join must have parsed a real corpus, or "one bucket" is what an empty file says.
        self.assertGreater(len(self.tiles), 50,
                           "only %d overworld tile(s) parsed out of play_region_buckets.tsv -- the "
                           "parse broke, so every assertion here is vacuous." % len(self.tiles))

    def test_stage1_an_ambiguous_tile_is_left_unresolved(self):
        """The rule is single-bucket-or-nothing; a two-region tile may not be resolved to either."""
        self.assertEqual(len(self.tiles.get(AMBIGUOUS_TILE, ())), 2,
                         "%s no longer carries two buckets -- if the data really changed, the "
                         "KNOWN_AMBIGUOUS pin in test_gf_check_ground_regions must move with it."
                         % AMBIGUOUS_TILE)

    # ---- stage 2: the spine ----------------------------------------------------------------
    def test_stage2_the_spine_still_owns_that_bucket(self):
        owner = {str(b): reg for reg, bs in self.rg.PLAY_REGION_GROUPS.items() for b in bs}
        self.assertEqual(owner.get(CHAROS_BUCKET), "Charo's",
                         "region_groups.PLAY_REGION_GROUPS no longer gives bucket %s to Charo's "
                         "(got %r). The 2026-07-15 in-game kick measured 6840000 there."
                         % (CHAROS_BUCKET, owner.get(CHAROS_BUCKET)))

    # ---- stage 3: the shipped corpus -------------------------------------------------------
    def test_stage3_every_check_on_the_tile_ships_as_charos(self):
        # WITNESS (test_gf_vacuous_pass): assert the corpus HAS all nine flags before asserting that
        # none of them is misfiled. "no check is wrong" is also what a lookup that matched nothing says.
        self.assertEqual(len([fl for fl in TILE_47_39_FLAGS if fl in self.region_of]),
                         len(TILE_47_39_FLAGS),
                         "not every flag on %s is in data.LOCATIONS at all -- the corpus moved under "
                         "this fixture, so the emptiness check below would be vacuous." % CHAROS_TILE)
        wrong = sorted((fl, self.region_of.get(fl)) for fl in TILE_47_39_FLAGS
                       if self.region_of.get(fl) != "Charo's")
        self.assertEqual(wrong, [],
                         "check(s) on %s did not ship in Charo's: %r. This is the reported defect -- "
                         "a Charo's-only seed does not create them and a Cerulean-only seed creates "
                         "them behind a kick." % (CHAROS_TILE, wrong))

    def test_stage3_the_reported_check_by_name(self):
        """f530855 is the case this derivation was built for. Name it, so it cannot go quiet."""
        self.assertEqual(self.region_of.get(530855), "Charo's",
                         "Ash of War: Ghostflame Call (f530855) is back outside Charo's.")

    # ---- the pins the derivation replaced --------------------------------------------------
    def test_the_retired_pins_did_not_come_back(self):
        if REPO is None:
            raise unittest.SkipTest(REPO_ONLY_REASON)
        with open(os.path.join(REPO, "greenfield", "gen_data.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("FLAG_REGION_OVERRIDE = {")
        body = src[i:src.index("\n}\n", i)]
        # WITNESS (test_gf_vacuous_pass): the "did a pin come back" scan must be able to SEE a pin.
        # 2048407010 stays pinned on purpose -- its tile 48,40 has no PlayRegionParam row -- so it is
        # the positive control that proves this string search still matches the table's format.
        self.assertIn("\n    2048407010:", body,
                      "the FLAG_REGION_OVERRIDE scan found none of the pins it KNOWS are there -- "
                      "the table's formatting changed and this search is now blind.")
        back = [f for f in RETIRED_PINS if ("\n    %d:" % f) in body]
        self.assertEqual(back, [],
                         "flag(s) %r are pinned in FLAG_REGION_OVERRIDE again. They sit on %s, which "
                         "TILE_ROW_REGION resolves on its own -- a redundant manual override is a "
                         "failure, and re-adding one hides that the other seven checks on the tile "
                         "depend on the derivation being right." % (back, CHAROS_TILE))


if __name__ == "__main__":
    unittest.main()
