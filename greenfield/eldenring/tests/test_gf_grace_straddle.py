"""GRACE-STRADDLE screen: two independent derivations, made to disagree out loud.

A Site of Grace sits in ONE region. So every check whose NEAREST grace is the same grace should land
in the same region -- and if a grace's checks straddle two regions, at least one derivation is wrong.

WHY THIS ORACLE: it needs no play_region -> region table, so it cannot be fooled by the `// 100`
bucket collapse that loses the game's own subdivision (Weeping is 61002, Limgrave 61000; both are
bucket 610). It compares the region assignment against the grace geometry and nothing else.

FOUND IT FIRST TRY (in-game report 2026-07-25): a Sacred Tear at the Church of Pilgrimage showed as
Limgrave. The church is Weeping. Nine checks share that grace; they split 5 Weeping / 4 Limgrave.
Neither the check's tile (m60_43_35) nor the grace's (m60_43_34) appears in `play_region_buckets.tsv`
at all -- 42 of the 203 tiles checks reference have no bucket -- so the region came from a
nearest-neighbour tile fallback, which never fails and therefore answered confidently and wrongly
(CONTRIBUTING rule 1: a derivation that cannot answer must FAIL, not answer).

NOT EVERY STRADDLE IS A DEFECT, which is why this pins a COUNT rather than demanding zero:
  * MAP VERSIONS -- `Leyndell, Capital of Ash` legitimately exists in both Leyndell and Ashen Capital.
  * `nearest_grace` is itself a nearest-neighbour derivation, so the GRACE may be the wrong one.
Pinning the count is the honest middle: it cannot grow silently, and driving it down is real work
rather than an allowlist. DO NOT "fix" a failure here by adding an exemption -- quarantining to go
green is how the last one hid. Lower the number, then lower the pin.
"""
import os
import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS  # noqa: E402

# Measured on main 2026-07-25. A RATCHET, not a target: it may only ever go DOWN.
MAX_STRADDLING_GRACES = 44
MAX_MINORITY_CHECKS = 117


def _nearest_grace():
    """flag (str) -> grace name. Beside the installed package (tools/gf_test.py copies the tsvs)."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nearest_grace.tsv")
    if not os.path.isfile(path):
        pytest.skip("nearest_grace.tsv not installed beside the package -- oracle would run BLIND")
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and parts[1]:
            out[parts[0]] = parts[1]
    assert out, "nearest_grace.tsv parsed to ZERO rows -- an empty oracle is a failure, not a pass"
    return out


def _straddles():
    import collections
    region = {str(f): r for r, locs in LOCATIONS.items() for (_n, _a, f) in locs}
    by_grace = collections.defaultdict(collections.Counter)
    for flag, grace in _nearest_grace().items():
        r = region.get(flag)
        if r is not None:
            by_grace[grace][r] += 1
    assert by_grace, "no check resolved to a grace -- the join matched nothing"
    return {g: c for g, c in by_grace.items() if len(c) > 1}


def test_grace_straddle_count_does_not_grow():
    s = _straddles()
    assert len(s) <= MAX_STRADDLING_GRACES, (
        f"{len(s)} graces have checks in more than one region (pin {MAX_STRADDLING_GRACES}). "
        "A new straddle means a region derivation moved. Find which side is wrong -- do NOT raise "
        "the pin: " + ", ".join(sorted(s)[:10]))


def test_minority_side_checks_do_not_grow():
    s = _straddles()
    minority = sum(sum(c.values()) - c.most_common(1)[0][1] for c in s.values())
    assert minority <= MAX_MINORITY_CHECKS, (
        f"{minority} checks sit on the minority side of a straddling grace (pin {MAX_MINORITY_CHECKS}). "
        "That is the upper bound on misregioned checks and it may only shrink.")


def test_the_church_of_pilgrimage_case_is_still_visible():
    # The reported bug, pinned as a NAMED case so the screen cannot silently stop seeing it.
    # Delete this test when the church resolves to one region -- and lower the pins in the same commit.
    s = _straddles()
    assert "Church of Pilgrimage" in s, (
        "Church of Pilgrimage no longer straddles -- if that is a real fix, drop this test AND "
        "lower MAX_STRADDLING_GRACES / MAX_MINORITY_CHECKS in the same commit")
