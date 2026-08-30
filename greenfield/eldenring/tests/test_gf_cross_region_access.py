import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features import cross_region_access as cross_access  # noqa: E402


STAGEFRONT_FRAGMENT_AP = 7771810


def test_unavailable_when_neither_route_exists(monkeypatch):
    class World:
        def _kept(self):
            return {"Belurat"}

    monkeypatch.setattr(cross_access, "_swept_members", lambda _world: set())
    assert not cross_access.location_available(World(), STAGEFRONT_FRAGMENT_AP)


class _StagefrontMixin:
    game = "Elden Ring"
    options = {"enable_dlc": True, "num_regions": 0}

    def _without_enir_lock(self):
        state = self.multiworld.get_all_state(False)
        lock = next(item for item in self.multiworld.get_items()
                    if item.player == self.world.player and item.name == "Enir Ilim Lock")
        state.remove(lock)
        return state

    def _location(self):
        return next(location for location in self.multiworld.get_locations(self.world.player)
                    if location.address == STAGEFRONT_FRAGMENT_AP)


class TestStagefrontFragmentAccess(_StagefrontMixin, WorldTestBase):

    def test_physical_pickup_requires_enir_ilim_without_sweep(self) -> None:
        location = self._location()
        self.assertTrue(location.can_reach(self.multiworld.get_all_state(False)))
        self.assertFalse(location.can_reach(self._without_enir_lock()))


class TestStagefrontFragmentSweepAccess(_StagefrontMixin, WorldTestBase):
    options = {
        **_StagefrontMixin.options,
        "dungeon_sweep": "bosses",
        # The default surface deliberately takes Fragments back out of sweeps. This seed shape
        # witnesses the independent sweep route by leaving the surface unconstrained.
        "progression_surface": [],
    }

    def test_dancing_lion_sweep_is_independent_of_enir_ilim(self) -> None:
        location = self._location()
        self.assertTrue(location.can_reach(self._without_enir_lock()))
