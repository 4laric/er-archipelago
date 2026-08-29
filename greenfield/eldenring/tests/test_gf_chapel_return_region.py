"""#1023's acceptance test: the Chapel of Anticipation RETURN is Liurnia, the tutorial half is not.

THE MOTIVATING CASE (255 on Discord, 2026-08-25, via the tracker/spheres report triaged as #1023):
*"same goes for chapel of anticipation being liurnia+limgrave+imbued sword key"*. The chapel floor
has no grace of its own, so nothing a Limgrave Lock lights puts the player on it; the only
repeatable route back is the Four Belfries -> Chapel warp, and the Belfries stand in Liurnia (the
Imbued Sword Key that opens them is itself the Liurnia check f1033477020, #940). The prologue pass
at that floor is a one-shot the game expects you to LOSE, so pinning its drop to sphere-0 Limgrave
sold the Limgrave Lock an access it does not grant.

THE RULING (Alaric 2026-08-25, #1023): "chapel of anticipation return we can model as liurnia."
Implemented as gen_data.FLAG_REGION_OVERRIDE[510030] = "Liurnia" plus its region_overrides.tsv
excuse row (the grace join reads m10_01 = Stormveil).

WHAT MOVES IS EXACTLY ONE FLAG, AND THIS FILE PINS BOTH HALVES OF THAT.
The chapel floor is authored inside m10_01, not inside the tutorial map m18_00: m10_01's own EMEVD
names the fight `$Event(10012800)` チュートリアルボス撃破 ("Defeat the tutorial boss"), which sets
9103 on 10010800's death, and `common.emevd $Event(1100)` slot 3 pays lot 10030 out under flag
510030 -- the Grafted Scion's Ornamental Straight Sword + Golden Beast Crest Shield. So f510030 is
the chapel-return check and the ONLY one.

m18_00's twelve rows STAY Limgrave and the test says so, because #1023's own candidate list
suspected three of them and the evidence refutes all three:
  * 18007000-18007070 are MSB treasures literally named 宝死体00X チュートリアルEX / チュートリアル入り口
    ("tutorial"), and item_grace_coords.tsv puts them on the descending Cave of Knowledge run
    (y +3.9 down to -88.8) around graces 71800/71801 -- prologue ground;
  * 18007900 (Erdtree Greatbow) is NOT a chapel chest: m18_00's EMEVD awards lot 18000900 from the
    CHARIOT event, `AwardItemsIncludingClients(18000900)` at the end of the block that force-kills
    18000400 (flag_names: チャリオット吊り下げ火炎樽で破壊, $Event(18002450)) -- Fringefolk Hero's Grave;
  * 510280 (Golden Seed) is paid on flag 9128, set by `$Event(18002800)` on the death of 18000800 --
    a 15000-rune boss (game_areas.tsv) standing at y -111.57, BELOW the whole tutorial run; and
    18007700 (Dragon Communion Seal) is its neighbour on enemy lot 301000010. Fringefolk Hero's
    Grave again, reached on foot from the Stranded Graveyard with Stonesword Keys.
Under-moving is the safe direction here: a row left in Limgrave is early, a row moved wrongly is a
check nobody can reach.
"""
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
# gen_data.py is NOT copied in beside the installed package, so the three assertions that read it
# (and region_overrides.tsv, which the ORACLE reads out of greenfield/) need the checkout. CI's
# --ap-dir sits inside the repo, so find_repo_root resolves and they RUN there; they skip only on a
# genuinely detached install. Never run them blind -- see _util.find_repo_root.
IN_REPO = REPO is not None

CHAPEL_FLAG = 510030
CHAPEL_APS = {
    # 2026-08-26 (#1013, Enia vanilla): the ap ids below moved because Enia's hundred hub rows
    # left the corpus, which renumbers every LATER ap id. That is this branch's change, NOT a
    # region move and NOT a renumbering bug. Every id here was RE-READ from the regenerated
    # data.py by flag, never by subtracting 100 from the old one.
    7773786: "Ornamental Straight Sword",  # -1 after dead f400020 left the pool (#1111)
    7900113: "Golden Beast Crest Shield",
}
CHAPEL_REGION = "Liurnia"

# Every live m18_00 check, and the region each must KEEP. Flags from greenfield/check_maps.tsv;
# 60000 (Tailoring Tools award) is not a live check and is deliberately absent.
TUTORIAL_MAP_FLAGS = (
    18007000, 18007010, 18007020, 18007030, 18007040, 18007050,
    18007060, 18007070, 18007700, 18007900, 60220, 510280,
)
TUTORIAL_REGION = "Limgrave"


