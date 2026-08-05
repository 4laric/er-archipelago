"""Provenance gate (tier A) -- PROVENANCE.md, check_integrity's foreign-list check,
and tools/diff_foreign_list.py.

The from-scratch derivation is this project's asset, legally and under CONTRIBUTING's
"derive the datum" rule. The rule is: reading another randomizer's list to cross-check is
fine, committing it -- or copying flags out of it -- is not. This gate makes that a machine
check rather than a habit, and it has two halves that fail in opposite directions:

  A. THE GUARD MUST BITE. A file carrying a foreign location-list key grammar must be
     refused by check_integrity, or the rule is only a paragraph.
  B. THE GUARD MUST NOT CRY WOLF. A pre-commit hook with false positives gets bypassed
     with --no-verify, which is the door every other corruption walks through. So the
     whole tracked tree must stay clean, and the legitimate uses of the grammar (the
     foreign-apworld degrade test) must be exempt via an IN-FILE declaration -- reviewable
     in a diff -- rather than a filename allowlist that could silently cover real data.

  C. THE DIFF TOOL MUST NOT BE ABLE TO LAUNDER. diff_foreign_list reports where OUR
     derivation is short; it must have no path that prints a foreign identifier, because
     "here are the flags we're missing, paste them in" is committing the list slowly.

Uses SYNTHETIC keys throughout -- grammar only, never anyone's data.
Run:  python -m pytest greenfield/eldenring/tests/test_gf_provenance_gate.py
"""
import importlib.util
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
# 🛑 Derive greenfield paths FROM the found root, never positionally. In CI the AP
# checkout `_ap/` sits INSIDE the repo, so find_repo_root succeeds and these suites
# RUN there -- but a positional GREENFIELD then resolves to `_ap/worlds/` and every
# tsv read misses. That is the second half of the 2026-07-27 path bug: fixing REPO
# alone moved 45 errors to 3 failures instead of to 0.
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GREENFIELD = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))
GF_PKG = os.path.join(GREENFIELD, "eldenring") if _FOUND else os.path.dirname(HERE)
INTEGRITY = os.path.join(REPO, "tools", "check_integrity.py")
DIFF_TOOL = os.path.join(REPO, "tools", "diff_foreign_list.py")
PROVENANCE = os.path.join(REPO, "PROVENANCE.md")

