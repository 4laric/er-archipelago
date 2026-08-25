"""The region second-opinion audit: name parsing, area mapping, verdicts, report writer.

OFFLINE BY CONSTRUCTION. Every fixture here is synthetic -- hand-written strings shaped like
the wikitext an item page carries, never a captured page. Nothing in this suite opens a socket,
so it is safe in the `tests` job and its result never depends on a wiki being up.

WHY IT EXISTS (CONTRIBUTING rule 11, the motivating case is the acceptance test):
  * `normalize_area` must try the LONGEST alias first. "Liurnia of the Lakes" contains "liurnia";
    if the short key wins by dict order the mapping still happens to be right, but "Ancient Ruins
    of Rauh" would resolve to "Rauh Base". A containment matcher with no ordering rule is the
    silent wrong answer this repo keeps paying for.
  * `verdict_for` must say NO-DATA on an empty external set. An empty result is a FAILURE, not a
    clean run (rule 2) -- and it must never be reported as AGREE just because nothing contradicted us.
  * `is_generic` must refuse `Golden Rune [1]` WITHOUT a network call: an item with a hundred
    vanilla copies cannot adjudicate a placement, and asking anyway manufactures a verdict.
  * `regions_from_wikitext` must label a page-wide read as `page-wide`. Weak evidence that does
    not announce itself is indistinguishable from strong evidence in the report.

THE MSB VOTE (tools/msb_region_vote.py) is tested here too, on SYNTHETIC geometry -- three
hand-placed graces and a point between them, not repo data, so the assertions say what the
algorithm does rather than what the current tables happen to contain:
  * a point nearer grace A than grace B must vote A's region. That is the whole claim, and it is
    the one that would break silently if the fold or the distance ever changed frame.
  * the LOD fold must be the SHARED one. A LOD2 tile has pitch 1024 and a centring term; a vote
    that folded it at 256 would put the check 384 m from where it is and still return an answer
    (rule 1: a derivation that cannot fail). One known pair is pinned against overworld_fold.
  * a vote with no coords, or with no region-attributed grace in its frame, must SAY SO in
    vote_note rather than return a region anyway.
  * an anchor whose own region came from a tile-default row must badge SUSPECT-ANCHOR. 17 of the
    19 current votes-against ride one such grace; unbadged, they read as 17 independent findings.
"""

import importlib.util
import os
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

ROOT = find_repo_root(HERE)
AUDIT = None
if ROOT is not None:
    TOOL = os.path.join(ROOT, "tools", "audit_region_second_opinion.py")
    if os.path.isfile(TOOL):
        SPEC = importlib.util.spec_from_file_location("region_second_opinion_test", TOOL)
        AUDIT = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(AUDIT)
        if not hasattr(AUDIT, "verdict_for"):
            # An installed world may sit beside an older checkout whose tool predates this test.
            AUDIT = None

VOTE = None
if ROOT is not None:
    _VT = os.path.join(ROOT, "tools", "msb_region_vote.py")
    if os.path.isfile(_VT):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        _VS = importlib.util.spec_from_file_location("msb_region_vote_test", _VT)
        VOTE = importlib.util.module_from_spec(_VS)
        _VS.loader.exec_module(VOTE)


# Synthetic wikitext. Shaped like a MediaWiki item page; written here, not copied from one.
PAGE_WITH_SECTION = """\
{{Infobox|name=Test Blade}}
A blade used for testing.

== Acquisition ==
Found in a chest in [[Renna's Rise]] in [[Liurnia of the Lakes]].

== Notes ==
* Also mentioned near [[Caelid]] for contrast.
"""

PAGE_NO_SECTION = """\
{{Infobox|name=Test Charm}}
Dropped somewhere in [[Mt. Gelmir]].
"""

PAGE_JOURNEY = """\
== Location ==
Carried from [[Limgrave]] through [[Caelid]] and on into [[Altus Plateau]].
"""

PAGE_NO_PLACES = """\
== Acquisition ==
Sold by a [[Nomadic Merchant]].
"""


