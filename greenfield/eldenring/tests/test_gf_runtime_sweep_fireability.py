"""Known-unfireable sweeps must not be promised to the client/tracker (#878).

MOTIVATING CASE. Cokeman5 spared Patches, then the tracker permanently showed
``Patches (Limgrave) -- 1/2 checks [flag 31000850] -- waiting on the boss``. #672 already knew
Patches yields instead of dying and barred that trigger from REQUIRED SweepSlot progression, but
the ordinary slot-data emit did not consume the ruling and still armed the dead group.

The distinction is load-bearing: an unnamed or unaudited trigger is unsafe for progression but is
not thereby proven dead at runtime.

2026-09-09 (#1529). This file used to hold up the Divine Tower's unnamed ``34100800`` as the
"unsafe but still live" control. That was the wrong example, and it took an EMEVD read to see why:
34100800's boss chain is DEFINED and never ``$InitializeEvent``'d from the map constructor, so the
flag is unreachable -- it was never merely unaudited, it was cut. Four such triggers (plus
34150800, which owns no group) are now DECLARED unfireable, and the "unsafe but live" side of the
distinction is carried by an UNAUDITED-ARENA control instead: a real, named, killable boss whose
arena region has not been adjudicated (#671). That is the honest shape of the distinction -- there
is no longer any blank-named trigger that owns a live group, and
``test_no_blank_named_trigger_still_owns_a_live_group`` is what keeps the next cut arena from
quietly becoming one.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.tables.boss_healthbars import BOSS_HEALTHBARS  # noqa: E402
from worlds.eldenring.tables.boss_sweeps import DUNGEON_SWEEPS  # noqa: E402
from worlds.eldenring.tables.data import LOCATIONS  # noqa: E402


PATCHES = 31000850
# Named, killable, and still live at runtime -- only its ARENA REGION is unadjudicated, which bars
# it from hosting REQUIRED progression (#671) without saying anything about whether it can fire.
UNAUDITED_CONTROL = 1035420800          # Omenkiller, m60_35_42
# The cut-content class: EMEVD chain defined, never initialized from the map constructor.
CUT_CONTENT = (30130810, 34100800, 34110800, 1041330800)
CUT_CONTENT_NO_GROUP = 34150800         # same ruling, but it owns no sweep group to remove


def _name_of(flag):
    info = BOSS_HEALTHBARS.get(flag)
    return str((info[3] if info and len(info) > 3 else "") or "")


class RuntimeSweepFireability(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "dungeon_sweep": "bosses"}

    def test_the_raw_evidence_still_contains_the_reported_group(self):
        """The fix is a runtime ruling, not deleting the evidence that makes it testable."""
        self.assertTrue(DUNGEON_SWEEPS.get(PATCHES),
                        "fixture lost Patches' raw group; the runtime filter is no longer exercised")
        for flag in CUT_CONTENT:
            if flag == 1041330800:
                # This one is ALSO an unspawned verdict, so gen_data drops it from the baked table
                # before it can be filtered at runtime. Both mechanisms agree; only one can be
                # observed in the shipped data.
                continue
            self.assertTrue(DUNGEON_SWEEPS.get(flag),
                            f"fixture lost the cut-content group {flag}; the filter is untested")

    def test_runtime_slot_data_drops_the_dead_groups_but_keeps_the_unaudited_control(self):
        """dungeonSweepFlags is exactly what the client watches and the F6 tracker renders."""
        live = self.world.fill_slot_data()[contract.DUNGEON_SWEEP_FLAGS]
        self.assertNotIn(str(PATCHES), live,
                         "Patches' non-lethal defeat flag is still promised to the tracker")
        for flag in CUT_CONTENT:
            self.assertNotIn(
                str(flag), live,
                f"cut-content trigger {flag} is still promised to the tracker -- its EMEVD chain is "
                f"never initialized, so the client would render 'waiting on the boss' forever")
        self.assertIn(str(UNAUDITED_CONTROL), live,
                      "the runtime filter widened to every progression-unsafe/unaudited sweep")

    def test_one_ruling_drives_surface_and_runtime_without_conflating_them(self):
        runtime = contract.runtime_sweep_skips()
        surface = contract.sweep_slot_skips()
        self.assertIn(PATCHES, runtime)
        self.assertTrue(set(runtime) <= set(surface))
        self.assertIn(UNAUDITED_CONTROL, surface,
                      "fixture lost the unaudited progression-safety control")
        self.assertNotIn(UNAUDITED_CONTROL, runtime,
                         "an unadjudicated arena is not evidence that a trigger cannot fire")
        self.assertTrue(_name_of(UNAUDITED_CONTROL).strip(),
                        "fixture check: the control must be NAMED, or it is testing the cut class")

    def test_every_declared_runtime_skip_cites_its_evidence(self):
        """A declared skip is a hand ruling. Unlike the derived ones it can only be checked against
        the reason string, so the reason has to be a citation and not an assertion -- a date and the
        issue that carries the write-up, at minimum."""
        skips = contract.runtime_sweep_skips()
        self.assertTrue(skips)
        for flag, reason in skips.items():
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason.strip()), 40, f"{flag} needs a real reason")
            self.assertRegex(reason, r"\d{4}-\d\d-\d\d",
                             f"{flag}'s reason cites no date -- when was this established?")
            self.assertRegex(reason, r"#\d+",
                             f"{flag}'s reason cites no issue -- where is the write-up?")

    def test_no_blank_named_trigger_still_owns_a_live_group(self):
        """🛑 THE REGRESSION GATE FOR THE NEXT CUT ARENA.

        A blank name in BOSS_HEALTHBARS means the datamine could not name a boss to kill. Every
        such trigger we have looked at turned out to be cut content whose EMEVD chain the map
        constructor never arms -- so a blank-named trigger that still ships a group in
        dungeonSweepFlags is a group the player can never collect, and the tracker says "waiting on
        the boss" until the seed ends.

        This does NOT say "blank implies dead" as a derivation -- it says any new blank-named group
        must be ADJUDICATED (given a name by the datamine, or a row in
        contract._RUNTIME_SWEEP_SKIP_REASONS with its constructor evidence) before it ships.
        """
        runtime = contract.runtime_sweep_skips()
        offenders = sorted(
            flag for flag, members in DUNGEON_SWEEPS.items()
            if members and not _name_of(flag).strip() and flag not in runtime)
        self.assertEqual(
            offenders, [],
            "blank-named sweep trigger(s) %s still own a live group. Read the map's EMEVD "
            "constructor $Event(0, Default): if the boss chain is never $InitializeEvent'd, add the "
            "flag to contract._RUNTIME_SWEEP_SKIP_REASONS with that file:line evidence; if the "
            "fight is real, the datamine owes it a name." % (offenders,))

    def test_the_groupless_cut_trigger_is_declared_anyway(self):
        """34150800 has no members today, so nothing observable changes by declaring it -- which is
        exactly why it would otherwise be dropped and silently reappear if a regen ever gave it a
        group. The ruling is about the boss, not about the current member count."""
        self.assertIn(CUT_CONTENT_NO_GROUP, contract.runtime_sweep_skips())
        self.assertFalse(DUNGEON_SWEEPS.get(CUT_CONTENT_NO_GROUP),
                         "fixture check: 34150800 was expected to own no group")

    def test_members_do_not_promise_a_sweep_eligible_patches_route(self):
        names = {ap: name for rows in LOCATIONS.values() for name, ap, _flag in rows}
        members = DUNGEON_SWEEPS[PATCHES]
        self.assertTrue(members)
        # #936 reworded the clause opener; the assertion is on the CURRENT wording, which is
        # the only one this repo's regenerated data.py can contain.
        wrong = [names[ap] for ap in members
                 if "may be sweep-granted by Patches" in names[ap] or "also granted by Patches" in names[ap]]
        self.assertEqual(wrong, [],
                         "a physical pickup still advertises the runtime route we refuse to arm")
