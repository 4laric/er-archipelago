"""Release-pairing gate -- tools/check_release_pairing.py.

MOTIVATING CASE (Rule 11): v0.3.11. The tag pinned client `a9830ebe` while the client tree that
was actually packaged -- and client main -- were at `19825995`. Nothing refused to build the zip.

🛑 The thing this test exists to keep straight, because two reviewers have now got it backwards in
writing: v0.3.11's BUNDLE WAS CURRENT. `package_release.ps1` packages the client working TREE, not
the gitlink, so players got the right dll. What was wrong was the RECORD -- and a record that
disagrees with its artifact means no bug report against that tag can ever be resolved to a client
commit. So the case below is PIN != TREE with a CURRENT tree and a CURRENT dll: everything a player
touches is right, and the gate must still refuse, because the unrecoverable thing is the pairing.

The checker is a pure function over five gathered strings precisely so this test can pin the
v0.3.11 triple without a repo, a network or an 8 MB dll on disk.

AP-FREE: imports one stdlib-only tool by path. Runs in the bare sandbox.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_release_pairing.py
"""
import importlib.util
import os
import sys
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None

_MOD = None
if RUNNING_FROM_REPO:
    _PATH = os.path.join(_FOUND, "tools", "check_release_pairing.py")
    if os.path.isfile(_PATH):
        _spec = importlib.util.spec_from_file_location("check_release_pairing", _PATH)
        _MOD = importlib.util.module_from_spec(_spec)
        # Register BEFORE exec: @dataclass resolves annotations through sys.modules, so a
        # by-path import that skips this dies on the Facts class with a bare AttributeError.
        sys.modules[_spec.name] = _MOD
        _spec.loader.exec_module(_MOD)

# The real shas, so the test reads as the incident rather than as a fixture.
V0311_PIN = "a9830ebec0d7c7d14856f0b223d955186fe85eb2"
V0311_MAIN = "198259951b1e6d0e4c6d0c0e4e0a1f0f6a0b2c3d"   # shape-accurate stand-in for 1982599...


def _facts(**kw):
    """A Facts with everything agreeing, then whatever the case under test disturbs."""
    base = dict(pin=V0311_MAIN, tree=V0311_MAIN, tree_dirty=False, tree_present=True,
                main=V0311_MAIN, main_present=True, dll_name="me3/eldenring_archipelago.dll",
                dll_bytes=b"...ER_GIT_SHA=" + V0311_MAIN[:12].encode() + b" built...",
                dll_present=True)
    base.update(kw)
    return _MOD.Facts(**base)


