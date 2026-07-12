"""A FOREIGN APWORLD MUST YIELD A PLAYABLE VANILLA SEED -- NOT AN ERROR.

Our client is the only Elden Ring client in the fswap lineage. Bedrock's apworld
(fswap/archipelago@er) has none -- his `_todo.txt` still says `TODO / merge client stuff` and the
link is dead. So the client will be asked to drive a world that emits NONE of our keys, and Alaric
promised him, in writing (2026-07-06):

    "2 are specific to my .apworld (startRegion, regionOpenFlags). When these arguments aren't
     present, they fall back to vanilla behaviour."

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
    "goalLocations": [7770875, 7770876, 7770885],
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
        both_required = [
            k.name for k in contract.CONTRACT
            if k.required and contract.BOTH in k.profiles
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
        """The whole point: his slot_data must pass OUR validator under the bedrock profile."""
        problems = contract.validate_slot_data(
            BEDROCK_SHAPED_SLOT_DATA, profile=contract.BEDROCK, strict=False)
        self.assertFalse(
            problems,
            f"a foreign apworld's slot_data does not validate: {problems}. It must, or we are telling "
            f"players their seed is broken when it is our contract that is wrong.")
