"""#618 -- `vanilla_pool: true` must actually produce a vanilla pool, BOTH halves.

THE CASE THIS IS BUILT FROM (CONTRIBUTING rule 11)
--------------------------------------------------
boblerrr, 2026-08-12 playtest thread: he counted the crystal tears in his seed, got 19 against a
catalog that is complete at 37/37, and reported items missing. Nineteen is not a coincidence and it
is not a defect -- it is the 18-item `presence_floor` roster plus the one Gravesite tear his seed
kept. The floor was doing its job.

The trap this file exists to nail down is the FIX being half a fix. `curated_filler: {}` already
gave a vanilla filler tail and had for months, so "there is already an escape hatch" was true and
useless: `presence_floor` declared no options and was not frozen -- it was unconditional -- so a
player who found the empty recipe, typed it, and went counting STILL got up to 18 injected tears,
with the seed looking exactly like the one he complained about. A gate on the recipe alone would be
green on precisely that seed.

So this asserts the OUTCOME, not the option echo, and it asserts both halves against the same
source of truth core builds the pool from (`LOCATION_ITEM`):

  1. every roster item appears in the pool exactly as often as VANILLA placed it on a kept
     location -- zero injected copies, checked name by name rather than in aggregate;
  2. the filler allocator rewrites NO tail slot (`plan()` is all-`None`, and `None` is defined in
     core.create_items as "keep what the check already paid");
  3. 🛑 and the differential: the SAME seed with the lever off must FAIL (1) or (2). Without this
     the file would pass on a build where the option does nothing at all, which is the failure mode
     the whole issue is about -- something that looks like it worked.

SCOPE, stated so nobody reads more into a green run than it earns
-----------------------------------------------------------------
This does NOT assert that a `vanilla_pool` seed is byte-identical to vanilla Elden Ring:

  * `item_shuffle` is frozen ON, so the vanilla items are still SHUFFLED between checks. The lever
    restores WHICH ITEMS EXIST, not where they sit. That is the axis `vanilla_placement` owns.
  * checks whose vanilla ware has no catalog entry pay the `FILLER` sentinel and still draw varied
    junk through `_pick_filler`, because `varied_filler` is frozen ON and there is no vanilla item
    on record to restore. Small, real, and named in features/vanilla_pool.py's scope note.
  * Region Locks and other progression items still displace vanilla items. They are the game.
"""
import collections

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.data import HUB, LOCATIONS  # noqa: E402
from worlds.eldenring.features import filler_budget as fb  # noqa: E402
from worlds.eldenring.features import presence_floor as pf  # noqa: E402
from worlds.eldenring.features import vanilla_pool as vp  # noqa: E402
from worlds.eldenring.item_ids import LOCATION_ITEM  # noqa: E402

GAME = "Elden Ring"

# One small, fully-specified seed, used for BOTH arms. num_regions is pinned rather than left at the
# default so the two arms keep the same location set -- a differential between two different maps
# would prove nothing.
_SEED_OPTIONS = {"num_regions": 6, "enable_dlc": False}


def _pool_items(world):
    """Location-paying items this world created (unplaced itempool + pre-placed on locations).

    Same helper as test_gf_presence_floor -- copied rather than imported because these two files
    must be able to disagree about the floor without one silently reshaping the other's evidence."""
    p = world.player
    mw = world.multiworld
    out = [i for i in mw.itempool if i.player == p]
    out += [loc.item for loc in mw.get_locations(p)
            if loc.item is not None and loc.item.player == p]
    return out


def _vanilla_counts(world, names):
    """{name: how many KEPT locations vanilla pays that name}, straight off LOCATION_ITEM.

    This is the expectation core itself builds `extras` from, which is why the assertions read it
    rather than a hand-typed number: a roster or a region set that moves takes this with it."""
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    want = set(names)
    out = collections.Counter()
    for rn in [HUB] + kept:
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            nm = LOCATION_ITEM.get(ap_id)
            if nm in want:
                out[nm] += 1
    return out


def _roster_pool_counts(world):
    """{roster name: copies of it in this world's pool}."""
    roster = set(pf.ROSTER)
    return collections.Counter(i.name for i in _pool_items(world) if i.name in roster)


def _tail_plan(world):
    """What the filler allocator decided for every tail slot. `None` = keep what vanilla paid."""
    return fb.plan(world, fb.budget_slots(world))


