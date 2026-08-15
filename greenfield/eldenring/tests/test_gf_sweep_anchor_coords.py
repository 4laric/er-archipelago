#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gates tools/derive_sweep_anchor_coords.py. AP-free: reads text, imports no world.

REPO_ONLY_REASON: needs tools/derive_sweep_anchor_coords.py and the committed greenfield/*.tsv, so
it goes dark against an installed world. Ledgered under GENERATORS in tools/gf_suite_ledger.py --
without that sentinel the ledger cannot SEE this file and reports OK while the suite runs nowhere,
which is the exact failure this repo keeps paying for.

RULE 7. Two of the tool's four refusals cannot fire on current data, and a refusal that has never
fired is UNTESTED, not proven. `ambiguous_sweep_refusal_fires_on_a_synthetic_double_claim` drives
it rather than trusting the zero, and `dungeon_sweeps_is_still_a_partition` measures the premise
that makes the zero true -- so if #363 (multi-boss sweeps duplicating members) ever returns, one
of these two says so instead of the tool quietly anchoring a check at the wrong boss.
"""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GF = os.path.join(ROOT, "greenfield")
TOOL = os.path.join(ROOT, "tools", "derive_sweep_anchor_coords.py")
OUT = os.path.join(GF, "sweep_anchor_coords.tsv")


def _sweeps(text):
    body = text.split("DUNGEON_SWEEPS = {", 1)[1]
    return {f: [m.strip() for m in mem.split(",") if m.strip()]
            for f, mem in re.findall(r"^\s*(\d+): \[([\d, ]*)\],", body, re.M)}


@unittest.skipUnless(os.path.isfile(TOOL), "repo-only tool not present (installed world)")
class SweepAnchorCoords(unittest.TestCase):

    def test_dungeon_sweeps_is_still_a_partition(self):
        """THE PREMISE behind the ambiguous-refusal zero. Measured 2026-08-15: 4045 slots, 4045
        distinct members. If this ever fails, #363 is back and the anchor tool may be guessing."""
        sw = _sweeps(open(os.path.join(GF, "eldenring", "boss_sweeps.py"), encoding="utf-8").read())
        slots = [m for members in sw.values() for m in members]
        self.assertTrue(slots, "no sweep members parsed -- an empty result is a failure")
        dupes = len(slots) - len(set(slots))
        self.assertEqual(dupes, 0,
                         "%d check(s) belong to more than one sweep; the anchor tool's "
                         "AMBIGUOUS refusal is now load-bearing -- verify it fires" % dupes)

    def test_ambiguous_sweep_refusal_fires_on_a_synthetic_double_claim(self):
        """RULE 7: drive the REAL tool down the refusal, do not assert on a local mock.

        Builds a throwaway tree, gives one check to a SECOND arena-bearing sweep, and requires the
        emitted header to count it. Asserting on a dict I built myself would test the scaffolding.
        """
        import shutil
        import tempfile

        sweeps_src = os.path.join(GF, "eldenring", "boss_sweeps.py")
        sw = _sweeps(open(sweeps_src, encoding="utf-8").read())
        arena_flags = set()
        for line in open(os.path.join(GF, "game_areas.tsv"), encoding="utf-8"):
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 10 and p[1].isdigit():
                try:
                    if (float(p[7]), float(p[8]), float(p[9])) != (0.0, 0.0, 0.0):
                        arena_flags.add(p[1])
                except ValueError:
                    pass
        pair = [f for f in sw if f in arena_flags][:2]
        self.assertEqual(len(pair), 2, "need two arena-bearing sweeps to build the case")
        victim = sw[pair[0]][0]

        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "tools"))
            os.makedirs(os.path.join(td, "greenfield", "eldenring"))
            shutil.copy(TOOL, os.path.join(td, "tools"))
            for f in ("game_areas.tsv", "item_grace_coords.tsv"):
                shutil.copy(os.path.join(GF, f), os.path.join(td, "greenfield", f))
            shutil.copy(os.path.join(GF, "eldenring", "data.py"),
                        os.path.join(td, "greenfield", "eldenring"))
            text = open(sweeps_src, encoding="utf-8").read()
            hurt = re.sub(r"(^\s*%s: \[)" % pair[1], r"\g<1>%s, " % victim, text, count=1, flags=re.M)
            self.assertNotEqual(hurt, text, "failed to inject the double-claim")
            open(os.path.join(td, "greenfield", "eldenring", "boss_sweeps.py"), "w",
                 encoding="utf-8").write(hurt)

            subprocess.check_call([sys.executable, os.path.join(td, "tools", os.path.basename(TOOL))],
                                  stdout=subprocess.DEVNULL)
            head = open(os.path.join(td, "greenfield", "sweep_anchor_coords.tsv"),
                        encoding="utf-8").read()

        m = re.search(r"# REFUSED (\d+) AMBIGUOUS SWEEP", head)
        self.assertTrue(m, "the emitted header does not report the AMBIGUOUS SWEEP refusal at all")
        self.assertGreaterEqual(int(m.group(1)), 1,
                                "a check claimed by two DIFFERENT arenas was not refused -- the "
                                "guard is inert and the tool would anchor it at a coin-flip boss")
        self.assertNotIn("\n%s\t" % victim, head,
                         "the ambiguous check was emitted anyway")

    def test_emitted_table_is_not_stale(self):
        before = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else None
        subprocess.check_call([sys.executable, TOOL], stdout=subprocess.DEVNULL)
        self.assertEqual(before, open(OUT, encoding="utf-8").read(),
                         "sweep_anchor_coords.tsv is stale -- re-run the tool and commit")

    def test_never_overwrites_a_real_position(self):
        have = set()
        for line in open(os.path.join(GF, "item_grace_coords.tsv"), encoding="utf-8"):
            p = line.split("\t")
            if len(p) >= 2 and p[0] == "item":
                have.add(p[1])
        rows = [l.rstrip("\n").split("\t") for l in open(OUT, encoding="utf-8")
                if not l.startswith("#") and not l.startswith("ap_location_id")]
        self.assertTrue(rows, "emitted no rows -- an empty result is a failure, not a clean run")
        clash = [r[0] for r in rows if r[1] and r[1] in have]
        self.assertEqual(clash, [], "anchored %d check(s) that already have a real position" % len(clash))

    def test_every_row_is_labelled_weak(self):
        rows = [l.rstrip("\n").split("\t") for l in open(OUT, encoding="utf-8")
                if not l.startswith("#") and not l.startswith("ap_location_id")]
        bad = [r[0] for r in rows if r[-1] != "sweep_arena"]
        self.assertEqual(bad, [], "rows missing the anchor=sweep_arena label: %s" % bad[:5])


if __name__ == "__main__":
    unittest.main(verbosity=2)
