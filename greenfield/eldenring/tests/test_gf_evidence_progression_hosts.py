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


def test_certification_promotes_generated_hold_but_not_finale(monkeypatch):
    monkeypatch.setattr(policy, "_generated_sets", lambda: ({11}, frozenset({12, 13})))
    monkeypatch.setattr(policy, "certified_aps", lambda: frozenset({12, 13}))
    monkeypatch.setattr(policy, "_always_hold_aps", lambda: frozenset({13}))
    monkeypatch.setattr(policy, "oracle_sweep_aps", lambda: frozenset())
    assert policy.hold_aps(None, candidates={11, 12, 13, 14}) == {13, 14}


def test_sweep_backed_corroboration_promotes_generated_hold_but_not_finale(monkeypatch):
    """The third promotion source behaves exactly like certification: it lifts a row out of the
    generated HOLD complement and out of the fail-closed complement, and never past the finale
    lifecycle bar."""
    monkeypatch.setattr(policy, "_generated_sets", lambda: ({11}, frozenset({12, 13, 14})))
    monkeypatch.setattr(policy, "certified_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_always_hold_aps", lambda: frozenset({13}))
    monkeypatch.setattr(policy, "oracle_sweep_aps", lambda: frozenset({12, 13, 15}))
    # 12 promoted; 13 promoted by the table but held by the finale bar; 14 stays generated HOLD;
    # 15 is not in the generated partition at all (fail-closed complement) and is promoted too.
    assert policy.hold_aps(None, candidates={11, 12, 13, 14, 15, 16}) == {13, 14, 16}
    assert policy.trusted_aps() == {11, 12, 13, 15}


def test_oracle_sweep_aps_is_the_three_way_intersection(monkeypatch):
    """Corroborated AND swept AND NOT missable AND NOT finale, from the tables alone."""
    import sys
    import types
    pkg = "worlds.eldenring.tables"
    saved = {k: sys.modules.get(k) for k in (pkg + ".oracle_corroborated_hosts",
                                             pkg + ".boss_sweeps", pkg + ".missable_locations")}
    try:
        corr = types.ModuleType(pkg + ".oracle_corroborated_hosts")
        corr.ORACLE_CORROBORATED_APS = frozenset({1, 2, 3, 4, 5})
        sweeps = types.ModuleType(pkg + ".boss_sweeps")
        sweeps.DUNGEON_SWEEPS = {100: [1, 2, 3, 9], 200: [4]}
        miss = types.ModuleType(pkg + ".missable_locations")
        miss.MISSABLE_LOCATIONS = {3: "questline"}
        for m in (corr, sweeps, miss):
            sys.modules[m.__name__] = m
        monkeypatch.setattr(policy, "_always_hold_aps", lambda: frozenset({4}))
        monkeypatch.setattr(policy, "__package__", "worlds.eldenring.features")
        # 1, 2: corroborated, swept, clean. 3: missable. 4: finale. 5: not swept. 9: not corroborated.
        assert policy.oracle_sweep_aps() == {1, 2}
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
