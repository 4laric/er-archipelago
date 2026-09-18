"""`progression_sharing` -- the ONE player-facing switch over where progression goes.

`balanced` (default) must leave the two hidden knobs it governs exactly as the yaml wrote them, so the
shipped seed cannot move; `open` must force the 1/N step off (`cross_game_progression: never`) AND lift
the foreign-progression bar (`confine_foreign_progression: 0`). The three old keys must stay hidden
from the player surface but still be ACCEPTED, or every existing yaml stops generating.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from Options import Visibility  # noqa: E402

GAME = "Elden Ring"
HIDDEN = ("progression_bias", "cross_game_progression", "confine_foreign_progression")


class SharingBalancedDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_default_is_balanced_and_touches_nothing(self):
        self.assertEqual(self.world.options.progression_sharing.current_key, "balanced")
        self.assertEqual(self.world.options.cross_game_progression.value, -1)      # auto
        self.assertEqual(self.world.options.confine_foreign_progression.value, 100)

    def test_old_knobs_are_hidden_but_present(self):
        for key in HIDDEN:
            opt = getattr(self.world.options, key)
            self.assertEqual(opt.visibility, Visibility.none, key)
        self.assertEqual(self.world.options.progression_sharing.visibility, Visibility.all)


class SharingBalancedRespectsOldKeys(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "cross_game_progression": 0, "confine_foreign_progression": 50}

    def test_balanced_leaves_an_explicit_old_yaml_alone(self):
        self.assertEqual(self.world.options.cross_game_progression.value, 0)
        self.assertEqual(self.world.options.confine_foreign_progression.value, 50)


class SharingOpen(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "progression_sharing": "open"}

    def test_open_skips_the_one_over_n_step_and_lifts_the_bar(self):
        self.assertEqual(self.world.options.cross_game_progression.value, 0)
        self.assertEqual(self.world.options.confine_foreign_progression.value, 0)
