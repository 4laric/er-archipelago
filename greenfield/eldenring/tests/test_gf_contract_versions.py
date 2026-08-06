"""The version <-> contract ledger is a RATCHET (CONTRIBUTING rule 15).

`tools/check_contract_version.py` is the gate that fires in CI. This file guards the
gate's one bypass: the ledger is a plain tsv, and the cheapest way to turn the gate
green is to edit the row for the current version instead of bumping. That edit would
erase the only record that two builds differ, so the historical rows are pinned here
as a literal fixture -- changing one in the tsv reddens the suite as well.

Rule 8 ("guard the right thing"), applied to this file: what would make these tests
pass while the bug is present? Only a change that edits BOTH the ledger and this
fixture in the same commit -- which is no longer a slip, it is a decision with a diff
a reviewer can see.

🛑 REPO-ONLY. These need `tools/` and `release/`, which `gf_test.py` does NOT copy
into the AP world dir, so under the `tests` job they skip (`find_repo_root` returns None).
The `generators` job is where they actually execute -- it has the real tree -- and it runs
them from the `for t in ...` loop alongside the other repo-tooling suites.

⚠️ CORRECTION 2026-08-03. This docstring briefly claimed the generators job "runs no
pytest at all, so a repo-only suite relying on it ran NOWHERE". **That was false**, and it
is the exact failure mode rule 10 names: a comment asserting a fact. The claim came from
grepping the workflow for `pytest` / `gf_test` and missing the multi-line shell loop, which
spells it `test_gf_$t.py`. The loop has run `client_resets_are_called` and friends since
2026-07-29. Re-derive before citing a CI fact -- `python3 -c "import yaml"` over the whole
`run:` block, not a substring search.

Run as a FILE, never as `-m greenfield.eldenring.tests...`: the package `__init__`
imports the world, which needs Archipelago, which the generators job does not have.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # invoked as a plain path, not as a package
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(_ROOT or "", "release", "CONTRACT-VERSIONS.tsv")
GATE = os.path.join(_ROOT or "", "tools", "check_contract_version.py")
CONTRACT_PY = os.path.join(_ROOT or "", "greenfield", "eldenring", "contract.py")

# Derived 2026-08-03 by loading contract.py at every tag:
#     python3 tools/check_contract_version.py --derive-history
# 🛑 A record of what SHIPPED. Do not "fix" a row to make something pass.
SHIPPED = {
    "0.2.0": "b3739fdf",
    "0.2.12": "8550ab05",
    "0.2.13": "8550ab05",
    "0.2.15": "d970dd88",
    "0.2.16": "d970dd88",
    "0.2.17": "d970dd88",
    "0.2.18": "d970dd88",
    "0.3.0": "5e8b11c9",
    "0.3.1": "5e8b11c9",
    "0.3.2": "5e8b11c9",
    # Added 2026-08-04, LATE: v0.3.3 was tagged on 08-03 and this row was not written, which is
    # the same missed release step as APWORLD_VERSION not moving off it. Both are now gated --
    # see test_every_tagged_version_is_recorded_as_shipped below and
    # check_release_notes.check_version_is_still_open.
    "0.3.3": "5e8b11c9",
    # Added 2026-08-04 when the v0.3.5 window was opened. v0.3.4 was tagged the same day and this
    # row was missed AGAIN -- the second time running. 🛑 CI CANNOT SEE THIS: the test asks the git
    # TAGS, and the workflow's checkout does not fetch them, so it silently finds no tags and
    # passes. It only went red in a local/sandbox clone that has them. Fetch-depth/tags is the
    # real fix; until then this row is written by hand at window-open, not at tag time.
    "0.3.4": "5e8b11c9",
    # Added 2026-08-06 at window-open, ON TIME for the first time -- and not by anyone
    # remembering. tests.yaml now sets fetch-tags/fetch-depth 0, so the test below finally
    # sees the tags it asks about; it went RED on the first PR to land past the v0.3.5 tag,
    # which is exactly what it was written to do. The gate, not a person, caught this one.
    "0.3.5": "5e8b11c9",
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


def _contract(path=None):
    spec = importlib.util.spec_from_file_location("_er_contract_test", path or CONTRACT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(_ROOT is not None, REPO_ONLY_REASON)
class ContractVersionLedger(unittest.TestCase):

    def test_shipped_contract_hashes_are_never_rewritten(self):
        """Every version that has shipped keeps the hash it shipped with."""
        rows = _ledger()
        for version, want in sorted(SHIPPED.items()):
            self.assertIn(version, rows,
                "version %s vanished from the ledger. Rows are append-only history; a version "
                "that shipped cannot stop having shipped." % version)
            self.assertEqual(rows[version], want,
                "the ledger row for %s was CHANGED from %s to %s.\n"
                "That row records the contract shape players actually received. Rewriting it does "
                "not make two builds compatible -- it deletes the evidence that they differ, which "
                "is the exact failure rule 15 exists to prevent." % (version, want, rows[version]))

    def test_current_version_owns_its_contract_hash(self):
        """The working tree's contract must match the row for the working tree's version."""
        mod = _contract()
        rows = _ledger()
        version, chash = mod.APWORLD_VERSION, mod.CONTRACT_HASH[:8]
        self.assertIn(version, rows,
            "APWORLD_VERSION is %s and the ledger has no row for it. Add "
            "`%s\t%s\t<why>` to release/CONTRACT-VERSIONS.tsv in the same commit as the bump."
            % (version, version, chash))
        self.assertEqual(rows[version], chash,
            "the contract moved under version %s: contract.py computes %s, the ledger says %s. "
            "Bump APWORLD_VERSION, or revert the contract change." % (version, chash, rows[version]))

    def test_gate_actually_goes_red_when_the_contract_moves(self):
        """Rule 7: a passing gate proves nothing until you have seen it fail.

        Runs the real gate against a temp copy whose contract has one extra key and no version
        bump, and asserts a NON-ZERO exit. If this ever passes, the gate has been talked into
        accepting the thing it exists to catch."""
        with tempfile.TemporaryDirectory() as td:
            for rel in ("tools", "release", os.path.join("greenfield", "eldenring")):
                dst = os.path.join(td, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copytree(os.path.join(_ROOT, rel), dst, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "tests"))
            victim = os.path.join(td, "greenfield", "eldenring", "contract.py")
            with open(victim, encoding="utf-8") as fh:
                src = fh.read()
            probe = ('    ContractKey("__gate_probe__", "INT", True, (GREENFIELD,), '
                     '"probe", "probe", "probe"),\n    ContractKey("fogWallDebug"')
            mutated = src.replace('    ContractKey("fogWallDebug"', probe, 1)
            # Rule 9: an edit whose pattern does not match must RAISE, not skip. If this fires,
            # the anchor key was renamed and this test is measuring nothing.
            self.assertNotEqual(mutated, src,
                'the probe anchor `ContractKey("fogWallDebug"` is gone from contract.py, so this '
                "test silently stopped mutating anything. Re-anchor it on a key that exists.")
            with open(victim, "w", encoding="utf-8") as fh:
                fh.write(mutated)
            # sanity: the mutation really does move the hash, or we are asserting on nothing
            self.assertNotEqual(_contract(victim).CONTRACT_HASH[:8], _contract().CONTRACT_HASH[:8],
                "the probe key did not change CONTRACT_HASH -- it landed outside CONTRACT (this "
                "exact mistake put the probe in OPTIONS_SUBKEYS on the first attempt).")
            rc = subprocess.call([sys.executable, os.path.join(td, "tools", "check_contract_version.py")],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 env={**os.environ, "NO_COLOR": "1"})
        self.assertEqual(rc, 1,
            "check_contract_version.py exited %s on a contract that gained a key with no version "
            "bump. It must exit 1. A gate that cannot go red is not a gate." % rc)

    def test_options_subkeys_blind_spot_is_still_real_and_still_documented(self):
        """The gate does NOT see OPTIONS_SUBKEYS changes, on purpose. Rule 10: a documented
        invariant needs a test that fails when it stops being true."""
        mod = _contract()
        self.assertTrue(hasattr(mod, "OPTIONS_SUBKEYS"), "OPTIONS_SUBKEYS was renamed or removed")
        names = {k.name for k in mod.CONTRACT}
        sub = {k.name for k in mod.OPTIONS_SUBKEYS}
        # NOT a disjointness claim -- measured 2026-08-03, five names legitimately appear in BOTH
        # (completion_scaling, completion_scaling_floor, death_link, enable_dlc,
        # no_weapon_requirements). The blind spot is the REMAINDER.
        self.assertTrue(sub - names,
            "every OPTIONS_SUBKEY now has a CONTRACT twin, so the blind spot may be closed. That is "
            "good news -- but tools/check_contract_version.py still tells readers subkeys are "
            "invisible to the hash. Re-measure, correct its docstring, then correct this test.")
        with open(GATE, encoding="utf-8") as fh:
            self.assertIn("OPTIONS_SUBKEYS is deliberately NOT folded", fh.read(),
                          "the gate stopped documenting its own blind spot")

    def test_every_tagged_version_is_recorded_as_shipped(self):
        """SHIPPED is a record of history, and history is written by the TAGS -- so ask them.

        v0.3.3 was tagged on 2026-08-03 and nobody added its row; it was noticed a day later only
        because someone happened to read this file. A ledger that depends on remembering to append
        to it is the thing rule 13 is about: it is a to-do list until something checks it.

        ⚠️ LOUD SKIP. Tags are not present in a shallow checkout, and a check that cannot answer must
        say so rather than pass quietly (rule 2). It warns; it never asserts on evidence it does not
        have.
        """
        import warnings
        if not _ROOT:
            self.skipTest(REPO_ONLY_REASON)
        try:
            out = subprocess.run(["git", "tag", "--list", "v*"], cwd=_ROOT,
                                 capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError) as exc:
            warnings.warn("[contract-versions] UNCHECKED: git unavailable (%s)" % exc)
            return
        tags = [t.strip().lstrip("v") for t in out.stdout.splitlines() if t.strip()]
        if not tags:
            warnings.warn("[contract-versions] UNCHECKED: no v* tags in this checkout (shallow "
                          "clone?) -- the tagged-version screen did NOT run")
            return
        ledger = _ledger()
        missing = sorted(t for t in tags if t in ledger and t not in SHIPPED)
        self.assertEqual([], missing,
                         "these versions are TAGGED (so they shipped) and carry a ledger row, but "
                         "have no SHIPPED entry: %s. Add each with the hash its ledger row records "
                         "-- that is what makes the ledger un-rewritable." % missing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
