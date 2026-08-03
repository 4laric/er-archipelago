"""The version <-> contract ledger is a RATCHET (CONTRIBUTING rule 15).

`tools/check_contract_version.py` is the gate that fires in CI. This file guards the
gate's one bypass: the ledger is a plain tsv, and the cheapest way to turn the gate
green is to edit the row for the current version instead of bumping. That edit would
erase the only record that two builds differ, so the historical rows are pinned here
as a literal fixture -- changing one in the tsv reddens the suite as well.

Rule 8 ("guard the right thing"), applied to this file: what would make these tests
pass while the bug is present? Only a change that edits BOTH the ledger and this
fixture in the same commit -- which is no longer a slip, it is a decision with a diff
a reviewer can see. That is the whole ambition.
"""
import importlib.util
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LEDGER = os.path.join(REPO, "release-v0.2", "CONTRACT-VERSIONS.tsv")
GATE = os.path.join(REPO, "tools", "check_contract_version.py")
CONTRACT_PY = os.path.join(REPO, "greenfield", "eldenring", "contract.py")

# Derived 2026-08-03 by loading contract.py at every tag:
#     python3 tools/check_contract_version.py --derive-history
# 🛑 These are a record of what SHIPPED. Do not "fix" a row to make something pass.
SHIPPED = {
    "0.2.0":  "b3739fdf",
    "0.2.12": "8550ab05",
    "0.2.13": "8550ab05",
    "0.2.15": "d970dd88",
    "0.2.16": "d970dd88",
    "0.2.17": "d970dd88",
    "0.2.18": "d970dd88",
    "0.3.0":  "5e8b11c9",
    "0.3.1":  "5e8b11c9",
}


def _ledger():
    rows = {}
    with open(LEDGER, encoding="utf-8") as fh:
        for line in fh:
            s = line.rstrip("\n")
            if not s.strip() or s.lstrip().startswith("#"):
                continue
            parts = s.split("\t")
            rows[parts[0].strip()] = parts[1].strip()
    return rows


def _contract():
    spec = importlib.util.spec_from_file_location("_er_contract_test", CONTRACT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_shipped_contract_hashes_are_never_rewritten():
    """Every version that has shipped keeps the hash it shipped with."""
    rows = _ledger()
    for version, want in sorted(SHIPPED.items()):
        assert version in rows, (
            "version %s vanished from the ledger. Rows are append-only history; a version "
            "that shipped cannot stop having shipped." % version)
        assert rows[version] == want, (
            "the ledger row for %s was CHANGED from %s to %s.\n"
            "That row records the contract shape players actually received. Rewriting it "
            "does not make two builds compatible -- it deletes the evidence that they "
            "differ, which is the exact failure rule 15 exists to prevent." % (version, want, rows[version]))


def test_current_version_owns_its_contract_hash():
    """The motivating case, end to end (rule 11): the working tree's contract must match
    the row for the working tree's version."""
    mod = _contract()
    rows = _ledger()
    version, chash = mod.APWORLD_VERSION, mod.CONTRACT_HASH[:8]
    assert version in rows, (
        "APWORLD_VERSION is %s and the ledger has no row for it. Add "
        "`%s\t%s\t<why>` to release-v0.2/CONTRACT-VERSIONS.tsv in the same commit as the "
        "bump." % (version, version, chash))
    assert rows[version] == chash, (
        "the contract moved under version %s: contract.py computes %s, the ledger says %s. "
        "Bump APWORLD_VERSION, or revert the contract change." % (version, chash, rows[version]))


def test_gate_actually_goes_red_when_the_contract_moves():
    """Rule 7: a passing gate proves nothing until you have seen it fail.

    Runs the real gate against a temp checkout whose contract has one extra key and no
    version bump, and asserts a NON-ZERO exit. If this ever passes, the gate has been
    talked into accepting the thing it exists to catch."""
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        for rel in ("tools", "release-v0.2", os.path.join("greenfield", "eldenring")):
            src = os.path.join(REPO, rel)
            dst = os.path.join(td, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "tests"))
        victim = os.path.join(td, "greenfield", "eldenring", "contract.py")
        src = open(victim, encoding="utf-8").read()
        probe = ('    ContractKey("__gate_probe__", "INT", True, (GREENFIELD,), '
                 '"probe", "probe", "probe"),\n    ContractKey("fogWallDebug"')
        mutated = src.replace('    ContractKey("fogWallDebug"', probe, 1)
        # Rule 9: an edit whose pattern does not match must RAISE, not skip. If this
        # fires, the anchor key was renamed and this test is measuring nothing.
        assert mutated != src, (
            "the probe anchor `ContractKey(\"fogWallDebug\"` is gone from contract.py, so "
            "this test silently stopped mutating anything. Re-anchor it on a key that exists.")
        open(victim, "w", encoding="utf-8").write(mutated)
        rc = subprocess.call([sys.executable, os.path.join(td, "tools", "check_contract_version.py")],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             env={**os.environ, "NO_COLOR": "1"})
    assert rc == 1, (
        "check_contract_version.py exited %s on a contract that gained a key with no "
        "version bump. It must exit 1. A gate that cannot go red is not a gate." % rc)


def test_options_subkeys_blind_spot_is_still_real_and_still_documented():
    """The gate does NOT see OPTIONS_SUBKEYS changes, on purpose (contract.py explains
    why: an absent subkey parses false on an older client). That is a blind spot, and
    rule 10 says a documented invariant needs a test that fails when it stops being
    true. If someone folds OPTIONS_SUBKEYS into CONTRACT_HASH, this test reds and the
    gate's docstring must be corrected -- rather than quietly becoming wrong."""
    mod = _contract()
    assert hasattr(mod, "OPTIONS_SUBKEYS"), "OPTIONS_SUBKEYS was renamed or removed"
    names = {k.name for k in mod.CONTRACT}
    sub = {k.name for k in mod.OPTIONS_SUBKEYS}
    # NOT a disjointness claim -- measured 2026-08-03, five names legitimately appear in
    # BOTH (completion_scaling, completion_scaling_floor, death_link, enable_dlc,
    # no_weapon_requirements), because they are echoed as top-level contract keys as well.
    # The blind spot is the REMAINDER: subkeys with no CONTRACT twin contribute nothing to
    # CONTRACT_HASH, so changing one is invisible to the gate.
    outside = sub - names
    assert outside, (
        "every OPTIONS_SUBKEY now has a CONTRACT twin, so the blind spot may be closed. "
        "That is good news -- but tools/check_contract_version.py still tells readers that "
        "subkeys are invisible to the hash. Re-measure, correct its docstring, then correct "
        "this test.")
    with open(GATE, encoding="utf-8") as fh:
        assert "OPTIONS_SUBKEYS is deliberately NOT folded" in fh.read(), (
            "the gate stopped documenting its own blind spot")
