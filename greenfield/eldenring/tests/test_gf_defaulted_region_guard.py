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
import unittest

from ..data import LOCATIONS
from ..location_tags import LOCATION_TAGS, DEFAULTED_REGION_APS
from ..features.progression_surface import allowed_ap_ids
from .. import contract


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