class VanillaPoolOn(WorldTestBase):
    """The lever on. This is the seed the issue asks for."""
    game = GAME
    options = dict(_SEED_OPTIONS, vanilla_pool=True)

    def test_the_predicate_agrees_the_mode_is_on(self):
        """Cheap, and it is the one thing that would make every assertion below vacuous."""
        self.assertTrue(vp.is_on(self.world),
                        "vanilla_pool reads OFF on a world built with vanilla_pool=True -- every "
                        "other test in this class is then asserting the default build's behaviour "
                        "and would stay green if the option were deleted.")

    def test_no_presence_floor_item_is_injected(self):
        """HALF ONE, and the half `curated_filler: {}` never covered.

        Name by name against LOCATION_ITEM, not as a total: an aggregate count can hide one
        injected tear behind one suppressed bell bearing, and the report that opened this issue was
        somebody counting ONE category."""
        got = _roster_pool_counts(self.world)
        want = _vanilla_counts(self.world, pf.ROSTER)
        # THE WITNESS, and this test is worthless without it (test_gf_vacuous_pass's ratchet is what
        # made me write it down). Every assertion below is "this collection is empty" or "these two
        # agree", and a roster that stopped resolving, or a LOCATION_ITEM walk that matched nothing,
        # satisfies all of them for the wrong reason -- silently, and in exactly the direction the
        # bug went. So first: say out loud that there was something to see.
        self.assertGreater(len(pf.ROSTER), 0,
                           "the presence-floor roster resolved to nothing, so this test cannot "
                           "witness an injection either way.")
        self.assertGreater(sum(want.values()), 0,
                           "no kept location on this seed pays a roster item according to "
                           "LOCATION_ITEM, so 'the pool matches vanilla' is a comparison of two "
                           "empty sets. Pin a seed that keeps at least one roster item's home.")
        self.assertEqual(pf.absent_roster(self.world), [],
                         "presence_floor still reports absent roster items to inject under "
                         "vanilla_pool -- the floor has not been stood down.")
        offenders = {n: (got.get(n, 0), want.get(n, 0))
                     for n in set(got) | set(want) if got.get(n, 0) != want.get(n, 0)}
        self.assertEqual(offenders, {},
                         "under vanilla_pool a roster item must appear exactly as often as vanilla "
                         "placed it on a kept location. {name: (in pool, vanilla)}: %r. A pool "
                         "count above the vanilla one is an injected copy -- the 18 tears that made "
                         "a complete 37/37 catalog look half-empty (#618)." % offenders)

    def test_the_filler_tail_keeps_what_vanilla_paid(self):
        """HALF TWO. `None` is core.create_items' 'keep what the check already paid' sentinel:

            for _k, _pick in zip(_budget_ix, _plan):
                if _pick is not None:      # None = keep what the check already paid
                    _names[_k] = _pick

        so an all-`None` plan IS the assertion that no tail check was rewritten."""
        plan = _tail_plan(self.world)
        self.assertTrue(plan, "the tail is empty on this seed, so this gate proves nothing -- pin a "
                              "seed that HAS a filler tail rather than letting it pass vacuously.")
        rewritten = collections.Counter(p for p in plan if p is not None)
        self.assertEqual(dict(rewritten), {},
                         "under vanilla_pool the filler allocator must leave every tail slot alone, "
                         "and it rewrote %d of %d. {item: slots}: %r"
                         % (sum(rewritten.values()), len(plan), dict(rewritten)))

    def test_the_recipe_is_overridden_rather_than_obeyed(self):
        """The ruling in features/vanilla_pool.py, asserted where it takes effect.

        `CuratedFiller` has a real nine-category DEFAULT, so this world has a non-empty recipe that
        nobody typed. If the lever rejected that combination it would reject the shipped template;
        if it obeyed it, the lever would do nothing on every default yaml -- which is every yaml."""
        self.assertEqual(fb.recipe_of(self.world), {fb.JUNK: 100},
                         "recipe_of must return the junk-only recipe under vanilla_pool no matter "
                         "what curated_filler holds. This world's curated_filler is the shipped "
                         "default, i.e. the case every real yaml is in.")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.world.player](state),
                        "a vanilla pool must still be winnable -- Region Locks are progression and "
                        "live outside the filler tail, so nothing this mode does may touch them.")


class VanillaPoolOffIsTheDifferential(WorldTestBase):
    """🛑 THE ANTI-VACUITY ARM. The same seed with the lever off must NOT look vanilla.

    Without this class the file above is green on a build where `vanilla_pool` is accepted, echoed,
    documented and wired to nothing -- and "it looks like it worked" is the entire subject of #618.
    So this asserts the default build still curates, and it is expected to fail the day the DEFAULT
    stops curating, which would be a much bigger change than this one and should not land quietly.
    """
    game = GAME
    options = dict(_SEED_OPTIONS, vanilla_pool=False)

    def test_the_predicate_agrees_the_mode_is_off(self):
        # Witnessed on the OPTION, not just on the predicate: `is_on` returns False for a world that
        # has no such option at all, so asserting only the False would keep passing if vanilla_pool
        # were deleted -- and this class exists precisely to catch "the option is not wired".
        self.assertIsNotNone(getattr(self.world.options, "vanilla_pool", None),
                             "vanilla_pool is not on the option surface at all; is_on() would read "
                             "False for a missing option and this arm would stay green.")
        self.assertFalse(vp.is_on(self.world))

    def test_the_default_build_still_curates(self):
        """At least one of the two halves must visibly differ from vanilla, or the arm above is
        proving nothing about the option."""
        plan = _tail_plan(self.world)
        rewrote_tail = any(p is not None for p in plan)
        got = _roster_pool_counts(self.world)
        want = _vanilla_counts(self.world, pf.ROSTER)
        injected = any(got.get(n, 0) > want.get(n, 0) for n in set(got) | set(want))
        self.assertTrue(rewrote_tail or injected,
                        "with vanilla_pool OFF this seed already looks vanilla: the allocator "
                        "rewrote no tail slot AND the presence floor injected nothing. The ON arm "
                        "of this file is then asserting a difference that does not exist and would "
                        "stay green with the option unwired.")
