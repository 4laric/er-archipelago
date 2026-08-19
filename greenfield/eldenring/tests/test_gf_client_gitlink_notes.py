"""Per-gitlink-bump release-notes gate (#709), pure Git fixture.

The v0.4.3 window moved the client pin after 18 client PRs and touched no notes. The old gate stayed
green because the release section was already non-empty. These tests reproduce that exact shape in a
temporary repository, plus the #687/clients#207 lockstep control and its explicit exemption form.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

ROOT = find_repo_root(HERE)
NOTES = None
if ROOT is not None:
    TOOL = os.path.join(ROOT, "tools", "check_release_notes.py")
    if os.path.isfile(TOOL):
        SPEC = importlib.util.spec_from_file_location("check_release_notes_gitlink_test", TOOL)
        NOTES = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(NOTES)
        if not hasattr(NOTES, "client_gitlink_note_failures"):
            # An installed world may sit inside a DIFFERENT, older world checkout. That is not the
            # tool paired with this test and must not be mistaken for one merely because paths fit.
            NOTES = None


def _git(repo, *args, input_text=None):
    return subprocess.run(["git", *args], cwd=repo, input=input_text, text=True,
                          capture_output=True, check=True).stdout.strip()


@unittest.skipUnless(NOTES is not None, REPO_ONLY_REASON)
class ClientGitlinkNotesGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.name", "Gate Test")
        _git(self.repo, "config", "user.email", "gate@example.invalid")
        os.makedirs(os.path.join(self.repo, "release"))
        with open(os.path.join(self.repo, "release", "CHANGELOG.md"), "w", encoding="utf-8") as fh:
            fh.write("# changelog\n")
        _git(self.repo, "add", "release/CHANGELOG.md")
        _git(self.repo, "commit", "-qm", "baseline")
        self.base = _git(self.repo, "rev-parse", "HEAD")
        self.pin = 1

    def tearDown(self):
        self.tmp.cleanup()

    def bump(self, subject, note=False, trailer=None):
        sha = "%040x" % self.pin
        self.pin += 1
        _git(self.repo, "update-index", "--add", "--cacheinfo", "160000,%s,%s" %
             (sha, NOTES.CLIENT_GITLINK))
        if note:
            with open(os.path.join(self.repo, "release", "CHANGELOG.md"), "a", encoding="utf-8") as fh:
                fh.write("- client behaviour changed\n")
            _git(self.repo, "add", "release/CHANGELOG.md")
        args = ["commit", "-qm", subject]
        if trailer is not None:
            args += ["-m", trailer]
        _git(self.repo, *args)
        return _git(self.repo, "rev-parse", "HEAD")

    def audit(self, start=None):
        start = start or self.base
        result, unchecked = NOTES.client_gitlink_note_failures(self.repo, "%s..HEAD" % start)
        self.assertIsNone(unchecked)
        return result

    def test_known_v043_shape_is_red(self):
        bad = self.bump("pin 18 unnoted client changes")
        result = self.audit()
        self.assertEqual([sha for sha, _subject in result["failures"]], [bad])

    def test_same_commit_changelog_update_is_green(self):
        self.bump("pin documented client changes", note=True)
        result = self.audit()
        self.assertEqual(result["bumps"], 1)
        self.assertEqual(result["failures"], [])

    def test_lockstep_control_with_exact_exemption_is_green(self):
        self.bump("pure version lockstep", trailer=(
            "%s: %s" % (NOTES.CLIENT_NOTES_EXEMPT_TRAILER,
                         NOTES.CLIENT_NOTES_EXEMPT_VALUE)))
        self.assertEqual(self.audit()["failures"], [])

    def test_unchanged_changelog_and_prose_are_not_an_exemption(self):
        bad = self.bump("version lockstep, no player-visible change")
        self.assertEqual([sha for sha, _subject in self.audit()["failures"]], [bad])

    def test_wrong_exemption_value_is_red(self):
        bad = self.bump("claimed exemption", trailer="Client-Gitlink-Notes: lockstep")
        self.assertEqual([sha for sha, _subject in self.audit()["failures"]], [bad])

    def test_merge_is_compared_only_to_first_parent(self):
        """An unrelated merge must not re-charge paths that exist only on its second parent."""
        _git(self.repo, "checkout", "-qb", "unrelated")
        with open(os.path.join(self.repo, "unrelated.txt"), "w", encoding="utf-8") as fh:
            fh.write("branch work\n")
        _git(self.repo, "add", "unrelated.txt")
        _git(self.repo, "commit", "-qm", "unrelated branch")
        _git(self.repo, "checkout", "-q", "master")
        self.bump("documented pin on main", note=True)
        _git(self.repo, "merge", "--no-ff", "-qm", "merge unrelated", "unrelated")
        result = self.audit()
        self.assertEqual(result["bumps"], 1,
                         "the merge's second-parent diff must not be counted as another bump")
        self.assertEqual(result["failures"], [])


if __name__ == "__main__":
    unittest.main()
