"""NPC TALK-ESD AWARDS: the gifts and gestures an NPC hands over IN DIALOGUE are invisible to every
screen we have, because every screen we have reads EMEVD or ItemLotParam.

🛑 THIS FILE IS EXPECTED TO BE RED when it lands (2026-07-26). It is a fix SPEC, not a passing
gate -- Alaric hit both failures in-game and asked for them pinned before the fix. The positive
control below is what proves the red is real and not a plumbing problem.

THE MECHANISM
-------------
Roderika (Stormhill Shack) hands over THREE things in one dialogue tree, and the pipeline places
exactly one of them:

  * Golden Seed          lot 101910 / flag 400191  -> LIVE check, 'Limgrave :: Golden Seed -
                         around Stormhill Shack', questline-missable.   ✅ POSITIVE CONTROL
  * Spirit Jellyfish     lot 101900 / flag 400190  -> region_map.csv row ap 7000918 exists, but its
    Ashes                                             region is the PLACEHOLDER 'Global /
                                                      Common-event (unplaced)' with map PENDING.
                                                      `method=global` rows only survive
                                                      gen_data._recover_row_ok if _recover_tile()
                                                      can decode a tile out of the flag NUMBER --
                                                      and a 6-digit 4xxxxx flag encodes no map. So
                                                      it is dropped, is a location NOWHERE, and the
                                                      player is handed the vanilla ashes.   ❌
  * "Sitting Sideways"   an ESD-taught GESTURE     -> gen_data._gesture_derive only scans EMEVD
    (gesture)                                        (`$InitializeCommonEvent` of 90005570 /
                                                     900005571, plus literal `AwardGesture` sites in
                                                     map EMEVDs). A gesture taught by a talk ESD has
                                                     no EMEVD award site at all, so it was never in
                                                     the 14-entry GESTURE_AWARD_FLAGS.   ❌

Both failures are the SAME shape as the two the project has already paid for -- "By My Sword" paying
vanilla in Leyndell (2026-07-14, the EMEVD gesture class) and the White Cipher Ring firing nothing
(2026-07-11, flag 60280 classified `global` and decoded to no tile). The id space is different each
time; the disease is that a check with no decodable MAP silently stops being a check.

DISPOSITION: randomised + MISSABLE, not excluded (Alaric 2026-07-26 -- "it's fine for all the quest
stuff to be randomized and missable, probably better than excluding it"; the same call that scoped
in the 7 NPC/quest gestures in 89b7d8a and widened _QUESTLINE_GATED). So each of these must become
an ordinary collectable check that simply may not host REQUIRED progression.

EVERY ID BELOW IS DERIVED, NOT TYPED
------------------------------------
No gesture id, talk id or acquisition flag is hand-written here except the two lot ids, which are
read straight off committed game-derived tables:
    greenfield/flag_lots.tsv  line 390:  400190  map  101900  ...  236000   (Spirit Jellyfish Ashes)
    greenfield/flag_lots.tsv  line 391:  400191  map  101910  ...  10010    (Golden Seed)
Roderika's talk ids come from esd_gifts.tsv (the ESD rows that hand over lot 101900), and the
gesture flags she teaches come from esd_flags.tsv filtered to those talk ids. If the datamine ever
re-derives a different population, this test follows it instead of pinning yesterday's answer.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_esd_npc_awards.py
  or: python greenfield/eldenring/tests/test_gf_esd_npc_awards.py   (unittest fallback)
No Archipelago import -- same AP-free path-load pattern as test_gf_data.py, so it runs anywhere.
"""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ELDENRING_DIR = os.path.dirname(HERE)
GREENFIELD_DIR = os.path.dirname(ELDENRING_DIR)
DATA_PY = os.path.join(ELDENRING_DIR, "data.py")
MISSABLE_PY = os.path.join(ELDENRING_DIR, "missable_locations.py")

# ---- the only literals in this file: two ItemLotParam_map lot ids, cited above ------------------
LOT_SPIRIT_JELLYFISH_ASHES = 101900   # flag_lots.tsv -> flag 400190, goods 236000
LOT_GOLDEN_SEED = 101910              # flag_lots.tsv -> flag 400191, goods 10010  (positive control)
# The in-game name Alaric reported for the gesture Roderika teaches. The NAME is the assertion, not a
# gesture id: gen_data resolves GestureParam.itemId -> the GoodsName FMG, so if this ever becomes a
# check the id comes from the game data and never from a guess here.
SITTING_SIDEWAYS = "Sitting Sideways"
# ER gesture acquisition flags are group-allocated in a contiguous band; every one of the 14 entries
# in data.GESTURE_AWARD_FLAGS is 608xx or 6086x. Used only to FILTER a datamined flag list.
GESTURE_FLAG_BAND = range(60800, 60900)


def _path_load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tsv(basename):
    """A committed greenfield datamine table, wherever it sits (source tree keeps them in
    greenfield/, the built apworld ships some beside data.py). None if absent -- the tests that need
    one SKIP rather than pass vacuously."""
    for p in (os.path.join(ELDENRING_DIR, basename), os.path.join(GREENFIELD_DIR, basename)):
        if os.path.exists(p):
            return p
    return None


