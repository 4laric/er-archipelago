"""THE WORLD DECLARES ITS PROFILE, AND THE CONTRACT REFUSES FOREIGN KEYS (#1463).

The client used to choose between its two location-resolution paths -- the matt slot-key resolver
(`locationIdsToKeys`) and our `locationFlags` table -- by asking whether the matt key happened to be
present. A path chosen by sniffing is a path nobody validates: a seed carrying BOTH key families, or
NEITHER, takes whichever branch the sniff lands on, and the symptom is checks that never fire hours
into a run. So the world now says what it is, in one required key, and `validate_slot_data` refuses
an emission that contradicts it.

What this file guards, in the order it matters:

  1. `profile` is DECLARED (BOTH, required) and EMITTED -- a declaration nobody emits is worse than
     no declaration, because the client's bridge would read the absence as "old seed" forever.
  2. A greenfield slot_data carrying a BEDROCK-only key FAILS, and the message NAMES the key. The
     name is the whole point: "your apworld emitted a key from the other contract" is one grep to
     fix once you know which key, and unfindable otherwise.
  3. The same in the other direction, so the check is a rule and not a special case for one key.
  4. `dungeonSweeps` is no longer a greenfield key and is no longer emitted. It was tagged as
     greenfield-produced while boss_locks.py wrote `{}` into it for its whole life
     (RECON-contract-keys-20260706 filed it as a profile blemish); an always-empty dict reads
     identically to absent on the client, so the tag was describing an intention, not an emission.

  5. NO bedrock-only key has a greenfield emitter, checked by reading greenfield's CODE rather
     than by rolling options -- and the emission half is run under `natural_progression` on AND
     off. Both were added by #1466, which is #1463 landing with `naturalKeyTriggers` mistagged
     bedrock-only while features/natural_progression.py emitted it. Guard 2 above was already
     here and did not catch it: it only ever saw one option set, and not that one. A cross-profile
     check that fires only on the options a test happens to roll is a check that ships broken.

Rule 8, applied here: what would make these pass while the bug is back? Only re-tagging the key as
greenfield, which is the change these tests exist to make someone argue for.

The contract half needs no Archipelago (contract.py imports nothing), so it loads by path and runs
anywhere; the emission half is a WorldTestBase suite and skips until the world is installed.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_profile_declaration.py
"""
import ast
import importlib.util
import io
import os
import tokenize
import unittest

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONTRACT_PY = os.path.join(os.path.dirname(_HERE), "contract.py")

_spec = importlib.util.spec_from_file_location("_gf_contract_profile", _CONTRACT_PY)
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)

GAME = "Elden Ring"


def _minimal(profile):
    """The smallest slot_data that VALIDATES for `profile`, so a test's one added key is the only
    thing under examination. Built from the contract rather than typed out, so a newly-required key
    cannot leave these tests quietly asserting against a dict that fails for an unrelated reason."""
    sd = {}
    for key in contract.CONTRACT:
        if not (key.required and key.in_profile(profile)):
            continue
        if key.name == contract.PROFILE:
            sd[key.name] = profile
            continue
        if key.shape == "OPTIONS_DICT":
            sd[key.name] = {s.name: _SHAPE_SAMPLES[s.shape]
                            for s in key.subkeys if s.required and s.in_profile(profile)}
            continue
        sd[key.name] = _SHAPE_SAMPLES[key.shape]
    return sd


# One valid sample per shape a required key can have. Kept tiny and obvious; if a required key ever
# takes a shape that is not here, the KeyError names it rather than producing a mystery failure.
_SHAPE_SAMPLES = {
    "ANY": {},
    "SCALAR_INT_MAP": {},
    "LISTVAL_INT_MAP": {},
    "STR_MAP": {},
    "STR": "x",
    "STR_LIST": [],
    "INT": 0,
    "INT_LIST": [],
    "BOOL": False,
    "BOOL_OR_INT": 0,
    "INT_OR_BOOL": 0,
    "NUMBER": 0,
    "TRIPLE_LIST": [],
    "PAIR_LIST": [],
    "LOCK_PLACEMENTS": {},
    "NESTED_GRANTS": {},
    "FLASK_LADDER": [],
    # OPTIONS_DICT is filled from the key's own required sub-keys in `_minimal`, not from here.
}


