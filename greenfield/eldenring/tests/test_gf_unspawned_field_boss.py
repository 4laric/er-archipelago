r"""A boss that DOES NOT EXIST may not own a sweep -- issue #540, and the general shape of it.

MOTIVATING CASE (CONTRIBUTING rule 11), boblerrr's Mt. Gelmir playtest 2026-08-10, falsified in
game by Alaric the same day:

    `1038540800` "Fallingstar Beast" (tile m60_38_54, Mt. Gelmir) has a boss healthbar, a defeat
    event flag, a name, and 23 sweep members. Warp to First Mt. Gelmir Campsite (grace 76351) and
    THERE IS NO BEAST. It is EMEVD-only -- a complete boss script for a character the MSB never
    places -- the same class as `34150800` (Isolated Divine Tower, confirmed absent 2026-08-05).

    Its defeat flag can therefore never be set, and 23 of Mt. Gelmir's 222 checks -- 10.4% of the
    region, twelve of them the pickups ringing the campsite the beast is supposed to stand beside
    -- sat behind a trigger that cannot fire.

THE TELLS THAT CAUGHT `34150800` DO NOT CATCH THIS ONE. That one had `DisplayBossHealthBar` nameId
0 and lived on a map with zero checks. This one is NAMED and carries 23 checks. A detector built on
the first case's tells would have been silent here -- which is why the fix is a SHAPE and not a
second id in a list. Two have now been found by hand; there is no reason to think the second is the
last.

THE SHAPE (gen_data._unspawned_candidate), from three committed tables and no hand list:
  (1) class == field, tile decodes m60_XX_YY
  (2) game_areas.tsv (GameAreaParam) knows NO ARENA ON THAT TILE
  (3) arena_graces.tsv `adjudicated_tiles` CONTAINS the tile -- the MSB *was* unpacked, so an
      absence there is a measurement rather than a gap
  (4) arena_graces.tsv `unresolved_bosses` CONTAINS the boss -- and it is not an MSB Part

(2) IS KEYED ON THE TILE, NOT ON THE FLAG, and that is the whole difference between a detector and
a coincidence. BOSS_HEALTHBARS is keyed by DEFEAT FLAG; GameAreaParam is keyed by ENTITY id; for a
night-class boss those differ (Death Rite Bird m60_36_45: entity 1036450340, flag 1036450800).
Ask "is this FLAG in game_areas?" and 13 of the 79 field bosses answer no -- twelve of them
spuriously (Night's Cavalry x2, Deathbird x2, Death Rite Bird, Tibia Mariner, Fire Giant, Borealis,
the 12-prefix festival Radahn, ...), every one of which has an arena ON ITS TILE under the 03xx or
12-prefix id. Ask the TILE and the twelve fall away by themselves: no roaming/night name list, no
duplicate carve-out, nothing to keep in sync with a boss roster.

WHAT THIS FILE GATES, in three tiers:
  * the DETECTOR, re-derived here from the tsvs so a gen_data bug cannot hide behind shared code;
  * the MOTIVATING CASE -- 1038540800 owns no group, and its 23 members are still swept, still in
    Mt. Gelmir, by a boss that exists;
  * REACHABILITY on the seed shape the report came from: num_regions 1, Mt. Gelmir kept.

Run:  python greenfield/eldenring/tests/test_gf_unspawned_field_boss.py
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
GREENFIELD = os.path.dirname(GF_PKG)


def _beside(name):
    """A gen INPUT tsv: beside the package in the source tree, INSIDE it once installed (the
    world-install step copies every greenfield/*.tsv in). First existing wins -- the same
    resolution test_gf_boss_sweeps.py uses, so this gate runs in the installed-world pytest too
    instead of quietly asserting nothing there."""
    for p in (os.path.join(GF_PKG, name), os.path.join(GREENFIELD, name)):
        if os.path.isfile(p):
            return p
    return None


def _mod(name):
    path = os.path.join(GF_PKG, name + ".py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("gf_" + name + "_unspawned", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_M60_TILE_RE = re.compile(r"^m60_\d\d_\d\d$")


def _arena_tiles():
    """Every map/tile GameAreaParam knows an ARENA on (the boss_map column)."""
    path = _beside("game_areas.tsv")
    tiles = set()
    if not path:
        return tiles
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line[:1] == "#" or line.startswith("area_id"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) > 6 and p[0].isdigit() and p[6]:
                tiles.add(p[6])
    return tiles


def _arena_grace_headers():
    """(adjudicated tiles, unresolved bosses) out of arena_graces.tsv's header block.

    Its own header states what these mean: adjudicated = the map's MSB was unpacked; unresolved =
    the DisplayBossHealthBar entities on it that are NOT MSB Parts and so have no position."""
    path = _beside("arena_graces.tsv")
    adjudicated, unresolved = set(), set()
    if not path:
        return adjudicated, unresolved
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("# adjudicated_tiles:"):
                adjudicated |= {t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()}
            elif line.startswith("# unresolved_bosses:"):
                for chunk in line.split(":", 1)[1].split(","):
                    _tile, _sep, ents = chunk.strip().partition(":")
                    for e in ents.split("+"):
                        if e.strip().isdigit():
                            unresolved.add(int(e))
    return adjudicated, unresolved


def _shape():
    """Re-derive the unspawned shape from the tsvs -- gen_data's answer is NOT consulted."""
    hb = _mod("boss_healthbars")
    if hb is None:
        return None
    arena_tiles = _arena_tiles()
    adjudicated, unresolved = _arena_grace_headers()
    if not arena_tiles or not adjudicated or not unresolved:
        return None
    out = set()
    for ent, (_bmap, tile, cls, _name) in hb.BOSS_HEALTHBARS.items():
        if cls != "field" or not _M60_TILE_RE.match(tile or ""):
            continue
        t00 = tile + "_00"
        if t00 in arena_tiles or t00 not in adjudicated:
            continue
        if ent in unresolved:
            out.add(ent)
    return out


FALLINGSTAR = 1038540800    # boss_healthbars: ('m60_38', 'm60_38_54', 'field', 'Fallingstar Beast')
GELMIR = "Mt. Gelmir"

# KEYED ON THE ACQUISITION FLAG, NEVER ON THE AP ID. A regen renumbers the positional ap id space,
# so an ap-keyed fixture fires on every unrelated change and gets switched off inside a month (the
# lesson test_gf_tutorial_boss_no_sweep records at length). These 23 are what
# DUNGEON_SWEEPS[1038540800] held on 0f3bd5a; twelve are on the beast's own tile m60_38_54 -- the
# pickups ringing the campsite it is not standing beside.
FALLINGSTAR_MEMBER_FLAGS = (
    1038547000,   # Bloodrose - near First Mt. Gelmir Campsite
    1038547010,   # Explosive Greatbolt - near First Mt. Gelmir Campsite
    1038547020,   # Golden Rune [8] - near First Mt. Gelmir Campsite
    1038547030,   # Fire Arrow - near First Mt. Gelmir Campsite
    1038547050,   # [Incantation] Golden Vow - near First Mt. Gelmir Campsite
    1038547060,   # Arteria Leaf - near First Mt. Gelmir Campsite
    1038547070,   # Throwing Dagger - near First Mt. Gelmir Campsite
    1038547080,   # Beast Blood - near First Mt. Gelmir Campsite
    1038547090,   # Smithing Stone [5] - near Shaded Castle Inner Gate
    1038547100,   # Antspur Rapier - around First Mt. Gelmir Campsite
    1038547110,   # Pulley Bow - near First Mt. Gelmir Campsite
    1038547700,   # Sacred Butchering Knife - around First Mt. Gelmir Campsite
    1039537000,   # Golden Rune [4] - near Bridge of Iniquity
    1039537010,   # Blood Grease - near Bridge of Iniquity
    1039537020,   # Golden Rune [3] - near Old Altus Tunnel
    1039537030,   # Miquella's Lily - near Bridge of Iniquity
    1039537040,   # Nascent Butterfly - near Bridge of Iniquity
    1039537050,   # [Sorcery] Unseen Blade - near Bower of Bounty
    1039537060,   # Slumbering Egg - near Bower of Bounty
    1039537070,   # Golden Rune [3] - near Bower of Bounty
    1039537080,   # Mirage Riddle - around Bridge of Iniquity
    1039537700,   # Crepus's Vial - around Bridge of Iniquity
    1039537750,   # Golden Rune [10] - around Bridge of Iniquity
)


class UnspawnedDetector(unittest.TestCase):
    """Tier A: the SHAPE, re-derived from the tsvs, must agree with what gen_data classified."""

    def setUp(self):
        self.sweeps = _mod("boss_sweeps")
        if self.sweeps is None:
            self.skipTest("boss_sweeps.py absent -- run gen_data.py")
        self.shape = _shape()
        if self.shape is None:
            self.skipTest("boss_healthbars.py / game_areas.tsv / arena_graces.tsv not beside the "
                          "package -- the detector cannot be re-derived here")

    def test_the_detector_catches_the_boss_that_started_this(self):
        """Fixture rot guard: a shape that no longer selects 1038540800 gates nothing."""
        self.assertIn(FALLINGSTAR, self.shape,
                      "the unspawned shape no longer catches 1038540800 (Fallingstar Beast, "
                      "m60_38_54) -- the case it was built from, confirmed absent in game. Either "
                      "game_areas.tsv gained an arena on that tile (then the boss EXISTS: say so "
                      "and delete the verdict) or a header this reads has moved.")

    def test_the_detector_does_not_catch_the_roaming_and_night_bosses(self):
        """The twelve the FLAG-keyed reading false-positives on must NOT be in the shape.

        This is the discriminator under test, not a decoration: keyed on the defeat flag these all
        look rowless, and a detector that fired on them would delete a dozen real sweeps."""
        hb = _mod("boss_healthbars")
        arena_tiles = _arena_tiles()
        flag_keyed = {e for e, (_m, t, c, _n) in hb.BOSS_HEALTHBARS.items()
                      if c == "field" and _M60_TILE_RE.match(t or "")
                      and (t + "_00") not in arena_tiles}
        cleared = flag_keyed - self.shape
        self.assertTrue(cleared,
                        "the tile-keyed detector cleared NOBODY the flag-keyed reading flags, so "
                        "the discriminator this file is about is not being exercised")
        for ent in sorted(cleared):
            self.assertNotIn(ent, self.sweeps.SWEEP_UNSPAWNED,
                             "%d was cleared by the tile-keyed detector yet gen_data dropped its "
                             "sweep anyway" % ent)

    def test_every_candidate_carries_a_reviewed_verdict(self):
        """A shape match is a QUESTION. Only a verdict may delete a sweep, and gen_data refuses to
        build without one -- this asserts the two tables agree once it has."""
        judged = set(self.sweeps.SWEEP_UNSPAWNED) | set(self.sweeps.SWEEP_UNSPAWNED_OPEN)
        self.assertTrue(judged, "gen_data classified NOBODY, so the equality below is between two "
                                "empty sets and gates nothing")
        self.assertEqual(self.shape, judged,
                         "the unspawned shape is %s but gen_data classified %s. A NEW id here is "
                         "the third boss of this kind: warp to its tile, look, and record the "
                         "verdict in gen_data._UNSPAWNED_VERDICTS ('unspawned' if there is no "
                         "boss, 'open' if you have not looked). Do NOT widen the shape to make "
                         "this pass." % (sorted(self.shape), sorted(judged)))
        for ent, reason in sorted(self.sweeps.SWEEP_UNSPAWNED.items()):
            self.assertTrue(reason.strip(),
                            "%d is dropped with no evidence recorded -- a sweep may not vanish on "
                            "an unattributed claim" % ent)

    def test_an_unfalsified_candidate_keeps_its_sweep(self):
        """The asymmetry, stated as a test: deleting a REAL boss's reward is the worse error.

        1041330800 (unnamed, m60_41_33 = Fourth Church of Marika) has the same shape and has NOT
        been looked at in game, so it keeps its 10 members until someone stands on the tile."""
        self.assertTrue(self.sweeps.SWEEP_UNSPAWNED_OPEN,
                        "no candidate is OPEN, so this gate is vacuous -- if the last one was "
                        "resolved in game, say so here rather than leaving an empty loop")
        for ent in self.sweeps.SWEEP_UNSPAWNED_OPEN:
            self.assertIn(ent, self.sweeps.DUNGEON_SWEEPS,
                          "%d is only a CANDIDATE (no in-game falsification) yet its sweep is "
                          "gone. Only a verdict of 'unspawned' may drop a trigger." % ent)


class TheBeastThatIsNotThere(unittest.TestCase):
    """Tier B: the motivating case itself."""

    def setUp(self):
        self.sweeps = _mod("boss_sweeps")
        self.data = _mod("data")
        if self.sweeps is None or self.data is None:
            self.skipTest("generated modules absent -- run gen_data.py")
        self.region_of = {}
        self.ap_of = {}
        for region, rows in self.data.LOCATIONS.items():
            for (_name, ap, flag) in rows:
                self.region_of[int(flag)] = region
                self.ap_of[int(flag)] = int(ap)

    def test_the_unspawned_boss_owns_no_sweep(self):
        # assertTrue, not assertNotIn: assertNotIn renders the WHOLE of DUNGEON_SWEEPS into the
        # failure text (219 lists, ~90 KB) and buries the sentence that says what is wrong.
        self.assertTrue(FALLINGSTAR not in self.sweeps.DUNGEON_SWEEPS,
                        "1038540800 has a sweep again, of %d check(s) in %r. There is no beast on "
                        "m60_38_54 -- Alaric warped to grace 76351 on 2026-08-10 -- so that flag "
                        "can never be set and those checks are auto-granted by nothing."
                        % (len(self.sweeps.DUNGEON_SWEEPS.get(FALLINGSTAR, [])),
                           self.sweeps.SWEEP_REGION.get(FALLINGSTAR)))
        self.assertNotIn(FALLINGSTAR, self.sweeps.SWEEP_REGION)
        self.assertNotIn(FALLINGSTAR, self.sweeps.SWEEP_ARENA_REGION)
        self.assertIn(FALLINGSTAR, self.sweeps.SWEEP_UNSPAWNED,
                      "the trigger is gone but nothing records WHY, so the next regen puts it back")

    def test_the_23_checks_still_exist_and_are_still_mt_gelmir(self):
        """The fix removes a TRIGGER, not the checks. They were always obtainable by hand."""
        self.assertTrue(self.region_of,
                        "the location table read EMPTY -- every assertion below would pass for the "
                        "wrong reason")
        self.assertEqual(len(FALLINGSTAR_MEMBER_FLAGS), 23,
                         "the fixture is no longer 23 checks; 23 is the measured size of the group "
                         "this issue is about")
        missing = [f for f in FALLINGSTAR_MEMBER_FLAGS if f not in self.region_of]
        self.assertFalse(missing,
                         "check flag(s) %s left the location table with the sweep. A sweep is a "
                         "convenience auto-grant; removing one may not remove a check." % missing)
        elsewhere = {f: self.region_of[f] for f in FALLINGSTAR_MEMBER_FLAGS
                     if self.region_of[f] != GELMIR}
        self.assertFalse(elsewhere, "check(s) left Mt. Gelmir with the trigger: %s" % elsewhere)

    def test_all_23_re_home_to_a_boss_that_exists_in_the_same_region(self):
        """The redistribution, and the reason no second mechanism was needed.

        Dropping the trigger hands its tile's filler back to the FIELD NEIGHBOURHOOD pass, which
        assigns every overworld filler check to the nearest SAME-REGION field boss. Measured on the
        regen: all 23 stayed in Mt. Gelmir, 12 to 1037540810 (Ulcerated Tree Spirit, m60_37_54) and
        11 to 1037530800 (Demi-Human Queen Maggie, m60_37_53). ADDED 0, REMOVED 0, 23 RE-OWNED,
        zero region crossings."""
        owner = {ap: trig for trig, aps in self.sweeps.DUNGEON_SWEEPS.items() for ap in aps}
        self.assertGreater(len(owner), 3000,
                           "the sweep corpus read as %d member(s); an empty or truncated "
                           "DUNGEON_SWEEPS would make every check below vacuously fine"
                           % len(owner))
        orphans, wrong_region, unspawned_owner = [], {}, {}
        for flag in FALLINGSTAR_MEMBER_FLAGS:
            trig = owner.get(self.ap_of[flag])
            if trig is None:
                orphans.append(flag)
                continue
            if self.sweeps.SWEEP_REGION.get(trig) != GELMIR:
                wrong_region[flag] = (trig, self.sweeps.SWEEP_REGION.get(trig))
            if trig in self.sweeps.SWEEP_UNSPAWNED:
                unspawned_owner[flag] = trig
        self.assertFalse(orphans,
                         "%d of the 23 belong to NO sweep now: %s. Re-homing them was the point -- "
                         "a check that lost its only trigger has traded a flag that never fires "
                         "for no flag at all." % (len(orphans), orphans))
        self.assertFalse(wrong_region,
                         "check(s) re-homed to a trigger OUTSIDE Mt. Gelmir: %s. A sweep may only "
                         "be paid by a boss that lives where the checks live (#445)." % wrong_region)
        self.assertFalse(unspawned_owner,
                         "check(s) re-homed onto ANOTHER boss that does not exist: %s"
                         % unspawned_owner)


# ---- Tier C: the seed shape the report came from -----------------------------------------------
# A CONDITIONAL CLASS, not a module-level `pytest.importorskip`. importorskip would skip the WHOLE
# module when Archipelago is absent, taking tiers A and B -- which need no AP at all -- down with
# it, and it makes `python <this file>` raise instead of running them. Defining the AP tier only
# when AP is importable keeps the pure tiers runnable everywhere and still lets the installed-world
# pytest run all three.
try:
    from test.bases import WorldTestBase          # noqa: E402  (Archipelago's own test base)
    import worlds.eldenring                       # noqa: F401,E402
except ImportError:                               # pragma: no cover - no AP checkout here
    WorldTestBase = None


class _MtGelmirOnlySeed:
    """num_regions 1 with Mt. Gelmir kept -- boblerrr's playtest shape -- must reach all 23.

    SEEDS, not a pinned seed: which region a 1-region draw keeps is a property of the draw, and a
    data change that shifts the pool must move the SEARCH rather than red the test (the lesson
    test_gf_boss_locks.BossLocationsSealed records: it went red on CI and green in the sandbox on
    one commit, which is what an unverified premise looks like). If no seed in the window keeps
    Mt. Gelmir the premise is UNEXERCISED and this fails loudly instead of passing vacuously."""

    game = "Elden Ring"
    options = {"num_regions": 1, "ending_condition": "great_runes"}
    SEEDS = tuple(range(64))

    def _setup_a_gelmir_seed(self):
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            if GELMIR in set(self.world._kept()):
                return seed
        self.fail("no seed in %r kept %s at num_regions=1, so the reachability claim in issue #540 "
                  "went UNEXERCISED -- widen SEEDS, or the region has left the draw pool"
                  % (self.SEEDS, GELMIR))

    def test_every_former_member_is_reachable_on_a_gelmir_seed(self):
        from worlds.eldenring.data import LOCATIONS

        seed = self._setup_a_gelmir_seed()
        ap_of = {int(f): int(a) for rows in LOCATIONS.values() for (_n, a, f) in rows}
        want = {ap_of[f] for f in FALLINGSTAR_MEMBER_FLAGS}
        self.assertEqual(len(want), len(FALLINGSTAR_MEMBER_FLAGS),
                         "the 23 fixture flags did not resolve to 23 distinct ap ids -- the "
                         "reachability claim below would be about the wrong checks")
        by_id = {loc.address: loc for loc in self.multiworld.get_locations(self.player)
                 if loc.address is not None}
        absent = sorted(want - set(by_id))
        self.assertFalse(absent,
                         "seed %d keeps %s, yet %d of the beast's 23 former checks are not in the "
                         "seed at all: %s" % (seed, GELMIR, len(absent), absent))
        state = self.multiworld.get_all_state(False)
        unreachable = sorted(a for a in want if not by_id[a].can_reach(state))
        self.assertFalse(unreachable,
                         "seed %d keeps %s but %d of the 23 are UNREACHABLE: %s"
                         % (seed, GELMIR, len(unreachable), unreachable))

    def test_no_kept_sweep_on_a_gelmir_seed_is_paid_by_a_boss_that_does_not_exist(self):
        """The general form, scoped to the seed: every trigger that can grant a kept check must be
        a boss someone can actually kill."""
        from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION, SWEEP_UNSPAWNED

        self._setup_a_gelmir_seed()
        kept = set(self.world._kept())
        self.assertIn(GELMIR, kept,
                      "the seed search returned without keeping %s, so this gate is looking at the "
                      "wrong seed" % GELMIR)
        self.assertTrue(SWEEP_UNSPAWNED,
                        "SWEEP_UNSPAWNED is EMPTY, so 'no kept trigger is unspawned' is true of "
                        "every possible tree and gates nothing")
        ghosts = {t: SWEEP_REGION.get(t) for t in DUNGEON_SWEEPS
                  if t in SWEEP_UNSPAWNED and SWEEP_REGION.get(t) in kept}
        self.assertFalse(ghosts,
                         "kept region(s) carry sweep trigger(s) whose boss does not exist: %s"
                         % ghosts)


if WorldTestBase is not None:
    class MtGelmirOnlySeed(_MtGelmirOnlySeed, WorldTestBase):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
