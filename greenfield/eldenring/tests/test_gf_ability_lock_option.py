"""locked_abilities option (#945) -- the apworld half is ONE OptionSet echoed into slot_data.

A locked ability is not an item and gates no check, so there is nothing to place: these tests guard
the OPTION and its EMISSION, not a pool. They cover the AP-free contract facts (the subkey exists,
is STR_LIST, and is NOT folded into CONTRACT_HASH so it forces no version pairing), the option's
shape (valid_keys == contract.ABILITY_LOCK_KEYS, default empty), that it is filed under a wizard
group, and that fill_slot_data emits options.locked_abilities as a SORTED name list that a client
would fold -- empty by default, the selected set when chosen, and always contract-valid.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"


# ---- AP-free contract facts (no world needed) -----------------------------------------------
def test_subkey_is_str_list_and_hash_stable():
    key = contract.OPTIONS_BY_NAME["locked_abilities"]
    assert key.shape == "STR_LIST"
    assert key.required is False, "absent must be legal -> empty set -> off"
    # OPTIONS_SUBKEYS are deliberately excluded from CONTRACT_HASH: adding this option moves no hash.
    assert "locked_abilities" not in contract.BY_NAME, "must be an OPTIONS subkey, not a top-level key"
    assert contract.LOCKED_ABILITIES == "locked_abilities"


def test_valid_names_match_the_authoritative_list():
    from worlds.eldenring.features.ability_lock import LockedAbilities
    assert LockedAbilities.valid_keys == frozenset(contract.ABILITY_LOCK_KEYS)
    assert set(LockedAbilities.default) == set()
    # the seven the client's er_logic Ability enum knows -- heal is deliberately absent
    assert set(contract.ABILITY_LOCK_KEYS) == {"jump", "crouch", "roll", "r1", "r2", "l1", "l2"}


def test_option_is_filed_under_a_wizard_group():
    from worlds.eldenring import core
    grouped = {k for entry in core._OPTION_GROUPS for k in entry[1]}
    assert "locked_abilities" in grouped, "an ungrouped visible option lands in the Advanced bucket"


# ---- emission (needs a built world) ----------------------------------------------------------
class AbilityLockOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_default_emits_empty_sorted_list(self):
        sd = self.world.fill_slot_data()
        assert contract.LOCKED_ABILITIES in sd["options"], "must ride the options sub-dict"
        assert sd["options"][contract.LOCKED_ABILITIES] == []
        contract.validate_slot_data(sd, strict=True)  # STR_LIST accepts the empty list


class AbilityLockOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "locked_abilities": ["roll", "r1", "jump"]}

    def test_selected_set_emits_sorted_names(self):
        sd = self.world.fill_slot_data()
        got = sd["options"][contract.LOCKED_ABILITIES]
        assert got == sorted(["roll", "r1", "jump"]), got
        assert got == sorted(got), "emitted sorted so the wire is stable across runs"
        contract.validate_slot_data(sd, strict=True)
