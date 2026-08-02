"""A GUESSED REGION MAY NOT CARRY PROGRESSION.

gen_data._region_of_raw() has three paths that fall back to the HUB (Roundtable Hold) when the real
region of a check is unknown:

    * an 'Overworld m60' row whose tile won't parse / has no play_region
    * method == 'shop_multi'   ("Multiple merchants (various regions)")
    * a REGION_MAP miss -- the region column is a PLACEHOLDER, not a place:
          'Global / Filler (scattered by design)'   (global_filler)
          'Global / Common-event (unplaced)'        (global)
          'Non-merchant reference (...)'            (shop_reference)

The quarantine site used to justify this with "reachable-from-start, never a false gate". That is
backwards. It avoids a false LATE gate, but it manufactures a FALSE EARLY CLAIM: AP is told the check
sits in the always-open hub, so fill is free to place PROGRESSION on it -- while the item still
physically spawns wherever it actually lives. If that place is behind a region Lock, the seed is dead.

REAL SEED (Alaric, AP_55352390472076588352, 2026-07-11, Caelid start):
    flag 400220, a Golden Seed, method=global_filler, region='PENDING'  -> quarantined to the HUB
    fill placed the STORMVEIL CASTLE LOCK on it (ap 7773853, sphere 1)
    ground truth (msb_flag_region.tsv, enemy chain): m10_00 = Stormveil, m60_46_36 = Limgrave
=>  the Stormveil key was inside Stormveil. Circular. Unwinnable.
    Confirmed in the client log: `AP scout-proof: location 7773853 -> Stormveil Castle Lock`.

Quarantining to the HUB remains fine for DETECTION -- the flag fires wherever the item really is. It
is simply not a licence to assert reachability. Note the rule is NOT "PENDING map => unjustified":
most PENDING rows still NAME a real place ('shop_merchant -> Caelid', 'boss_arena -> Stormveil
Castle') and are derived. Only a DEFAULTED region is a guess.
"""
import collections
import csv
import os
import re
import unittest

from ..data import LOCATIONS
from ..location_tags import LOCATION_TAGS, DEFAULTED_REGION_APS, REGION_CONFIRMED_APS
from ..features.progression_surface import allowed_ap_ids
from .. import contract

_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TILE_RE = re.compile(r"m60_(\d\d)_(\d\d)")


def _beside(name):
    """A gen input copied in beside the installed package (tools/gf_test.py --install-only).

    Absent when the tests run from SOURCE, where these live one directory up in greenfield/ -- the
    same convention test_gf_tile_anchor_coverage.py uses. Returns None so the caller can skip rather
    than run BLIND: an oracle that silently reads nothing is a vacuous pass.
    """
    path = os.path.join(_PKG_DIR, name)
    return path if os.path.isfile(path) else None


