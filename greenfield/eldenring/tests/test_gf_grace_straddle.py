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
    This is not hypothetical and it was the single largest entry on this list: `Altar South` appeared
    to span FOUR regions (Liurnia, Altus, Mt. Gelmir, Mountaintops of the Giants) because twelve
    checks 8.7-10.4 KILOMETRES away had anchored to it -- the resolver had no distance cap, and a
    nearest-neighbour with no cap never fails. Its four genuine checks are 59-201 m out and all
    Liurnia. The regions were right; the grace was wrong. Capped in build_nearest_grace.py
    (DEFAULT_MAX_DIST); 13 straddles' worth of noise left this screen with it. When a straddle looks
    geographically impossible, suspect the GRACE first.
Pinning the count is the honest middle: it cannot grow silently, and driving it down is real work
rather than an allowlist. DO NOT "fix" a failure here by adding an exemption -- quarantining to go
green is how the last one hid. Lower the number, then lower the pin.
"""
import os
import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS  # noqa: E402

# Measured on main 2026-07-25, after (a) the Cave of Knowledge map fix and (b) grouping on the
# grace's own KEY instead of its display name. A RATCHET, not a target: it may only ever go DOWN.
# RE-PINNED 2026-07-26 (39/98 -> 52/116) and the question this file's own failure message asks --
# "a new straddle means a region derivation moved" -- was ANSWERED FIRST, with a control, not assumed:
#
#   nearest_grace.tsv grew 3205 -> 3435 rows, because datamine_item_grace_coords.py --enemy located
#   the 61 enemy-source checks (--enemy is opt-in and the previous emit had not used it) and the
#   merchant fold added shop positions.
#
#   CONTROL -- recompute the straddles on the NEW table but restricted to the OLD flag set:
#       new table, all flags      52 graces / 116 minority
#       new table, OLD flags only 39 graces /  98 minority   <-- EXACTLY the old pins
#       old table                 39 graces /  98 minority
#
#   Not one existing check changed side. All 13 new straddling graces and all 18 new minority checks
#   are checks the oracle COULD NOT SEE BEFORE. No region derivation moved.
#
# ⚠️ These counts can only rise as the coordinate table improves, so they will keep going red for
# the right reason. Run that control before touching them again -- it is three lines and it answers
# the question outright:
#   restrict `keys` to the flags present in the PREVIOUS nearest_grace.tsv (git show <sha>:...) and
#   recompute. Unchanged => new checks. Changed => a derivation moved, and THAT is the bug.
#
# --- 2026-08-04, issue #338: 103 -> 150 minority, 49 -> 52 straddling graces (measured rows
# 3435 -> 3856). THE CONTROL THIS FILE PRESCRIBES WAS RUN, and it is unambiguous:
#       new table, OLD flags only:  49 graces / 103 minority   <-- EXACTLY the old measurement
#       old table                :  49 graces / 103 minority
#   0 checks changed grace, 0 lost one. No region derivation moved. The whole delta is checks the
#   oracle could not see before, because build_nearest_grace could not join 3-field overworld ids.
#
# ⭐ AND A MECHANISM THIS FILE DID NOT KNOW ABOUT, which is most of the delta: "minority" is
#   defined relative to a MUTABLE MAJORITY, so adding correctly-located checks to a grace can FLIP
#   which region is the majority and convert previously-majority checks into minority ones with
#   nothing having moved. Three graces flipped here -- Ancient Snow Valley Ruins (Mountaintops ->
#   Liurnia), Ancient Ruins Base (Scadu Altus -> Gravesite), Ranni's Chamber (Raya Lucaria ->
#   Limgrave) -- converting 27 checks on their own. The metric is NOT monotone under improvement.
#
# 🛑 Ranni's Chamber was checked by hand because "13 Limgrave checks nearest Ranni's Chamber" reads
#   like a region bug. It is not: they are Sorceress Sellen's 13 sorceries, all at one coordinate
#   (her LATE-questline position), and every one renders "from Sorceress Sellen" off the seller
#   layer -- the nearest-grace row is never shown. A merchant's endgame position is not evidence
#   about where their stock is regioned, which is the same objection this file already raises
#   against `via` rows. Worth excluding one day; recorded here rather than acted on, because it
#   changes what the screen MEASURES and that deserves its own change.
#
# ⚠️ CORRECTION to the line below it: "The share cannot be inflated by locating more checks" is
#   FALSE. It moved 3.00% -> 3.89% here, because the newly located population straddles at a higher
#   rate than the existing one. It is still the better quantity to defend -- it cannot be moved by
#   volume ALONE -- but it is not immune, and the ceiling has 0.11 points of headroom left.
MAX_STRADDLING_GRACES = 52
MAX_MINORITY_CHECKS = 150
# The share cannot be inflated by locating more checks, so it is the quantity to defend.
# Observed: 98/3205 = 3.1%, then 116/3435 = 3.4%, now 150/3856 = 3.9% (see the #338 note above).
MAX_MINORITY_SHARE = 0.040


def _nearest_grace(column=1):
    """flag (str) -> nearest_grace.tsv column. Beside the installed package (gf_test.py copies it).

    column 1 = grace NAME (for humans), column 2 = grace KEY (the grace's own warpUnlockFlag).

    GROUP ON THE KEY. Seven display names are shared by two physically distant graces -- the five
    Leyndell/Ashen-Capital map-version pairs (Divine Bridge, East Capital Rampart, Elden Throne,
    Erdtree Sanctuary, Queen's Bedchamber) plus two genuinely duplicated shacks (Artist's Shack in
    Liurnia and Altus, Isolated Merchant's Shack in the Weeping Peninsula and Dragonbarrow). Keyed on
    the name, this screen merged each pair into one bucket and reported the merge as a straddle.
    Measured: keying on the name gives 43 straddles / 115 minority checks, keying on the grace's own
    flag gives 41 / 111 -- so 2 of the reported straddles and 4 of the reported misregioned checks
    were the oracle's own doing (Artist's Shack and Queen's Bedchamber), indistinguishable in the
    output from real findings. Only 2 of the 7 duplicated names produced a phantom, because the pair
    must ALSO sit in different regions and both hold checks; the point is that nothing in the output
    said which. An oracle that manufactures findings is worse than one that misses them.

    ⭐ SAME REASONING, SECOND CASE (2026-07-27): rows with a non-empty `via` column are DERIVED
    positions and are EXCLUDED here. `boss_reward_coords.tsv` anchors a boss reward at the BOSS'S
    ARENA, not at the item -- so its nearest grace tells you where the boss is, which is not
    evidence about where the item is REGIONED. Feeding them in moved this screen 52 -> 53 straddles
    and 116 -> 118 minority checks: 7 derived rows landed on straddling graces (Prayer Room Key and
    Crusade Insignia both onto 'Theatre of the Divine Beast', Igon's rewards onto 'Foot of the
    Jagged Peak', 2 Deathroot onto overworld graces). Every one of those is a phantom of the
    anchoring, not a region derivation that moved -- which is exactly the failure mode the
    paragraph above exists to prevent, so the fix is to exclude them rather than raise the pin.
    This screen is an oracle over MEASURED geometry; an inferred anchor is not admissible evidence
    in it. Other consumers (a "near <grace>" descriptor) are welcome to the same rows.
    """
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nearest_grace.tsv")
    if not os.path.isfile(path):
        pytest.skip("nearest_grace.tsv not installed beside the package -- oracle would run BLIND")
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if parts[0] == "flag":
            continue  # header
        # column 3 = `via`: empty for a MEASURED position, else the derivation that produced it.
        # Derived rows are not admissible evidence in this screen -- see the docstring.
        if len(parts) > 3 and parts[3].strip():
            continue
        if len(parts) > column and parts[column]:
            out[parts[0]] = parts[column]
    assert out, "nearest_grace.tsv parsed to ZERO rows -- an empty oracle is a failure, not a pass"
    return out


def _straddles():
    """{grace key -> Counter(region)} for graces whose checks land in more than one region."""
    import collections
    region = {str(f): r for r, locs in LOCATIONS.items() for (_n, _a, f) in locs}
    keys = _nearest_grace(column=2)
    assert keys, (
        "nearest_grace.tsv has no grace_key column -- re-emit it with tools/build_nearest_grace.py. "
        "Falling back to the NAME would silently reintroduce the phantom straddles this screen "
        "exists to not manufacture.")
    by_grace = collections.defaultdict(collections.Counter)
    for flag, key in keys.items():
        r = region.get(flag)
        if r is not None:
            by_grace[key][r] += 1
    assert by_grace, "no check resolved to a grace -- the join matched nothing"
    return {g: c for g, c in by_grace.items() if len(c) > 1}


def _name_of(key):
    """Grace key -> its display name, for failure messages only."""
    return {k: n for k, n in zip(_nearest_grace(column=2).values(),
                                 _nearest_grace(column=1).values())}.get(key, key)


def _straddling_names():
    return sorted(_name_of(k) for k in _straddles())


def test_grace_straddle_count_does_not_grow():
    s = _straddles()
    assert len(s) <= MAX_STRADDLING_GRACES, (
        f"{len(s)} graces have checks in more than one region (pin {MAX_STRADDLING_GRACES}). "
        "A new straddle means a region derivation moved. Find which side is wrong -- do NOT raise "
        "the pin: " + ", ".join(_straddling_names()[:10]))


def test_minority_side_checks_do_not_grow():
    s = _straddles()
    minority = sum(sum(c.values()) - c.most_common(1)[0][1] for c in s.values())
    _total = len(_nearest_grace(column=2))
    _share = minority / _total if _total else 0.0
    assert _share <= MAX_MINORITY_SHARE, (
        f"{100.0 * _share:.1f}% of grace-resolved checks ({minority} of {_total}) sit on the minority "
        f"side of a straddling grace -- over the {100.0 * MAX_MINORITY_SHARE:.0f}% ceiling. THIS is "
        "the assertion that means something: locating more checks cannot move it, only a derivation "
        "getting worse can.")
    assert minority <= MAX_MINORITY_CHECKS, (
        f"{minority} checks sit on the minority side of a straddling grace (pin {MAX_MINORITY_CHECKS}). "
        "That is the upper bound on misregioned checks and it may only shrink.")


def test_the_church_of_pilgrimage_case_is_still_visible():
    # The reported bug, pinned as a NAMED case so the screen cannot silently stop seeing it.
    # Delete this test when the church resolves to one region -- and lower the pins in the same commit.
    assert "Church of Pilgrimage" in _straddling_names(), (
        "Church of Pilgrimage no longer straddles -- if that is a real fix, drop this test AND "
        "lower MAX_STRADDLING_GRACES / MAX_MINORITY_CHECKS in the same commit")
