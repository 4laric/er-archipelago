"""Options-description gate (greenfield analog of the eldenring options-description gate).

Every greenfield/feature option this world defines must carry a non-empty class docstring -- that
docstring is the description the options wizard / webhost surfaces, so a blank one ships a mystery
knob. AP-common options (DeathLink and friends, whose class __module__ is "Options") are inherited,
not ours to document, so they're skipped. WorldTestBase; importorskips when AP isn't importable
(source-tree sandbox), so it's a no-op there and only runs once the world is installed under
Archipelago/worlds/.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_gf_options.py
"""
import dataclasses
import typing

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

GAME = "Elden Ring (Greenfield)"


class OptionsDescriptionGate(WorldTestBase):
    game = GAME

    def test_every_feature_option_has_a_description(self):
        dc = self.world.options_dataclass
        # Resolve field annotations to the actual Option classes (fields store the type).
        hints = typing.get_type_hints(dc)
        missing = []
        checked = 0
        for f in dataclasses.fields(dc):
            opt_cls = hints.get(f.name, f.type)
            module = getattr(opt_cls, "__module__", "") or ""
            # AP-common options live in the top-level Options module -> inherited, not ours.
            if module.startswith("Options"):
                continue
            checked += 1
            doc = getattr(opt_cls, "__doc__", None)
            if not (doc and doc.strip()):
                missing.append(f.name)
        self.assertGreater(
            checked, 0, "no greenfield/feature options found -- gate would be vacuous")
        self.assertEqual(
            missing, [],
            "these greenfield/feature options have an empty class docstring (description): "
            + ", ".join(missing))