def _rows(basename, fields):
    path = _tsv(basename)
    if path is None:
        return None
    out = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln or ln.startswith("#"):
                continue
            parts = ln.split("\t")
            if len(parts) < len(fields) or parts[0] == fields[0]:
                continue
            out.append(dict(zip(fields, parts)))
    return out


def _flag_of_lot(lot):
    """lot id -> acquisition flag, from flag_lots.tsv. Refuses to answer if the table is absent or
    the lot is ambiguous -- an invented flag is exactly the failure this repo bans."""
    rows = _rows("flag_lots.tsv", ("flag", "table", "lot", "slot", "category", "item_id", "num",
                                   "goods_type", "name"))
    if rows is None:
        return None
    flags = {int(r["flag"]) for r in rows
             if r["lot"].isdigit() and int(r["lot"]) == lot and r["flag"].lstrip("-").isdigit()}
    return flags.pop() if len(flags) == 1 else None


def _roderika_talk_ids():
    """The talk ESDs that hand over her Spirit Jellyfish Ashes lot (esd_gifts.tsv). Derived, so a
    re-emit of the datamine moves this test with it."""
    rows = _rows("esd_gifts.tsv", ("talk_id", "gate_flag", "gate_sense", "item_lot"))
    if rows is None:
        return None
    return {r["talk_id"] for r in rows
            if r["item_lot"].isdigit() and int(r["item_lot"]) == LOT_SPIRIT_JELLYFISH_ASHES}


def _gesture_flags_taught_by(talk_ids):
    """Gesture-band event flags those talk ESDs SET (esd_flags.tsv). An NPC-taught gesture has no
    EMEVD award site, so this is the only handle on it we have."""
    rows = _rows("esd_flags.tsv", ("flag", "sense", "talk_id", "map_id", "how"))
    if rows is None:
        return None
    return {int(r["flag"]) for r in rows
            if r["talk_id"] in talk_ids and r["flag"].isdigit()
            and int(r["flag"]) in GESTURE_FLAG_BAND and r["sense"] == "on"}


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = _path_load("gf_data_esd_awards", DATA_PY)
        cls.missable = _path_load("gf_missable_esd_awards", MISSABLE_PY).MISSABLE_LOCATIONS
        cls.locs = [(region, name, ap_id, flag)
                    for region, entries in cls.data.LOCATIONS.items()
                    for (name, ap_id, flag) in entries]

    def by_flag(self, flag):
        return [t for t in self.locs if t[3] == flag]

    def by_name(self, needle):
        return [t for t in self.locs if needle.lower() in t[1].lower()]

    def assert_questline_missable(self, loc, what):
        _region, name, ap_id, _flag = loc
        self.assertIn(ap_id, self.missable,
                      f"{what} ({name!r}, ap {ap_id}) is a check but is NOT tagged missable -- fill "
                      f"may put required progression on an NPC handover the player can lose")
        self.assertEqual(self.missable[ap_id], "questline",
                         f"{what} is missable for the wrong reason: {self.missable[ap_id]!r}")


class TestRoderikaPositiveControl(_Base):
    """The control. Her Golden Seed comes off the SAME dialogue tree as the two failures below, and
    it is placed and tagged correctly. If this test ever goes red the harness is broken and the two
    reds below say nothing -- fix this one first."""

    def test_her_golden_seed_is_a_questline_missable_check_in_limgrave(self):
        flag = _flag_of_lot(LOT_GOLDEN_SEED)
        if flag is None:
            self.skipTest("flag_lots.tsv absent or ambiguous for the Golden Seed lot")
        found = self.by_flag(flag)
        self.assertEqual(len(found), 1, f"expected exactly one check on f{flag}, got {found}")
        self.assert_questline_missable(found[0], f"Roderika's Golden Seed (f{flag})")


