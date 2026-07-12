"""Unified "Progressive Flask Upgrade" -- the ladder must BUY MAX FLASKS and DECELERATE.

The design in one line: the Kth copy grants an ITEM (a Golden Seed or a Sacred Tear), not an upgrade
LEVEL. The player still walks to a grace and pays the game's own escalating price, so the
"later pickups buy less" curve is INHERITED from the vanilla cost table -- no re-pricing, no param
edit, no client change. That is the property this file guards, because it is the property that makes
the feature worth having, and it is invisible to a test that only counts items.

Why it exists at all: Golden Seeds work in a randomizer because they are plentiful (43) and cost MORE
per level as you climb. Sacred Tears do not: 13 in the whole game, each a flat +1, so they arrive
rarely, silently, and never form a curve. Interleaving them into the seed track fixes the tear line
without touching the thing that already works.

Oracles are DERIVED from the game's real cost tables, never pinned to an observed count -- and
test_cost_tables_match_tools guards the one place a number is repeated, so the datum keeps a single
source of truth.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import progressive as pg  # noqa: E402

from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring"

_SEED, _TEAR = pg._GOOD_GOLDEN_SEED, pg._GOOD_SACRED_TEAR


def _levels_bought(n, cost_table):
    """Highest upgrade level fully paid for by `n` items, spending against the real per-level cost."""
    lv = 0
    for c in cost_table:
        if n >= c:
            n -= c
            lv += 1
        else:
            break
    return lv


def _flask_levels_after(ladder, k):
    """Total flask upgrade levels (charges + potency) a player holds after receiving k copies."""
    got = ladder[:k]
    return (_levels_bought(got.count(_SEED), pg.FLASK_CHARGE_SEED_COST)
            + _levels_bought(got.count(_TEAR), pg.FLASK_POTENCY_TEAR_COST))


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


# ---- the ladder itself -------------------------------------------------------------------------
# ⛔ The feature is FROZEN OFF (defaults.py) because it BRICKS THE GAME -- see test_option_is_frozen_off
# below for the mechanism. The world-level cases cannot be constructed while it is off (the option is
# filtered out of GFOptions), so they are skipped rather than deleted: the ladder is sound and this
# suite is what proves it, the moment the client can grant a tier's goods as CONSUMED rather than OWNED.
@pytest.mark.skip(reason="progressive_flasks is FROZEN OFF: reconcile.rs re-grants tier goods (they go "
                         "to unique_goods, a self-healing OWN set), so a spent Golden Seed / Sacred Tear "
                         "is handed back -> unbounded flask upgrades -> CTD. Un-skip when tier grants are "
                         "ledgered.")
class ProgressiveFlaskLadder(WorldTestBase):
    game = GAME
    options = {"progressive_flasks": True, "enable_dlc": True, "num_regions": 0}

    def _ladder(self):
        return pg.flask_ladder(self.world)

    def test_ladder_buys_exactly_max_flasks(self):
        """Every rung is spendable and the last rung completes the flask. Not one wasted, not one
        short -- if the ladder were longer, its tail would be dead pickups; shorter, and max flasks
        would be unreachable no matter how many copies you found."""
        ladder = self._ladder()
        self.assertEqual(ladder.count(_SEED), sum(pg.FLASK_CHARGE_SEED_COST),
                         "ladder must contain exactly the seeds max charges costs")
        self.assertEqual(ladder.count(_TEAR), sum(pg.FLASK_POTENCY_TEAR_COST),
                         "ladder must contain exactly the tears max potency costs")

        full = _flask_levels_after(ladder, len(ladder))
        self.assertEqual(full, len(pg.FLASK_CHARGE_SEED_COST) + len(pg.FLASK_POTENCY_TEAR_COST),
                         "the full ladder must buy MAX charges AND MAX potency")
        # and the final rung must be load-bearing (no dead tail inside the ladder)
        self.assertLess(_flask_levels_after(ladder, len(ladder) - 1), full,
                        "the last rung buys nothing -- the ladder is longer than the flask needs")

    def test_pickups_decelerate(self):
        """THE property. Early copies buy a level each; late copies are progress toward a level that
        now costs five. This must fall out of the vanilla cost table, not out of a tuning constant.

        Compared by HALVES rather than adjacent pickups: the curve is monotone in aggregate but
        deliberately lumpy up close (that lumpiness -- 'this one did nothing, the next one will' -- is
        the tension being preserved), so an adjacent-pair assertion would encode noise.
        """
        ladder = self._ladder()
        n = len(ladder)
        mid = n // 2
        first = _flask_levels_after(ladder, mid)
        second = _flask_levels_after(ladder, n) - first
        self.assertGreater(
            first, second,
            f"no deceleration: first {mid} copies bought {first} flask levels, last {n - mid} bought "
            f"{second}. The vanilla escalating cost table is supposed to supply this for free -- if it "
            f"is flat, the ladder is granting LEVELS instead of ITEMS and the design is broken.")

        # A player's first few pickups should actually move the bar -- the early game is exactly where
        # the playtest felt dead.
        self.assertGreaterEqual(_flask_levels_after(ladder, 3), 2,
                                "the first 3 copies must buy at least 2 flask levels")

    def test_tears_are_interleaved_not_backloaded(self):
        """A tear is due on a steady cadence -- the whole point is that the tear line MOVES. If they
        clump at the end, potency is dead for most of the run, which is the bug we came to fix."""
        ladder = self._ladder()
        n_tear = sum(pg.FLASK_POTENCY_TEAR_COST)
        n = len(ladder)
        seen = 0
        for k, good in enumerate(ladder, start=1):
            if good == _TEAR:
                seen += 1
            owed = k * n_tear / n
            self.assertLessEqual(
                abs(seen - owed), 2.0,
                f"tear cadence drifted at rung {k}: {seen} tears vs ~{owed:.1f} owed on a proportional "
                f"schedule. Jitter may move a rung by one step, never clump the track.")
        # at least one tear inside the opening stretch: potency must come online early
        self.assertIn(_TEAR, ladder[:6], "no Sacred Tear in the first 6 copies -- potency starts dead")

    def test_ladder_is_deterministic_per_seed(self):
        """create_items and fill_slot_data must never disagree about which ladder they built."""
        self.assertEqual(self._ladder(), self._ladder(), "flask_ladder must be cached, not re-rolled")

    # ---- pool + contract ----------------------------------------------------------------------
    def test_vanilla_seeds_and_tears_are_replaced_one_for_one(self):
        """The copies come from SUBSTITUTING the seed/tear checks the seed actually kept, not from a
        fixed count -- so the pool stays count-exact and the ladder scales with num_regions/DLC. Both
        vanilla items must be gone: shipping discrete seeds AND progressive copies would double the
        track."""
        names = world_item_names(self)
        for vanilla in pg.VANILLA_FLASK_ITEMS:
            self.assertEqual(names.count(vanilla), 0,
                             f"{vanilla} still in the pool alongside {pg.PROG_FLASK}")
        self.assertGreater(names.count(pg.PROG_FLASK), 0, "no progressive flask copies in the pool")

    def test_slot_data_ladder_matches_and_overflows(self):
        """The client reads progressiveGrants and already overflows copies past the ladder to a Lord's
        Rune -- so a full world (43 seeds + 13 tears = 56 checks vs a 42-rung ladder) has a soft tail,
        not dead pickups. Guards the contract shape AND that we are relying on overflow, not dodging
        it by shortening the pool."""
        sd = self.world.fill_slot_data()
        grants = sd[contract.PROGRESSIVE_GRANTS]
        self.assertIn(pg.PROG_FLASK, grants)

        ladder = self._ladder()
        goods = [rung["goods"] for rung in grants[pg.PROG_FLASK]]
        self.assertEqual(goods, [g | pg._GOODS_NIBBLE for g in ladder],
                         "slot_data ladder disagrees with the ladder create_items used")
        self.assertTrue(all(rung["flags"] == [] for rung in grants[pg.PROG_FLASK]),
                        "flask rungs are spend-at-grace goods; they set no flags")

        copies = world_item_names(self).count(pg.PROG_FLASK)
        self.assertGreater(copies, len(ladder),
                           f"a full world should place MORE copies ({copies}) than the ladder has rungs "
                           f"({len(ladder)}) -- the surplus rides the client's Lord's Rune overflow")


def test_option_is_frozen_off():
    """It BRICKS THE GAME. This test is the tripwire on turning it back on.

    er-logic reconcile.rs folds a progressive item's TIER goods into `unique_goods` -- a SELF-HEALING
    set meaning "the player should OWN this; if it is missing, grant it". Correct for the stone BELL
    BEARINGS the tier system was built for (a bell bearing is a key item you keep forever). Wrong, and
    dangerous, for a CONSUMABLE: a Golden Seed / Sacred Tear is SPENT at the grace, so the instant it
    leaves the inventory the reconciler hands it back. Upgrade -> re-grant -> upgrade -> re-grant, until
    the flask runs past its cap and the game crashes.

    Alaric, live playtest 2026-07-12: "sat down at grace, upgraded. still had the option to upgrade so
    kept going. kept going until game CTD'ed."

    reconcile.rs already HAS the right mechanism a few lines below -- overflow copies go to `d.ledgered`
    keyed by the copy's stream index, so they land exactly once. The tier path never got it, because no
    tier had ever granted a consumable before this one.

    So: do not flip this tuple to (1, None) until a tier can say "my goods are CONSUMED, not owned".
    The ladder itself (flask_ladder) is sound and stays -- the tests above prove it and un-skip with it.
    """
    from worlds.eldenring import defaults
    assert defaults.FROZEN_OPTIONS["progressive_flasks"] == (0, None), (
        "progressive_flasks must stay OFF until reconcile.rs can grant a tier's goods as CONSUMED "
        "(ledgered once) rather than OWNED (self-healing). Turning it on re-grants spent flask "
        "upgrade items forever and CTDs the game.")


# ---- the CTD, as a contract invariant ----------------------------------------------------------
def test_every_rung_declares_consumed_vs_owned():
    """The field that did not exist on 2026-07-12, and whose absence CTD'd a live playtest.

    The client folds a rung's goods one of two ways. OWNED -> `unique_goods`, a SELF-HEALING set
    ("the player should have this; if it is missing, grant it") -- right for a stone bell bearing, a
    key item you keep forever. CONSUMED -> ledgered by the copy's stream index, granted exactly once.

    A Golden Seed is SPENT at a grace. Shipped as OWNED, the reconciler saw it leave the inventory and
    handed it back: upgrade, re-grant, upgrade, re-grant, until the flask ran past its cap and the game
    crashed. The bug was possible because the dangerous behaviour was the SILENT DEFAULT.

    So every rung must SAY. `contract._chk_nested_grants` rejects a rung without it, and this asserts
    the two ladders declare the semantics their items actually have -- the flask spends, the bell keeps.
    """
    from worlds.eldenring.features import progressive as pg

    class _W:
        class options:
            class progressive_flasks: value = 1
            class progressive_stone_bells: value = 1
            class progressive_stonesword_keys: value = 0
        import random as _r
        random = _r.Random(1)
        player = 1

    feat = pg.Progressive()
    flask = feat._grant_ladder(_W, pg.PROG_FLASK)
    assert flask, "flask ladder is empty"
    assert all(r["consumed"] is True for r in flask), (
        "flask rungs grant Golden Seeds / Sacred Tears, which the player SPENDS at a grace. Marked "
        "owned, the client re-grants them forever and CTDs the game.")

    bell = feat._grant_ladder(_W, pg.PROG_SMITHING_BELL)
    assert bell, "bell ladder is empty"
    assert all(r["consumed"] is False for r in bell), (
        "a bell bearing is a KEY ITEM the player keeps -- it must stay self-healing (owned), or one "
        "lost to a save-scum never comes back")


def test_contract_rejects_a_rung_that_forgets_to_declare():
    """Belt and braces: the validator must REFUSE a rung with no `consumed`, so this can never again
    ship by omission."""
    from worlds.eldenring import contract

    bad = {"Progressive Flask Upgrade": [{"goods": 1073751844, "flags": []}]}
    err = contract._chk_nested_grants(bad)
    assert err and "consumed" in err, f"validator accepted a rung with no `consumed`: {err!r}"

    good = {"Progressive Flask Upgrade": [{"goods": 1073751844, "flags": [], "consumed": True}]}
    assert contract._chk_nested_grants(good) is None
