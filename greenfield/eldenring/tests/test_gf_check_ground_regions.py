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

WHAT THIS TEST IS. A RATCHET, not a clean bill. It opened with 20 pinned mismatches and 1 ambiguous
tile; the pinned list may only ever SHRINK, and it reached ZERO on 2026-08-26 -- see the note on
KNOWN_MISMATCHES for how each row left, because "the pin is empty" is a claim that has to say which
verdicts it rests on. An empty pin is still not a clean bill: the audit
measures under half the corpus (2284 checks are UNMEASURED, below), so it means "nothing the join
can currently see", never "nothing is wrong".

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
KNOWN_MISMATCHES = set()
# EMPTIED 2026-08-26, and an empty pin is NOT a clean bill -- the audit still measures under half
# the corpus (see the coverage warning below), so this is "nothing the join can currently see",
# not "nothing is wrong". The two rows left as follows, and neither left by being re-pinned:
#
#   (400175, "Farum Azula", "Caelid") -- the INPUT changed under it. It was pinned when its only
#   datamined coordinate was m60_52_38 (Caelid, tile-default bucket 64000), so the join could see
#   nothing but Caelid ground for a Farum Azula check. main's full-census coordinate refresh
#   (76c107e0, "updated item_grace_coords") gave the flag SIX more sites, one of which is
#   m13_00_00_00 -- Crumbling Farum Azula itself, bucket 13000, PLAY_REGION_GROUPS["Farum Azula"].
#   The disjunct-site rule (any site's ground matching suffices) now resolves it to AGREE. The
#   attribution was right all along; the corpus simply could not witness it.
#
#   (400349, "Roundtable Hold", "Limgrave") -- the same story, same commit. Pinned as D's quest
#   family, assigned to the HUB where the handover happens and datamined only at his m60_44_39
#   field station. The refresh added m11_10_00_00 (bucket 11100 = Roundtable Hold), i.e. the Hold
#   itself, so the assigned region is now among its grounds and the row AGREES.
#
# The two mismatches that same refresh CREATED were adjudicated in the same pass rather than
# pinned, which is what the test below demands:
#
#   (400036, "Mohgwyn", "Limgrave") -- assignment UPHELD, excused as SWEEP-ANCHORED. The refresh
#   measured a previously no_coord flag and the only coordinates it has are two placements of the
#   shared lot 110301 on Bloody-Finger invader NPCs (m60_35_44, m60_42_36); the award site is
#   Mohg's own m12_05 EMEVD grant, which has no MSB coordinate at all. f400036 is a member of
#   Mohg's sweep (trigger 12050800, SWEEP_ARENA_REGION "Mohgwyn"), so a Mohgwyn seed obtains it by
#   killing him -- and since #1059 made member/arena co-region a GATE, moving it onto the accusing
#   ground would BREAK test_gf_sweep_region_containment. The ruling is written out in
#   tools/check_ground_regions.RULED_SWEEP_ANCHORS[12050800].
#
#   (400220, "Roundtable Hold", "Stormveil") -- assignment WRONG, attribution fixed. The Hold was
#   never derived for this flag (legacy region_map row: map=PENDING, method=global_filler; the
#   name still said "(region unconfirmed)"; location_descriptions.tsv records that Alaric's
#   2026-08-04 pass over all 43 Golden Seeds left this one blank). Its only lot, 112200, is placed
#   on three MSB enemies -- m10_00 (Stormveil, bucket 10000) and the play_region-less Limgrave
#   tiles m60_45_38 / m60_46_36 -- none of them in the Hold. Because the HUB is in scope in every
#   seed, the Hold filing CREATED the check unconditionally while its only witnessed ground sat
#   behind the Stormveil lock: the #680 shape. gen_data.FLAG_REGION_OVERRIDE[400220] now files it
#   Stormveil, with the reason in region_overrides.tsv.
#
# 🛑 THE PROTOCOL IS UNCHANGED: a new mismatch is FIXED or RULED, never appended here. If this set
# is ever non-empty again, each row is an open question with a name on it.

