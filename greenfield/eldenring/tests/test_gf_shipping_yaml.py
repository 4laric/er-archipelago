"""The yaml we SHIP must name the game we ship.

Found 2026-07-12 while clearing the release checklist: `release/EldenRing.yaml` -- the flagship
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

THE OTHER DIRECTION (2026-08-10, and it took a player to find it)
----------------------------------------------------------------
Everything above gates template -> code: no key in the template may be a fake option. Nothing gated
code -> template, so an option could ship for eight releases without ever appearing in the file we
hand players. `capital_reconciler` did exactly that: on by default since v0.2.13, it decides whether
burning the Erdtree permanently strands Royal Leyndell's ~152 checks, and a player who hit that
strand went looking for it, found only `SPEC-capital-reconciler.md` on GitHub, and reported back
that "there no such setting the in he templat so i could find where it was described."

The asymmetry is not an oversight anyone would repeat on purpose -- it is that the wizard's option
list is GENERATED from the option classes and the template is HAND-MAINTAINED, so only the wizard
moves when a feature lands. When three options missed the wizard in the v0.3.9 window the fix was to
re-run the generator, and the changelog entry concluded "The yaml has always accepted these options;
only the wizard was behind." True, and it is the sentence that hid this: a template nobody diffs
against the option surface is behind in a way no player can see, because AP silently ignores what is
missing just as happily as what is invented.

`_TEMPLATE_DEBT` below is the sixteen that were already missing when the gate went in, listed so the
gate can be LIVE while they are drained (#512). It is checked in both directions -- an option
that leaves the template must be added to the list, and one that reaches the template must leave it
-- because a quarantine that may quietly grow is not a gate and one that keeps a fixed entry is a
redundant override.
"""
import os
import re
import unittest

from ..core import GAME

_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_GREENFIELD = os.path.dirname(_GF_PKG)
_REPO = os.path.dirname(_GREENFIELD)

# In the SOURCE tree the release bundle sits at <repo>/release/. In an INSTALLED world (which is
# what CI runs) the package has been copied into Archipelago/worlds/, so <repo> is the AP checkout and
# the bundle is nowhere near it -- the test would SKIP, i.e. assert nothing, which is how the yaml rotted
# through a rename in the first place. So the install step copies the template in beside the package,
# and we resolve from either. First existing wins -- same convention as region_map.csv / shop_rows.tsv.
_YAML = next((p for p in (os.path.join(_GF_PKG, "EldenRing.yaml"),
                          os.path.join(_REPO, "release", "EldenRing.yaml")) if os.path.isfile(p)),
             "")


# The sixteen options that were already missing from the shipped template when this gate landed
# (2026-08-10). `capital_reconciler` was the seventeenth and is fixed in the same commit, because a
# gate that quarantines its own motivating case documents nothing. Drain this list; do not add to it.
_TEMPLATE_DEBT = {
    "auto_equip",
    "dlc_blessing_catchup",
    "exclude_local_item_only",
    "grace_attunement",
    "grace_attunement_anchor",
    "keep_local",
    "keep_local_rune_cap",
    "no_equip_load",
    "no_fall_damage",
    "no_runes_in_shops",
    "num_regions_order",
    "progression_bias",
    "scadutree_blessing_scope",
    "start_regions",
    "start_with_whetblades",
    "vanilla_placement",
}

