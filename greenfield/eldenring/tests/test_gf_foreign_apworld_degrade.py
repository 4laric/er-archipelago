"""A FOREIGN APWORLD MUST YIELD A PLAYABLE VANILLA SEED -- NOT AN ERROR.

Our client is the only Elden Ring client in the fswap lineage. Bedrock's apworld
(fswap/archipelago@er) has none -- his `_todo.txt` still says `TODO / merge client stuff` and the
link is dead. So the client will be asked to drive a world that emits NONE of our keys, and Alaric
promised him, in writing (2026-07-06):

    "2 are specific to my .apworld (startRegion, regionOpenFlags). When these arguments aren't
     present, they fall back to vanilla behaviour."

PROVENANCE-OK: the one location key below is SYNTHETIC -- it encodes the foreign key GRAMMAR so
the degrade path can be tested, and contains no data from any other project. See PROVENANCE.md.

THIS FILE IS THAT PROMISE. Its Rust half lives in the client:
`region.rs::foreign_apworld_degrade` + `fogwall.rs::foreign_apworld_degrade`.

The contract used to CONTRADICT the promise: `locationFlags`, `regionOpenFlags` and `startRegion`
were all `required=True` in the BOTH profile -- i.e. we demanded a foreign apworld emit three keys
it does not have and cannot be asked to add (he emits `locationIdsToKeys`; key_resolver.rs derives
the flag from token 1 of the matt slot key). Moved to GREENFIELD-only, where they belong.
"""
import unittest

from .. import contract

# EXACTLY what Bedrock's fill_slot_data emits, per his own message (2026-07-06) and the shape of
# fswap/archipelago@er. Deliberately hand-written, NOT copied from his repo: we do not ingest his
# data (his location table is matt's itemslots.yaml). This is a SHAPE fixture, not his content.
BEDROCK_SHAPED_SLOT_DATA = {
    "apIdsToItemIds": {"7770001": 1073750026},
    "locationIdsToKeys": {"7770001": "301200,0:0000520110::"},
    "goalLocations": [7770874, 7770875, 7770884],
    "itemCounts": {"7770001": 1},
}


class TestForeignApworldDegrades(unittest.TestCase):

    def test_no_greenfield_only_key_is_required_of_a_foreign_apworld(self):
        """Anything only WE produce must never be required in the bedrock profile."""
        offenders = [
            k.name for k in contract.CONTRACT
            if k.required and k.in_profile(contract.BEDROCK) and not k.in_profile(contract.GREENFIELD)
        ]
        # (that set is bedrock-only keys, which he does emit -- fine.) The real trap is the reverse:
        # ONE DOCUMENTED EXEMPTION, and it is an ASK rather than an assumption (#1463). `profile`
        # is required of both contracts because the whole point of it is that a seed SAYS which one
        # it speaks -- a declaration only our side sends is a declaration the client can never rely
        # on. A foreign apworld does not send it yet, and we do not strand it for that: the client
        # reads an absent `profile` as "seed predates the declaration" and falls back to the
        # key-presence sniff this replaces, warning once (eldenring-archipelago/src/profile.rs).
        # 🛑 That is the ONLY thing that makes this exemption legitimate. If the bridge is ever
        # removed, this exemption becomes the lie the rest of this file exists to prevent, and the
        # key must move to GREENFIELD in the same change.
        _BRIDGED_BY_THE_CLIENT = {"profile"}
        both_required = [
            k.name for k in contract.CONTRACT
            if k.required and contract.BOTH in k.profiles and k.name not in _BRIDGED_BY_THE_CLIENT
        ]
        for name in both_required:
            self.assertIn(
                name, BEDROCK_SHAPED_SLOT_DATA,
                f"contract requires {name!r} of EVERY apworld, but a foreign world does not emit it. "
                f"Either it is not really required of foreigners (move it to GREENFIELD), or our "
                f"client cannot drive anyone else's world -- which is a promise we already broke once.")

    def test_the_region_lock_keys_are_ours_alone(self):
        """The three that contradicted the promise. Regression guard."""
        for name in ("regionOpenFlags", "startRegion", "locationFlags"):
            key = contract.BY_NAME[name]
            self.assertNotIn(
                contract.BOTH, key.profiles,
                f"{name!r} is back in the BOTH profile. A foreign apworld does not emit it: it has no "
                f"region lock (Bedrock's is an unbuilt wishlist) and it detects checks from "
                f"locationIdsToKeys, not locationFlags. Requiring it of everyone is how we quietly "
                f"stop being able to drive their world.")

    def test_a_bedrock_shaped_slot_data_validates(self):
        """The whole point: his slot_data must pass OUR validator under the bedrock profile.

        Since #1463 the observed fixture falls short of the contract by EXACTLY ONE key -- the
        `profile` declaration he does not send yet -- and that gap is asserted by name below rather
        than tolerated by a loosened assertion. Declare it on his behalf and everything else he
        emits validates unchanged, which is the claim this test has always made."""
        problems = contract.validate_slot_data(
            BEDROCK_SHAPED_SLOT_DATA, profile=contract.BEDROCK, strict=False)
        self.assertEqual(
            problems, ["MISSING required key 'profile' (producer core._base_slot_data)"],
            f"a foreign apworld's slot_data does not validate: {problems}. It must -- apart from the "
            f"one declaration we are asking foreign worlds to adopt, and which our client bridges "
            f"when it is absent -- or we are telling players their seed is broken when it is our "
            f"contract that is wrong.")

        declared = dict(BEDROCK_SHAPED_SLOT_DATA, profile=contract.BEDROCK)
        self.assertFalse(
            contract.validate_slot_data(declared, profile=contract.BEDROCK, strict=False),
            "a foreign apworld that DOES declare its profile must validate with nothing left over: "
            "the declaration is the only thing we are asking of it.")

    def test_a_foreign_apworld_emitting_one_of_our_keys_is_named(self):
        """The other direction of the same rule (#1463): a bedrock seed carrying a greenfield-only
        key is a seed the client would have resolved down the wrong path, so it fails and the key is
        NAMED. Unnamed, the report is 'contract violation' and the fix is a diff of two contracts."""
        sd = dict(BEDROCK_SHAPED_SLOT_DATA, profile=contract.BEDROCK, locationFlags={})
        problems = contract.validate_slot_data(sd, profile=contract.BEDROCK, strict=False)
        self.assertTrue(any("FOREIGN" in p and "locationFlags" in p for p in problems), problems)