class TestSpiritJellyfishAshesIsDroppedByTheUndecodableFlag(_Base):
    """f400190 has a region_map.csv row, a lot, and an item -- and no MAP. `method=global` survives
    only if `_recover_tile` can decode a tile out of the flag number, and 4xxxxx encodes none, so the
    row is dropped and the ashes pay vanilla. Its sibling f400191 was rescued because the EMEVD scan
    found it in m60_41_38; nothing rescued this one."""

    def test_the_ashes_are_a_live_check(self):
        flag = _flag_of_lot(LOT_SPIRIT_JELLYFISH_ASHES)
        if flag is None:
            self.skipTest("flag_lots.tsv absent or ambiguous for the Spirit Jellyfish Ashes lot")
        found = self.by_flag(flag)
        self.assertEqual(len(found), 1,
                         f"Spirit Jellyfish Ashes (f{flag}) is a location NOWHERE -- Roderika hands "
                         f"over the vanilla item and nothing fires. Expected exactly one check, "
                         f"got {found}")

    def test_the_ashes_land_where_her_golden_seed_lands(self):
        """DERIVED, not asserted: the two gifts come off one dialogue tree, so whatever region the
        pipeline gives the Golden Seed is the region the ashes belong in. Pinning the RELATIONSHIP
        rather than the string means a later Stormhill/Stormveil boundary correction moves both
        together instead of silently splitting one NPC across two regions.

        WARNING -- ASSUMPTION, not invariant, and the weakest claim in this file. RODERIKA
        RELOCATES: esd_flags.tsv puts her talks on m11_10 (Roundtable Hold) as well as the
        overworld, so both gifts are obtainable in two places. The tree has ALREADY made this call
        once -- the Golden Seed f400191 is \'Limgrave :: ... around Stormhill Shack\' despite gating
        on the Roundtable flags 3708/3709 -- so this test only demands the ashes be treated
        CONSISTENTLY with their sibling. If the pair belongs at the HUB instead, change BOTH and
        this test still holds. It costs nothing either way: the missable tag is what keeps required
        progression off them, and that is asserted separately."""
        ashes_flag = _flag_of_lot(LOT_SPIRIT_JELLYFISH_ASHES)
        seed_flag = _flag_of_lot(LOT_GOLDEN_SEED)
        if ashes_flag is None or seed_flag is None:
            self.skipTest("flag_lots.tsv absent")
        ashes, seed = self.by_flag(ashes_flag), self.by_flag(seed_flag)
        if not ashes:
            self.fail(f"Spirit Jellyfish Ashes (f{ashes_flag}) is not a check at all -- see "
                      f"test_the_ashes_are_a_live_check")
        self.assertEqual(len(seed), 1, seed)
        self.assertEqual(ashes[0][0], seed[0][0],
                         f"one NPC, one shack, two regions: ashes in {ashes[0][0]!r} vs Golden Seed "
                         f"in {seed[0][0]!r}")

    def test_the_ashes_are_questline_missable(self):
        flag = _flag_of_lot(LOT_SPIRIT_JELLYFISH_ASHES)
        if flag is None:
            self.skipTest("flag_lots.tsv absent")
        found = self.by_flag(flag)
        if not found:
            self.fail(f"f{flag} is not a check at all -- see test_the_ashes_are_a_live_check")
        self.assert_questline_missable(found[0], f"Spirit Jellyfish Ashes (f{flag})")


class TestEsdTaughtGesturesAreInvisibleToTheEmevdScan(_Base):
    """_gesture_derive reads EMEVD only. A gesture an NPC TEACHES IN DIALOGUE has no EMEVD award
    site, so no amount of widening the EMEVD scan will ever find it -- the ESD is a different corpus
    and needs its own derivation (the tables are already committed: esd_flags.tsv)."""

    def test_sitting_sideways_is_a_live_check(self):
        found = self.by_name(SITTING_SIDEWAYS)
        self.assertEqual(len(found), 1,
                         f"{SITTING_SIDEWAYS!r} is a location NOWHERE -- Roderika teaches the "
                         f"vanilla gesture and nothing fires. Expected exactly one check, "
                         f"got {found}")

    def test_sitting_sideways_is_questline_missable(self):
        found = self.by_name(SITTING_SIDEWAYS)
        if not found:
            self.fail(f"{SITTING_SIDEWAYS!r} is not a check at all -- see "
                      f"test_sitting_sideways_is_a_live_check")
        self.assert_questline_missable(found[0], SITTING_SIDEWAYS)

    def test_every_gesture_roderika_teaches_is_a_check(self):
        """The POPULATION, derived end to end so it cannot calcify into a hand list:
            esd_gifts.tsv  : which talk ESDs hand over lot 101900   -> her talk ids
            esd_flags.tsv  : which gesture-band flags those talks SET -> what she teaches
        Measured on this tree: talks {320001110, 320006000} set gesture-band flags {60803, 60835},
        and data.GESTURE_AWARD_FLAGS (14 entries, all EMEVD-derived) contains NEITHER. Which of the
        two is 'Sitting Sideways' is a question for GestureParam at regen time -- deliberately NOT
        guessed here."""
        talks = _roderika_talk_ids()
        if not talks:
            self.skipTest("esd_gifts.tsv absent (or no row hands over the ashes lot)")
        taught = _gesture_flags_taught_by(talks)
        if taught is None:
            self.skipTest("esd_flags.tsv absent")
        self.assertTrue(taught,
                        f"esd_flags.tsv reports NO gesture-band flag set by talks {sorted(talks)} -- "
                        f"the datamine changed shape; re-derive before trusting this test")
        all_flags = {flag for (_r, _n, _a, flag) in self.locs}
        missing = sorted(taught - all_flags)
        self.assertEqual(missing, [],
                         f"gesture flag(s) {missing} are taught by Roderika's talk ESD "
                         f"(talks {sorted(talks)}) and are checks nowhere. GESTURE_AWARD_FLAGS is "
                         f"EMEVD-only, so an ESD-taught gesture can never appear in it -- the ESD "
                         f"needs its own derivation in gen_data")


if __name__ == "__main__":
    unittest.main()
