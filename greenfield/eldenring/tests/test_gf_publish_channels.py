#!/usr/bin/env python3
"""The publish surface: the apworld packer agrees with build.ps1, and the channel ledger is sound.

REPO-ONLY (tools/ + release/ + build.ps1 are not installed beside the world), so this is a
GENERATORS suite with a __main__ entry point.

WHY THE PACKER NEEDS A TEST AT ALL. `tools/build_apworld.py` is a SECOND builder of the same
artifact -- `build.ps1 -Apworld` is the first, and it is the one that cuts releases. Two builders is
two chances to disagree, and the disagreement would be silent: both produce a zip that installs, and
the difference would be a file that shipped to players or one that did not. So the exclusion lists
are asserted equal by reading them out of the PowerShell source. If either side changes, this reds
instead of drifting.
"""
import ast
import os
import re
import subprocess
import sys
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# 🛑 NOT `dirname(dirname(dirname(HERE)))`. gf_test.py copies this package into an AP checkout with
# no tools/ beside it, where the positional walk lands on the AP root and every path below silently
# points at the wrong tree. `_util.find_repo_root` looks for a marker instead, and there is a gate
# (test_gf_data.py::RepoRootIsNeverDerivedPositionally) that reds on the idiom -- it caught this file.
sys.path.insert(0, HERE)
from _util import find_repo_root  # noqa: E402

REPO = find_repo_root(HERE)
TOOLS = os.path.join(REPO, "tools") if REPO else None
BUILD_PS1 = os.path.join(REPO, "build.ps1") if REPO else None
REPO_ONLY = "needs the repo tree (tools/, build.ps1, release/); not installed beside the world"
HAVE_REPO = bool(REPO) and os.path.isfile(BUILD_PS1) and os.path.isdir(TOOLS)


def _load(name):
    sys.path.insert(0, TOOLS)
    try:
        return __import__(name)
    finally:
        sys.path.pop(0)


def _ps1_list(var):
    """The @('a','b') array literal assigned to $var in build.ps1, as a python list."""
    src = open(BUILD_PS1, encoding="utf-8", errors="replace").read()
    m = re.search(r"\$" + var + r"\s*=\s*@\(([^)]*)\)", src)
    if not m:
        return None
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


@unittest.skipUnless(HAVE_REPO, REPO_ONLY)
class ApworldPacker(unittest.TestCase):
    def test_exclusions_match_build_ps1(self):
        """🛑 THE ONE THAT MATTERS. build.ps1 is the release packer; this must pack the same set."""
        bp = _load("build_apworld")
        for var, ours in (("excludeName", bp.EXCLUDE_GLOB), ("excludeExact", bp.EXCLUDE_EXACT)):
            theirs = _ps1_list(var)
            self.assertIsNotNone(theirs, f"build.ps1 no longer defines ${var} -- the parity check "
                                         f"has gone blind; re-point it at whatever replaced it")
            self.assertTrue(theirs, f"${var} parsed empty from build.ps1")
            self.assertEqual(sorted(theirs), sorted(ours),
                             f"tools/build_apworld.py and build.ps1 ${var} disagree -- one of them "
                             f"would ship a file the other drops, and nothing else would say so")

    def test_pack_is_deterministic_and_rooted(self):
        bp = _load("build_apworld")
        rels = bp.members()
        self.assertTrue(rels, "nothing to pack")
        self.assertIn("archipelago.json", rels, "the manifest must be in the pack")
        self.assertIn("__init__.py", rels)
        self.assertEqual(rels, sorted(rels), "member order must be sorted (half of determinism)")
        for r in rels:
            self.assertFalse(r.endswith(".pyc"), r)
            self.assertNotIn("__pycache__", r, r)
            self.assertNotEqual(os.path.basename(r), "region_map.csv",
                                "region_map.csv is a gen INPUT copied in for the tests; shipping it "
                                "would put a test fixture in a player's download")

    def test_built_zip_has_the_ap_inner_root(self):
        """AP looks for worlds/<name>/__init__.py inside the archive; a flat zip installs to nothing."""
        import tempfile
        bp = _load("build_apworld")
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "eldenring.apworld")
            bp.build(out)
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
                first = open(out, "rb").read()
            self.assertTrue(all(n.startswith("eldenring/") for n in names),
                            "every entry must sit under the eldenring/ inner root")
            self.assertIn("eldenring/archipelago.json", names)
            # rebuild and compare bytes -- a non-deterministic artifact makes "did it change?"
            # unanswerable, and a release job cannot verify what it cannot compare.
            bp.build(out)
            self.assertEqual(first, open(out, "rb").read(), "the pack is not byte-reproducible")


