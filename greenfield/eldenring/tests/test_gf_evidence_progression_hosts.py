"""Focused unit tests for the v0.6 evidence-backed progression-host seam."""
import importlib.util
import os
from types import SimpleNamespace


HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(os.path.dirname(HERE), "features", "evidence_progression_hosts.py")
SPEC = importlib.util.spec_from_file_location("evidence_progression_hosts_policy", MODULE)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class _Location:
    def __init__(self, address, previous=lambda _item: True):
        self.address = address
        self.item_rule = previous


def _item(*, advancement, player):
    return SimpleNamespace(advancement=advancement, player=player)


def test_hold_aps_is_complement_of_stub_trust_set():
    assert policy.hold_aps(None, trusted={11, 13}, candidates={11, 12, 13, 14}) == {12, 14}


def test_untrusted_location_bars_advancement_from_every_owner():
    location = _Location(12)
    policy.apply_location_rule(None, location, trusted={11})
    assert not location.item_rule(_item(advancement=True, player=1))
    assert not location.item_rule(_item(advancement=True, player=99))
    assert location.item_rule(_item(advancement=False, player=1))
    assert location.item_rule(_item(advancement=False, player=99))


def test_trusted_location_preserves_existing_rule_unchanged():
    previous = lambda item: item.player != 7
    location = _Location(11, previous)
    policy.apply_location_rule(None, location, trusted={11})
    assert location.item_rule is previous


def test_untrusted_rule_composes_with_existing_rule():
    location = _Location(12, lambda item: item.player != 7)
    policy.apply_location_rule(None, location, trusted={11})
    assert location.item_rule(_item(advancement=False, player=1))
    assert not location.item_rule(_item(advancement=False, player=7))
    assert not location.item_rule(_item(advancement=True, player=1))


def test_empty_stub_trust_set_fails_closed():
    assert policy.hold_aps(None, trusted=(), candidates={11, 12}) == {11, 12}
