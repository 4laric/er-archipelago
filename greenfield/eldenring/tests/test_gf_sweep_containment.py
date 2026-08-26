"""THE INVARIANT: a boss sweep may only grant checks in the region the boss is FOUGHT in.

Alaric's ruling, 2026-08-26: *"there shouldn't be any cross-region boss sweeps in general"*.

WHY IT IS A DEFECT AND NOT A LABEL PROBLEM. A region lock buys a region. If a trigger fought in
region A pays members that present in region B, a player who bought A, killed the boss and was
shown those rows is being paid checks in a region they do not own -- and if they walk to one, the
kick guard ejects them from a play_region their seed never opened. That is #330's shape, and the
Hippo rule (#885, region_overrides.tsv f510440) is the same sentence said once about one boss.

THE TWO MOTIVATING CASES (CONTRIBUTING rule 11), both player-reported on 2026-08-26:

  * NovahDango: five `Abyssal ::` rows near the Church Ruins / Abyssal Woods (Clarifying Boluses,
    Frenzyflame Perfume Bottle, Scadutree Fragment, Shadow Realm Rune, Swollen Grape) read "also
    granted by Jori, Elder Inquisitor (m61_52_43)", and *"Jori's region is Midra's Manse territory,
    not Abyssal Woods"*. Our own tables agree with him: boss_area_regions.tsv puts Jori's arena in
    play_region 40020, and REGION_PLAY_IDS gives 40020 to Scadu Altus. So the LINK is what is
    wrong, and gen_data's containment pass CUTS it -- the members re-home to an Abyssal host and
    Jori, left holding nothing, is dropped like an SWEEP_UNSPAWNED trigger.

  * Lilith: `Belurat :: Message from Leda - near Scaduview Cross, also granted by Divine Beast
    Dancing Lion (m20_00)`, with *"this one is in Shadow Keep, not in Belurat"*. Here the REGION is
    what is wrong: the PlayArea item scan answers `volume:` bucket 69000 for f580600, so the check
    stands in Scadu Altus and was only filed Belurat because the Lion swept it. The fix is
    FLAG_REGION_OVERRIDE[580600] -- fixing the region, not cutting the link -- after which it rides
    a Scadu Altus host (Dryleaf Dane) and the Lion never reaches out of Belurat.

Two shapes, two different right answers, and this file pins BOTH so a later regen cannot quietly
swap one for the other.

🛑 UNAUDITED IS NOT CLEAN. A trigger with no arena region from any of gen_data's four sources says
nothing here, and the count of those is asserted rather than ignored: it may not grow silently.
"""
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

JORI = 2052430800
JORI_ARENA = "Scadu Altus"
JORI_MEMBER_REGION = "Abyssal"
LEDA_FLAG = 580600
LEDA_REGION = "Scadu Altus"
DANCING_LION = 20000800
BELURAT = "Belurat"

# The arena/members split was 4 groups / 22 member links before the ruling. Three of the four were
# the ARENA attribution being stale against a ruling the CHECKS already followed (Divine Tower of
# Limgrave -> Stormveil; the two Ashen Capital finale triggers), and are curated in
# _ARENA_REGION_CURATED rather than cut. Only Jori's was a real cross-region grant.
UNAUDITED_CEILING = 26


def _sweeps():
    from .. import boss_sweeps
    return boss_sweeps


def _present_region():
    from .. import data
    return {ap: region for region, rows in data.LOCATIONS.items() for (_n, ap, _f) in rows}


class NoSweepGrantsOutsideItsArenaRegion(unittest.TestCase):
    def test_every_audited_trigger_is_contained(self):
        bs = _sweeps()
        where = _present_region()
        bad = []
        for trigger, arena in bs.SWEEP_ARENA_REGION.items():
            for ap in bs.DUNGEON_SWEEPS.get(trigger, ()):
                got = where.get(ap)
                if got is not None and got != arena:
                    bad.append((trigger, arena, got, ap))
        self.assertEqual(
            bad, [],
            "cross-region sweep grant(s) (trigger, arena region, member region, ap): %r. A sweep "
            "may only grant checks in the region it is fought in (Alaric 2026-08-26). Either the "
            "arena attribution is wrong -- curate it in gen_data._ARENA_REGION_CURATED citing the "
            "ruling -- or the CHECK's region is wrong (FLAG_REGION_OVERRIDE). Do not widen this "
            "test." % (bad,))

    def test_sweep_region_is_the_arena_region(self):
        """SWEEP_REGION is the region the kill PAYS IN; containment makes it the arena's."""
        bs = _sweeps()
        split = {t: (bs.SWEEP_REGION.get(t), a) for t, a in bs.SWEEP_ARENA_REGION.items()
                 if bs.SWEEP_REGION.get(t) != a}
        self.assertEqual(split, {}, "SWEEP_REGION disagrees with SWEEP_ARENA_REGION for %r" % (split,))

    def test_unaudited_triggers_do_not_grow_silently(self):
        """An absent arena region is UNMEASURED, not clean (#445). This invariant says nothing
        about those triggers, so their number is the size of what it cannot see."""
        bs = _sweeps()
        unaudited = sorted(set(bs.DUNGEON_SWEEPS) - set(bs.SWEEP_ARENA_REGION))
        self.assertLessEqual(
            len(unaudited), UNAUDITED_CEILING,
            "%d trigger(s) have no arena region (was %d). The containment invariant is blind to "
            "every one of them; measure them (boss_area_regions.tsv / boss_arena_rulings.tsv) "
            "rather than raising this ceiling: %r"
            % (len(unaudited), UNAUDITED_CEILING, unaudited))


