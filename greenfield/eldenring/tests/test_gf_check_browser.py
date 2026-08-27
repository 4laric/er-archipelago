"""Check-browser gate (tier A) -- tools/build_check_browser.py.

The browser is a READING tool for the check corpus, so its only real failure mode is
LYING: showing a set of checks, tags or counts that the world does not actually define.
A reader that silently drops rows is worse than no reader, because it is then used to
reason about coverage. This gate asserts the join is total and the shipped page is fresh:

  A. TOTALITY -- every (name, ap_id, flag) in data.LOCATIONS appears exactly once in the
     page payload, and the payload contains nothing else. A join that drops or duplicates
     rows fails here rather than being discovered by eye.
  B. AGREEMENT -- the tag histogram recomputed from the payload equals location_tags.
     TAG_COUNTS, and every missable ap_id is carried. This is the same cross-check that
     caught nothing when written, and is exactly what a future tag rename would break.
  C. DETERMINISM -- two builds from the same inputs are byte-identical. Required, because
     the CI `generators` job gates on a git diff of the committed output; a nondeterministic
     build (dict order, a git hash, CRLF) would make that gate permanently red.
  D. FRESHNESS -- the committed er-archipelago-check-browser.html equals a fresh build.
     Catches "changed the data, never regenerated the page".

AP-FREE: the tool reads the generated modules with ast, never imports them, so this test
needs no Archipelago on sys.path and runs in the bare sandbox.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_check_browser.py
  or: python greenfield/eldenring/tests/test_gf_check_browser.py
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
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
# 🛑 Derive greenfield paths FROM the found root, never positionally. In CI the AP
# checkout `_ap/` sits INSIDE the repo, so find_repo_root succeeds and these suites
# RUN there -- but a positional GREENFIELD then resolves to `_ap/worlds/` and every
# tsv read misses. That is the second half of the 2026-07-27 path bug: fixing REPO
# alone moved 45 errors to 3 failures instead of to 0.
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GREENFIELD = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))
GF_PKG = os.path.join(GREENFIELD, "eldenring") if _FOUND else os.path.dirname(HERE)
TOOL = os.path.join(REPO, "tools", "build_check_browser.py")
SHIPPED = os.path.join(REPO, "er-archipelago-check-browser.html")


def _load_tool():
    spec = importlib.util.spec_from_file_location("_build_check_browser", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(html):
    """Pull the embedded JSON back out of a built page."""
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
class CheckBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.tmp = tempfile.mkdtemp(prefix="check_browser_")
        cls.html = _build(os.path.join(cls.tmp, "a.html"))
        cls.data = _payload(cls.html)
        cls.checks = cls.data["checks"]
        consts = cls.tool.load_module_consts(
            os.path.join(GF_PKG, "data.py"), {"LOCATIONS"})
        cls.LOCATIONS = consts["LOCATIONS"]

    # -- A. totality ------------------------------------------------------
    def test_every_location_present_exactly_once(self):
        want = {(a, f, r) for r, v in self.LOCATIONS.items() for (_n, a, f) in v}
        got = Counter((c["id"], c["f"], c["r"]) for c in self.checks)
        dupes = {k: n for k, n in got.items() if n > 1}
        self.assertFalse(dupes, f"payload duplicates {len(dupes)} check(s): {list(dupes)[:5]}")
        missing = want - set(got)
        extra = set(got) - want
        self.assertFalse(missing, f"{len(missing)} location(s) dropped by the join: {sorted(missing)[:5]}")
        self.assertFalse(extra, f"{len(extra)} check(s) invented by the join: {sorted(extra)[:5]}")

    def test_meta_total_matches(self):
        self.assertEqual(self.data["meta"]["total"], len(self.checks))
        self.assertEqual(len(self.checks), sum(len(v) for v in self.LOCATIONS.values()))

    # -- B. agreement with the generated modules ---------------------------
    def test_tag_histogram_matches_TAG_COUNTS(self):
        declared = self.tool.load_module_consts(
            os.path.join(GF_PKG, "location_tags.py"), {"TAG_COUNTS"})["TAG_COUNTS"]
        got = Counter(t for c in self.checks for t in c["t"])
        self.assertEqual(dict(sorted(got.items())), dict(sorted(declared.items())))

    def test_every_missable_is_carried(self):
        declared = self.tool.load_module_consts(
            os.path.join(GF_PKG, "missable_locations.py"), {"MISSABLE_LOCATIONS"})["MISSABLE_LOCATIONS"]
        got = {c["id"]: c["miss"] for c in self.checks if "miss" in c}
        self.assertEqual(got, dict(declared))

    def test_stamp_is_the_data_inputs_hash_not_a_commit(self):
        stamp = self.data["meta"]["stamp"]
        self.assertTrue(stamp.startswith("sha256:"), f"stamp is not a content hash: {stamp!r}")
        self.assertEqual(stamp, self.tool.data_stamp(os.path.join(GF_PKG, "data.py")))

    # -- C. determinism ----------------------------------------------------
    def test_two_builds_are_byte_identical(self):
        again = _build(os.path.join(self.tmp, "b.html"))
        self.assertEqual(len(again), len(self.html), "build length is nondeterministic")
        self.assertEqual(again, self.html, "build is nondeterministic -- the CI diff gate cannot hold")

    def test_output_has_no_crlf(self):
        self.assertNotIn("\r\n", self.html, "build wrote CRLF; CI regen on Linux would diff")

    # -- E. gate evidence is PLURAL ----------------------------------------
    # The page previously showed only lot_gates, teaching the reader "110 of 4879 checks
    # are gated". Four corpora document gating and their union is 684. These gates keep
    # the other three joined AND keep their caveats in the payload, because a UI that
    # flattens NO_ENTITY_HANDLE ("proof of no gating") into "gated: unknown" inverts it.
    def test_all_four_gate_corpora_reach_the_payload(self):
        for key, tsv in (("gates", "lot_gates.tsv"), ("enab", "treasure_enablers.tsv"),
                         ("gift", "esd_gifts.tsv"), ("eshop", "esd_gates.tsv")):
            n = sum(1 for c in self.checks if c.get(key))
            self.assertTrue(n > 0, f"no check carries {key} -- the {tsv} join is broken")

    def test_enabler_join_matches_the_tsv(self):
        """treasure_enablers.tsv states its own distinct-check count in its header."""
        rows = self.tool.read_tsv(os.path.join(GREENFIELD, "treasure_enablers.tsv"))
        want = {int(r["flag"]) for r in rows if r.get("flag", "").isdigit()}
        got = {c["f"] for c in self.checks if c.get("enab")}
        self.assertEqual(got, want & {c["f"] for c in self.checks})

    def test_enabler_verdicts_are_carried_verbatim(self):
        """Never normalise a verdict string: the UI facets on it and the caveat text
        explains it by that exact name."""
        rows = self.tool.read_tsv(os.path.join(GREENFIELD, "treasure_enablers.tsv"))
        want = {r["verdict"] for r in rows if r.get("verdict")}
        got = {e["verdict"] for c in self.checks for e in c.get("enab", []) if e["verdict"]}
        self.assertEqual(got, want)
        self.assertIn("NO_ENTITY_HANDLE", got, "the 'proof of no gating' verdict vanished")

    def test_caveat_headers_are_present_and_not_paraphrased(self):
        cav = self.data["meta"]["caveats"]
        for k in ("treasure_enablers", "esd_gates", "esd_gifts", "msb_gated_treasures", "lot_gates"):
            self.assertTrue(cav.get(k, "").strip(), f"no caveat text carried for {k}")
        # the specific warnings that stop a misread -- if the header is reworded, re-check the UI
        self.assertIn("NO_ENTITY_HANDLE", cav["treasure_enablers"])
        self.assertIn("POLARITY IS NOT ENCODED", cav["treasure_enablers"])
        self.assertIn("NOT A RISK LIST", cav["msb_gated_treasures"].upper())

    def test_gate_union_is_not_a_sum(self):
        """The corpora overlap; the footer shows a union. If this ever equals the sum,
        someone has double-counted."""
        m = self.data["meta"]
        parts = m["gate_lot"] + m["gate_enabler"] + m["gate_gift"] + m["gate_eshop"]
        self.assertLessEqual(m["gate_any"], parts)
        self.assertGreater(m["gate_any"], m["gate_lot"],
                           "union is no bigger than lot_gates alone -- the new joins are inert")

    # -- F. negative space --------------------------------------------------
    def test_residuals_are_present_and_disjoint_from_checks(self):
        res = self.data["residuals"]
        self.assertTrue(len(res) > 0)
        check_flags = {c["f"] for c in self.checks}
        bad = [r for r in res if r["k"].startswith("itemlot") and r["f"] in check_flags]
        self.assertFalse(bad, f"{len(bad)} residual(s) are actually checks: {bad[:3]}")

    def test_residual_reasons_are_recorded_or_honestly_blank(self):
        """A fabricated reason is the disease this view exists to cure. Blank is allowed;
        a non-string is not."""
        for r in self.data["residuals"]:
            self.assertIsInstance(r["reason"], str)

    # -- G. the map tab ----------------------------------------------------
    # A point placed off-image is invisible; a point placed WRONG is worse, because the
    # map is used to eyeball misregioned checks and a wrong dot invents an outlier.
    def test_every_plotted_point_lands_inside_its_map(self):
        cal = self.data["meta"]["cal"]
        self.assertTrue(cal, "no calibration carried -- the map tab has nothing to project with")
        boxes = {}
        for key, svg in (("m60", "lands_between_map.svg"), ("m61", "land_of_shadow_map.svg")):
            with open(os.path.join(REPO, "poptracker", "maps", svg), encoding="utf-8") as fh:
                m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', fh.read(400))
            boxes[key] = (float(m.group(1)), float(m.group(2)))
        oob, n = [], 0
        for c in self.checks:
            for p in c.get("pos", []):
                k = cal.get(p["b"])
                if not k:
                    continue
                wb, im = k["world_bounds"], k["image"]
                px = im["margin"] + (p["gx"] - wb["gx_min"]) / (wb["gx_max"] - wb["gx_min"]) * im["draw_w"]
                py = im["margin"] + (1 - (p["gz"] - wb["gz_min"]) / (wb["gz_max"] - wb["gz_min"])) * im["draw_h"]
                W, H = boxes[p["b"]]
                n += 1
                if not (0 <= px <= W and 0 <= py <= H):
                    oob.append((c["f"], p["b"], round(px), round(py)))
        self.assertTrue(n > 1500, f"only {n} points -- the coord join went missing")
        self.assertFalse(oob, f"{len(oob)} of {n} points land OFF the map: {oob[:5]}")

    def test_dlc_calibration_is_not_the_base_one(self):
        """m61 has its own bounds and draw_h. Projecting DLC through the base transform
        would put every Shadow-Realm check in the sea, plausibly enough to be believed."""
        cal = self.data["meta"]["cal"]
        self.assertIn("m61", cal)
        self.assertNotEqual(cal["m60"]["world_bounds"], cal["m61"]["world_bounds"])

    def test_map_positions_are_deduped_across_map_versions(self):
        for c in self.checks:
            keys = [(p["b"], round(p["gx"]), round(p["gz"])) for p in c.get("pos", [])]
            self.assertEqual(len(keys), len(set(keys)), f"f{c['f']} has duplicate positions")

    def test_plottable_count_matches_the_payload(self):
        self.assertEqual(self.data["meta"]["plottable"],
                         sum(1 for c in self.checks if c.get("pos")))
        # the map must NOT silently imply full spatial coverage
        self.assertLess(self.data["meta"]["plottable"], self.data["meta"]["total"],
                        "every check claims a position -- interiors should have none")

    def test_both_maps_are_inlined(self):
        """The page is offline; an <img src> or a CDN would make the map tab blank."""
        for token in ("lands_between", "land_of_shadow"):
            self.assertIn(token, self.html, f"{token} map not inlined")
        self.assertNotIn("cdnjs", self.html)
        self.assertNotIn("<img", self.html)

    # -- H. diff mode is a REVIEW AID, not a gate --------------------------
    def test_payload_is_reparseable_by_the_diff_loader(self):
        """Diff mode re-extracts a payload from another build with this exact regex; if
        the emitted shape ever stops matching it, diff silently loads nothing."""
        m = re.search(r"^const DATA = (\{.*\});$", self.html, re.M)
        self.assertIsNotNone(m, "diff mode's loader regex no longer matches our own output")
        again = json.loads(m.group(1))
        self.assertEqual(len(again["checks"]), len(self.checks))
        for k in ("id", "r", "n", "t", "f", "g"):
            self.assertIn(k, again["checks"][0], f"diff keys on {k}; it left the payload")

    def test_diff_mode_is_labelled_as_not_a_gate(self):
        self.assertIn("review aid", self.html)
        self.assertIn("not a gate", self.html)

    # -- D. freshness ------------------------------------------------------
    def test_committed_page_is_not_stale(self):
        if not os.path.exists(SHIPPED):
            self.skipTest("er-archipelago-check-browser.html not present")
        with open(SHIPPED, encoding="utf-8", newline="") as fh:
            shipped = fh.read()
        self.assertEqual(
            shipped.replace("\r\n", "\n"), self.html,
            "committed er-archipelago-check-browser.html is STALE -- "
            "run: python tools/build_check_browser.py")


TEMPLATE = os.path.join(REPO, "tools", "check_browser_template.html")
ISSUE_FORM = os.path.join(REPO, ".github", "ISSUE_TEMPLATE", "check-report.yml")
NODE = None
for _cand in ("node", "nodejs"):
    try:
        subprocess.run([_cand, "--version"], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        NODE = _cand
        break
    except (OSError, subprocess.CalledProcessError):
        pass


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class ReportAProblemLink(unittest.TestCase):
    """Every check row can open a PREFILLED GitHub issue about itself (Alaric, 2026-08-27).

    A static page cannot POST, and we are not adding a backend to collect bug reports. The whole
    mechanism is a plain <a href> to github.com's new-issue form with query parameters -- a
    NAVIGATION, so the self-contained-page rule is untouched: the page still fetches nothing.

    Rule 11, the motivating case: a player finds the check that misbehaved in the browser, clicks
    one link, and lands on a GitHub issue form that already knows which check it is, which region
    it was assigned, which map tile it sits on and how that region was decided -- none of which the
    player could be expected to supply, and all of which triage needs before it can start.

    WHAT THIS GATE IS FOR. The link is built by string concatenation in JS, so its failure mode is
    a URL that LOOKS fine and is wrong: an unescaped `&` in a check name truncating the body, a
    template filename that no longer exists, a field id renamed on one side only. None of those
    show up as an error anywhere -- the player just gets a half-empty form, or GitHub's 404. So:
    the URL is evaluated under node from the SHIPPED page, parsed as a URL, and its parameter names
    are checked against the ids in the issue form itself.

    🛑 Only `input` and `textarea` fields prefill from a URL query -- that is the whole of what
    GitHub documents ("Creating an issue from a URL query" + the form-schema `id` key). So the gate
    asserts every prefilled parameter names a TEXT field. The `symptom` dropdown is deliberately
    not prefilled: the browser does not know what happened to the player.
    """

    @classmethod
    def setUpClass(cls):
        with open(SHIPPED, encoding="utf-8") as fh:
            cls.page = fh.read()
        with open(TEMPLATE, encoding="utf-8") as fh:
            cls.tpl = fh.read()

    def _form(self):
        import yaml
        with open(ISSUE_FORM, encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    # -- the page carries the link -----------------------------------------
    def test_the_template_emits_a_report_link_for_every_row(self):
        self.assertIn('class="rep2"', self.tpl,
                      "the report link is gone from the detail pane; a check browser that cannot "
                      "report a check is the thing this gate exists to prevent")
        self.assertIn("checkReportUrl", self.tpl)
        self.assertIn("const REPORT_TEMPLATE='check-report.yml'", self.tpl,
                      "the issue-form filename is no longer a single named constant, so the gate "
                      "below can no longer tell whether the page and the form agree")

    def test_the_shipped_page_carries_it_too(self):
        """The template is the source, the shipped page is what peliarch serves. A gate on the
        template alone passes happily while the deployed page is a regen behind."""
        self.assertIn("checkReportUrl", self.page)
        self.assertIn("check-report.yml", self.page)

    def test_the_page_still_fetches_nothing_at_load(self):
        """github.com appears in the page as a link target only. A `fetch` to it would break the
        self-contained rule and leak every reader's view."""
        for bad in ("fetch(", "XMLHttpRequest", "new WebSocket"):
            self.assertNotIn(bad, self.page,
                             f"{bad} appeared in the check browser; the page is served from a file "
                             f"and must make no requests on load")

    # -- the URL is well formed --------------------------------------------
    @unittest.skipUnless(NODE, "needs node to evaluate the page's own URL builder")
    def test_the_url_is_well_formed_for_sampled_rows(self):
        """Evaluated under node, from the shipped page's OWN source -- not a python re-write of it.
        A test that reimplemented the builder would agree with itself and prove nothing.

        The sample is deliberately not random: the first row, the last row, and every row whose
        name carries a character that has broken a query string before -- `&`, `#`, `+`, `%`, a
        quote, a comma, a non-ASCII dash.
        """
        harness = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const m = src.match(/^const DATA = (\{.*\});$/m);