@unittest.skipUnless(AUDIT is not None, REPO_ONLY_REASON)
class ItemNameTests(unittest.TestCase):
    def test_label_yields_the_item_not_our_positional_hint(self):
        label = ("Liurnia :: Snow Witch Hat - near Royal Moongazing Grounds "
                 "(region unconfirmed) [f103451790]")
        self.assertEqual(AUDIT.item_name_from_label(label), "Snow Witch Hat")

    def test_upgrade_bracket_and_duplicate_ordinal_are_handled_differently(self):
        # A "+1" is a DIFFERENT page and must survive; a trailing "(2)" is OUR de-duplicator.
        self.assertEqual(
            AUDIT.item_name_from_label(
                "Altus :: Pearldrake Talisman +1 - near Seethewater River "
                "(region unconfirmed) [f1038527000]"),
            "Pearldrake Talisman +1")
        self.assertEqual(
            AUDIT.item_name_from_label(
                "Liurnia :: Dragon Heart - m60_33_41 (region unconfirmed) (2) [f1033417410]"),
            "Dragon Heart")

    def test_spell_prefix_is_stripped(self):
        self.assertEqual(
            AUDIT.item_name_from_label(
                "Roundtable Hold :: [Incantation] Rotten Breath (region unconfirmed) [f190040]"),
            "Rotten Breath")

    def test_generic_items_are_refused_without_a_network_call(self):
        # WITNESS: the refusal list is non-empty. Without this the assertFalse half below would
        # pass just as happily against an EMPTY GENERIC_ITEMS -- i.e. with the refusal switched
        # off entirely (test_gf_vacuous_pass's witness ratchet).
        self.assertTrue(AUDIT.GENERIC_ITEMS, "the generic-item refusal list is empty")
        for name in ("Golden Rune [1]", "golden rune [12]", "Smithing Stone [7]", "Rune Arc"):
            self.assertTrue(AUDIT.is_generic(name), name)
        for name in ("Dragonscale Blade", "Snow Witch Hat", "Pearldrake Talisman +1"):
            self.assertFalse(AUDIT.is_generic(name), name)

    def test_an_empty_item_name_is_generic_not_queryable(self):
        # A blank lot name must never become an empty wiki query that returns a stray page.
        self.assertTrue(AUDIT.is_generic(""))
        self.assertTrue(AUDIT.is_generic(None))


@unittest.skipUnless(AUDIT is not None, REPO_ONLY_REASON)
class AreaMappingTests(unittest.TestCase):
    def test_longest_alias_wins_so_a_prefix_cannot_shadow_it(self):
        self.assertEqual(AUDIT.normalize_area("Liurnia of the Lakes")[0], "Liurnia")
        self.assertEqual(AUDIT.normalize_area("Ancient Ruins of Rauh")[0], "Ancient Ruins")
        self.assertEqual(AUDIT.normalize_area("Rauh Base")[0], "Rauh Base")

    def test_case_and_trailing_punctuation_do_not_defeat_the_lookup(self):
        self.assertEqual(AUDIT.normalize_area("  CAELID.  ")[0], "Caelid")

    def test_a_recognised_non_region_is_reported_as_recognised_not_dropped(self):
        mapped, known = AUDIT.normalize_area("Roundtable Hold")
        self.assertIsNone(mapped)
        self.assertTrue(known)

    def test_an_unknown_place_is_unknown_not_a_guess(self):
        # WITNESS: the same call SAYS KNOWN for a place we do recognise. A normalize_area that
        # returned (None, False) for everything would satisfy the assertions below.
        self.assertTrue(AUDIT.normalize_area("Caelid")[1])
        mapped, known = AUDIT.normalize_area("Some Place That Does Not Exist")
        self.assertIsNone(mapped)
        self.assertFalse(known)

    def test_every_mapped_value_is_in_our_region_vocabulary(self):
        # data.py is loaded BY PATH: importing the package pulls in AP's BaseClasses, and
        # this suite must stay AP-free so it can never be the reason the job needs a world.
        spec = importlib.util.spec_from_file_location(
            "region_vocab_probe", os.path.join(ROOT, "greenfield", "eldenring", "data.py"))
        data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(data)
        regions = set(data.REGIONS)
        for alias, value in AUDIT.AREA_ALIASES.items():
            if value is not None:
                self.assertIn(value, regions, "%s -> %s is not a REGION" % (alias, value))


