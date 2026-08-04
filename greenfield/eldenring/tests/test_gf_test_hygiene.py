"""The test suite is a corpus too, and two of its decay modes are silent. Lint them, every run.

WHY THIS FILE EXISTS (inert-test audit, 2026-08-04, systemic findings #2 and #3). Two shapes of
inert test were found ALIVE in this suite, each by a one-off AST walk:

  * A WARN-ONLY BODY. `test_the_exemptions_still_exist` "failed" a stale _EDGE_EXEMPT entry by
    `warnings.warn(...)` -- injecting a bogus module gave **1 passed** with the warning scrolled
    off the log. A test whose only failure mode is a warning nobody reads is a comment wearing a
    green checkmark, and that file's own __main__ note had already conceded warnings scroll.
  * AN ASSERT-FREE BODY. `test_sweeps_off_when_disabled` had a body of literally `pass` and sat
    green while the feature's off-state went untested (finding P1; fixed in PR #360). One true
    positive out of ~950 test functions -- cheap to screen for, expensive to host.

The audit ran that walk ONCE. This file runs it on every push, so the next warn-only body and the
next pass-body turn CI red on the day they land instead of waiting for the next audit.

WHAT COUNTS AS AN ASSERT PATH -- fail-closed, but honest about the suite's real shapes, each of
which exists in the tree today and is pinned by a planted-source test below:
  * a lexical `assert` or `raise` anywhere in the function;
  * self.assert* / self.fail / pytest.fail / pytest.raises / pytest.xfail / pytest.warns;
  * a call to a module-LOCAL helper that itself has an assert path, transitively -- helpers
    holding the asserts are this suite's normal idiom (_check_x(...) styles), not an exemption;
  * a call to a name in _RAISING_DELEGATES -- a cross-module validator that raises on violation;
  * the MIRROR-LEG shape: the same module proves, inside `pytest.raises` / `assertRaises`, that
    this exact callable CAN raise -- so a bare no-raise call of it is a real assertion
    ("a guard that rejects everything is not a guard", test_gf_goal_choice.py). Derived from the
    module's own AST rather than allowlisted, so the exemption travels with the pattern and
    expires by itself if the raising legs are ever deleted.

WHAT DOES NOT COUNT, deliberately: "it ran without an exception" for an arbitrary callable. That
is the property every inert test already has, and accepting it would readmit the whole class.

Pure stdlib on purpose -- no AP import, no client checkout -- so it runs identically in the
`tests` job (installed world) and on any dev box, and can be run standalone:
    python test_gf_test_hygiene.py
"""
import ast
import os
import textwrap

_HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------------------------
# ALLOWLISTS. Small, explicit, and each entry is checked LIVE below (test_the_allowlists_are_live):
# a delegate nobody calls or a warn-only exemption naming a test that is no longer warn-only goes
# red until pruned. An allowlist that can grow (or rot) silently reproduces the disease this file
# screens for -- a stale _EDGE_EXEMPT row is the motivating case, one directory over.
# ---------------------------------------------------------------------------------------------

# Cross-module callables that RAISE on violation, so delegating the whole assertion to them is a
# legitimate no-assert body. By CALL NAME, not test name, so the exemption travels with the
# pattern: a new test using the same validator is fine; a new assert-free test that does not call
# a raising validator is not.
_RAISING_DELEGATES = {
    # contract.validate_slot_data(sd, strict=True) raises ContractViolation on any breach --
    # the `test_slot_data_passes_contract` bodies (test_gf_boss_keys.py, test_gf_boss_lock_items.py,
    # test_gf_slot_data_fixture.py) delegate to it. Audit section 5 cleared the shape explicitly.
    "validate_slot_data",
}

# (filename, qualified test name) pairs allowed to warn WITHOUT an assert path. EMPTY since
# 2026-08-04, when the one instance (test_the_exemptions_still_exist) was converted to a real
# failure, and the bar for an entry is high: a warning is only the right severity when the
# condition is a LEGAL state someone must merely notice -- and in that case the test almost
# always has a ratchet assert beside the warn already (test_the_debt_ledger_only_shrinks is the
# exemplar), which keeps it out of this lint's sights without an entry here.
_WARN_ONLY_ALLOWED = set()

# Floors for the scan itself (test_the_scan_is_not_vacuous). Measured 126 files / 977 test
# functions on 2026-08-04 (this file included); a scan that suddenly sees far fewer found a path bug, not a smaller
# suite, and a green from a scan of nothing is the lie this whole file exists to remove.
_MIN_FILES, _MIN_TESTS = 100, 900


# ---------------------------------------------------------------------------------------------
# The scanner. Everything below is derived from the AST -- string content never matters, so this
# file's own planted-offender sources do not trip it.
# ---------------------------------------------------------------------------------------------

