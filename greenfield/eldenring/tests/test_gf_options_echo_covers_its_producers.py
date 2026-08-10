"""Tier-B gate: every OPTIONS_SUBKEY that NAMES `core._options_echo` as its producer is emitted there.

## The bug this is built from (er-archipelago#325, found in a player log 2026-08-10)

`merchant_bells_on_talk` shipped complete on both sides and was dark for every seed that turned it
on. The client baked its 38-row `(shop range -> hand-in flag)` table, armed the ESD detour beside
`shop_hints::on_shop_open`, and listed the tag in `client_features.rs SUPPORTED`. `contract.py`
declared the sub-key -- naming `core._options_echo (features/merchant_bells.py)` as its PRODUCER --
and `CONTRACT.md` documented it. The one line that joins the two halves,

    contract.MERCHANT_BELLS_ON_TALK: _opt("merchant_bells_on_talk"),

was never written into `_options_echo`. The client reads
`slot_data["options"]["merchant_bells_on_talk"]` (`er-logic/options.rs parse_bool_option`), got
`None`, parsed `false`, and `merchant_bells::set_enabled(false)` made the detour return on its first
atomic load.

## THE FOUR GREEN GATES, and why this one is a new DIRECTION rather than a widening

  * `validate_slot_data` only reports MISSING for `required=True`. This sub-key is `required=False`
    -- correctly so, because an absent key must parse false on an older client -- so its absence is
    indistinguishable from its off state at the point of validation.
  * `OPTIONS_SUBKEYS` is deliberately not folded into `CONTRACT_HASH`, so the client printed
    `VERSION: OK` and `contract: slot_data OK` over the gap.
  * `test_gf_client_contract_paths.py` runs CLIENT-READ -> DECLARATION and passed, because the
    declaration is exactly the half that exists. This file is the MIRROR: DECLARATION -> PRODUCER.
  * `test_gf_bell_handins.py` asserted the tag is IN `OPTIONS_SUBKEYS` -- a declaration check that
    the buggy tree satisfies. `test_gf_auto_equip.py` has the emission mutant for its OWN key
    ("deleted `contract.AUTO_EQUIP` from `core._options_echo`"), and that per-feature shape is why
    auto_equip works and this did not: the guard was never generalised, so the next option through
    the door had to remember to copy it. This gate is the general one.
  * `test_gf_off_means_off.py` EXCLUDES `_options_echo` on the stated grounds that "every subkey is
    echoed unconditionally by design". That was an assumption ABOUT the file, not a check OF it, and
    it was false for four days. The exclusion is still right for that scan's question (does an OFF
    option emit a live value?) and its docstring now points here for the other half.

The seed's only visible trace was `requiresClientFeatures ["merchant_bells_on_talk"]` going out to a
client that implements the feature, accepts the handshake, and is handed nothing to act on -- a
handshake succeeding over an empty payload, which is worse than a refusal because it reads as proof.

## What is checked, and what deliberately is not

Static, over `core.py`'s AST: the keys of the dict `_options_echo` returns. Static because the bug
is A LINE THAT IS NOT THERE, and absence is exactly what a source read sees best -- a dynamic check
would need a built world per option combination and would still only prove the combinations it
built. VALUES are none of this gate's business: `completion_scaling_floor` is unit-converted here
and `global_scadutree_blessing` is derived, so the only claim that generalises is PRESENCE.

The producer string is the join. A sub-key produced elsewhere (none today) is outside this file's
jurisdiction, so the set is asserted rather than filtered -- a declaration quietly moving its
producer must be a deliberate edit here, not a silent exit from the check.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_options_echo_covers_its_producers.py
  or: python greenfield/eldenring/tests/test_gf_options_echo_covers_its_producers.py
"""
import ast
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                      # .../greenfield/eldenring
CONTRACT_PY = os.path.join(GF_PKG, "contract.py")
CORE_PY = os.path.join(GF_PKG, "core.py")

