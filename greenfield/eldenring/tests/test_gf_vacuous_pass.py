"""A test that examined NOTHING is a checkmark, not a test (2026-08-05).

Sibling to `test_gf_test_hygiene.py`, which asks whether a test *can* fail (has an assert path, is
not warn-only). This file asks the next question: whether it *looked at anything*. Both are the same
disease -- a green tick that carries no information -- and this repo keeps catching new strains:

  * 2026-08-04 audit: `test_sweeps_off_when_disabled`'s body was `pass`; `test_sealed_boss_regions_
    excluded` was an `all()` over a list of measured length 1.
  * 2026-08-05, piece B of SPEC-broaden-sweeps: a new invariant test read region_map's raw `map`
    column, which is `PENDING` for exactly the `global`/`global_filler` rows it existed to protect.
    It had an assert path, it ran ~4900 rows, and its final predicate could never match. Green, and
    blind. Only a mutation -- deleting the members it guards -- exposed it.

TWO guards, because the two shapes need different instruments:

1. `all()`/`any()` over an EMPTY iterable is unambiguously vacuous, and is caught at RUNTIME by the
   spy in `conftest.py` (the one buildable guard from the 08-04 list that had not been built). The
   tests here are that spy's own red cases.
2. The `for ... bad.append(...)` / `assertEqual(bad, [])` shape cannot be judged statically -- a
   filter matching nothing today may be perfectly correct. What CAN be required is a WITNESS: an
   assertion showing the scan saw something. Since 2026-09-07 the witness has to be TIED TO THAT
   SCAN -- it must mention the iterable, a loop variable, a counter, or an input the filter reads
   (see "what tied to the scan means" below). Before that any positive assertion counted, and 31
   tests on main were green on a decorative `assertTrue` about something else, which is the
   ratchet being satisfied instead of the test being fixed. 177 of this suite's 559
   empty-assertions have no tied witness, which is too many to fix in one pass and exactly why this
   is a RATCHET on the count rather than an exemption list of names. The number may go DOWN freely.
   It may not go up -- and going up by one for a genuinely new test is a one-line edit here with a
   dated note, not a reason to add an assertion that proves nothing.
"""
import ast
import builtins
import glob
import importlib.util
import os
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- the spy's red cases