_HARD_ASSERT_CALLS = {("pytest", "fail"), ("pytest", "raises"), ("pytest", "xfail"),
                      ("pytest", "warns")}


def _call_name(func):
    """Bare name a call resolves to for OUR purposes: `f(...)` -> f, `self._gen(...)` -> _gen."""
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_warn_call(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr == "warn" and isinstance(f.value, ast.Name) and f.value.id == "warnings"
    return isinstance(f, ast.Name) and f.id == "warn"


def _fn_signals(fn):
    """(called names, has a DIRECT assert, calls warnings.warn) -- lexical walk of one function."""
    names, direct, warns = set(), False, False
    for node in ast.walk(fn):
        if isinstance(node, (ast.Assert, ast.Raise)):
            direct = True
        elif isinstance(node, ast.Call):
            if _is_warn_call(node):
                warns = True
            f = node.func
            if isinstance(f, ast.Attribute):
                # self.assertEqual / self.assertFalse / self.fail / tc.assertRaises ...
                if f.attr == "fail" or f.attr.startswith("assert"):
                    direct = True
                if isinstance(f.value, ast.Name) and (f.value.id, f.attr) in _HARD_ASSERT_CALLS:
                    direct = True
            name = _call_name(f)
            if name:
                names.add(name)
    return names, direct, warns


def _functions_with_qualnames(tree):
    out = []

    def visit(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append((prefix + child.name, child))
                visit(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                visit(child, prefix + child.name + ".")
            else:
                visit(child, prefix)

    visit(tree, "")
    return out


def _proven_raisers(tree):
    """Names the module itself proves can raise: every callable invoked inside a
    `with pytest.raises(...)` / `with self.assertRaises(...)` block anywhere in the module."""
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        raising = False
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and _call_name(ctx.func) in ("raises", "assertRaises",
                                                                      "assertRaisesRegex"):
                raising = True
        if raising:
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call):
                        n = _call_name(sub.func)
                        if n:
                            names.add(n)
    return names


def _scan_source(src, filename):
    """-> list of dicts, one per test function: name, has_assert_path, warns_directly."""
    tree = ast.parse(src, filename=filename)
    fns = _functions_with_qualnames(tree)
    mirror = _proven_raisers(tree)

    # Module-local callables by bare name, for transitive helper resolution. Collect ALL
    # same-named definitions (two classes may share a method name) and OR them.
    local = {}
    for qual, node in fns:
        local.setdefault(node.name, []).append(node)

    memo = {}

    def has_assert_path(node, stack):
        if id(node) in memo:
            return memo[id(node)]
        if id(node) in stack:
            return False
        calls, direct, _ = _fn_signals(node)
        ok = (direct
              or bool(calls & _RAISING_DELEGATES)
              or bool(calls & mirror)
              or any(has_assert_path(cand, stack | {id(node)})
                     for name in calls if name in local
                     for cand in local[name] if cand is not node))
        memo[id(node)] = ok
        return ok

    records = []
    for qual, node in fns:
        # `test` prefix, not `test_`: unittest collects any method starting with "test", and a
        # lint that screens a narrower set than the runners collect has a hole exactly there.
        if not node.name.startswith("test"):
            continue
        _, _, warns = _fn_signals(node)
        records.append({"name": qual, "assert_path": has_assert_path(node, frozenset()),
                        "warns": warns})
    return records


def _scan_tree(root=_HERE):
    """filename -> records, for every test_*.py beside this file (the convention run_ci and
    gf_test.py both install and collect)."""
    out = {}
    for fn in sorted(os.listdir(root)):
        if fn.startswith("test_") and fn.endswith(".py"):
            with open(os.path.join(root, fn), encoding="utf-8") as fh:
                out[fn] = _scan_source(fh.read(), fn)
    return out


# ---------------------------------------------------------------------------------------------
# THE MOTIVATING CASES, planted and watched fail (CONTRIBUTING rule 11: the case that motivated
# the change IS the acceptance test -- and per the audit's own rule, an unfired guard is
# untested). Each offender below is the audited defect, verbatim in shape.
# ---------------------------------------------------------------------------------------------

_PLANTED_WARN_ONLY = textwrap.dedent('''
    import warnings
    def test_the_ledger_is_fresh():
        stale = ["totally_bogus_module_that_never_existed"]
        if stale:
            warnings.warn("stale: %s -- prune them" % stale)
''')

_PLANTED_PASS_BODY = textwrap.dedent('''
    class DungeonSweepFlags:
        def test_sweeps_off_when_disabled(self):
            pass
''')

_PLANTED_RAN_WITHOUT_ERROR = textwrap.dedent('''
    def _emit(mode):
        return {"flags": mode}
    def test_emission_runs():
        _emit("all")   # completing is not an assertion -- every inert test "completes"
''')

_PLANTED_LEGIT_SHAPES = textwrap.dedent('''
    import pytest, warnings
    def _check_rungs(rows):
        assert rows, "helper holds the assert -- the suite's normal idiom"
    def test_via_local_helper():
        _check_rungs([1])
    class C:
        def test_via_delegate(self):
            validate_slot_data({}, strict=True)
        def _generate(self, **kw):
            return kw
        def test_illegal_pairing_raises(self):
            with pytest.raises(ValueError):
                self._generate(bad=True)
        def test_the_legal_pairings_do_not_raise(self):
            self._generate(good=True)   # mirror leg: the raises test above proves _generate CAN
        def test_warns_but_also_asserts(self):
            warnings.warn("informational, beside a live assert -- the debt-ledger shape")
            assert True is not False
''')


def test_the_lint_flags_a_planted_warn_only_body():
    """RED CASE #1, the exact P3 shape: warn on staleness, no assert path, 1 passed."""
    rec = {r["name"]: r for r in _scan_source(_PLANTED_WARN_ONLY, "<planted>")}
    r = rec["test_the_ledger_is_fresh"]
    assert r["warns"] and not r["assert_path"], (
        "the scanner no longer flags the audited warn-only shape (warn + no assert path) -- the "
        "lint below is scanning with a hole exactly where the motivating defect lives")


def test_the_lint_flags_a_planted_assert_free_body():
    """RED CASE #2, the exact P1 shape: a `pass` body -- and the ran-without-error variant."""
    rec = {r["name"]: r for r in _scan_source(_PLANTED_PASS_BODY, "<planted>")}
    assert not rec["DungeonSweepFlags.test_sweeps_off_when_disabled"]["assert_path"], (
        "the scanner credits a literal `pass` body with an assert path")
    rec = {r["name"]: r for r in _scan_source(_PLANTED_RAN_WITHOUT_ERROR, "<planted>")}
    assert not rec["test_emission_runs"]["assert_path"], (
        "the scanner credits 'called a local helper that asserts nothing' as an assert path -- "
        "'it ran without an exception' is the one property every inert test already has")


def test_the_lint_accepts_the_suites_legitimate_shapes():
    """The four real no-lexical-assert shapes in this tree must NOT be flagged -- a lint that
    cries wolf gets an allowlist bolted on, and a growing allowlist is the disease itself."""
    rec = {r["name"]: r for r in _scan_source(_PLANTED_LEGIT_SHAPES, "<planted>")}
    for name in ("test_via_local_helper", "C.test_via_delegate",
                 "C.test_the_legal_pairings_do_not_raise", "C.test_warns_but_also_asserts"):
        assert rec[name]["assert_path"], "%s is a legitimate shape and the scanner flags it" % name
    assert not (rec["C.test_warns_but_also_asserts"]["warns"]
                and not rec["C.test_warns_but_also_asserts"]["assert_path"]), (
        "warn-BESIDE-assert (the debt-ledger shape) must stay legal; only warn-INSTEAD-OF-assert "
        "is the defect")


def test_the_mirror_leg_exemption_expires_with_its_raising_legs():
    """Delete the pytest.raises legs and the bare no-raise call stops counting -- the derived
    exemption must decay WITH the evidence, or it is an allowlist that grew itself."""
    src = _PLANTED_LEGIT_SHAPES.replace("with pytest.raises(ValueError):", "if True:")
    rec = {r["name"]: r for r in _scan_source(src, "<planted>")}
    assert not rec["C.test_the_legal_pairings_do_not_raise"]["assert_path"], (
        "the mirror-leg credit survived deletion of the raises leg that justified it")


# ---------------------------------------------------------------------------------------------
# THE LINTS, over the real tree.
# ---------------------------------------------------------------------------------------------

def test_no_warn_only_test_bodies():
    """Systemic guard #2: a test that 'fails' by emitting a warning nobody reads is inert.

    The `generators` CI job pipes script runs through `tail -5` and pytest only surfaces warnings
    in a summary column nobody gates on -- both sinks scroll. If the condition is worth a test it
    is worth a failure; if a warning is genuinely the right severity, the test needs a ratchet
    assert BESIDE the warn (test_the_debt_ledger_only_shrinks is the exemplar, and then this lint
    ignores it) or, failing that, an entry in _WARN_ONLY_ALLOWED with a reason a reader can check.
    """
    hits = sorted("%s::%s" % (f, r["name"])
                  for f, recs in _scan_tree().items() for r in recs
                  if r["warns"] and not r["assert_path"]
                  and (f, r["name"]) not in _WARN_ONLY_ALLOWED)
    assert not hits, (
        "%d test function(s) call warnings.warn with NO assert path -- their failure mode is a "
        "line that scrolls:\n  %s\n"
        "Convert the warn to a failure (the default), put a ratchet assert beside it if the "
        "warned condition is a legal state, or -- rarely -- add (filename, qualname) to "
        "_WARN_ONLY_ALLOWED with a reason. This is the exact shape that let a stale _EDGE_EXEMPT "
        "entry pass green on 2026-08-04." % (len(hits), "\n  ".join(hits)))


def test_every_test_function_has_an_assert_path():
    """Systemic guard #3, the assertion census: a test that cannot fail is a checkmark, not a test.

    One true positive in ~950 functions on 2026-08-04 (a literal `pass` body that had sat green
    while its feature's off-state went untested) -- so this is nearly noise-free, and anything it
    flags deserves the question. Delegating to a raising validator or a mirror-leg no-raise call
    both count (see the module docstring); 'it ran without an exception' does not.
    """
    hits = sorted("%s::%s" % (f, r["name"])
                  for f, recs in _scan_tree().items() for r in recs
                  if not r["assert_path"])
    assert not hits, (
        "%d test function(s) have NO assert path -- no assert/raise, no self.assert*/fail, no "
        "pytest.raises, no asserting local helper, no raising delegate, no mirror leg:\n  %s\n"
        "Give each a real assertion. If it delegates to a cross-module validator that RAISES on "
        "violation, add that validator's CALL NAME to _RAISING_DELEGATES (never the test's name "
        "-- the exemption must travel with the pattern). If it is the no-raise mirror of a "
        "pytest.raises test, keep both in the same module and the credit is derived automatically."
        % (len(hits), "\n  ".join(hits)))


def test_the_scan_is_not_vacuous():
    """A lint that scanned nothing reports nothing -- pin the corpus size and the parse."""
    tree = _scan_tree()
    ntests = sum(len(v) for v in tree.values())
    assert len(tree) >= _MIN_FILES and ntests >= _MIN_TESTS, (
        "scanned %d files / %d test functions, expected >= %d / >= %d (126/977 measured "
        "2026-08-04). Either the suite shrank drastically -- update the floors and say why -- or "
        "this file is no longer scanning the directory the tests actually live in."
        % (len(tree), ntests, _MIN_FILES, _MIN_TESTS))
    assert "test_gf_test_hygiene.py" in tree, "the lint no longer scans itself"


def test_the_allowlists_are_live():
    """Every exemption must correspond to something in the tree TODAY, or it is a stale ledger row
    -- the precise decay this branch exists to make loud. Prune on green, never park."""
    tree = _scan_tree()
    all_calls = set()
    for fn in tree:
        with open(os.path.join(_HERE, fn), encoding="utf-8") as fh:
            for node in ast.walk(ast.parse(fh.read(), filename=fn)):
                if isinstance(node, ast.Call):
                    n = _call_name(node.func)
                    if n:
                        all_calls.add(n)
    dead = sorted(d for d in _RAISING_DELEGATES if d not in all_calls)
    assert not dead, (
        "_RAISING_DELEGATES entries %s are called by nothing in the tree -- a dead exemption "
        "reads as coverage. Delete them (re-add with the pattern that needs them)." % dead)
    current = {(f, r["name"]) for f, recs in tree.items() for r in recs
               if r["warns"] and not r["assert_path"]}
    stale = sorted("%s::%s" % e for e in _WARN_ONLY_ALLOWED if e not in current)
    assert not stale, (
        "_WARN_ONLY_ALLOWED names %s, which are no longer warn-only tests (fixed, renamed, or "
        "gone). Delete the row(s) -- a stale exemption is how the 2026-07-31 shop_preview alarm "
        "was silenced." % stale)


if __name__ == "__main__":
    # Standalone entry point, same convention as the repo-only suites: usable on any checkout
    # (pure stdlib), exits nonzero on a violation so shell loops cannot swallow it.
    import sys
    failures = 0
    for t in (test_the_lint_flags_a_planted_warn_only_body,
              test_the_lint_flags_a_planted_assert_free_body,
              test_the_lint_accepts_the_suites_legitimate_shapes,
              test_the_mirror_leg_exemption_expires_with_its_raising_legs,
              test_no_warn_only_test_bodies,
              test_every_test_function_has_an_assert_path,
              test_the_scan_is_not_vacuous,
              test_the_allowlists_are_live):
        try:
            t()
            print("ok    %s" % t.__name__)
        except AssertionError as exc:
            failures += 1
            print("FAIL  %s\n%s" % (t.__name__, exc))
    sys.exit(1 if failures else 0)
