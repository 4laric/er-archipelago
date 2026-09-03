"""Release-note update instructions are complete, first, resolved, and consistent."""

import importlib.util
import os
import sys
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
        SPEC = importlib.util.spec_from_file_location("check_release_update_guidance_test", TOOL)
        NOTES = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(NOTES)
        if not hasattr(NOTES, "parse_update_guidance"):
            # An installed world may sit inside another checkout whose tool predates this test.
            # That is not the source tree paired with the installed test package.
            NOTES = None


VALID = """### What you need to update

- **Client:** Required — replace it.
- **APWorld:** Host-only — the host replaces it.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Regenerate to see options.
- **Existing seed/save:** Compatible — keep playing.
- **Profile/assets:** No action — keep the profile.

### Changes
Something happened.
"""


@unittest.skipUnless(NOTES is not None, REPO_ONLY_REASON)
class ReleaseUpdateGuidanceTests(unittest.TestCase):
    def test_blurb_must_lead_with_the_current_run_answer(self):
        old_shape = """# v9.9.9 — release blurb (draft)

## What you need to update

Enough prose to clear any unrelated size floor. This deliberately models the old shape where the
answer players need was reduced to a compatibility row and could disappear from published notes.
"""
        errors = NOTES.current_run_guidance_failures(old_shape, "blurb")
        self.assertEqual(len(errors), 1)
        self.assertIn("current run", errors[0])

    def test_blurb_accepts_a_resolved_current_run_answer(self):
        text = """# v9.9.9 — release blurb (draft)

## Will updating affect my current run?

**Do not update a run already in progress.** Keep its old client until it is finished.

## What you need to update
"""
        self.assertEqual(NOTES.current_run_guidance_failures(text, "blurb"), [])

    def test_valid_block_parses_to_semantic_statuses(self):
        values, errors = NOTES.parse_update_guidance(VALID, 3, "changelog")
        self.assertEqual(errors, [])
        self.assertEqual(values["Client"], "required")
        self.assertEqual(values["APWorld"], "host-only")
        self.assertEqual(
            values["YAML"], "new yaml optional. existing yamls remain valid.")

    def test_update_block_must_be_the_first_section(self):
        values, errors = NOTES.parse_update_guidance(
            "### Features\n\nStuff.\n\n" + VALID, 3, "changelog")
        self.assertIsNone(values)
        self.assertIn("where `### What you need to update` belongs", errors[0])

    def test_placeholders_and_missing_fields_fail(self):
        text = """## Will updating affect my current run?

Keep an active run on its old client.

## What you need to update

- **Client:** TODO(open): Required / Optional / No
- **YAML:** New YAML optional. Existing YAMLs remain valid.
"""
        values, errors = NOTES.parse_update_guidance(text, 2, "blurb")
        self.assertIsNone(values)
        self.assertTrue(any("unresolved placeholder" in error for error in errors))
        self.assertTrue(any("missing resolved" in error for error in errors))
        self.assertTrue(any("must bold" in error for error in errors))

    def test_semantic_statuses_expose_document_contradictions(self):
        changelog, errors = NOTES.parse_update_guidance(VALID, 3, "changelog")
        self.assertEqual(errors, [])
        blurb_text = ("## Will updating affect my current run?\n\n"
                      "Keep an active run on its old client.\n\n" +
                      VALID.replace("###", "##")).replace(
            "**Client:** Required", "**Client:** Optional")
        blurb, errors = NOTES.parse_update_guidance(blurb_text, 2, "blurb")
        self.assertEqual(errors, [])
        mismatched = [field for field in NOTES.UPDATE_FIELDS
                      if changelog[field] != blurb[field]]
        self.assertEqual(mismatched, ["Client"])


if __name__ == "__main__":
    unittest.main()
