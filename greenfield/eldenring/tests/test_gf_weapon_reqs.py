"""no_weapon_requirements -- the option that stopped being fixed behaviour in v0.4.1.

WHAT THIS FILE IS FOR, and it is one property, not a feature suite. `no_weapon_requirements` was
FROZEN AT 1 in `defaults.FROZEN_OPTIONS` from the v0.2 option slim until 2026-08-13: every seed ever
rolled has had weapon, shield, catalyst and spell requirements zeroed, and no yaml could say
otherwise. Unfreezing it makes that a choice -- and unfreezing is exactly the operation that
silently reverts every seed which does not name the option, because while an option is frozen its
class `default` is unreachable and rots unobserved.

That is not hypothetical. `PoolBuilderIntensity` was frozen at `max` with `default = 1` (`high`)
sitting underneath, and unfreezing it moved every default seed from the 1013-item juice catalog to
the 536-item one, inside a release whose changelog said nothing about a default seed had changed.
97 test files did not catch it; a review did.

So the assertion is simply: THE FREEZE VALUE IS THE DEFAULT. Everything else here exists so that
assertion cannot pass vacuously.
"""
import dataclasses

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract                                    # noqa: E402
from worlds.eldenring.core import GAME, GFOptions                        # noqa: E402
from worlds.eldenring.defaults import FROZEN_OPTIONS                     # noqa: E402
from worlds.eldenring.features.weapon_reqs import NoWeaponRequirements   # noqa: E402

#: The value the option was pinned at for the whole time it was frozen. Written down ONCE, here,
#: and read by every case below -- a test that retypes the number in three places can be half
#: updated, which is the failure mode of a constant that is really a fact about history.
FREEZE_VALUE = 1

_SURFACE = {f.name for f in dataclasses.fields(GFOptions)}


def test_the_option_is_actually_on_the_yaml_surface():
    """THE ANTI-VACUITY CASE, and it has to come first.

    Every other test in this file would pass unchanged if the option were re-frozen tomorrow: a
    class default is readable whether or not any yaml can reach it, so `default == 1` says nothing
    about whether a player can set the thing. This is the case that fails if the freeze comes back,
    and its failure message is the instruction.
    """
    assert "no_weapon_requirements" in _SURFACE, (
        "no_weapon_requirements is off the yaml surface again -- it is back in "
        "defaults.FROZEN_OPTIONS. That may well be right, but the rest of this file then asserts "
        "properties of an option nobody can set, so say why in the freeze comment and decide "
        "whether these cases should be skipped or deleted.")
    assert "no_weapon_requirements" not in FROZEN_OPTIONS, (
        "no_weapon_requirements is on GFOptions AND in FROZEN_OPTIONS -- apply_frozen refuses to "
        "overwrite a live field, so the frozen value would be silently ignored.")


def test_the_unfrozen_default_matches_the_freeze_value():
    """⭐ THE CHECK THE PoolBuilderIntensity UNFREEZE WENT WITHOUT.

    A bare `Toggle` defaults to 0. This one does not, and the reason is entirely historical: it was
    frozen at 1, so 1 is what every existing seed does, so 1 is what a seed that does not name the
    option must keep doing. Moving this to 0 is a legitimate decision -- it is just never a silent
    one, and this is the test that stops it being silent.
    """
    assert NoWeaponRequirements.default == FREEZE_VALUE, (
        "NoWeaponRequirements.default is %r, but the option was FROZEN AT %r until 2026-08-13. "
        "Unfreezing at a different default changes the behaviour of every seed that does not name "
        "the option -- requirements would start being ENFORCED for players who never asked for "
        "that. Either move the default back to the freeze value, or say in the changelog exactly "
        "what moved and for whom." % (NoWeaponRequirements.default, FREEZE_VALUE))


class TestDefaultSeedStillRemovesRequirements(WorldTestBase):
    """THE BEHAVIOUR WITNESS. The two cases above are statements about a class attribute; this one
    builds a real world that names no options at all and reads what the client will actually be
    told. A default that is right in the class and wrong on the wire is still wrong."""

    game = GAME
    options = {"num_regions": 0}

    def test_the_echo_the_client_reads_is_still_on(self):
        sd = self.world.fill_slot_data()
        self.assertIn("options", sd, "the options echo sub-dict is missing entirely")
        self.assertEqual(
            FREEZE_VALUE, sd["options"][contract.NO_WEAPON_REQUIREMENTS],
            "a seed that names no options must still zero weapon requirements -- that is what "
            "every seed has done since the v0.2 slim, and slot_data['options'] is the copy "
            "no_weapon_reqs.rs reads.")

    def test_the_legacy_top_level_copy_agrees_with_it(self):
        """contract.py carries a SECOND, top-level `no_weapon_requirements` key (a legacy duplicate
        the client no longer reads). Two copies of one fact drift; assert they cannot."""
        sd = self.world.fill_slot_data()
        if contract.NO_WEAPON_REQUIREMENTS not in sd:
            self.skipTest("no top-level legacy copy is emitted any more -- nothing to disagree")
        self.assertEqual(
            bool(sd["options"][contract.NO_WEAPON_REQUIREMENTS]),
            bool(sd[contract.NO_WEAPON_REQUIREMENTS]),
            "the top-level legacy copy and the options-echo copy disagree about the same setting")


class TestTheOptionCanActuallyBeTurnedOff(WorldTestBase):
    """The whole point of the unfreeze: a yaml can now say no. While frozen, this world could not
    be constructed -- AP silently ignores an unknown key, so `no_weapon_requirements: false` read
    as a knob and did nothing."""

    game = GAME
    options = {"num_regions": 0, "no_weapon_requirements": False}

    def test_off_reaches_the_wire(self):
        opts = self.world.fill_slot_data()["options"]
        # WITNESS FIRST. `0` is what an absent key, a broken echo and a working `false` all look
        # like from the assertion below, and only one of those is the thing under test. So: the key
        # is present, and the echo around it carries real values rather than a dict of zeros.
        self.assertIn(
            contract.NO_WEAPON_REQUIREMENTS, opts,
            "the key is missing from the options echo, which is a different bug from the option "
            "being off -- and it reads identically at the assertion below.")
        self.assertTrue(
            any(v for v in opts.values() if isinstance(v, int)),
            "every int in the options echo is 0, so this world proves nothing about one of them "
            "being 0 on purpose. The echo itself is broken.")
        self.assertEqual(
            0, opts[contract.NO_WEAPON_REQUIREMENTS],
            "a yaml saying no_weapon_requirements: false still emitted the frozen 1 -- the option "
            "is on the surface but something downstream is not reading it.")
