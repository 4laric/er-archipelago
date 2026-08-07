"""Off means off: every CONDITIONALLY-EMITTED slot_data key must name its absent-when-off test.

MOTIVATING CASE (2026-08-04 inert-test audit, finding P1). test_gf_boss_locks.py carried
`test_sweeps_off_when_disabled` whose body was literally `pass`, inside a class that ran
`dungeon_sweep: "all"`. Replacing the emission gate in features/boss_locks.py
(`if world.options.dungeon_sweep.value != 0:`) with `if True:` left all 57 tests across the four
files referencing the option GREEN: a player who disabled dungeon_sweep still got whole-dungeon
auto-grants on boss kills, silently. The contract validator could not catch it either -- the sweep
keys are required=False, and an optional key that appears when it should not is exactly what
`validate_slot_data` is silent about. Per feature, the question "is the key ABSENT when the option
is off?" was asked nowhere except by accident (finding P1's sibling: scaduBlessingCap's off test
reasoned about the fixture's bookkeeping sets instead of generating an off world, so a broken gate
would have passed it too).

WHAT THIS FILE ENFORCES, for every ContractKey with required=False in the greenfield profile:
  1. An AST scan over core.py + features/*.py classifies each key's emission as UNCONDITIONAL
     (some producer emits it on every path through its function) or CONDITIONAL (every emission
     sits behind an `if`, or behind an early bare `return`, or no emission exists at all).
  2. Every CONDITIONAL key must have a row in OFF_LEDGER below, and the row is VERIFIED, not
     trusted: the named test must exist, its class must pin the named option to the named off
     value, and its body must contain an assertion that mentions the key. A row naming a test that
     does not exist, does not turn the option off, or never asserts on the key is RED.
  3. A NEW option-gated key added without its off-test therefore turns CI red the moment it lands
     (test_every_conditional_key_names_its_off_test). That ratchet is the point of this file.

DESIGN: LEDGER + SCAN, NOT PURE INFERENCE, NOT PURE PROSE.
  * Pure inference ("find the gating option in the AST, roll the off-world automatically")
    UNDER-matches: gates hide behind early returns (features/auto_equip.py), helper predicates
    (progressive.py `_flasks_on(world)`), world attributes set in generate_early
    (features/capital.py `gf_capital_reconciler`), and data presence (features/check_lots.py).
    An under-matching checker is itself an inert test -- it would have waved P1 through had the
    gate been written as an early return.
  * A pure prose ledger ("this key is covered, trust me") is the P1 `pass` body wearing a table.
  * So the scan answers only the question it can answer soundly -- "COULD this key legally be
    absent?", where OVER-flagging is safe (worst case: one more verified ledger row) -- and the
    ledger answers the rest, every row mechanically checked against the named test. The two-way
    match (no missing rows, no stale rows) means scanner rot is loud too: if a refactor hides a
    gate from the scan, the key flips to UNCONDITIONAL and its now-stale ledger row fails the run.

WHAT THE SCAN CANNOT SEE (stated, not hidden):
  * A key emitted under a gate by one producer but unconditionally by another counts as
    UNCONDITIONAL -- which is simply true: the unconditional producer emits it on every seed.
  * A gate whose off state emits the key with an EMPTY value (present-but-empty, e.g.
    shopRunePrices, progressionSurfaceLocations) classifies UNCONDITIONAL here; absent-not-empty
    vs present-but-empty is the fixture's jurisdiction (test_gf_slot_data_fixture ALWAYS_KEYS).
  * `core._options_echo` is excluded: it feeds the `options` SUB-dict, whose every subkey is
    echoed unconditionally by design (contract.OPTIONS_SUBKEYS; features never write there).
"""
import ast
import os
import re

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.dirname(HERE)

# contract attribute name -> key string, for resolving `contract.X` emissions and mentions.
_CONTRACT_ATTRS = {n: v for n, v in vars(contract).items() if isinstance(v, str)}