@unittest.skipUnless(AUDIT is not None, REPO_ONLY_REASON)
class WikitextTests(unittest.TestCase):
    def test_acquisition_section_is_preferred_and_notes_are_not_read(self):
        regions, _unmapped, scope = AUDIT.regions_from_wikitext(PAGE_WITH_SECTION)
        self.assertEqual(scope, "acquisition")
        self.assertEqual(regions, ["Liurnia"])
        self.assertNotIn("Caelid", regions)

    def test_a_page_without_the_section_is_read_whole_and_SAYS_SO(self):
        regions, _unmapped, scope = AUDIT.regions_from_wikitext(PAGE_NO_SECTION)
        self.assertEqual(scope, "page-wide")
        self.assertEqual(regions, ["Mt. Gelmir"])

    def test_no_recognised_place_yields_nothing_rather_than_a_default(self):
        # WITNESS: the fixture really does carry wikilinks. An empty result off a page with no
        # links at all would prove nothing about the mapping refusing them.
        self.assertIn("[[", PAGE_NO_PLACES)
        regions, _unmapped, _scope = AUDIT.regions_from_wikitext(PAGE_NO_PLACES)
        self.assertEqual(regions, [])

    def test_empty_input_is_empty_output(self):
        self.assertEqual(AUDIT.regions_from_wikitext("")[0], [])
        self.assertEqual(AUDIT.regions_from_wikitext(None)[2], "none")


@unittest.skipUnless(AUDIT is not None, REPO_ONLY_REASON)
class VerdictTests(unittest.TestCase):
    def test_empty_external_is_no_data_never_agree(self):
        self.assertEqual(AUDIT.verdict_for("Altus", []), "NO-DATA")

    def test_our_region_present_is_agree_even_among_alternatives(self):
        self.assertEqual(AUDIT.verdict_for("Liurnia", ["Liurnia", "Raya Lucaria Academy"]),
                         "AGREE")

    def test_our_region_absent_from_a_short_list_is_disagree(self):
        self.assertEqual(AUDIT.verdict_for("Altus", ["Mt. Gelmir"]), "DISAGREE")

    def test_a_page_naming_three_regions_is_a_journey_not_a_disagreement(self):
        regions, _u, _s = AUDIT.regions_from_wikitext(PAGE_JOURNEY)
        self.assertEqual(len(regions), 3)
        self.assertEqual(AUDIT.verdict_for("Liurnia", regions), "AMBIGUOUS")

    def test_generic_short_circuits_before_any_comparison(self):
        self.assertEqual(AUDIT.verdict_for("Altus", ["Caelid"], generic=True),
                         "AMBIGUOUS-GENERIC")