@unittest.skipUnless(RUNNING_FROM_REPO and _MOD is not None, REPO_ONLY_REASON)
class TestReleasePairing(unittest.TestCase):

    def _check(self, facts, allow_stale=False):
        code, lines = _MOD.check(facts, allow_stale)
        return code, "\n".join(lines)

    def test_the_v0311_pairing_is_refused(self):
        """THE acceptance case. Tree, main and dll are all current and mutually agreed; only the
        gitlink trails. Everything a player receives is correct and the gate must still say no."""
        code, out = self._check(_facts(pin=V0311_PIN))
        self.assertEqual(code, _MOD.HARD, "the v0.3.11 pairing must not be packageable:\n" + out)
        self.assertIn("PIN != TREE", out)

    def test_the_v0311_pairing_cannot_be_overridden(self):
        """ALLOW_STALE_PIN exists for a deliberate lag against client MAIN. It must not buy a
        release whose own record disagrees with its own artifact -- that is not a shipping
        decision, it is a lost fact."""
        code, out = self._check(_facts(pin=V0311_PIN), allow_stale=True)
        self.assertEqual(code, _MOD.HARD, "PIN != TREE must take no override:\n" + out)

    def test_everything_agreeing_passes(self):
        code, out = self._check(_facts())
        self.assertEqual(code, _MOD.OK, out)
        self.assertIn("PASS", out)

    def test_a_pin_behind_client_main_is_refused_by_default(self):
        code, out = self._check(_facts(pin=V0311_MAIN, tree=V0311_MAIN, main=V0311_PIN))
        self.assertEqual(code, _MOD.HARD, out)

    def test_a_pin_behind_client_main_is_allowed_when_typed(self):
        """Exit 2, never 0 -- the run is staged but the operator is told what they bought, and the
        summary line must NOT round an allowed lag up to "agree"."""
        code, out = self._check(_facts(pin=V0311_MAIN, tree=V0311_MAIN, main=V0311_PIN),
                                allow_stale=True)
        self.assertEqual(code, _MOD.STALE_ALLOWED, out)
        self.assertIn("KNOWN-STALE", out)
        self.assertNotIn("PASS", out)

    def test_a_dirty_client_tree_is_refused(self):
        """A bundle from a dirty tree corresponds to no commit at all -- the unrecoverable-record
        problem in its worst form, so no override."""
        for allow in (False, True):
            code, out = self._check(_facts(tree_dirty=True), allow_stale=allow)
            self.assertEqual(code, _MOD.HARD, "allow_stale=%s:\n%s" % (allow, out))

    def test_a_dll_stamped_dirty_is_refused(self):
        code, out = self._check(_facts(
            dll_bytes=b"...ER_GIT_SHA=" + V0311_MAIN[:12].encode() + b"-dirty built..."))
        self.assertEqual(code, _MOD.HARD, out)

    def test_a_dll_from_another_commit_is_refused(self):
        """The artifact identifying itself is the last link in the chain: source agreement proves
        nothing if the binary predates it."""
        code, out = self._check(_facts(dll_bytes=b"...ER_GIT_SHA=deadbeefcafe built..."))
        self.assertEqual(code, _MOD.HARD, out)
        self.assertIn("does not carry ER_GIT_SHA", out)

    def test_a_missing_gitlink_is_refused(self):
        code, out = self._check(_facts(pin=""))
        self.assertEqual(code, _MOD.HARD, out)

    def test_ci_without_the_submodule_still_checks_the_pin(self):
        """The CI call site has no submodule and no dll. It must SAY it is answering a smaller
        question rather than pass silently -- and it must still catch a stale pin."""
        code, out = self._check(_facts(tree_present=True, tree="", main=V0311_PIN, pin=V0311_MAIN,
                                       dll_name="", dll_present=False, dll_bytes=b""))
        self.assertEqual(code, _MOD.HARD, out)
        skipped = _MOD.Facts(pin=V0311_MAIN, tree_present=False, main=V0311_MAIN,
                             notes=["submodule not checked out -- TREE, clean and DLL checks SKIPPED"])
        code, out = self._check(skipped)
        self.assertEqual(code, _MOD.OK, out)
        self.assertIn("SKIPPED", out)

    def test_an_unreachable_client_main_blocks_by_default(self):
        """A network blip must not read as agreement. The escape is typed."""
        code, out = self._check(_facts(main="", main_present=False))
        self.assertEqual(code, _MOD.HARD, out)
        code, out = self._check(_facts(main="", main_present=False), allow_stale=True)
        self.assertEqual(code, _MOD.STALE_ALLOWED, out)