class TheJoriLinkIsCut(unittest.TestCase):
    """NovahDango's case: the LINK was wrong, so the link was cut."""

    def test_jori_grants_no_abyssal_check(self):
        bs = _sweeps()
        where = _present_region()
        members = bs.DUNGEON_SWEEPS.get(JORI, ())
        strays = [ap for ap in members if where.get(ap) == JORI_MEMBER_REGION]
        self.assertEqual(
            strays, [],
            "Jori, Elder Inquisitor (%d) is fought in %s (boss_area_regions.tsv play_region 40020) "
            "and must not grant %s checks -- NovahDango, 2026-08-26. Got %r"
            % (JORI, JORI_ARENA, JORI_MEMBER_REGION, strays))

    def test_the_cut_members_did_not_vanish_from_the_sweep_corpus(self):
        """A narrowing must be diffed, not trusted: the Abyssal rows NovahDango named are still
        swept, by a host in their OWN region."""
        bs = _sweeps()
        where = _present_region()
        abyssal_swept = {ap for t, mem in bs.DUNGEON_SWEEPS.items() for ap in mem
                         if where.get(ap) == JORI_MEMBER_REGION}
        self.assertTrue(
            abyssal_swept,
            "containment emptied %s of every sweep grant -- the Astel clawback shape. A region's "
            "pool may not silently empty." % JORI_MEMBER_REGION)
        for t, mem in bs.DUNGEON_SWEEPS.items():
            if any(where.get(ap) == JORI_MEMBER_REGION for ap in mem):
                self.assertEqual(
                    bs.SWEEP_ARENA_REGION.get(t, JORI_MEMBER_REGION), JORI_MEMBER_REGION,
                    "trigger %d re-homed %s members but is not fought there" % (t, JORI_MEMBER_REGION))


class TheLedaCheckMovedInsteadOfLosingItsLink(unittest.TestCase):
    """Lilith's case: the REGION was wrong, so the region was fixed."""

    def test_message_from_leda_is_no_longer_belurat(self):
        from .. import data
        found = {region for region, rows in data.LOCATIONS.items()
                 for (_n, _ap, flag) in rows if flag == LEDA_FLAG}
        self.assertEqual(
            found, {LEDA_REGION},
            'f%d "Message from Leda" stands at Scaduview Cross, not in Belurat (Lilith 2026-08-26; '
            "PlayArea scan volume: bucket 69000). Got %r" % (LEDA_FLAG, sorted(found)))

    def test_the_dancing_lion_no_longer_sweeps_it(self):
        bs = _sweeps()
        from .. import data
        ap = next((a for rows in data.LOCATIONS.values() for (_n, a, f) in rows if f == LEDA_FLAG),
                  None)
        self.assertIsNotNone(ap, "f%d is not a check any more" % LEDA_FLAG)
        self.assertNotIn(
            ap, bs.DUNGEON_SWEEPS.get(DANCING_LION, ()),
            "the Divine Beast Dancing Lion is fought in %s and must not reach a %s check"
            % (BELURAT, LEDA_REGION))

    def test_it_is_still_swept_by_a_scadu_altus_host(self):
        """Preferring the region fix over the cut is only better if the check keeps a route."""
        bs = _sweeps()
        from .. import data
        ap = next((a for rows in data.LOCATIONS.values() for (_n, a, f) in rows if f == LEDA_FLAG),
                  None)
        hosts = [t for t, mem in bs.DUNGEON_SWEEPS.items() if ap in mem]
        self.assertTrue(hosts, "f%d lost every sweep host" % LEDA_FLAG)
        for t in hosts:
            self.assertEqual(bs.SWEEP_REGION.get(t), LEDA_REGION,
                             "trigger %d pays in %r, not %r" % (t, bs.SWEEP_REGION.get(t), LEDA_REGION))


if __name__ == "__main__":
    unittest.main()
