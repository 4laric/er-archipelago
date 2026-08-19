"""Alaric's 2026-08-19 cull ruling: worldless map-lot singles are not checks -- and the class is a
RULE over the committed corpora, never a hand list.

THE STANDARD OF EVIDENCE, met in order: the #330 Rada removal proved param rows can be checks
without being pickups; the census coverage witness (#891) then showed the ground truth was blind in
39 maps, so absence was not yet evidence; the full-MSB rerun closed every blind map; and only then
was the surviving class culled. Two contamination theories were tested and resolved on the way:
scripted awards (real -- excluded by the corpus rule) and Mohgwyn's rune farm (disproven -- the
visible farm runes are flagless enemy drops; the 33 flagged lots reference nothing).

THE CLASS: map-ENCODED flag (ground-loot shaped) + no coords row + no census row + no scripted
corpus mention + not already in _RADA_WORLDLESS. Short flags -- boss drops, NPC handovers, physick
tears -- are structurally out (their award mechanisms are not ground corpora), which is what keeps
provably-live checks like the Great Rune boss drops (f172-176) safe from this rule forever.
"""
import ast
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

PROVEN_SHORT_FLAGS = {172, 173, 175, 176, 400390, 530950, 65010, 65080}


def _emevd_blob():
    """Every event/*.js from the committed gen_inputs bundle, concatenated -- the safety screen's
    corpus. The bundle is committed (9+ MB sqlite of zlib blobs), so this runs anywhere the repo
    does; no Windows artifacts needed."""
    import sqlite3
    import zlib
    db_path = os.path.join(REPO, "gen_inputs.db")
    if not os.path.isfile(db_path):
        return None
    db = sqlite3.connect(db_path)
    parts = []
    for (path, blob) in db.execute("select path, blob from files where path like 'event/%.js'"):
        parts.append(zlib.decompress(blob).decode("utf-8", errors="replace"))
    return "\n".join(parts)


def _map_shaped(fl):
    return ((len(fl) == 8 and fl[:2].isdigit() and 10 <= int(fl[:2]) <= 59)
            or (len(fl) == 10 and fl[:2] in ("10", "20")))


def _gen_literal(name):
    src = os.path.join(REPO, "greenfield", "gen_data.py")
    for node in ast.walk(ast.parse(open(src, encoding="utf-8").read())):
        if (isinstance(node, ast.Assign) and node.targets
                and getattr(node.targets[0], "id", "") == name):
            return set(ast.literal_eval(node.value.args[0]))
    raise AssertionError(f"{name} is gone from gen_data.py")


# Map-shaped rows the derivation names but a RULING keeps live. Each entry carries its witness.
RULED_LIVE_MAP_FLAGS = frozenset({
    10007452,   # Crimson Hood, Roundtable Hold. Awarded by EMEVD event 11100704 in m11_10
                # (flag_names.tsv: "NPC320_Farnese_Replaced with hood item") -- a FLAG-level EMEVD
                # reference the lot-grepping safety screen cannot see. In-repo witness: culling it
                # regressed test_gf_options gear_one_region with a FillError (the hub lost its one
                # spare non-shop gear slot). 2026-08-19.
})