class ProfileIsDeclared(unittest.TestCase):
    def test_profile_is_a_required_key_of_both_profiles(self):
        key = contract.BY_NAME.get("profile")
        self.assertIsNotNone(key, "the contract must declare `profile` (#1463)")
        self.assertTrue(key.required, "a profile nobody has to send is a profile nobody can trust")
        for p in (contract.GREENFIELD, contract.BEDROCK):
            self.assertTrue(key.in_profile(p), f"`profile` must belong to {p}")

    def test_the_module_constant_matches_the_wire_name(self):
        # Emitters go through contract.PROFILE, never a literal; this is the pin that makes that
        # indirection safe to rely on.
        self.assertEqual(contract.PROFILE, "profile")


class ForeignKeysAreRefused(unittest.TestCase):
    def _problems(self, sd, profile):
        return contract.validate_slot_data(sd, profile=profile, strict=False)

    def test_a_clean_greenfield_slot_data_has_no_profile_problems(self):
        # The control. Without it, a test below could "pass" because everything fails.
        sd = _minimal(contract.GREENFIELD)
        self.assertIn(contract.PROFILE, sd, "the minimal fixture built nothing to validate")
        problems = self._problems(sd, contract.GREENFIELD)
        self.assertEqual([p for p in problems if "FOREIGN" in p], [])

    def test_greenfield_emitting_a_bedrock_key_fails_and_names_it(self):
        sd = _minimal(contract.GREENFIELD)
        sd["locationIdsToKeys"] = {"1": "1,0:0000000000::"}
        problems = [p for p in self._problems(sd, contract.GREENFIELD) if "FOREIGN" in p]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("locationIdsToKeys", problems[0])
        with self.assertRaises(contract.ContractError) as raised:
            contract.validate_slot_data(sd, profile=contract.GREENFIELD, strict=True)
        self.assertIn("locationIdsToKeys", str(raised.exception))

    def test_bedrock_emitting_a_greenfield_key_fails_and_names_it(self):
        sd = _minimal(contract.BEDROCK)
        sd["locationFlags"] = {}
        problems = [p for p in self._problems(sd, contract.BEDROCK) if "FOREIGN" in p]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("locationFlags", problems[0])

    def test_a_both_key_is_foreign_to_neither(self):
        # itemCounts is tagged BOTH; the check must not fire on a key both contracts share, or
        # every seed would fail and the rule would be reverted rather than fixed.
        self.assertIn(contract.BOTH, contract.BY_NAME["itemCounts"].profiles)
        for profile in (contract.GREENFIELD, contract.BEDROCK):
            sd = _minimal(profile)
            sd["itemCounts"] = {}
            self.assertEqual([p for p in self._problems(sd, profile) if "FOREIGN" in p], [])


class DungeonSweepsIsBedrockOnly(unittest.TestCase):
    def test_the_tag_says_what_is_true(self):
        key = contract.BY_NAME["dungeonSweeps"]
        self.assertEqual(key.profiles, (contract.BEDROCK,),
                         "greenfield never produced dungeonSweeps -- it wrote {} into it")
        self.assertNotIn("boss_locks", key.producer,
                         "the producer string must not name a greenfield module")

    def test_the_flag_keyed_sibling_is_untouched(self):
        # The live greenfield sweep wire. If this ever went bedrock-only too, sweeps would go dark.
        self.assertTrue(contract.BY_NAME["dungeonSweepFlags"].in_profile(contract.GREENFIELD))


