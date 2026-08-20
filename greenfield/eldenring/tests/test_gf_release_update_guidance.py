"""Release-note update instructions are complete, first, resolved, and consistent."""

import importlib.util
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
TOOL = os.path.join(ROOT, "tools", "check_release_notes.py")
SPEC = importlib.util.spec_from_file_location("check_release_update_guidance_test", TOOL)
NOTES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NOTES)


VALID = """### What you need to update

- **Client:** Required — replace it.
- **APWorld:** Host-only — the host replaces it.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Regenerate to see options.
- **Existing seed/save:** Compatible — keep playing.
- **Profile/assets:** No action — keep the profile.

### Changes
Something happened.
"""


class ReleaseUpdateGuidanceTests(unittest.TestCase):
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
        self.assertIn("not `### What you need to update`", errors[0])

    def test_placeholders_and_missing_fields_fail(self):
        text = """## What you need to update

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
        blurb_text = VALID.replace("###", "##").replace(
            "**Client:** Required", "**Client:** Optional")
        blurb, errors = NOTES.parse_update_guidance(blurb_text, 2, "blurb")
        self.assertEqual(errors, [])
        mismatched = [field for field in NOTES.UPDATE_FIELDS
                      if changelog[field] != blurb[field]]
        self.assertEqual(mismatched, ["Client"])


if __name__ == "__main__":
    unittest.main()
