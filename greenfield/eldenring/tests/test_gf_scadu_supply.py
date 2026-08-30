"""scadu_supply -- the blessing's fragment supply must match the cap that was budgeted for it.

THE BUG THIS PINS. `SCADU_INJECTION_TARGET` (was `scaling.SCADU_BLESSING_CAP`) exists to bound an INJECTION (SPEC §9.2: *"Injection
budget. SCADU_CUM[20] = 50 fragments is a lot of filler to displace in a base seed. Cap at 12 (26
fragments) instead?"*). The cap shipped; the injection did not. Measured 2026-08-01 over 40 rolled
seeds at the shipped default `num_regions: 6`, only ONE could reach the cap; the median seed topped
out at blessing 3 of 12. `test_a_rolled_default_seed_reaches_the_cap` is that measurement as a gate.
"""
import os
import re
import sys

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features import scadu_supply as ss  # noqa: E402
from worlds.eldenring.features import scaling as sc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
GAME = "Elden Ring"


# ---- the pure predicate ------------------------------------------------------------------------
class TestFragmentsToInject:
    def test_mode_off_injects_nothing(self):
        assert ss.fragments_to_inject(0, 12, 0, 2000, False) == 0

    def test_a_no_dlc_region_seed_gets_the_whole_budget(self):
        # SCADU_CUM[12] == 26
        assert ss.fragments_to_inject(1, 12, 0, 2000, False) == 26
        assert ss.fragments_to_inject(2, 12, 0, 2000, False) == 26

    def test_the_reported_seed(self):
        """AP_90729554631839684613: one DLC region (Enir Ilim), 3 natural fragments, cap 12.

        Rule 11 -- the case that motivated the work is the acceptance test, by name and by number.
        The spec's own trigger ("a DLC seed injects none") would return 0 here and leave the bug."""
        assert ss.fragments_to_inject(2, 12, 3, 2090, False) == 23

    def test_a_full_dlc_seed_injects_none(self):
        # 50 natural UNITS (46 lot slots, four of them x2 -- see tests/test_gf_location_units.py)
        # >= 26 needed: the spec's "a DLC seed injects none" as a CONSEQUENCE.
        assert ss.fragments_to_inject(2, 12, 50, 4000, False) == 0

    def test_dlc_excluded_injects_nothing(self):
        # Injecting a DLC good into a DLC-off pool is the test_gf_dlc_pool_leak class.
        assert ss.fragments_to_inject(2, 12, 0, 2000, True) == 0

    def test_an_out_of_range_cap_refuses_rather_than_guessing(self):
        assert ss.fragments_to_inject(1, 0, 0, 2000, False) == 0
        assert ss.fragments_to_inject(1, 99, 0, 2000, False) == 0

    def test_the_clamp_binds_on_a_degenerate_pool(self):
        """The guard has no corpus case -- the smallest real seed is 727 locations and needs 26 --
        so it gets a DIRECT call, or it is untested (guard-absent-from-corpus-needs-a-direct-call).

        UNITS IN, ITEMS OUT -- and this assertion did not survive the two being split. It read
        `== 10   # 10% of 100` and was correct while every injected fragment was exactly one pool
        item: the two spaces held the same number, so nothing had to name which one MAX_POOL_SHARE
        bounds. The x2 stack (`UNITS_PER_STACK_ITEM`, 2026-08-06) separated them -- the return is
        UNITS, the ceiling is on ITEMS -- and the assertion kept the old number, which is 13 units
        short of nothing but three units short of the answer. It was right about the share and
        wrong about the SPACE (CONTRIBUTING rule 3: name the space wherever two components exchange
        a value), so this is written in both spaces now and neither is a bare literal.

        2026-08-25 (#1013): the FLOOR now overrides the clamp up to SCADU_CUM[CLAMP_FLOOR_LEVEL].
        Target 12 IS the floor level, so this call is the maximal breach: the clamp sheds 26 -> 13
        (the largest injection whose ITEMS fit the share) and the floor lifts the return back to
        26. Both numbers are pinned -- the clamp still bounds everything ABOVE the floor, the floor
        bounds the loss."""
        ceiling_items = int(100 * ss.MAX_POOL_SHARE)
        self_units = ss.fragments_to_inject(1, 12, 0, 100, False)
        assert self_units == 26, "26 units: the clamp bound at 13, the floor overrode back to the cap"
        assert ss.items_for_units(self_units) == 20, (
            "the breach, stated in ITEM space: 26 units -> 20 items vs ceiling %d (~20%% of the "
            "pool -- the bounded cost of holding the floor; see CLAMP_FLOOR_LEVEL)" % ceiling_items)
        # The clamp itself still works underneath the floor: 13 units is the LARGEST injection
        # that fits -- one more unit's items overrun the share.
        assert ss.items_for_units(13) == ceiling_items == 10
        assert ss.items_for_units(14) > ceiling_items
        # ...and the floor does NOT fire on a pool too small to charge (zero ceiling): injecting
        # 26 units into <10 locations would BE the pool.
        assert ss.fragments_to_inject(1, 12, 0, 0, False) == 0
        # Above the floor the clamp is untouched: target 20 on the same pool sheds 48 -> 26, no
        # further (the floor is already met) and never to the target.
        assert ss.fragments_to_inject(1, 20, 0, 100, False) == 26


