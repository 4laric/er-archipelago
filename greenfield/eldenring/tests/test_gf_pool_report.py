"""pool_report._tally: multiworld-contribution counts bounded by construction (#995).

The bug: numerator (items placed in other worlds) and denominator (itempool) were measured against
DIFFERENT universes -- itempool excludes event items -- so the ratio could exceed 100%. _tally reads
ONE universe (placed locations), so `sent <= free <= pool` must hold for ANY input, including the
event-heavy pathological case that produced the original 155%. _tally is pure (rows in, dict out).
"""
import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring import pool_report as pr  # noqa: E402

ME = 1
# row = (item_owner, location_owner, is_event, item_name, class)


def _bound_holds(s):
    assert 0 <= s["sent"] <= s["free"] <= s["pool"], s
    pct = (100.0 * s["sent"] / s["free"]) if s["free"] else 0.0
    assert pct <= 100.0 + 1e-9, pct
    assert s["sent"] == s["sent_filler"] + s["sent_useful"] + s["sent_progression"]


def test_basic_sent_home_received():
    rows = [
        (ME, 2, False, "Sword", "useful"),
        (ME, 2, False, "Rune", "filler"),
        (ME, ME, False, "Shield", "useful"),
        (2, ME, False, "FF Item", "progression"),
    ]
    s = pr._tally(rows, ME, local=set())
    assert s["sent"] == 2 and s["received"] == 1 and s["home"] == 1
    assert s["pool"] == 3 and s["free"] == 3
    _bound_holds(s)


def test_events_are_excluded_and_the_ratio_stays_bounded():
    # The #995 shape: a flood of home event items (region locks / sweeps) itempool would miss.
    rows = [(ME, ME, True, f"Sweep {i}", "filler") for i in range(2000)]
    rows += [(ME, 2, False, f"Real {i}", "filler") for i in range(300)]
    rows += [(ME, ME, False, "Kept", "useful")]
    s = pr._tally(rows, ME, local=set())
    assert s["pool"] == 301 and s["free"] == 301   # 2000 events excluded from travelable
    assert s["sent"] == 300 and s["home"] == 2001
    _bound_holds(s)                                 # ~99.7%, NOT >100%


def test_held_local_items_are_not_free_and_not_sent():
    rows = [
        (ME, ME, False, "LocalOnly", "useful"),
        (ME, 2, False, "Travels", "filler"),
        (ME, ME, False, "Home", "filler"),
    ]
    s = pr._tally(rows, ME, local={"LocalOnly"})
    assert s["pool"] == 3 and s["held"] == 1 and s["free"] == 2 and s["sent"] == 1
    _bound_holds(s)


def test_nothing_mine():
    s = pr._tally([(2, 2, False, "x", "filler"), (3, 3, True, "y", "filler")], ME, local=set())
    assert s["sent"] == 0 and s["received"] == 0 and s["pool"] == 0 and s["free"] == 0
    _bound_holds(s)
