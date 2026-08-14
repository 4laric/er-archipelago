"""A check must STAND on ground its seed lets the player walk to -- the second half of issue #445.

THE MECHANISM, and it is two derivations that had never been made to agree:

  * `core._add_locations` walks `[HUB] + kept` and CREATES a location for every check whose ASSIGNED
    region is kept. That assignment comes from the check's flag / map / MSB attribution.
  * `er_logic::region_lock::kick_decision` ejects the player from any play_region bucket whose
    region is not kept. That comparison is made against the player's POSITION.

Where a check's assigned region and its position's region differ, a seed can create a location it
also forbids you to reach: created, flag-polled, counted on the tracker, uncollectable.

FOUND WHILE VERIFYING #445 (2026-08-07). That issue is about a sweep TRIGGER standing in the wrong
region; this is the same shape one level down, on ordinary checks. It surfaced because 8 members of
the Gravesite sweep (2046450800) turned out to sit on Rauh Base ground -- so a seed keeping Gravesite
without Rauh Base does not merely lose that sweep's convenience, it ships checks behind the kick.

WHAT THIS TEST IS. A RATCHET, not a clean bill. 20 mismatches and 1 ambiguous tile exist on `main`
today; they are pinned below so a NEW one fails loudly, and the pinned list may only ever SHRINK.
Each pinned row needs an in-game verdict (label `needs-playtest`) before it can be called benign --
the join says where the datamine put the item, and a datamined coordinate is not a playtest.

🛑 AND IT MEASURES LESS THAN HALF THE CORPUS. 2451 of 4916 checks resolve; the other 2465 have no
coordinate or sit on a tile with no play_region row. `test_ground_audit_coverage_is_stated_out_loud`
warns on a GREEN run, because a self-reported coverage number is not a safeguard unless something
acts on it (CONTRIBUTING rule 11) and this one is the reason the pinned set is a floor.
"""
import os
import sys
import unittest
import warnings

try:                                   # pytest (package context)
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                    # `python greenfield/eldenring/tests/test_gf_check_ground_regions.py`
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

# (event_flag, assigned_region, ground_region). NOT a benign list: each is an open question about
# which of the two regions is right, and all four look like a genuinely wrong ASSIGNMENT rather than
# a reachability bug -- "Mohgwyn :: Festering Bloody Finger - near The First Step" is a Mohgwyn
# invasion item that is picked up in Limgrave, and "Limgrave :: Hefty Cracked Pot - near Bonny Gaol"
# is a DLC gaol check filed under Limgrave. Resolve them one at a time, in game, and delete the row
# when it is settled. Adding a row here is not a fix.
#
# ⭐ SHRANK 20 -> 4 on 2026-08-09, and the reason is a DERIVATION, not a re-pin. All sixteen rows
# that left were the same defect: a check on an overworld tile with NO GRACE of its own, whose region
# ANCHOR/ANCHOR61 had nearest-neighboured onto whichever neighbour happened to hold one, while
# play_region_buckets.tsv -- the table er_logic's own kick_decision reads -- carried a row for that
# exact tile. gen_data.TILE_ROW_REGION now consults it (below the tile's own grace, above the hop),
# so the ASSIGNMENT moved onto the ground instead of the pin being deleted:
#     m61_47_39  7 checks  Cerulean  -> Charo's                    (the Nexus report, f530855)
#     m61_46_45 13 checks  Gravesite -> Rauh Base   (11 of them pinned; the #445 sweep members)
#     m60_48_51  2 checks  Altus     -> Mountaintops of the Giants
# The four that remain are NOT of that class: each sits on a tile whose region was never in doubt,
# so no tile fix can move them and only an in-game verdict can. See test_gf_tile_row_region.py.
#
# 🛑 KEYED ON THE EVENT FLAG, NOT THE ap-id. ap-ids are positional: the 2026-08-07 regen added 16
# checks and renumbered every id above 7774000, so an ap-id pin would have gone on passing while
# naming different checks. Flags are game data and do not move. (CONTRIBUTING: "whenever two
# components exchange ids, name the SPACE in the type, the key, or the comment -- and assert it.")
KNOWN_MISMATCHES = {
    (400175, "Farum Azula", "Caelid"),
    # REMOVED 2026-08-14, and the reason is the ATTRIBUTION being fixed, not an input moving under
    # it. This row was pinned as a tolerated mismatch and it was never only a mismatch: flag 66930's
    # only lot is 41010000 (m41_01 Bonny Gaol), so a LIVE Limgrave check pointed at ground inside a
    # DLC gaol. On an enable_dlc:false seed it shipped, sat on the progression surface, and could
    # have taken a Region Lock the player could never reach (#680, off Alaric's own tracker).
    # gen_data._REGION_CONFIRMED_FLAGS now sends it to Scadu Altus beside every other m41_01 check,
    # which is where the grace join said it belonged all along.
    (400036, "Mohgwyn", "Limgrave"),
    (400401, "Raya Lucaria Academy", "Caelid"),
}