@unittest.skipUnless(HAVE_REPO, REPO_ONLY)
class ChannelLedger(unittest.TestCase):
    def test_ledger_passes_its_own_gate(self):
        # WITNESS: an empty ledger passes every rule vacuously, so assert it has rows before
        # asserting they are good. Both channels must be present or the pointer points nowhere.
        cc = _load("check_channels")
        channels = {r[1] for r in cc.rows() if not r[4]}
        self.assertEqual(channels, set(cc.CHANNELS),
                         "the ledger must carry a row for every channel")
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "check_channels.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_tag_independent_violation_is_caught_at_any_checkout_depth(self):
        """The one rule that must hold even in a shallow checkout: `stable` may not name a moving
        ref. Kept separate from the tag-existence case so at least one negative is depth-proof."""
        cc = _load("check_channels")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("stable\tmain\t2026-01-01\tbogus\nbeta\tmain\t2026-01-02\t\n")
            path = f.name
        try:
            bad = cc.check(path, tags=set())
            self.assertTrue(any("only `beta`" in b for b in bad), bad)
        finally:
            os.unlink(path)

    def test_the_gate_can_actually_fail(self):
        """⭐ A gate nobody has watched fail is a gate nobody knows the shape of. Feed it a ledger
        naming a tag that does not exist and require a finding -- the failure this file exists for
        is a typo'd pointer, which parses fine and looks right."""
        cc = _load("check_channels")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("stable\tv9.9.9-not-a-tag\t2026-01-01\tbogus\nbeta\tmain\t2026-01-02\t\n")
            path = f.name
        try:
            # 🛑 TAGS ARE INJECTED, NOT TAKEN FROM THE CHECKOUT. This test passed locally and went
            # RED IN CI on 2026-08-08 for the opposite reason to the obvious one: the `tests` job
            # checks out shallow, so `git tag -l` returned nothing, the gate took its
            # no-tags-so-skip branch, found no fault, and the NEGATIVE test failed. A negative case
            # that depends on checkout depth is testing the runner, not the gate.
            bad = cc.check(path, tags={"v0.3.7"})
            self.assertTrue(bad, "the gate accepted a ledger pointing at a nonexistent tag")
            # ...and the shallow branch must be a SKIP, not a pass-by-accident that looks the same.
            self.assertFalse([b for b in cc.check(path, tags=set()) if "not a tag" in b],
                             "with no tags available the existence check must stand down, not "
                             "invent a verdict")
        finally:
            os.unlink(path)

    def test_channels_are_named_in_the_spec(self):
        spec = os.path.join(REPO, "SPEC-publishing-pipeline.md")
        self.assertTrue(os.path.isfile(spec), "the spec that explains the ledger is missing")
        text = open(spec, encoding="utf-8").read()
        self.assertIn("CHANNELS.tsv", text,
                      "the ledger exists but nothing explains it -- CONTRIBUTING rule 14")




