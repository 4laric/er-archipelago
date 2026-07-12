"""The yaml we SHIP must name the game we ship.

Found 2026-07-12 while clearing the release checklist: `release-v0.2/EldenRing.yaml` -- the flagship
template, the one SETUP.md tells a player to drop into `Players/` -- declared:

    game: EldenRing

but the world is `GAME = "Elden Ring"` (the v0.2 rename). Archipelago rejected it outright:

    Exception: No world found to handle game EldenRing. Did you mean 'Elden Ring' (90% sure)?

So the release bundle did not work out of the box: a player's FIRST action failed. Every doc
(SETUP, CHANGELOG, RELEASE-NOTES) also asserted the id was "unchanged from v0.1", which was the
opposite of the truth and would have sent people hunting for an install problem they did not have.

Nothing caught it because the test suite builds its worlds through the AP test harness, which is handed
the game name directly -- it never reads the shipped yaml. The template was the one artifact with no
test pointing at it, which is exactly why it rotted through a rename.

This test closes that: the shipped yaml's `game:` key must equal the world's GAME, and its options block
must be keyed the same. Cheap, and it fails the moment a rename lands without the template following.
"""
import os
import unittest

from ..core import GAME

_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_GREENFIELD = os.path.dirname(_GF_PKG)
_REPO = os.path.dirname(_GREENFIELD)

# In the SOURCE tree the release bundle sits at <repo>/release-v0.2/. In an INSTALLED world (which is
# what CI runs) the package has been copied into Archipelago/worlds/, so <repo> is the AP checkout and
# the bundle is nowhere near it -- the test would SKIP, i.e. assert nothing, which is how the yaml rotted
# through a rename in the first place. So the install step copies the template in beside the package,
# and we resolve from either. First existing wins -- same convention as region_map.csv / shop_rows.tsv.
_YAML = next((p for p in (os.path.join(_GF_PKG, "EldenRing.yaml"),
                          os.path.join(_REPO, "release-v0.2", "EldenRing.yaml")) if os.path.isfile(p)),
             "")


class TestShippingYaml(unittest.TestCase):

    def test_the_template_is_actually_present(self):
        """If the template goes missing, the two tests below would pass VACUOUSLY. Fail loudly."""
        self.assertTrue(_YAML, "EldenRing.yaml not found in the package dir OR release-v0.2/ -- the "
                               "install step must copy it in, or this whole gate asserts nothing.")

    def setUp(self):
        with open(_YAML, encoding="utf-8") as f:
            self.lines = [l.rstrip("\n") for l in f]

    def _keys(self):
        """Top-level yaml keys (no indent, ends in ':'), ignoring comments."""
        out = []
        for l in self.lines:
            if not l or l.startswith("#") or l[0].isspace():
                continue
            if ":" in l:
                out.append(l.split(":", 1))
        return out

    def test_game_key_matches_the_world(self):
        """`game:` must name the world AP will look up. This is the one that shipped broken."""
        game = [v.strip() for k, v in self._keys() if k.strip() == "game"]
        self.assertEqual(1, len(game), "the template must declare exactly one `game:`")
        self.assertEqual(
            GAME, game[0],
            f"the shipped yaml says game: {game[0]!r} but the world is GAME = {GAME!r}. "
            f"Archipelago will reject it with 'No world found to handle game {game[0]}'.")

    def test_options_block_is_keyed_by_the_game(self):
        """The options live under a block named for the game. Rename one, rename both."""
        blocks = [k for k, v in self._keys() if not v.strip() and k.strip() != "game"]
        self.assertIn(
            GAME, [b.strip() for b in blocks],
            f"the template has no `{GAME}:` options block (found {blocks!r}) -- every option in it "
            f"would be silently ignored, and the seed would generate on defaults.")


if __name__ == "__main__":
    unittest.main()