class ChapelReturnIsLiurnia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .. import data
        cls.by_ap = {}
        cls.by_flag = {}
        for region, rows in data.LOCATIONS.items():
            for (name, ap, flag) in rows:
                cls.by_ap[ap] = (region, name)
                cls.by_flag.setdefault(int(flag), []).append((region, name, ap))

    def test_both_scion_drops_present_as_liurnia(self):
        """The ruling, at the surface a player and the tracker actually read."""
        rows = self.by_flag.get(CHAPEL_FLAG) or []
        self.assertEqual(
            len(rows), len(CHAPEL_APS),
            "f%d should carry exactly the Scion's two drops; got %r" % (CHAPEL_FLAG, rows))
        for region, name, ap in rows:
            self.assertIn(ap, CHAPEL_APS, "unexpected ap id on f%d: %d" % (CHAPEL_FLAG, ap))
            self.assertEqual(
                region, CHAPEL_REGION,
                "#1023: %s (ap %d) is the Chapel of Anticipation RETURN and must present as %s, "
                "not %s -- the Belfry warp is the access and the Belfries are Liurnia's."
                % (CHAPEL_APS[ap], ap, CHAPEL_REGION, region))
            self.assertTrue(
                name.startswith(CHAPEL_REGION + " ::"),
                "the location NAME prefix must move with the region: %r" % name)

    def test_the_ap_ids_did_not_move(self):
        """A region move re-sorts names; it must never renumber an id (#952)."""
        for ap, item in CHAPEL_APS.items():
            self.assertIn(ap, self.by_ap, "ap id %d (%s) vanished" % (ap, item))
            self.assertIn(item, self.by_ap[ap][1])

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_the_pin_is_the_declared_mechanism(self):
        """The move is one FLAG_REGION_OVERRIDE row, not a map-scoped curation that would drag
        the rest of m10_01 (Stormveil) along with it."""
        self.assertEqual(_gen_literal("FLAG_REGION_OVERRIDE").get(CHAPEL_FLAG), CHAPEL_REGION)
        self.assertNotIn("m10_01_00_00", _gen_literal("DUNGEON_REGION_CURATED"))

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_the_override_is_excused_to_the_independent_oracle(self):
        """m10_01's grace truth is Stormveil, so the provenance oracle needs the reasoned row --
        an override with no recorded reason is the failure mode region_overrides.tsv exists for."""
        path = os.path.join(REPO, "greenfield", "region_overrides.tsv")
        rows = [ln.rstrip("\n").split("\t") for ln in open(path, encoding="utf-8")
                if ln.strip() and not ln.startswith("#")]
        hits = [r for r in rows if len(r) >= 4 and r[0] == "flag" and r[1] == str(CHAPEL_FLAG)]
        self.assertEqual(len(hits), 1, "expected exactly one region_overrides row for f%d" % CHAPEL_FLAG)
        self.assertEqual(hits[0][2], CHAPEL_REGION)
        self.assertIn("1023", hits[0][3], "the row must cite the ruling that made it")

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_the_scion_still_hosts_no_progression(self):
        """The move must not smuggle a missable one-shot fight into the progression surface."""
        self.assertIn(CHAPEL_FLAG, _gen_literal("_SURFACE_EXCLUDE_FLAGS"))
        self.assertIn(CHAPEL_FLAG, _gen_literal("QUEST_GATED_FLAGS"))


class TheTutorialMapDidNotMove(unittest.TestCase):
    """m18_00 is the Cave of Knowledge / Stranded Graveyard / Fringefolk Hero's Grave map. None of
    it is the chapel floor, so none of it moves -- see this module's docstring for the evidence."""

    @classmethod
    def setUpClass(cls):
        from .. import data
        cls.by_flag = {}
        for region, rows in data.LOCATIONS.items():
            for (name, ap, flag) in rows:
                cls.by_flag.setdefault(int(flag), []).append((region, name, ap))

    def test_every_m18_00_check_stays_limgrave(self):
        for flag in TUTORIAL_MAP_FLAGS:
            rows = self.by_flag.get(flag) or []
            self.assertTrue(rows, "f%d is no longer a check -- re-derive this list from "
                                  "greenfield/check_maps.tsv before editing it" % flag)
            for region, name, ap in rows:
                self.assertEqual(
                    region, TUTORIAL_REGION,
                    "#1023 moved ONLY f%d. f%d (%s, ap %d) is m18_00 -- prologue ground or "
                    "Fringefolk Hero's Grave, both walkable from Limgrave -- and must stay %s, "
                    "got %s." % (CHAPEL_FLAG, flag, name, ap, TUTORIAL_REGION, region))


def _gen_literal(name):
    """Read one module-level literal out of gen_data.py by AST.

    gen_data is NOT imported: importing it runs the whole generator, which needs
    elden_ring_artifacts/ and rewrites the tree. A gate that has to run the thing it gates is
    not a gate. The first literal-evaluable binding of `name` wins (QUEST_GATED_FLAGS is later
    extended by expressions the reader deliberately does not follow).
    """
    import ast
    tree = ast.parse(open(os.path.join(REPO, "greenfield", "gen_data.py"), encoding="utf-8").read())
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        tgt = node.targets[0]
        if not (isinstance(tgt, ast.Name) and tgt.id == name):
            continue
        value = node.value
        if isinstance(value, ast.Call) and value.args:      # frozenset({...})
            value = value.args[0]
        try:
            return ast.literal_eval(value)
        except ValueError:
            continue
    raise AssertionError("gen_data.py has no literal binding for %s" % name)


if __name__ == "__main__":
    unittest.main()
