"""The yaml the wizard EMITS must actually generate a seed. End to end, no stubs.

MOTIVATING CASE (CONTRIBUTING rule 11), 2026-08-08. `buildYaml` carried the game name as a literal,
`"EldenRing"`, while the world has been `"Elden Ring"` for months. Every yaml the wizard produced --
Copy, Download, and the Generate & host button -- named a game Archipelago cannot resolve. It was
live, and it was found by a human reading a screenshot.

What makes that worth a test file of its own is WHY four green gates missed it:

    dump_options_metadata --check   the option surface is current  -- and it was
    check_wizard_lint_currency      the rules name live options    -- and they did
    build_region_census --check     the census is current          -- and it was
    check_wizard_census_js          the seed-size maths agrees     -- and it did

Every one of them checks an INPUT to the wizard. None looked at what it hands the player. The
option keys were metadata-driven and correct; the three strings carrying the game name were typed,
and no gate read them, because no gate read the OUTPUT at all.

So this reads the output, and hands it to the thing it is meant to be handed to. It would have
caught the game-name bug on the first run, and it catches the whole family the four gates above
cannot: a key the world stopped accepting, a value outside a live option's range, a preset that
rolls into an unwinnable combination, a yaml that is subtly malformed. Anything where the wizard is
internally consistent and still produces a file that does not work.

🛑 IT RUNS THE REAL GENERATOR. Not a parse, not a schema check -- `Generate.py` against the installed
world, asserting a seed archive comes out. A yaml can parse cleanly, name every option correctly and
still fail to fill; only generation knows.

NODE, because `buildYaml` is JavaScript and the point is to test THE function the player's browser
runs, not a Python reimplementation of it. A port would be a second source of truth and would have
agreed with itself about "EldenRing".

Cost: one generation per case, ~2-4 s each in CI. Kept to three -- defaults plus two presets --
because this is a smoke test of the seam, not a matrix; option coverage lives in the option-matrix
suites.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

# Presets to exercise alongside the defaults. `None` is "no preset applied".
CASES = [None, "first_run", "dlc_only"]


def _wizard_html():
    with open(os.path.join(REPO, "wizard", "wizard.html"), "r", encoding="utf-8", newline="") as f:
        return f.read()


def _core_and_meta(html):
    core = re.search(r'<script id="wizard-core">(.*?)</script>', html, re.S)
    meta = re.search(r'<script id="er-options-metadata" type="application/json">\n(.*?)</script>',
                     html, re.S)
    return (core.group(1) if core else None), (json.loads(meta.group(1)) if meta else None)


def _build_yaml(core, meta, preset):
    """Run the wizard's OWN buildYaml under node. Returns the yaml text."""
    js = (core + "\nconst __meta = " + json.dumps(meta) + ";\n"
          + "const m = ERW.loadMeta(__meta);\n"
          + "let st = { name:'CI', presetId:null, presetTitle:'Defaults', values:{} };\n"
          + ("" if preset is None else
             "st = ERW.applyPreset(m, st, %s);\n" % json.dumps(preset))
          + "console.log(JSON.stringify(ERW.buildYaml(m, st)));\n")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "b.js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(js)
        out = subprocess.run(["node", path], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError("the wizard's buildYaml failed under node:\n" + (out.stderr or ""))
    return json.loads(out.stdout.strip().splitlines()[-1])


def _ap_root():
    """The AP checkout this suite is running inside (…/worlds/eldenring/tests → …)."""
    d = os.path.abspath(HERE)
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isfile(os.path.join(d, "Generate.py")):
            return d
    return None


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class WizardYamlGenerates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise unittest.SkipTest(
                "node is not on PATH -- the wizard's OWN buildYaml cannot be run, so what it hands "
                "players is NOT covered on this box. CI has node; this should never skip there.")
        cls.ap = _ap_root()
        if not cls.ap:
            raise unittest.SkipTest("no Generate.py above this suite -- not running inside an AP "
                                    "checkout, so real generation is NOT covered here.")
        html = _wizard_html()
        cls.core, cls.meta = _core_and_meta(html)
        if not cls.core or not cls.meta:
            raise AssertionError("wizard.html is missing wizard-core or its metadata blob -- this "
                                 "test cannot see the wizard and must not pass quietly.")

    def _generate(self, yaml_text, label):
        with tempfile.TemporaryDirectory() as work:
            players, out = os.path.join(work, "p"), os.path.join(work, "o")
            os.makedirs(players)
            os.makedirs(out)
            with open(os.path.join(players, "wizard.yaml"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(yaml_text)
            env = dict(os.environ)
            env.update({"AP_NONINTERACTIVE": "1", "SKIP_REQUIREMENTS_UPDATE": "1",
                        "HOME": work, "TMPDIR": work})
            r = subprocess.run(
                [sys.executable, "Generate.py", "--player_files_path", players,
                 "--outputpath", out, "--seed", "1", "--spoiler", "1"],
                cwd=self.ap, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True)
            tail = (r.stdout or "")[-2500:] + (r.stderr or "")[-2500:]
            self.assertEqual(r.returncode, 0,
                             "the wizard's own yaml (%s) does not generate:\n%s\n--- yaml ---\n%s"
                             % (label, tail, yaml_text))
            zips = glob.glob(os.path.join(out, "AP_*.zip"))
            self.assertTrue(zips, "generation reported success but produced no seed (%s)" % label)
            self.assertGreater(os.path.getsize(zips[0]), 1024)

    def test_the_yaml_the_wizard_emits_generates(self):
        for preset in CASES:
            label = preset or "defaults"
            with self.subTest(preset=label):
                yaml_text = _build_yaml(self.core, self.meta, preset)
                # The bug that motivated this file, asserted directly as well as through
                # generation: a wrong game name fails below anyway, but this names it.
                self.assertIn("game: %s" % self.meta["game"], yaml_text,
                              "the emitted yaml does not name the metadata's game")
                self._generate(yaml_text, label)


if __name__ == "__main__":
    unittest.main()
