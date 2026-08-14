"""SweepSlot may only nominate a member we are CONFIDENT is swept (er-archipelago#672).

SweepSlot's premise is that this world's progression only lands where a sweep trigger will hand it
over. A trigger that cannot fire turns that promise into a coincidence: the item sits on junk, the
player is told nothing, and there is no boss to go and kill.

MOTIVATING CASE (bobler, Discord 2026-08-14). Progression restricted to boss sweeps. He cleared
**19/19 Limgrave bosses** and finished at 235/332 with two progression checks still open:

    * Limgrave :: Mushroom - treasure - Murkwater Cave [f31007000]      swept by 31000850
    * Limgrave :: Warming Stone - near Limgrave Tower Bridge [f34107000] swept by 34100800

`34100800` is the Divine Tower of Limgrave: BOSS_HEALTHBARS records an EMPTY name, and
arena_graces.tsv's own header already lists it under `# unresolved_bosses`. `31000850` is Patches,
who yields rather than dying, so his defeat flag is never reached in normal play.

🛑 These assertions were written against the BROKEN behaviour first: with `skips={}` -- the
pre-fix expression -- both ap-ids ARE nominated, which is what `test_the_fix_is_load_bearing`
pins. Delete the gate and this file goes red rather than vacuous.

Run:  python greenfield/eldenring/tests/test_gf_sweep_slot_skips.py
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)


def _load(name):
    """Load a leaf data/contract module by path, so this runs with no AP install."""
    spec = importlib.util.spec_from_file_location(
        "gf_" + name + "_skipcheck", os.path.join(GF_PKG, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CONTRACT = _load("contract")
SWEEPS = _load("boss_sweeps").DUNGEON_SWEEPS
HEALTHBARS = _load("boss_healthbars").BOSS_HEALTHBARS

# bobler's two, resolved from data.py by FLAG rather than hard-coded ap-id: #249 renumbered the ap
# ids once already, and a test that pins the old number would pass for the wrong reason.
_TRIPLE = re.compile(r'\(\s*([\'"])(.*?)\1\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
with open(os.path.join(GF_PKG, "data.py"), encoding="utf-8", errors="replace") as fh:
    _AP_BY_FLAG = {t[3]: int(t[2]) for t in _TRIPLE.findall(fh.read())}

MUSHROOM_AP = _AP_BY_FLAG["31007000"]      # Murkwater Cave, swept by Patches
WARMING_STONE_AP = _AP_BY_FLAG["34107000"]  # Divine Tower of Limgrave, swept by nothing


class TestSweepSlotSkips(unittest.TestCase):

    def test_boblers_two_checks_are_not_nominated(self):
        """THE MOTIVATING CASE. Neither check may be a SweepSlot surface entry.

        Healthbars are passed explicitly, exactly as `progression_surface.sweep_slot_aps` passes
        them: `sweep_slot_skips()`'s own lazy import is package-relative and CANNOT resolve under
        `spec_from_file_location`, so a test that relied on the default would assert the degraded
        path and call it a pass -- see `test_the_lazy_default_degrades_SAFELY`."""
        nominated = CONTRACT.nominate_sweep_slots(
            SWEEPS, skips=CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS))
        self.assertNotIn(MUSHROOM_AP, nominated,
                         "Murkwater Cave mushroom is swept by Patches, who never dies")
        self.assertNotIn(WARMING_STONE_AP, nominated,
                         "Divine Tower warming stone is swept by a trigger with no boss")

    def test_the_fix_is_load_bearing(self):
        """🛑 The same call WITHOUT the gate nominates both -- so the assertions above are a real
        witness of the defect, not a restatement of whatever the code happens to do."""
        unguarded = CONTRACT.nominate_sweep_slots(SWEEPS, skips={})
        self.assertIn(MUSHROOM_AP, unguarded)
        self.assertIn(WARMING_STONE_AP, unguarded)

    def test_every_unnamed_trigger_is_skipped(self):
        """The derived half: a trigger BOSS_HEALTHBARS cannot name cannot be vouched for."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        unnamed = [f for f, info in HEALTHBARS.items()
                   if not str((info[3] if len(info) > 3 else "") or "").strip()]
        self.assertTrue(unnamed, "fixture check: expected at least one unnamed trigger")
        for flag in unnamed:
            self.assertIn(flag, skips, f"unnamed trigger {flag} must be skipped")

    def test_patches_is_skipped_though_he_IS_named(self):
        """The declared half, and why it cannot be derived.

        Patches has a NAME in BOSS_HEALTHBARS, so no join over the shipped tables can exclude him --
        bobler's tracker even read "Patches ✅", because that is the check his ENCOUNTER grants, not
        the sweep's defeat flag."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        for flag in (31000800, 31000850):
            self.assertIn(flag, skips)
            self.assertTrue(str(HEALTHBARS[flag][3]).strip(),
                            "fixture check: Patches is NAMED, so the derived half cannot catch him")

    def test_every_skip_carries_a_reason(self):
        """ShopSlot's SHOP_SLOT_SKIPS shape: keyed by what is excluded, valued by WHY. A silent
        filter is how an exclusion outlives the reason for it."""
        for flag, reason in CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS).items():
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason.strip()), 20, f"{flag} needs a real reason")

    def test_the_gate_only_removes(self):
        """It must never ADD a nomination -- the surface may shrink (the feasibility ladder widens
        to cover it), but a gate that grows the surface is a different feature."""
        guarded = CONTRACT.nominate_sweep_slots(
            SWEEPS, skips=CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS))
        unguarded = CONTRACT.nominate_sweep_slots(SWEEPS, skips={})
        self.assertTrue(guarded.issubset(unguarded))
        self.assertLess(len(guarded), len(unguarded), "fixture check: the gate should bite")

    def test_the_lazy_default_degrades_SAFELY(self):
        """🛑 `sweep_slot_skips()` with no argument resolves BOSS_HEALTHBARS through a
        package-relative import. When that cannot resolve -- which is the case here, and would be
        the case for any caller loading contract.py by path -- it must fall back to the DECLARED
        set and never to 'skip everything' or 'skip nothing but crash'.

        This is why `progression_surface.sweep_slot_aps` passes the table explicitly instead of
        trusting the default: silently dropping the derived half would put the unfireable triggers
        straight back on the surface with no error anywhere."""
        self.assertEqual(set(CONTRACT.sweep_slot_skips()), {31000800, 31000850})

    def test_missing_healthbars_does_not_empty_the_surface(self):
        """🛑 If the healthbar table were unavailable, skipping on absence would silently disable
        SweepSlot everywhere and the ladder would widen with nobody the wiser. Only the DECLARED
        set survives that case."""
        skips = CONTRACT.sweep_slot_skips(healthbars={})
        self.assertEqual(set(skips), {31000800, 31000850})
        still = CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips)
        self.assertGreater(len(still), len(SWEEPS) - 10)


if __name__ == "__main__":
    unittest.main()
