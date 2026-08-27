"""The generator input hash is a property of gen_inputs.db, not its extraction context."""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_FOUND = find_repo_root(HERE)
REPO = _FOUND
if _FOUND is not None:
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import gen_manifest


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
class GenManifestBundleIdentity(unittest.TestCase):
    def test_artifact_leftovers_do_not_change_bundle_identity(self):
        baseline = gen_manifest.compute_inputs_hash(REPO)
        artifacts = os.path.join(REPO, "elden_ring_artifacts")
        os.makedirs(os.path.join(artifacts, "event"), exist_ok=True)
        leftover = os.path.join(artifacts, "event", "stale-leftover.emevd.dcx.js")
        try:
            with open(leftover, "w", encoding="utf-8") as fh:
                fh.write("not in gen_inputs.db\n")
            self.assertEqual(baseline, gen_manifest.compute_inputs_hash(REPO))
        finally:
            if os.path.exists(leftover):
                os.remove(leftover)

    def test_same_bundle_hashes_identically_without_an_extracted_tree(self):
        baseline = gen_manifest.compute_inputs_hash(REPO)
        with tempfile.TemporaryDirectory() as other:
            os.makedirs(os.path.join(other, "tools"))
            os.makedirs(os.path.join(other, "greenfield"))
            for rel in gen_manifest.FILE_INPUTS:
                if rel.startswith("elden_ring_artifacts/"):
                    continue
                src = os.path.join(REPO, rel)
                if os.path.isfile(src):
                    dst = os.path.join(other, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
            shutil.copyfile(os.path.join(REPO, "gen_inputs.db"),
                            os.path.join(other, "gen_inputs.db"))
            self.assertEqual(baseline, gen_manifest.compute_inputs_hash(other))

    def test_bundle_manifest_is_read_only(self):
        before = os.stat(os.path.join(REPO, "gen_inputs.db")).st_mtime_ns
        gen_manifest.compute_inputs_hash(REPO)
        after = os.stat(os.path.join(REPO, "gen_inputs.db")).st_mtime_ns
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
