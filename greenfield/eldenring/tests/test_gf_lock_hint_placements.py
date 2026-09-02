"""Post-fill region-Lock placement disclosure (#581)."""

from types import SimpleNamespace

import pytest

from ..core import _lock_hint_placements


def _location(owner, address, item_name=None, receiver=None):
    item = None if item_name is None else SimpleNamespace(name=item_name, player=receiver)
    return SimpleNamespace(player=owner, address=address, item=item)


def test_foreign_location_keeps_its_owner_not_the_item_receiver():
    rows = [
        _location(1, 100, "Limgrave Lock", 1),
        _location(3, 200, "Stormveil Lock", 1),
        _location(3, 201, "Someone else's Lock", 2),
        _location(1, 202, "ordinary item", 1),
    ]
    assert _lock_hint_placements(rows, 1, {"Limgrave Lock", "Stormveil Lock"}) == {
        "Limgrave Lock": {"player": 1, "location": 100},
        "Stormveil Lock": {"player": 3, "location": 200},
    }


def test_unplaced_and_event_only_locks_are_omitted():
    rows = [_location(1, None, "Ashen Capital Lock", 1)]
    assert _lock_hint_placements(rows, 1, {"Ashen Capital Lock"}) == {}


def test_duplicate_lock_placement_is_refused_instead_of_nondeterministic():
    rows = [
        _location(1, 100, "Stormveil Lock", 1),
        _location(2, 200, "Stormveil Lock", 1),
    ]
    with pytest.raises(Exception, match="more than one"):
        _lock_hint_placements(rows, 1, {"Stormveil Lock"})
