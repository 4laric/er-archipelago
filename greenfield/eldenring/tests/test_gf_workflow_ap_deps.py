"""Every workflow that generates a seed installs Archipelago's requirements first.

WHY. `er-release.yaml` ran for the first time on the v0.4.1 tag and its `bundle` job died on

    zip-smoke: FAILED -- generation from the zipped apworld did not complete (exit 1).
      ModuleNotFoundError: No module named 'yaml'

It set up Python and went straight to `tools/gf_zip_gen_smoke.py`, which bootstraps the pinned
Archipelago checkout and does NOT pip-install -- Archipelago's own requirements have always been
the caller's job. The other two callers do it (`tests.yaml` from `_ap/requirements.txt`,
`release.yaml` as an inline list beside its own copy of the same gate); this one did neither, and
nothing anywhere compared them. Every step below the gate -- the icon fetch, `pack_release.py`,
the upload -- was skipped, so the release automation produced nothing on its debut.

🛑 WHY IT SCANS RATHER THAN TAKING A LIST, same reason as test_gf_noninteractive_guard: a hardcoded
set of three workflow names goes stale the first time someone adds a fourth, and does so silently.
The failure mode this repo keeps paying for is absence being invisible.

🛑 WHAT THIS CANNOT SEE. It reads text, not a runner. A workflow that installs the wrong pins, or
whose install step is gated behind an `if:` that is false at release time, passes here. It answers
one question -- "does this file install anything at all before it generates?" -- which is the
question the v0.4.1 failure asked and nobody had.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
_WORKFLOWS = ".github/workflows"

# A step that will run a generation on this runner. The zip smoke is the release form; a bare
# `Generate.py` invocation is the inline form release.yaml uses.
_GENERATES = re.compile(r"gf_zip_gen_smoke\.py|(?<![\w/-])Generate\.py[ \t]")

# An install that puts AP's runtime deps on the runner. Either the requirements file, or an
# explicit list -- in which case pyyaml is the one that must be in it, because `yaml` is what
# Generate.py imports before it touches a world at all.
_INSTALLS = re.compile(r"pip install[^\n]*-r[^\n]*requirements\.txt"
                       r"|pip[ \t]+install[^\n]{0,400}?pyyaml", re.I | re.S)


class WorkflowApDeps(unittest.TestCase):
    def _workflows(self):
        """{relpath: {'generates': bool, 'installs': bool}} for every workflow file."""
        if not _ROOT:
            self.skipTest(REPO_ONLY_REASON)
        d = os.path.join(_ROOT, _WORKFLOWS)
        if not os.path.isdir(d):
            self.skipTest("%s is not present in this checkout" % _WORKFLOWS)
        out = {}
        for name in sorted(os.listdir(d)):
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                text = fh.read()
            out["%s/%s" % (_WORKFLOWS, name)] = {
                "generates": bool(_GENERATES.search(text)),
                "installs": bool(_INSTALLS.search(text)),
            }
        return out

    def test_the_sweep_actually_sees_the_workflows(self):
        """Rule 2: an empty result is a FAILURE, not a clean run. A detector that stopped matching
        would report a green 'all generators provisioned' over zero of them."""
        found = self._workflows()
        self.assertGreaterEqual(len(found), 3,
                                "only %d workflow file(s) scanned: %s" % (len(found), sorted(found)))
        gen = sorted(p for p, v in found.items() if v["generates"])
        self.assertGreaterEqual(
            len(gen), 2,
            "the generation detector found %d workflow(s); tests.yaml, release.yaml and "
            "er-release.yaml all run one. A drop means the detector broke, not that the "
            "generations went away: %s" % (len(gen), gen))

    def test_every_generating_workflow_installs_ap_requirements(self):
        """HARD gate. This is the v0.4.1 failure, stated as the thing that must not recur."""
        found = self._workflows()
        generating = sorted(p for p, v in found.items() if v["generates"])
        # THE WITNESS. Without it this assertion passes for the same reason whether the workflows
        # are provisioned or the detector stopped matching -- and an empty candidate set is the
        # more likely of the two after any workflow rename (test_gf_vacuous_pass).
        self.assertNotEqual([], generating,
                            "no workflow was detected as running a generation, so the emptiness "
                            "below would be the detector's, not the repo's. Scanned: %s"
                            % sorted(found))
        naked = sorted(p for p, v in found.items() if v["generates"] and not v["installs"])
        self.assertEqual(
            naked, [],
            "these workflows run a generation without installing Archipelago's requirements, so "
            "Generate.py dies at `ModuleNotFoundError: No module named 'yaml'` before it loads any "
            "world -- and every step below it is skipped. `tools/gf_zip_gen_smoke.py` bootstraps "
            "the AP CHECKOUT, not its dependencies. Add `pip install -r <ap>/requirements.txt`:"
            "\n  " + "\n  ".join(naked))

    def test_the_motivating_case_is_covered_by_name(self):
        """Rule 11: the case that motivated the gate is the acceptance test, asserted BY NAME
        through the finished pipeline. er-release.yaml is the file whose first ever run failed."""
        found = self._workflows()
        rel = "%s/er-release.yaml" % _WORKFLOWS
        self.assertIn(rel, found,
                      "the release workflow this gate was written for is no longer scanned; the "
                      "gate would pass while blind to its own motivating case. Seen: %s"
                      % sorted(found))
        self.assertTrue(found[rel]["generates"],
                        "%s is scanned but no longer detected as running a generation -- the "
                        "detector, not the workflow, is what changed" % rel)
        self.assertTrue(found[rel]["installs"],
                        "%s runs the zip-gen gate and installs nothing. This is exactly the v0.4.1 "
                        "failure it was written for." % rel)

    def test_the_gate_can_fail(self):
        """Rule 7: a passing gate proves nothing until you have seen it fail. Drive the same two
        detectors over a synthetic workflow that generates and installs nothing."""
        naked = "jobs:\n  x:\n    steps:\n      - run: python tools/gf_zip_gen_smoke.py --apworld d/e.apworld\n"
        self.assertTrue(_GENERATES.search(naked), "the generation detector missed the obvious case")
        self.assertFalse(_INSTALLS.search(naked), "the install detector matched a workflow with no pip at all")
        fixed = naked.replace("      - run: python",
                              "      - run: pip install -r .ap-test/requirements.txt\n      - run: python")
        self.assertTrue(_INSTALLS.search(fixed), "the install detector missed a requirements install")


if __name__ == "__main__":
    unittest.main()
