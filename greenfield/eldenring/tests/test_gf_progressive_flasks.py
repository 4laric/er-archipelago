"""Unified "Progressive Flask Upgrade" -- the flask is a HYBRID across two axes.

The design (v0.2, reworked 2026-07-19): every Golden Seed / Sacred Tear check pays a single
"Progressive Flask Upgrade" item. Each copy raises the flask on TWO independent axes, and the item
rides BOTH wires at once (intentional, non-overlapping):
  * CHARGES = a reconciled LEVELED STATE (contract.flaskLadder). The client reconciles the flask
    charge target to flaskLadder[K-1]["charges"] after K copies -- a direct write, no spend to heal.
  * POTENCY = GRANTED consumed Sacred Tears (progressiveGrants). Each copy grants ONE consumed Sacred
    Tear (good 10020); the player upgrades potency at a grace the vanilla way, which updates every
    flask mirror safely. consumed=True is REQUIRED (an OWNED build re-granted spent tears unbounded and
    CTD'd, playtest 2026-07-12; the in-place potency item-id swap CTD'd on death against the
    half-updated mirrors, playtest 2026-07-19). One tear per copy => one ledger entry per stream index
    => no batching problem.

This file guards: the progressiveGrants flask ladder is 12 consumed Sacred Tears (good 10020|nibble);
the flaskLadder charges climb (escalating) to 14 at the last rung; the flaskLadder potency climbs a
flat +1 per rung capped at 12 (min(rung,12)); LENGTH == the PROG_FLASK copies the seed has (the
substituted seed/tear checks, or a fixed 12 injected under dlc_only).

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
    """A flaskLadder is a non-empty list of {charges 2..14, potency 0..12}, monotonic non-decreasing.
    CHARGES climb (escalating) to FLASK_CHARGES_MAX at the last rung. POTENCY climbs a flat +1 per rung
    capped at FLASK_POTENCY_MAX -- i.e. rung i (1-based) has potency == min(i, 12). One consumed Sacred
    Tear is granted per copy, so a rung may NEVER advance potency by more than 1 (a +2 rung would need
    two tears at one stream index = the batching the ledger forbids)."""
    testcase.assertIsInstance(ladder, list)
    testcase.assertGreater(len(ladder), 0)
    for i, r in enumerate(ladder, start=1):
        testcase.assertIsInstance(r, dict)
        testcase.assertIn("charges", r)
        testcase.assertIn("potency", r)
        testcase.assertTrue(pg.FLASK_CHARGES_BASE <= r["charges"] <= pg.FLASK_CHARGES_MAX,
                            f"charges out of [2,14]: {r}")
        testcase.assertEqual(r["potency"], min(i, pg.FLASK_POTENCY_MAX),
                             f"potency must be min(rung,12) = +1/rung capped at 12: rung {i} -> {r}")
    for a, b in zip(ladder, ladder[1:]):
        testcase.assertLessEqual(a["charges"], b["charges"], "charges not monotonic")
        testcase.assertLessEqual(a["potency"], b["potency"], "potency not monotonic")
        testcase.assertLessEqual(b["potency"] - a["potency"], 1, "potency must never jump by >1 (1 tear/copy)")
    testcase.assertEqual(ladder[-1]["charges"], pg.FLASK_CHARGES_MAX,
                         "charges must reach FLASK_CHARGES_MAX (14) at the last rung")
    testcase.assertEqual(ladder[-1]["potency"], min(len(ladder), pg.FLASK_POTENCY_MAX),
                         "last-rung potency must be min(len,12)")


def _assert_flask_potency_grants(testcase, rungs):
    """The flask's progressiveGrants ladder = FLASK_POTENCY_MAX (12) consumed Sacred Tears, good
    10020|nibble, empty flags. This is the POTENCY axis: one tear per copy, consumed=True (spent at a
    grace; shipping it OWNED re-granted it unbounded and CTD'd, playtest 2026-07-12)."""
    expected_goods = pg._GOOD_SACRED_TEAR | pg._GOODS_NIBBLE
    testcase.assertEqual(pg._GOOD_SACRED_TEAR, 10020, "Sacred Tear good id must be 10020")
    testcase.assertEqual(expected_goods, 1073751844, "Sacred Tear FullID must match item_ids.py")
    testcase.assertEqual(len(rungs), pg.FLASK_POTENCY_MAX,
                         f"flask potency ladder must have {pg.FLASK_POTENCY_MAX} rungs (12 tears)")
    for r in rungs:
        testcase.assertEqual(r["goods"], expected_goods, "every flask potency rung grants a Sacred Tear")
        testcase.assertEqual(r["flags"], [], "flask potency rungs carry no flags")
        testcase.assertIs(r["consumed"], True,
                          "flask tears MUST be consumed (spent at a grace; OWNED re-grants unbounded)")


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

    def test_slot_data_emits_flask_ladder_and_potency_tears(self):
        """The flask rides BOTH wires: CHARGES on flaskLadder (leveled state) and POTENCY on
        progressiveGrants (12 consumed Sacred Tears). The split is the whole point -- charges are a
        reconciled state (no spend to heal), potency is granted/ledgered tears the player upgrades at a
        grace (which updates every flask mirror safely)."""
        sd = self.world.fill_slot_data()
        self.assertIn(contract.FLASK_LADDER, sd, "flaskLadder must be emitted when flasks are on")
        self.assertEqual(sd[contract.FLASK_LADDER], self._ladder(),
                         "emitted flaskLadder disagrees with the ladder create_items used")
        grants = sd[contract.PROGRESSIVE_GRANTS]
        self.assertIn(pg.PROG_FLASK, grants,
                      "PROG_FLASK MUST be in progressiveGrants now (its POTENCY axis grants tears)")
        _assert_flask_potency_grants(self, grants[pg.PROG_FLASK])
        # both wires pass their contract shape checkers
        self.assertIsNone(contract._chk_flask_ladder(sd[contract.FLASK_LADDER]))
        self.assertIsNone(contract._chk_nested_grants({pg.PROG_FLASK: grants[pg.PROG_FLASK]}))


# ---- the ladder under dlc_only (the fixed floor) -----------------------------------------------
class ProgressiveFlaskLadderDLCOnly(WorldTestBase):
    """dlc_only seals every base region, so no kept REGION holds a seed/tear check (only the HUB's lone
    Golden Seed substitutes). The feature tops the pool up to a fixed 12 copies and builds a 12-rung
    ladder: charges max (14) via the escalating schedule and potency maxes (12) via one tear/copy, so
    BOTH axes fully max exactly at copy 12."""
    game = GAME
    options = {"dlc_only": True, "progressive_flasks": True}

    def test_dlc_only_injects_twelve_rung_ladder(self):
        w = self.world
        self.assertEqual(pg._region_flask_copies(w), 0,
                         "dlc_only should keep no REGION flask check (only the HUB's Golden Seed)")
        self.assertEqual(pg.DLC_ONLY_FLASK_COPIES, 12, "dlc_only floor must be 12 (1 tear/copy -> potency 12)")
        ladder = pg.flask_ladder(w)
        self.assertEqual(len(ladder), pg.DLC_ONLY_FLASK_COPIES,
                         "dlc_only ladder must be exactly the fixed floor length (12)")
        _assert_leveled_ladder_invariants(self, ladder)
        # both axes fully maxed at the last (12th) rung
        self.assertEqual(ladder[-1], {"charges": pg.FLASK_CHARGES_MAX, "potency": pg.FLASK_POTENCY_MAX})

    def test_dlc_only_potency_grants_twelve_tears(self):
        """The dlc_only seed grants exactly 12 consumed Sacred Tears (one per copy) so potency reaches
        its cap the ledgered/consumed way."""
        grants = self.world.fill_slot_data()[contract.PROGRESSIVE_GRANTS]
        self.assertIn(pg.PROG_FLASK, grants)
        _assert_flask_potency_grants(self, grants[pg.PROG_FLASK])

    def test_pool_holds_exactly_ladder_length_copies(self):
        """Count-consistency: ladder length == PROG_FLASK copies actually in the pool (HUB substitution
        + injected top-up)."""
        w = self.world
        copies = world_item_names(self).count(pg.PROG_FLASK)
        self.assertEqual(copies, pg.DLC_ONLY_FLASK_COPIES)
        self.assertEqual(copies, 12)
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


# ---- the CTD, as a contract invariant (consumed vs owned) ---------------------------------------
def test_flask_potency_grants_consumed_tears_bells_stay_owned():
    """The flask's POTENCY axis rides progressiveGrants as 12 CONSUMED Sacred Tears (spent at a grace;
    shipping them OWNED re-granted spent tears unbounded and CTD'd, playtest 2026-07-12). The bell
    bearings ride the same wire but must stay OWNED (self-healing) -- a key item you keep forever.
    Same ladder machinery, opposite grant semantics."""
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
    active = feat._active_items(_W)
    assert pgg.PROG_FLASK in active, "flasks are on, so PROG_FLASK is an active pool item"

    flask = feat._grant_ladder(_W, pgg.PROG_FLASK)
    assert len(flask) == pgg.FLASK_POTENCY_MAX == 12, "flask potency ladder must be 12 tears"
    assert all(r["goods"] == (pgg._GOOD_SACRED_TEAR | pgg._GOODS_NIBBLE) for r in flask), (
        "every flask potency rung grants a Sacred Tear (good 10020|nibble)")
    assert all(r["consumed"] is True for r in flask), (
        "flask tears are SPENT at a grace -- they MUST be consumed (OWNED re-grants unbounded, CTD)")
    assert all(r["flags"] == [] for r in flask), "flask tears carry no flags"

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
