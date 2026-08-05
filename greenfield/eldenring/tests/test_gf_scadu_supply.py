"""scadu_supply -- the blessing's fragment supply must match the cap that was budgeted for it.

THE BUG THIS PINS. `SCADU_BLESSING_CAP` exists to bound an INJECTION (SPEC §9.2: *"Injection
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
        # 46 natural >= 26 needed: the spec's "a DLC seed injects none" as a CONSEQUENCE.
        assert ss.fragments_to_inject(2, 12, 46, 4000, False) == 0

    def test_dlc_excluded_injects_nothing(self):
        # Injecting a DLC good into a DLC-off pool is the test_gf_dlc_pool_leak class.
        assert ss.fragments_to_inject(2, 12, 0, 2000, True) == 0

    def test_an_out_of_range_cap_refuses_rather_than_guessing(self):
        assert ss.fragments_to_inject(1, 0, 0, 2000, False) == 0
        assert ss.fragments_to_inject(1, 99, 0, 2000, False) == 0

    def test_the_clamp_binds_on_a_degenerate_pool(self):
        """The guard has no corpus case -- the smallest real seed is 727 locations and needs 26 --
        so it gets a DIRECT call, or it is untested (guard-absent-from-corpus-needs-a-direct-call)."""
        assert ss.fragments_to_inject(1, 12, 0, 100, False) == 10   # 10% of 100
        assert ss.fragments_to_inject(1, 12, 0, 0, False) == 0


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
               "global_scadutree_blessing": 2}

    def _pool_fragments(self):
        try:
            from ._util import world_items
        except ImportError:
            from _util import world_items
        return sum(1 for i in world_items(self) if i.name == ss.FRAGMENT)

    def test_a_rolled_default_seed_reaches_the_cap(self):
        cap = sc.SCADU_BLESSING_CAP
        need = ss.SCADU_CUM[cap]
        got = self._pool_fragments()
        assert got >= need, (
            f"blessing cap {cap} needs {need} fragments; this seed's pool has {got}. "
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
