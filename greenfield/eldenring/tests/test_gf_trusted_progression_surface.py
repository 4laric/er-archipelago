"""Trusted-only widening for restricted own progression (#1358)."""
from types import SimpleNamespace

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.evidence_progression_hosts import trusted_aps  # noqa: E402
from worlds.eldenring.features import progression_surface as surface  # noqa: E402

GAME = "Elden Ring"


class _Multiworld:
    def __init__(self, locations):
        self._locations = locations

    def get_locations(self, _player):
        return self._locations


def test_final_widening_rung_is_exactly_open_enabled_trusted(monkeypatch):
    locations = [
        SimpleNamespace(address=11, item=None),
        SimpleNamespace(address=12, item=None),
        SimpleNamespace(address=13, item=object()),
        SimpleNamespace(address=14, item=None),
        SimpleNamespace(address=None, item=None),
    ]
    world = SimpleNamespace(player=1, multiworld=_Multiworld(locations))
    monkeypatch.setattr(surface, "_trusted_host_aps", lambda: frozenset({11, 13}))
    assert surface._open_trusted(world) == [locations[0]]


def test_tag_rungs_intersect_the_trusted_ledger(monkeypatch):
    locations = [SimpleNamespace(address=11, item=None), SimpleNamespace(address=12, item=None)]
    world = SimpleNamespace(player=1, multiworld=_Multiworld(locations))
    monkeypatch.setattr(surface, "surface_ap_ids", lambda _world, _classes: frozenset({11, 12}))
    monkeypatch.setattr(surface, "_trusted_host_aps", lambda: frozenset({11}))
    assert surface._open_allowed(world, ["MajorBoss"]) == [locations[0]]


class _TrustedRestrictedMixin:
    def test_every_reserved_progression_host_is_trusted_and_nothing_spilled(self):
        trusted = set(trusted_aps())
        placed = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.item is not None and loc.item.player == self.player
                  and surface.is_restricted_progression(loc.item, self.player)]
        self.assertTrue(placed, "the integration witness placed no restricted progression")
        offenders = [loc.name for loc in placed if loc.address not in trusted]
        self.assertFalse(offenders[:10], "restricted progression used HOLD: %s" % offenders[:10])
        self.assertEqual(self.world.gf_prog_surface_spilled, 0)


class SmallSeedUsesOnlyTrustedHosts(_TrustedRestrictedMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "enable_dlc": False, "progression_bias": 100}


class DefaultSeedUsesOnlyTrustedHosts(_TrustedRestrictedMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 6, "enable_dlc": True, "progression_bias": 100}


class NarrowSurfaceUsesOnlyTrustedHosts(_TrustedRestrictedMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "enable_dlc": True,
               "progression_surface": {"MajorBoss"}, "progression_bias": 100}
