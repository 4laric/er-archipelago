#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The page stamps are NARROW -- gen_manifest.BUILDER_INPUTS, and only that.

WHY (2026-09-09). Every offline page embedded the GLOBAL `inputs_hash`, read out of
`greenfield/eldenring/tables/data.py`'s `_GEN_STAMP`. That hash is computed over
`gen_manifest.FILE_INPUTS`, whose FIRST entry is `greenfield/gen_data.py` -- the generator's own
source. So editing a COMMENT in gen_data.py moved the stamp on four pages that read nothing which
had changed, every one of them had to be rebuilt, and each rebuild rewrote a multi-megabyte
single-line JSON payload. Two PRs doing that at once conflict on the whole line. AGENTS.md section
5a says this out loud ("including a comment edit to gen_data.py, which is FILE_INPUTS[0]") and
`tools/regen_all.py`'s docstring records the PR it turned red (#698).

WHAT THIS ASSERTS, and why each half is needed:

  A. THE NARROWING IS REAL. A comment-only edit to `greenfield/gen_data.py` -- in a scratch COPY of
     the repo, never the real tree -- must NOT move any page's stamp. This is the property the
     change was made for, so it is tested directly rather than inferred from the declaration.

  B. THE NARROWING DID NOT GO TOO FAR. An edit to a DECLARED input MUST move that builder's stamp.
     A stamp that never moves is not a narrow stamp, it is a constant -- and a constant passes (A)
     perfectly, which is exactly why (A) alone would be a gate switched off while looking on.

  C. EVERY DECLARED INPUT EXISTS, and every stamp-embedding page builder has a declaration. A
     declaration naming a path that has been renamed hashes as "ABSENT" forever and silently stops
     tracking the file it was written for.

  D. NO DECLARATION NAMES A GENERATOR. `greenfield/gen_data.py` and the datamines are the things
     whose bytes the global hash covers; a page reads their OUTPUT. Naming a generator here would
     re-create the coupling this whole change removes, so it is forbidden rather than remembered.

REPO-ONLY: it reads `tools/` and copies the repo, neither of which gf_test.py installs beside the
world. Ledgered in tools/gf_suite_ledger.py under GENERATORS.