OPTIONAL_GF_KEYS = frozenset(
    k.name for k in contract.CONTRACT if not k.required and k.in_profile("greenfield"))


# ---------------------------------------------------------------------------------------------
# THE SCAN
# ---------------------------------------------------------------------------------------------

def _key_of(node):
    """Resolve an emission key node: a string literal or a `contract.X` attribute."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "contract"):
        return _CONTRACT_ATTRS.get(node.attr)
    return None


def _producer_files():
    feats = os.path.join(WORLD, "features")
    files = [os.path.join(WORLD, "core.py")]
    files += [os.path.join(feats, f) for f in sorted(os.listdir(feats)) if f.endswith(".py")]
    return files


def _dict_keys(node):
    """Keys of a dict literal, or None if the node is not a dict literal we can resolve."""
    if not isinstance(node, ast.Dict):
        return None
    out = set()
    for kn in node.keys:
        if kn is None:            # **splat: cannot resolve -> caller treats as unresolvable
            return None
        k = _key_of(kn)
        if k is not None:
            out.add(k)
    return out


def survey():
    """Classify every optional greenfield contract key by emission shape.

    Returns (conditional, evidence): `conditional` is the set of keys for which NO producer emits
    on every path; `evidence` maps every key to human-readable emission-site notes for messages.
    """
    per_fn = {}     # (file, fnname) -> {"emits": {key: [conds...]}, "cond_ret_keys": [set|None]}
    for path in _producer_files():
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for parent in ast.walk(tree):
            for ch in ast.iter_child_nodes(parent):
                ch._p = parent

        def _enclosing(node):
            """Nearest enclosing function + the `if` conditions crossed to reach it."""
            conds, cur = [], node
            while cur is not None:
                p = getattr(cur, "_p", None)
                if isinstance(p, (ast.If, ast.IfExp)) and cur is not p.test:
                    conds.append(ast.unparse(p.test))
                if isinstance(p, ast.FunctionDef):
                    return p, conds
                cur = p
            return None, conds

        fname = os.path.basename(path)
        for node in ast.walk(tree):
            emitted = []
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)):
                k = _key_of(node.targets[0].slice)
                if k:
                    emitted.append(k)
            if isinstance(node, ast.Dict):
                for kn in node.keys:
                    k = _key_of(kn) if kn is not None else None
                    if k:
                        emitted.append(k)
            is_ret = isinstance(node, ast.Return)
            if not emitted and not is_ret:
                continue
            fn, conds = _enclosing(node)
            if fn is None or fn.name == "_options_echo":
                continue          # module level, or the options sub-dict echo (see docstring)
            rec = per_fn.setdefault((fname, fn.name), {"emits": {}, "cond_ret_keys": []})
            for k in emitted:
                if k in OPTIONAL_GF_KEYS:
                    rec["emits"].setdefault(k, []).append(conds)
            if is_ret and conds:
                # A conditional return. Which keys does it still emit? A dict literal tells us; any
                # other value (None, a name, a call) resolves to "emits nothing we can prove" --
                # conservative: it gates every key emitted elsewhere in this function.
                rec["cond_ret_keys"].append(_dict_keys(node.value) or set())

    conditional, evidence = set(), {}
    for key in OPTIONAL_GF_KEYS:
        sites = []
        unconditional = False
        for (loc, rec) in per_fn.items():
            if key not in rec["emits"]:
                continue
            for conds in rec["emits"][key]:
                sites.append("%s:%s conds=%s" % (loc[0], loc[1], conds or "[]"))
            gated_by_return = any(key not in ks for ks in rec["cond_ret_keys"])
            if any(not conds for conds in rec["emits"][key]) and not gated_by_return:
                unconditional = True
        evidence[key] = sites or ["NO EMISSION SITE FOUND"]
        if not unconditional:
            conditional.add(key)
    return conditional, evidence


# ---------------------------------------------------------------------------------------------
# THE LEDGER. key -> row. Row kinds:
#   ("off_test",   "file.py::Class::test", {option: off_value, ...})
#       The named WorldTestBase class pins each option to the value under which the key must be
#       ABSENT, and the named test asserts that absence. Fully verified below.
#   ("absent_test", "file.py::Class::test" or "file.py::test", reason)
#       Absence asserted, but not behind an option (e.g. CONTRACT: DEAD keys). Verified: test
#       exists, mentions the key, asserts.
#   ("data_gated", "file.py::Class::test" or "file.py::test", reason)
#       Conditional on GENERATED DATA presence, not on an option -- there is no yaml that reaches
#       the off state, so no off-world can be rolled. Verified: the named guard test exists and
#       asserts. The reason must name the data condition.
#   ("not_emitted", reason)
#       Declared but never emitted. Verified against the fixture's _CONTRACT_NOT_EMITTED ledger.
# ---------------------------------------------------------------------------------------------
_SWEEP_OFF = ("off_test",
              "test_gf_boss_locks.py::DungeonSweepOffSeed::test_sweeps_off_when_disabled",
              {"dungeon_sweep": "none"})
_CAPITAL_OFF = ("off_test",
                "test_gf_capital_reconciler.py::CapitalOffSeed::test_no_wire",
                {"capital_reconciler": False})
_CHECK_LOT_REASON = (
    "gated on generated DATA, not an option: features/check_lots.py returns {} when "
    "check_lots_data.py has no tables, and the legacy-vs-split shape rides the _LEGACY probe of "
    "that data module. No yaml reaches the off state, so no off-world can be rolled; the fixture's "
    "exact-keyset test owns the mutex invariant (exactly one of legacy / Map+Enemy, never none).")

OFF_LEDGER = {
    # --- the 2026-08-04 audit's motivating trio (finding P1) ---
    "dungeonSweepFlags": _SWEEP_OFF,
    "dungeonSweeps": _SWEEP_OFF,
    "sweepLockGates": _SWEEP_OFF,
    # --- option-gated keys that already had a real off-test (verified, now ratcheted) ---
    "flaskLadder": ("off_test",
                    "test_gf_progressive_flasks.py::ProgressiveFlasksOff"
                    "::test_slot_data_emits_no_flask_ladder",
                    {"progressive_flasks": False}),
    "goalRequiredItems": ("off_test",
                          "test_gf_goal_required_items.py::GoalRequiredItemsUnderNaturalProgression"
                          "::test_the_key_is_omitted_entirely",
                          {"natural_progression": True}),
    "capitalBurnFlag": _CAPITAL_OFF,
    "capitalBurnDoneFlag": _CAPITAL_OFF,
    "capitalAshenPlayRegions": _CAPITAL_OFF,
    "capitalRoyalPlayRegions": _CAPITAL_OFF,
    "capitalReleaseRows": _CAPITAL_OFF,
    # SPEC-ashen-capital-lock (2026-08-06). These two ride the SAME off-wire as the five above --
    # features/capital.slot_data returns {} outright when the reconciler is off, so the whole
    # family goes absent together and _CAPITAL_OFF's class already asserts that. Their extra
    # `is not None` guard is a PRE-REGEN guard (an absent generated value must not ship a
    # placeholder: a wrong flag 300 costs the player the floor, not a feature), not a second
    # option -- so there is no second off-state to pin.
    "capitalWorldBurnFlag": _CAPITAL_OFF,
    "capitalPreBurnFlag": _CAPITAL_OFF,
    # --- option-gated keys whose off-tests were ADDED with this file (they had none) ---
    # scaduBlessingCap. The ceiling was REMOVED 2026-08-06 and nothing emits the key at any mode.
    #
    # 🛑 The comment that replaced its off_test row asserted that "survey() no longer classifies
    # it as conditional". It does, and it must: "or no emission exists at all" is CONDITIONAL by
    # this file's own definition (see the header, point 1), and that is the right answer — a key
    # nothing emits is a key that is always absent, which is the strongest form of off. Dropping
    # the row therefore did not silence the checker, it reddened it
    # (`scaduBlessingCap: NO EMISSION SITE FOUND`) and took `test_the_checker_rejects_a_stale_row`
    # down with it, since that test asserts on the FIRST failure the checker reports.
    #
    # So it is ledgered as `not_emitted` — the kind whose verification is the fixture's
    # _CONTRACT_NOT_EMITTED entry rather than an off-world, which is exactly where the guarantee
    # was said to have moved.
    "scaduBlessingCap": ("not_emitted",
                         "ceiling REMOVED 2026-08-06 (features/scaling.py): no mode emits a "
                         "blessing cap, and an absent cap already means the ladder ceiling on the "
                         "client side. The contract entry stays declared because the client still "
                         "honours a cap from any apworld that sends one"),
    "dlcScadutreeFloorRanges": ("off_test",
                                "test_gf_scadu_blessing_cap.py::ScaduBlessingOffSeed"
                                "::test_the_floor_ranges_are_absent_when_the_mode_is_off",
                                {"global_scadutree_blessing": "off"}),
    "dlcRegionBuckets": ("off_test",
                         "test_gf_scaling_sphere.py::DlcOffSeed::test_dlc_buckets_absent_without_dlc",
                         {"enable_dlc": False}),
    # UNION key -- every producer (auto_equip handshake, scaling ceiling) must be off at once for
    # the key to vanish, so its off-world pins them all. Per-tag exactness lives with each feature
    # (test_gf_auto_equip.py, test_gf_options.py's ceiling matrix); this row owns full absence.
    "requiresClientFeatures": ("off_test",
                               "test_gf_off_means_off.py::AllClientFeatureGatesOffSeed"
                               "::test_no_client_feature_demand_when_nothing_is_used",
                               {"auto_equip": False, "maximum_enemy_difficulty": 100}),
    "enemyDropRoll": ("off_test",
                      "test_gf_off_means_off.py::RerollWiresOffSeed"
                      "::test_enemy_drop_wire_absent_when_off",
                      {"reroll_enemy_drops": False}),
    "shopInfiniteStock": ("off_test",
                          "test_gf_off_means_off.py::RerollWiresOffSeed"
                          "::test_shop_stock_wire_absent_when_off",
                          {"reroll_infinite_shop_stock": False}),
    # --- no option reaches the off state ---
    "checkLotBlank": ("data_gated",
                      "test_gf_slot_data_fixture.py::SlotDataFixtureRich::test_exact_keyset",
                      _CHECK_LOT_REASON),
    "checkLotBlankMap": ("data_gated",
                         "test_gf_slot_data_fixture.py::SlotDataFixtureRich::test_exact_keyset",
                         _CHECK_LOT_REASON),
    "checkLotBlankEnemy": ("data_gated",
                           "test_gf_slot_data_fixture.py::SlotDataFixtureRich::test_exact_keyset",
                           _CHECK_LOT_REASON),
    "checkLotZeroMap": ("data_gated",
                        "test_gf_slot_data_fixture.py::SlotDataFixtureRich::test_exact_keyset",
                        _CHECK_LOT_REASON),
    "checkLotZeroEnemy": ("data_gated",
                          "test_gf_slot_data_fixture.py::SlotDataFixtureRich::test_exact_keyset",
                          _CHECK_LOT_REASON),
    "apPlaceholderGoods": ("data_gated",
                           "test_gf_slot_data_fixture.py::SlotDataFixtureRich::test_exact_keyset",
                           _CHECK_LOT_REASON),
    # --- declared, never emitted ---
    "runeGatedGraces": ("absent_test",
                        "test_gf_grace_gates.py::GatesArmed::test_rune_gate_keys_retired",
                        "CONTRACT: DEAD since 2026-07-14; the client half never existed"),
    "greatRuneItemIds": ("absent_test",
                         "test_gf_grace_gates.py::GatesArmed::test_rune_gate_keys_retired",
                         "CONTRACT: DEAD since 2026-07-14; the client half never existed"),
    "enable_dlc": ("not_emitted",
                   "top-level copy retired; the client reads options/enable_dlc, echoed "
                   "unconditionally by core._options_echo (contract.OPTIONS_SUBKEYS)"),
}


# ---------------------------------------------------------------------------------------------
# ROW VERIFICATION
# ---------------------------------------------------------------------------------------------

def _load_test_module_ast(fname):
    path = os.path.join(HERE, fname)
    assert os.path.isfile(path), "ledger names a test file that does not exist: %s" % fname
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _find_test(ref):
    """Resolve 'file.py::Class::test' / 'file.py::test' -> (module_ast, class_ast|None, fn_ast, src)."""
    parts = ref.split("::")
    assert len(parts) in (2, 3), "bad ledger test ref (want file.py::Class::test): %r" % ref
    mod = _load_test_module_ast(parts[0])
    scope, cls = mod, None
    if len(parts) == 3:
        cls = next((n for n in mod.body
                    if isinstance(n, ast.ClassDef) and n.name == parts[1]), None)
        assert cls is not None, "%s: class %s not found" % (parts[0], parts[1])
        scope = cls
    fn = next((n for n in scope.body
               if isinstance(n, ast.FunctionDef) and n.name == parts[-1]), None)
    assert fn is not None, "%s: test %s not found -- the ledger row is stale or a lie" % (
        parts[0], parts[-1])
    return mod, cls, fn


def _class_option_pins(cls):
    """The class-level `options = {...}` dict, values resolved where literal."""
    for n in cls.body:
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "options"
                and isinstance(n.value, ast.Dict)):
            pins = {}
            for kn, vn in zip(n.value.keys, n.value.values):
                if isinstance(kn, ast.Constant):
                    try:
                        pins[kn.value] = ast.literal_eval(vn)
                    except (ValueError, SyntaxError):
                        pins[kn.value] = _UNRESOLVED
            return pins
    return None


class _Unresolved:
    def __repr__(self):
        return "<non-literal>"


_UNRESOLVED = _Unresolved()


def _module_aliases_for(mod, key):
    """Module- and class-level NAME = "<key>" bindings, so a test may say KEY instead of the
    literal (test_gf_goal_required_items.py's `KEY = "goalRequiredItems"` shape)."""
    names = set()
    for scope in [mod] + [n for n in mod.body if isinstance(n, ast.ClassDef)]:
        for n in scope.body:
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                    and n.value.value == key):
                names.update(t.id for t in n.targets if isinstance(t, ast.Name))
    return names


