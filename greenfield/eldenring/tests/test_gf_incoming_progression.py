"""Pure contract tests for #927's per-partner incoming progression reservation."""
import random
from types import SimpleNamespace

import pytest

from Fill import FillError
from ..features import progression_surface
from ..features.incoming_progression import (
    BalanceProgressionAcrossGames, _eligible_by_game, fair_sample_by_player, requested_share,
    reserve_incoming_progression)


def _item(player, name):
    return SimpleNamespace(player=player, name=name)


def test_balance_is_on_by_default():
    assert BalanceProgressionAcrossGames.default == 1


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


def test_insufficient_surface_capacity_fails_with_requested_breakdown(monkeypatch):
    foreign = [SimpleNamespace(player=2, name=f"Key {i}", advancement=True) for i in range(5)]
    partner = SimpleNamespace(game="Partner", options=SimpleNamespace(
        local_items=SimpleNamespace(value=set())))
    destination = SimpleNamespace(
        player=1, game="Elden Ring", options=SimpleNamespace(
            balance_progression_across_games=SimpleNamespace(value=1)))
    mw = SimpleNamespace(
        itempool=foreign, worlds={1: destination, 2: partner}, random=random.Random(927))
    destination.multiworld = mw
    monkeypatch.setattr(progression_surface, "_selection", lambda _world: {"MajorBoss"})
    monkeypatch.setattr(progression_surface, "selected_surface", lambda value: value)
    monkeypatch.setattr(progression_surface, "_open_allowed", lambda _world, _surface: [object()])

    with pytest.raises(FillError, match=r"requests 3 item\(s\).*only 1 open"):
        reserve_incoming_progression(mw, [destination])
