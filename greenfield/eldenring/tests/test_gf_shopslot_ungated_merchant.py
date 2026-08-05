"""A merchant may hold a progression slot only if it is reachable UNGATED.

MOTIVATING CASE (rule 11, 2026-08-05). The spell-vendor re-key (PR #391) fixed the reported Gowry
check but left the same defect wearing a different door: `Gravesite :: Note: Sealed Spiritsprings -
from Moore` (talk 415006100) sells notes, not spells, and Moore only becomes a merchant once you
progress him. Pidia (307106000) and Smithing Master Iji (224006000) are the same shape. Alaric:
"I don't want any merchant where you have to do that much to make them appear."

THE PREDICATE. `esd_gates.tsv` records one row per GATE PATH onto a shop range; gate_flag -1 means
that path is unconditional. A merchant qualifies iff it has at least one -1 path. Of the 44
non-spell merchants, 22 qualify and 21 are gated-only -- and the gated-only list reads exactly like
what it should (Gostoc, Patches, Bernahl, Thiollier, Blackguard, Rogier, Moore, Pidia, Iji).

WHY THIS IS ANSWERABLE WHEN THE ROW-LEVEL VERSION IS NOT. gen_data's criterion-2 note says the ESD
gate is "not usable yet" -- that is about deciding START-STOCKED per ROW, where joining ungated
ranges collapses to 31 rows at one merchant. The MERCHANT-level question ("has this NPC any
unconditional path at all") does not collapse. Different question; the objection does not transfer.

THE SPY. test_spy_the_dropped_three_are_gated_not_absent keeps this file honest: it asserts the three
merchants are gated-because-their-paths-carry-flags, not gated-because-the-tsv-forgot-them. If the
esd_gates join ever thins out, every merchant would trivially "fail" the criterion and these tests
would pass for the wrong reason -- the spy fails first and says so.
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                                        # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
pytestmark = pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)

# The three the criterion exists to drop, by talk ESD.
MOORE = "415006100"
PIDIA = "307106000"
IJI = "224006000"
DROPPED = {MOORE: "Moore", PIDIA: "Pidia, Carian Servant", IJI: "Smithing Master Iji"}
UNGATED = "-1"


def _gf(*parts):
    return os.path.join(_ROOT, "greenfield", *parts)


def _tags():
    spec = importlib.util.spec_from_file_location(
        "_gf_location_tags_ungated_test", _gf("eldenring", "location_tags.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gate_flags():
    """talk_id -> the set of gate_flags on its paths. Derived, never pinned."""
    flags = {}
    with open(_gf("esd_gates.tsv"), encoding="utf-8-sig") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            q = line.rstrip("\n").split("\t")
            if len(q) < 2 or not q[0].isdigit():
                continue
            flags.setdefault(q[0], set()).add(q[1].strip())
    assert flags, "esd_gates.tsv parsed to NOTHING -- the criterion has no input and is vacuous"
    return flags


def test_gated_merchants_hold_no_progression_slot():
    lt = _tags()
    for talk, who in DROPPED.items():
        assert talk not in lt.SHOP_SLOT_PINS, (
            "%s (%s) is pinned again -- a merchant you must first make appear may not host this "
            "world's progression" % (who, talk))
        assert "not reachable ungated" in lt.SHOP_SLOT_SKIPS.get(talk, ""), (
            "%s must be skipped for the STATED reason, not silently absent: %r"
            % (who, lt.SHOP_SLOT_SKIPS.get(talk)))


def test_every_pinned_merchant_has_an_ungated_path():
    """The invariant. The three above are cases of it, not the rule itself."""
    flags, lt = _gate_flags(), _tags()
    # WITNESS (test_gf_vacuous_pass): say out loud that this function SAW candidates. With no pins
    # the comprehension below is empty and the invariant passes for the wrong reason.
    assert lt.SHOP_SLOT_PINS, "no ShopSlot pins at all -- this invariant would pass vacuously"
    offenders = {t: sorted(flags.get(t, ())) for t in lt.SHOP_SLOT_PINS
                 if UNGATED not in flags.get(t, set())}
    assert not offenders, (
        "pinned merchants with no unconditional ESD path onto their shop: %r" % offenders)


def test_spy_the_dropped_three_are_gated_not_absent():
    """Anti-vacuity: they must FAIL the criterion by carrying gate flags, not by being missing from
    esd_gates.tsv entirely -- otherwise a thinned join would satisfy this file for the wrong reason."""
    flags = _gate_flags()
    for talk, who in DROPPED.items():
        own = flags.get(talk, set())
        assert own, ("%s (%s) has NO esd_gates row at all -- this file would then be asserting "
                     "nothing about gating" % (who, talk))
        assert UNGATED not in own, (
            "%s now has an unconditional path %r, so the criterion no longer drops him and this "
            "file has stopped guarding what it claims" % (who, sorted(own)))


def test_the_criterion_is_not_eating_the_whole_pool():
    """A predicate that drops everything is a broken predicate, not a strict one. The zero-pins
    FATAL in gen_data guards generation; this guards the SHAPE -- plain roadside merchants survive."""
    lt = _tags()
    assert len(lt.SHOP_SLOT_PINS) >= 8, (
        "only %d ShopSlot pins survive -- the ungated criterion has over-eaten the pool"
        % len(lt.SHOP_SLOT_PINS))
