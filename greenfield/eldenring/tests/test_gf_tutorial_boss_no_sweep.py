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
    checks. 3197 was the count when the Scion exclusion landed.

    3197 -> 3187 (2026-08-01, legacy region-major routing audit). WHY, as this docstring demands --
    two fixes in one pass, net -10:

    +3  THE FINALE MAPS. Gideon, Godfrey/Hoarah Loux and Radagon/Elden Beast live on m11_05 and
        m19_00, whose _mreg vote was a TIE -- {Leyndell 3, Ashen Capital 3, Limgrave 1} and
        {Leyndell 1, Liurnia 1} -- broken to Leyndell by Counter insertion order. Now pinned to Ashen
        Capital, whose three checks (ap 7771132/7771133/7771134) previously belonged to NO sweep.
        Leyndell's pool is unchanged at 64; it re-divvies across 2 triggers instead of 6. That is the
        point: 42 of those 64 hung off post-burn bosses, and the burn warps you into m11_05
        PERMANENTLY, so they could never fire from base Leyndell.

    -13 THE HUB LEAK. m12_04 (Astel), m12_08 (Ancestor Spirit) and m12_09 (Regal Ancestor Spirit) got
        no vote at all and fell through `or HUB`, so those three were paying out ROUNDTABLE HOLD --
        13 checks in a region that is open from turn one, for kills in the Eternal Cities. Pinned to
        Ainsel River / Siofra River / Siofra River from the repo's own tables. Those regions' pools
        are unchanged (101 and 147); they simply gained triggers. The 13 hub checks are still
        obtainable by normal pickup -- a sweep is a convenience auto-grant, not the only source.

    The `or HUB` fallback is GONE, replaced by a gen-time assert naming every offender, so the next
    unregioned region major fails the build instead of quietly banking itself in the hub.

    Trigger count 241 -> 240: Ashen Capital's pool is 3 checks across 4 triggers, so the 4th
    (19000810 Radagon) gets an empty slice and is dropped. Harmless -- Radagon and the Elden Beast
    are ONE fight and 19000800 still carries it -- but it is why SWEEP_REGION is not a boss ROSTER.
    Anything needing "every boss in region R" must read BOSS_HEALTHBARS.

    3187 -> 3189 (2026-08-03, TWO tile curations -- gen_data.M60_TILE_CURATED). Trigger count
    unchanged at 240, no member LOST, two GAINED, ten sweeps re-partitioned. WHY:

    Both tiles hold no grace of their own, so tile_pr() nearest-neighboured them; both TIED at
    distance 1 between a Limgrave anchor and a Caelid one; both ties were settled by the row order
    of grace_flags.tsv. They fell OPPOSITE ways and both were wrong.

      m60_45_39  Summonwater Village / Third Church of Marika   Caelid   -> Limgrave  (12 checks)
      m60_47_38  Fort Gael                                      Limgrave -> Caelid    (15 checks)

    +2  ap 7774636 / 7774637 ("Smoldering Butterfly", m60_47_38) belonged to NO sweep, because the
        nearest field boss inside Chebyshev 2 of them was regioned across the seam from them and the
        nearest-boss pass is same-region. With m60_47_38 in Caelid they join the Caelid sweep
        1048370800 (13 -> 26). Nothing else entered the corpus.

     0  net redistribution across ten sweeps. 1045390800 (Summonwater) flips Caelid -> Limgrave,
        19 -> 24; seven neighbouring Limgrave field bosses shed what is now nearer to it; the Caelid
        pair 1047400800 (20 -> 27) and 1048370800 (13 -> 26) take back the Caelid ground. Every one
        of those moves is a check changing WHICH boss grants it, not whether.

    The bug: on a seed without Caelid the Summonwater trigger, its members and the Tibia Mariner's
    Deathroot (f530170) did not exist, so felling him paid nothing -- reported 2026-07-24 (Alaric)
    and again 2026-08-03 (boblerrr). Fort Gael is the same defect pointed the other way, found when
    Alaric answered a region-confirmation form and gave two different answers for one tile. See
    test_gf_boss_sweeps.test_summonwater_killsite_checks_are_limgrave.

    -18  (2026-08-04, #363) THREE SECONDARY ARENA HEADS lost their sweep: 30100801 Crucible Knight
        (m30_10, 8 members), 30120801 Perfumer Tricia (m30_12, 3) and 32050801 Crystalian (Spear)
        (m32_05, 7). Each is one head of an arena that ANOTHER head on the SAME map reports --
        GameAreaParam gives each of them defeat_flag != its own id and bonus_soul 0 -- while dungeon
        members are keyed on the MAP, so every head held the SAME list and the sweep paid the whole
        dungeon out when any one of them flipped. bobler got 7 Altus Tunnel checks on ENTERING the
        boss room, 69 seconds before the fight ended, after which the Crystalian he killed dropped
        nothing. The three PRIMARY triggers keep those members in full, so NO check left the corpus
        -- only the duplicate copies did (3189 -> 3171). See
        test_gf_boss_sweeps.test_no_secondary_arena_head_carries_a_sweep."""
    total = sum(len(v) for v in DUNGEON_SWEEPS.values())
    assert total == 3171, (
        "sweep corpus is %d, expected 3171. If a sweep was legitimately added or removed, say WHY "
        "here -- do not just re-baseline the number." % total)
