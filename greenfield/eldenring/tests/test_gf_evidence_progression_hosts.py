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
    # The wiki row 11 is only a host while swept: pin that here so the test's expectation is
    # about certification alone.
    monkeypatch.setattr(policy, "_swept_aps", lambda: frozenset({11}))
    monkeypatch.setattr(policy, "_missable_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_oracle_corroborated_aps", lambda: frozenset())
    assert policy.hold_aps(None, candidates={11, 12, 13, 14}) == {13, 14}


def test_wiki_trust_without_a_sweep_is_held(monkeypatch):
    """2026-09-23: the two-family ledger ADMITS a row; only a boss sweep makes it a host. An
    unswept wiki-trusted row is play at your own risk and is held like any other."""
    monkeypatch.setattr(policy, "_generated_sets", lambda: ({11, 12}, frozenset({13})))
    monkeypatch.setattr(policy, "certified_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_always_hold_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_oracle_corroborated_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_missable_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_swept_aps", lambda: frozenset({11, 13}))
    # 11: wiki + swept -> host. 12: wiki, unswept -> held. 13: swept but corroborated by nobody.
    assert policy.trusted_aps() == {11}
    assert policy.hold_aps(None, candidates={11, 12, 13}) == {12, 13}


def test_sweep_backed_corroboration_promotes_generated_hold_but_not_finale(monkeypatch):
    """The oracle table is a second admission source beside the wiki ledger: a swept row it
    carries leaves the generated HOLD complement and the fail-closed complement, and never
    passes the finale lifecycle bar."""
    monkeypatch.setattr(policy, "_generated_sets", lambda: ({11}, frozenset({12, 13, 14})))
    monkeypatch.setattr(policy, "certified_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_always_hold_aps", lambda: frozenset({13}))
    monkeypatch.setattr(policy, "_oracle_corroborated_aps", lambda: frozenset({12, 13, 15}))
    monkeypatch.setattr(policy, "_missable_aps", lambda: frozenset())
    monkeypatch.setattr(policy, "_swept_aps", lambda: frozenset({11, 12, 13, 15, 16}))
    # 11 wiki+swept; 12 promoted; 13 promoted by the table but held by the finale bar; 14 stays
    # generated HOLD (unswept, uncorroborated by the oracle); 15 is outside the generated
    # partition (fail-closed complement) and is promoted; 16 is swept but nobody corroborates it.
    assert policy.hold_aps(None, candidates={11, 12, 13, 14, 15, 16}) == {13, 14, 16}
    assert policy.trusted_aps() == {11, 12, 15}


def test_sweep_backed_aps_is_the_intersection(monkeypatch):
    """(wiki OR oracle) AND swept AND NOT missable AND NOT finale."""
    monkeypatch.setattr(policy, "_generated_sets", lambda: ({1, 6}, frozenset()))
    monkeypatch.setattr(policy, "_oracle_corroborated_aps", lambda: frozenset({1, 2, 3, 4, 5}))
    monkeypatch.setattr(policy, "_swept_aps", lambda: frozenset({1, 2, 3, 4, 9}))
    monkeypatch.setattr(policy, "_missable_aps", lambda: frozenset({3}))
    monkeypatch.setattr(policy, "_always_hold_aps", lambda: frozenset({4}))
    # 1, 2: corroborated, swept, clean. 3: missable. 4: finale. 5: not swept. 6: wiki, unswept.
    # 9: swept, corroborated by nobody.
    assert policy.sweep_backed_aps() == {1, 2}


def test_sweep_backed_aps_reads_the_real_tables():
    """Against the shipped tables: every host is swept, none missable, none finale, and the set
    is large enough that an empty progression surface can actually scatter. Uses the INSTALLED
    module, because the by-path `policy` above has no package and its relative table imports
    resolve to nothing (fail-closed), which is a property, not a witness."""
    import pytest
    live = pytest.importorskip("worlds.eldenring.features.evidence_progression_hosts")
    hosts = live.sweep_backed_aps()
    assert len(hosts) > 3000, len(hosts)
    assert hosts <= live._swept_aps()
    assert hosts.isdisjoint(live._missable_aps())
    assert hosts.isdisjoint(live._always_hold_aps())
    assert hosts <= (live._generated_sets()[0] | live._oracle_corroborated_aps())
    # And the by-path copy really is fail-closed without a package.
    assert policy.sweep_backed_aps() == frozenset()
