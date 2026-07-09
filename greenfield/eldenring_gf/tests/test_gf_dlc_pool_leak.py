"""DLC pool-leak regression -- DLC items must never enter a DLC-off seed's pool (WorldTestBase, needs AP).

Guards the fix for the 2026-07-06 leak (seed "GFShatter", enable_dlc:false): region gating sealed DLC
*regions*, but the pool-AUGMENTATION paths (pool_builder juice, core varied filler, filler_foreign)
drew from the full ITEM_CATALOG / FILLER_POOL -- which is built from BASE **and** DLC FMG name tables --
so DLC gear/spells/remembrances flooded in as juice/filler regardless of enable_dlc.

The fix publishes world.gf_dlc_excluded (== DLC_ITEM_NAMES when DLC off, else empty) and the three
augmentation consumers drop it. These tests run the exact leaky option combo (item_shuffle +
pool_builder max + varied_filler) with DLC off and assert the resulting itempool is DLC-clean, plus
directly exercise the two solo-visible gate helpers and confirm the gate is inert when DLC is on.

importorskips when AP isn't importable (source-tree sandbox). Also skips (module-level) when
DLC_ITEM_NAMES is not yet generated -- i.e. before patch_greenfield_dlc_leak.py is applied and
gen_data.py has been re-run -- so a pre-patch CI run is a clean skip, not a collection error.

Run (from the Archipelago dir, world installed, AFTER apply + gen_data.py):
    python -m pytest worlds/eldenring_gf/tests/test_gf_dlc_pool_leak.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.item_ids import ITEM_CATALOG  # noqa: E402
try:
    from worlds.eldenring_gf.item_ids import DLC_ITEM_NAMES
except ImportError:  # patch not applied / gen_data.py not re-run yet -> skip cleanly, don't error CI
    pytest.skip("DLC_ITEM_NAMES not generated yet -- apply patch_greenfield_dlc_leak.py then "
                "run python greenfield/gen_data.py", allow_module_level=True)
from worlds.eldenring_gf.features.filler_foreign import filler_names  # noqa: E402
from worlds.eldenring_gf.features.pool_builder import PoolBuilderFeature  # noqa: E402

GAME = "Elden Ring (Greenfield)"
_DLC = frozenset(DLC_ITEM_NAMES)

# The exact leaky combo from the reported seed: every pool-augmentation path on, DLC off.
_LEAKY_DLC_OFF = {
    "enable_dlc": False,
    "item_shuffle": True,
    "pool_builder": True,
    "pool_builder_intensity": "max",
    "varied_filler": True,
}
# Canonical DLC items observed leaking in the report -- sanity anchors for the membership set.
_KNOWN_DLC = [
    "Rellana's Twin Blades", "Rellana's Twin Moons", "Messmer's Orb", "Messmer's Armor",
    "Shadow Sunflower Blossom", "Remembrance of the Shadow Sunflower", "Land of Shadow",
    "Gaius's Armor", "Young Lion's Armor",
]
# Base items that must NEVER be excluded -- incl. the 4 base<->DLC name collisions.
_KNOWN_BASE = ["Longsword", "Golden Rune [1]", "Smithing Stone [1]",
               "Golden Vow", "Larval Tear", "Beast Claw", "Perfumer's Talisman"]


class DLCNamesGenerated(WorldTestBase):
    """Pure-data guards on the generated DLC membership set (no world state needed)."""
    game = GAME

    def test_dlc_names_generated_and_sane(self):
        self.assertTrue(DLC_ITEM_NAMES, "gen_data.py must emit a non-empty DLC_ITEM_NAMES")
        # every catalog DLC name known to have leaked is flagged (when it resolved to the catalog)
        for n in _KNOWN_DLC:
            if n in ITEM_CATALOG:
                self.assertIn(n, _DLC, f"{n!r} is a DLC item and must be in DLC_ITEM_NAMES")
        # base items (including base<->DLC name collisions) are never flagged
        for n in _KNOWN_BASE:
            self.assertNotIn(n, _DLC, f"{n!r} is base -- must NOT be in DLC_ITEM_NAMES")

    def test_dlc_names_are_catalog_items(self):
        self.assertTrue(_DLC <= set(ITEM_CATALOG),
                        "DLC_ITEM_NAMES must be a subset of the real-item catalog")


class DLCOffNoPoolLeak(WorldTestBase):
    """The core regression: with DLC off and every augmentation path on, the pool is DLC-clean."""
    game = GAME
    options = _LEAKY_DLC_OFF

    def test_gate_published_and_nonempty(self):
        self.assertEqual(self.world.gf_dlc_excluded, _DLC,
                         "DLC-off world must exclude exactly DLC_ITEM_NAMES")
        self.assertTrue(self.world.gf_dlc_excluded, "exclusion set must be non-empty when DLC off")

    def test_no_dlc_item_in_itempool(self):
        leaked = sorted({i.name for i in self.multiworld.itempool
                         if i.player == self.player and i.name in _DLC})
        self.assertEqual(leaked, [], f"DLC items leaked into a DLC-off pool: {leaked[:20]}")

    def test_juice_order_has_no_dlc(self):
        order = PoolBuilderFeature()._juice_order(self.world)
        self.assertFalse([n for n in order if n in _DLC],
                         "pool_builder juice must contain no DLC items when DLC off")

    def test_filler_names_have_no_dlc(self):
        self.assertFalse([n for n in filler_names(self.world) if n in _DLC],
                         "foreign/varied filler names must contain no DLC items when DLC off")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCOnGateInert(WorldTestBase):
    """DLC on (default): the exclusion set is empty, so the gate is a no-op (no behavior change)."""
    game = GAME
    options = {"item_shuffle": True, "pool_builder": True,
               "pool_builder_intensity": "max", "varied_filler": True}

    def test_gate_empty_when_dlc_on(self):
        self.assertEqual(self.world.gf_dlc_excluded, frozenset(),
                         "DLC-on world must publish an empty exclusion set (gate inert)")

    def test_juice_order_unfiltered_when_dlc_on(self):
        # Not asserting DLC IS present (depends on the roll), only that the gate did not strip it:
        # the feature's order equals the unfiltered order when the exclusion set is empty.
        from worlds.eldenring_gf.features.pool_builder import juice_order_for_floor
        feat = PoolBuilderFeature()
        self.assertEqual(feat._juice_order(self.world),
                         juice_order_for_floor(feat._floor(self.world)),
                         "with DLC on the juice order must be unfiltered")
