"""#1059's acceptance test: a sweep trigger may only grant checks in the region it is FOUGHT in.

THE RULING (Alaric, 2026-08-26): *"there shouldn't be any [Abyssal checks sweeping on Jori], or
cross-region boss sweeps in general."*

THE MOTIVATING CASES, both from players on Discord 2026-08-26:
  * NovahDango screenshotted five `Abyssal :: ...` checks -- Clarifying Boluses, Frenzyflame
    Perfume Bottle, Scadutree Fragment, Shadow Realm Rune [7], Swollen Grape -- each reading
    "also granted by Jori, Elder Inquisitor". Jori is fought in SCADU ALTUS: PlayRegionParam puts
    his arena in bucket 40020 (boss_area_regions.tsv) and Alaric walked it in game on 2026-08-10
    (boss_verdict_tiles.tsv). So an Abyssal Lock alone could never reach the kill, and a seed
    holding both regions paid the grant out anyway.
  * Lilith reported `Belurat :: Message from Leda - near Scaduview Cross, also granted by Divine
    Beast Dancing Lion (m20_00) [f580600]`. That one is NOT a containment violation and this file
    says so below: m20_00 IS Belurat, so the sweep is contained. Her real complaint -- that the
    check stands in Shadow Keep -- is the disjunct-multisite family (#320/#502): f580600 has
    fourteen placements across m20_00, m21_01 and m22_00, and no single region answer. Out of
    scope here, deliberately.

WHY THE INVARIANT IS STATED AGAINST THE **ARENA** REGION.
tools/datamine_check_nearest_boss.py already measured "checks whose OWN region != their sweep
boss's SWEEP_REGION: 0" -- and its own docstring explains the zero: SWEEP_REGION is DERIVED from
the members, so it cannot disagree with them. A guard its subject cannot witness is not a guard.
SWEEP_ARENA_REGION is independent evidence (PlayRegionParam's answer to where the player stands),
and the 2026-08-26 audit found 22 real cross-region member links against it.

WHAT THE FIX WAS. Not a member filter -- a re-HOST. A legacy boss's host region now ranks
BOSS_AREA_REGION (measured) above `_m61_boss_region` (the nearest-neighbour tile decode that also
regions the checks, i.e. the circular source). Jori became a Scadu Altus host and his five Abyssal
checks fell back into the Abyssal divvy, where Midra, Lord of Frenzied Flame picked them up. A
late member filter would have stripped them AFTER the divvy was dealt and left them unswept: the
member-link total is the measure, and it did not move (4101 before and after).
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
IN_REPO = REPO is not None

JORI = 2052430800
JORI_ARENA_REGION = "Scadu Altus"
# The five NovahDango reported, by ap id, with the region they live in and the boss that must
# grant them now. Midra is Abyssal's own major (m28_00, inside the region).
# 2026-08-26 (#1013, Enia vanilla): the ap ids below moved because Enia's hundred hub rows
# left the corpus, which renumbers every LATER ap id. That is this branch's change, NOT a
# region move and NOT a renumbering bug. Every id here was RE-READ from the regenerated
# data.py by flag, never by subtracting 100 from the old one.
NOVAHDANGO_FIVE = {7773584, 7773629, 7773653, 7773654, 7773655}
ABYSSAL = "Abyssal"

LEDA = 580600
LEDA_REGION = "Belurat"

# The arena-coverage floor. 185 of 211 triggers carry a measured arena row; the other 26 are
# UNAUDITED, not clean. Ratcheted so the invariant cannot be widened by quietly losing coverage.
ARENA_COVERAGE_FLOOR = 185


class NoSweepGrantsOutsideItsArenaRegion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .. import boss_sweeps, data
        cls.sweeps = boss_sweeps.DUNGEON_SWEEPS
        cls.sweep_region = boss_sweeps.SWEEP_REGION
        cls.arena_region = getattr(boss_sweeps, "SWEEP_ARENA_REGION", {})
        cls.ap_region = {}
        for region, rows in data.LOCATIONS.items():
            for (name, ap, flag) in rows:
                cls.ap_region[ap] = region

    def test_the_invariant(self):
        """THE gate. Every member of a trigger with a measured arena lives in that arena's region."""
        bad, examined = [], 0
        for trigger, members in self.sweeps.items():
            arena = self.arena_region.get(trigger)
            if arena is None:
                continue                      # UNAUDITED -- counted by the floor test below
            for ap in members:
                region = self.ap_region.get(ap)
                if region is None:
                    continue
                examined += 1
                if region != arena:
                    bad.append((trigger, arena, ap, region))
        # WITNESS: an empty `bad` must mean "looked and found none", never "the join stopped
        # matching". 3695 member links carried a measured arena when this was written.
        self.assertGreater(
            examined, 3000,
            "the invariant examined only %d member link(s) -- the ap-id/arena join has broken and "
            "this test would pass for the wrong reason" % examined)
        self.assertEqual(
            bad, [],
            "#1059: %d cross-region sweep member link(s). A boss may only grant checks in the "
            "region it is fought in; these are granted somewhere the player need never have "
            "reached. First ten: %r" % (len(bad), bad[:10]))

    def test_the_gate_is_not_a_tautology(self):
        """SWEEP_ARENA_REGION must be INDEPENDENT evidence, not a copy of SWEEP_REGION.

        If someone ever 'fixes' a violation by assigning SWEEP_ARENA_REGION from the members, the
        test above becomes unfailable. Independence is checked structurally: the arena table must
        be partial (a derived copy would cover every trigger) and its coverage must be the
        measured one.
        """
        self.assertLess(
            len(self.arena_region), len(self.sweeps),
            "SWEEP_ARENA_REGION now covers EVERY trigger -- if it was filled from the members' own "
            "region, the containment test above can no longer fail. gen_data deliberately excludes "
            "the tile decode as an arena source for exactly this reason.")
        self.assertGreaterEqual(
            len(self.arena_region), ARENA_COVERAGE_FLOOR,
            "arena coverage fell below %d triggers -- the invariant would pass by measuring less"
            % ARENA_COVERAGE_FLOOR)

    def test_jori_hosts_scadu_altus_and_the_abyssal_five_moved_to_an_abyssal_boss(self):
        """NovahDango's five, named. The report is the test."""
        self.assertEqual(
            self.arena_region.get(JORI), JORI_ARENA_REGION,
            "Jori is fought in %s (bucket 40020)" % JORI_ARENA_REGION)
        self.assertEqual(
            self.sweep_region.get(JORI), JORI_ARENA_REGION,
            "Jori must HOST the region he is fought in, not the one his tile decodes to")
        for ap in NOVAHDANGO_FIVE:
            self.assertNotIn(
                ap, self.sweeps.get(JORI, []),
                "ap %d is an %s check and must not be granted by Jori" % (ap, ABYSSAL))
            self.assertEqual(self.ap_region.get(ap), ABYSSAL)
            hosts = [t for t, m in self.sweeps.items() if ap in m]
            self.assertTrue(
                hosts,
                "ap %d lost its sweep entirely -- a dropped cross-region member must be RE-HOSTED "
                "by its own region's divvy, never silently orphaned" % ap)
            for t in hosts:
                self.assertEqual(
                    self.arena_region.get(t, ABYSSAL), ABYSSAL,
                    "ap %d was re-hosted onto trigger %d, which is fought outside %s"
                    % (ap, t, ABYSSAL))

    def test_ledas_message_is_not_a_containment_violation(self):
        """Lilith's report, adjudicated rather than swept in. m20_00 IS Belurat, so the Dancing
        Lion grant is contained; the Shadow Keep placement is the #320/#502 multisite family."""
        from .. import data
        rows = [(r, n, ap) for r, rows_ in data.LOCATIONS.items()
                for (n, ap, flag) in rows_ if int(flag) == LEDA]
        self.assertTrue(rows, "f%d is no longer a check" % LEDA)
        for region, name, ap in rows:
            self.assertEqual(region, LEDA_REGION)
            hosts = [t for t, m in self.sweeps.items() if ap in m]
            for t in hosts:
                arena = self.arena_region.get(t)
                if arena is not None:
                    self.assertEqual(
                        arena, LEDA_REGION,
                        "if this ever fails, the check MOVED (the #320/#502 multisite question was "
                        "answered) and its sweep must be re-adjudicated with it")