def _fn_asserts(fn):
    """True if the function body contains an assert statement or a self.assert*/fail call."""
    for n in ast.walk(fn):
        if isinstance(n, ast.Assert):
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr.startswith("assert") or n.func.attr == "fail":
                return True
    return False


def _fn_mentions(fn, mod, key):
    src = ast.unparse(fn)
    tokens = {key} | _module_aliases_for(mod, key)
    tokens |= {a for a, v in _CONTRACT_ATTRS.items() if v == key}
    return any(re.search(r"\b%s\b" % re.escape(t), src) for t in tokens)


def verify_row(key, row):
    """Raise AssertionError unless this ledger row is real, off, and asserting. See kinds above."""
    kind = row[0]
    if kind == "not_emitted":
        from worlds.eldenring.tests import test_gf_slot_data_fixture as fx
        assert key in fx._CONTRACT_NOT_EMITTED, (
            "%s: ledgered not_emitted, but the fixture's _CONTRACT_NOT_EMITTED does not list it -- "
            "either it IS emitted (give it a real off_test row) or the fixture ledger is stale" % key)
        return
    ref = row[1]
    mod, cls, fn = _find_test(ref)
    assert _fn_asserts(fn), (
        "%s: %s has no assertion path at all -- a body that cannot fail is the exact defect this "
        "file exists to prevent (audit finding P1 was a literal `pass`)" % (key, ref))
    if kind == "off_test":
        pins = row[2]
        assert cls is not None, "%s: off_test rows must name a WorldTestBase class: %r" % (key, ref)
        got = _class_option_pins(cls)
        assert got is not None, (
            "%s: %s has no literal `options = {...}` dict, so the off state cannot be verified"
            % (key, ref))
        for opt, off_val in pins.items():
            assert opt in got, (
                "%s: %s does not pin %r at all -- it relies on the class default, which can drift "
                "(memory: er-unfreezing-an-option-needs-the-class-default). Pin it." % (key, ref, opt))
            assert got[opt] == off_val, (
                "%s: %s pins %r=%r, but the ledger says the key is absent when %r=%r -- this test "
                "is NOT testing the off state" % (key, ref, opt, got[opt], opt, off_val))
        assert _fn_mentions(fn, mod, key), (
            "%s: %s never mentions the key (literally, via a KEY alias, or via contract.<CONST>) -- "
            "it cannot be asserting its absence" % (key, ref))
    elif kind == "absent_test":
        assert _fn_mentions(fn, mod, key), (
            "%s: %s never mentions the key -- it cannot be asserting its absence" % (key, ref))
    elif kind == "data_gated":
        assert row[2] and isinstance(row[2], str), (
            "%s: data_gated rows must say WHICH data condition gates the key" % key)
    else:
        raise AssertionError("%s: unknown ledger row kind %r" % (key, kind))


