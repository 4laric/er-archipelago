"""The template Archipelago generates FOR THIS GAME must be loadable by Archipelago.

MOTIVATING CASE (CONTRIBUTING rule 11), 2026-08-11. `ConfineForeignProgression` carried
`special_range_names = {"false": 0, "off": 0, "none": 0, "true": 100, "on": 100, "all": 100}`.
Every one of those names is legal, every one round-trips through `from_any`, and the option's own
suite was green on all six. The generated player template was still broken, and a player hit it:

    KeyError: Duplicate key False found in YAML. Already found keys: {False, 'random-low', ...}

AP writes a `Range`'s weight table through the `range_option` macro in `data/options.yaml`, and that
macro emits the key UNQUOTED -- `{{ entry }}: {{ default }}`. The Choice/Toggle branch a few lines
below it does not; it runs every name through `yaml_dump`. So for a range, and only for a range, the
NAME becomes a bare yaml scalar, and YAML 1.1 resolves `false` and `off` both to the boolean
`False`, `true` and `on` both to `True`. Two duplicate pairs, and `Utils.UniqueKeyLoader` -- the
loader AP reads player yamls with -- refuses the file.

🛑 THE QUIET HALF IS WORSE THAN THE LOUD ONE. Under a loader that does not check for duplicates the
mapping collapses last-wins, so `on: 0` overwrites `true: 50` and the template ships with its own
default weighted to ZERO. That failure has no error message at all; it is a seed that rolled
something nobody asked for. An option can be correct, its docstring accurate and its own tests
green, and the artifact a player is handed still be malformed -- because until now no test in this
repo had ever read the generated template.

WHY THREE TESTS. `test_special_range_names_stay_distinct_once_yaml_reads_them` is the cheap,
specific one: it names the offending keys, so the diagnosis is in the assertion message rather than
in a stack trace from inside PyYAML. `test_the_generated_template_parses` is the general one -- AP's
real generator over the real world, output handed to AP's real loader -- so it also catches the
family the first cannot enumerate: a name colliding with the null resolver, a docstring whose text
breaks the comment block, a future AP that changes the macro. `..._keeps_every_default_weighted` is
the quiet half, which neither of the other two can see. None subsumes another.

🛑 IT IS A COLLISION TEST, NOT A BAN ON BOOLEAN-LOOKING NAMES. `true` and `false` on their own are
fine -- they resolve to two different keys, and they are the words this option was born with. It is
`off` sitting BESIDE `false` that breaks it, which is why the fix dropped the redundant pair rather
than all four.
"""
import dataclasses
import io
import os
import tempfile
import typing

import pytest
import yaml

pytest.importorskip("worlds.eldenring")

import Options  # noqa: E402
import Utils  # noqa: E402
from worlds.eldenring.core import GAME, GFOptions  # noqa: E402

# The sub-option names AP's `dictify_range` writes beside a range's special names. Listed because a
# special name colliding with one of THEM is the same defect wearing a different hat.
GENERIC_RANGE_KEYS = ("random", "random-low", "random-high", "random-range-%s-%s")


def _option_classes():
    hints = typing.get_type_hints(GFOptions)
    return [(f.name, hints[f.name]) for f in dataclasses.fields(GFOptions)]


def _as_yaml_key(name):
    """What a BARE `name:` becomes when a yaml loader reads it -- which is how the generated
    template writes it. `off` is not the string "off"; it is the boolean `False`."""
    return next(iter(yaml.safe_load("%s: 0" % name)))