class CallersPassTheWorldRoot(unittest.TestCase):
    """🛑 THE CALLER CAN BE WRONG WHILE THE TOOL IS RIGHT, and every case above tests the tool.

    MOTIVATING CASE (rule 11): er-release.yaml called this gate as
    `check_release_pairing.py --repo from-software-archipelago-clients`. `--repo` is the WORLD
    repo root -- it is the directory the tool runs `git ls-tree HEAD <CLIENT_DIR>` in to read the
    gitlink. Handed the client directory, the tool looked for a gitlink to the client INSIDE the
    client, found none, and said so correctly. Every assertion in this file passed the whole time,
    because the defect was in the invocation.

    It survived because the step had never executed: on the only tag er-release.yaml has ever
    fired on, the zip smoke above it failed and every step below was skipped. The first
    workflow_dispatch that got past the smoke went red here.
    """

    def setUp(self):
        if not RUNNING_FROM_REPO:
            self.skipTest(REPO_ONLY_REASON)
        self.wf = os.path.join(_FOUND, ".github", "workflows")
        if not os.path.isdir(self.wf):
            self.skipTest("no .github/workflows in this checkout")

    def test_package_allowlist_iterator_cannot_overwrite_release_name(self):
        """PowerShell variables are case-insensitive: `$name` overwrote the bundle's `$Name` with
        the final allowlist filename, producing `shoplineup_flags.json-<timestamp>.zip` (#834)."""
        script = os.path.join(_FOUND, "package_release.ps1")
        with open(script, encoding="utf-8-sig") as fh:
            text = fh.read()
        self.assertNotIn("foreach ($name in $Me3Allow)", text)
        self.assertIn("foreach ($me3Entry in $Me3Allow)", text)

    def _invocations(self):
        """[(workflow, line)] for every line invoking the pairing tool."""
        out = []
        for name in sorted(os.listdir(self.wf)):
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(self.wf, name), encoding="utf-8") as fh:
                for line in fh:
                    if "check_release_pairing.py" in line and not line.lstrip().startswith("#"):
                        out.append((name, line.strip()))
        return out

    def test_the_sweep_sees_the_callers(self):
        """Rule 2: an empty result is a failure. Both release workflows call this gate; if the
        sweep finds none, the assertion below is green over nothing."""
        found = self._invocations()
        self.assertGreaterEqual(
            len(found), 2,
            "only %d workflow invocation(s) of check_release_pairing.py found -- release.yaml and "
            "er-release.yaml both call it: %r" % (len(found), found))

    def test_no_caller_passes_the_client_dir_as_the_world_root(self):
        """HARD gate, and the exact defect. `--repo` names the world repo; the client directory is
        never a valid value for it."""
        found = self._invocations()
        # THE WITNESS (test_gf_vacuous_pass). The assertion below is green whether the callers are
        # right or the sweep stopped finding them, and a renamed workflow makes the second far more
        # likely than the first.
        self.assertNotEqual(
            [], found,
            "no workflow invocation of check_release_pairing.py was found, so the emptiness below "
            "is the sweep's, not the repo's")
        bad = [(w, l) for w, l in found if "--repo" in l and _MOD.CLIENT_DIR in l.split("--repo", 1)[1]]
        self.assertEqual(
            [], bad,
            "these hand --repo the CLIENT directory. --repo is the WORLD repo root -- where the "
            "tool reads `git ls-tree HEAD %s` to find the gitlink -- so this makes it look for a "
            "gitlink to the client inside the client and report 'this tree does not record a "
            "client at all'. Its default is already the world root; drop the flag:\n  %r"
            % (_MOD.CLIENT_DIR, bad))

    def test_a_dll_argument_comes_after_the_artifact_is_on_disk(self):
        """The .dll half cannot run before the download. A `--dll` above the step that fetches it
        reads as a check and asserts nothing -- the tool prints `(MISSING)` and fails, or, if the
        submodule is absent too, skips the half entirely and stays green."""
        for name in sorted(os.listdir(self.wf)):
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(self.wf, name), encoding="utf-8") as fh:
                text = fh.read()
            if "--dll" not in text:
                continue
            dll_at = text.index("--dll")
            dl_at = text.find("download-artifact")
            self.assertNotEqual(-1, dl_at,
                               "%s passes --dll but never downloads the client artifact" % name)
            self.assertLess(dl_at, dll_at,
                            "%s runs the pairing gate with --dll ABOVE the download-artifact step, "
                            "so the file it names does not exist yet" % name)


if __name__ == "__main__":
    unittest.main()
