"""Enforce the evidence-backed progression-host allow-list.

The generated evidence table answers a deliberately narrow question: which checks have enough
location evidence to be trusted with an advancement item.  This module is the policy seam between
that data and fill.  It bars advancement from *every* owner at every other check, while leaving
useful and filler placement available to normal fill.

The import may be absent in a pre-regen development checkout.  That state is fail-open only so the
generator can bootstrap; release generation always supplies ``evidence_progression_hosts.py`` and
the generated-data drift gate verifies it.
"""
from typing import FrozenSet, Iterable, Optional


def certified_aps() -> FrozenSet[int]:
    """Return direct maintainer adjudications, kept distinct from external corroboration."""
    try:
        from ..certified_progression_hosts import CERTIFIED_PROGRESSION_HOST_APS
    except ImportError:
        return frozenset()
    return frozenset(CERTIFIED_PROGRESSION_HOST_APS)


def trusted_aps() -> FrozenSet[int]:
    """Return every externally corroborated, directly adjudicated, or sweep-backed host."""
    generated_trusted, _generated_hold = _generated_sets()
    return frozenset(generated_trusted or ()) | certified_aps() | oracle_sweep_aps()


def oracle_sweep_aps() -> FrozenSet[int]:
    """Return the checks the shipping accuracy bar itself makes safe hosts (2026-09-23).

    The bar is: sweep mode is the default, and a sweep-granted check is a reachable check -- kill
    the owning boss and the check registers whatever the pickup's own placement did. So a check
    that (1) a second, independently curated table of the same game also carries, with no review
    queue disputing it (``tables/oracle_corroborated_hosts``), (2) some boss sweep grants, and
    (3) is not missable, cannot strand required progression through a placement error: the
    identity is corroborated, and reachability does not depend on the placement at all.

    This is the third promotion source beside the two-family wiki ledger and the certified list,
    and it is what lets ``progression_surface: []`` genuinely scatter (3,600-odd hosts against the
    ledger's 1,155) instead of quietly landing on the same few hundred rows every seed. Every
    OTHER bar still applies on top: this promotes out of the generated HOLD complement only, never
    out of the finale lifecycle bar, the surface exclusions, or the region-defaulted set.

    Fail-closed: a missing table on any side admits nothing.
    """
    try:
        from ..tables.oracle_corroborated_hosts import ORACLE_CORROBORATED_APS
        from ..tables.boss_sweeps import DUNGEON_SWEEPS
        from ..tables.missable_locations import MISSABLE_LOCATIONS
    except ImportError:
        return frozenset()
    swept = frozenset(ap for members in DUNGEON_SWEEPS.values() for ap in members)
    return ((frozenset(ORACLE_CORROBORATED_APS) & swept)
            - frozenset(MISSABLE_LOCATIONS) - _always_hold_aps())


def _generated_sets():
    try:
        from ..tables.evidence_progression_hosts import (HOLD_PROGRESSION_HOST_APS,
                                                  TRUSTED_PROGRESSION_HOST_APS)
    except ImportError:
        return None, frozenset()
    return (frozenset(TRUSTED_PROGRESSION_HOST_APS),
            frozenset(HOLD_PROGRESSION_HOST_APS))


def _all_location_aps() -> FrozenSet[int]:
    try:
        from ..tables.data import LOCATIONS
    except ImportError:
        return frozenset()
    return frozenset(ap for rows in LOCATIONS.values() for _name, ap, _flag in rows)


def _always_hold_aps() -> FrozenSet[int]:
    """Return checks whose lifecycle makes them unsafe hosts despite location corroboration."""
    try:
        from .finale import finale_entries
    except ImportError:
        return frozenset()
    # Finale checks are constructed outside the ordinary location loop and sit behind the goal.
    # External sources can corroborate their identity and region, but never make them safe places
    # for advancement required to reach that goal.
    return frozenset(ap for _name, ap, _flag in finale_entries())


def hold_aps(world, *, trusted: Optional[Iterable[int]] = None,
             candidates: Optional[Iterable[int]] = None) -> FrozenSet[int]:
    """Return checks that may not host advancement for this world.

    ``world`` is accepted because this is the shared per-world policy interface used by surface
    computation.  The current v0.6 policy is invariant across options: the generated allow-list is
    authoritative for every seed.  Explicit arguments make the rule independently testable and let
    generator tests use a tiny stub universe.
    """
    del world
    generated_trusted, generated_hold = _generated_sets()
    if trusted is None:
        trusted = (frozenset(generated_trusted or ()) | certified_aps() | oracle_sweep_aps()
                   if generated_trusted is not None else None)
    if trusted is None:
        return frozenset()  # pre-regen bootstrap only
    universe = frozenset(candidates) if candidates is not None else _all_location_aps()
    # The complement makes newly generated, unaudited checks fail closed.  The named HOLD set is
    # retained as an explicit audit result and catches corrupt tables whose rows escaped `data.py`.
    # A direct adjudication, or a sweep-backed corroborated check, intentionally promotes a row
    # out of the generated HOLD complement.
    effective_hold = generated_hold - certified_aps() - oracle_sweep_aps()
    return ((universe - frozenset(trusted)) | (effective_hold & universe)
            | (_always_hold_aps() & universe))


def apply_location_rule(world, location, *, trusted: Optional[Iterable[int]] = None) -> None:
    """Compose the all-owner advancement bar into ``location.item_rule`` when untrusted."""
    ap_id = getattr(location, "address", None)
    if ap_id is None:
        return
    if ap_id not in hold_aps(world, trusted=trusted, candidates=(ap_id,)):
        return
    previous = location.item_rule
    location.item_rule = lambda item, _p=previous: (
        not getattr(item, "advancement", False)) and _p(item)
