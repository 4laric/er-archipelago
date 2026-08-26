"""Region second-opinion worksheet gate (tier A) -- tools/build_region_second_opinion_page.py.

The worksheet is a READING tool over an audit whose whole point is that nobody has ruled yet,
so its failure mode is the same as the check browser's: LYING. A page that quietly drops audit
rows would be used to conclude "we looked at all 305", and a page that split one flag's ap ids
across two rows would invite a ruling region_overrides.tsv cannot express. This gate asserts:

  A. TOTALITY -- every row of check_region_second_opinion.tsv reaches the payload exactly once,
     and every ap_id in the tsv is carried by exactly one unit. Nothing dropped, nothing
     invented, no ap_id in two units.
  B. THE UNIT IS THE FLAG -- units are keyed by flag, and the eight multi-ap-id flags come
     through as ONE unit each carrying all of their ids. This is the invariant the page exists
     to preserve; a per-row page would pass every other gate here.
  C. VERDICTS ARE CARRIED VERBATIM and every one of them has a rendered explanation. NO-DATA is
     specifically pinned as its own verdict: the audit's own suite pins "NO-DATA is not AGREE"
     and a UI that folded them would undo that at the last mile.
  D. THE ADJUDICATION SURFACE EXISTS -- all four rulings, the note field, and the TSV export
     with its header. The export is the ONLY way a reading leaves the page (a file:// page
     cannot download), so if it regressed the afternoon's work would be unrecoverable.
  E. OFFLINE -- no external script, stylesheet, image or fetch. The page ships in a repo
     checkout and is opened over file://; one <script src> would blank it.
  F. DETERMINISM + FRESHNESS -- two builds are byte-identical and the committed page equals a
     fresh build, because the CI `generators` job gates on a git diff of the committed output.

AP-FREE: reads tsvs and parses data.py's stamp with a regex; imports no world module, so this
runs in the bare sandbox with no Archipelago on sys.path.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_region_second_opinion_page.py
  or: python greenfield/eldenring/tests/test_gf_region_second_opinion_page.py
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
# 🛑 Derive greenfield paths FROM the found root, never positionally -- in CI the AP checkout
# sits INSIDE the repo, and a positional GREENFIELD resolves to `_ap/worlds/` where every tsv
# read misses. Same trap the check-browser suite documents.
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GREENFIELD = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))
GF_PKG = os.path.join(GREENFIELD, "eldenring") if _FOUND else os.path.dirname(HERE)
TOOL = os.path.join(REPO, "tools", "build_region_second_opinion_page.py")
SHIPPED = os.path.join(REPO, "er-archipelago-region-second-opinion.html")
AUDIT_TSV = os.path.join(GREENFIELD, "check_region_second_opinion.tsv")


def _load_tool():
    spec = importlib.util.spec_from_file_location("_build_rso_page", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(html):
    m = re.search(r"^const DATA = (\{.*\});$", html, re.M)
    if not m:
        raise AssertionError("built page has no embedded DATA payload")
    return json.loads(m.group(1))


def _build(out_path):
    subprocess.run([sys.executable, TOOL, "--repo", REPO, "--out", out_path],
                   check=True, stdout=subprocess.DEVNULL)
    with open(out_path, encoding="utf-8") as fh:
        return fh.read()


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class RegionSecondOpinionPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.tmp = tempfile.mkdtemp(prefix="rso_page_")
        cls.html = _build(os.path.join(cls.tmp, "a.html"))
        cls.data = _payload(cls.html)
        cls.units = cls.data["units"]
        cls.rows, _cmts = cls.tool.read_tsv(AUDIT_TSV)

    # -- A. totality -------------------------------------------------------
    def test_every_audit_row_reaches_the_payload(self):
        want = {(r["flag"], r["ap_id"]) for r in self.rows}
        got = [(str(u["flag"]), a) for u in self.units for a in u["ap_ids"]]
        self.assertEqual(len(got), len(set(got)), "an (flag, ap_id) pair is carried twice")
        self.assertEqual(set(got), want,
                         "the join dropped or invented rows: missing=%s extra=%s"
                         % (sorted(want - set(got))[:5], sorted(set(got) - want)[:5]))

    def test_row_count_is_stated_and_true(self):
        self.assertEqual(self.data["meta"]["rows"], len(self.rows))
        self.assertEqual(sum(len(u["ap_ids"]) for u in self.units), len(self.rows))

    def test_no_ap_id_appears_in_two_units(self):
        seen = {}
        for u in self.units:
            for a in u["ap_ids"]:
                self.assertNotIn(a, seen, "ap_id %s is in units %s and %s" % (a, seen.get(a), u["key"]))
                seen[a] = u["key"]

    # -- B. the adjudication unit is the FLAG ------------------------------
    def test_units_are_keyed_by_flag(self):
        keys = [u["key"] for u in self.units]
        self.assertEqual(len(keys), len(set(keys)), "two units share a key")
        self.assertEqual({u["key"] for u in self.units},
                         {"f" + str(u["flag"]) for u in self.units})
        self.assertEqual(len(self.units), len({r["flag"] for r in self.rows}))

    def test_multi_apid_flags_are_ONE_unit_carrying_all_their_ids(self):
        """The Scaled set is one flag with four ap ids. region_of decides per FLAG, so a page
        that let a reader rule on one id and not its siblings would produce an override the
        table cannot express."""
        by_flag = {}
        for r in self.rows:
            by_flag.setdefault(r["flag"], set()).add(r["ap_id"])
        multi = {f: ids for f, ids in by_flag.items() if len(ids) > 1}
        self.assertTrue(multi, "no multi-ap-id flag in the corpus -- this gate has gone vacuous")
        units = {str(u["flag"]): u for u in self.units}
        for f, ids in multi.items():
            self.assertIn(f, units)
            self.assertEqual(set(units[f]["ap_ids"]), ids)

    # -- C. verdicts -------------------------------------------------------
    def test_verdicts_are_carried_verbatim(self):
        self.assertEqual({u["verdict"] for u in self.units},
                         {r["verdict"] for r in self.rows})

    def test_every_verdict_is_ordered_and_explained(self):
        order = self.data["meta"]["verdict_order"]
        why = self.data["meta"]["verdict_why"]
        for v in {u["verdict"] for u in self.units}:
            self.assertIn(v, order, "verdict %r has no place in the group order" % v)
            self.assertTrue(why.get(v, "").strip(), "verdict %r is rendered with no explanation" % v)
        self.assertEqual(order[0], "DISAGREE", "DISAGREE must lead -- it is the only defect claim")
        self.assertEqual(order[-1], "AMBIGUOUS-GENERIC")

    def test_no_data_is_not_folded_into_agree(self):
        """The audit's own suite pins NO-DATA != AGREE. A UI that merged them would undo it."""
        self.assertIn("NO-DATA", self.data["meta"]["verdict_order"])
        self.assertNotEqual(self.data["meta"]["verdict_why"]["NO-DATA"],
                            self.data["meta"]["verdict_why"]["AGREE"])
        self.assertIn("NO-DATA", self.html)

    def test_generic_group_is_collapsed_by_default(self):
        """209 sourceless rows rendered open is how a reader starts adjudicating noise."""
        n = sum(1 for u in self.units if u["verdict"] == "AMBIGUOUS-GENERIC")
        self.assertGreater(n, 100, "the generic bucket vanished -- re-check the collapse default")
        self.assertIn('VERDICTS.filter(v => v !== "AMBIGUOUS-GENERIC")', self.html)

    def test_generic_rows_carry_no_source_and_say_why(self):
        """Their tsv `source` is EMPTY: not consulted, which is not the same as consulted and
        empty-handed. If a url ever appears on one, the audit changed and this page lies."""
        for u in self.units:
            if u["verdict"] == "AMBIGUOUS-GENERIC":
                self.assertEqual(u["url"], "", "a generic row grew a source link: %s" % u["key"])
        self.assertIn("cannot speak about one pickup",
                      self.data["meta"]["verdict_why"]["AMBIGUOUS-GENERIC"])

    # -- links -------------------------------------------------------------
    def test_every_sourced_unit_links_to_its_own_page_title(self):
        linked = [u for u in self.units if u["url"]]
        self.assertGreater(len(linked), 50, "the wiki links went missing")
        for u in linked:
            self.assertIn(u["source"], self.tool.SOURCE_BASE)
            self.assertTrue(u["url"].startswith(self.tool.SOURCE_BASE[u["source"]]))
            self.assertTrue(u["url"].endswith(u["page_title"].replace(" ", "_")))

    def test_sources_and_licenses_are_in_the_page(self):
        foot = self.data["meta"]["footer"]
        for token in ("Eldenpedia", "CC BY-SA 4.0", "Fandom", "CC BY-SA 3.0"):
            self.assertIn(token, foot, "footer does not name %s" % token)
        self.assertIn("Fextralife", foot)
        self.assertIn("not consulted", foot)

    # -- D. the adjudication surface --------------------------------------
    def test_all_four_rulings_and_the_note_field_are_rendered(self):
        vals = [p[0] for p in self.data["meta"]["adjudications"]]
        self.assertEqual(vals, ["ours-right", "wiki-right", "needs-msb", "generic-collision"])
        self.assertIn('class="note"', self.html)
        self.assertIn('type="radio"', self.html)

    def test_the_tsv_export_exists_and_its_header_is_the_contract(self):
        self.assertEqual(self.data["meta"]["export_header"],
                         ["flag", "ap_ids", "audit_verdict", "adjudication", "note"])
        self.assertIn("copy adjudications as TSV", self.html)
        self.assertIn("exportTsv", self.html)
        # the textarea, not just the clipboard: a file:// page cannot hand over a download
        self.assertIn('id="exportta"', self.html)
        self.assertIn("execCommand", self.html)

    def test_state_never_leaves_the_browser(self):
        """A worksheet that POSTed anywhere would be a different, worse thing."""
        for token in ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon",
                      "<form"):
            self.assertNotIn(token, self.html, "the page can talk to a server: %s" % token)

    # -- tile clusters -----------------------------------------------------
    def test_clusters_are_adjacent_tiles_and_never_singletons(self):
        by_id = {}
        for u in self.units:
            if u["cluster"]:
                by_id.setdefault(u["cluster"], set()).add(u["tile"])
        self.assertTrue(by_id, "no tile cluster found -- the hint is inert")
        declared = {c["id"]: c["n"] for c in self.data["meta"]["clusters"]}
        self.assertEqual(set(declared), set(by_id))
        for cid, tiles in by_id.items():
            self.assertGreater(len(tiles), 1, "%s is a singleton, not a cluster" % cid)
            self.assertEqual(declared[cid], len(tiles))
            prefixes = {t[:3] for t in tiles}
            self.assertEqual(len(prefixes), 1, "%s spans two maps: %s" % (cid, tiles))

    def test_the_cluster_hint_says_it_is_a_hint(self):
        note = self.data["meta"]["cluster_note"]
        self.assertIn("HINT", note.upper())
        self.assertIn("not a finding", note)

    # -- caveats -----------------------------------------------------------
    def test_both_tsv_headers_are_carried_verbatim(self):
        cav = self.data["meta"]["caveats"]
        self.assertTrue(cav["second_opinion"], "the audit tsv header was not carried")
        self.assertTrue(cav["triage"], "the triage tsv header was not carried")
        joined = " ".join(cav["triage"])
        self.assertIn("NOT a defect list", joined,
                      "the triage caveat lost the line that stops it being read as a bug list")

    # -- stamp -------------------------------------------------------------
    def test_stamp_is_the_data_inputs_hash_not_a_commit(self):
        stamp = self.data["meta"]["stamp"]
        self.assertTrue(stamp.startswith("sha256:"), "stamp is not a content hash: %r" % stamp)
        self.assertEqual(stamp, self.tool.data_stamp(os.path.join(GF_PKG, "data.py")))

    # -- E. offline --------------------------------------------------------
    def test_the_page_makes_no_external_request(self):
        for token in ("<script src", "<link ", "<img", "cdnjs", "@import", "url(http"):
            self.assertNotIn(token, self.html, "external asset reference: %s" % token)

    # -- F. determinism + freshness ---------------------------------------
    def test_two_builds_are_byte_identical(self):
        again = _build(os.path.join(self.tmp, "b.html"))
        self.assertEqual(len(again), len(self.html), "build length is nondeterministic")
        self.assertEqual(again, self.html,
                         "build is nondeterministic -- the CI diff gate cannot hold")

    def test_output_has_no_crlf(self):
        self.assertNotIn("\r\n", self.html, "build wrote CRLF; CI regen on Linux would diff")

    def test_committed_page_is_not_stale(self):
        if not os.path.exists(SHIPPED):
            self.skipTest("er-archipelago-region-second-opinion.html not present")
        with open(SHIPPED, encoding="utf-8", newline="") as fh:
            shipped = fh.read()
        self.assertEqual(
            shipped.replace("\r\n", "\n"), self.html,
            "committed er-archipelago-region-second-opinion.html is STALE -- "
            "run: python tools/build_region_second_opinion_page.py")

    def test_the_check_flag_agrees_with_the_freshness_assertion(self):
        """regen_all's consumers call --check; if it ever disagreed with this suite the CI
        byte-diff and the gate would point in opposite directions.

        The WITNESS is the word it printed: a --check that exited 0 because it never compared
        anything would pass a bare returncode assertion for the same reason a fresh page does."""
        run = subprocess.run([sys.executable, TOOL, "--repo", REPO, "--check"],
                             stdout=subprocess.PIPE, universal_newlines=True)
        self.assertIn("fresh:", run.stdout,
                      "--check exited without saying it compared anything: %r" % run.stdout)
        self.assertIn(os.path.basename(SHIPPED), run.stdout)
        self.assertEqual(run.returncode, 0,
                         "tools/build_region_second_opinion_page.py --check says STALE")


