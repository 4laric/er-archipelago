"""THE WORLD DECLARES ITS PROFILE, AND THE CONTRACT REFUSES FOREIGN KEYS (#1463).

The client used to choose between its two location-resolution paths -- the matt slot-key resolver
(`locationIdsToKeys`) and our `locationFlags` table -- by asking whether the matt key happened to be
present. A path chosen by sniffing is a path nobody validates: a seed carrying BOTH key families, or
NEITHER, takes whichever branch the sniff lands on, and the symptom is checks that never fire hours
into a run. So the world now says what it is, in one required key, and `validate_slot_data` refuses
an emission that contradicts it.

What this file guards, in the order it matters:

  1. `profile` is DECLARED (BOTH, required) and EMITTED -- a declaration nobody emits is worse than
     no declaration, because the client's bridge would read the absence as "old seed" forever.
  2. A greenfield slot_data carrying a BEDROCK-only key FAILS, and the message NAMES the key. The
     name is the whole point: "your apworld emitted a key from the other contract" is one grep to
     fix once you know which key, and unfindable otherwise.
  3. The same in the other direction, so the check is a rule and not a special case for one key.
  4. `dungeonSweeps` is no longer a greenfield key and is no longer emitted. It was tagged as
     greenfield-produced while boss_locks.py wrote `{}` into it for its whole life
     (RECON-contract-keys-20260706 filed it as a profile blemish); an always-empty dict reads
     identically to absent on the client, so the tag was describing an intention, not an emission.

Rule 8, applied here: what would make these pass while the bug is back? Only re-tagging the key as
greenfield, which is the change these tests exist to make someone argue for.

The contract half needs no Archipelago (contract.py imports nothing), so it loads by path and runs
anywhere; the emission half is a WorldTestBase suite and skips until the world is installed.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_profile_declaration.py
"""
import importlib.util
import os
import unittest

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONTRACT_PY = os.path.join(os.path.dirname(_HERE), "contract.py")

_spec = importlib.util.spec_from_file_location("_gf_contract_profile", _CONTRACT_PY)
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)

GAME = "Elden Ring"


def _minimal(profile):
    """The smallest slot_data that VALIDATES for `profile`, so a test's one added key is the only
    thing under examination. Built from the contract rather than typed out, so a newly-required key
    cannot leave these tests quietly asserting against a dict that fails for an unrelated reason."""
    sd = {}
    for key in contract.CONTRACT:
        if not (key.required and key.in_profile(profile)):
            continue
        if key.name == contract.PROFILE:
            sd[key.name] = profile
            continue
        if key.shape == "OPTIONS_DICT":
            sd[key.name] = {s.name: _SHAPE_SAMPLES[s.shape]
                            for s in key.subkeys if s.required and s.in_profile(profile)}
            continue
        sd[key.name] = _SHAPE_SAMPLES[key.shape]
    return sd


# One valid sample per shape a required key can have. Kept tiny and obvious; if a required key ever
# takes a shape that is not here, the KeyError names it rather than producing a mystery failure.
_SHAPE_SAMPLES = {
    "ANY": {},
    "SCALAR_INT_MAP": {},
    "LISTVAL_INT_MAP": {},
    "STR_MAP": {},
    "STR": "x",
    "STR_LIST": [],
    "INT": 0,
    "INT_LIST": [],
    "BOOL": False,
    "BOOL_OR_INT": 0,
    "INT_OR_BOOL": 0,
    "NUMBER": 0,
    "TRIPLE_LIST": [],
    "PAIR_LIST": [],
    "LOCK_PLACEMENTS": {},
    "NESTED_GRANTS": {},
    "FLASK_LADDER": [],
    # OPTIONS_DICT is filled from the key's own required sub-keys in `_minimal`, not from here.
}


class ProfileIsDeclared(unittest.TestCase):
    def test_profile_is_a_required_key_of_both_profiles(self):
        key = contract.BY_NAME.get("profile")
        self.assertIsNotNone(key, "the contract must declare `profile` (#1463)")
        self.assertTrue(key.required, "a profile nobody has to send is a profile nobody can trust")
        for p in (contract.GREENFIELD, contract.BEDROCK):
            self.assertTrue(key.in_profile(p), f"`profile` must belong to {p}")

    def test_the_module_constant_matches_the_wire_name(self):
        # Emitters go through contract.PROFILE, never a literal; this is the pin that makes that
        # indirection safe to rely on.
        self.assertEqual(contract.PROFILE, "profile")


