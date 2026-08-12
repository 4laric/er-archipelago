"""no_equip_load carries a ROLL MODE, and only the new value demands a new client.

MOTIVATING CASE (CONTRIBUTING rule 11). The client has shipped a three-way roll mode since v0.3.11
-- `er_logic::equip_load::RollMode` (`0` off / `1` light / `2` medium), with `no_equip_load_roll` in
`client_features.rs` SUPPORTED. The apworld could only ever emit a Toggle, so `medium` was
unreachable: the strongest setting was the ONLY setting, and a player who wanted heavy armour to
still cost something had no way to ask for it. v0.3.11's own release notes said as much -- "a
medium-roll setting is built on the client side, waiting on its yaml half".

This file asserts the three things that half has to get right, and they fail for DIFFERENT reasons:

  1. THE VALUE. `options.no_equip_load` must carry 0/1/2, not a bool. Without the widening the
     client's `parse` only ever sees the two old values.
  2. THE HANDSHAKE, IN BOTH DIRECTIONS -- and this is the asymmetric one. `medium` MUST tag, because
     `contract._contract_hash()` folds in CONTRACT and NOT OPTIONS_SUBKEYS: an older client reports
     `VERSION: OK`, reads the new `2` through `parse_bool_option`, sees a nonzero, and gives LIGHT.
     The player asked for the WEAKER setting and silently got the strongest one. `light` MUST NOT
     tag, because an old client's reading of `1` is the correct one -- tagging it would refuse the
     connect on every client that has implemented this capability for months, over a setting they
     honour perfectly. Getting either half backwards is a shipped bug, so both are asserted.
  3. THE LEGACY SPELLINGS. This option shipped as a `Toggle`, so yamls in the wild say
     `no_equip_load: true`. AP's `Choice.from_any` tests `type(data) == int` and `type(True)` is
     `bool`, so a bare yaml boolean falls through to `from_text`. Without `alias_true` / `alias_false`
     every existing yaml that turned this on becomes an OptionError at generation -- a silent compat
     break for exactly the players who already use the feature.

VERIFIED BY BREAKING (2026-08-12), each half separately, because a test that would pass without the
fix is not a test:
  * made `features/body_tuning.NoEquipLoadFeature.slot_data` return `{}` unconditionally
    -> `TestMedium.test_medium_declares_the_client_feature` FAILS ("requiresClientFeatures absent"),
       every value assertion still passes.
  * changed the hook's guard to `if not world.options.no_equip_load.value` (tag whenever on)
    -> `TestLight.test_light_does_NOT_demand_the_client_feature` FAILS, medium still passes.
  * deleted `alias_true` / `alias_false`
    -> both `TestLegacyYamlSpellings` value tests FAIL; TestOff/TestLight/TestMedium are untouched,
       because they name the values (`"light"`) and resolve through `option_*` rather than aliases.
No break reddens another's assertion, which is what makes these separate tests.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features.body_tuning import CLIENT_FEATURE_TAG, NoEquipLoad  # noqa: E402

GAME = "Elden Ring"

# PINNED, not left to the class default -- same reasoning as test_gf_auto_equip: an unpinned
# num_regions makes the kept set a per-seed subset, and nothing here depends on the region count.
# The echo and the handshake are pure functions of the options.
REGIONS = 6


class TestOff(WorldTestBase):
    """THE DEFAULT SEED. Off is the default and must stay a no-change wire."""
    game = GAME
    options = {"num_regions": REGIONS, "no_equip_load": "off"}

    def test_off_seed_sends_zero(self):
        sd = self.world.fill_slot_data()
        self.assertIn("no_equip_load", sd["options"],
                      "options.no_equip_load must be emitted on EVERY seed, not only when it is on "
                      "-- the presence of a key must never itself carry meaning, and the client "
                      "reads it unconditionally.")
        self.assertEqual(0, sd["options"]["no_equip_load"])
        contract.validate_slot_data(sd, strict=True)

    def test_off_seed_does_NOT_demand_the_client_feature(self):
        required = sd_required(self.world)
        self.assertNotIn(CLIENT_FEATURE_TAG, required,
                         "a DEFAULT seed declared %r. Every client without the tag would REFUSE to "
                         "connect to an ordinary seed." % (required,))


class TestLight(WorldTestBase):
    """WHAT `true` HAS ALWAYS MEANT. Wire value 1, and -- the half that protects existing players --
    still no handshake, because every released client reads 1 correctly."""
    game = GAME
    options = {"num_regions": REGIONS, "no_equip_load": "light"}

    def test_light_sends_one(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(
            1, sd["options"]["no_equip_load"],
            "light must ride as 1: that is what the legacy Toggle's `true` put on the wire, so a "
            "client that predates the roll mode goes on doing exactly what it did before.")
        self.assertIsInstance(sd["options"]["no_equip_load"], int)
        contract.validate_slot_data(sd, strict=True)

    def test_light_does_NOT_demand_the_client_feature(self):
        """The compat half. `light` is OLDER than every client in circulation; a tag here would lock
        every one of them out of a seed whose feature they already implement correctly."""
        required = sd_required(self.world)
        self.assertNotIn(
            CLIENT_FEATURE_TAG, required,
            "a LIGHT seed declared %r. Light is what these clients have implemented for months -- "
            "refusing them is a compat break paid by the players already using the feature."
            % (required,))


class TestMedium(WorldTestBase):
    """THE NEW VALUE, AND THE ONLY ONE THAT NEEDS A NEW CLIENT."""
    game = GAME
    options = {"num_regions": REGIONS, "no_equip_load": "medium"}

    def test_medium_sends_two(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(
            2, sd["options"]["no_equip_load"],
            "medium must ride as 2 -- er_logic::equip_load::WIRE_MEDIUM. Any other value is read "
            "as light by the client, which is the bug this option exists to avoid.")
        contract.validate_slot_data(sd, strict=True)

    def test_medium_declares_the_client_feature(self):
        required = sd_required(self.world)
        self.assertIn(
            CLIENT_FEATURE_TAG, required,
            "requiresClientFeatures is %r; a medium seed MUST name %r. OPTIONS_SUBKEYS is not "
            "folded into CONTRACT_HASH, so an older client reports VERSION: OK, reads the 2 through "
            "parse_bool_option, and gives the player LIGHT -- the stronger setting they did not "
            "ask for, silently." % (required, CLIENT_FEATURE_TAG))


class TestLegacyYamlSpellings(WorldTestBase):
    """A yaml written before the widening must still generate. Uses the OFF pin so the class is
    cheap; the assertions are on the option class, not on this seed."""
    game = GAME
    options = {"num_regions": REGIONS, "no_equip_load": "off"}

    def test_bare_yaml_booleans_still_resolve(self):
        """`no_equip_load: true` in a yaml is a Python bool, and AP's Choice.from_any tests
        `type(data) == int` -- which `bool` is not. Without the aliases this raises."""
        self.assertEqual(1, NoEquipLoad.from_any(True).value,
                         "`no_equip_load: true` must go on meaning light, the behaviour it has had "
                         "since the option shipped.")
        self.assertEqual(0, NoEquipLoad.from_any(False).value)

    def test_the_textual_spellings_resolve(self):
        for text, expected in (("true", 1), ("false", 0), ("on", 1), ("off", 0),
                               ("light", 1), ("medium", 2)):
            self.assertEqual(expected, NoEquipLoad.from_any(text).value,
                             "no_equip_load: %s must resolve to %d" % (text, expected))

    def test_ints_resolve(self):
        for value in (0, 1, 2):
            self.assertEqual(value, NoEquipLoad.from_any(value).value)


class TestTagSpelling(WorldTestBase):
    """A handshake whose two sides spell the tag differently is worse than no handshake: it refuses
    every client, including the ones that DO support the feature."""
    game = GAME
    options = {"num_regions": REGIONS, "no_equip_load": "off"}

    def test_the_tag_is_the_one_the_client_greps_for(self):
        self.assertEqual("no_equip_load_roll", CLIENT_FEATURE_TAG)

    def test_the_tag_is_NOT_the_option_key(self):
        """Deliberately different from `auto_equip`, where tag and key share a spelling. Here the
        option is older than the tag: the KEY needs no client support, only the third VALUE does."""
        self.assertNotEqual(
            CLIENT_FEATURE_TAG,
            [k.name for k in contract.OPTIONS_SUBKEYS if k.name == "no_equip_load"][0],
            "the tag gates the roll MODE, not the option -- if they are ever unified, say so here "
            "rather than letting the distinction erode quietly.")


def sd_required(world):
    """`requiresClientFeatures` as a list, tolerating absence.

    NB the tests assert the TAG, not full key absence: other producers (features/scaling.py's
    `scaling_ceiling`) legitimately contribute on these small seeds. The fully-absent state is owned
    by test_gf_off_means_off.AllClientFeatureGatesOffSeed.
    """
    return world.fill_slot_data().get(contract.REQUIRES_CLIENT_FEATURES, [])
