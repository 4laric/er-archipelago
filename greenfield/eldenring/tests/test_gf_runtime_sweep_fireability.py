"""Known-unfireable sweeps must not be promised to the client/tracker (#878).

MOTIVATING CASE. Cokeman5 spared Patches, then the tracker permanently showed
``Patches (Limgrave) -- 1/2 checks [flag 31000850] -- waiting on the boss``. #672 already knew
Patches yields instead of dying and barred that trigger from REQUIRED SweepSlot progression, but
the ordinary slot-data emit did not consume the ruling and still armed the dead group.

The distinction is load-bearing: an unnamed or unaudited trigger is unsafe for progression but is
not thereby proven dead at runtime. This file pins both sides using the Divine Tower's unnamed
34100800 group as the control.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS  # noqa: E402
from worlds.eldenring.data import LOCATIONS  # noqa: E402


PATCHES = 31000850
UNNAMED_CONTROL = 34100800


class RuntimeSweepFireability(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "dungeon_sweep": "bosses"}

    def test_the_raw_evidence_still_contains_the_reported_group(self):
        """The fix is a runtime ruling, not deleting the evidence that makes it testable."""
        self.assertTrue(DUNGEON_SWEEPS.get(PATCHES),
                        "fixture lost Patches' raw group; the runtime filter is no longer exercised")

    def test_runtime_slot_data_drops_patches_but_keeps_the_unaudited_control(self):
        """dungeonSweepFlags is exactly what the client watches and the F6 tracker renders."""
        live = self.world.fill_slot_data()[contract.DUNGEON_SWEEP_FLAGS]
        self.assertNotIn(str(PATCHES), live,
                         "Patches' non-lethal defeat flag is still promised to the tracker")
        self.assertIn(str(UNNAMED_CONTROL), live,
                      "the runtime filter widened to every progression-unsafe/unaudited sweep")

    def test_one_ruling_drives_surface_and_runtime_without_conflating_them(self):
        runtime = contract.runtime_sweep_skips()
        surface = contract.sweep_slot_skips()
        self.assertIn(PATCHES, runtime)
        self.assertTrue(set(runtime) <= set(surface))
        self.assertIn(UNNAMED_CONTROL, surface,
                      "fixture lost the unnamed progression-safety control")
        self.assertNotIn(UNNAMED_CONTROL, runtime,
                         "unnamed is not evidence that a trigger cannot fire")

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