@unittest.skipUnless(AUDIT is not None, REPO_ONLY_REASON)
class ReportTests(unittest.TestCase):
    ROWS = [
        {"verdict": "AGREE", "our_region": "Liurnia", "external_regions": ["Liurnia"],
         "flag": "200", "ap_id": "2", "map_tile": "m60_33_45", "item": "Snow Witch Hat",
         "source": "eldenpedia", "page_title": "Snow Witch Hat", "scope": "acquisition",
         "how": "GUESSED", "label": "Liurnia :: Snow Witch Hat (region unconfirmed) [f200]"},
        {"verdict": "DISAGREE", "our_region": "Altus", "external_regions": ["Mt. Gelmir"],
         "flag": "100", "ap_id": "1", "map_tile": "m60_38_52", "item": "Pearldrake Talisman +1",
         "source": "eldenpedia", "page_title": "Pearldrake Talisman +1", "scope": "acquisition",
         "how": "GUESSED", "label": "Altus :: Pearldrake Talisman +1 (region unconfirmed) [f100]"},
        {"verdict": "NO-DATA", "our_region": "Caelid", "external_regions": [],
         "flag": "300", "ap_id": "3", "map_tile": "m60_51_41", "item": "Yellow Ember",
         "source": "", "page_title": "", "scope": "", "how": "GUESSED",
         "label": "Caelid :: Yellow Ember (region unconfirmed) [f300]"},
    ]

    def test_counts_cover_every_verdict_name(self):
        counts = AUDIT.summarize(self.ROWS)
        self.assertEqual(counts["AGREE"], 1)
        self.assertEqual(counts["DISAGREE"], 1)
        self.assertEqual(counts["NO-DATA"], 1)
        self.assertEqual(set(counts), set(AUDIT.VERDICTS))

    def test_tsv_puts_disagree_first_and_carries_the_licence_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.tsv")
            AUDIT.write_report(self.ROWS, path)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        head = [ln for ln in text.splitlines() if ln.startswith("#")]
        self.assertTrue(any("CC BY-SA 4.0" in ln for ln in head))
        self.assertTrue(any("Fextralife" in ln for ln in head))
        body = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
        self.assertEqual(body[0].split("\t")[0], "verdict")
        self.assertEqual(body[1].split("\t")[0], "DISAGREE")

    def test_external_regions_serialise_as_a_comma_list(self):
        rows = [dict(self.ROWS[0], external_regions=["Liurnia", "Raya Lucaria Academy"])]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.tsv")
            AUDIT.write_report(rows, path)
            with open(path, encoding="utf-8") as fh:
                line = [ln for ln in fh if ln.startswith("AGREE")][0]
        self.assertIn("Liurnia,Raya Lucaria Academy", line)

    def test_markdown_lists_every_disagree_and_says_absence_is_weak(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.md")
            AUDIT.write_markdown(self.ROWS, AUDIT.summarize(self.ROWS), path,
                                 probes=[("eldenpedia", "CC BY-SA 4.0", "REACHABLE")])
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("Pearldrake Talisman +1", text)
        self.assertIn("weak evidence", text)
        self.assertIn("Fextralife", text)

    def test_markdown_says_none_rather_than_printing_an_empty_table(self):
        rows = [self.ROWS[0]]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.md")
            AUDIT.write_markdown(rows, AUDIT.summarize(rows), path)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("## DISAGREE\n\nNone.", text)


@unittest.skipUnless(VOTE is not None, REPO_ONLY_REASON)
class VoteGeometryTests(unittest.TestCase):
    """Synthetic geometry. No repo table is read; every coordinate is placed here by hand."""

    # Two graces on one fine-grid tile, 100 m apart in x. Nothing else is on this tile.
    GRACES = [
        ("9001", "m60_40_40_00", 10.0, 0.0, 0.0, "Grace A"),
        ("9002", "m60_40_40_00", 110.0, 0.0, 0.0, "Grace B"),
        ("9003", "m41_00", 0.0, 0.0, 0.0, "Interior Grace"),
    ]
    REGIONS = {"9001": "Limgrave", "9002": "Caelid", "9003": "Ainsel River"}

    def voter(self, items, suspect=()):
        return VOTE.Voter(items, self.GRACES, self.REGIONS, suspect)

    def test_a_point_nearer_grace_a_than_grace_b_votes_a_region(self):
        v = self.voter({"1": ("m60_40_40_00", 20.0, 0.0, 0.0)}).vote("1")
        self.assertEqual(v.region, "Limgrave")
        self.assertEqual(v.anchor_grace, "9001")
        self.assertAlmostEqual(v.distance_m, 10.0, places=3)

    def test_the_same_point_moved_past_the_midpoint_votes_b_instead(self):
        """The MIRROR of the test above: prove the vote MOVES. A voter hard-wired to return the
        first grace would pass the previous assertion for the wrong reason."""
        v = self.voter({"1": ("m60_40_40_00", 100.0, 0.0, 0.0)}).vote("1")
        self.assertEqual(v.region, "Caelid")
        self.assertEqual(v.anchor_grace, "9002")

    def test_top_three_unanimity_is_reported_not_assumed(self):
        split = self.voter({"1": ("m60_40_40_00", 20.0, 0.0, 0.0)}).vote("1")
        self.assertFalse(split.unanimous)      # A is Limgrave, B is Caelid
        same = VOTE.Voter({"1": ("m60_40_40_00", 20.0, 0.0, 0.0)}, self.GRACES,
                          dict(self.REGIONS, **{"9002": "Limgrave"})).vote("1")
        self.assertTrue(same.unanimous)

    def test_the_lod_fold_is_the_shared_one_not_a_local_reimplementation(self):
        """m60_10_10_02 is a LOD2 tile: pitch 1024, centring term (1024-256)/2 = 384. A local
        fold at *256 would answer too -- with a point 3 km away (issue #338's exact shape)."""
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import overworld_fold
        self.assertEqual(overworld_fold.world_xz("m60_10_10_02", 0.0, 0.0),
                         ("m60", 10 * 1024 + 384.0, 10 * 1024 + 384.0))
        frame, point = VOTE.fold("m60_10_10_02", 0.0, 5.0, 0.0)
        self.assertEqual(frame, "m60")
        self.assertEqual((point[0], point[2]), (10624.0, 10624.0))
        # and the fine tile that covers that world position folds to the SAME neighbourhood
        self.assertEqual(VOTE.fold("m60_41_41_00", 128.0, 5.0, 128.0)[0], "m60")

    def test_a_coarse_lod_row_is_noted_because_the_position_is_coarser(self):
        v = self.voter({"1": ("m60_10_10_02", 0.0, 0.0, 0.0)}).vote("1", "m60_10_10")
        self.assertIn(VOTE.NOTE_COARSE, v.notes)

    def test_no_coords_says_so_and_returns_no_region(self):
        v = self.voter({}).vote("404")
        self.assertIsNone(v.region)
        self.assertEqual(v.notes, [VOTE.NOTE_NO_COORDS])
        self.assertEqual(v.as_columns()["msb_vote_region"], "")
        self.assertEqual(v.as_columns()["vote_distance_m"], "")

    def test_a_frame_with_no_region_attributed_grace_votes_nothing(self):
        """An interior map with no attributed grace must NOT reach across to the overworld and
        answer from 40 km away. An empty candidate list is a FAILURE, not a clean run (rule 2)."""
        v = VOTE.Voter({"1": ("m30_00", 0.0, 0.0, 0.0)}, self.GRACES, self.REGIONS).vote("1")
        self.assertIsNone(v.region)
        self.assertIn(VOTE.NOTE_NO_ANCHOR, v.notes)

    def test_an_interior_frame_votes_only_within_its_own_map(self):
        v = VOTE.Voter({"1": ("m41_00", 1.0, 0.0, 0.0)}, self.GRACES, self.REGIONS).vote("1")
        self.assertEqual(v.region, "Ainsel River")

    def test_a_tile_default_anchor_is_badged_suspect_not_dropped(self):
        v = self.voter({"1": ("m60_40_40_00", 20.0, 0.0, 0.0)}, suspect={"9001"}).vote("1")
        self.assertEqual(v.region, "Limgrave")            # still answered
        self.assertIn(VOTE.NOTE_SUSPECT, v.notes)         # and still flagged

    def test_several_placements_pick_the_closest_and_SAY_they_chose(self):
        """442 flags in item_grace_coords.tsv are placed more than once. Taking whichever row was
        read last would pick a winner by file order and never mention it (rule 4)."""
        v = self.voter({"1": [("m60_40_40_00", 108.0, 0.0, 0.0),      # 2 m from B
                              ("m60_40_40_00", 30.0, 0.0, 0.0)]}).vote("1")
        self.assertEqual(v.region, "Caelid")                 # the CLOSEST anchor wins
        self.assertIn(VOTE.NOTE_MULTI, v.notes)
        self.assertIn("MULTI-PLACEMENT-SPLIT", v.notes)      # the two placements disagreed

    def test_duplicate_placements_at_the_same_folded_point_are_not_a_split(self):
        """The `_00`/`_10` MSB version pair is the SAME point. The fold ignores the version digit,
        so it must not manufacture a MULTI-PLACEMENT note out of one placement."""
        v = self.voter({"1": [("m60_40_40_00", 20.0, 0.0, 0.0),
                              ("m60_40_40_10", 20.0, 0.0, 0.0)]}).vote("1")
        self.assertEqual(v.region, "Limgrave")
        self.assertNotIn(VOTE.NOTE_MULTI, v.notes)

    def test_coords_authored_on_another_fine_tile_are_noted_as_cross_tile(self):
        v = self.voter({"1": ("m60_40_40_00", 20.0, 0.0, 0.0)}).vote("1", "m60_51_41")
        self.assertIn(VOTE.NOTE_CROSS_TILE, v.notes)
        same = self.voter({"1": ("m60_40_40_00", 20.0, 0.0, 0.0)}).vote("1", "m60_40_40")
        self.assertNotIn(VOTE.NOTE_CROSS_TILE, same.notes)


@unittest.skipUnless(VOTE is not None and AUDIT is not None, REPO_ONLY_REASON)
class VoteWiringTests(unittest.TestCase):
    """The vote as it reaches the report -- columns, header, and the committed numbers."""

    def test_the_report_declares_the_vote_columns(self):
        for col in VOTE.VOTE_COLUMNS:
            self.assertIn(col, AUDIT.REPORT_COLUMNS)

    def test_a_run_without_a_voter_writes_blank_cells_rather_than_dying(self):
        rows = [dict(r) for r in ReportTests.ROWS]     # no msb_vote_* keys at all
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.tsv")
            AUDIT.write_report(rows, path)
            with open(path, encoding="utf-8") as fh:
                body = [ln for ln in fh if not ln.startswith("#") and ln.strip()]
        header = body[0].rstrip("\n").split("\t")
        self.assertEqual(header[-5:], VOTE.VOTE_COLUMNS)
        self.assertEqual(body[1].rstrip("\n").split("\t")[-5:], ["", "", "", "", ""])

    def test_the_tsv_header_carries_the_calibration_verbatim(self):
        """A number that travels without its caveat becomes an authority. The header must say
        the accuracy IN THE FILE, not only in the tool that wrote it."""
        self.assertIn(VOTE.CALIBRATION, AUDIT.REPORT_HEADER)

    def test_the_committed_report_has_the_vote_columns_populated(self):
        path = os.path.join(ROOT, "greenfield", "check_region_second_opinion.tsv")
        with open(path, encoding="utf-8") as fh:
            body = [ln.rstrip("\n") for ln in fh if not ln.startswith("#") and ln.strip()]
        header = body[0].split("\t")
        rows = [dict(zip(header, ln.split("\t"))) for ln in body[1:]]
        cast = [r for r in rows if r["msb_vote_region"]]
        against = [r for r in cast if r["msb_vote_region"] != r["our_region"]]
        # Re-measured 2026-08-25 against this tsv. These move when the audit is re-run: update
        # them WITH the regenerated table, never by loosening the assertion.
        self.assertEqual(len(rows), 305)
        self.assertEqual(len(cast), 260)
        self.assertEqual(len(against), 19)
        self.assertTrue(all(r["vote_note"] for r in rows if not r["msb_vote_region"]),
                        "a row with no vote must say WHY in vote_note")
        suspect = [r for r in against if VOTE.NOTE_SUSPECT in r["vote_note"]]
        self.assertEqual(len(suspect), 17,
                         "the Yelough Anix Tunnel cluster must stay visible as ONE anchor")

    def test_the_calibration_number_is_still_true_of_this_repo(self):
        """Rule 7's mirror: the sentence in CALIBRATION is re-derivable, so it cannot rot into a
        remembered number. The floor is deliberately BELOW the measured 90.1% -- this pins that
        the vote is a usable ranking signal, not that it never moves."""
        hits, misses, _families = VOTE.calibrate(ROOT)
        total = hits + misses
        self.assertGreater(total, 2000, "control set collapsed -- the vote is unmeasured")
        self.assertGreater(100.0 * hits / total, 85.0)
        self.assertLess(100.0 * hits / total, 100.0,
                        "a 100%% control score means the control set is the vote's own output")


if __name__ == "__main__":
    unittest.main()