class WorldlessSingles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if REPO is None:
            raise unittest.SkipTest(REPO_ONLY_REASON)
        if REPO not in sys.path:
            sys.path.insert(0, REPO)
        from tools.audit_worldless_checks import audit
        cls.a = audit()
        cls.frozen = _gen_literal("_WORLDLESS_SINGLES")
        cls.rada = _gen_literal("_RADA_WORLDLESS")
        from .. import data
        cls.flags = {int(flag) for rows in data.LOCATIONS.values() for (_n, _a, flag) in rows}

    def test_the_frozen_class_matches_the_rule(self):
        """An input shifting under the frozenset turns red HERE (and shrinking is the loop
        working: a re-export that attributes one of these rows releases it, exactly as m21_02's
        ten Rada rows were released).

        The derivation includes the EMEVD SAFETY SCREEN: a candidate whose lot id appears anywhere
        in the committed event corpus stays a check. Over-inclusive on purpose -- an id that
        resolves is not a table match, but for an exclusion list the asymmetric cost rules: keeping
        an unproven row costs nothing, culling a live one costs a check. The screen is what kept
        the #653 inverted-tower trio and Godefroy's evergaol drop out of the cull."""
        singles = {int(f) for f, _ in self.a["singles"]}
        derived = {f for f in singles if _map_shaped(str(f))} - self.rada
        self.assertTrue(derived, "WITNESS: the rule derives nothing -- corpus or audit broke")
        blob = _emevd_blob()
        self.assertTrue(blob, "WITNESS: gen_inputs.db absent or empty -- the safety screen "
                              "cannot run and equality below would be over the wrong rule")
        import csv as _csv
        lots = {}
        with open(os.path.join(REPO, "greenfield", "flag_lots.tsv"), encoding="utf-8") as fh:
            for row in _csv.DictReader(fh, delimiter="\t"):
                lots.setdefault(row["flag"], []).append(row["lot"])
        derived = {f for f in derived
                   if not any(l in blob for l in lots.get(str(f), ()))}
        # 2026-08-19: #898's audited tile placements are a world reference too. A flag the
        # unplaced-globals datamine can place has a world object by construction; subtract the
        # corpus rather than hand-releasing its rows (8 released the day it landed).
        tiles = set()
        with open(os.path.join(REPO, "greenfield", "unplaced_global_tiles.tsv"), encoding="utf-8") as fh:
            _body = (l for l in fh if not l.startswith("#"))  # the emit writes a comment banner
            for row in _csv.DictReader(_body, delimiter="\t"):
                if row.get("flag", "").isdigit():
                    tiles.add(int(row["flag"]))
        self.assertTrue(tiles, "WITNESS: unplaced_global_tiles.tsv absent or empty -- the "
                               "audited-tile subtraction would be vacuous")
        derived -= tiles
        derived -= RULED_LIVE_MAP_FLAGS
        only_frozen = sorted(self.frozen - derived - self.flags)
        # a frozen flag may legitimately leave the DERIVED set only by leaving the corpus (it is
        # excluded, so the audit cannot see it); one that RE-ENTERS the corpus while still frozen
        # is the drift this test exists for.
        stale = sorted(self.frozen & self.flags)
        self.assertEqual(stale, [], "frozen worldless singles are LIVE locations again -- the "
                                    "corpora now place them; release them from the set: %r"
                         % stale[:8])
        new = sorted(derived - self.frozen)
        self.assertEqual(new, [], "the rule now derives rows the frozenset does not carry -- a "
                                  "regen moved the corpora; extend the set (with the ruling) or "
                                  "explain the arrival: %r" % new[:8])

    def test_the_short_flag_class_is_untouchable(self):
        """The overshoot guard, by name: boss/NPC/quest awards must never enter this cull."""
        culled_short = sorted(f for f in self.frozen if not _map_shaped(str(f)))
        self.assertEqual(culled_short, [], "non-map-shaped flag(s) in _WORLDLESS_SINGLES: %r"
                         % culled_short)
        gone = sorted(PROVEN_SHORT_FLAGS - self.flags)
        self.assertEqual(gone, [], "provably-live short-flag checks left the pool: %r" % gone)

    def test_the_class_is_disjoint_from_rada(self):
        both = sorted(self.frozen & self.rada)
        self.assertEqual(both, [], "a flag sits in BOTH worldless sets -- each ruling must read "
                                   "on its own: %r" % both)

    def test_the_corpus_size_is_pinned(self):
        # 86 -> 78 (2026-08-19, same day): #898's audited unplaced_global_tiles.tsv placed 8 of
        # them -- the derivation below now subtracts that corpus, which is exactly the shrink
        # this message asks to be named.
        self.assertEqual(len(self.frozen), 77,
                         "the cull corpus moved (was 77, ruled 2026-08-19; EMEVD screen -40, audited tiles -8, "
                         "RULED_LIVE -1 off the original 126). A shrink after a "
                         "census improvement is the loop working -- name the released rows; a "
                         "growth needs its own ruling.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
