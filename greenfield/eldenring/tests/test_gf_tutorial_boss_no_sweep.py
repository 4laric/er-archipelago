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
    r"""Removing the Scion redistributes Stormveil's pool; it must not DELETE checks from it.

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
        test_gf_boss_sweeps.test_no_secondary_arena_head_carries_a_sweep.

    -82  (2026-08-04, #363 part two) TWELVE MORE SECONDARY HEADS, from the EMEVD defeat banner
        rather than GameAreaParam. Trigger count 240 -> 225. Again NO CHECK LEFT THE CORPUS: every
        one of these is a duplicate copy of a list its arena's PRIMARY still holds in full, which is
        why the arithmetic is exactly the suppressed heads' own member counts --

          m30_14  30140801  Erdtree Burial Watchdog (Scepter)         4
          m31_06  31060801  Crystalian (Spear)                        2
          m31_07  31070801  Kindred of Rot                            7
          m31_10  31100801  Beastman of Farum Azula (Throwing Knife)  5
          m31_11  31110801 + 31110802  Putrid Crystalian x2          24  (12 each)
          m31_15  31150801  Demi-Human Chief                          3
          m31_18  31180801  Omenkiller                                8
          m31_20  31200801  Cleanrot Knight (Sickle)                  4
          m31_22  31220801 + 31220802  Godskin Apostle / Noble       18  (9 each)
          m34_14  34140851  Fell Twin                                 7
                                                                  ---- 82

        61 DISTINCT checks stop being payable by a boss the player has not fought. m34_14 is the one
        bobler confirmed live: he got its 7 checks on ENTERING the arena. GameAreaParam could not
        reach any of these -- it has no row for 34140851 at all -- so the discriminator is the game's
        own `HandleBossDefeatAndDisplayBanner`, which names ONE reporter per fight.

        Two of these contradict the guesses on #363's handoff, and the EMEVD wins: m31_18 (Miranda
        the Blighted Bloom + Omenkiller) was guessed SEPARATE and is one banner over both deaths;
        m31_22's Godskins are SUMMONS the snail's flag force-kills, not co-required heads.

        STILL SHARED, deliberately: m30_05, m30_13, m31_00 and m31_19 (32 checks). Each fires TWO
        banners, so each is genuinely two fights -- they need PARTITIONING and must NOT be
        suppressed. m31_19 Sage's Cave is pinned as the negative control in
        test_gf_boss_sweeps.test_sages_cave_retains_BOTH_triggers.

    -32  (2026-08-04, #363 part three -- the PER-MAP DIVVY) those four maps now PARTITION their
        filler between their two bosses instead of each holding the whole list. Trigger count is
        UNCHANGED at 225: both heads keep their trigger, because both fire their own defeat banner
        and suppressing either would delete a real boss's reward.

          m30_05  Black Knife Catacombs   4 checks -> 2 / 2
          m30_13  Auriza Side Tomb       10        -> 5 / 5
          m31_00  Murkwater Cave          4        -> 2 / 2
          m31_19  Sage's Cave            14        -> 7 / 7
                                        ---- 32 duplicate member links removed

        NO CHECK LEFT THE CORPUS AGAIN -- the -32 is exactly the duplicate second copy of each pool.
        Every check is still granted by exactly one of the map's two bosses, and the union per map
        is unchanged (test_the_multi_fight_dungeons_still_PARTITION_their_whole_pool pins it).

        WHY a round-robin and not an ownership rule: there is no owner to find. None of the 32
        carries an EMEVD arena association, and every one is untagged FILLER -- cave pickups, not
        boss rewards. Nearest-boss geometry was measured and REJECTED: all 14 Sage's Cave checks are
        nearer Necromancer Garris by 20-30m (the arenas are 39.8m apart while the checks sit 33-72m
        from both), so it would hand Garris 14 and the Black Knife Assassin 0. This is the same
        shape the LEGACY divvy has solved since 2026-07-11, so it uses the same partition.

        Player-visible: each of these eight bosses now grants about half what it did. That is the
        correction -- granting all of it was the bug.

      0 (2026-08-05, the m60 TILE DECODE fix) trigger count 225 -> 226, corpus UNCHANGED at 3056.
        NOTHING entered or left; 29 member links moved between Mountaintops field bosses.

        1248550800 -- the Night's Cavalry duo by Yelough Anix Tunnel -- had tile 'm60_48' instead of
        'm60_48_55', because datamine_boss_healthbars decoded overworld tiles only for ids starting
        "10". Overworld ids also come in a 12-form; Radahn, the Fire Giant and Borealis survived the
        "10"-only rule because for THEM the 12-form is the flag over a 10-form entity, while this
        arena's entity IS its flag (game_areas.tsv flag_equals_id=yes). gen_data's field pass matches
        `^m60_(\d\d)_(\d\d)$`, so the bare map was rejected and the boss granted NOTHING.

        Now it holds 29 members and five neighbours shed exactly those, the nearest-boss partition
        being disjoint -- 1048570800 41->30, 1050560800 39->28, 1049520800 17->14, 1050570850 8->6,
        1050570800 7->5, plus a same-size swap on the Fire Giant 1252520800. Every move is a check
        changing WHICH boss grants it, never whether.

        The decode is now guarded by a SECOND DERIVATION rather than a longer prefix allowlist: the
        decoded tile must be one an emevd actually exists for. Measured over the corpus, all 79 field
        bosses agree with the emevd file they are defined in, 0 disagreements, one entry changed.
        See test_gf_boss_sweeps.test_every_field_boss_tile_decodes (which also removes a `continue`
        in test_field_sweeps_are_local that had been excusing exactly this boss).

    +150 (2026-08-05, SPEC-broaden-sweeps PIECE B) 3056 -> 3206. Trigger count UNCHANGED at 226 and
        NOTHING left the corpus -- 150 checks entered it, and every one already had a known map.

        `_swept` admitted a minor-dungeon row only when its method was `flag_prefix`. But
        `global`/`global_filler` is a statement about an item's DISTRIBUTION -- region_map's own
        column reads `Global / Filler (scattered by design)` -- not about whether THIS pickup has a
        place. 127 of them sat on a minor-dungeon map that ALREADY hosted a boss with a working
        map-local sweep. Motivating case: Ruin-Strewn Precipice (m39_20), where Magma Wyrm Makar
        granted NONE of the 21 pickups you fight past on the way down.

        Where the 150 landed:
          dungeon 87 · catacomb 30 · cave 9  = 126 map-local, the intended target
          legacy  24                         = rows on a minor-dungeon map with NO boss on it, which
                                               fall through to the region divvy. A side effect of
                                               admitting them to _mem_region -- measured rather than
                                               assumed, and kept: they are region-correct and were
                                               granted by nobody before.

        No sweep-region flips; no trigger added or removed. m30_13's partition pool grows 10 -> 14
        (four Living Jar Shards around Auriza Side Tomb) and stays a 7/7 split.

        TWO were REFUSED, and this branch carries a filler cut the older ones do not because of them:
        a Sacred Tear at Ruin-Strewn Precipice (7774260, Church) and [Incantation] Knight's Lightning
        Spear at Scorpion River Catacombs (7774285, Legendary). The map path has never applied
        `_filler_only` -- test_gf_dungeon_sweep_rungs ratchets six pre-existing important members and
        says fixing that wholesale needs its own balance argument. This change does not touch those
        six; it just refuses to grow them.

        Scoped to _is_dungeon deliberately: legacy interiors are the same defect and worth ~280 more,
        but they need a map-local legacy pass that does not exist yet (piece C), and admitting them
        here would silently route them into the coarser region divvy instead.

    +270 (2026-08-05, SPEC-broaden-sweeps PIECE C) 3206 -> 3476. A legacy boss now sweeps its OWN
        MAP's filler before the region divvy sees the pool -- "this boss's building" instead of
        "1/Nth of the region". Shadow Keep 129, Leyndell 77, Mohgwyn 25 lead it. Nothing left the
        corpus, no check is granted twice, no sweep region flipped.

        THREE things this pass had to get right, each measured rather than assumed:

        * INTERIORS ONLY. `_class` calls the m61 DLC OVERWORLD "legacy", so an unfiltered
          legacy-map set pulls in m61_XX BANDS -- and a band spans several fine-regions, which is
          exactly why those bosses needed tile recovery for the divvy. 209 DLC checks walked in
          before this was scoped out. The overworld wants a neighbourhood (piece A), not a map.
        * GROUPED BY THE BOSS'S REGION, not the map's majority. A trigger carries ONE SWEEP_REGION
          and a legacy boss also holds a region slice, so filtering by map-majority could mis-region
          the trigger -- m10_00 is Stormveil 3 / Weeping 2 and m12_05 is Mohgwyn 25 / Liurnia 1.
        * `_filler_only`, which the dungeon map path has never applied. Without it this pass swept
          282 important-tagged checks the region divvy had always been filtering out. A new pass does
          not inherit an old pass's hole.

        THE CLAWBACK, and why Astel needs it. The map-local pass is deliberately greedy (a specific
        boss beats the region major, as the field/dungeon dedup has always done), so a region's
        leftover pool can empty. Astel's arena m12_04 is a bare boss room; every "Eternal Cities"
        check physically lives in m12_01 and m12_02, which now belong to the bosses standing in them.
        Astel went 33 -> 0 -- not losing a claim to anything of its own, losing a consolation slice
        of a pool that no longer exists. Dealing the remainder to the emptiest bosses first (also
        added here) rescued two Shadow Keep bosses 9 -> 1 but cannot help Astel: Ainsel River's
        remainder is genuinely EMPTY. So a starved region major claws back a share from the largest
        holder in its own region, re-dealt round-robin: Astel 26, its donor 27.

        m19_00 is EXEMPT BY MAP: Radagon and the Elden Beast are one fight on a map with no filler,
        and a convenience grant at the end of the run is not a convenience. Keyed on the MAP because
        the first cut exempted only 19000800 and 19000810 promptly clawed back instead -- an
        entity-keyed exemption on a two-head arena protects exactly half of it. Elden Beast 1 -> 0 is
        therefore the ONE trigger this change removes, deliberately.

    +225 (2026-08-05, SPEC-broaden-sweeps PIECE A -- the DLC overworld) 3476 -> 3701. NOTHING lost,
        no trigger removed, no sweep region flipped, and -- the thing this piece could have got
        wrong -- NO REGION SHRANK. The 28 m61 bosses hold 247 -> 476 members.

        They are classed `legacy` and STAY that way. A reclass to `field` was the obvious move and is
        a NET LOSS: they are their regions' divvy hosts, 268 members hang off them, and Gravesite,
        Ensis, Rauh Base, Cerulean and Jagged Peak have no other host at all. So the neighbourhood is
        ADDITIVE -- the field pass runs first, `_covered` takes what it claims out of the divvy pool,
        and the two never double-grant.

        Three things had to be true, and each was verified rather than assumed:

        * THE TILE. `DisplayBossHealthBar` carries only the coarse `m61_XX` BAND, so the field pass
          could never place these bosses. Their id encodes the real one (20XXYYLLLL, the DLC sibling
          of the base game's 10/12 forms) -- the same decode gen_data already trusted for the divvy
          (`_M61_BOSS_RE`), now recorded on the boss table and guarded by the same second derivation:
          all 28 land on a tile that HAS an m61 emevd, 28/28.
        * THE GRID. `_tile_xy` held a bare (x, y). m60 (44,45) and m61 (44,45) are different places
          on different continents, and comparing them yields a small, meaningless distance -- a DLC
          boss quietly claiming base-game checks. Every comparison is now grid-guarded (`_near`) and
          test_overworld_sweeps_never_mix_GRIDS states it independently.
        * THE ADMISSION. `_mem_tile` is fed from rows that passed `_swept`, and a `global_filler` on
          m61_46_46 passed none of its branches -- so the first cut of this pass ran over an EMPTY
          grid and claimed exactly 0 checks while looking perfectly healthy. A row that already names
          an overworld tile is now admitted on that basis.

        The +225 (vs ~217 predicted) is the m61 population plus a handful of m60-tiled rows the same
        admission rule legitimately picks up.

    -13 (2026-08-05, spell-vendor MERCHANT re-key, #391) 3701 -> 3688. NOTHING was removed from a
        sweep by geometry; 13 checks became INELIGIBLE for sweeps because they were finally tagged.

        `_FIELD_EXCLUDE_TAGS` holds the shop tags, and these 13 carried NO shop tag at all: the
        spell-vendor classifier was keyed on the ShopLineupParam 100-block, so a check whose block
        was spell-heavy was passed over entirely and never got `ShopNonSpell`. Untagged, they read
        as ordinary overworld filler and were being GRANTED BY KILLING A BOSS despite being merchant
        stock. Re-keying the classifier onto the talk ESD tags them, and the tag excludes them.

        Verified as exactly the tag-changed set, by set-difference rather than inferred from the
        total moving: 0 checks were ADDED to any sweep, 13 were removed, and (added | removed) is a
        subset of the checks whose LOCATION_TAGS changed in the same regen."""
    total = sum(len(v) for v in DUNGEON_SWEEPS.values())
    # 3057 -> 3056 (2026-08-04): ONE check left the corpus, and it left for a reason.
    # ap 7771252, "Siofra River :: Fingerslayer Blade", was a member of sweep trigger 12020830. It is
    # now MISSABLE (label `questline_item`: the item is handed to Ranni), and a missable check is not
    # sweep corpus. Verified as exactly one check, by set-difference against main -- not inferred
    # from the total moving by one.
    assert total == 3688, (
        "sweep corpus is %d, expected 3688. If a sweep was legitimately added or removed, say WHY "
        "here -- do not just re-baseline the number." % total)