class ForeignKeysAreRefused(unittest.TestCase):
    def _problems(self, sd, profile):
        return contract.validate_slot_data(sd, profile=profile, strict=False)

    def test_a_clean_greenfield_slot_data_has_no_profile_problems(self):
        # The control. Without it, a test below could "pass" because everything fails.
        problems = self._problems(_minimal(contract.GREENFIELD), contract.GREENFIELD)
        self.assertEqual([p for p in problems if "FOREIGN" in p], [])

    def test_greenfield_emitting_a_bedrock_key_fails_and_names_it(self):
        sd = _minimal(contract.GREENFIELD)
        sd["locationIdsToKeys"] = {"1": "1,0:0000000000::"}
        problems = [p for p in self._problems(sd, contract.GREENFIELD) if "FOREIGN" in p]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("locationIdsToKeys", problems[0])
        with self.assertRaises(contract.ContractError) as raised:
            contract.validate_slot_data(sd, profile=contract.GREENFIELD, strict=True)
        self.assertIn("locationIdsToKeys", str(raised.exception))

    def test_bedrock_emitting_a_greenfield_key_fails_and_names_it(self):
        sd = _minimal(contract.BEDROCK)
        sd["locationFlags"] = {}
        problems = [p for p in self._problems(sd, contract.BEDROCK) if "FOREIGN" in p]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("locationFlags", problems[0])

    def test_a_both_key_is_foreign_to_neither(self):
        # itemCounts is tagged BOTH; the check must not fire on a key both contracts share, or
        # every seed would fail and the rule would be reverted rather than fixed.
        self.assertIn(contract.BOTH, contract.BY_NAME["itemCounts"].profiles)
        for profile in (contract.GREENFIELD, contract.BEDROCK):
            sd = _minimal(profile)
            sd["itemCounts"] = {}
            self.assertEqual([p for p in self._problems(sd, profile) if "FOREIGN" in p], [])


class DungeonSweepsIsBedrockOnly(unittest.TestCase):
    def test_the_tag_says_what_is_true(self):
        key = contract.BY_NAME["dungeonSweeps"]
        self.assertEqual(key.profiles, (contract.BEDROCK,),
                         "greenfield never produced dungeonSweeps -- it wrote {} into it")
        self.assertNotIn("boss_locks", key.producer,
                         "the producer string must not name a greenfield module")

    def test_the_flag_keyed_sibling_is_untouched(self):
        # The live greenfield sweep wire. If this ever went bedrock-only too, sweeps would go dark.
        self.assertTrue(contract.BY_NAME["dungeonSweepFlags"].in_profile(contract.GREENFIELD))


# --------------------------------------------------------------------------------------------
# The EMISSION half: needs the world installed under Archipelago/worlds (gf_test.py's job).
# --------------------------------------------------------------------------------------------
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")


class ProfileIsEmitted(WorldTestBase):
    game = GAME
    options = {"dungeon_sweep": "all"}   # the option under which boss_locks.py used to emit {}

    def test_slot_data_declares_greenfield(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd.get("profile"), "greenfield")

    def test_slot_data_carries_no_bedrock_only_key(self):
        sd = self.world.fill_slot_data()
        foreign = sorted(
            name for name in sd
            if name in contract.BY_NAME
            and not contract.BY_NAME[name].in_profile(contract.GREENFIELD)
        )
        self.assertEqual(foreign, [], f"greenfield emitted foreign key(s): {foreign}")

    def test_dungeon_sweeps_is_not_emitted_even_with_sweeps_on(self):
        # The blemish itself: this is the option under which the empty dict used to be written.
        sd = self.world.fill_slot_data()
        self.assertNotIn("dungeonSweeps", sd)
        self.assertIn("dungeonSweepFlags", sd, "the live flag-keyed sweep wire must still be sent")