# EMPTIED 2026-08-19: 2047457180's region flipped Scadu Altus -> Gravesite in the full-census
# regen (one of nine ground-truth corrections), and Gravesite is one of its m61_47_44 tile's two
# bucket regions -- the record now AGREES instead of straddling. The set stays declared so the
# next genuine tile ambiguity has a ledger to enter (the mechanism note it entered under: one tile,
# two buckets, two regions; a tile-level join must not guess at a 3-D volume).
KNOWN_AMBIGUOUS = set()

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

    def test_access_route_rulings_are_exact_and_explain_their_mechanism(self):
        """Only the two Chapel-return checks may outrank their isolated m10_01 ground."""
        from tools.check_ground_regions import RULED_ACCESS_ROUTES
        recs = self.a["access_route_ruled"]
        self.assertEqual(
            [(row[0], row[1], row[2]) for row in recs],
            [(10017010, "Liurnia", ["Stormveil"]),
             (10017900, "Liurnia", ["Stormveil"])],
            "the access-route-ruling corpus changed; adjudicate the new/vanished check rather "
            "than broadening this exception")
        self.assertEqual(set(RULED_ACCESS_ROUTES), {10017010, 10017900})
        self.assertTrue(all("Four Belfries" in reason and "Goods 8186" in reason
                            for reason in RULED_ACCESS_ROUTES.values()))

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

    def test_sweep_anchored_class_is_exactly_the_ruled_corpus(self):
        """The SWEEP-ANCHORED verdict (#885) may only excuse what a ruling covers.

        The class exists for the Golden Hippopotamus: his 48 measurable m21_00 members stand on
        Shadow Keep ground (bucket 21000) and present as Scadu Altus, the arena bucket the fight is
        fought from -- a RULING (Alaric 2026-08-19), not a mis-attribution, and every one of them is
        obtainable from Scadu Altus alone by killing him. Three witnesses keep the class honest:

          * every record's trigger must be in tools/check_ground_regions.RULED_SWEEP_ANCHORS --
            a new trigger reaching this class without its ruling being written down is a FAIL;
          * every record's ASSIGNED region must equal that trigger's arena region (the excusing
            mechanism itself, re-asserted from the outside);
          * the corpus is pinned EXACTLY. It moves only when item_grace_coords coverage or the
            Hippo's membership moves, and the bump must say what the extra one IS
            (er-sandbox-regen lesson: bumping a pin to green is only honest then).
        """
        from tools.check_ground_regions import RULED_SWEEP_ANCHORS
        recs = self.a["sweep_anchored"]
        self.assertTrue(recs, "WITNESS: the sweep-anchored class is empty -- the #885 corpus should "
                              "be here; an empty class means the join or the ruling table broke")
        triggers = {rec[5] for rec in recs}
        self.assertLessEqual(
            triggers, set(RULED_SWEEP_ANCHORS),
            "sweep-anchored record(s) from a trigger with NO written ruling: %r"
            % sorted(triggers - set(RULED_SWEEP_ANCHORS)))
        # 2026-08-26: 12050800 (Mohg, Lord of Blood) joined the Hippo, and it entered the way the
        # table demands -- with its ruling written out. One member reaches this class, f400036; the
        # adjudication is in KNOWN_MISMATCHES' note above and in RULED_SWEEP_ANCHORS itself.
        self.assertEqual(triggers, {12050800, 21000850},
                         "the ruled corpus changed shape -- a trigger was added or a ruled "
                         "trigger's members vanished: %r" % sorted(triggers))
        regions = {rec[1] for rec in recs}
        self.assertEqual(regions, {"Mohgwyn", "Scadu Altus"},
                         "a sweep-anchored check is assigned a region other than its trigger's "
                         "arena: %r" % sorted(regions))
        # PER RECORD, not just per set -- with two triggers in the table a set-level equality
        # would pass if the Hippo's members were filed Mohgwyn. Each record carries its own
        # trigger (rec[5]); its arena must be the region the check is filed in.
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "_cgr_sweeps_test", os.path.join(REPO, "greenfield", "eldenring", "boss_sweeps.py"))
        _sw = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_sw)
        crossed = [(rec[0], rec[1], rec[5], _sw.SWEEP_ARENA_REGION.get(rec[5]))
                   for rec in recs if _sw.SWEEP_ARENA_REGION.get(rec[5]) != rec[1]]
        self.assertEqual(crossed, [],
                         "a sweep-anchored check is excused by a trigger fought in a DIFFERENT "
                         "region -- the excusing mechanism does not hold for it: %r" % crossed)
        # 2026-08-19 (#330 merged under #885): 88 -> 48. The Hippo sweep shrank from 108 to 58
        # members because exactly 50 worldless Rada Fruit flags left the location corpus; all 50
        # removed members are in gen_data._RADA_WORLDLESS and no non-Rada member left. Of the 58
        # retained members, these 48 have coordinates that let this partial ground audit measure
        # them. This is source removal, not a looser SWEEP-ANCHORED predicate.
        # 2026-08-26: 48 -> 49. The one added record is Mohg's f400036 and nothing else moved --
        # the Hippo's 48 are unchanged. Named, per the rule below.
        self.assertEqual(
            len(recs), 49,
            "the measurable sweep-anchored corpus moved (48 Hippo members after #330, + Mohg's "
            "f400036 on 2026-08-26). Fine if item_grace_coords.tsv coverage or a ruled trigger's "
            "membership changed -- say which check(s) and why, then re-pin.")
        self.assertEqual(
            sorted(rec[0] for rec in recs if rec[5] == 12050800), [400036],
            "Mohg's ruling was written for ONE accused member (f400036); another of his 60 members "
            "reaching this class is a new question, not a covered one: %r"
            % sorted(rec[0] for rec in recs if rec[5] == 12050800))

    def test_sites_elsewhere_is_the_relocating_merchant_class(self):
        """The 2026-08-19 verdict for a multi-site check NONE of whose sites ground in its region.

        Every member is a RELOCATING NPC's shop/drop row -- assigned to the FIRST station by the
        merchant-ESD ground truth, datamined only at LATER stations (the Kale-family rows one tile
        over). The
        assignment is unwitnessed, not contradicted: the missing datum is the first station's
        coordinates, and promoting these to MISMATCH would accuse rows the ESD corpus places
        correctly. Pinned by count so the class cannot quietly absorb a real defect: a NEW entry is
        either a relocating NPC (re-pin with the name) or a mis-assignment wearing this class's
        clothes."""
        recs = self.a["sites_elsewhere"]
        self.assertTrue(recs, "WITNESS: the class is empty -- the relocating-merchant rows should "
                              "be here; an empty class means the join or the corpus moved")
        single = [r for r in recs if "/" not in r[3]]
        self.assertEqual(single, [],
                         "SINGLE-site record(s) entered sites_elsewhere -- those are plain "
                         "mismatches: %r" % single[:3])
        # 2026-08-31 (#331): 76 -> 22. Exactly 54 rows left this audit class when the generator
        # began honoring its already-derived multi-region merchant set: those rows now use the
        # honest HUB/defaulted fallback instead of a sibling merchant's legacy block region.
        # The remaining 22 are the two Kale-family shared inventories listed above.
        self.assertEqual(
            len(recs), 22,
            "the sites-elsewhere corpus moved (22 Kale-family rows after the 54 proven "
            "multi-region rows moved to HUB under #331). Name the new/departed rows and their NPC "
            "before re-pinning.")

    def test_ground_audit_coverage_is_stated_out_loud(self):
        """The screen knows it is partial, so it says so on a GREEN run."""
        a = self.a
        resolved = (len(a["agree"]) + len(a["benign"]) + len(a["sweep_anchored"])
                    + len(a["mismatch"]) + len(a["ambiguous"]) + len(a["sites_elsewhere"]))
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