@unittest.skipUnless(HAVE_REPO, REPO_ONLY)
class WizardDeploy(unittest.TestCase):
    """`tools/deploy_wizard.sh` + the page's own channel detection.

    The script runs on a box nobody here can see, so what is testable is its SHAPE: that it reads
    the ledger rather than taking a tag as an argument, that it installs atomically, and that it
    refuses a fetch that is not a wizard.
    """
    def _script(self):
        path = os.path.join(TOOLS, "deploy_wizard.sh")
        self.assertTrue(os.path.isfile(path), "tools/deploy_wizard.sh is missing")
        return path, open(path, encoding="utf-8").read()

    def test_it_is_ascii_and_executable(self):
        path, text = self._script()
        self.assertTrue(os.access(path, os.X_OK), "deploy_wizard.sh is not executable")
        bad = [(i + 1, ln) for i, ln in enumerate(text.splitlines()) if not ln.isascii()]
        self.assertFalse(bad, f"non-ASCII in a shell script that runs on a strange box: {bad[:3]}")

    def test_the_install_is_atomic(self):
        """🛑 A wizard is one ~2 MB file a browser can be mid-GET on. `curl -o` straight onto the
        served path serves a TRUNCATED page for the length of the download, and a half-parsed
        wizard renders as a blank panel rather than an error anyone reports."""
        _path, text = self._script()
        self.assertIn("mktemp", text)
        self.assertIn("mv -f", text)
        self.assertNotIn('curl -fsSL "${RAW}/${ref}/wizard/wizard.html" -o "$dst"', text)

    def test_latest_json_is_emitted_from_the_ledgers_atomically(self):
        """/er/latest.json feeds the client's update banner (phase 1 of the updater, 2026-08-21).
        The verdict a player sees ("safe mid-seed" vs "contract moved") is derived by comparing
        this file's `contract` to the dll's compiled hash -- so the emit must read BOTH ledgers
        (CHANNELS.tsv for the tag, CONTRACT-VERSIONS.tsv for its contract), never a typed hash,
        and must install with the same mktemp-sibling + mv discipline as every page."""
        _, script = self._script()
        # WITNESS: the block exists at all (a deleted emit must fail here, not pass vacuously).
        self.assertIn("latest.json", script)
        self.assertIn("CONTRACT-VERSIONS.tsv", script)
        self.assertIn('"$cvledger"', script)
        # The contract comes from the ledger row for the stable version -- the awk join.
        self.assertRegex(script, r'awk[^\n]*\$1==v[^\n]*print \$2')
        # Atomic: a sibling temp file, then mv onto the destination.
        self.assertRegex(script, r'mktemp "\$\{DEST\}/latest\.json\.XXXXXX\.tmp"')
        self.assertRegex(script, r'mv "\$ljtmp" "\$\{DEST\}/latest\.json"')
        # A missing ledger row DIES rather than emitting a lie.
        self.assertIn("latest.json would lie", script)
        # Stable-only artifact: both non-stable modes guard it off.
        self.assertRegex(script, r'\[ "\$BETA_ONLY" = "0" \] && \[ "\$SITE_ONLY" = "0" \]')

    def test_the_stable_tag_comes_from_the_ledger(self):
        """Not from an argument: a tag typed on the box is a second source of truth for which build
        is stable, and the two would disagree the first time someone was in a hurry."""
        _path, text = self._script()
        self.assertIn("release/CHANNELS.tsv", text)
        self.assertIn('$1=="stable"', text)

    def test_it_refuses_a_fetch_that_is_not_a_wizard(self):
        _path, text = self._script()
        self.assertIn('id="er-options-metadata"', text,
                      "the fetched file must be checked for the options blob -- a 200 from a proxy "
                      "or a ref with no wizard is not an error curl can see")

    def test_the_page_decides_its_own_channel(self):
        """The deploy script must not edit the HTML. A shell script rewriting markup it did not
        write is wrong the first time the markup moves, and silently."""
        wiz = open(os.path.join(REPO, "wizard", "wizard.html"), encoding="utf-8").read()
        self.assertIn("function currentChannel()", wiz)
        self.assertIn('id="chanbanner"', wiz)
        _path, text = self._script()
        for edit in ("sed -i", "> \"$dst\" <<", "cat >> "):
            self.assertNotIn(edit, text, f"the deploy script edits the page ({edit!r})")

    def test_baked_stable_hosts_have_an_honest_beta_only_mode(self):
        """peliarch mounts only DEST/beta. A default deploy can still support generic hosts, but
        the baked-stable command must neither fetch nor claim to install stable artifacts."""
        _path, text = self._script()
        self.assertIn("--beta-only", text)
        self.assertIn('stable -> baked image (UNTOUCHED)', text)
        self.assertIn('Stable was NOT written', text)




