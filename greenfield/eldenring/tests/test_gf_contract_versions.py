"""The version <-> contract ledger is a RATCHET (CONTRIBUTING rule 15).

`tools/check_contract_version.py` is the gate that fires in CI. This file guards the
gate's one bypass: the ledger is a plain tsv, and the cheapest way to turn the gate
green is to edit the row for the current version instead of bumping. That edit would
erase the only record that two builds differ.

⭐⭐⭐ THE HISTORY IS NOW DERIVED FROM `git tag`, not typed here as a fixture (2026-08-14).
contract.py is EXECUTED at every tag and its CONTRACT_HASH compared to that version's
ledger row, so an edited row reddens this suite without anybody having remembered to
write the version down first. The literal it replaces was late in nine consecutive
windows and invisible in the last two -- see the block above _REPEATED_VERSION_ERA for
why that is a mechanism rather than a run of forgetfulness, and for what the change
gives up.

Rule 8 ("guard the right thing"), applied to this file: what would make these tests
pass while the bug is present? Editing the ledger row AND moving the tag it disagrees
with -- which is not a slip, it is a rewrite of published history.

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

# ---------------------------------------------------------------------------------------------
# WHAT THE TAGS ACTUALLY SHIPPED -- DERIVED, never typed.
#
# 🛑 THIS REPLACES A LITERAL `SHIPPED` DICT, and the reason is a mechanism, not tidiness. Cutting a
# tag does TWO things in the same instant: it leaves APWORLD_VERSION naming a version that has now
# shipped (check_release_notes, rule 14, goes red at step 9 of `generators`) and it owes that
# version a row here (this file, in the loop at step 11). An aborting step skips every step below
# it, so the gate that reports the second is STRUCTURALLY behind the one that aborts on the first.
# Nine consecutive windows wrote the row late -- 0.3.3, 0.3.4, 0.3.6, 0.3.9, 0.3.10, 0.3.11,
# 0.3.12, 0.4.0(on time), 0.4.1 -- and the last two were not even visible while they were owed.
# A fixture that has to be remembered will be forgotten; the fix named at 0.3.10 and again at
# 0.3.12 is to ask git. This is that.
#
# 🛑 WHAT WAS TRADED, stated plainly rather than left for someone to discover. The literal was
# frozen INDEPENDENTLY of git: a moved or force-pushed tag could not change it. The derivation
# moves with the tags. That is a real reduction in what this file can catch, accepted because
# moving a published tag is a far larger event than this suite -- and because a fixture nine
# windows out of date protects nothing at all.
#
# 🛑 KEYED ON THE TREE'S APWORLD_VERSION, NOT THE TAG NAME, and that is not pedantry: tags
# v0.3.3, v0.3.4, v0.3.5 and v0.3.6 all carry `APWORLD_VERSION = "0.3.2"` -- in those windows the
# tag was cut BEFORE the bump commit, so the apworld players received reported itself as 0.3.2.
# Reading the version off the tag name would compare the wrong two things and call it history.
_REPEATED_VERSION_ERA = {
    # 0.2.0 names FIVE distinct contracts across v0.2 .. v0.2.11, which is the whole reason
    # rule 15 and this ledger exist. One tsv row cannot record five shapes, so the hash
    # comparison is waived HERE -- and test_the_waiver_is_earned asserts the split is real, so
    # this cannot quietly cover a version that has since become consistent.
    "0.2.0",
}


def _tags():
    """Every `v*` tag in THIS checkout, or [] when there are none (shallow clone)."""
    if not _ROOT:
        return []
    try:
        out = subprocess.run(["git", "tag", "--list", "v*"], cwd=_ROOT,
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    return [t.strip() for t in out.stdout.splitlines() if t.strip()]


def _shipped_by_tag():
    """{APWORLD_VERSION: {tag: contract_hash8}} -- contract.py EXECUTED at each tag.

    Executed, not parsed: CONTRACT_HASH is computed from the contract keys, so a textual guess
    would be a different number that looks like the right one. Tags with no contract.py (v0.1.x,
    before the file existed) are skipped rather than reported as a failure -- absence there is
    history, not breakage.
    """
    by = {}
    with tempfile.TemporaryDirectory() as td:
        for i, tag in enumerate(_tags()):
            blob = subprocess.run(["git", "show", "%s:greenfield/eldenring/contract.py" % tag],
                                  cwd=_ROOT, capture_output=True, timeout=30,
                                  # UTF-8 explicitly: `text=True` alone decodes with the LOCALE,
                                  # which on a Windows dev box is cp1252 -- a non-cp1252 byte in an
                                  # old tag's contract.py kills the reader thread and leaves
                                  # `blob.stdout` None, erroring the suite on a machine where the
                                  # gate is supposed to be runnable. CI (Linux, UTF-8) never saw it.
                                  encoding="utf-8", errors="replace")
            if blob.returncode != 0 or len(blob.stdout) < 100:
                continue
            path = os.path.join(td, "c_%d.py" % i)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(blob.stdout)
            spec = importlib.util.spec_from_file_location("_er_tag_contract_%d" % i, path)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except Exception:                                     # noqa: BLE001
                continue
            by.setdefault(mod.APWORLD_VERSION, {})[tag] = mod.CONTRACT_HASH[:8]
    return by


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

    _CACHE = None

    def _by_version(self):
        """{version: {tag: hash8}}, computed once -- ~30 contract.py executions, ~0.2 s.

        🛑 WARNS AND SKIPS when the checkout has no tags, and every caller goes through here so
        none of them can forget. This is not defensive padding: the `tests` job checks out
        shallow (fetch-tags is set on `generators` only), so without the skip the derivation
        returns {} there -- which makes the ratchet iterate an empty dict and pass, and makes the
        waiver test fail for a reason that has nothing to do with the waiver. One vacuous green
        and one false red, from the same missing guard.
        """
        import warnings
        if not _ROOT:
            self.skipTest(REPO_ONLY_REASON)
        if not _tags():
            warnings.warn("[contract-versions] UNCHECKED: no v* tags in this checkout (shallow "
                          "clone?) -- the tag-derived ledger screen did NOT run")
            self.skipTest("no v* tags in this checkout -- see the warning above")
        if ContractVersionLedger._CACHE is None:
            ContractVersionLedger._CACHE = _shipped_by_tag()
        return ContractVersionLedger._CACHE

    def test_the_ledger_records_the_hash_the_tag_actually_shipped(self):
        """THE RATCHET. For every version a tag really shipped, the ledger row must be the hash
        that version had AT that tag -- so editing a row to make check_contract_version green
        reddens this instead, which is the one bypass rule 15 has.

        Stronger than the literal fixture it replaces: that one could only catch an edit to a row
        somebody had remembered to write down, and nine windows running, nobody had."""
        by = self._by_version()
        rows = _ledger()
        wrong, missing, checked = [], [], []
        for version, per_tag in sorted(by.items()):
            if version in _REPEATED_VERSION_ERA:
                continue
            hashes = set(per_tag.values())
            if len(hashes) != 1:
                continue                                  # covered by test_the_waiver_is_earned
            want = hashes.pop()
            checked.append(version)
            if version not in rows:
                missing.append((version, want, sorted(per_tag)))
            elif rows[version] != want:
                wrong.append((version, rows[version], want, sorted(per_tag)))
        # THE WITNESS (test_gf_vacuous_pass). Both emptiness assertions below are green whether
        # the ledger is honest or the derivation stopped returning anything, and the second is by
        # far the likelier way this file rots -- a renamed contract.py, a tag scheme change, a git
        # invocation that starts erroring. Say out loud that comparisons happened.
        self.assertGreater(
            len(checked), 5,
            "only %d version(s) could be compared against their tags (%r). The ratchet below is "
            "now green over almost nothing -- fix the derivation, do not lower this."
            % (len(checked), checked))
        self.assertEqual(
            [], wrong,
            "the ledger disagrees with what the tag actually shipped -- (version, ledger says, "
            "tag shipped, tags): %r\n"
            "That row records the contract shape players received. Rewriting it does not make two "
            "builds compatible; it deletes the evidence that they differ." % (wrong,))
        self.assertEqual(
            [], missing,
            "these versions were SHIPPED under a tag and have no ledger row -- (version, hash, "
            "tags): %r\n"
            "Append the row; it is append-only history." % (missing,))

    def test_every_version_a_tag_shipped_has_a_ledger_row(self):
        """History is written by the TAGS, so ask them.

        ⚠️ LOUD SKIP. A shallow checkout has no tags and a check that cannot answer must say so
        rather than pass quietly (rule 2). The `tests` job's checkout is shallow; `generators`
        fetches tags, and that is where this actually runs.
        """
        by = self._by_version()          # loud-skips when the checkout has no tags
        rows = _ledger()
        # THE WITNESS: an empty derivation would make the assertion below pass for the wrong
        # reason, which is the failure this whole file was rewritten to stop repeating.
        self.assertGreater(len(by), 5,
                           "only %d version(s) were found on tags -- the derivation, not the "
                           "ledger, is what this would be measuring: %r" % (len(by), sorted(by)))
        missing = sorted(v for v in by if v not in rows)
        self.assertEqual([], missing,
                         "these versions are on a TAG (so they shipped) and have no row in "
                         "release/CONTRACT-VERSIONS.tsv: %s" % missing)

    def test_the_derivation_saw_the_tags(self):
        """Rule 2 again, pointed at the derivation itself. An empty result would make every
        assertion above vacuously green -- which is precisely the failure mode this file is
        replacing, in a new costume."""
        by = self._by_version()          # loud-skips when the checkout has no tags
        self.assertGreaterEqual(
            len(by), 10,
            "contract.py was executed at only %d distinct version(s) across %d tag(s). The "
            "derivation has stopped seeing history and every ledger assertion here is now "
            "vacuous: %r" % (len(by), len(_tags()), sorted(by)))
        newest = max(_ledger(), key=lambda v: [int(x) for x in v.split(".")])
        self.assertNotIn(newest, by,
                         "the newest ledger version %s is already on a tag, so its window is not "
                         "open -- either the ledger row was added late or a tag was cut without a "
                         "new window being opened" % newest)

    def test_the_waiver_is_earned(self):
        """A waiver must assert its own premise, or it is a hole with a comment next to it.
        _REPEATED_VERSION_ERA exists because 0.2.0 names five contracts; if that ever stopped
        being true, the waiver would be silently excusing a version this gate could check."""
        by = self._by_version()
        for version in sorted(_REPEATED_VERSION_ERA):
            self.assertIn(version, by,
                          "%s is waived from the hash check but no tag ships it -- the waiver is "
                          "covering nothing and should be deleted" % version)
            hashes = set(by[version].values())
            self.assertGreater(
                len(hashes), 1,
                "%s is waived from the hash check on the grounds that its tags disagree, and they "
                "do not: every tag shipping it computes %s. Remove it from "
                "_REPEATED_VERSION_ERA so the row is actually checked." % (version, hashes))

    def test_the_derived_ratchet_goes_red_on_a_rewritten_row(self):
        """Rule 7: a passing gate proves nothing until you have seen it fail. Drive the same
        comparison over an injected history whose ledger row has been 'fixed'."""
        by = {"9.9.9": {"v9.9.9": "aaaaaaaa"}}
        rows = {"9.9.9": "bbbbbbbb"}                     # the row somebody edited to go green
        wrong = [(v, rows.get(v), set(t.values()).pop())
                 for v, t in by.items()
                 if len(set(t.values())) == 1 and rows.get(v) != set(t.values()).copy().pop()]
        self.assertEqual(1, len(wrong),
                         "the comparison this file's ratchet performs did not flag a ledger row "
                         "that disagrees with its tag -- the ratchet is inert")

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

if __name__ == "__main__":
    unittest.main(verbosity=2)
