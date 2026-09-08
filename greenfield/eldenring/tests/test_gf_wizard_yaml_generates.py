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

Coverage: defaults and two legacy presets, plus five actual browser-profile compositions
across three seeds each. Values come from the JavaScript profile definitions; broader option
coverage lives in the option-matrix suites.
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
    meta = re.search(r'<script id="er-options-metadata" type="application/json">\r?\n(.*?)</script>',
                     html, re.S)
    return (core.group(1) if core else None), (json.loads(meta.group(1)) if meta else None)


def _build_yaml(core, meta, preset=None, profiles=None):
    """Run the wizard's OWN buildYaml under node. Returns the yaml text."""
    js = (core + "\nconst __meta = " + json.dumps(meta) + ";\n"
          + "const m = ERW.loadMeta(__meta);\n"
          + "let st = { name:'CI', presetId:null, presetTitle:'Defaults', values:{} };\n"
          + ("" if preset is None else
             "st = ERW.applyPreset(m, st, %s);\n" % json.dumps(preset))
          + "const selections = " + json.dumps(profiles or {}) + ";\n"
          + "for (const [groupId,pickId] of Object.entries(selections)){\n"
          + " const group=ERW.profiles(m).find(g=>g.id===groupId);\n"
          + " const pick=group && group.picks.find(p=>p.id===pickId);\n"
          + " if(!pick) throw new Error(groupId + ':' + pickId);\n"
          + " ERW.applyProfile(m,st,pick);\n}\n"
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

    def _generate(self, yaml_text, label, seed=1):
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
                 "--outputpath", out, "--seed", str(seed), "--spoiler", "1"],
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

    def test_profile_compositions_generate(self):
        # IDs select the actual JS pick definitions, never a parallel Python recipe.
        cases = [
            {"content": "base", "size": "short", "exploration": "rush", "rewards": "supplies", "travel": "explore", "multiplayer": "local"},
            {"content": "base-gear", "size": "standard", "exploration": "balanced", "rewards": "gear", "travel": "landmarks", "multiplayer": "share"},
            {"content": "all", "size": "standard", "exploration": "thorough", "rewards": "original", "travel": "all"},
            {"content": "dlc", "size": "short", "exploration": "rush", "rewards": "balanced", "travel": "landmarks"},
            {"content": "base-gear", "size": "short", "rewards": "original"},
        ]
        for picks in cases:
            yaml_text = _build_yaml(self.core, self.meta, profiles=picks)
            for seed in (1, 7, 19):
                with self.subTest(profiles=picks, seed=seed):
                    self._generate(yaml_text, str(picks), seed)

    def test_the_yaml_writes_every_option_down(self):
        """#732. The wizard emitted the DEVIATIONS only, so an untouched run produced
        `Elden Ring: {}` -- a file that generates a correct seed and documents nothing. Generation
        cannot see this: `{}` is the most generatable yaml there is, so the test above was green
        throughout. This is the assertion that names it.

        Held on the METADATA's key list rather than a pinned count, so a new option is covered the
        day it is dumped and this does not become a number somebody bumps."""
        yaml_text = _build_yaml(self.core, self.meta, None)
        emitted = set(re.findall(r"^  ([a-z_][a-z0-9_]*):", yaml_text, re.M))
        # WITNESS. `missing` is empty in two very different worlds: every option was emitted, or
        # the metadata is empty / this regex stopped matching the builder's output. Only one of
        # those is the pass this test means, so say out loud that the scan saw something. No pinned
        # count -- these are floors on "anything at all", not on how many options exist.
        self.assertTrue(self.meta["options"],
                        "options metadata carries no options; every assertion below is vacuous")
        self.assertTrue(emitted,
                        "the yaml emitted no option lines at all -- the builder or this regex moved")
        missing = [o["key"] for o in self.meta["options"] if not o.get("compatibility_only") and o["key"] not in emitted]
        self.assertFalse(missing,
                         "the wizard's yaml is silent about %d live option(s) it configures: %s"
                         % (len(missing), ", ".join(missing)))

    def test_every_value_the_yaml_writes_is_legal_for_its_option(self):
        """The landmine under the test above, and the reason it is a separate assertion.

        `cross_game_progression` and `maximum_enemy_difficulty` are NamedRanges whose DEFAULT sits
        outside their own declared `0..100` -- `-1`, reachable only as the name `auto`. While the
        wizard emitted deviations only, a default was never written down and so its illegal
        spelling was never written down either. Writing every option down puts both in every file,
        and `Range.from_any(-1)` raises: the yaml stops generating at all.

        Generation catches that one, loudly. It would NOT catch the quiet direction -- a special
        name emitted for a value that is in range, e.g. `all` for `confine_foreign_progression: 100`
        -- which generates fine and is simply less legible. So this reads the numbers directly."""
        yaml_text = _build_yaml(self.core, self.meta, None)
        by_key = {o["key"]: o for o in self.meta["options"]}
        bad = []
        examined = 0
        for line in yaml_text.splitlines():
            m = re.match(r'^  ([a-z_][a-z0-9_]*): (-?\d+|"[^"]*")\s*(?:#.*)?$', line)
            if not m:
                continue
            key, raw = m.group(1), m.group(2)
            o = by_key.get(key)
            rng = (o or {}).get("range")
            if not rng:
                continue
            examined += 1
            names = {s["name"]: s["value"] for s in (o.get("special_values") or [])}
            if raw.startswith('"'):
                # The quiet direction: a name where a plain number would do.
                nm = raw.strip('"')
                if nm not in names:
                    bad.append("%s: %s is not one of this range's special names %s"
                               % (key, raw, sorted(names)))
                elif rng["start"] <= names[nm] <= rng["end"]:
                    bad.append("%s: emitted as the name %s for %d, which is in range %d..%d -- the "
                               "number is the legible spelling and the name is only needed when it "
                               "is not" % (key, raw, names[nm], rng["start"], rng["end"]))
            elif not (rng["start"] <= int(raw) <= rng["end"]):
                bad.append("%s: %s is outside its declared range %d..%d -- it has to be emitted as "
                           "one of its special names %s"
                           % (key, raw, rng["start"], rng["end"], sorted(names)))
        # WITNESS. Every `continue` above is a silent skip, so `bad` stays empty whether the values
        # are legal or the line regex simply stopped matching -- and the second is the more likely
        # of the two, because the emitted shape is exactly what this PR changed.
        self.assertTrue(examined,
                        "no ranged option line was examined: the line regex matched nothing, so "
                        "this test proves nothing about the values the wizard writes")
        self.assertFalse(bad, "the wizard emitted %d unusable value(s):\n  %s"
                              % (len(bad), "\n  ".join(bad)))


if __name__ == "__main__":
    unittest.main()