@unittest.skipUnless(REPO is not None, REPO_ONLY)
class SiteChannel(unittest.TestCase):
    """`deploy_wizard.sh --site` ships pages from MAIN, skipping the stable-tag pin. That is safe
    for exactly one kind of page and catastrophic for the others, so the membership is DERIVED
    from the files rather than maintained by hand.

    THE HAZARD, and it is the one SPEC-publishing-pipeline.md was written about (section 2.1,
    measured not assumed): Archipelago does NOT error on an option the installed apworld has never
    heard of. It prints one line among ~50 loader errors and generates the seed WITHOUT it. So a
    wizard shipped ahead of the released apworld does not break -- it silently ignores the setting
    a player chose, which is the worst failure this pipeline can produce.

    A page is COUPLED if it carries either marker:
        er-options-metadata   an option surface  -> must match the released apworld
        inputs_hash           a corpus join      -> describes a build's data
    A page is FREE if it carries neither: it asserts nothing about any build, so no ref can make it
    disagree with one.

    Asserted in BOTH directions on purpose. Forwards stops a coupled page being added to the fast
    path. Backwards stops a free page being silently left off it -- and, more usefully, means that
    the day landing.html grows a version stamp, THIS test fails rather than the deploy quietly
    shipping a stamped page from main forever.
    """

    def _script(self):
        return open(os.path.join(TOOLS, "deploy_wizard.sh"), encoding="utf-8").read()

    def _site_pages(self):
        """The src paths in SITE_PAGES="src:name:sentinel ..."."""
        m = re.search(r'^SITE_PAGES="([^"]*)"', self._script(), re.M)
        self.assertIsNotNone(m, "SITE_PAGES is gone from deploy_wizard.sh -- this gate now checks "
                                "nothing, which is worse than the drift it was written for.")
        return sorted(e.split(":")[0] for e in m.group(1).split() if e)

    def _installed_sources(self):
        """Every artifact the script installs, from its *_SRC assignments -- so a new page joins
        this gate by existing, not by anyone remembering to list it here."""
        srcs = set(re.findall(r'^[A-Z]+_SRC="([^"]+)"', self._script(), re.M))
        srcs |= set(self._site_pages())
        return sorted(srcs)

    @staticmethod
    def _markers(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        return ("er-options-metadata" in text), ("inputs_hash" in text)

    def test_every_site_page_is_free_of_version_and_data_stamps(self):
        for src in self._site_pages():
            path = os.path.join(REPO, src)
            self.assertTrue(os.path.isfile(path), f"SITE_PAGES names {src}, which does not exist")
            opts, data = self._markers(path)
            self.assertFalse(
                opts, f"{src} carries an OPTION SURFACE and is on the --site fast path. A wizard "
                      f"shipped from main can offer an option the released apworld has never heard "
                      f"of -- Archipelago drops it silently and the player's setting does nothing.")
            self.assertFalse(
                data, f"{src} carries a DATA STAMP (inputs_hash) and is on the --site fast path. "
                      f"It is a join over generator output, so a copy from main describes a corpus "
                      f"the released build does not have.")

    def test_every_stamp_free_page_is_on_the_site_channel(self):
        """The backwards half. Without it the set only ever shrinks by accident."""
        free = []
        for src in self._installed_sources():
            path = os.path.join(REPO, src)
            if not os.path.isfile(path):
                continue
            opts, data = self._markers(path)
            if not opts and not data:
                free.append(src)
        self.assertEqual(
            sorted(free), self._site_pages(),
            "SITE_PAGES disagrees with the files. Every page carrying neither an option surface "
            "nor a data stamp belongs on --site, and only those do. If a page just gained a stamp, "
            "take it OFF --site; if one just lost the last of its stamps, it can go on.")


@unittest.skipUnless(REPO is not None, REPO_ONLY)
class SiteTabs(unittest.TestCase):
    """The tab strip has ONE definition for the four static pages, and this pins it.

    THE SITE IS TWO KINDS OF PAGE. /downloads, /hosting and /room/<id> are Jinja templates in
    peliarch and inherit their chrome from webgui/templates/base.html. landing.html, wizard.html,
    checks.html and report.html are single files built here and installed by deploy_wizard.sh; they
    never pass through Jinja, so they cannot inherit anything. Hand-copying navigation into four
    files is four places to forget -- landing.html already hand-copies the FOOTER for exactly this
    reason, with a comment asking the next person not to drop it. wizard/tabs.js is the one
    definition for all four.

    🛑 THE STRIP THEREFORE EXISTS TWICE ACROSS TWO REPOS, and that is a deliberate trade rather
    than an oversight: a templated page whose only navigation came from a script that 404s on a box
    with no ER tooling deployed would have no navigation at all. peliarch's
    webgui/test_app.py::TestTabStrip pins the other copy, with the same six hrefs in the same
    order. If you change a tab, BOTH tests fail -- which is the point of writing the list twice.
    """

    # href order is load-bearing: the BUILDER IS FIRST because it is the only surface anyone can
    # use before deciding whether to install a DLL. Hosting is a tab, not the front page.
    HREFS = [
        "/er/", "/downloads", "/hosting", "/er/questlines.html", "/er/checks.html",
        "/er/report.html",
    ]
    # src path -> the data-tab value that page must declare
    PAGES = {
        "wizard/wizard.html": "builder",
        "wizard/report.html": "report",
        "er-archipelago-check-browser.html": "checks",
        # The landing page is the front door, reached by the wordmark; it is not one of the tabs,
        # so it declares none and the strip renders with nothing marked.
        "wizard/landing.html": "",
    }

    def _read(self, rel):
        path = os.path.join(REPO, rel)
        self.assertTrue(os.path.isfile(path), f"{rel} is missing")
        return open(path, encoding="utf-8", errors="replace").read()

    def test_tabs_js_lists_exactly_the_six_tabs_in_order(self):
        js = self._read("wizard/tabs.js")
        found = re.findall(r'\["[a-z]+",\s*"([^"]+)",\s*"[^"]+"\]', js)
        self.assertEqual(found, self.HREFS,
                         "tabs.js's TABS table disagrees with this gate. If the change is "
                         "intended, peliarch's webgui/templates/base.html and its TestTabStrip "
                         "need the same edit -- that is what the second copy is for.")

    def test_every_static_page_carries_the_placeholder_and_the_script(self):
        for rel, tab in self.PAGES.items():
            text = self._read(rel)
            self.assertIn(f'<div id="er-tabs" data-tab="{tab}"></div>', text,
                          f"{rel} has no tab strip placeholder (or the wrong data-tab)")
            self.assertIn('<script src="/er/tabs.js" defer></script>', text,
                          f"{rel} does not load /er/tabs.js")

    def test_the_placeholder_is_empty_so_a_missing_script_leaves_no_hole(self):
        """wizard.html also ships as a file:// page in the release zip, where /er/tabs.js CANNOT
        load. The placeholder must therefore render as nothing at all -- no border, no reserved
        height, no "loading" text -- and the script must no-op when the div is absent."""
        for rel in self.PAGES:
            text = self._read(rel)
            self.assertNotIn('<div id="er-tabs" ', text.replace(
                f'<div id="er-tabs" data-tab="{self.PAGES[rel]}"></div>', ""),
                f"{rel} has a second, non-empty er-tabs div")
        js = self._read("wizard/tabs.js")
        self.assertIn("if (!host) { return; }", js,
                      "tabs.js must no-op when there is no placeholder, not throw")

    def test_tabs_js_fetches_nothing(self):
        """It is chrome. A network call here would put the whole site's navigation behind a
        request that can fail, and on a file:// page it fails by construction."""
        js = self._read("wizard/tabs.js")
        for bad in ("fetch(", "XMLHttpRequest", "import(", "//cdn", "http://", "https://"):
            self.assertNotIn(bad, js, f"tabs.js reaches outside itself ({bad!r})")

    def test_the_deploy_script_installs_it(self):
        """A page nothing installs is a page nobody sees. Checked here rather than trusted."""
        script = open(os.path.join(TOOLS, "deploy_wizard.sh"), encoding="utf-8").read()
        self.assertIn('TABS_SRC="wizard/tabs.js"', script)
        self.assertIn('"${DEST}/tabs.js"', script)
        self.assertIn("wizard/tabs.js:tabs.js:er-tabs-strip", script,
                      "tabs.js carries no option surface and no data stamp, so it belongs on the "
                      "--site fast path; SiteChannel asserts that in both directions.")

    def test_the_sentinel_the_deploy_script_greps_for_is_really_in_the_file(self):
        """install_one refuses a body without its sentinel. A sentinel that is not in the file
        turns every deploy into a hard failure, and one that is in a login page too checks nothing.
        """
        self.assertIn('id="er-tabs-strip"', self._read("wizard/tabs.js"))


class LandingNumbersAreCurrent(unittest.TestCase):
    """The front page's "checks catalogued" number is a CLAIM about the corpus, and it was wrong.

    landing.html is hand-written and has no build step, so its 4,931 sat there through the Enia
    removal and every regen since -- the site told players a number the world had not defined for
    months, and nothing anywhere could notice. This is the same failure the wizard-metadata
    currency gate was written for: a literal that duplicates derived data with no gate between them
    only ever drifts one way.

    The fix is not a build step (a static page on the --site fast path is the point of that page).
    It is a MARKER plus this gate: the number lives in `data-derived="checks-catalogued"`
    attributes, and every one of them must equal the count the world actually defines. Change the
    corpus without changing the page and CI reds, in the `generators` job, before it deploys.

    TWO derivations are asserted equal, not one. wizard/region-census.json's per-region sum and the
    shipped check browser's payload length are built by different tools from the same data; if they
    ever disagree, the page's number is unanswerable and the right outcome is red, not a coin flip.

    The motivating case (Rule 11): on 2026-08-27 the page said 4,931 and the world defined 4,948.
    """

    LANDING = "wizard/landing.html"
    MARKER = "checks-catalogued"

    def _landing(self):
        return open(os.path.join(REPO, self.LANDING), encoding="utf-8").read()

    @staticmethod
    def _n(text):
        return int(text.replace(",", "").strip())

    def _derived_from_census(self):
        import json
        with open(os.path.join(REPO, "wizard", "region-census.json"), encoding="utf-8") as fh:
            return sum(v["checks"] for v in json.load(fh)["regions"].values())

    def _derived_from_check_browser(self):
        import json
        path = os.path.join(REPO, "er-archipelago-check-browser.html")
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        m = re.search(r"^const DATA = (\{.*\});$", html, re.M)
        self.assertIsNotNone(m, "the shipped check browser has no DATA payload")
        return len(json.loads(m.group(1))["checks"])

    def test_the_two_derivations_agree(self):
        census, browser = self._derived_from_census(), self._derived_from_check_browser()
        self.assertEqual(
            census, browser,
            "region-census.json and the shipped check browser disagree about how many checks "
            "exist. Both are generated from data.py, so one of them is stale -- regen before "
            "touching the landing page, because neither number can be trusted to stamp it.")

    def test_every_marked_number_equals_the_derived_count(self):
        derived = self._derived_from_census()
        marked = re.findall(r'data-derived="%s"[^>]*>([^<]+)<' % self.MARKER, self._landing())
        self.assertGreaterEqual(
            len(marked), 2,
            "landing.html has fewer than two checks-catalogued markers. The number appears in the "
            "stat strip AND in the check-browser card; a marker that vanished took its gate with "
            "it, which is how the last stale number survived.")
        for got in marked:
            self.assertEqual(
                self._n(got), derived,
                "landing.html claims %s catalogued checks; the world defines %d. Update the page "
                "(both markers) -- peliarch serves this file from main, so it is live the moment "
                "--site runs." % (got, derived))

    def test_no_unmarked_check_count_is_left_in_the_prose(self):
        """A future edit that writes the number in a new sentence without the marker would be
        invisible to the gate above, which is exactly how this drifted the first time."""
        text = self._landing()
        stripped = re.sub(r'data-derived="%s"[^>]*>[^<]+<' % self.MARKER, "", text)
        near = [m.group(0) for m in
                re.finditer(r"[\d,]{4,7}(?=[^<>]{0,60}catalogu)", stripped)]
        self.assertEqual(
            [], near,
            "landing.html states a catalogued-check count outside a "
            'data-derived="%s" marker: %r. Wrap it, or the next regen leaves it stale silently.'
            % (self.MARKER, near))


if __name__ == "__main__":
    unittest.main()
