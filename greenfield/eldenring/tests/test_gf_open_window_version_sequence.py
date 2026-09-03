"""Release patch windows advance one number at a time."""

import importlib.util
import os


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
SPEC = importlib.util.spec_from_file_location(
    "open_window_version_sequence", os.path.join(ROOT, "tools", "open_window.py"))
OPEN_WINDOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPEN_WINDOW)


def test_next_patch_is_accepted():
    assert OPEN_WINDOW.patch_sequence_error("0.5.8", "0.5.9") is None


def test_skipped_patch_is_rejected_with_the_expected_successor():
    error = OPEN_WINDOW.patch_sequence_error("0.5.8", "0.5.10")
    assert error is not None
    assert "0.5.9" in error


def test_intentional_minor_window_is_not_treated_as_a_skipped_patch():
    assert OPEN_WINDOW.patch_sequence_error("0.5.8", "0.6.0") is None