# One tile (m61_47_44) carries two buckets in two regions, so the join CANNOT say which one this
# check stands in. It is reported as ambiguous and stays that way: a tile-level join guessing at a
# 3-D volume is exactly the `tile_pr()` failure CONTRIBUTING opens with.
KNOWN_AMBIGUOUS = {(2047457180, "Scadu Altus")}

# Floor for the measured subset, so the audit cannot quietly stop looking at most of the corpus.
RESOLVED_FLOOR = 2400


def _audit():
    if REPO is None:
        raise unittest.SkipTest(REPO_ONLY_REASON)
    if REPO not in sys.path:
        sys.path.insert(0, REPO)
    from tools.check_ground_regions import audit
    return audit(REPO)


class CheckGroundRegions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = _audit()

    def test_no_new_check_stands_on_ground_its_region_does_not_own(self):
        # WITNESS (test_gf_vacuous_pass): the audit must have RESOLVED a real corpus, or "no new
        # mismatches" is what a join that stopped matching says too.
        self.assertGreater(len(self.a["agree"]), 2000,
                           "the ground audit resolved almost nothing -- an empty `new` below would "
                           "then mean the join broke, not that the data is clean")
        found = {(flag, region, "/".join(str(g) for g in grounds))
                 for (flag, region, grounds, _tile, _name) in self.a["mismatch"]}
        new = found - KNOWN_MISMATCHES
        self.assertEqual(
            sorted(new), [],
            "%d NEW check(s) are assigned to a region they do not physically stand in. A seed that "
            "keeps the assigned region without the ground region CREATES these locations and then "
            "kicks the player out of the bucket they sit in (er_logic::region_lock::kick_decision). "
            "Fix the attribution -- do NOT add the row to KNOWN_MISMATCHES: %r" % (len(new), sorted(new)))

    def test_the_pinned_mismatch_list_only_shrinks(self):
        """A pin that can be edited in either direction is a pin that gets edited in the easy one."""
        found = {(flag, region, "/".join(str(g) for g in grounds))
                 for (flag, region, grounds, _tile, _name) in self.a["mismatch"]}
        gone = KNOWN_MISMATCHES - found
        if gone:
            self.fail(
                "%d pinned mismatch(es) no longer appear. That is GOOD NEWS and it still fails, "
                "because the pin must be shrunk deliberately and the reason recorded -- say whether "
                "the attribution was fixed or an INPUT changed under it (CONTRIBUTING: 'a count that "
                "grows because ground truth improved is fine; a count that grows because a predicate "
                "got looser is a bug' -- the same question runs in reverse here). Remove: %r"
                % (len(gone), sorted(gone)))

    def test_ambiguous_tiles_are_reported_not_resolved(self):
        found = {(flag, region) for (flag, region, _g, _t, _n) in self.a["ambiguous"]}
        self.assertEqual(found, KNOWN_AMBIGUOUS,
                         "the set of checks on a tile spanning two regions moved: %r" % sorted(found))

    def test_every_benign_ground_states_its_mechanism(self):
        """A benign class with no reason is how a real defect gets filed as noise."""
        from tools.check_ground_regions import BENIGN_GROUNDS
        grounds = {str(g) for (_fl, _r, gs, _t, _n) in self.a["benign"] for g in gs}
        self.assertTrue(grounds, "WITNESS: no benign grounds were seen at all")
        missing = sorted(g for g in grounds if not BENIGN_GROUNDS.get(g))
        self.assertEqual(missing, [], "benign ground(s) with no recorded reason: %r" % missing)

    def test_ground_audit_coverage_is_stated_out_loud(self):
        """The screen knows it is partial, so it says so on a GREEN run."""
        a = self.a
        resolved = len(a["agree"]) + len(a["benign"]) + len(a["mismatch"]) + len(a["ambiguous"])
        unmeasured = len(a["no_coord"]) + len(a["no_bucket_row"])
        self.assertGreaterEqual(
            resolved, RESOLVED_FLOOR,
            "the ground audit now resolves only %d checks (floor %d) -- it is looking at less of the "
            "corpus than it was, so its silence means less. Did item_grace_coords.tsv or "
            "play_region_buckets.tsv lose rows?" % (resolved, RESOLVED_FLOOR))
        warnings.warn(
            "check ground-region audit is PARTIAL: %d of %d checks resolved, %d unmeasured "
            "(%d without a datamined coordinate, %d on a tile with no play_region bucket row). "
            "The %d pinned mismatch(es) are a LOWER BOUND." % (
                resolved, resolved + unmeasured, unmeasured, len(a["no_coord"]),
                len(a["no_bucket_row"]), len(a["mismatch"])))


if __name__ == "__main__":
    unittest.main(verbosity=2)
