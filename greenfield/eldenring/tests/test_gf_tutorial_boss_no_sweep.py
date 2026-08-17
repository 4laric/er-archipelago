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
import hashlib

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
    """The general form: a sweep may only be paid by a boss that lives where the checks live.

    m34_10 is the deliberate exception: its Divine Tower runtime bucket is Stormveil even though
    its grace geography is Limgrave (#202, Alaric ruling 2026-08-17). m10_01 remains the bad fold
    this test was created to catch.
    """
    from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS
    wrong = []
    for flag, region in SWEEP_REGION.items():
        if region != "Stormveil":
            continue
        info = BOSS_HEALTHBARS.get(flag)
        if info and info[0] not in ("m10_00", "m34_10"):
            wrong.append((flag, info[0], info[3]))
    assert not wrong, (
        "a Stormveil sweep is keyed outside Stormveil's approved m10_00/m34_10 maps: %s. m10_01 "
        "is the intro map and rides Stormveil's bucket; it is not IN Stormveil." % wrong)


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

    -13 (2026-08-05, spell-vendor MERCHANT re-key) 3701 -> 3688. NOTHING was removed from a sweep by
        geometry; 13 checks became INELIGIBLE for sweeps because they were finally tagged.

        `_FIELD_EXCLUDE_TAGS` holds the shop tags, and these 13 carried NO shop tag at all: the
        spell-vendor classifier was keyed on the ShopLineupParam 100-block, so a check whose block
        was spell-heavy was passed over entirely and never got `ShopNonSpell`. Untagged, they read
        as ordinary overworld filler and were being GRANTED BY KILLING A BOSS despite being merchant
        stock. Re-keying the classifier onto the talk ESD tags them, and the tag excludes them.

        Verified as exactly the tag-changed set, by set-difference rather than inferred from the
        total moving: 0 checks were ADDED to any sweep, 13 were removed, and (added | removed) is a
        subset of the checks whose LOCATION_TAGS changed in the same regen.

    +3 (2026-08-07, #249 de-dup re-key) 3688 -> 3691. The corpus GREW, and nothing was removed.

    -6 (2026-08-08, the Shop umbrella fix) 3691 -> 3685. SIX MEMBERS LEFT ONE SWEEP AND NOTHING
        ELSE MOVED -- diffed by (trigger, flag) against main, 6 removed, 0 added, 0 re-owned. All six
        came off dungeon trigger 1034500800, and all six are PRECEPTOR SELUVIS'S SORCERY SHOP ROWS:

          7770266 Glintstone Cometshard   7770269 Swift Glintstone Shard
          7770267 Star Shower             7770270 Glintblade Phalanx
          7770268 Great Glintstone Shard  7770271 Carian Slicer

        Felling a Liurnia catacomb boss was auto-granting six of Seluvis's shop slots. Shop classes
        are in gen_data._FIELD_EXCLUDE_TAGS precisely so merchant stock is never sweep filler, and
        the exclusion was reading the `Shop` TAG -- which came from the region_map `method` column,
        while ShopNonSpell/ShopSlot came from the stock FLAG. These six sit in the 35-row gap between
        those two predicates, so the exclusion could not see them. One predicate now
        (gen_data._is_shop_row), and the sweeps lose stock they should never have held. No check left
        the sweep corpus for any other reason, and all six remain normal shop checks.

        The #249 regen re-keyed the unplaced-global de-dup off the ITEM NAME, which recovered 16
        locations that the old key had been silently dropping. Three of those 16 sit in
        sweep-eligible dungeon geometry and are therefore sweep corpus by the same rule as their
        neighbours -- no rule changed, the input did:

            Raya Lucaria Academy :: Starlight Shards - around Church of the Cuckoo [f400103]
            Shadow Keep :: Furnace Visage - around Storehouse, First Floor  [f400612]
            Stormveil :: Erdsteel Dagger - around Castleward Tunnel         [f400221]

    -8 (2026-08-08, the SECOND boss reward mechanism) 3685 -> 3677. Diffed by (trigger, flag) as
        this file demands: **8 LOST, 0 GAINED, 60 RE-OWNED, and ZERO of the re-owned crossed a sweep
        REGION** -- so the churn is pacing, not reachability (#445's shape is absent).

        The 8 that left are the point of the change, not a cost of it. Each is now `Boss`-tagged
        because `Boss` began reading the scripted-reward mechanism (BOSS_REWARD_DEFEAT) as well as
        the handler-drop one, and gen_data's `_filler_only` cut keeps premium classes out of the
        legacy sweep pool. They are boss drops, so a filler sweep should never have been handing them
        out:

          7770027 Talisman Pouch (Divine Tower of Caelid)   7770787 Assassin's Cerulean Dagger
          7770757 Gargoyle's Greatsword (Underground Road)  7770788 Viridian Amber Medallion
          7770783 Noble Sorcerer Ashes (Elden Throne)       7770791 Death Knight's Twin Axes
          7770784 Assassin's Crimson Dagger                7770785 Banished Knight Engvall

        The 60 re-owned are the multi-boss divvy re-phasing on its stable modulus -- adding members
        to a map's pool shifts the phase for everything after them (#363). Every one stayed with a
        boss in the same region.

        🛑🛑 VERIFIED BY NAME, NOT BY AP ID, AND THE DIFFERENCE IS THE WHOLE POINT. The same regen
        RENUMBERED the ap id space, so an id-level set-difference reads 615 members added and 612
        removed -- 1227 lines of pure noise that hide the three real ones. Keyed on the LOCATION
        NAME it is exactly +3 / -0. An id that resolves is not a match; when a regen can move the
        id space, only a structural key answers "what actually changed"."""
    total = sum(len(v) for v in DUNGEON_SWEEPS.values())
    # 3057 -> 3056 (2026-08-04): ONE check left the corpus, and it left for a reason.
    # ap 7771252, "Siofra River :: Fingerslayer Blade", was a member of sweep trigger 12020830. It is
    # now MISSABLE (label `questline_item`: the item is handed to Ranni), and a missable check is not
    # sweep corpus. Verified as exactly one check, by set-difference against main -- not inferred
    # from the total moving by one.
    # 🛑 THE TOTAL CANNOT SEE A PERMUTATION -- see test_the_sweep_OWNERSHIP_did_not_churn below.
    #
    # +49 (2026-08-09, #495 -- a bossless map's checks reach their region's remainder pool) 3677 ->
    # 3726. `_LEGACY_SWEEP_MAPS` is the set of maps that HOST a legacy boss, and the membership gate
    # reused it to decide which checks MAY BE swept -- so m21_02 (West Rampart), which hosts no
    # healthbar boss, was excluded from Shadow Keep's remainder pool BECAUSE it has no owner, when
    # having no owner is that pool's whole qualification. Shadow Keep's remainder was 5 against 271
    # locations; Commander Gaius, who owns a tile and no building, paid ONE check (bobler, 2026-08-09).
    # Diffed by (trigger, flag), never by ap id: ADDED 52, REMOVED 3, RE-OWNED 3, net +49.
    # Added by region: Shadow Keep 39, Siofra River 13. All three REMOVED are the same three that were
    # RE-OWNED -- 21027050, 21027230, 21027250 moved between Shadow Keep triggers as the divvy modulus
    # re-phased around a larger pool, exactly the #363 effect. SWEEP_REGION is 'Shadow Keep' on both
    # sides for all three, so that is a pacing change and not a reachability one.
    # The same +3 regen ALSO moved 133 existing members to a different boss.
    # +6 (2026-08-09, TILE_ROW_REGION -- a graceless tile regioned by PlayRegionParam's own row)
    # 3726 -> 3732. NOT a sweep change: 219 triggers before and after, and no check was created or
    # destroyed. Twenty-two checks moved region, and the swept SHARE of a region is a function of its
    # check count and its trigger count, so moving seven checks out of Cerulean and into Charo's
    # (50 -> 43 checks / 3 -> 2 triggers, and 20 -> 27 / 1 -> 2) lets the round-robin remainder reach
    # six checks in Charo's it could not reach before. ADDED 6, REMOVED 0, all six in Charo's --
    # diffed by (trigger, flag) against main, not inferred from the total.
    # The Gravesite -> Rauh Base thirteen did NOT churn: their trigger (2046450800) changed region
    # with them, so they keep the same owner and the group stops being one of #445's six.
    # -1 (2026-08-11, #556 -- m10_00 curated into DUNGEON_REGION_OVERRIDE) 3732 -> 3731.
    # ONE member left: ap 7773843, "Stormveil :: Gostoc's Bell Bearing - near Gateside Chamber"
    # (f400051). ADDED 0, REMOVED 1, RE-OWNED 3, and all three re-owned stayed inside Stormveil.
    # 🛑 IT IS NOT A REGION MOVE -- the check reads Stormveil before and after. It is region_of's
    # SIDE EFFECT going away. f400051 is MSB-placed in m10_00, so with m10_00 now resolvable the
    # MSB-ground-truth branch answers it and returns; previously that branch failed, the row fell
    # through to the global-recovery branch, and THAT branch sets `r['map'] = _im` as a side effect
    # of answering. The sweep pools are keyed on the map column, so the check was only ever
    # sweep-eligible because a worse branch had answered it. Getting the region right took the map
    # away. The check is unaffected as a check: it exists, it is in Stormveil, and it is obtainable
    # by physical pickup -- a sweep is a convenience auto-grant, not the only source.
    # ▶️ FILED SEPARATELY, NOT FIXED HERE. Recording the map in the MSB branch as well restores this
    # member AND adds 49 more (3732 -> 3782, 34 re-owned) -- a 50-check sweep change has no business
    # riding inside a merchant-region fix, so it is its own issue with its own diff.
    # +145 (2026-08-13 -- the per-seed surface cut) 3731 -> 3876. gen_data's cut stopped being the
    # whole 16-class SURFACE_CLASSES vocabulary and became the FLOOR only (_SWEEP_NEVER_TAGS);
    # Seedtree/Church/Fragment/Revered/Basin/Legendary are admitted into the bake and cut per seed
    # by features/boss_locks.sweep_surface_cut against that seed's Progression Surface. ADDED 145,
    # REMOVED 0, triggers 218 before and after: Legendary 47, Seedtree 38, Fragment 22, Revered 21,
    # Church 13, Basin 4, over all 29 regions. Every one carries exactly ONE tag -- no combos --
    # because a check that also carried a floor tag was, and stays, excluded.
    # 🛑 THIS NUMBER IS THE BAKE, NOT WHAT A SEED GRANTS. A default-surface seed sees 3876 - 94 =
    # 3782 (Church/Seedtree/Fragment/Revered are in contract.SURFACE_DEFAULT_CLASSES); an
    # empty-surface seed sees all 3876. The per-seed arithmetic is asserted in
    # test_gf_dungeon_sweep_rungs, on the output of enabled_sweeps, which is where it is observable.
    # +169 (2026-08-13, #191) 3876 -> 4045. WHY, as this gate demands: co-check SIBLINGS now
    # inherit their primary's sweep membership. The member loop walks `rows` POSITIONALLY
    # (`_ap = BASE_AP + _i`), so a registry ap_id in the COCHECK band was structurally invisible to
    # it and NO co-check had ever been swept -- including the original five. A sibling is the same
    # physical acquisition as its primary: if killing the boss sweeps the primary, the player has
    # already picked the sibling off the same corpse, so leaving it out marked a check that is
    # provably in hand as unfound. gen_data MIRRORS the primary's membership rather than re-deriving
    # it, so a sibling cannot be swept into a region its primary was not (the #445/#598 class), and
    # the map-region vote is deliberately NOT re-cast -- one physical pickup votes once.
    # Alaric's ruling, 2026-08-13: all co-checks are swept with their primary.
    # -1 (2026-08-16, #737) 4045 -> 4044. WHY: flag 60510, `Talisman Pouch`, stopped being SWEPT
    # FILLER and became the check Margit's death GRANTS. It had no boss attribution at all until now
    # -- datamine_boss_reward_lots discarded its row as "reward flag flipped by 2 maps", because
    # Morgott's defeat event back-fills the same reward flag behind `if (!EventFlag(9100))` (Margit
    # and Morgott are one character, so killing Morgott implies Margit). With the back-fill
    # distinguished from an ownership claim, the check resolves to Margit's own trigger 10000850 --
    # and a boss's REWARD cannot also be one of the members its own defeat sweeps, so it leaves the
    # corpus. Exactly one check, and it is the one the fix was about. The reshuffle between
    # 10000800 and 10000850 in the same regen is the m10_00 pair re-partitioning 111 members instead
    # of 112 (the DIVVIED path), not membership crossing a region boundary.
    # -10 (2026-08-17, #653): 4044 -> 4034. All ten removals are the Carian Study Hall inverted
    # layout: flags 34117100/110/120, 34117400/401/402/403, 34117500 (two co-checks), and 34117710.
    # Trigger 34110800 is reachable on the ordinary layout, before the Carian Inverted Statue changes
    # the map, so sweeping those checks from it bypassed the new key gate. The five ordinary-layout
    # checks stay on that trigger. ADDED 0, RE-OWNED 0; physical pickup remains their only award path.
    # -1 (2026-08-17, #664): 4034 -> 4033. REMOVED only: flag 2053467600 / ap 7773806 is the
    # Finger Ruins of Rhia bell reward, gated by the Hole-Laden Necklace. It shared the Scadu Altus
    # legacy pool with Rakshasa (trigger 2051440800), an unrelated fight reachable without the
    # necklace. The check stays obtainable at the bell; only the gate-bypassing convenience award
    # is gone. ADDED 0, RE-OWNED 0.
    # -1 (2026-08-17, #665): 4033 -> 4032. Retagging BOTH bell interactions as KeyItem generalises
    # #664's Rhia exclusion and also removes Dheo (flag 2050407000) from Bayle's filler sweep. The
    # two removals are now the same policy: a necklace-gated quest action is not filler an unrelated
    # boss may grant. Rhia was already absent, so this stack removes only Dheo. ADDED 0, RE-OWNED 0.
    assert total == 4032, (
        "sweep corpus is %d, expected 4032. If a sweep was legitimately added or removed, say WHY "
        "here -- do not just re-baseline the number." % total)


def _sweep_digest():
    """A stable fingerprint of WHICH BOSS OWNS WHICH CHECK -- keyed on the acquisition FLAG.

    🛑 NEVER on the ap id. Positional ap ids renumber whenever a location is added or removed
    earlier in the table, so an ap-keyed digest would fire on every unrelated change and be switched
    off inside a month. The flag is the invariant."""
    from worlds.eldenring.data import LOCATIONS
    flag_of = {ap: fl for _r, v in LOCATIONS.items() for (_n, ap, fl) in v}
    pairs = sorted((int(trig), int(flag_of[m])) for trig, ms in DUNGEON_SWEEPS.items()
                   for m in ms if m in flag_of)
    return hashlib.sha256(repr(pairs).encode()).hexdigest()[:16], len(pairs)


def test_the_sweep_OWNERSHIP_did_not_churn():
    """The companion to the total above, and the reason it needs one.

    2026-08-07: the corpus total moved 3688 -> 3691 while **133 members changed which boss grants
    them** -- 21010800 <-> 21010801 swapping 16 and 15 (the two Shadow Keep bosses trading half their
    lists), plus overworld 3-cycles 1042550800 -> 1043530800 -> 1041530800, four members each. The
    multi-boss divvy's PHASE depends on the member list's length, so inserting members re-phases
    everything after them (#363's stable-modulus problem). Bumping the total went green through all
    of it; the churn was found only because someone diffed by hand.

    That churn was ACCEPTED on a measurement, not a shrug: of the 133, **ZERO crossed a region
    boundary**. Every one stayed with a boss in the same region, so no check moved somewhere a
    player might not have access to -- the softlock-shaped risk (#445) is not present.

    2026-08-08 (the Shop umbrella fix): digest a50f6de2 -> a8d14d12, n 3691 -> 3685. Six REMOVED,
    zero added, zero RE-OWNED -- the cleanest shape this diff can have. All six are Preceptor
    Seluvis shop rows leaving dungeon trigger 1034500800; see the sibling test's docstring for why
    they were ever in it. No re-phasing followed, because removing the TAIL of one member list
    cannot shift a modulus that no other sweep shares.

    2026-08-08 (phase-2 heads are not defeat flags, #481): digest a8d14d12 -> 3a3b9d44, n 3685 ->
    3685. **408 RE-OWNED, zero net added, zero net removed, and ZERO crossed a region boundary** --
    the safe shape this docstring asks for. Six triggers were dropped (12020801, 13000801, 14000801,
    16000801, 20010801, 21010801: the second health-bar head of a fight whose flag sets when that
    bar appears, not when the boss dies), so their members return to the fight's own primary and the
    per-map divvy re-phases around them. The re-phase is why 24 triggers appear in the removed set
    and 19 in the added set for a change that drops six: the modulus moved, exactly as #363 warned.
    Two neighbours (12080800, 12090800) gained one member each for the same reason.

    2026-08-08 (the second boss reward mechanism, STACKED ON #481): n 3685 -> 3677. 8 removed, 0 added, **60
    RE-OWNED with zero region crossings** -- the largest re-ownership churn this pin has recorded,
    and it is benign for the reason the 2026-08-07 entry established: the divvy's phase depends on
    member-list length, so growing a map's pool re-phases the rest. Checked the way this docstring
    says to, per-check on both sides of SWEEP_REGION. The digest is re-derived on THIS base rather
    than carried over from the pre-#481 measurement -- two ownership changes compose, and a digest
    copied across a rebase would be a number nobody measured.


    2026-08-09 (#495, the bossless-map remainder pool): n 3677 -> 3726. ADDED 52, REMOVED 3,
    RE-OWNED 3. The three removed ARE the three re-owned -- 21027050, 21027230, 21027250 changed
    trigger as the Shadow Keep divvy modulus re-phased around a pool that grew from 5 to 41. Checked
    the way this docstring says to: SWEEP_REGION is 'Shadow Keep' for both the old and the new owner
    of all three, so they stayed inside their region. Added by region: Shadow Keep 39, Siofra River
    13.

    2026-08-09 (TILE_ROW_REGION, the graceless-tile regioning fix): n 3726 -> 3732. ADDED 6,
    REMOVED 0, RE-OWNED 53 -- and ZERO of the 53 changed the REGION of their sweep, checked the way
    this docstring says to, per-check on both sides of SWEEP_REGION. The re-ownership is the divvy
    re-phasing again: two regions changed size (Cerulean 50 -> 43 checks, Charo's 20 -> 27; Gravesite
    161 -> 152 members, Rauh Base 67 -> 76), so the modulus moved under the members that stayed. All
    six ADDED are in Charo's, which gained a second trigger along with the checks. The thirteen
    Gravesite -> Rauh Base checks appear in NONE of the three sets: their trigger 2046450800 moved
    region with them, so nothing was re-owned -- which is the same fact as #445 losing one of its six
    mismatched groups.

    WHEN THIS FAILS: diff DUNGEON_SWEEPS by (trigger, flag) across the regen and record ADDED,
    REMOVED and RE-OWNED separately. For the re-owned, check SWEEP_REGION on both sides: staying
    inside one region is a pacing change, leaving it is a reachability bug.

    2026-08-10 (#528, the Cerulean merge): digest 1652af0d -> b680bd65, n 3732 -> 3732. ADDED 0,
    REMOVED 0, **12 RE-OWNED**. A pure permutation -- exactly what this gate exists for, since the
    total cannot see one -- and I DID NOT UPDATE THIS PIN, so main ran red from that merge until
    now. Cause: Charo's and Stone Coffin folded into Cerulean, and sweep members are filtered to
    their sweep's region, so a check whose region moves re-homes to a boss in the new region.
    Dancer of Ranah -> Death Rite Bird 7, Ghostflame Dragon -> Death Rite Bird 3, and 2 back.
    All 12 stayed INSIDE their region pair, so this is the pacing shape, not the reachability one.

    2026-08-10 (#532, the boss-region verdicts): digest b680bd65 -> bd5147a4, n 3732 -> 3732.
    ADDED 0, REMOVED 0, **172 RE-OWNED**. Same mechanism, larger input: six in-game rulings moved
    68 checks across 14 tiles into another region (Tree Sentinel -> Shadow Keep, Dancing Lion ->
    Ancient Ruins, plus Jagged Peak Drake, Godefroy, Jori, Marigga) and each took its sweep
    membership with it. Romina -> Dancing Lion 30, Dancing Lion -> Rugalea 13, Ralva -> Tree
    Sentinel 12. NOTHING entered or left the swept corpus -- only who grants what changed, which
    is the shape this digest was added to make visible.

    2026-08-10 (#532 again, the straddle resolution): digest bd5147a4 -> 0f647980, n 3732 -> 3732.
    The verdicts split nine graces at region boundaries (53 -> 59 straddles, pin 55), so the nine
    were resolved to their MAJORITY side -- 20 checks, see issue #534 -- which moved ownership a
    third time. Straddles land at 51 and minority at 4.23%, both under the limits and better than
    main. Still ADDED 0 / REMOVED 0: every movement today has been a permutation.

    2026-08-10 (#540, the unspawned Fallingstar Beast): digest 0f647980 -> ebbf592b, n 3732 ->
    3732. **ADDED 0, REMOVED 0, 23 RE-OWNED, ZERO region crossings** -- the pacing shape, again,
    and this time by construction. Trigger 1038540800 ("Fallingstar Beast", m60_38_54, Mt. Gelmir)
    is EMEVD-only: a complete boss script for a character the MSB never places, so its defeat flag
    can never be set and its 23 members -- 10.4% of Mt. Gelmir's 222 checks -- hung off a trigger
    that cannot fire. Alaric warped to First Mt. Gelmir Campsite (grace 76351) on 2026-08-10 and
    there is no beast. Dropping the trigger hands its tile's filler back to the FIELD NEIGHBOURHOOD
    pass, which re-homed all 23 inside Mt. Gelmir: 12 to 1037540810 (Ulcerated Tree Spirit,
    m60_37_54) and 11 to 1037530800 (Demi-Human Queen Maggie, m60_37_53). Trigger count 219 -> 218.
    Checked the way this docstring says to, per-check on both sides of SWEEP_REGION: all 23 read
    'Mt. Gelmir' before and after.

    2026-08-11 (#556, m10_00 -> Stormveil): digest ebbf592b -> 7ed70eb4, n 3732 -> 3731. ADDED 0,
    REMOVED 1, **3 RE-OWNED, ZERO region crossings**. The removal is explained in full on the total
    above (region_of's map side effect, not a region move). The three re-owned are the pacing shape
    and nothing else: 7771014 and 7773854 went 10000800 -> 10000850 and 7774041 went the other way,
    all six endpoints SWEEP_REGION 'Stormveil'. Both triggers are Stormveil majors on m10_00, so
    losing one member from a 111-check pool re-phased the two-way round-robin by one -- the #363
    stable-modulus effect this docstring already records twice, at its smallest possible size.

    2026-08-13 (#191, co-check siblings inherit their primary's sweep): digest 3c4273a8 -> 328ce8d0,
    n 3876 -> 4045. **ADDED only**, +169, and every addition is a COCHECK-band ap_id sitting in the
    same (trigger, flag) group as its primary -- no existing member changed owner. That is the shape
    to verify if this moves again: a mirror can only add beside a primary, so an addition anywhere
    else, or any REMOVAL, is a different bug wearing this number.

    2026-08-13 (the per-seed surface cut): digest 7ed70eb4 -> 3c4273a8, n 3731 -> 3876. **ADDED
    145, REMOVED 0, 774 RE-OWNED, ZERO region crossings.** By far the largest re-ownership this pin
    has recorded, and it is entirely the stable-modulus effect at full size: the region divvy deals
    a region's pool round-robin over `_ents[_j % len(_ents)]`, so inserting even one member near the
    head of a sorted pool re-phases every member after it. Siofra River 128, Haligtree 106,
    Leyndell 97, Farum Azula 87. Checked the way this docstring says to, per-check on both sides of
    SWEEP_REGION: all 774 read the same region before and after, so not one check changed hands
    across a region boundary -- the pacing moved, the geography did not.
    🛑 A churn this size is exactly when to distrust the total: 145 added and 3876 - 3731 = 145 agree
    only because REMOVED is 0, and the digest is what proves that rather than 900 in and 755 out.

    2026-08-13 (76916 Castle Watering Hole reversed to Scadu Altus, #645): digest 328ce8d0 ->
    d049e865, n 4045 -> 4045. **ADDED 0, REMOVED 0, 59 RE-OWNED -- and 24 of them DID cross a region
    boundary.**

    🛑 THE FIRST ENTRY HERE WITH REGION CROSSINGS, and they are the change rather than a side effect:
    the 24 are exactly the Castle Watering Hole checks moving Shadow Keep -> Scadu Altus, which is
    what #645 is. Every previous paragraph could say "zero crossings" because it was re-phasing;
    this one cannot, and saying so is the point of the pin. The check to make when it moves again is
    unchanged -- ask WHICH checks crossed and whether their crossing was the intent.

    The other 35 are ordinary re-phasing on both sides of the move (30 now in Scadu Altus, 29 in
    Shadow Keep): taking 24 members out of one region's round-robin pool and putting them in
    another re-phases `_ents[_j % len(_ents)]` for both, the same stable-modulus effect as the
    paragraph above. Zero added and zero removed is what proves it is a permutation and not a
    silent 24-in/24-out."""
    digest, n = _sweep_digest()
    # 2026-08-14: d049e865 -> 28f04fe4, count UNCHANGED at 4045. Pure membership movement, and it is
    # the #680 fix: flag 66930 (Hefty Cracked Pot, lot m41_01 Bonny Gaol) moved Limgrave -> Scadu
    # Altus, so one member left Limgrave's sweep and joined Scadu Altus's. A churn with the SAME
    # total is exactly what a one-check re-region looks like; a real regression would move the count.
    # 2026-08-16 (#737): 28f04fe4 -> 03b7fb99, count 4045 -> 4044. The count moving is the tell that
    # this one is NOT a permutation, and it should not be: flag 60510 LEFT the corpus because it
    # became Margit's reward instead of his filler (see the +/- note in the corpus test above). The
    # rest of the digest change is m10_00's two triggers re-partitioning 111 members where they had
    # 112 -- the DIVVIED path re-phases both sides whenever the pool size moves.
    # 2026-08-17 (#653): 03b7fb99 -> 1755ba16, count 4044 -> 4034. REMOVED only: the ten
    # Carian-Inverted-Statue checks named in the corpus ratchet above left ordinary-layout trigger
    # 34110800. No member was added or re-owned, so this is the narrow gate-bypass correction.
    # 2026-08-17 (#664): 1755ba16 -> 1f01b69f, 4034 -> 4033. REMOVED only: Rhia bell reward
    # 2053467600 left Rakshasa's sweep. No member was added or re-owned.
    # 2026-08-17 (#665): 1f01b69f -> 79ccf39c, 4033 -> 4032. REMOVED only: Dheo bell reward
    # 2050407000 left Bayle's sweep when both bell interactions became KeyItem checks.
    assert (digest, n) == ("79ccf39c8e3be6aa", 4032), (
        "sweep OWNERSHIP changed: (%s, %d), expected (79ccf39c8e3be6aa, 4032). The total alone will "
        "not tell you what moved -- diff by (trigger, flag), never by ap id." % (digest, n))
