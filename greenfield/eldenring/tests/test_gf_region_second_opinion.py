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


if __name__ == "__main__":
    unittest.main()