class TheArenaTableIsFoldedThroughTheLiveSpine(unittest.TestCase):
    """boss_area_regions.tsv's `region` column is a SNAPSHOT; region_groups.py is the source.

    Six of its 120 rows were stale when #1059 was audited -- 11050 still Leyndell after the Ashen
    Capital split, 34100 still Limgrave after the #202 ruling, and two rows naming "Sewer", a
    region deleted by the 2026-08-20 Shunning-Grounds merge. Those six produced 17 of the 22
    cross-region links. gen_data now re-folds the BUCKET and ignores the column.
    """

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_every_arena_bucket_is_owned_by_the_live_spine(self):
        sys.path.insert(0, os.path.join(REPO, "greenfield"))
        import region_groups
        owner = {b: r for r, bs in region_groups.PLAY_REGION_GROUPS.items() for b in bs}
        path = os.path.join(REPO, "greenfield", "boss_area_regions.tsv")
        rows = 0
        for line in open(path, encoding="utf-8"):
            if line[:1] == "#" or line.startswith("defeat_flag"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3 or not parts[0].isdigit():
                continue
            rows += 1
            buckets = [int(b) for b in parts[1].split(";") if b.strip().isdigit()]
            owners = {owner.get(b) for b in buckets} - {None}
            self.assertTrue(
                owners,
                "boss_area_regions row %s names bucket(s) %s that PLAY_REGION_GROUPS does not own"
                % (parts[0], parts[1]))
            self.assertEqual(
                len(owners), 1,
                "boss_area_regions row %s spans more than one region (%s) -- a boss is fought in ONE"
                % (parts[0], sorted(owners)))
        self.assertGreater(rows, 100, "boss_area_regions.tsv looks truncated (%d rows)" % rows)

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_gen_does_not_read_the_region_column(self):
        """The whole point. If a future edit re-trusts column 3, this fails."""
        src = open(os.path.join(REPO, "greenfield", "gen_data.py"), encoding="utf-8").read()
        head = src[:src.index("# region_map.csv's region-column LABEL")]
        self.assertIn("_bar_owners", head,
                      "the boss_area_regions load no longer re-folds the bucket through "
                      "PLAY_REGION_GROUPS -- a stale copy of a table that moves is not evidence")
        self.assertNotIn("BOSS_AREA_REGION[int(_p[0])] = _p[2]", head,
                         "gen is reading boss_area_regions' stale `region` column again")


if __name__ == "__main__":
    unittest.main()
