"""The tutorial Grafted Scion must not sweep Stormveil Castle.

MOTIVATING CASE (CONTRIBUTING rule 11), dafranky67 on Nexus 2026-07-29:
"when i killed grafted scion in the start it gave me like 30 items?" and "i get so much op stuff
from any boss killed".

It was 36. The game buckets m10_01 (the ruined Chapel of Anticipation intro, where a fresh character
fights or flees the Grafted Scion) under Stormveil (m10). gen_data's legacy DIVVY then counted the
Scion as one of Stormveil's legacy bosses and handed it a round-robin slice of the region's filler --
Ash of War: Storm Assault, Misericorde, smithing stones by Rampart Tower -- for killing an OPTIONAL
TUTORIAL boss in the first few minutes, from a legacy dungeon gated behind Margit.

🛑 THE LESSON, and why this test is worth its weight: region_groups.py ALREADY excluded this exact
fold (bucket 10010) from kick-watch geometry, for the same reason, after it CTD'd a playtest. The
fold had two consumers; one was fixed and the other was not, and nothing connected them. When a
data fold needs an exception, grep for every consumer of the fold -- an exception applied once is
not an exception applied.
"""
import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION  # noqa: E402

# 🛑 THERE ARE TWO GRAFTED SCIONS AND THEY ARE NOT THE SAME FIGHT (Alaric, 2026-07-29). Stormveil
# Castle has its own Grafted Scion, distinct from the intro one. Only the INTRO one is excluded here.
# Checked rather than assumed, because excluding the wrong one would both leave the bug in place and
# silently delete a real Stormveil sweep:
#   * boss_healthbars holds exactly ONE Grafted Scion -- 10010800, map m10_01 (the intro).
#   * m10_00's EMEVD declares exactly two banner bosses, 10000800 Godrick and 10000850 Margit. The
#     Stormveil Scion gets no defeat banner, so it is legitimately absent from a banner-derived
#     corpus and never had a sweep to lose.
GRAFTED_SCION = 10010800          # boss_healthbars: ('m10_01', 'm10_01', 'legacy', 'Grafted Scion')
SCION_OWN_DROP_AP = 7773886       # Ornamental Straight Sword, f510030 -- a normal check, must SURVIVE


def test_the_tutorial_boss_grants_no_sweep():
    assert GRAFTED_SCION not in DUNGEON_SWEEPS, (
        "the tutorial Grafted Scion (m10_01) has a sweep again, of %d check(s) in %r. Killing it is "
        "possible in the first few minutes; its sweep pays out a legacy dungeon gated behind Margit."
        % (len(DUNGEON_SWEEPS.get(GRAFTED_SCION, [])), SWEEP_REGION.get(GRAFTED_SCION)))


def test_no_stormveil_sweep_is_keyed_on_a_non_stormveil_boss():
    """The general form: a sweep may only be paid by a boss that lives where the checks live."""
    from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS
    wrong = []
    for flag, region in SWEEP_REGION.items():
        if region != "Stormveil":
            continue
        info = BOSS_HEALTHBARS.get(flag)
        if info and not info[0].startswith("m10_00"):
            wrong.append((flag, info[0], info[3]))
    assert not wrong, (
        "a Stormveil sweep is keyed on a boss outside m10_00: %s. m10_01 is the intro map and rides "
        "Stormveil's bucket; it is not IN Stormveil." % wrong)


def test_the_scions_own_drop_is_untouched():
    """The fix removes a sweep, not a check. The boss's own reward is a normal location."""
    from worlds.eldenring.data import LOCATIONS
    every = {int(ap) for rows in LOCATIONS.values() for (_n, ap, _f) in rows}
    assert SCION_OWN_DROP_AP in every, (
        "the Grafted Scion's own drop (Ornamental Straight Sword, ap %d) vanished. The sweep "
        "exclusion must not remove the boss's reward check -- that is a different mechanism."
        % SCION_OWN_DROP_AP)


def test_the_sweep_corpus_did_not_shrink():
    """Removing the Scion redistributes Stormveil's pool; it must not DELETE checks from it.

    A fix that quietly drops coverage is the same bug pointed the other way -- the pool is
    partitioned round-robin, so losing a boss means bigger slices for the real ones, not fewer
    checks. 3197 is the count with the exclusion in place."""
    total = sum(len(v) for v in DUNGEON_SWEEPS.values())
    assert total == 3197, (
        "sweep corpus is %d, expected 3197. If a sweep was legitimately added or removed, say WHY "
        "here -- do not just re-baseline the number." % total)
