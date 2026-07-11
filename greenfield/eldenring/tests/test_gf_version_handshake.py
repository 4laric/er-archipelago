"""VERSION HANDSHAKE gate (tier A).

The apworld and the client .dll ship as SEPARATE artifacts -- the apworld off-site, the .dll on
Nexus -- so a player running a mismatched pair is the NORM, not an edge case. A stale .dll against a
fresh apworld looks exactly like a bug in the game, and without a handshake half of a tester round's
reports are version noise that cannot be triaged.

This is not hypothetical: on 2026-07-11 the shipped `me3/eldenring_archipelago.dll` still announced
"Elden Ring (Greenfield)" after the world had been renamed to "Elden Ring" -- the source and the
submodule pointer were both correct, only the BUILT ARTIFACT was stale. Shipped bytes != f(inputs),
the same class the gen-input stamp gate exists to kill on the generation side.

The wire: slot_data["versions"] = "apworld/<semver> contract/<hash8> data/<inputs_hash16>".
  * contract/<hash8> is DERIVED FROM THE CONTRACT (contract.CONTRACT_HASH) -- add, remove, reshape or
    flip the required-ness of any key and it changes by itself. A hand-bumped version is a thing people
    forget; a derived one cannot go stale.
  * The client compares it to the value baked into contract_gen.rs at COMPILE time and logs
    VERSION MISMATCH loudly if they differ.
  * data/<hash> is the gen-input hash of the generated data the seed was built from, so a report
    names the exact data, not just the code.
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)


def _mod(name):
    spec = importlib.util.spec_from_file_location("_v_" + name, os.path.join(GF_PKG, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


contract = _mod("contract")

_WIRE = re.compile(r"^apworld/\S+ contract/[0-9a-f]{8} data/\S+$")


class VersionHandshake(unittest.TestCase):
    def test_versions_is_required(self):
        key = [k for k in contract.CONTRACT if k.name == "versions"]
        self.assertTrue(key, "the `versions` key must exist in the contract")
        self.assertTrue(key[0].required,
                        "`versions` must be REQUIRED -- the failure it catches (a stale client) is "
                        "silent, so the key must never be optionally absent")

    def test_version_string_shape(self):
        v = contract.version_string("sha256:0123456789abcdef0123")
        self.assertRegex(v, _WIRE, f"version wire has the wrong shape: {v!r}")
        self.assertIn(contract.CONTRACT_HASH[:8], v)
        self.assertIn("0123456789abcdef", v, "the generated-data hash must ride in the wire")

    def test_contract_hash_is_derived_not_typed(self):
        """It must change when the contract changes -- otherwise it is a version number someone forgets."""
        before = contract.CONTRACT_HASH
        original = contract.CONTRACT
        try:
            contract.CONTRACT = tuple(original) + (
                contract.ContractKey("zz_probe", "STR", False, (contract.GREENFIELD,), "p", "p", "p"),)
            after = contract._contract_hash()
        finally:
            contract.CONTRACT = original
        self.assertNotEqual(before, after,
                            "CONTRACT_HASH did not change when a key was added -- it is not derived "
                            "from the contract, so it will go stale")

    def test_rust_mirror_carries_the_hash(self):
        """contract_gen.rs must bake the hash in, or the client has nothing to compare against."""
        rs = contract.to_rust()
        self.assertIn('pub const CONTRACT_HASH', rs)
        self.assertIn(contract.CONTRACT_HASH[:8], rs,
                      "the Rust mirror's CONTRACT_HASH must match the Python contract's")


if __name__ == "__main__":
    unittest.main(verbosity=2)
