"""The four collectathon lines are POWER, not filler, and the filler tail must never eat them.

WHY THIS TEST EXISTS
--------------------
`Golden Seed` and `Sacred Tear` were protected from displacement. Their DLC counterparts --
`Scadutree Fragment` and `Revered Spirit Ash` -- were not. All four are GOODS, so
`_is_junk_consumable` called the unprotected two junk, and `filler_budget` displaced every one of
them: a DLC seed shipped with ZERO Scadutree Fragments in the pool.

Scadutree blessing is the DLC's entire damage/defence curve. With no fragments it can only come from
the per-region FLOOR -- and that lookup was independently broken by the play_region bucket bug. So the
DLC's power curve was pinned at zero by two bugs that could not see each other, and every per-pass
test stayed green because each pass was locally correct.

Note the SHAPE of the omission: base-game lines guarded, DLC lines not. The DLC had never been played,
so nothing that was only wrong in the DLC ever surfaced. That is the class of bug this file exists to
close, so the assertion is DERIVED from `COLLECTATHON_ITEMS` rather than listing four names again --
a fifth line cannot be added without being protected.
"""
import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features import filler_curation as fc  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GOODS = 0x40000000


def test_every_collectathon_line_is_in_the_catalog():
    # If a name here stops matching the catalog (a rename upstream), the protection below silently
    # protects nothing -- which is exactly how the DLC two went missing. Fail loudly instead.
    missing = [n for n in fc.COLLECTATHON_ITEMS if n not in ITEM_CATALOG]
    assert not missing, f"collectathon items absent from ITEM_CATALOG (protection would be inert): {missing}"


def test_collectathon_lines_are_goods_and_would_otherwise_be_eaten():
    # The precondition that makes this bug possible: they are GOODS, so the junk predicate would claim
    # them if they were not explicitly protected. If this ever stops holding, the guard is load-bearing
    # for a reason that no longer exists and someone should find out why.
    for name in fc.COLLECTATHON_ITEMS:
        full = ITEM_CATALOG[name]
        assert (full & 0xF0000000) == GOODS, f"{name} is not GOODS -- re-derive this guard"


def test_no_collectathon_line_is_junk_consumable():
    eaten = [n for n in fc.COLLECTATHON_ITEMS if fc._is_junk_consumable(n)]
    assert not eaten, (
        "the filler tail would DISPLACE these permanent power items: %s.\n"
        "Golden Seed / Sacred Tear were protected and the DLC's Scadutree Fragment / Revered Spirit "
        "Ash were not, which shipped DLC seeds with zero fragments and a blessing pinned at 0." % eaten
    )