def test_natural_supply_reads_the_filtered_seed_locations():
    """A kept region is not the pool: progression-surface can remove individual checks.

    The planner used to walk raw LOCATIONS while core walked `_seed_locations`; crediting a
    filtered Fragment made the injector stop one unit early and produced a 49/50 rolled seed.
    """
    from types import SimpleNamespace
    from worlds.eldenring.data import HUB, LOCATIONS
    from worlds.eldenring.item_ids import LOCATION_ITEM
    from worlds.eldenring.core import item_name_to_id as catalog_ids, stacked_vanilla_name

    witness = next((region, ap_id) for region, rows in LOCATIONS.items() for _, ap_id, _ in rows
                   if region != HUB and LOCATION_ITEM.get(ap_id) == ss.FRAGMENT)
    region, removed_ap = witness

    class World:
        options = SimpleNamespace(item_shuffle=SimpleNamespace(value=1))
        gf_dlc_excluded = frozenset()
        item_name_to_id = catalog_ids

        @staticmethod
        def _kept():
            return [region]

        @staticmethod
        def _seed_locations(name):
            return [row for row in LOCATIONS.get(name, ()) if row[1] != removed_ap]

    raw_units = sum(stacked_vanilla_name(ss.FRAGMENT, ap, catalog_ids)[1]
                    for name in (HUB, region) for _, ap, _ in LOCATIONS.get(name, ())
                    if LOCATION_ITEM.get(ap) == ss.FRAGMENT)
    removed_units = stacked_vanilla_name(ss.FRAGMENT, removed_ap, catalog_ids)[1]
    assert ss.natural_fragments(World()) == raw_units - removed_units


# ---- the cross-repo constant -------------------------------------------------------------------
@pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)
def test_scadu_cum_matches_the_client_rung_for_rung():
    """One game constant, two repos. The client derives the live blessing level from its own copy,
    so a silent divergence would mean the world budgets for a curve the client does not use."""
    rs = os.path.join(_ROOT, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "upgrades.rs")
    if not os.path.exists(rs):
        pytest.skip("client not checked out beside the repo")
    with open(rs, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"SCADU_CUM:\s*\[i32;\s*21\]\s*=\s*\[(.*?)\]", src, re.S)
    assert m, "SCADU_CUM not found in er-logic/src/upgrades.rs -- did it move?"
    rust = tuple(int(x) for x in re.findall(r"-?\d+", m.group(1)))
    assert rust == ss.SCADU_CUM, f"ladder drift: rust {rust} vs world {ss.SCADU_CUM}"