Run: python greenfield/eldenring/tests/test_gf_page_stamp_scope.py
"""
import importlib.util
import os
import re
import shutil
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
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))

# The stamp-embedding page builders, and the BUILDER_INPUTS key each one uses. Typed here on
# purpose: this is the list the test is ABOUT, and deriving it from BUILDER_INPUTS would make (C)
# vacuous -- a builder that silently stopped declaring anything would take its row with it.
BUILDERS = {
    "tools/build_check_browser.py": "check_browser",
    "tools/build_desc_triage.py": "desc_triage",
    "tools/build_questline_dag_page.py": "questline_dag_page",
    "tools/build_region_second_opinion_page.py": "region_second_opinion_page",
}

# Sources whose BYTES the global hash covers and whose OUTPUT the pages read. Declaring one of
# these in BUILDER_INPUTS is the defect this change removed, wearing the new table's clothes.
FORBIDDEN_INPUTS = ("greenfield/gen_data.py", "greenfield/region_groups.py")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gen_manifest(repo):
    return _load(os.path.join(repo, "tools", "gen_manifest.py"), "gm_%d" % abs(hash(repo)))


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class PageStampScope(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gm = _gen_manifest(REPO)

    # -- C / D. the declaration itself -------------------------------------
    def test_every_page_builder_has_a_declaration(self):
        for script, key in sorted(BUILDERS.items()):
            self.assertTrue(os.path.isfile(os.path.join(REPO, *script.split("/"))),
                            "%s is not on disk -- renamed? then rename its BUILDER_INPUTS key too"
                            % script)
            self.assertIn(key, self.gm.BUILDER_INPUTS,
                          "%s embeds a stamp but gen_manifest.BUILDER_INPUTS has no %r entry"
                          % (script, key))
            self.assertTrue(self.gm.BUILDER_INPUTS[key],
                            "BUILDER_INPUTS[%r] is empty -- a stamp over nothing is a constant, "
                            "and a constant cannot go stale" % key)

    def test_every_declared_input_exists(self):
        for key, rels in sorted(self.gm.BUILDER_INPUTS.items()):
            for rel in rels:
                self.assertTrue(
                    os.path.isfile(os.path.join(REPO, *rel.split("/"))),
                    "BUILDER_INPUTS[%r] names %s, which is not on disk. It would hash as ABSENT "
                    "forever, so the file it was written for would stop being tracked SILENTLY."
                    % (key, rel))

    def test_no_declaration_names_a_generator(self):
        for key, rels in sorted(self.gm.BUILDER_INPUTS.items()):
            for bad in FORBIDDEN_INPUTS:
                self.assertNotIn(
                    bad, rels,
                    "BUILDER_INPUTS[%r] declares %s -- a GENERATOR. The pages read its OUTPUT "
                    "(greenfield/eldenring/tables/*.py); hashing the generator's own source is "
                    "exactly the coupling this table exists to remove, and would make a comment "
                    "edit re-stale the page again." % (key, bad))

    # -- A / B. the property, on a scratch copy of the tree -----------------
    def _sandbox(self):
        """A copy of the files any BUILDER_INPUTS entry needs, plus gen_data.py and gen_manifest."""
        tmp = tempfile.mkdtemp(prefix="stampscope_")
        self.addCleanup(shutil.rmtree, tmp, True)
        wanted = {"greenfield/gen_data.py", "tools/gen_manifest.py"}
        for rels in self.gm.BUILDER_INPUTS.values():
            wanted.update(rels)
        for rel in sorted(wanted):
            src = os.path.join(REPO, *rel.split("/"))
            dst = os.path.join(tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
        return tmp

    def test_a_comment_only_edit_to_gen_data_moves_no_page_stamp(self):
        tmp = self._sandbox()
        gm = _gen_manifest(tmp)
        before = {k: gm.builder_hash(tmp, k) for k in gm.BUILDER_INPUTS}

        gd = os.path.join(tmp, "greenfield", "gen_data.py")
        with open(gd, "a", encoding="utf-8") as fh:
            fh.write("\n# a comment that generates nothing (test_gf_page_stamp_scope)\n")

        after = {k: gm.builder_hash(tmp, k) for k in gm.BUILDER_INPUTS}
        self.assertEqual(before, after,
                         "a COMMENT-ONLY edit to greenfield/gen_data.py moved a page stamp. That "
                         "is the whole defect this narrowing removed (AGENTS.md section 5a, "
                         "regen_all.py's docstring, PR #698): the page reads none of gen_data's "
                         "bytes, so its identity must not depend on them.")

        # THE WITNESS. `before == after` is also what a broken hash function returns. Prove the
        # GLOBAL hash really did move on that same edit -- otherwise this test passes for the
        # wrong reason and would keep passing if the narrowing were reverted.
        self.assertNotEqual(
            self.gm.compute_manifest(REPO)["files"]["greenfield/gen_data.py"],
            gm.compute_manifest(tmp)["files"]["greenfield/gen_data.py"],
            "the edit did not change gen_data.py's own digest -- this test proved nothing")

    def test_an_edit_to_a_declared_input_moves_exactly_that_builders_stamp(self):
        tmp = self._sandbox()
        gm = _gen_manifest(tmp)
        moved_for = {}
        # One declared input per builder, chosen as the FIRST one, so this covers every entry's
        # first row rather than a single hand-picked file.
        for key, rels in sorted(gm.BUILDER_INPUTS.items()):
            rel = rels[0]
            before = {k: gm.builder_hash(tmp, k) for k in gm.BUILDER_INPUTS}
            path = os.path.join(tmp, *rel.split("/"))
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n# test_gf_page_stamp_scope touched this\n")
            after = {k: gm.builder_hash(tmp, k) for k in gm.BUILDER_INPUTS}
            moved_for[key] = sorted(k for k in before if before[k] != after[k])
            self.assertIn(key, moved_for[key],
                          "editing %s (a DECLARED input of %r) did NOT move that page's stamp -- "
                          "the stamp is a constant, not a narrow hash" % (rel, key))

    def test_the_builders_read_what_they_declare(self):
        """Every path a builder opens by literal name is declared, or is its own output/template.

        Not a proof that the reading list is complete -- a builder can compute a path -- but it
        catches the cheap and most likely drift: a new tsv joined into a page and never declared,
        which would leave the page's identity unchanged when that tsv moves."""
        lit = re.compile(r'"([A-Za-z0-9_./-]+\.(?:tsv|csv|json))"')
        witnessed = set()
        for script, key in sorted(BUILDERS.items()):
            with open(os.path.join(REPO, *script.split("/")), encoding="utf-8") as fh:
                text = fh.read()
            declared = {os.path.basename(r) for r in self.gm.BUILDER_INPUTS[key]}
            # Calibration files and the builders' own map assets are inlined verbatim rather than
            # joined; they are covered by the template/determinism tests, not by identity.
            allowed = declared | {"map_calibration.json", "map_calibration_dlc.json",
                                  "oracle-missable-queue.tsv", "oracle-region-queue.tsv"}
            found = set(lit.findall(text))
            witnessed |= found & declared
            undeclared = sorted(found - allowed)
            self.assertEqual(
                [], undeclared,
                "%s opens %s by name but BUILDER_INPUTS[%r] does not declare it, so a change to "
                "that table would leave this page's stamp -- its identity -- unmoved."
                % (script, ", ".join(undeclared), key))
        # WITNESS LAST, over the whole sweep: "nothing undeclared" is also what a regex that matched
        # NOTHING says, and a builder that moved to os.path.join would empty this scan silently.
        # Per-builder it cannot be asserted -- build_questline_dag_page.py legitimately names no
        # table literally, it renders the tsv paths its caller hands it -- so the population that
        # has to stay non-empty is the union: some builder, somewhere, still names a DECLARED input
        # by literal string, or this test is comparing two empty sets.
        self.assertGreater(
            len(witnessed), 10,
            "the literal-path scan recognised only %d declared input(s) across %d builder(s); it "
            "has stopped seeing the code and the emptiness assertion above is now vacuous: %s"
            % (len(witnessed), len(BUILDERS), sorted(witnessed)))


if __name__ == "__main__":
    unittest.main()
