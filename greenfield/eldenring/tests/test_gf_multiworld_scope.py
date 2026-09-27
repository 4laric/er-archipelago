"""`multiworld_scope` (#1612) -- only Progression Surface checks exchange items with other worlds.

`all` must leave every knob exactly as written. `surface` must widen the non-surface bar from foreign
advancement to EVERY foreign item, force the knobs that would otherwise hold my own filler on the
surface, and refuse `progression_sharing: open` by name.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from Options import OptionError  # noqa: E402
from worlds.eldenring.features import multiworld_scope as mws  # noqa: E402
from worlds.eldenring.features import progression_surface as ps  # noqa: E402

GAME = "Elden Ring"


class _Item:
    def __init__(self, player, advancement):
        self.player, self.advancement, self.name = player, advancement, "x"


def test_foreign_item_barred_is_owner_only():
    assert mws.foreign_item_barred(_Item(2, False), 1)
    assert mws.foreign_item_barred(_Item(2, True), 1)
    assert not mws.foreign_item_barred(_Item(1, False), 1)
    assert not mws.foreign_item_barred(_Item(1, True), 1)


class ScopeAllDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_default_changes_nothing(self):
        o = self.world.options
        self.assertEqual(o.multiworld_scope.current_key, "all")
        self.assertEqual(self.world.gf_multiworld_scope_overrides, [])
        self.assertIs(ps.foreign_bar_for(self.world), ps.foreign_advancement_barred)
        self.assertTrue(o.keep_local.value)
        self.assertEqual(o.filler_foreign_pct.value, 70)


class ScopeSurface(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "multiworld_scope": "surface",
               "confine_foreign_progression": 40, "filler_foreign_pct": 10}

    def test_overrides_are_applied_and_recorded(self):
        o = self.world.options
        self.assertEqual(o.confine_foreign_progression.value, 100)
        self.assertEqual(o.filler_foreign_pct.value, 100)
        self.assertEqual(set(o.keep_local.value), set())
        names = {n for (n, _old, _new) in self.world.gf_multiworld_scope_overrides}
        self.assertEqual(names, {"confine_foreign_progression", "keep_local", "filler_foreign_pct"})

    def test_bar_widens_to_every_foreign_item(self):
        self.assertIs(ps.foreign_bar_for(self.world), mws.foreign_item_barred)
        self.assertIs(self.world._foreign_barred_fn, mws.foreign_item_barred)

    def test_non_surface_checks_refuse_foreign_filler_and_surface_takes_it(self):
        surf = self.world._foreign_confine_surface
        self.assertTrue(surf, "surface must resolve, or the mode is a silent no-op")
        foreign_filler = _Item(self.player + 1, False)
        own_filler = _Item(self.player, False)
        seen_non, seen_surf = 0, 0
        for loc in self.multiworld.get_locations(self.player):
            if loc.address is None or loc.item is not None:
                continue
            if loc.address in surf:
                continue
            seen_non += 1
            self.assertFalse(loc.item_rule(foreign_filler), loc.name)
            if seen_non >= 50:
                break
        self.assertGreater(seen_non, 0)
        for loc in self.multiworld.get_locations(self.player):
            if loc.address in surf and loc.item is None:
                seen_surf += 1
                if loc.item_rule(foreign_filler):
                    break
        else:
            self.fail("no surface check accepts a foreign filler item")
        self.assertTrue(any(loc.item_rule(own_filler)
                            for loc in self.multiworld.get_locations(self.player)
                            if loc.address is not None and loc.address not in surf))


def test_surface_with_open_sharing_is_refused():
    class _Opt:
        def __init__(self, value, key=None):
            self.value, self.current_key = value, key

    class _Opts:
        multiworld_scope = _Opt(mws.MultiworldScope.option_surface)
        progression_sharing = _Opt(1, "open")

    class _W:
        options = _Opts()

    with pytest.raises(OptionError, match="progression_sharing: open"):
        mws.apply_multiworld_scope(_W())
