"""no_rune_loss -- the option surface, and the multi-producer tag list it forced open.

Two things are under test here and they are not the same thing:

1. `no_rune_loss` is declared as an `options` SUB-KEY. Sub-keys do NOT move CONTRACT_HASH (see
   client_features.rs), so an old client would ignore the key in total silence -- the player asks to
   keep their runes, dies, and loses them. The seed therefore has to declare the `no_rune_loss` tag
   in `requiresClientFeatures`, and ONLY when the option is on, so default seeds still connect to
   any client.

2. Declaring that tag made `requiresClientFeatures` a MULTI-PRODUCER key -- features/scaling.py
   already emits it. `merge_slot_data`'s duplicate-key guard is right for every other key (two
   producers means one silently wins) but here it would have raised at gen time for any seed that
   enabled two tagged features at once. That is a failure that appears only in COMBINATION, which is
   the kind that reaches a player. So the merge unions this one key, and the union is what the
   second half of this file pins.

No AP import needed: contract.py and registry.py both carry standalone-import fallbacks.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(PKG, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


contract = _load("gf_contract_nrl", "contract.py")
registry = _load("gf_registry_nrl", "registry.py")


class _FakeFeature:
    def __init__(self, name, sd):
        self.name = name
        self._sd = sd

    def slot_data(self, world):
        return self._sd


def test_no_rune_loss_is_a_declared_options_subkey():
    key = contract.OPTIONS_BY_NAME.get("no_rune_loss")
    assert key is not None, "no_rune_loss must be declared in contract.OPTIONS_SUBKEYS"
    assert key.shape == "BOOL_OR_INT"
    assert contract.NO_RUNE_LOSS == "no_rune_loss"


def test_declaring_the_subkey_does_not_move_the_contract_hash():
    """The whole reason the requiresClientFeatures tag exists. If this ever fails, an options
    addition started forcing a client update for every seed and the tag is redundant."""
    assert "no_rune_loss" not in [k.name for k in contract.CONTRACT], (
        "no_rune_loss belongs in OPTIONS_SUBKEYS, not the top-level CONTRACT -- putting it in "
        "CONTRACT moves CONTRACT_HASH and forces a client update on every seed"
    )


def test_requires_client_features_unions_across_features():
    """THE MOTIVATING CASE: a seed with both scaling_ceiling and no_rune_loss must generate."""
    feats = [
        _FakeFeature("scaling", {contract.REQUIRES_CLIENT_FEATURES: ["scaling_ceiling"]}),
        _FakeFeature("deathlink", {contract.REQUIRES_CLIENT_FEATURES: ["no_rune_loss"]}),
    ]
    sd = registry.merge_slot_data({}, feats, None)
    assert sd[contract.REQUIRES_CLIENT_FEATURES] == ["no_rune_loss", "scaling_ceiling"]


def test_tag_union_is_sorted_and_deduped():
    """Stable wire value: the same seed must not produce a different ordering between gens."""
    feats = [_FakeFeature("b", {contract.REQUIRES_CLIENT_FEATURES: ["z", "a"]}),
             _FakeFeature("c", {contract.REQUIRES_CLIENT_FEATURES: ["a", "m"]})]
    sd = registry.merge_slot_data({contract.REQUIRES_CLIENT_FEATURES: ["m"]}, feats, None)
    assert sd[contract.REQUIRES_CLIENT_FEATURES] == ["a", "m", "z"]


def test_duplicate_guard_still_fires_for_every_other_key():
    """The union is a carve-out for ONE key, not a weakening of the guard. Mutation-test it: if the
    carve-out ever widens, this is what notices."""
    feats = [_FakeFeature("x", {contract.DEATH_LINK: False})]
    try:
        registry.merge_slot_data({contract.DEATH_LINK: True}, feats, None)
    except ValueError as e:
        assert "death_link" in str(e)
    else:
        raise AssertionError("duplicate-key guard did not fire for a non-tag key")