def _anchor_tiles():
    """gen_data's ANCHOR, rebuilt from the same two committed tsvs: the overworld tiles that HOLD a
    grace with a play_region. Every other tile is one tile_pr() nearest-neighbours a guess onto."""
    gfp, gregp = _beside("grace_flags.tsv"), _beside("grace_region_map.tsv")
    if not gfp or not gregp:
        return None
    gf = {}
    with open(gfp, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if 71000 <= int(row["warpUnlockFlag"]) <= 76999:
                gf[row["warpUnlockFlag"]] = row["mapTile"]
    greg = {}
    with open(gregp, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            greg[row["grace_flag"]] = row["play_region_id"]
    anchor = set()
    for flag, tile in gf.items():
        pr, m = greg.get(flag), _TILE_RE.match(tile)
        if pr and pr != "0" and m:
            anchor.add((int(m.group(1)), int(m.group(2))))
    assert len(anchor) > 100, f"only {len(anchor)} anchored tiles -- the grace join has drifted"
    return anchor


def _msb_truth_map():
    """gen_data's MSB_TRUTH_MAP: flag -> its ONE datamined map, unambiguous placements only."""
    path = _beside("msb_flag_region.tsv")
    if not path:
        return None
    seen = collections.defaultdict(set)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 2 or not p[0].isdigit():
                continue
            seen[int(p[0])].add(p[1])
    truth = {f: next(iter(m)) for f, m in seen.items() if len(m) == 1}
    assert len(truth) > 1000, f"only {len(truth)} unambiguous MSB placements -- the datamine has drifted"
    return truth


def _ap_of(flag):
    """Resolve a check's LIVE ap-id from its acquisition FLAG.

    ap-ids are POSITIONAL (BASE_AP + index over `rows`), so they DRIFT whenever a row is added or
    dropped earlier in the list -- and this test exists to guard a softlock, so it must not go quietly
    stale the first time someone recovers a check. The flag is the durable key; the ap-id is derived.
    (Same reasoning gen_data already applies to MAJOR_BOSS_EXTRAS.) Pinning the ap-id is pinning the
    symptom.
    """
    for locs in LOCATIONS.values():
        for (_name, ap, fl) in locs:
            if fl == flag:
                return ap
    raise AssertionError(f"no location carries flag {flag} -- the check was DROPPED from the world")


class TestDefaultedRegionGuard(unittest.TestCase):

    def test_defaulted_set_is_populated(self):
        """If this is empty the guard has silently stopped being emitted by gen_data."""
        self.assertGreater(len(DEFAULTED_REGION_APS), 0,
                           "DEFAULTED_REGION_APS is empty -- gen_data no longer flags guessed regions")

    def test_the_stormveil_golden_seed_is_barred(self):
        """The exact check that killed AP_55352390472076588352: Golden Seed f400220, really in
        Stormveil, quarantined to the HUB, given the Stormveil Castle Lock.

        Keyed by FLAG, not ap-id: the ap-ids these used to pin (7773853 / 7773916) drifted the moment
        the boss-reward family was recovered (+37 rows), and 7773916 silently became a DIFFERENT,
        legitimately-unbarred Liurnia check -- so the assertion started failing while the property it
        guards was still perfectly true. A guard that pins a positional id is a guard with a half-life.
        """
        for flag, what in ((400220, "Golden Seed f400220"),):
            ap = _ap_of(flag)
            self.assertIn(ap, DEFAULTED_REGION_APS,
                          f"ap {ap} ({what}, region GUESSED) must be barred from progression")
        # f520180 used to sit beside f400220 here. It is NOT barred any more -- and that is the
        # derivation catching up, not the guard regressing: its MSB truth map is m30_18 (Giants'
        # Mountaintop Catacombs), which the ConnectCollision datamine resolved on 2026-07-12
        # (dungeon_regions.tsv m30_18 -> Mountaintops of the Giants). Pin the derived region so a
        # future regen can't silently drop it back into the guessed pool.
        ap = _ap_of(520180)
        self.assertNotIn(ap, DEFAULTED_REGION_APS,
                         "Golden Seed f520180 regressed to a GUESSED region -- dungeon_regions.tsv "
                         "lost m30_18 (re-run tools/datamine_dungeon_regions.py with the MSBs)")

    def test_the_rold_seam_boss_check_is_barred(self):
        """f530505, Gargoyle's Black Blades -- the Black Blade Kindred BELOW the Grand Lift of Rold.

        Filed 'Mountaintops of the Giants', and physically on m60_49_52: Forbidden-Lands ground under
        the lift. Rold is deliberately NOT in logic (README: "You never need the Rold Medallion to
        reach the Mountaintops of the Giants"), so a Mountaintops-anchored player cannot stand on that
        ground -- the Rold Medallion is a LEYNDELL check. A region Lock or a required Great Rune here
        is an unwinnable seed.

        It got through because the tile-guess bar judged only the DESCRIPTOR tile (m60_39_53, which IS
        anchored, hence the confident pass) while the region actually shipped came from the MSB tile
        m60_49_52, which is graceless and nearest-neighbours onto the m60_49_53 seam that carries
        graces for BOTH regions. The two OTHER checks on that same ground were already barred, which
        is the tell: one derivation path was guarded and the other was not.
        """
        for flag, what in ((530505, "Gargoyle's Black Blades f530505 (below the Grand Lift of Rold)"),
                           (1049527000, "Freezing Grease f1049527000 (same ground)"),
                           (1049527800, "Golden Seed f1049527800 (same ground)")):
            ap = _ap_of(flag)
            self.assertIn(ap, DEFAULTED_REGION_APS,
                          f"ap {ap} ({what}) is progression-eligible -- fill may place a region Lock "
                          f"or a required Great Rune below the Rold lift, which a Mountaintops-"
                          f"anchored player cannot reach without a Leyndell check")

    def test_no_msb_derived_graceless_tile_is_progression_eligible(self):
        """THE STRUCTURAL FORM of the case above, so the next one cannot arrive quietly.

        region_of() ranks the MSB datamine ABOVE the row's map column, so for most checks the tile
        that PRODUCED the region is the MSB one. If that tile holds no grace, the region is a
        nearest-neighbour guess and the check may not carry progression -- exactly as if the guess had
        come through the map column.

        The ONE exception is a check a human stood in front of and confirmed in game
        (gen_data._REGION_CONFIRMED_FLAGS -> REGION_CONFIRMED_APS). Read, not re-typed: a test that
        keeps its own copy of that list is a test that goes stale the next time Alaric clears one.
        """
        anchor, truth = _anchor_tiles(), _msb_truth_map()
        if anchor is None or truth is None:
            self.skipTest("gen inputs not installed beside the package -- the oracle would run BLIND")
        xs = [x for x, _ in anchor]; ys = [y for _, y in anchor]
        lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
        ap_by_flag = {fl: ap for locs in LOCATIONS.values() for (_n, ap, fl) in locs}
        judged, leaked = 0, []
        for flag, tile in truth.items():
            m = _TILE_RE.match(tile)
            if not m:
                continue
            x, y = int(m.group(1)), int(m.group(2))
            if not (lo_x <= x <= hi_x and lo_y <= y <= hi_y):
                continue          # a coarse LOD index, not a fine tile -- _gt_region refuses it too
            if (x, y) in anchor:
                continue
            ap = ap_by_flag.get(flag)
            if ap is None:
                continue          # datamined flag that is not a check in this world
            judged += 1
            if ap not in DEFAULTED_REGION_APS and ap not in REGION_CONFIRMED_APS:
                leaked.append((ap, flag, tile))
        # MEASURED 2026-08-02: 309 checks are judged here, 298 of which the `_mtile` path already
        # barred on its own -- the two derivations mostly agree, and the 11 they disagreed about are
        # exactly what this gate exists for. The floor is a VACUITY tripwire, not a ratchet: if the
        # msb table or the grace join breaks, this oracle would quietly pass on an empty set.
        self.assertGreater(judged, 200,
                           f"only {judged} checks derive a region from a graceless MSB tile (309 when "
                           f"this was written) -- the oracle has gone vacuous, not the defect gone away")
        self.assertEqual([], sorted(leaked),
                         f"{len(leaked)} check(s) take their region from a GRACELESS msb tile "
                         f"(nearest-neighbour guess) and are still progression-eligible: "
                         f"{sorted(leaked)[:8]}")

    def test_the_region_confirmed_exception_stays_small_and_human(self):
        """The bar's only escape hatch. It exists so an in-game confirmation can BUY BACK a check the
        tile geometry cannot vouch for -- which means every entry is a claim someone made with their
        eyes. Keep it visible and keep it tiny; a growing list is the guard being negotiated away."""
        self.assertLessEqual(len(REGION_CONFIRMED_APS), 12,
                             "REGION_CONFIRMED_APS is growing -- each entry un-bars a check on ground "
                             "the derivation cannot see. If these are real in-game confirmations, "
                             "raise the pin WITH who confirmed them and when (gen_data "
                             "_REGION_CONFIRMED_FLAGS carries that note); if not, they are guesses "
                             "wearing a confirmation's clothes.")
        self.assertEqual([], sorted(set(REGION_CONFIRMED_APS) & set(DEFAULTED_REGION_APS)),
                         "a check cannot be both region-CONFIRMED and region-GUESSED")

    def test_no_defaulted_check_is_ever_progression_eligible(self):
        """THE INVARIANT. Over every progression surface the yaml can select, no check whose region was
        a guess may be eligible to hold progression."""
        vocab = sorted(contract.PROGRESSION_SURFACE_VOCAB) \
            if hasattr(contract, "PROGRESSION_SURFACE_VOCAB") else \
            ['Church', 'Fragment', 'GreatRune', 'KeyItem', 'MajorBoss',
             'Remembrance', 'Revered', 'Seedtree', 'ShopSlot']
        # the full surface is the most permissive selection -- if it's clean, every subset is
        allowed = allowed_ap_ids(LOCATION_TAGS, vocab)
        leaked = sorted(set(allowed) & set(DEFAULTED_REGION_APS))
        self.assertEqual([], leaked,
                         f"{len(leaked)} check(s) with a GUESSED region are progression-eligible -- "
                         f"AP will believe them reachable at spawn while the item spawns in whatever "
                         f"region it actually lives in (softlock): {leaked[:10]}")

    def test_each_surface_class_alone_is_clean(self):
        """Per-class, so a future tag can't sneak a guessed check back in through one narrow surface."""
        for cls in ('Seedtree', 'ShopSlot', 'GreatRune', 'KeyItem', 'MajorBoss',
                    'Remembrance', 'Church', 'Fragment', 'Revered'):
            leaked = sorted(set(allowed_ap_ids(LOCATION_TAGS, [cls])) & set(DEFAULTED_REGION_APS))
            self.assertEqual([], leaked,
                             f"surface class {cls!r} admits {len(leaked)} guessed-region check(s): {leaked[:5]}")


if __name__ == "__main__":
    unittest.main()