def _conftest():
    spec = importlib.util.spec_from_file_location("gf_conftest_under_test",
                                                  os.path.join(HERE, "conftest.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_skip_census_records_once_under_xdist(tmp_path, monkeypatch):
    """RED CASE (#778): xdist runs the report hook in a worker and again in the controller.

    Recording both makes an unchanged skip inventory look exactly twice as large. The controller
    owns the complete report stream, so the worker copy must be inert while the controller copy
    still writes the one real skip.
    """
    m = _conftest()
    out = tmp_path / "skips.jsonl"
    monkeypatch.setenv("GF_SKIP_CENSUS_OUT", str(out))
    report = SimpleNamespace(skipped=True, context=None,
                             longrepr=("test_x.py", 1, "Skipped: deliberate"),
                             nodeid="test_x.py::test_x", when="setup")

    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    m.pytest_runtest_logreport(report)
    assert not out.exists(), "the worker wrote the duplicate skip report"

    monkeypatch.delenv("PYTEST_XDIST_WORKER")
    m.pytest_runtest_logreport(report)
    rows = out.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1 and '"reason": "deliberate"' in rows[0], rows


def test_the_spy_records_an_empty_quantifier():
    """RED CASE: `all([])` is True and tells you nothing. The spy must say so."""
    m = _conftest()
    m._QSPY_HITS.clear()
    m._QSPY_DIR = HERE                       # this file counts as suite code for the test
    spied = m._qspy_wrap(_raw_all, "all")
    assert spied([]) is True, "the spy must not change what all() returns"
    assert m._QSPY_HITS, "an all() over an empty iterable was NOT recorded -- the spy is inert"
    assert m._QSPY_HITS[0].startswith("test_gf_vacuous_pass.py::"), m._QSPY_HITS
    assert "all()" in m._QSPY_HITS[0], m._QSPY_HITS


def _raw_all(iterable):
    """A pristine `all`, for the red cases below.

    🛑 They must NOT wrap the global builtin. When the spy is ACTIVE -- which it is in CI -- the
    global is already the wrapper, so `_qspy_wrap` correctly refuses to wrap it again and the test
    ends up asserting against a wrapper that writes into the INSTALLED conftest's lists rather than
    the freshly-exec'd module's. Both behaviours are right; wrapping the global was the mistake, and
    it made these three tests fail in CI while passing locally with the spy off."""
    for v in iterable:
        if not v:
            return False
    return True


def test_the_spy_refuses_to_DOUBLE_WRAP():
    """RED CASE, and a bug the spy found in itself during its first CI run.

    Wrapping an already-wrapped `all` makes the inner copy observe the outer copy's own `fn(())` and
    report `conftest.py::wrapper all()` -- the diagnostic reporting its own plumbing. It matters
    because the red cases below deliberately wrap the GLOBAL builtin, which is already patched when
    the spy is active."""
    m = _conftest()
    once = m._qspy_wrap(_raw_all, "all")
    assert m._qspy_wrap(once, "all") is once, "double-wrapping was not refused"


def test_the_spy_is_quiet_on_a_real_quantifier():
    """...and a lint that fires on legitimate shapes is a lint people learn to ignore."""
    m = _conftest()
    m._QSPY_HITS.clear()
    m._QSPY_DIR = HERE
    spied = m._qspy_wrap(_raw_all, "all")
    m._QSPY_SEEN.clear()
    assert spied([True, True]) is True
    assert spied([True, False]) is False
    assert not m._QSPY_HITS, "the spy fired on a NON-empty iterable: %r" % (m._QSPY_HITS,)
    assert m._QSPY_SEEN, ("a non-empty call was not recorded in _QSPY_SEEN -- without that, a STALE "
                          "waiver can never be detected")


def test_the_spy_preserves_laziness_and_short_circuit():
    """It pulls ONE element to decide emptiness and chains it back.

    If it materialised the iterable instead, `all()` would stop short-circuiting -- which is a
    behaviour change smuggled in by a diagnostic, and the kind of thing that makes a suite slower and
    subtly different for no stated reason."""
    m = _conftest()
    m._QSPY_DIR = HERE
    pulled = []

    def gen():
        for v in (True, False, True):
            pulled.append(v)
            yield v

    assert m._qspy_wrap(_raw_all, "all")(gen()) is False
    assert pulled == [True, False], ("all() consumed %r -- it must stop at the first False, exactly "
                                     "as the unwrapped builtin does" % (pulled,))


def test_the_verdict_flags_an_unwaived_empty_site():
    """RED CASE: an empty quantifier nobody has ruled on must fail the run."""
    m = _conftest()
    unwaived, stale = m._qspy_verdict({"a.py::f all()"}, {"a.py::f all()"}, {})
    assert unwaived == ["a.py::f all()"] and stale == [], (unwaived, stale)


def test_the_verdict_flags_a_STALE_waiver():
    """RED CASE, the other direction: a waived site that RAN and was never empty is protecting
    nothing. 'An exclusion that matches nothing is a lie.'"""
    m = _conftest()
    unwaived, stale = m._qspy_verdict(set(), {"a.py::f any()"}, {"a.py::f any()": "reason"})
    assert stale == ["a.py::f any()"] and unwaived == [], (unwaived, stale)


def test_the_verdict_is_quiet_about_a_waiver_whose_file_never_ran():
    """...and NOT stale when the site simply did not execute -- otherwise every chunked run would
    condemn the waivers belonging to the other chunks."""
    m = _conftest()
    unwaived, stale = m._qspy_verdict(set(), set(), {"a.py::f any()": "reason"})
    assert (unwaived, stale) == ([], []), (unwaived, stale)


def test_every_waiver_is_documented():
    """A waiver list is a claim, and a one-word reason is not one.

    The staleness half is enforced at RUNTIME by conftest (a waived site that runs and is never
    empty fails the spy run). This half is what can be checked without the spy: that every entry
    says WHY the empty case is the correct reading."""
    import json as _json
    path = os.path.join(HERE, "expected_vacuous_quantifiers.json")
    waived = _json.load(open(path, encoding="utf-8"))
    bad = [k for k, v in waived.items() if len(str(v).split()) < 12]
    assert not bad, ("waiver(s) with no real reason: %r. Say why an EMPTY iterable is the correct "
                     "answer at that site, or fix the site." % bad)
    shape = [k for k in waived if "::" not in k or not k.endswith(("all()", "any()"))]
    assert not shape, ("waiver key(s) not in `file.py::function all()` form: %r -- the spy keys on "
                       "the function, not the line, so a drifting line number cannot orphan it"
                       % shape)


# ------------------------------------------------------------------- the witness ratchet (shape 2)

_EMPTY_ASSERTS = ("assertEqual", "assertListEqual", "assertSetEqual", "assertCountEqual")
_POSITIVE = ("assertTrue", "assertIn", "assertGreater", "assertGreaterEqual", "assertNotEqual",
             "assertIsNotNone", "assertLess", "assertLessEqual")
# Calls that merely re-shape the collection under test: `assertEqual(sorted(bad), [])` is about
# `bad`. A call to anything else is code under test, and every name in it is part of the scan.
_WRAPPERS = frozenset({"sorted", "list", "set", "len", "tuple", "dict", "frozenset", "sum", "bool"})
_MUTATORS = frozenset({"append", "add", "extend", "update", "setdefault", "insert", "discard",
                       "remove"})
_IGNORED_ROOTS = frozenset(dir(builtins)) | {"self", "cls"}


def _is_empty_literal(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return not node.elts
    if isinstance(node, ast.Dict):
        return not node.keys
    return isinstance(node, ast.Constant) and node.value == 0 and node.value is not False


def _is_not(node):
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)


def _empty_side(a, b):
    """The expression `a` asserts EMPTY against literal `b`, or None. A bare `0` counts only
    against `len(x)`/`sum(x)` (the subject is then `x`): `assertEqual(tool.main(), 0)` is an exit
    code, not an emptiness claim, and reading it as one flagged 75 tests for the wrong reason."""
    if not _is_empty_literal(b):
        return None
    if isinstance(b, ast.Constant) and b.value == 0:
        if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) \
                and a.func.id in ("len", "sum") and a.args:
            return ast.unparse(a.args[0])
        return None
    return ast.unparse(a)


def _empty_assert_subjects(fn):
    """Expressions this test asserts are EMPTY -- the ones that pass when the scan saw nothing."""
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in _EMPTY_ASSERTS and len(n.args) >= 2:
                subject = _empty_side(n.args[0], n.args[1]) or _empty_side(n.args[1], n.args[0])
                if subject:
                    out.append(subject)
            elif n.func.attr == "assertFalse" and n.args:
                out.append(ast.unparse(n.args[0]))
        elif isinstance(n, ast.Assert) and _is_not(n.test):
            out.append(ast.unparse(n.test.operand))
    return out


# ---------------------------------------------------------------- what "tied to the scan" means
#
# A witness has to say the SCAN saw candidates -- not that some unrelated thing is truthy. So the
# lint first works out what the scan IS, as a set of dotted names, and then only an assertion that
# mentions one of them counts. In order:
#
#   seeds     every name in the empty-asserted expression except the accumulator itself
#             (`assertEqual(trap_items(w), [])` -> {trap_items, w}); for a local accumulator, the
#             iterable, loop targets and everything READ in the body of any loop that feeds it
#             (`for r in rows: if bad(r): out.append(r)` -> {rows, r, bad}), plus the right-hand
#             side of any assignment to it; reads inside a nested helper the loop calls count too.
#   closure   names co-assigned with a seed, forwards (`n = len(rows)`) and one step backwards
#             (`missing = surface - block` pulls in surface and block), through `for` targets and
#             `with ... as` bindings, until nothing new appears.
#
# Builtins and bare `self`/`cls` are never names in this sense, so `len`, `set` and `self.assertX`
# cannot tie anything to anything. `self.groups` can: dotted attribute chains are keys.


def _key(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _keys(node):
    """Dotted names read anywhere under `node`, minus builtins and a bare self/cls."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.Name, ast.Attribute)):
            k = _key(n)
            if not k or k in ("self", "cls"):
                continue
            root = k.split(".")[0]
            if root in ("self", "cls") or root not in _IGNORED_ROOTS:
                out.add(k)
    return out


def _targets(node):
    return {k for k in (_key(n) for n in ast.walk(node)
                        if isinstance(n, (ast.Name, ast.Attribute))) if k}


def _locals_of(fn):
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                out |= _targets(t)
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign, ast.For, ast.comprehension)):
            out |= _targets(n.target)
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            out |= _targets(n.optional_vars)
    return out


def _accumulator(expr):
    """The local collection an emptiness assertion is about, unwrapped from sorted()/list()/len()
    and subscripts; None when the subject is a call into code under test."""
    while isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) \
            and expr.func.id in _WRAPPERS and expr.args:
        expr = expr.args[0]
    if isinstance(expr, ast.Call):
        return None
    while isinstance(expr, ast.Subscript):
        expr = expr.value
    return _key(expr)


def _assigns_to(node, acc):
    if isinstance(node, ast.Assign):
        return any(_targets(t) & acc for t in node.targets)
    return isinstance(node, ast.AugAssign) and bool(_targets(node.target) & acc)


def _scan_names(fn, subjects):
    """(accumulators, seed names) for this test -- see the block comment above."""
    local = _locals_of(fn)
    helpers = {n.name: n for n in ast.walk(fn) if isinstance(n, ast.FunctionDef) and n is not fn}
    acc, seeds = set(), set()
    for text in subjects:
        expr = ast.parse(text, mode="eval").body
        a = _accumulator(expr)
        if a is not None and a in local:
            acc.add(a)
        seeds |= _keys(expr) - {a}
    for n in ast.walk(fn):
        if isinstance(n, ast.For):
            feeds = any((isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                         and c.func.attr in _MUTATORS and _key(c.func.value) in acc)
                        or _assigns_to(c, acc)
                        for b in n.body for c in ast.walk(b))
            if feeds:
                seeds |= _keys(n.iter) | _targets(n.target)
                for b in n.body:
                    seeds |= _keys(b)
                    for c in ast.walk(b):
                        if isinstance(c, ast.Assign):
                            for t in c.targets:
                                seeds |= _targets(t)
                        elif isinstance(c, (ast.AugAssign, ast.For)):
                            seeds |= _targets(c.target)
                for name in list(seeds):
                    if name in helpers:
                        seeds |= _keys(helpers[name])
        elif _assigns_to(n, acc):
            seeds |= _keys(n.value)
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    seeds |= _targets(t)
            for c in ast.walk(n.value):
                if isinstance(c, ast.comprehension):
                    seeds |= _keys(c.iter) | _targets(c.target)
    return acc, seeds - acc


def _closure(fn, names, acc):
    changed = True
    while changed:
        changed = False
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                ts = set().union(*(_targets(t) for t in n.targets))
                vs = _keys(n.value)
                if vs & names or ts & names:
                    new = (ts | vs) - names - acc
                    if new:
                        names |= new
                        changed = True
            elif isinstance(n, ast.For) and _keys(n.iter) & names:
                new = _targets(n.target) - names - acc
                if new:
                    names |= new
                    changed = True
            elif isinstance(n, ast.withitem) and n.optional_vars is not None \
                    and _keys(n.context_expr) & names:
                new = _targets(n.optional_vars) - names - acc
                if new:
                    names |= new
                    changed = True
    return names


def _has_witness(fn, subjects):
    """A positive assertion that mentions the scan the empty-checked collection came from.

    Before 2026-09-07 ANY positive assertion counted, and the ratchet could be kept green by a
    decorative `assertTrue` about something else. 31 tests on main had exactly that shape."""
    acc, names = _scan_names(fn, subjects)
    names = _closure(fn, names, acc)
    subs = set(subjects)
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in _POSITIVE and n.args and ast.unparse(n.args[0]) not in subs \
                    and _keys(n) & names:
                return True
            if n.func.attr in _EMPTY_ASSERTS and len(n.args) >= 2 \
                    and not _is_empty_literal(n.args[0]) and not _is_empty_literal(n.args[1]) \
                    and ast.unparse(n.args[0]) not in subs and _keys(n) & names:
                return True
        elif isinstance(n, ast.Assert) and not _is_not(n.test) and _keys(n.test) & names:
            return True
    return False


def _scan(paths):
    total, witnessless = 0, []
    for path in paths:
        tree = ast.parse(open(path, encoding="utf-8").read())
        for fn in [n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]:
            subjects = _empty_assert_subjects(fn)
            if not subjects:
                continue
            total += 1
            if not _has_witness(fn, subjects):
                witnessless.append((os.path.basename(path), fn.name))
    return total, witnessless


def _suite_files():
    return sorted(glob.glob(os.path.join(HERE, "test_*.py")))


# Measured by THIS scan, 2026-08-05: **152 on main**, and **154** on the tree that also carries
# SPEC-broaden-sweeps pieces A and C (PR #386, two more invariant tests of the collect-and-assert-
# empty shape). The ceiling was set to 154 so the ratchet would not go red the moment #386 landed --
# stated rather than hidden, because a ceiling with undisclosed headroom is how a ratchet quietly
# stops ratcheting.
#
# 2026-08-10: #386 is on main and the headroom is now SPENT -- 154 is the measured value, with no
# slack left in it. It earned that the same day: the trap-items suite (#515) landed two off-case
# tests whose `trap_items(...) == []` would have passed just as happily if the minter were dead, the
# count went to 156, and BOTH were fixed with real on-case witnesses rather than by moving this
# number. That is the intended response to a red here.
# GOING DOWN IS ALWAYS FINE -- lower it whenever you add a witness. Going UP means a new test was
# written that passes without looking at anything, which is the whole point of this file.
# 2026-08-14: 154 -> 153. test_gf_contract_versions' tag-derived rewrite retired one
# witnessless test (test_every_tagged_version_is_recorded_as_shipped) and added two that
# DO carry witnesses -- net -1. Lowered here in the same PR, per the line above.
# 2026-09-07: 153 -> 152. #1463 landed test_gf_profile_declaration.py with two witnessless
# collect-and-assert-empty tests, which put the branch at 154 over a 153 ceiling -- red, and paid
# here rather than by moving the number up. #1466 gave all of them real witnesses (each now pins a
# key every seed emits, so a fill_slot_data that returned {} can no longer read as "no foreign
# keys") and added three more tests that carry witnesses from the start. Net -1 against main.
# 2026-09-07: 152 -> 177, a RE-BASELINE, not a regression. The witness now has to be tied to the
# scan (block comment above _has_witness). Two things moved at once: `== 0` against anything but
# len()/sum() stopped counting as an emptiness claim (exit codes; 75 tests left the population,
# 634 -> 559), and 31 tests whose only witness was about something else stopped counting as
# witnessed. Measured by this scan on main @ 3f5c9d13. Every one of the 31 is a real gap: the
# test would pass identically if its scan matched nothing.
_WITNESSLESS_CEILING = 177


def test_no_new_witnessless_empty_assertions():
    """Ratchet, not a fix. A count, not a name list -- 154 is far too many to exempt individually,
    and an exemption list that long is scenery rather than protection."""
    total, witnessless = _scan(_suite_files())
    assert total >= 200, ("the scan found only %d empty-assertion test(s); it has stopped seeing the "
                          "suite and this ratchet is now vacuous itself" % total)
    assert len(witnessless) <= _WITNESSLESS_CEILING, (
        "%d test(s) assert a collection is empty without any assertion that the scan SAW anything, "
        "up from the %d ceiling. A test whose filter stops matching then passes for the same reason "
        "it would pass if the code were right. Add a witness -- assert the candidate set is "
        "non-empty -- or say here why this one cannot have it. This ratchet COUNTS, it does not "
        "diff: the tests listed here are the last six by filename, NOT necessarily the new ones. "
        "Look in the test files your branch added or touched. Last six: %r"
        % (len(witnessless), _WITNESSLESS_CEILING, witnessless[-6:]))


def test_the_lint_flags_a_planted_witnessless_body(tmp_path):
    """RED CASE for the ratchet itself."""
    p = tmp_path / "test_planted.py"
    p.write_text("def test_x():\n    bad = []\n    for i in []:\n        bad.append(i)\n"
                 "    assert not bad\n", encoding="utf-8")
    total, witnessless = _scan([str(p)])
    assert total == 1 and len(witnessless) == 1, (total, witnessless)


def test_the_lint_rejects_a_decorative_witness(tmp_path):
    """RED CASE for the tie: a positive assertion about something UNRELATED to the scan is not a
    witness. This is the body that kept the old ratchet green while proving nothing."""
    p = tmp_path / "test_planted_decorative.py"
    p.write_text("def test_x():\n    cands = []\n    other = [1]\n    bad = []\n    for i in cands:\n"
                 "        bad.append(i)\n    assert other, 'decorative'\n    assert not bad\n",
                 encoding="utf-8")
    total, witnessless = _scan([str(p)])
    assert total == 1 and len(witnessless) == 1, (total, witnessless)


def test_the_lint_ties_through_assignment_and_helpers(tmp_path):
    """The witness may sit one hop away: on a counter kept in the loop, on an input the filter
    reads, or on the operands the accumulator was computed from."""
    p = tmp_path / "test_planted_tied.py"
    p.write_text(
        "def test_counter():\n    seen = 0\n    bad = []\n    for r in rows():\n        seen += 1\n"
        "        bad.append(r)\n    assert seen > 10\n    assert not bad\n"
        "def test_operands():\n    surface, block = a(), b()\n"
        "    missing = sorted(set(surface) - set(block))\n    assert len(surface) > 40\n"
        "    assert not missing\n"
        "def test_exit_code_is_not_emptiness():\n    assert tool.main() == 0\n",
        encoding="utf-8")
    total, witnessless = _scan([str(p)])
    assert total == 2 and witnessless == [], (total, witnessless)


def test_the_lint_accepts_a_witnessed_body(tmp_path):
    """...and the same test with a witness must NOT be flagged."""
    p = tmp_path / "test_planted_ok.py"
    p.write_text("def test_x():\n    cands = [1]\n    bad = []\n    for i in cands:\n"
                 "        bad.append(i) if False else None\n"
                 "    assert cands, 'nothing to scan'\n    assert not bad\n", encoding="utf-8")
    total, witnessless = _scan([str(p)])
    assert total == 1 and witnessless == [], (total, witnessless)


def test_the_scan_is_not_vacuous():
    """This file's own dogfood: a lint whose file list is empty reports a clean bill of health."""
    files = _suite_files()
    assert len(files) > 50, "the suite scan found %d files; it is not reading the suite" % len(files)