class NoBedrockOnlyKeyHasAGreenfieldEmitter(unittest.TestCase):
    """The tag audit, done by reading greenfield's source rather than by rolling options.

    This is the test that would have caught #1466 before CI did. `naturalKeyTriggers` was tagged
    BEDROCK-only while features/natural_progression.py returned it under `natural_progression`, and
    the emission suite below never noticed, because the emission suite only ever sees the options a
    given test rolls -- and no test in it rolled that one. A cross-profile check that fires on an
    option nobody exercises is a check that ships broken.

    So this walks the SOURCE instead: every BEDROCK-only wire name, looked for in the CODE of every
    module under greenfield/. Code, not text -- comments and docstrings are stripped first, because
    both core.py and boss_locks.py legitimately *discuss* bedrock-only keys in prose ("dungeonSweeps:
    NOT emitted (#1463)") and a scan that counted those would be a scan people silence with an
    allow-list until it means nothing. String literals are deliberately KEPT: `sd["fogWalls"] = ...`
    is exactly the emission being hunted, and it is a string.
    """

    # The two generators that render the declaration itself. Everything else is fair game.
    _NOT_EMITTERS = {"contract.py", "gen_contract.py", "gen_handoff.py"}

    @staticmethod
    def _code_only(text):
        """`text` with comments and docstrings blanked, so a mention in prose is not an emission."""
        lines = text.splitlines()
        blank = set()
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                blank.update(range(tok.start[0], tok.end[0] + 1))
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.ClassDef,
                                     ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                blank.update(range(body[0].lineno, body[0].end_lineno + 1))
        return "\n".join("" if i + 1 in blank else ln for i, ln in enumerate(lines))

    def _greenfield_sources(self):
        # The APWORLD PACKAGE, not its parent. In the repo that is greenfield/eldenring; once
        # gf_test.py installs the world it is Archipelago/worlds/eldenring -- and the parent there
        # is `worlds/`, i.e. every other AP world, which is neither ours to audit nor even all
        # parseable (MuseDash's presets carry a BOM). Anchoring on the package makes the scan the
        # same set of files in both layouts, which is the only way its result means one thing.
        root = os.path.dirname(_HERE)
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", "handoff")]
            for f in files:
                if f.endswith(".py") and f not in self._NOT_EMITTERS:
                    yield os.path.join(base, f)

    def test_the_stripper_keeps_code_and_drops_prose(self):
        # Rule 8: a scan that silently stripped everything would pass forever. Pin both halves.
        sample = ('"""a docstring naming fogWalls."""\n'
                  '# a comment naming lockGrantItems\n'
                  'sd["randomStartAreaId"] = 1\n')
        stripped = self._code_only(sample)
        self.assertNotIn("fogWalls", stripped)
        self.assertNotIn("lockGrantItems", stripped)
        self.assertIn("randomStartAreaId", stripped, "a real emission must survive stripping")

    def test_bedrock_only_names_appear_in_no_greenfield_code(self):
        bedrock_only = sorted(k.name for k in contract.CONTRACT
                              if not k.in_profile(contract.GREENFIELD))
        self.assertTrue(bedrock_only, "the contract must still have bedrock-only keys to audit")
        hits, scanned = {}, 0
        for path in self._greenfield_sources():
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            scanned += 1
            code = self._code_only(text)
            for name in bedrock_only:
                if name in code:
                    hits.setdefault(name, []).append(os.path.basename(path))
        # WITNESS: an empty `hits` means nothing if the walk found no files. It has found ~40 for
        # this package's whole life; 20 is a floor that only a broken anchor can cross.
        self.assertGreater(scanned, 20,
                           f"the walk scanned only {scanned} module(s) -- it has lost the package")
        self.assertEqual(
            hits, {},
            "these keys are tagged BEDROCK-only but greenfield CODE names them. If the module emits "
            "the key, the tag is the bug -- retag it BOTH, which is exactly what #1466 was for "
            f"naturalKeyTriggers. Hits: {hits}")

    def test_natural_key_triggers_is_tagged_for_both(self):
        # The specific regression. Named separately so the failure reads as itself, not as a
        # generic audit hit.
        key = contract.BY_NAME["naturalKeyTriggers"]
        self.assertTrue(key.in_profile(contract.GREENFIELD),
                        "features/natural_progression.py emits naturalKeyTriggers whenever "
                        "natural_progression is ON -- it is not bedrock-only (#1466)")
        self.assertTrue(key.in_profile(contract.BEDROCK))
        self.assertIn("natural_progression", key.producer,
                      "the producer string must name the greenfield module that emits it")