def check_coverage(conditional, ledger):
    """The two-way match. Raise on any conditional key without a row, or any stale row."""
    _, evidence = _SURVEY
    missing = conditional - set(ledger)
    assert not missing, (
        "slot_data keys are emitted CONDITIONALLY but have NO absent-when-off test row:\n%s\n"
        "For each: add the off-state test (a WorldTestBase class pinning the option off and "
        "asserting the key is ABSENT from fill_slot_data()), then ledger it here. Emission sites:\n%s"
        % (sorted(missing),
           "\n".join("  %s: %s" % (k, "; ".join(evidence.get(k, ["<new key -- rerun survey>"])))
                     for k in sorted(missing))))
    stale = set(ledger) - conditional
    assert not stale, (
        "OFF_LEDGER rows for keys the scan no longer classifies as conditional: %s\n"
        "Either the key became unconditional (drop the row and move its guarantee to the fixture's "
        "ALWAYS_KEYS jurisdiction) or a refactor hid its gate from the scan (teach survey() the new "
        "shape -- do NOT delete the row to get green)." % sorted(stale))


_SURVEY = survey()


# ---------------------------------------------------------------------------------------------
# THE TESTS
# ---------------------------------------------------------------------------------------------

def test_the_scan_still_sees_the_motivating_gate():
    """Anchor: the P1 gate (`if world.options.dungeon_sweep.value != 0`) must classify CONDITIONAL.
    If this fails, survey() rotted -- every other green in this file is then meaningless."""
    conditional, evidence = _SURVEY
    for key in ("dungeonSweepFlags", "dungeonSweeps", "sweepLockGates"):
        assert key in conditional, (
            "%s no longer classifies as conditionally emitted: %s" % (key, evidence[key]))
    assert any("dungeon_sweep" in s for s in evidence["dungeonSweepFlags"])


