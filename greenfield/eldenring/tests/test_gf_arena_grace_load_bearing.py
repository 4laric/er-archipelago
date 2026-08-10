"""ARENA-GRACE RETIREMENT GATE (tier A: runs with NO artifacts).

`test_gf_grace_skip_oracle.py` adjudicates `_BOSS_GATED_GRACE_FLAGS` from the EMEVD and says so
plainly: `_ARENA_GRACE_FLAGS` graces "emit NO 9005810 signal -- those are out of scope for this EMEVD
oracle by construction, and this gate does not adjudicate them." The MSB-derived oracle
(`arena_graces.tsv`) is supposed to be the one that does.

THE HOLE THIS GATE CLOSES (2026-08-10)
--------------------------------------
`arena_graces.tsv`'s `adjudicated_tiles:` header says a map's MSB was UNPACKED. It does NOT say every
boss on that map was LOCATED: `datamine_arena_graces.py` drops any `DisplayBossHealthBar` entity that
is not an MSB `Part/Enemy` (`if b in ep`), and the tile still counted adjudicated. So a grace standing
inside that boss's arena is absent from the derived set for the same reason a safe grace is -- and
"tile adjudicated + grace absent" reads as "measured safe" when it means "nobody looked at that boss".

76931 "Shadow Keep, Back Gate" is that case. Its tile m61_49_48 is in `adjudicated_tiles`; it is not
in the derived set; and it stands in front of Commander Gaius (2049480800). The header was read the
wrong way round on 2026-08-10 and the grace was called wrongly-withheld. It is withheld CORRECTLY, by
the hand list, and the hand list is the ONLY thing withholding it.

gen_data's `_ARENA_GRACE_LOAD_BEARING` records that. This test pins it so the record cannot be
deleted alongside the thing it protects, and pins the tool's per-boss reporting so the evidence keeps
being produced. All four assertions read committed source -- no MSBs, no EMEVD, no gen run.
"""
import ast
import os
import re
import sys
import unittest

try:
    from ._util import find_repo_root
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root

ROOT = find_repo_root(os.path.abspath(__file__))
GEN = os.path.join(ROOT, "greenfield", "gen_data.py")
TOOL = os.path.join(ROOT, "tools", "datamine_arena_graces.py")
GRACE_FLAGS = os.path.join(ROOT, "greenfield", "grace_flags.tsv")
HEALTHBARS = os.path.join(ROOT, "greenfield", "eldenring", "boss_healthbars.py")

# The motivating case, spelled out rather than read from the table it guards -- a pin that sources
# itself from its subject cannot fail when the subject is deleted.
MOTIVATING_FLAG = 76931
MOTIVATING_BOSS = 2049480800
MOTIVATING_TILE = "m61_49_48"


def _src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _frozenset_literal(src, name):
    m = re.search(r"%s\s*=\s*frozenset\((\{.*?\})\)" % re.escape(name), src, re.S)
    assert m, "could not parse %s from gen_data.py (shape changed?)" % name
    return {int(x) for x in ast.literal_eval(m.group(1))}


def _load_bearing(src):
    """-> {flag: boss}. Parsed from the literal, tolerating the (boss, why) tuple shape."""
    m = re.search(r"_ARENA_GRACE_LOAD_BEARING\s*=\s*(\{.*?\n\})", src, re.S)
    assert m, "could not parse _ARENA_GRACE_LOAD_BEARING from gen_data.py"
    return {int(k): int(v[0]) for k, v in ast.literal_eval(m.group(1)).items()}


class ArenaGraceRetirementGate(unittest.TestCase):

    def test_every_load_bearing_entry_is_still_in_the_hand_list(self):
        """The gate itself. Retiring a load-bearing flag must not be possible quietly."""
        src = _src(GEN)
        hand = _frozenset_literal(src, "_ARENA_GRACE_FLAGS")
        gone = sorted(set(_load_bearing(src)) - hand)
        self.assertFalse(gone, (
            "%s recorded LOAD-BEARING in _ARENA_GRACE_LOAD_BEARING but MISSING from "
            "_ARENA_GRACE_FLAGS. The derived oracle's silence is not evidence: check "
            "arena_graces.tsv's `unresolved_bosses:` for that boss first." % gone))

    def test_the_gaius_case_is_pinned_by_value(self):
        """76931 specifically. Deleting the row AND the gate still fails here."""
        src = _src(GEN)
        self.assertIn(MOTIVATING_FLAG, _frozenset_literal(src, "_ARENA_GRACE_FLAGS"),
                      "76931 'Shadow Keep, Back Gate' stands in front of Commander Gaius. Force-"
                      "lighting it warps the player into his arena. It may only leave the hand list "
                      "once datamine_arena_graces.py RESOLVES boss 2049480800 -- see this test's "
                      "docstring for why the derived set's silence does not license it.")
        self.assertEqual(_load_bearing(src).get(MOTIVATING_FLAG), MOTIVATING_BOSS,
                         "the 76931 entry must stay keyed on Gaius's healthbar entity")

    def test_load_bearing_evidence_is_coherent(self):
        """Each entry's grace and its named boss must actually share a tile."""
        lb = _load_bearing(_src(GEN))

        grace_tile = {}
        with open(GRACE_FLAGS, encoding="utf-8") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if p and p[0].isdigit():
                    grace_tile[int(p[0])] = p[1]

        hb = _src(HEALTHBARS)
        for flag, boss in sorted(lb.items()):
            m = re.search(r"\b%d:\s*\('[^']*',\s*'([^']*)'" % boss, hb)
            self.assertTrue(m, "boss %d (for grace %d) is not in boss_healthbars.py" % (boss, flag))
            self.assertEqual(grace_tile.get(flag), m.group(1),
                             "grace %d is on tile %s but its load-bearing boss %d is on %s -- the "
                             "evidence does not line up" % (flag, grace_tile.get(flag), boss,
                                                            m.group(1)))
        self.assertEqual(grace_tile.get(MOTIVATING_FLAG), MOTIVATING_TILE)

    def test_the_tool_still_reports_per_boss(self):
        """The evidence must keep being produced, or the gate above ossifies into a hand list of its
        own. Reverting the tool to per-MAP `unresolved` fails here."""
        tool = _src(TOOL)
        self.assertIn("unresolved_bosses", tool,
                      "datamine_arena_graces.py no longer tracks per-BOSS resolution -- "
                      "`adjudicated_tiles:` alone cannot tell 'measured safe' from 'nobody looked'")
        self.assertIn("# unresolved_bosses:", tool,
                      "the tool must EMIT the `unresolved_bosses:` header so gen_data can read it")
        self.assertRegex(tool, r"missing\s*=\s*sorted\(b for b in bosses\[map_id\] if b not in ep\)",
                         "the per-boss miss set is what makes the header meaningful")


if __name__ == "__main__":
    unittest.main()