# --------------------------------------------------------------------------------------------
# The EMISSION half: needs the world installed under Archipelago/worlds (gf_test.py's job).
# --------------------------------------------------------------------------------------------
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")


class ProfileIsEmitted(WorldTestBase):
    game = GAME
    options = {"dungeon_sweep": "all"}   # the option under which boss_locks.py used to emit {}

    def test_slot_data_declares_greenfield(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd.get("profile"), "greenfield")

    def test_slot_data_carries_no_bedrock_only_key(self):
        sd = self.world.fill_slot_data()
        self.assertIn("locationFlags", sd, "this seed emitted no locationFlags at all")
        foreign = sorted(
            name for name in sd
            if name in contract.BY_NAME
            and not contract.BY_NAME[name].in_profile(contract.GREENFIELD)
        )
        self.assertEqual(foreign, [], f"greenfield emitted foreign key(s): {foreign}")

    def test_dungeon_sweeps_is_not_emitted_even_with_sweeps_on(self):
        # The blemish itself: this is the option under which the empty dict used to be written.
        sd = self.world.fill_slot_data()
        self.assertNotIn("dungeonSweeps", sd)
        self.assertIn("dungeonSweepFlags", sd, "the live flag-keyed sweep wire must still be sent")


class _NoForeignKeyUnderTheseOptions:
    """Mixin: assert the full emission under one option set carries no bedrock-only key.

    The source scan above is the durable guard; this is the live one, and it exists because a
    feature can compose a key name rather than write it (`sd[contract.SOMETHING]`, an f-string, a
    dict merged in from data). Each subclass is one option set the cross-profile check has to
    survive, and `natural_progression` on/off is here by name: ON is the combination that failed
    CI on #1466, OFF is the control that passed it and therefore hid the bug.
    """

    game = GAME

    def test_no_bedrock_only_key_is_emitted(self):
        sd = self.world.fill_slot_data()
        foreign = sorted(name for name in sd
                         if name in contract.BY_NAME
                         and not contract.BY_NAME[name].in_profile(contract.GREENFIELD))
        # WITNESS: "no foreign keys" is also what an empty slot_data says. Pin a greenfield key
        # that every seed emits, so a fill_slot_data that returned {} cannot read as a pass.
        self.assertIn("locationFlags", sd, "this seed emitted no locationFlags at all")
        self.assertEqual(foreign, [],
                         f"options={self.options!r} emitted foreign key(s): {foreign}")

    def test_the_emission_validates_as_greenfield(self):
        # The end-to-end statement: not just "no foreign key" but "the contract accepts this",
        # which is what the server-side assertion actually runs.
        contract.validate_slot_data(self.world.fill_slot_data(),
                                    profile=contract.GREENFIELD, strict=True)


class ForeignKeysNaturalProgressionOn(_NoForeignKeyUnderTheseOptions, WorldTestBase):
    options = {"natural_progression": True, "num_regions": 0}


class ForeignKeysNaturalProgressionOff(_NoForeignKeyUnderTheseOptions, WorldTestBase):
    options = {"natural_progression": False}

    def test_natural_key_triggers_is_absent_when_the_mode_is_off(self):
        """The off half of the #1466 retag, and the row test_gf_off_means_off ledgers.

        `naturalKeyTriggers` became a greenfield key because natural_progression emits it. That
        makes it CONDITIONAL, and this project's rule for a conditional key is that its absence is
        asserted somewhere rather than assumed -- otherwise "off" is only ever tested by nobody
        looking. features/natural_progression.slot_data early-returns {} when the mode is off, so
        a default seed must not carry the key at all.
        """
        sd = self.world.fill_slot_data()
        self.assertIn("locationFlags", sd, "this seed emitted no locationFlags at all")
        self.assertNotIn("naturalKeyTriggers", sd)


class ForeignKeysNaturalProgressionOnWithDlcAndSweeps(_NoForeignKeyUnderTheseOptions, WorldTestBase):
    # The two features that own bedrock-adjacent wires (natural keys, sweeps) turned on together,
    # with the DLC in play so the DLC-only branches of both are exercised.
    options = {"natural_progression": True, "num_regions": 0,
               "enable_dlc": True, "dungeon_sweep": "all"}