const DATA = JSON.parse(m[1]);
const CHECKS = DATA.checks, META = DATA.meta;
const REPO = 'https://github.com/4laric/er-archipelago';
const location = {href: 'https://peliarch.ca/er/checks.html#q=&id=1'};
// the two builders, lifted verbatim out of the page
function grab(name){
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('no function ' + name);
  let d = 0, j = src.indexOf('{', i);
  for (let k = j; k < src.length; k++){
    if (src[k] === '{') d++;
    else if (src[k] === '}') { d--; if (!d) return src.slice(i, k + 1); }
  }
  throw new Error('unbalanced ' + name);
}
const constLine = src.match(/^const REPORT_TEMPLATE=.*$/m);
if (!constLine) throw new Error('no REPORT_TEMPLATE constant in the page');
eval(constLine[0] + '\n' + grab('tileMates') + '\n' + grab('checkFacts') + '\n' + grab('checkReportUrl'));
const risky = c => /[&#+%'",–—]/.test(c.full || '');
const pick = new Set([CHECKS[0], CHECKS[CHECKS.length - 1]]);
let n = 0;
for (const c of CHECKS) { if (risky(c) && n++ < 60) pick.add(c); }
const out = [];
for (const c of pick) out.push({id: c.id, full: c.full, url: checkReportUrl(c)});
process.stdout.write(JSON.stringify({risky: n, rows: out}));
"""
        with tempfile.TemporaryDirectory() as tmp:
            hp = os.path.join(tmp, "h.js")
            with open(hp, "w", encoding="utf-8") as fh:
                fh.write(harness)
            res = subprocess.run([NODE, hp, SHIPPED], capture_output=True, text=True)
        self.assertEqual(0, res.returncode, res.stderr[-2000:])
        got = json.loads(res.stdout)
        self.assertGreater(got["risky"], 0,
                           "no check name in the corpus carries a query-hostile character, so the "
                           "escaping half of this gate witnessed nothing. Widen the sample.")
        ids = {b.get("id") for b in self._form()["body"] if b.get("id")}
        try:                                   # py3.9+: the stdlib parser is the arbiter, not a regex
            from urllib.parse import urlsplit, parse_qs
        except ImportError:                    # pragma: no cover
            raise
        for row in got["rows"]:
            u = urlsplit(row["url"])
            self.assertEqual("https", u.scheme, row["url"][:120])
            self.assertEqual("github.com", u.netloc, row["url"][:120])
            self.assertEqual("/4laric/er-archipelago/issues/new", u.path)
            q = parse_qs(u.query, keep_blank_values=True, strict_parsing=True)
            self.assertEqual({"template", "title", "check", "facts"}, set(q),
                             f"unexpected query parameters for check {row['id']}")
            self.assertEqual(["check-report.yml"], q["template"])
            # the round trip is the point: whatever was in the name comes back out intact
            self.assertIn(row["full"], q["check"][0],
                          f"check {row['id']} lost part of its name through the query string")
            self.assertIn(str(row["id"]), q["facts"][0])
            for key in ("title", "check", "facts"):
                self.assertTrue(q[key][0].strip(), f"{key} arrived empty for check {row['id']}")
            self.assertLess(len(row["url"]), 8000,
                            "GitHub answers 414 above roughly 8k; this row's prefill is too big")
        for key in ("check", "facts"):
            self.assertIn(key, ids,
                          f"the page prefills `{key}`, which is not a field id in check-report.yml "
                          f"-- GitHub silently ignores an unknown key, so the form would open "
                          f"EMPTY and nobody would be told")

    # -- the issue form itself ---------------------------------------------
    def test_the_issue_form_is_valid_and_its_prefilled_fields_are_text(self):
        form = self._form()
        self.assertTrue(form.get("name") and form.get("description"))
        self.assertIn("player-report", form.get("labels", []))
        by_id = {b["id"]: b for b in form["body"] if b.get("id")}
        self.assertEqual(len(by_id), len([b for b in form["body"] if b.get("id")]),
                         "duplicate field ids; GitHub prefill keys on the id")
        for key in ("check", "facts"):
            self.assertIn(key, by_id, f"check-report.yml has no `{key}` field for the browser to "
                                      f"prefill")
            self.assertIn(by_id[key]["type"], ("input", "textarea"),
                          f"`{key}` is a {by_id[key]['type']}; only input and textarea prefill "
                          f"from a URL query, so this one would open blank")
        self.assertEqual("dropdown", by_id["symptom"]["type"])
        self.assertNotIn("symptom", ("check", "facts"))
        for b in form["body"]:
            self.assertIn(b["type"], ("markdown", "input", "textarea", "dropdown", "checkboxes"))
            self.assertTrue(b.get("attributes"), f"{b.get('id')} has no attributes block")

    def test_the_form_asks_the_questions_triage_always_ends_up_asking(self):
        """Not decoration. Every one of these has cost a round trip in a real report: the build
        (the version string alone does not identify it), the yaml, and the log -- which is APPENDED
        across sessions, so the form has to say so or the wrong session gets pasted."""
        by_id = {b["id"]: b for b in self._form()["body"] if b.get("id")}
        for key in ("symptom", "what", "version", "yaml", "log"):
            self.assertIn(key, by_id)
        self.assertIn("F6", by_id["version"]["attributes"]["description"])
        self.assertIn("SESSION START", by_id["log"]["attributes"]["description"])
        opts = by_id["symptom"]["attributes"]["options"]
        joined = " | ".join(opts).lower()
        for want in ("never fired", "vanilla", "reach", "wrong region"):
            self.assertIn(want, joined, f"the symptom list dropped `{want}`")


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class SweepClauseIsEligibilityNotAPromise(unittest.TestCase):
    """E. #936 -- the page must not tell a seedless reader that a boss GRANTS a check.

    THE MOTIVATING CASE (rule 11), colombius on Discord, 2026-08-27. He read

        Mountaintops of the Giants :: Golden Seed - near Foot of the Forge, by two snow
        trolls, also granted by Fire Giant (m60_52_52) [f1052537800]

    and the Fire Giant did not hand it over. Nothing was broken: the check is tagged
    `Seedtree`, `Seedtree` is in SURFACE_DEFAULT_CLASSES and in
    features/boss_locks._SWEEP_SURFACE_CUTTABLE, so `sweep_surface_cut` correctly took it back
    out of the Fire Giant sweep for that seed -- that is where the seed hid its Locks. The NAME
    said otherwise, because names ride the static AP datapackage and cannot vary per seed.

    This page is the seedless surface: it is built once from the corpus and has no
    `dungeon_sweep` rung and no `progression_surface` to consult. So it may state ELIGIBILITY
    and must not state a grant. (The in-game client holds the seed truth in slot_data
    `dungeonSweepFlags` and filters the clause outright -- er_logic::sweep_clause.)
    """

    COLOMBIUS_AP = 7773183
    COLOMBIUS_FLAG = 1052537800
    # The OLD wording -- used as a guard to make sure it does not sneak back into names.
    OPENER = ", also granted by "

    @classmethod
    def _corpus_opener(cls):
        """The opener currently baked into data.py -- read from desc_sources, not hardcoded."""
        import importlib.util as _iu
        spec = _iu.spec_from_file_location(
            "ds_corpus", os.path.join(GREENFIELD, "desc_sources.py"))
        ds = _iu.module_from_spec(spec)
        spec.loader.exec_module(ds)
        return ds.SWEEP_CLAUSE_OPENER

    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.tmp = tempfile.mkdtemp()
        cls.checks = _payload(_build(os.path.join(cls.tmp, "e.html")))["checks"]
        cls.by_id = {c["id"]: c for c in cls.checks}

    def test_the_motivating_check_names_no_grant_and_keeps_its_identity(self):
        c = self.by_id[self.COLOMBIUS_AP]
        self.assertEqual(c["f"], self.COLOMBIUS_FLAG)
        self.assertNotIn(self.OPENER, c["full"])
        self.assertNotIn(self.OPENER, c["n"])
        # the flag tail is the check's identity in logs and issue reports -- stripping the
        # clause must not take it with it.
        self.assertTrue(c["full"].endswith("[f%d]" % self.COLOMBIUS_FLAG), c["full"])
        self.assertIn("near Foot of the Forge, by two snow trolls", c["full"])

    def test_the_motivating_check_still_carries_the_boss_as_eligibility(self):
        # the #670 answer to "so idk what boss to kill?" must survive the fix, or this trades
        # one unusable surface for another.
        self.assertEqual(self.by_id[self.COLOMBIUS_AP]["sw"], ["Fire Giant", "m60_52_52"])

    def test_no_payload_name_anywhere_still_asserts_a_grant(self):
        # WITNESS FIRST: "no name asserts a grant" is also what an empty page says, so pin that
        # the scan is looking at the whole corpus and that it is looking at names that DID carry
        # the clause -- otherwise this passes for the wrong reason the day the join breaks.
        self.assertGreater(len(self.checks), 3000)
        self.assertGreater(len([c for c in self.checks if c["sw"]]), 3000)
        offenders = [c["id"] for c in self.checks
                     if self.OPENER in c["full"] or self.OPENER in c["n"]]
        self.assertFalse(offenders,
                         "%d name(s) still assert a per-seed grant: %s"
                         % (len(offenders), offenders[:5]))

    def test_every_clause_the_corpus_bakes_was_recovered_not_just_deleted(self):
        # A splitter that silently failed to match would look identical to one that worked, by
        # the test above -- the clause would simply still be in the name. Pin the population:
        # every corpus name carrying the clause must come back with a boss on the `sw` row.
        corpus_opener = self._corpus_opener()
        locs = self.tool.load_module_consts(
            os.path.join(GF_PKG, "data.py"), {"LOCATIONS"})["LOCATIONS"]
        baked = {a for v in locs.values() for (n, a, _f) in v if corpus_opener in n}
        self.assertGreater(len(baked), 3000, "the corpus stopped baking the clause?")
        lost = sorted(a for a in baked if not self.by_id[a]["sw"])
        self.assertFalse(lost, "%d clause(s) dropped instead of recovered: %s"
                              % (len(lost), lost[:5]))
        # and the converse: `sw` is never invented for a name that never carried one.
        invented = sorted(c["id"] for c in self.checks if c["sw"] and c["id"] not in baked)
        self.assertFalse(invented, "sw invented for: %s" % invented[:5])

    def test_the_page_says_the_seed_decides_rather_than_hiding_the_hedge(self):
        html = open(os.path.join(REPO, "er-archipelago-check-browser.html"),
                    encoding="utf-8").read()
        self.assertIn("function sweepRow", html)
        self.assertIn("dungeon_sweep", html)
        self.assertIn("progression_surface", html)
        # ...and the promise must not come back as UI chrome. Scoped to the DATA rather than
        # the whole file: the only other occurrence is the source comment above `sweepRow`
        # quoting the clause it exists to explain, and a test that forbade naming the thing
        # would forbid documenting it.
        payload = _payload(html)
        self.assertNotIn("also granted by", json.dumps(payload))

    def test_the_splitter_is_the_inverse_of_the_writer_it_sits_next_to(self):
        # The splitter and `with_sweep` are two halves of one shape; the corpus test above only
        # proves they agree on the shapes the corpus HAPPENS to contain today. This pins the
        # contract itself, including the tile-less form `sweep_clause` also writes.
        import importlib.util as _iu
        spec = _iu.spec_from_file_location(
            "ds_rt", os.path.join(GREENFIELD, "desc_sources.py"))
        ds = _iu.module_from_spec(spec)
        spec.loader.exec_module(ds)
        for desc, boss, tile in (
            ("near Foot of the Forge, by two snow trolls", "Fire Giant", "m60_52_52"),
            ("On a tree near the road", "Night's Cavalry", None),
            ("in a chest (region unconfirmed)", "Deathbird", "m60_44_53"),
        ):
            baked = "R :: I - %s [f7]" % ds.with_sweep(desc, boss, tile)
            back, got_boss, got_tile = ds.split_sweep_clause(baked)
            self.assertEqual(back, "R :: I - %s [f7]" % desc)
            self.assertEqual(got_boss, boss)
            self.assertEqual(got_tile, tile)
        # a name that never carried a clause comes back untouched, boss None.
        plain = "R :: I - just here [f7]"
        self.assertEqual(ds.split_sweep_clause(plain), (plain, None, None))

    def test_the_boss_stays_searchable(self):
        # "which checks does Fire Giant sweep" is the question this page is asked; moving the
        # name out of `n` must not move it out of the search haystack.
        tpl = open(os.path.join(REPO, "tools", "check_browser_template.html"),
                   encoding="utf-8").read()
        hay = tpl.split("function haystack(c){", 1)[1].split("}", 1)[0]
        self.assertIn("c.sw", hay)


if __name__ == "__main__":
    unittest.main()