# Grammar only. This is not a real key from anywhere; the ids are invented.
SYNTHETIC_KEY = "301200,0:0000520110::"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class ProvenanceGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ci = _load(INTEGRITY, "_check_integrity")

    # -- A. the guard bites -------------------------------------------------
    def test_foreign_key_grammar_is_refused(self):
        self.assertTrue(self.ci.foreign_list_hits(SYNTHETIC_KEY + "\n"),
                        "a foreign location key is not detected at all")

    def test_itemslots_structure_is_refused(self):
        self.assertTrue(self.ci.foreign_list_hits("ItemSlots:\n  - Key: x\n"))

    def test_guard_fails_the_process_not_just_the_function(self):
        """check_one must promote the hit to an ERROR and the CLI must exit nonzero."""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "list.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(SYNTHETIC_KEY + "\n")
            errs, _warns = self.ci.check_one(p)
            self.assertTrue(any("FOREIGN LOCATION LIST" in e for e in errs), errs)
            r = subprocess.run([sys.executable, INTEGRITY, p], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("PROVENANCE.md", r.stdout + r.stderr)

    # -- B. the guard does not cry wolf -------------------------------------
    def test_no_false_positive_anywhere_in_the_tracked_tree(self):
        out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest("not a git checkout")
        bad = []
        for rel in out.stdout.split():
            path = os.path.join(REPO, rel)
            if self.ci.ext(rel) not in self.ci.TEXT_EXTS or not os.path.exists(path):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            if self.ci.foreign_list_hits(text):
                bad.append(rel)
        self.assertFalse(bad, f"guard would block legitimate committed file(s): {bad}")

    def test_exemption_is_an_in_file_declaration_not_a_filename_allowlist(self):
        with open(INTEGRITY, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("PROVENANCE_OK", src)
        # a basename allowlist is the fragile version -- it would cover a file that later
        # gained real foreign data, invisibly.
        self.assertNotIn('os.path.basename(path) not in ("PROVENANCE.md"', src)
        self.assertEqual(self.ci.foreign_list_hits(SYNTHETIC_KEY + "\n# PROVENANCE-OK: synthetic\n"),
                         [], "the in-file marker does not exempt")

    def test_declared_exemptions_stay_a_short_list(self):
        out = subprocess.run(["git", "grep", "-l", "PROVENANCE-OK:"], cwd=REPO,
                             capture_output=True, text=True)
        files = [f for f in out.stdout.split() if f]
        self.assertLessEqual(len(files), 5,
                             f"PROVENANCE-OK is spreading ({files}) -- each one is a claim "
                             "that a file's foreign-looking keys are synthetic")

    # -- C. the diff tool cannot launder ------------------------------------
    def test_diff_tool_declares_no_flag_emitting_option(self):
        """Inspect the CODE, not the prose -- the docstring legitimately names --emit-flags
        while explaining why it does not exist. (The first version of this test failed on
        exactly that, which is the whole reason it reads the AST now.)"""
        import ast
        with open(DIFF_TOOL, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        opts = [a.value for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "add_argument"
                for a in node.args if isinstance(a, ast.Constant)]
        for o in opts:
            self.assertNotRegex(str(o), r"emit|print|dump|flags|list-",
                                f"CLI option {o!r} looks like a way to print foreign ids")
        self.assertEqual(sorted(o for o in opts if str(o).startswith("--")), ["--repo"])

    def test_diff_tool_never_opens_a_file_for_writing(self):
        import ast
        with open(DIFF_TOOL, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open":
                mode = ""
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = str(node.args[1].value)
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = str(kw.value.value)
                self.assertNotIn("w", mode, "diff tool opens a file for WRITING")
                self.assertNotIn("a", mode, "diff tool opens a file for APPEND")

    def test_diff_tool_output_names_no_foreign_identifier(self):
        """End to end on a SYNTHETIC list: the report must contain none of its flags."""
        planted = [999000001, 999000002, 999000003]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "synthetic.txt")
            with open(p, "w", encoding="utf-8") as fh:
                for i, f in enumerate(planted):
                    fh.write(f"{301200 + i},0:{f:010d}::\n")
            r = subprocess.run([sys.executable, DIFF_TOOL, p, "--repo", REPO],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in planted:
                self.assertNotIn(str(f), r.stdout,
                                 "the diff printed a foreign identifier -- that is the copy path")
            self.assertIn("PROVENANCE.md", r.stdout)

    def test_diff_tool_parses_the_key_grammar_rather_than_scraping_it(self):
        """The leading field of a key is a shop/lot id, NOT a flag. Scraping both roughly
        doubles the apparent gap; the tool must take field 1 only when the grammar is there."""
        tool = _load(DIFF_TOOL, "_diff_foreign_list")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "synthetic.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("301200,0:0000520110::\n")
            flags, how = tool.extract_flags(p)
            self.assertEqual(how, "keyed")
            self.assertEqual(flags, {520110}, "parsed the id field as a flag")

    def test_scrape_fallback_is_labelled_an_upper_bound(self):
        tool = _load(DIFF_TOOL, "_diff_foreign_list2")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "plain.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("520110\n60300\n")
            _flags, how = tool.extract_flags(p)
            self.assertEqual(how, "scraped")
        with open(DIFF_TOOL, encoding="utf-8") as fh:
            self.assertIn("UPPER BOUND", fh.read())

    # -- the doc the rule lives in ------------------------------------------
    def test_provenance_doc_exists_and_readme_points_at_it(self):
        self.assertTrue(os.path.exists(PROVENANCE), "PROVENANCE.md is missing")
        with open(os.path.join(REPO, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn("PROVENANCE.md", readme)

    def test_provenance_and_attribution_cross_references_resolve(self):
        """Both docs point at each other; a dangling pointer between them is exactly the defect
        this suite was written to clear.

        🛑 I asserted on 2026-07-27 that release/ATTRIBUTION.md 'has never existed'. It has
        existed at every commit in this history. The check that told me otherwise ran inside a
        clone whose checkout had TIMED OUT, so `git ls-files` under-reported -- and README.md was
        pointing at the file, which I read as the README being wrong rather than my clone being
        broken. This test exists so the claim is checked by something other than my memory.
        """
        attribution = os.path.join(REPO, "release", "ATTRIBUTION.md")
        if not os.path.exists(attribution):
            self.skipTest("release/ATTRIBUTION.md not present in this checkout")
        with open(attribution, encoding="utf-8") as fh:
            attr = fh.read()
        with open(PROVENANCE, encoding="utf-8") as fh:
            prov = fh.read()
        self.assertIn("PROVENANCE.md", attr,
                      "ATTRIBUTION.md no longer points at the repo provenance doc")
        self.assertIn("ATTRIBUTION.md", prov,
                      "PROVENANCE.md no longer points back at the release attribution doc")
        # ATTRIBUTION.md promises this doc spells out five non-negotiables + how CI enforces them
        if "five non-negotiables" in attr:
            self.assertIn("five non-negotiables", prov,
                          "ATTRIBUTION.md promises a 'five non-negotiables' section that "
                          "PROVENANCE.md does not have -- a dangling forward reference")

    def test_referenced_repo_paths_actually_exist(self):
        """Any repo-relative path PROVENANCE.md names must resolve. The whole reason this file
        was written was a README pointing at something; a provenance doc that itself dangles is
        worse than none."""
        import re as _re
        with open(PROVENANCE, encoding="utf-8") as fh:
            prov = fh.read()
        missing = []
        for m in _re.finditer(r"`(tools/[\w./-]+|greenfield/[\w./-]+|release-v0\.2/[\w./-]+|"
                              r"\.github/[\w./-]+|[A-Z][A-Z-]+\.md)`", prov):
            rel = m.group(1)
            if any(ch in rel for ch in "*<>") or rel.endswith("/"):
                continue
            if not os.path.exists(os.path.join(REPO, rel)):
                missing.append(rel)
        self.assertFalse(missing, f"PROVENANCE.md references non-existent path(s): {sorted(set(missing))}")

    def test_no_matt_lineage_world_is_tracked(self):
        out = subprocess.run(["git", "ls-files", "worlds/"], cwd=REPO,
                             capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest("not a git checkout")
        self.assertEqual(out.stdout.strip(), "", "a worlds/ tree is tracked again")


if __name__ == "__main__":
    unittest.main()