class VoteColumnTests(unittest.TestCase):
    """The MSB vote as the page presents it.

    WHY (rule 11 -- the motivating case is the acceptance test): the vote is a 90%-accurate
    ranking signal wearing the clothes of a measurement. Every assertion here is about a reader
    being unable to mistake it for one: the caveat is ON the page, the anchor and distance travel
    WITH the region, the tile-default anchors are badged, and a reader can filter to the rows
    where the vote disagrees -- which is the only view that changes what anyone does next.
    """

    @classmethod
    def setUpClass(cls):
        if not RUNNING_FROM_REPO:
            raise unittest.SkipTest(REPO_ONLY_REASON)
        cls._tmp = tempfile.TemporaryDirectory()
        cls.html = _build(os.path.join(cls._tmp.name, "page.html"))
        cls.payload = _payload(cls.html)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    def test_every_unit_carries_a_vote_side_even_when_there_is_no_vote(self):
        sides = {p[0] for p in self.payload["meta"]["vote_sides"]}
        for u in self.payload["units"]:
            self.assertIn(u["vote_side"], sides)
            if not u["vote_region"]:
                self.assertEqual(u["vote_side"], "none")
                self.assertTrue(u["vote_note"],
                                "unit %s has no vote and no reason" % u["flag"])

    def test_a_vote_is_classified_by_who_it_backs(self):
        for u in self.payload["units"]:
            if u["vote_side"] == "ours":
                self.assertEqual(u["vote_region"], u["our_region"])
            elif u["vote_side"] == "wiki":
                self.assertIn(u["vote_region"], u["external_regions"])
                self.assertNotEqual(u["vote_region"], u["our_region"])
            elif u["vote_side"] == "both":
                self.assertNotEqual(u["vote_region"], u["our_region"])
                self.assertNotIn(u["vote_region"], u["external_regions"])

    def test_the_region_never_travels_without_its_distance_and_anchor(self):
        """A bare region name reads as a fact. The distance and the anchoring grace are what let
        a reader disbelieve it, so the payload must never carry one without the others."""
        for u in self.payload["units"]:
            if not u["vote_region"]:
                continue
            if u["vote_ruled"]:
                # A RULING is not a vote and has no anchor to disbelieve: its falsifier is the
                # scan row, which the note names. Requiring a distance here would force the page
                # to print a nearest-grace hop that never happened.
                self.assertFalse(u["vote_distance"], "unit %s: a ruling with a hop" % u["flag"])
                self.assertFalse(u["vote_anchor"])
                self.assertIn("PLAYAREA-CONFIRMED", u["vote_note"])
                continue
            self.assertTrue(u["vote_distance"], "unit %s: vote with no distance" % u["flag"])
            self.assertTrue(u["vote_anchor"], "unit %s: vote with no anchor" % u["flag"])

    def test_a_ruling_renders_as_its_own_class_and_is_exempt_from_the_caveat(self):
        """The invariant the ruling class exists for: a PLAYAREA-CONFIRMED row must NOT read as
        a vote (its own badge class, its own note), and the accuracy caveat -- which describes a
        heuristic that cannot fail -- must SAY it does not describe this row. One caveat covering
        both answers would either slander the ruling or launder the guess."""
        ruled = [u for u in self.payload["units"] if u["vote_ruled"]]
        self.assertTrue(ruled, "no rulings -- the ruling class is an unfired guard")
        self.assertEqual(len(ruled), self.payload["meta"]["vote_ruled_count"])
        note = self.payload["meta"]["vote_ruling_note"]
        self.assertIn("PLAYAREA-CONFIRMED", note)
        self.assertIn("tile-default", note)      # says WHY a fallback is not a ruling
        self.assertIn("kick-watch", note)        # names what the id actually is
        self.assertIn("DOES NOT APPLY", self.payload["meta"]["vote_caveat"])
        self.assertIn("vote-ruled", self.html)   # the distinct class is really in the page
        self.assertIn(note[:60], self.html)
        for u in ruled:
            self.assertIn("PLAYAREA-CONFIRMED", u["vote_note"])
            self.assertTrue(u["vote_region"], "a ruling with no region is not a ruling")

    def test_the_calibration_caveat_is_rendered_on_the_page_not_only_in_the_tool(self):
        caveat = self.payload["meta"]["vote_caveat"]
        self.assertIn("ranking", caveat.lower())
        self.assertNotIn("UNKNOWN in this build", caveat,
                         "the page could not read the tool that measured the vote")
        self.assertIn("votecaveat", self.html)
        self.assertIn(caveat[:60], self.html)

    def test_the_suspect_anchor_badge_exists_and_explains_itself(self):
        suspect = [u for u in self.payload["units"] if u["vote_suspect"]]
        self.assertTrue(suspect, "no SUSPECT-ANCHOR rows -- the badge is untested (unfired "
                                 "guard = untested guard)")
        self.assertIn("SUSPECT-ANCHOR", self.html)
        self.assertIn("tile-default", self.payload["meta"]["vote_suspect_note"])
        for u in suspect:
            self.assertIn("SUSPECT-ANCHOR", u["vote_note"])

    def test_the_vote_filter_offers_the_disagrees_view(self):
        sides = dict(self.payload["meta"]["vote_sides"])
        self.assertIn("both", sides)
        self.assertIn("wiki", sides)
        self.assertIn("disagree", sides["both"].lower())
        self.assertIn('data-vs=', self.html)
        self.assertIn("state.votes", self.html)

    def test_the_vote_counts_total_the_units(self):
        self.assertEqual(sum(self.payload["meta"]["vote_counts"].values()),
                         len(self.payload["units"]))

    def test_the_vote_is_searchable_by_region_and_anchor(self):
        for u in self.payload["units"]:
            if u["vote_region"]:
                self.assertIn(u["vote_region"].lower(), u["hay"])
                self.assertIn(u["vote_anchor"].split(" ")[0].lower(), u["hay"])

    def test_the_generic_bucket_is_where_the_vote_earns_its_place(self):
        """The 209 AMBIGUOUS-GENERIC rows are the ones no wiki can speak about. If the vote did
        not reach them the column would only decorate rows that already had an opinion."""
        generic = [u for u in self.payload["units"] if u["verdict"] == "AMBIGUOUS-GENERIC"]
        voted = [u for u in generic if u["vote_region"]]
        self.assertGreater(len(voted), len(generic) // 2)

    def test_a_multi_ap_id_flag_carries_one_vote_for_all_its_ids(self):
        multi = [u for u in self.payload["units"] if len(u["ap_ids"]) > 1]
        self.assertTrue(multi, "the flag-is-the-unit fixture vanished")
        for u in multi:
            self.assertIsInstance(u["vote_region"], str)


if __name__ == "__main__":
    unittest.main()