def test_every_conditional_key_names_its_off_test():
    check_coverage(_SURVEY[0], OFF_LEDGER)


def test_every_ledger_row_is_verified():
    for key, row in sorted(OFF_LEDGER.items()):
        verify_row(key, row)


# ------------------------------ the checker must be seen to fail ------------------------------
# Rule 11: the motivating case IS the acceptance test. Each of these hands the checker the exact
# defect it exists to catch and demands the red. A guard that has never fired is not a guard.

def test_the_checker_rejects_an_unpaired_key():
    with pytest.raises(AssertionError, match="bogusNewGatedKey"):
        check_coverage(_SURVEY[0] | {"bogusNewGatedKey"}, OFF_LEDGER)


def test_the_checker_rejects_a_stale_row():
    padded = dict(OFF_LEDGER)
    padded["locationRegions"] = ("off_test", "test_gf_boss_locks.py::DungeonSweepOffSeed"
                                 "::test_sweeps_off_when_disabled", {"dungeon_sweep": "none"})
    with pytest.raises(AssertionError, match="locationRegions"):
        check_coverage(_SURVEY[0], padded)


def test_the_checker_rejects_a_test_that_leaves_the_option_on():
    # DungeonSweepFlags runs dungeon_sweep="all" -- the exact class the P1 `pass` body hid in.
    with pytest.raises(AssertionError, match="NOT testing the off state"):
        verify_row("dungeonSweepFlags",
                   ("off_test", "test_gf_boss_locks.py::DungeonSweepFlags"
                    "::test_sweep_flags_present_and_scoped", {"dungeon_sweep": "none"}))