class TestShippingYaml(unittest.TestCase):

    def test_the_template_is_actually_present(self):
        """If the template goes missing, the two tests below would pass VACUOUSLY. Fail loudly."""
        self.assertTrue(_YAML, "EldenRing.yaml not found in the package dir OR release/ -- the "
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

    def test_every_option_in_the_template_actually_exists(self):
        """THE ONE THAT MATTERS. Archipelago SILENTLY IGNORES unknown yaml options -- it does not warn,
        it does not error, it just generates a seed on defaults. So a template key that is not a real
        option is invisible: it reads like a knob and does nothing.

        Found 2026-07-12: of the 30 keys in the shipped template, only 10 were real. 19 were FROZEN
        (removed from the option surface by defaults.FROZEN_OPTIONS in the v0.2 slim-down) and 1
        (`grace_rando`) did not exist at all. Worse, three of them stated the WRONG behaviour --
        `flatten_regular_upgrades: 0` promised the vanilla 2/4/6 smithing ladder while the game
        actually runs a uniform 2-stone ladder, and `global_scadutree_blessing: off` while it is
        actually `scaled`. The template described a different game than the one that runs.

        The template rotted because nothing pointed a test at it -- the same reason it went on
        declaring `game: EldenRing` through the rename. This is that test.
        """
        real = self._world_option_names()
        block = self._game_block_keys()
        unknown = sorted(k for k in block if k not in real)
        self.assertEqual(
            [], unknown,
            f"{len(unknown)} key(s) in the shipped template are NOT real options and will be SILENTLY "
            f"IGNORED: {unknown}. A key that reads like a knob and does nothing is worse than no key.")

    def test_every_player_facing_option_is_in_the_template(self):
        """THE OTHER DIRECTION. An option absent from the template is invisible to every player who
        does not use the wizard: they cannot set it, and -- worse for a default-ON behaviour -- they
        cannot discover that it is what is happening to them.

        Scope is the WIZARD'S definition of player surface, and deliberately so, because the wizard
        is the other artifact that has to answer this question and two answers would be one too
        many: the fields GFOptions adds on top of PerGameCommonOptions (AP's own plando/item_links
        keys are AP's to document), minus `Visibility.none` (a field hidden from the player is not
        player surface anywhere).
        """
        surface, block = self._player_surface_names(), self._game_block_keys()
        # WITNESS both halves. Either scan can silently stop matching -- the dataclass walk if the
        # options plumbing is reshaped, the yaml parser if the template's indentation changes -- and
        # an empty scan on EITHER side satisfies the assertion below for free, in opposite
        # directions. The numbers are floors, not the true counts, so they do not need touching every
        # time an option lands.
        assert len(surface) > 40, f"only {len(surface)} options found -- the surface scan is blind"
        assert len(block) > 25, f"only {len(block)} template keys parsed -- the yaml scan is blind"
        missing = sorted(set(surface) - set(block))
        undocumented = [k for k in missing if k not in _TEMPLATE_DEBT]
        self.assertEqual(
            [], undocumented,
            f"{len(undocumented)} option(s) exist but are not in the shipped template: "
            f"{undocumented}. A player who does not use the wizard cannot set them and cannot find "
            f"out they exist. Add a commented block to release/EldenRing.yaml.")

    def test_the_template_debt_list_has_no_stale_entries(self):
        """A drained debt entry must LEAVE this list. CONTRIBUTING: a redundant manual override is a
        failure -- a quarantine that keeps entries it no longer needs stops describing the debt and
        starts hiding the next one."""
        surface, block = self._player_surface_names(), self._game_block_keys()
        assert len(surface) > 40, f"only {len(surface)} options found -- the surface scan is blind"
        assert len(block) > 25, f"only {len(block)} template keys parsed -- the yaml scan is blind"
        stale = sorted(_TEMPLATE_DEBT - (set(surface) - set(block)))
        self.assertEqual(
            [], stale,
            f"{stale} are in the template now -- delete them from _TEMPLATE_DEBT so the gate covers "
            f"them for real.")

    def _player_surface_names(self):
        """The yaml-tunable ER surface, by the same rule tools/dump_options_metadata.py uses."""
        import dataclasses
        from Options import PerGameCommonOptions, Visibility
        from worlds.AutoWorld import AutoWorldRegister
        dc = AutoWorldRegister.world_types[GAME].options_dataclass
        common = {f.name for f in dataclasses.fields(PerGameCommonOptions)}
        return [f.name for f in dataclasses.fields(dc)
                if f.name not in common
                and getattr(f.type, "visibility", Visibility.all) != Visibility.none]

    def _world_option_names(self):
        from worlds.AutoWorld import AutoWorldRegister
        return set(AutoWorldRegister.world_types[GAME].options_dataclass.type_hints)

    def _game_block_keys(self):
        """Keys indented exactly two spaces under the `<GAME>:` block."""
        out, inside = [], False
        for l in self.lines:
            if l.startswith(f"{GAME}:"):
                inside = True
                continue
            if inside:
                if l and not l[0].isspace() and not l.startswith("#"):
                    break                      # left the block
                m = re.match(r"^  ([a-z_][a-z0-9_]*):", l)
                if m:
                    out.append(m.group(1))
        return out

    def test_options_block_is_keyed_by_the_game(self):
        """The options live under a block named for the game. Rename one, rename both."""
        blocks = [k for k, v in self._keys() if not v.strip() and k.strip() != "game"]
        self.assertIn(
            GAME, [b.strip() for b in blocks],
            f"the template has no `{GAME}:` options block (found {blocks!r}) -- every option in it "
            f"would be silently ignored, and the seed would generate on defaults.")


if __name__ == "__main__":
    unittest.main()