ECHO_FN = "_options_echo"
# The substring that makes a ContractKey.producer THIS function's responsibility. Matched on the
# function name alone: the declarations spell it `core._options_echo (features/<x>.py)`, and that
# parenthetical names the feature which DECLARES the option -- it varies, so it must not be part of
# the join.
PRODUCER_MARK = ECHO_FN


def _load_contract():
    """Load contract.py by path. It is import-clean (no Archipelago import), which is what lets this
    gate run in the AP-free half of the suite -- the same trick test_gf_client_contract_paths uses."""
    spec = importlib.util.spec_from_file_location("gf_contract_echoaudit", CONTRACT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _echo_keys(source, contract_mod, fn_name=ECHO_FN):
    """Wire names of the keys `fn_name`'s dict literal emits, read from SOURCE.

    Accepts both spellings a key can take: `contract.SOME_CONST` (resolved through the contract
    module, whose constants are generated from the ContractKey names) and a bare string literal. An
    unresolvable `contract.X` comes back as the marker `?X`, so a renamed constant surfaces as a
    miss here instead of vanishing silently from the set.
    """
    tree = ast.parse(source)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn_name),
              None)
    if fn is None:
        return None
    names = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Dict):
            continue
        for k in node.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                names.add(k.value)
            elif (isinstance(k, ast.Attribute) and isinstance(k.value, ast.Name)
                    and k.value.id == "contract"):
                names.add(getattr(contract_mod, k.attr, "?" + k.attr))
    return names