def test_special_range_names_stay_distinct_once_yaml_reads_them():
    """The invariant, stated exactly: the weight-table keys AP emits for a range must still be
    DISTINCT after the yaml loader has resolved them. They are written unquoted, so the name is not
    necessarily the key, and two names landing on one key is a duplicate the loader refuses.

    One test over the whole surface rather than a parametrize, because the per-option form would
    SKIP for the ~68 options that have no `special_range_names`, and every one of those skips would
    have to be carried in `expected_skips_ci.json` forever to say nothing."""
    classes = dict(_option_classes())
    scanned = {key: dict(getattr(cls, "special_range_names", {}) or {})
               for key, cls in classes.items()
               if getattr(cls, "special_range_names", None)}
    # WITNESS (test_gf_vacuous_pass): an empty scan would satisfy the assertion below while proving
    # nothing at all, and that is exactly how this defect would come back unnoticed.
    assert scanned, ("no option on the surface has special_range_names -- either they are all gone "
                     "or this test stopped being able to see them; either way it is not a pass")

    collisions = {}
    for key, names in scanned.items():
        cls = classes[key]
        emitted = list(names) + [k % (cls.range_start, cls.range_end) if "%s" in k else k
                                 for k in GENERIC_RANGE_KEYS]
        seen = {}
        for name in emitted:
            seen.setdefault(_as_yaml_key(name), []).append(name)
        clashing = {resolved: got for resolved, got in seen.items() if len(got) > 1}
        if clashing:
            collisions[key] = clashing

    assert not collisions, (
        "%s. AP's `range_option` macro writes weight-table keys UNQUOTED, so these names collapse "
        "onto a single key and `Utils.UniqueKeyLoader` refuses the generated template. Drop the "
        "redundant spelling -- an unquoted `on` in a player's yaml is already a bool by the time "
        "`from_any` sees it, so nothing is lost."
        % "; ".join("%s.special_range_names: %s all resolve to %r" % (key, sorted(got), resolved)
                    for key, clashing in sorted(collisions.items())
                    for resolved, got in sorted(clashing.items(), key=lambda kv: str(kv[0]))))


def _generate_template_for_this_game():
    """AP's own generator, not a re-render. A reimplementation here would be a second source of
    truth and would agree with itself about exactly the thing that is wrong."""
    with tempfile.TemporaryDirectory() as tmp:
        Options.generate_yaml_templates(tmp)
        path = os.path.join(tmp, "%s.yaml" % GAME)
        assert os.path.isfile(path), ("AP generated no template for %r. Templates present: %s"
                                      % (GAME, sorted(os.listdir(tmp))))
        return io.open(path, encoding="utf-8").read()


def test_the_generated_template_parses():
    """End to end. `Utils.parse_yaml` is literally what `Generate.py` reads a player's file with, so
    a pass here means the file AP hands a player is a file AP will accept back."""
    text = _generate_template_for_this_game()
    try:
        data = Utils.parse_yaml(text)
    except KeyError as exc:  # UniqueKeyLoader raises KeyError, not a YAMLError
        pytest.fail("the generated template for %r does not load: %s\nAlmost always a "
                    "`special_range_names` key that yaml resolves to something other than itself "
                    "-- see test_special_range_names_stay_distinct_once_yaml_reads_them." % (GAME, exc))
    assert data["game"] == GAME
    assert GAME in data, "the template has no option block for %r" % GAME


def test_the_generated_template_keeps_every_default_weighted():
    """The duplicate-key error is the loud half. This is the quiet half: a name that collapses onto
    another does not merely duplicate a key, it DELETES the weight the generator meant to write, and
    a plain loader will not say so. Every weight table must carry at least one entry above zero.

    Scoped to Range and Choice ON PURPOSE -- they are the only kinds the jinja renders as a weight
    table. An `OptionDict` like `start_inventory` is also a mapping and is legitimately empty;
    reading it as an all-zero weight table is a false positive I hit writing this."""
    from Options import Choice, Range

    block = yaml.safe_load(_generate_template_for_this_game())[GAME]
    weighted_kinds = {key for key, cls in _option_classes()
                      if isinstance(cls, type) and issubclass(cls, (Range, Choice))}
    assert weighted_kinds, "no Range/Choice options found -- the scan is looking at nothing"

    unweighted = sorted(
        key for key in weighted_kinds
        if isinstance(block.get(key), dict)
        and not any(isinstance(w, int) and not isinstance(w, bool) and w > 0
                    for w in block[key].values()))
    assert not unweighted, (
        "%s: every value in the generated template is weighted 0, so the template does not express "
        "its own default. A `special_range_names` key that collides with the default's key (e.g. "
        "`on` landing on `true`) does exactly this, silently." % unweighted)