# ---- every one-region seed, deterministically ---------------------------------------------------
def test_every_one_region_draw_clears_the_original_cap_under_the_clamp():
    """SPEC-ashen-capital-lock (2026-08-06) removed the `auto` force-keep of GOAL_REGION, so
    `num_regions: 1` produces genuinely one-region seeds (hub + one region, 240-360 locations) for
    the first time -- and on 16 of the 30 possible draws MAX_POOL_SHARE now BINDS: 50 units do not
    fit a 10% share, injection stops short of SCADU_INJECTION_TARGET, and create_items warns. That
    degrade is the design (the clamp's comment has said "a seed this small is already being told,
    loudly, that it cannot reach the target" since it landed); what it must never become is a
    STARVED blessing. This sweeps every possible draw -- deterministic where test_gf_options'
    one_region_dlc fixture is one rolled sample -- and pins the floor: natural + injected always
    reaches at least CLAMP_FLOOR_LEVEL (12, the original shipped cap the 12->20 target raise
    replaced; worst draw today injects 32 units, level 14). Conservative on purpose: feature
    extras (gf_extra_locations) only raise the ceiling, so they are counted as 0 here.

    If this fails, region geometry shrank past the point where the clamp starves the blessing
    below its original cap. That is a premise change -- take it back to a ruling on the
    clamp-vs-floor trade, not a number to relax. (2026-08-25, #1013: it happened -- Enia's 100
    hub rows left and the Abyssal draw fell to 22 units. The ruling landed: the floor is now
    enforced in code as a bounded breach of the share ceiling; see CLAMP_FLOOR_LEVEL. This sweep
    still gates it, now by construction of the breach bound.)"""
    from worlds.eldenring import region_spine as rspine
    from worlds.eldenring.data import HUB, LOCATIONS, REGIONS
    from worlds.eldenring.item_ids import LOCATION_ITEM, LOCATION_UNITS

    hub = len(LOCATIONS.get(HUB, []))
    target = ss.SCADU_INJECTION_TARGET
    floor_units = ss.SCADU_CUM[ss.CLAMP_FLOOR_LEVEL]
    clamped, unclamped = set(), set()
    for region in REGIONS:
        kept = [region] + rspine.parent_chain(region)
        total = hub + sum(len(LOCATIONS.get(r, [])) for r in kept)
        # UNITS, not placements (#616): four vanilla lot slots grant two fragments and
        # `natural_fragments` counts what they hand over, so a sweep that counted locations would
        # be measuring a supply the feature no longer reasons about.
        natural = sum(LOCATION_UNITS.get(ap_id, 1) for r in kept
                      for (_n, ap_id, _f) in LOCATIONS.get(r, [])
                      if LOCATION_ITEM.get(ap_id) == ss.FRAGMENT)
        want = max(0, ss.SCADU_CUM[target] - natural)
        for mode in (1, 2):
            injected = ss.fragments_to_inject(mode, target, natural, total, False)
            (clamped if injected < want else unclamped).add(region)
            assert natural + injected >= floor_units, (
                f"{region} (mode {mode}): a one-region seed here carries {natural} natural + "
                f"{injected} injected = {natural + injected} fragment unit(s), below "
                f"SCADU_CUM[{ss.CLAMP_FLOOR_LEVEL}] = {floor_units} -- the clamp is starving the "
                f"blessing below the original cap")
    # Both arms must actually occur, or the quantifier above is vacuous on the side that matters
    # (vacuous-quantifier discipline). Measured 2026-08-06: 16 draws clamp, 14 do not. Asserting
    # the split EXISTS, not its census -- the census moves with geometry and is not the invariant.
    assert clamped, ("no one-region draw binds the clamp any more -- this sweep has stopped "
                     "testing the degrade path; if that is a deliberate geometry change, the "
                     "one_region_dlc arm in test_gf_options is now dead code too")
    assert unclamped, "every one-region draw clamps -- the full-guarantee path is untested here"


# ---- full seeds ---------------------------------------------------------------------------------
class _Seed(WorldTestBase):
    game = GAME
    run_default_tests = False

    def _frags_in_pool(self):
        from worlds.eldenring.features.scadu_supply import FRAGMENT
        from .._util import world_items  # noqa
        return None


class ScaduSupplyRolledDefault(WorldTestBase):
    """The measured failure: a rolled seed at the SHIPPED default."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 6, "enable_dlc": 1,
               "scadutree_blessing_scope": "anywhere", "dlc_blessing_catchup": True}

    def _pool_fragments(self):
        try:
            from ._util import world_items
        except ImportError:
            from _util import world_items
        # UNITS: a `Scadutree Fragment x2` is one pool item worth two fragments. See the same note
        # in test_gf_options -- the blessing counts what was handed over, not how many items it
        # arrived in, and so must this.
        return sum(2 if i.name == ss.FRAGMENT_X2 else 1 for i in world_items(self)
                   if i.name in (ss.FRAGMENT, ss.FRAGMENT_X2))

    def test_a_rolled_default_seed_reaches_the_target(self):
        target = ss.SCADU_INJECTION_TARGET
        need = ss.SCADU_CUM[target]
        got = self._pool_fragments()
        assert got >= need, (
            f"injection target {target} needs {need} fragment units; this seed's pool has {got}. "
            "Before scadu_supply only 1 rolled seed in 40 cleared this.")

    def test_injected_fragments_are_useful_never_progression(self):
        try:
            from ._util import world_items
        except ImportError:
            from _util import world_items
        from BaseClasses import ItemClassification
        for i in world_items(self):
            if i.name == ss.FRAGMENT:
                assert i.classification != ItemClassification.progression, \
                    "fragments gate nothing; progression would over-constrain fill"


class ScaduSupplyOff(WorldTestBase):
    """Mode off must be byte-identical to before this feature existed."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 6, "enable_dlc": 1,
               "global_scadutree_blessing": 0}

    def test_mode_off_injects_nothing(self):
        mode, cap, natural, want, injected = ss.plan(self.world)
        assert mode == 0 and injected == 0 and want == 0
