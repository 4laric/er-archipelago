"""`defaults.Frozen` -- the stand-in a removed yaml option leaves behind.

WHY THIS FILE EXISTS. `Frozen` deliberately raises on any attribute it does not carry, so that a
degraded read announces itself instead of looking like absence. That is the right default and it had
one hole: it assumed the reader was always one of OUR features. It is not. Archipelago's own spoiler
writer (`BaseClasses.Spoiler.to_file`) walks every option on every world and reads `.visibility`,
so a Frozen raised from inside the spoiler write -- a crash at the very END of a successful
generation, with the seed already filled.

Found by `greenfield/fuzz_gf.py` on `start_with_whetblades` (2026-08-09). It reproduces on `main` at
the same fuzz seed, so it predates the work that found it.
"""
import unittest

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.defaults import Frozen  # noqa: E402


class TestFrozenVisibility(unittest.TestCase):
    def test_visibility_exists_and_is_falsy_against_the_spoiler_flag(self):
        """THE MOTIVATING CASE, expressed the way AP expresses it: `res.visibility & spoiler`.

        `Visibility.spoiler` is `0b1000`. The assertion is on the AND, not on the attribute, because
        it is the AND that the spoiler writer branches on -- an attribute that existed but was truthy
        would send it on to `.current_option_name`, which Frozen also does not carry."""
        spoiler_flag = 0b1000   # Options.Visibility.spoiler
        # WITNESS: the mask is not vacuous -- against a visible option it selects. So the zero below
        # is Frozen answering "not visible", not `&` always producing 0.
        self.assertTrue(0b1111 & spoiler_flag)
        f = Frozen(1, name="start_with_whetblades")
        self.assertEqual(f.visibility & spoiler_flag, 0)

    def test_it_is_still_loud_about_everything_else(self):
        """The guard this file is protecting must not have been weakened to fix the crash. An
        attribute Frozen genuinely cannot answer still raises, and the message still says what to do
        about it."""
        f = Frozen(1, name="some_option")
        with self.assertRaises(AttributeError) as ctx:
            _ = f.range_end
        msg = str(ctx.exception)
        self.assertIn("some_option", msg)
        self.assertIn("range_end", msg)
        self.assertIn("FROZEN_OPTIONS", msg)

    def test_the_message_names_archipelago_too_not_just_our_features(self):
        """The old text said "a feature read attribute X", which sent the reader looking in the
        wrong repo: the reader was AP. A diagnostic that names the wrong suspect costs more than a
        vague one."""
        with self.assertRaises(AttributeError) as ctx:
            _ = Frozen(1, name="x").current_option_name
        self.assertIn("Archipelago", str(ctx.exception))

    def test_value_and_current_key_still_work(self):
        f = Frozen(3, current_key="all_filler", name="pool_builder_scope")
        self.assertEqual(f.value, 3)
        self.assertEqual(f.current_key, "all_filler")
