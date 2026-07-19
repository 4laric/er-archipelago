"""Unified "Progressive Flask Upgrade" -- the flask is a reconciled LEVELED STATE now.

The design (v0.2, reworked 2026-07-19): every Golden Seed / Sacred Tear check pays a single
"Progressive Flask Upgrade" item, and the client reconciles the player's flask to a cumulative
LEVELED target -- slot_data `flaskLadder[K-1] = {charges, potency}` after receiving K copies. It is a
STATE, not consumed goods, so a spent flask is never re-granted (the CTD the old per-copy Golden-Seed /
Sacred-Tear goods ladder caused: reconcile.rs self-healed a spent seed and re-upgraded unbounded,
playtest 2026-07-12). PROG_FLASK is NO LONGER emitted inside progressiveGrants.

This file guards the wire contract of the new ladder: monotonic non-decreasing, bounded
(charges 2..14, potency 0..12), reaching the max at the LAST rung, with LENGTH == the PROG_FLASK
copies the seed actually has (the substituted seed/tear checks, or a fixed 10 injected under dlc_only).

The vanilla cost tables (FLASK_CHARGE_SEED_COST / FLASK_POTENCY_TEAR_COST) are retained as documented
data; test_cost_tables_match_tools keeps them equal to tools/upgrade_costs.py (one datum, one source).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import progressive as pg  # noqa: E402

from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring"


# ---- pure-data guards (no world) ---------------------------------------------------------------
def test_cost_tables_match_tools():
    """The feature MIRRORS tools/upgrade_costs.py rather than importing it (tools/ is a script package
    -- sys.path hacks, no __init__, not guaranteed to ship inside the apworld zip). That is only safe
    if a gate keeps the two copies equal. This is the gate."""
    import importlib.util
    import pathlib

    tools = pathlib.Path(pg.__file__).resolve().parent.parent / "tools" / "upgrade_costs.py"
    if not tools.is_file():
        pytest.skip(f"tools/upgrade_costs.py not shipped here ({tools})")
    spec = importlib.util.spec_from_file_location("_er_upgrade_costs", tools)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert list(mod.FLASK_CHARGE_SEED_COST) == list(pg.FLASK_CHARGE_SEED_COST), (
        "seed cost ladder drifted from tools/upgrade_costs.py -- one datum, one source")
    assert list(mod.FLASK_POTENCY_TEAR_COST) == list(pg.FLASK_POTENCY_TEAR_COST), (
        "tear cost ladder drifted from tools/upgrade_costs.py -- one datum, one source")


def _assert_leveled_ladder_invariants(testcase, ladder):
    """A flaskLadder is a non-empty list of {charges 2..14, potency 0..12}, monotonic non-decreasing,
    reaching (14,12) at the last rung."""
    testcase.assertIsInstance(ladder, list)
    testcase.assertGreater(len(ladder), 0)
    for r in ladder:
        testcase.assertIsInstance(r, dict)
        testcase.assertIn("charges", r)
        testcase.assertIn("potency", r)
        testcase.assertTrue(pg.FLASK_CHARGES_BASE <= r["charges"] <= pg.FLASK_CHARGES_MAX,
                            f"charges out of [2,14]: {r}")
        testcase.assertTrue(0 <= r["potency"] <= pg.FLASK_POTENCY_MAX, f"potency out of [0,12]: {r}")
    for a, b in zip(ladder, ladder[1:]):
        testcase.assertLessEqual(a["charges"], b["charges"], "charges not monotonic")
        testcase.assertLessEqual(a["potency"], b["potency"], "potency not monotonic")
    testcase.assertEqual(ladder[-1], {"charges": pg.FLASK_CHARGES_MAX, "potency": pg.FLASK_POTENCY_MAX},
                         "the last rung must be maxed (14,12)")


# ---- the ladder on a FULL seed -----------------------------------------------------------------
class ProgressiveFlaskLadder(WorldTestBase):
    game = GAME
    options = {"progressive_flasks": True, "enable_dlc": True, "num_regions": 0}

    def _ladder(self):
        return pg.flask_ladder(self.world)

    def test_ladder_invariants(self):
        _assert_leveled_ladder_invariants(self, self._ladder())

    def test_ladder_length_matches_copy_count(self):
        """The wire length == the PROG_FLASK copies actually in the pool (so no rung is dead and no
        copy lacks a rung). On a full seed every kept Golden Seed / Sacred Tear substitutes to a copy."""
        ladder = self._ladder()
        copies = world_item_names(self).count(pg.PROG_FLASK)
        self.assertEqual(len(ladder), copies,
                         f"ladder rungs ({len(ladder)}) != PROG_FLASK copies ({copies})")
        self.assertEqual(len(ladder), pg.flask_copy_count(self.world))

    def test_ladder_is_deterministic_per_seed(self):
        """create_items and fill_slot_data must never disagree about the ladder (it is cached)."""
        self.assertEqual(self._ladder(), self._ladder(), "flask_ladder must be cached, not re-rolled")

    def test_vanilla_seeds_and_tears_replaced_one_for_one(self):
        names = world_item_names(self)
        for vanilla in pg.VANILLA_FLASK_ITEMS:
            self.assertEqual(names.count(vanilla), 0,
                             f"{vanilla} still in the pool alongside {pg.PROG_FLASK}")
        self.assertGreater(names.count(pg.PROG_FLASK), 0, "no progressive flask copies in the pool")

    def test_slot_data_emits_flask_ladder_not_a_grant(self):
        """The flask rides its OWN key (flaskLadder) and is GONE from progressiveGrants -- that split
        is the whole point (a leveled state cannot be re-granted like consumed goods)."""
        sd = self.world.fill_slot_data()
        self.assertIn(contract.FLASK_LADDER, sd, "flaskLadder must be emitted when flasks are on")
        self.assertEqual(sd[contract.FLASK_LADDER], self._ladder(),
                         "emitted flaskLadder disagrees with the ladder create_items used")
        self.assertNotIn(pg.PROG_FLASK, sd[contract.PROGRESSIVE_GRANTS],
                         "PROG_FLASK must NOT be in progressiveGrants (it is a leveled state now)")
        # and the emitted wire passes the contract shape checker
        self.assertIsNone(contract._chk_flask_ladder(sd[contract.FLASK_LADDER]))


# ---- the ladder under dlc_only (the fixed floor) -----------------------------------------------
class ProgressiveFlaskLadderDLCOnly(WorldTestBase):
    """dlc_only seals every base region, so no kept REGION holds a seed/tear check (only the HUB's lone
    Golden Seed substitutes). The feature tops the pool up to a fixed 10 copies and builds a 10-rung
    ladder that maxes by rung 10 -- some rungs advancing multiple charge/potency steps."""
    game = GAME
    options = {"dlc_only": True, "progressive_flasks": True}

    def test_dlc_only_injects_ten_rung_ladder(self):
        w = self.world
        self.assertEqual(pg._region_flask_copies(w), 0,
                         "dlc_only should keep no REGION flask check (only the HUB's Golden Seed)")
        ladder = pg.flask_ladder(w)
        self.assertEqual(len(ladder), pg.DLC_ONLY_FLASK_COPIES,
                         "dlc_only ladder must be exactly the fixed floor length (10)")
        _assert_leveled_ladder_invariants(self, ladder)

    def test_pool_holds_exactly_ladder_length_copies(self):
        """Count-consistency: ladder length == PROG_FLASK copies actually in the pool (HUB substitution
        + injected top-up)."""
        w = self.world
        copies = world_item_names(self).count(pg.PROG_FLASK)
        self.assertEqual(copies, pg.DLC_ONLY_FLASK_COPIES)
        self.assertEqual(copies, len(pg.flask_ladder(w)))

    def test_maxes_by_the_last_rung_only(self):
        """The last rung is the max, and it is load-bearing (an earlier rung is below it) -- so the
        short ladder actually climbs rather than jumping to max and idling."""
        ladder = pg.flask_ladder(self.world)
        self.assertEqual(ladder[-1], {"charges": pg.FLASK_CHARGES_MAX, "potency": pg.FLASK_POTENCY_MAX})
        self.assertNotEqual(ladder[-2], ladder[-1], "the last rung buys nothing -- ladder idles at max")


# ---- the toggle's OFF half ---------------------------------------------------------------------
class ProgressiveFlasksOff(WorldTestBase):
    game = GAME
    options = {"progressive_flasks": False, "enable_dlc": True, "num_regions": 0}

    def test_vanilla_seeds_and_tears_stay_discrete(self):
        names = world_item_names(self)
        self.assertEqual(names.count(pg.PROG_FLASK), 0,
                         "progressive copies in the pool with the toggle OFF")
        for vanilla in pg.VANILLA_FLASK_ITEMS:
            self.assertGreater(names.count(vanilla), 0,
                               f"{vanilla} missing from the pool with progressive_flasks off")

    def test_slot_data_emits_no_flask_ladder(self):
        sd = self.world.fill_slot_data()
        self.assertNotIn(contract.FLASK_LADDER, sd,
                         "no flaskLadder may be emitted when the toggle is off")
        self.assertNotIn(pg.PROG_FLASK, sd[contract.PROGRESSIVE_GRANTS])


def test_option_is_a_real_toggle_default_on():
    """progressive_flasks is a REAL yaml toggle (un-frozen 2026-07-15), default ON: the unified ladder
    is the intended v0.2 flask economy. Flipping either silently reverts it."""
    from worlds.eldenring import defaults
    from worlds.eldenring.features.progressive import ProgressiveFlasks
    assert "progressive_flasks" not in defaults.FROZEN_OPTIONS, (
        "progressive_flasks went back into FROZEN_OPTIONS -- it is supposed to be a real yaml toggle")
    assert ProgressiveFlasks.default == 1, (
        "progressive_flasks must default ON: the unified ladder is the intended v0.2 flask economy")


# ---- the CTD, as a contract invariant (bells half still applies) --------------------------------
def test_flask_is_not_in_progressive_grants_bells_still_declare_consumed():
    """The flask no longer rides progressiveGrants at all (a leveled state cannot be re-granted). The
    bell bearings still do, and must stay OWNED (self-healing) -- a key item you keep forever."""
    from worlds.eldenring.features import progressive as pgg

    class _W:
        class options:
            class progressive_flasks: value = 1
            class progressive_stone_bells: value = 1
            class progressive_stonesword_keys: value = 0
        import random as _r
        random = _r.Random(1)
        player = 1

    feat = pgg.Progressive()
    # PROG_FLASK is excluded from progressiveGrants (slot_data path); it has no goods ladder now.
    active = feat._active_items(_W)
    assert pgg.PROG_FLASK in active, "flasks are on, so PROG_FLASK is an active pool item"
    bell = feat._grant_ladder(_W, pgg.PROG_SMITHING_BELL)
    assert bell, "bell ladder is empty"
    assert all(r["consumed"] is False for r in bell), (
        "a bell bearing is a KEY ITEM the player keeps -- it must stay self-healing (owned)")


def test_contract_rejects_a_rung_that_forgets_to_declare():
    """The progressiveGrants validator must still REFUSE a rung with no `consumed` (the field whose
    absence CTD'd a live playtest), so a bell/key rung can never again ship by omission."""
    bad = {"Progressive Smithing-Stone Miner's Bell Bearing": [{"goods": 1073751844, "flags": []}]}
    err = contract._chk_nested_grants(bad)
    assert err and "consumed" in err, f"validator accepted a rung with no `consumed`: {err!r}"

    good = {"Progressive Smithing-Stone Miner's Bell Bearing":
            [{"goods": 1073751844, "flags": [280080], "consumed": False}]}
    assert contract._chk_nested_grants(good) is None
