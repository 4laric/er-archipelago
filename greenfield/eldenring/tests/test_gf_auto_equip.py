"""auto_equip -- the option reaches the client, AND an old client is told it cannot honour it.

MOTIVATING CASE (CONTRIBUTING rule 11). The client has shipped a complete auto-equip implementation
for weeks -- `auto_equip.rs`, armed from `core.rs` with
`set_enabled(er_logic::options::parse_auto_equip(sd))`, reading `slot_data["options"]["auto_equip"]`.
The apworld has NEVER emitted that key. `parse_bool_option` on an absent key is `false`, so the
feature was inert for every ER seed ever generated, and nothing said so: the wire was well-formed,
the contract validated, the client logged nothing. It took reading the cross-side gate's ALLOW
ratchet to find it.

So this file asserts the two halves of "the setting the player chose actually happens", and they
fail for DIFFERENT reasons:

  1. THE VALUE. `options.auto_equip` is what the client reads. Without it the feature is dark.
  2. THE HANDSHAKE. `requiresClientFeatures` must carry `auto_equip` when -- and only when -- the
     option is on. `contract._contract_hash()` folds in CONTRACT and NOT OPTIONS_SUBKEYS, so adding
     an options sub-key does not move the hash: a client older than this change reports
     `VERSION: OK`, cannot see the key, and silently runs the seed with auto-equip off. That is
     indistinguishable from the bug above -- the same silent failure, one release later. And the
     "only when on" half matters just as much in the other direction: tag a DEFAULT seed and every
     player on a current client is refused a connection over a feature the seed does not use.

VERIFIED BY BREAKING (2026-08-02), each half separately, because a test that would pass without the
fix is not a test:
  * deleted `contract.AUTO_EQUIP: _opt("auto_equip")` from `core._options_echo`
    -> `test_on_seed_sends_the_value` FAILS ("options.auto_equip is missing entirely"),
       `test_on_seed_declares_the_client_feature` still passes.
  * made `features/auto_equip.slot_data` return `{}` unconditionally
    -> `test_on_seed_declares_the_client_feature` FAILS ("requiresClientFeatures absent"),
       `test_on_seed_sends_the_value` still passes.
Neither break reddens the other's assertion, which is what makes them two tests and not one.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"
TAG = "auto_equip"

# PINNED, not left to the class default. Two reasons, both learned the hard way: an unpinned
# num_regions makes the kept set a per-seed subset, and these are slot_data-shape assertions that
# must not be re-deciding which regions exist; and 6 (the shipped default) fills in a fraction of
# the time an all-regions world does, which is the whole cost of a WorldTestBase class. Nothing
# here depends on the region count -- the echo and the handshake are pure functions of the options.
REGIONS = 6


class AutoEquipOff(WorldTestBase):
    """THE DEFAULT SEED. Off is the default, and an old client must still be able to connect.

    auto_equip is PINNED False rather than left to the class default: the off state is what this
    class exists to test, and a default that drifts ON would silently turn every assertion below
    into an on-seed reading (memory: er-unfreezing-an-option-needs-the-class-default). The pin is
    also what lets test_gf_off_means_off verify AllClientFeatureGatesOffSeed-style rows against
    a class that really sets its option."""
    game = GAME
    options = {"num_regions": REGIONS, "auto_equip": False}

    def test_off_seed_sends_a_falsey_value(self):
        sd = self.world.fill_slot_data()
        self.assertIn("auto_equip", sd["options"],
                      "options.auto_equip must be emitted on EVERY seed, not only when it is on -- "
                      "the presence of a key must never itself carry meaning (contract.py's rule "
                      "for completion_scaling_ceiling), and the client reads it unconditionally.")
        self.assertFalse(sd["options"]["auto_equip"],
                         "the default seed must send a falsey auto_equip; the option defaults OFF "
                         "and a default seed must be no-change.")
        contract.validate_slot_data(sd, strict=True)

    def test_off_seed_does_NOT_demand_the_client_feature(self):
        """The half that protects everyone who did NOT ask for this.

        `requiresClientFeatures` is a connect REFUSAL on the client side. A tag emitted
        unconditionally would lock every player on a pre-0.3.1 client out of every seed we roll --
        a compatibility break paid by people who never turned the feature on.
        """
        sd = self.world.fill_slot_data()
        # NB this asserts the TAG, not full key absence: on this 2-region seed
        # maximum_enemy_difficulty=auto resolves below 100, so features/scaling.py legitimately
        # declares "scaling_ceiling" here. The FULL absent-when-every-producer-is-off state is
        # owned by test_gf_off_means_off.AllClientFeatureGatesOffSeed (2026-08-04 sweep).
        required = sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
        self.assertNotIn(TAG, required,
                         "a DEFAULT seed declared requiresClientFeatures %r. Every client without "
                         "the tag would REFUSE to connect to an ordinary seed." % (required,))


class AutoEquipOn(WorldTestBase):
    """THE SEED THAT ASKED FOR IT -- the French Challenge shape: you wear what you are sent."""
    game = GAME
    options = {"num_regions": REGIONS, "auto_equip": True}

    def test_on_seed_sends_the_value(self):
        sd = self.world.fill_slot_data()
        self.assertIn("auto_equip", sd["options"],
                      "options.auto_equip is missing entirely -- this is the original bug: the "
                      "client reads slot_data['options']['auto_equip'] and the apworld never sent "
                      "it, so the feature was inert for every seed.")
        self.assertTrue(sd["options"]["auto_equip"],
                        "the player set auto_equip and the wire says %r. The client parses this "
                        "with parse_bool_option, so a falsey value is the feature turned off."
                        % (sd["options"]["auto_equip"],))
        self.assertIsInstance(sd["options"]["auto_equip"], int)
        contract.validate_slot_data(sd, strict=True)

    def test_on_seed_declares_the_client_feature(self):
        sd = self.world.fill_slot_data()
        required = sd.get(contract.REQUIRES_CLIENT_FEATURES)
        self.assertIsNotNone(
            required,
            "requiresClientFeatures absent on a seed that USES auto_equip. OPTIONS_SUBKEYS is not "
            "folded into CONTRACT_HASH, so an older client reports VERSION: OK, never sees "
            "options.auto_equip, and runs the seed with the feature off -- silently.")
        self.assertIn(TAG, required,
                      "requiresClientFeatures is %r; it must name %r, the tag in er-logic's "
                      "client_features.rs SUPPORTED list." % (required, TAG))

    def test_the_tag_string_is_the_one_the_client_greps_for(self):
        """A handshake whose two sides spell the tag differently is worse than no handshake: it
        refuses every client, including the ones that DO support the feature."""
        from worlds.eldenring.features.auto_equip import CLIENT_FEATURE_TAG
        self.assertEqual(CLIENT_FEATURE_TAG, "auto_equip")
        self.assertEqual(
            CLIENT_FEATURE_TAG,
            [k.name for k in contract.OPTIONS_SUBKEYS if k.name == "auto_equip"][0],
            "the feature tag and the options sub-key deliberately share a spelling; if they ever "
            "diverge, say so here rather than letting the two drift apart quietly.")


class AutoEquipWithScalingCeiling(WorldTestBase):
    """TWO features declaring a tag at once -- the combination that used to CRASH GENERATION.

    `registry.merge_slot_data` raises on a duplicate slot_data key, and `features/scaling.py` has
    emitted `requiresClientFeatures` since 2026-07-27. So the first ordinary seed that turned on
    auto_equip AND capped difficulty would have died in `fill_slot_data` with "slot_data key
    'requiresClientFeatures' emitted by core and feature 'auto_equip'" -- a generation crash on a
    perfectly legal option combination, from the machinery that exists to PREVENT silent breakage.
    `registry.UNION_KEYS` makes the key a union instead. This is the test that would have caught it.
    """
    game = GAME
    options = {"num_regions": REGIONS, "auto_equip": True, "maximum_enemy_difficulty": 50}

    def test_both_tags_ride_together(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sorted(sd[contract.REQUIRES_CLIENT_FEATURES]),
                         ["auto_equip", "scaling_ceiling"],
                         "both features declared a dependency and the wire carries %r. A union, "
                         "sorted, is the only shape that is a function of the OPTIONS rather than "
                         "of feature import order." % (sd[contract.REQUIRES_CLIENT_FEATURES],))
        contract.validate_slot_data(sd, strict=True)
