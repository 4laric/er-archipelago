"""Pure contract tests for #927's per-partner incoming progression reservation."""
import random
from types import SimpleNamespace

from ..features import progression_surface
from ..features.incoming_progression import (
    _eligible_by_game, fair_sample_by_player, requested_share, reserve_incoming_progression)


def _item(player, name):
    return SimpleNamespace(player=player, name=name)


def test_auto_is_the_default_and_aggregate_is_spellable():
    # The balanced shape IS the default (auto = -1), and the older one-batch shape kept a NAME
    # (#929's draft toggle was folded into auto -- `aggregate` is its "false" spelling).
    from ..features.progression_surface import CrossGameProgression
    assert CrossGameProgression.default == -1
    assert CrossGameProgression.special_range_names == {"auto": -1, "aggregate": -2, "never": 0}


def test_requested_share_is_nearest_one_over_n_half_up():
    assert requested_share(0, 3) == 0
    assert requested_share(1, 3) == 0
    assert requested_share(2, 3) == 1
    assert requested_share(4, 3) == 1
    assert requested_share(5, 3) == 2
    assert requested_share(7, 2) == 4
    assert requested_share(100, 1) == 0


def test_fair_sample_round_robins_slots_of_the_same_game():
    items = [_item(2, f"p2-{i}") for i in range(8)] + [_item(3, f"p3-{i}") for i in range(8)]
    chosen = fair_sample_by_player(items, 6, random.Random(927))
    assert len(chosen) == 6
    assert {player: sum(item.player == player for item in chosen) for player in (2, 3)} == {2: 3, 3: 3}


def test_fair_sample_redistributes_when_one_slot_runs_out():
    items = [_item(2, "only")] + [_item(3, f"p3-{i}") for i in range(8)]
    chosen = fair_sample_by_player(items, 5, random.Random(927))
    assert len(chosen) == 5
    assert sum(item.player == 2 for item in chosen) == 1
    assert sum(item.player == 3 for item in chosen) == 4


def test_fair_sample_is_seed_deterministic():
    items = [_item(player, f"p{player}-{i}") for player in (2, 3, 4) for i in range(5)]
    a = [item.name for item in fair_sample_by_player(items, 8, random.Random(17))]
    b = [item.name for item in fair_sample_by_player(items, 8, random.Random(17))]
    assert a == b


def test_owner_local_advancement_is_excluded_before_quota():
    local = SimpleNamespace(player=2, name="Local Key", advancement=True)
    travelling = SimpleNamespace(player=2, name="Travelling Key", advancement=True)
    useful = SimpleNamespace(player=2, name="Useful Gear", advancement=False)
    owner = SimpleNamespace(game="Partner", options=SimpleNamespace(
        local_items=SimpleNamespace(value={"Local Key"})))
    mw = SimpleNamespace(itempool=[local, travelling, useful], worlds={2: owner})
    assert _eligible_by_game(mw, {1}) == {"Partner": [travelling]}


def test_insufficient_surface_capacity_caps_the_share_loudly(monkeypatch, caplog):
    """The DERIVED cap: 5 eligible at a two-game table asks for 3, one open surface slot caps it
    at 1 -- generation proceeds (the shipped two-game smoke measured 135 requested vs 134 open;
    a default-on option must not fail the shipped configuration). The refused-placement error
    after fill_restrictive stays fatal and is not exercised here."""
    import logging

    foreign = [SimpleNamespace(player=2, name=f"Key {i}", advancement=True) for i in range(5)]
    partner = SimpleNamespace(game="Partner", options=SimpleNamespace(
        local_items=SimpleNamespace(value=set())))
    destination = SimpleNamespace(
        player=1, game="Elden Ring", options=SimpleNamespace(
            cross_game_progression=SimpleNamespace(value=-1)))   # auto = the balanced regime
    mw = SimpleNamespace(
        itempool=foreign, worlds={1: destination, 2: partner}, random=random.Random(927))
    destination.multiworld = mw
    mw.get_unfilled_locations = lambda _player: []   # no off-surface checks in this fixture
    monkeypatch.setattr(progression_surface, "_selection", lambda _world: {"MajorBoss"})
    monkeypatch.setattr(progression_surface, "selected_surface", lambda value: value)
    monkeypatch.setattr(progression_surface, "_open_allowed", lambda _world, _surface: [object()])

    seen = {}

    def _fake_fill(multiworld, state, locations, batch, **kwargs):
        seen["batch"] = list(batch)
        batch.clear()          # everything placed -- the cap, not the fill, is under test

    import Fill
    monkeypatch.setattr(Fill, "fill_restrictive", _fake_fill)
    mw.get_all_state = lambda _use_cache: object()

    with caplog.at_level(logging.WARNING, logger="eldenring"):
        reserve_incoming_progression(mw, [destination])

    # WITNESS: the pass really ran and really asked for the capped share.
    assert len(seen["batch"]) == 1, "the surface has one open slot; the reservation must cap at 1"
    assert "caps the reservation at 1 of 3" in caplog.text
    assert len(mw.itempool) == 4, "exactly the reserved item leaves the pool"