class OptionsEchoCoversItsProducers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for p in (CONTRACT_PY, CORE_PY):
            if not os.path.isfile(p):
                raise unittest.SkipTest(
                    "%s absent (installed-world copy / partial tree) -- this gate reads the gen "
                    "SOURCE, so it only runs in the repo layout." % os.path.basename(p))
        cls.c = _load_contract()
        with open(CORE_PY, encoding="utf-8") as fh:
            cls.core_src = fh.read()
        cls.emitted = _echo_keys(cls.core_src, cls.c)
        cls.owned = [k for k in cls.c.OPTIONS_SUBKEYS if PRODUCER_MARK in k.producer]
        cls.disowned = [k for k in cls.c.OPTIONS_SUBKEYS if PRODUCER_MARK not in k.producer]

    def test_the_echo_was_found_and_parsed(self):
        """Vacuity guard #1: a renamed function, or a refactor to a non-literal dict, would empty
        the subject set and every assertion below would pass over nothing."""
        self.assertIsNotNone(self.emitted,
                             "core.%s not found -- if it was renamed, update ECHO_FN here AND the "
                             "producer strings in contract.py, which are the join this gate uses."
                             % ECHO_FN)
        self.assertGreaterEqual(
            len(self.emitted), 10,
            "core.%s parsed to only %d key(s) -- the extractor lost the dict literal (a helper "
            "call, a comprehension or a merge would do it). Fix the extractor; do not lower this."
            % (ECHO_FN, len(self.emitted)))

    def test_there_are_subkeys_claiming_this_producer(self):
        """Vacuity guard #2: if the declarations stopped naming `_options_echo`, the real gate below
        would quantify over an empty list and pass."""
        self.assertTrue(
            self.owned,
            "no OPTIONS_SUBKEYS entry names %r as its producer -- either the producer strings were "
            "reworded (fix PRODUCER_MARK) or the echo was dismantled." % PRODUCER_MARK)
        self.assertEqual(
            [], [k.name for k in self.disowned],
            "these OPTIONS_SUBKEYS name a producer other than %s. That may be legitimate, but it "
            "puts them outside this gate, so record the decision here deliberately rather than "
            "letting the subject set drift out from under the check." % ECHO_FN)

    def test_every_declared_subkey_is_actually_emitted(self):
        """THE GATE. A declaration whose producer does not produce it is a dark feature that reports
        `slot_data OK` -- #325's `merchant_bells_on_talk`, dark from the day it shipped."""
        # WITNESS (test_gf_vacuous_pass, shape 2). `missing` is empty on a healthy tree, and it is
        # ALSO empty if `owned` silently became empty -- a reworded producer string would do it. Say
        # out loud that the scan saw candidates on both sides before believing the empty result.
        self.assertGreaterEqual(
            len(self.owned), 5,
            "only %d sub-key(s) claim core.%s -- the join went stale, so an empty `missing` below "
            "would mean nothing was checked." % (len(self.owned), ECHO_FN))
        self.assertIn("auto_equip", self.emitted,
                      "auto_equip is missing from the echo too -- at that point the extractor is "
                      "broken, not the source, and this gate's empty results are worthless.")
        missing = sorted(k.name for k in self.owned if k.name not in self.emitted)
        self.assertEqual(
            [], missing,
            "\n\nDECLARED in contract.OPTIONS_SUBKEYS with producer core.%s, but NOT emitted "
            "there:\n  %s\n\nThe client reads slot_data[\"options\"][<key>] and an absent key "
            "parses FALSE, so the option is unreachable from yaml while gen and the connect "
            "handshake both report OK. Add the line to %s -- or, if the key genuinely moved, change "
            "its `producer` in contract.py so the join follows it.\n"
            % (ECHO_FN, "\n  ".join(missing), ECHO_FN))

    def test_merchant_bells_on_talk_specifically(self):
        """Rule 11: the motivating case is its own acceptance test. The general gate above covers
        it, but a named case survives a future rewrite of the extractor."""
        self.assertIn(
            "merchant_bells_on_talk", self.emitted,
            "merchant_bells_on_talk is not in the options echo. This is #325's original defect: a "
            "seed rolled with the option on emits requiresClientFeatures "
            "[\"merchant_bells_on_talk\"], the client accepts the handshake because it DOES "
            "implement the feature, and then reads no value -- so opening a merchant hands nothing "
            "to the Twin Maiden Husks.")

    def test_the_echo_emits_nothing_undeclared(self):
        """The reverse direction, cheap while we are here. `validate_slot_data` already rejects an
        UNDECLARED sub-key, but only on a seed that reaches validation; this says so from the source
        and names the file to edit."""
        # WITNESS: an empty `undeclared` must mean "every emitted key is declared", not "nothing was
        # emitted". The declared set is the other half of the comparison, so it is witnessed too.
        self.assertTrue(self.emitted, "the echo parsed to no keys at all -- see the parse guard")
        self.assertTrue(self.c.OPTIONS_SUBKEYS, "OPTIONS_SUBKEYS is empty")
        undeclared = sorted(n for n in self.emitted
                            if n not in {k.name for k in self.c.OPTIONS_SUBKEYS})
        self.assertEqual([], undeclared,
                         "core.%s emits sub-key(s) with no OPTIONS_SUBKEYS declaration: %s -- "
                         "declare them in contract.py (name/shape/profile/producer/consumer) so the "
                         "client half has something to point at." % (ECHO_FN, undeclared))

    def test_injection_catches_a_dropped_line(self):
        """PROOF the gate bites, on the exact mutant that shipped: take the real source, delete one
        declared key's line from the echo, and confirm it is reported missing. Without this, a
        broken extractor that returns everything-is-fine looks identical to a healthy tree."""
        victim = "merchant_bells_on_talk"
        const = [c for c in dir(self.c) if c.isupper() and getattr(self.c, c, None) == victim]
        self.assertTrue(const, "no module-level constant resolves to %r" % victim)
        needle = 'contract.%s: _opt("%s"),' % (const[0], victim)
        self.assertIn(needle, self.core_src,
                      "the injection needle no longer matches the real line -- update it, do not "
                      "delete the test.")
        emitted = _echo_keys(self.core_src.replace(needle, ""), self.c)
        self.assertIsNotNone(emitted)
        self.assertNotIn(victim, emitted,
                         "the mutant still emits %r, so this proof proves nothing" % victim)
        self.assertIn(victim, {k.name for k in self.owned},
                      "%r stopped claiming this producer, so the gate would skip it" % victim)


if __name__ == "__main__":
    unittest.main()
