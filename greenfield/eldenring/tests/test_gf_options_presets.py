"""`GFWeb.options_presets` -- the "for dummies" yamls -- are valid, visible and generated.

Archipelago turns each preset into a dropdown entry on the WebHost player-options page and a
ready-to-use yaml under Players/Templates/Presets/. They are how a player who never opens the web
wizard gets a sensible first seed, so a broken one is invisible to us and confusing to them.

Upstream ships a test for exactly this (test/webhost/test_option_presets.py) but our CI only runs
worlds/eldenring/tests, so nothing checked ours. The first two tests below restate its assertions for
this world. The third is OURS and is the reason presets and option demotion have to be reviewed
together: the WebHost applies a preset with an unguarded

    document.getElementById(key).value = ...

so a SCALAR preset key that is not on the simple page (because we demoted it out of the Launcher /
WebHost simple UI) makes that line throw and the preset dropdown stops working for every preset.
"""
import io
import os
import tempfile

import pytest
import yaml

pytest.importorskip("worlds.eldenring")

import Options  # noqa: E402
import Utils  # noqa: E402
from BaseClasses import PlandoOptions  # noqa: E402
from Options import NumericOption, OptionCounter, OptionList, OptionSet, Visibility  # noqa: E402
from worlds.eldenring.core import GAME, GreenfieldEldenRingWorld  # noqa: E402
from worlds.eldenring.option_presets import OPTIONS_PRESETS  # noqa: E402

WORLD = GreenfieldEldenRingWorld
HINTS = WORLD.options_dataclass.type_hints


def test_the_presets_are_registered_on_the_world():
    assert OPTIONS_PRESETS, "no presets defined -- the 'for dummies' story is gone"
    assert WORLD.web.options_presets == OPTIONS_PRESETS


@pytest.mark.parametrize("preset", sorted(OPTIONS_PRESETS))
def test_every_preset_key_is_live_valid_and_a_deviation(preset):
    """Upstream's rules, for this world: the key exists, the value parses and verifies, it is a
    type the WebHost supports, and (ours) it is a DEVIATION -- a preset that restates a default is
    noise that hides what the preset is for."""
    for name, value in OPTIONS_PRESETS[preset].items():
        assert name in HINTS, "preset %r names %r, which is not an option of %s" % (preset, name, GAME)
        cls = HINTS[name]
        option = cls.from_any(value)
        option.verify(WORLD, "Test Player", PlandoOptions(sum(PlandoOptions)))
        assert not str(value).startswith("random"), "%s: special random values are unsupported" % name
        assert any(issubclass(type(option), t) for t in (NumericOption, OptionSet, OptionList, OptionCounter)), (
            "%s in %r is not a type the WebHost can apply" % (name, preset))
        assert Visibility.complex_ui in cls.visibility or Visibility.simple_ui in cls.visibility, (
            "%s in %r is not visible in any supported UI" % (name, preset))
        assert option.value != cls.default, (
            "%s=%r in %r equals the default -- presets carry deviations only" % (name, value, preset))


@pytest.mark.parametrize("preset", sorted(OPTIONS_PRESETS))
def test_every_scalar_preset_key_is_on_the_simple_page(preset):
    """The WebHost applies a preset with an unguarded getElementById(key).value = ..., so a scalar
    key that is not rendered on the simple page throws. Demoting an option out of the simple UI must
    not silently break the preset dropdown -- if this fails, either keep the option visible or drop
    it from the preset."""
    for name, value in OPTIONS_PRESETS[preset].items():
        option = HINTS[name].from_any(value)
        if isinstance(option, (OptionSet, OptionList, OptionCounter)):
            continue  # applied through a different code path (checkbox groups)
        assert Visibility.simple_ui in HINTS[name].visibility, (
            "preset %r sets %r, which is hidden from the simple UI: the WebHost cannot apply it "
            "(getElementById(%r) would be null)" % (preset, name, name))


def test_archipelago_writes_a_loadable_yaml_for_every_preset():
    """AP's real generator, output handed to AP's real loader (Utils.parse_yaml is what Generate.py
    reads a player's file with)."""
    with tempfile.TemporaryDirectory() as tmp:
        Options.generate_yaml_templates(tmp)
        folder = os.path.join(tmp, "Presets")
        written = {f for f in os.listdir(folder) if f.startswith(GAME + " - ")}
        assert len(written) == len(OPTIONS_PRESETS), (
            "expected one yaml per preset, found %s" % sorted(written))
        for preset, values in OPTIONS_PRESETS.items():
            path = os.path.join(folder, "%s - %s.yaml" % (GAME, preset))
            assert os.path.isfile(path), "no yaml written for preset %r (have %s)" % (preset, sorted(written))
            data = Utils.parse_yaml(io.open(path, encoding="utf-8").read())
            assert data["game"] == GAME
            block = data[GAME]
            for name, value in values.items():
                weights = block[name]
                # a scalar option is written as a weight table: the preset value carries weight 50
                if isinstance(weights, dict):
                    heavy = [k for k, w in weights.items() if w == 50]
                    assert len(heavy) == 1, "%s in %r: expected exactly one weighted value, got %s" % (
                        name, preset, weights)
                    assert HINTS[name].from_any(heavy[0]).value == HINTS[name].from_any(value).value, (
                        "%s in %r: the generated yaml weights %r, not the preset value %r"
                        % (name, preset, heavy[0], value))
