#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The regen entrypoint is COMPLETE -- tools/regen_all.py vs. what the tree actually ships.

WHY (issue #699, 2026-08-15). The regen recipe lived in three places -- AGENTS.md section 5a,
`.github/workflows/tests.yaml`, `build.ps1` -- and the one agents are told to read was the
incomplete one: it named no page builder at all, and `tools/build_questline_dag_page.py` appeared
in no doc anywhere. PR #698 followed it exactly and `generators` went red on ONE line, the page's
`inputs_hash` stamp.

Consolidating the list into `tools/regen_all.py` fixes today's failure. It does NOT stop the FIFTH
page being written next month and forgotten the same way -- only a gate does that, and this is it.

WHAT IT ASSERTS, and why each is the thing that would actually have caught #699:

  A. EVERY STAMP-BEARING FILE IN THE TREE IS EMITTED BY A STEP. The defect class is exactly
     "a committed artifact embeds `inputs_hash`, so it re-stales on every data change, and nothing
     regenerates it." So the population is DISCOVERED, not typed: scan the working tree for the
     current stamp and demand each hit be covered by some step's `emits`. A new stamped artifact
     is red on the commit that adds it. 🛑 The scan matches a 16-hex PREFIX, because
     `er-archipelago-questline-dag.html` renders the stamp TRUNCATED -- a full-hash scan silently
     misses the very page that motivated the issue.

  B. EVERY STALENESS-CHECKING tools/build_*.py HAS ALL OF ITS DECLARED OUTPUTS EMITTED BY A STEP.
     This is producer-driven, not location-driven. #708 recurred because the old version knew to
     inspect root HTML pages but could not see greenfield/surface_confidence.tsv or either wizard/
     output. A builder with `--check` is an executable claim that its committed outputs must match;
     the regen entrypoint must be able to make that claim true.

  C. THE STAMP IS WRITTEN BEFORE ANY PAGE IS BUILT. `gen_data.py` writes `_GEN_STAMP`; the pages
     EMBED it. Reordering them is a red CI diff with no visible cause -- it cost six rounds on
     world PR #481, so it is pinned rather than remembered.

  D. THE CONSUMERS CITE THE ENTRYPOINT AND ENUMERATE NO PAGE. `build.ps1`, `tests.yaml` and
     AGENTS.md must invoke `regen_all.py`, and none of them may run a PAGE builder directly.
     This is the assertion that keeps "three lists" from growing back.

  E. Every step names a file that exists (no stale row), and phases are declared/ordered.

REPO-ONLY: it reads `tools/`, `build.ps1` and `.github/`, none of which gf_test.py installs beside
the world. Ledgered in tools/gf_suite_ledger.py under GENERATORS.

Run: python greenfield/eldenring/tests/test_gf_regen_all.py
"""
import fnmatch
import importlib.util
import json
import os
import re
import sys
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
ENTRYPOINT = os.path.join(REPO, "tools", "regen_all.py")
STAMP = os.path.join(REPO, "greenfield", "eldenring", "_gen_stamp.json")

# Not part of the tree the entrypoint owns: the artifact bundle is gitignored, the client is
# another repo, `_ap` / `.ap-test` are AP checkouts, and `.git` is not source.
#
# 🛑 `.ap-test` IS `tools/gf_test.py`'S DEFAULT, and it was missing here until 2026-08-16. This list
# had `_ap` -- the name CI passes via `--ap-dir _ap` -- and nothing else, so the walk descended into
# the INSTALLED COPY of the world that gf_test.py had just written and reported its generated
# modules as artifacts no `regen_all` step emits. That is a spurious red reading exactly like the
# real thing this test is for (#699), on the default local harness, for anyone who ran gf_test.py
# without `--ap-dir`. Both names, and any new AP-checkout convention belongs here too.
SKIP_DIRS = {".git", ".github", "_ap", ".ap-test", "__pycache__", "node_modules",
             "elden_ring_artifacts", "from-software-archipelago-clients", ".pytest_cache", ".venv"}
# A stamped file is only interesting if it is TEXT we ship. 8 MB of html is fine to read; a param
# blob is not, and cannot embed the hash as text anyway.
SCAN_EXT = {".html", ".py", ".json", ".tsv", ".csv", ".md", ".rs", ".yaml", ".yml", ".ps1"}

# WHICH direct invocations are forbidden, and why only these. The forbidden set is derived from
# the PAGES phase, not typed: those four are the steps #699 found enumerated inconsistently, and
# nothing else in the repo legitimately runs them. It deliberately does NOT cover the table steps
# -- the `client-main-drift` job runs gen_region_locks/gen_contract against a DIFFERENT checkout to
# answer a different question, and forbidding that would be a gate punishing a correct caller.
# Command form only: prose that names a tool is fine, and the docs are full of it for good reasons.
def _forbidden_re(mod):
    names = sorted(os.path.basename(s.script)[:-3] for s in mod.STEPS if s.phase == mod.PAGES)
    return re.compile(r"python[3]?\s+(?:[^\s\"']*[\\/])?(?:tools|greenfield)[\\/]"
                      r"(?:%s)\.py" % "|".join(names))


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location("regen_all", ENTRYPOINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class RegenEntrypointIsComplete(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_entrypoint()
        cls.steps = cls.mod.STEPS
        cls.emits = [e for s in cls.steps for e in s.emits]

    def _covered(self, rel):
        rel = rel.replace(os.sep, "/")
        return any(fnmatch.fnmatch(rel, pat) for pat in self.emits)

    # -- E. the list is not stale -------------------------------------------
    def test_every_step_names_a_file_that_exists(self):
        for s in self.steps:
            self.assertTrue(os.path.isfile(os.path.join(REPO, *s.script.split("/"))),
                            "regen_all STEPS names %s, which is not on disk (renamed tool?)"
                            % s.script)
            self.assertIn(s.phase, self.mod.PHASES,
                          "step %s declares phase %r, which is not in PHASES" % (s.script, s.phase))
            self.assertTrue(s.why.strip(),
                            "step %s has no `why` -- a step nobody can justify is a step nobody "
                            "can safely delete" % s.script)

    # -- C. the stamp is written before the pages read it -------------------
    def test_the_stamp_is_written_before_any_page_is_built(self):
        order = [self.mod.PHASES.index(s.phase) for s in self.steps]
        self.assertEqual(order, sorted(order),
                         "STEPS is out of phase order -- the pages EMBED the stamp gen_data "
                         "writes, so a page that runs first carries the PREVIOUS hash and the CI "
                         "byte-diff goes red with no visible cause (world PR #481, six rounds).")
        gen = [i for i, s in enumerate(self.steps) if s.script.endswith("gen_data.py")]
        self.assertEqual(len(gen), 1, "expected exactly one gen_data.py step")
        pages = [i for i, s in enumerate(self.steps) if s.phase == self.mod.PAGES]
        self.assertTrue(pages, "no page steps at all -- that is the #699 defect, restored")
        self.assertLess(gen[0], min(pages),
                        "gen_data.py must precede every page builder")

    # -- A. discovered, not typed: every stamped artifact has a producer ----
    def test_every_stamp_bearing_artifact_is_emitted_by_a_step(self):
        with open(STAMP, encoding="utf-8") as fh:
            full = json.load(fh)["inputs_hash"]
        # 🛑 PREFIX, not the full hash: the questline page renders the stamp truncated to 16 hex.
        needle = full.split(":", 1)[-1][:16]
        self.assertEqual(len(needle), 16, "unexpected inputs_hash shape: %r" % full)

        stamped, orphans = [], []
        for root, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                if os.path.splitext(fn)[1].lower() not in SCAN_EXT:
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as fh:
                        if needle not in fh.read():
                            continue
                except OSError:
                    continue
                rel = os.path.relpath(path, REPO).replace(os.sep, "/")
                stamped.append(rel)
                if not self._covered(rel):
                    orphans.append(rel)

        self.assertGreaterEqual(len(stamped), 10,
                                "found only %d stamp-bearing files -- the scan is broken (wrong "
                                "hash? wrong root?), and a broken scan reports zero orphans, "
                                "which is indistinguishable from clean" % len(stamped))
        self.assertEqual([], sorted(orphans),
                         "these committed files EMBED inputs_hash but no tools/regen_all.py step "
                         "emits them, so every data change re-stales them and only CI's byte-diff "
                         "notices (issue #699). Add the producing step to STEPS with an `emits` "
                         "entry.")

    # -- B. the other direction: checked producers unreachable from the entrypoint
    def test_every_checked_builder_output_is_emitted_by_a_step(self):
        scripted = {s.script for s in self.steps}
        # Output globals are the builders' existing convention: OUT, OUTPUT, *_OUT, *_OUTPUT and
        # *_HTML. Read their final path component, then resolve it against the shipped tree. This
        # asks PRODUCERS what they write; it does not enumerate directories or artifact names.
        output_re = re.compile(
            r'^\s*(OUT|OUTPUT|[A-Z][A-Z0-9_]*(?:_OUT|_OUTPUT|_HTML))\s*=\s*os\.path\.join\('
            r'[^\n]*?["\']([^"\']+\.(?:html|json|tsv|csv|py|rs))["\']\s*\)\s*$', re.MULTILINE)
        by_name = {}
        for root, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                by_name.setdefault(fn, []).append(
                    os.path.relpath(os.path.join(root, fn), REPO).replace(os.sep, "/"))

        seen, missing, undeclared = [], [], []
        tools = os.path.join(REPO, "tools")
        for fn in sorted(os.listdir(tools)):
            if not (fn.startswith("build_") and fn.endswith(".py")):
                continue
            with open(os.path.join(tools, fn), encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            if "--check" not in text:
                continue
            declared = []
            for _var, basename in output_re.findall(text):
                declared.extend(by_name.get(basename, ()))
            declared = sorted(set(declared))
            if not declared:
                undeclared.append(fn)
                continue
            seen.append(fn)
            script = "tools/%s" % fn
            if script not in scripted:
                missing.append("%s -> %s" % (fn, ", ".join(declared)))
                continue
            for rel in declared:
                if not self._covered(rel):
                    missing.append("%s does not emit %s" % (fn, rel))
        self.assertEqual([], undeclared,
                         "these builders offer --check but declare no discoverable output global; "
                         "name outputs OUT/OUTPUT/*_OUT/*_OUTPUT/*_HTML so regen_all can own them: "
                         + ", ".join(undeclared))
        # THE WITNESS. An empty `missing` is also what a blind scan produces. Four checked builders
        # exist today; assert the producer scan still sees the corpus before trusting its answer.
        self.assertGreaterEqual(len(seen), 4,
                                "the checked-builder scan matched only %d tool(s) (%s) -- it has "
                                "stopped seeing the corpus, and a blind scan reports no orphans"
                                % (len(seen), ", ".join(seen)))
        self.assertEqual([], missing,
                         "these checked builder outputs are not reachable from tools/regen_all.py "
                         "-- exactly how #708 recurred one PR after the root-page-only guard")

    # -- D. no consumer keeps its own list ----------------------------------
    def test_the_consumers_invoke_the_entrypoint_and_enumerate_nothing(self):
        consumers = ["build.ps1", os.path.join(".github", "workflows", "tests.yaml"), "AGENTS.md"]
        for rel in consumers:
            path = os.path.join(REPO, rel)
            if not os.path.isfile(path):          # a partial clone; say so rather than pass
                self.skipTest("%s absent from this checkout" % rel)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            # assertTrue, not assertIn: assertIn's default message pastes the whole haystack, and
            # build.ps1 is 600 lines -- a gate whose output nobody reads is a gate nobody heeds.
            self.assertTrue("regen_all.py" in text,
                            "%s does not cite tools/regen_all.py -- it is a fourth list waiting "
                            "to drift" % rel)
            hand = sorted(set(m.group(0).strip() for m in _forbidden_re(self.mod).finditer(text)))
            self.assertEqual([], hand,
                             "%s invokes regen steps directly (%s). That is the duplicated list "
                             "issue #699 removed; call `python tools/regen_all.py` instead."
                             % (rel, "; ".join(hand)))


if __name__ == "__main__":
    unittest.main()