def test_the_checker_rejects_a_missing_test():
    with pytest.raises(AssertionError, match="not found"):
        verify_row("dungeonSweepFlags",
                   ("off_test", "test_gf_boss_locks.py::DungeonSweepOffSeed"
                    "::test_that_was_never_written", {"dungeon_sweep": "none"}))


def test_the_checker_rejects_a_body_that_never_mentions_the_key():
    with pytest.raises(AssertionError, match="never mentions the key"):
        verify_row("dungeonSweepFlags",
                   ("absent_test", "test_gf_boss_locks.py::BossLocationsAll"
                    "::test_boss_data_nonempty_and_valid", "doctored row for the self-test"))


# ---------------------------------------------------------------------------------------------
# THE CATCH-ALL OFF WORLD -- off-state coverage for gated wires whose features have no test file
# of their own (reroll_enemy_drops / reroll_infinite_shop_stock had NO off-state coverage before
# the 2026-08-04 sweep). One world, every orphan gate pinned off.
# ---------------------------------------------------------------------------------------------

class RerollWiresOffSeed(WorldTestBase):
    game = GAME
    options = {"num_regions": 0,
               "reroll_enemy_drops": False,
               "reroll_infinite_shop_stock": False}

    def test_enemy_drop_wire_absent_when_off(self):
        leaked = "enemyDropRoll" in self.world.fill_slot_data()
        assert not leaked, (
            "enemyDropRoll emitted with reroll_enemy_drops off -- the client would re-roll enemy "
            "drop tables on a seed whose yaml said vanilla")

    def test_shop_stock_wire_absent_when_off(self):
        leaked = "shopInfiniteStock" in self.world.fill_slot_data()
        assert not leaked, (
            "shopInfiniteStock emitted with reroll_infinite_shop_stock off -- the client would "
            "restock shelves the yaml said to leave vanilla")

class AllClientFeatureGatesOffSeed(WorldTestBase):
    """requiresClientFeatures is a UNION key: features/auto_equip.py contributes "auto_equip",
    features/scaling.py contributes "scaling_ceiling" whenever the RESOLVED max difficulty caps
    below 100 -- and `auto` resolves below 100 on any partial map, so "leave everything default"
    does NOT reach the off state on most test seeds (AutoEquipOff's 2-region world emits
    ["scaling_ceiling"] legitimately). The off state = every producer pinned off, asserted here:
    the key must be ABSENT outright, because an old client refuses any seed whose
    requiresClientFeatures it cannot satisfy, and a phantom entry would lock players out of seeds
    that use nothing."""
    game = GAME
    options = {"num_regions": 0,
               "auto_equip": False,
               "maximum_enemy_difficulty": 100}

    def test_no_client_feature_demand_when_nothing_is_used(self):
        sd = self.world.fill_slot_data()
        demanded = sd.get("requiresClientFeatures", "<absent>")
        assert demanded == "<absent>", (
            "requiresClientFeatures = %r on a seed that uses no client-gated feature -- some "
            "producer is declaring a dependency it does not have, and every older client would "
            "refuse this seed for nothing" % (demanded,))
