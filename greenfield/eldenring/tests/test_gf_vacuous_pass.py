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
   filter matching nothing today may be perfectly correct. What CAN be required is a WITNESS: some
   other assertion showing the scan saw something. 154 of this suite's 266 empty-assertions have
   none, which is too many to fix in one pass and exactly why this is a RATCHET on the count rather
   than an exemption list of names. The number may go DOWN freely. It may not go up.
"""
import ast
import glob
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- the spy's red cases

def _conftest():
    spec = importlib.util.spec_from_file_location("gf_conftest_under_test",
                                                  os.path.join(HERE, "conftest.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_spy_records_an_empty_quantifier():
    """RED CASE: `all([])` is True and tells you nothing. The spy must say so."""
    m = _conftest()
    m._QSPY_HITS.clear()
    m._QSPY_DIR = HERE                       # this file counts as suite code for the test
    spied = m._qspy_wrap(all, "all")
    assert spied([]) is True, "the spy must not change what all() returns"
    assert m._QSPY_HITS, "an all() over an empty iterable was NOT recorded -- the spy is inert"
    assert m._QSPY_HITS[0].startswith("test_gf_vacuous_pass.py::"), m._QSPY_HITS
    assert "all()" in m._QSPY_HITS[0], m._QSPY_HITS


def test_the_spy_is_quiet_on_a_real_quantifier():
    """...and a lint that fires on legitimate shapes is a lint people learn to ignore."""
    m = _conftest()
    m._QSPY_HITS.clear()
    m._QSPY_DIR = HERE
    spied = m._qspy_wrap(all, "all")
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

    assert m._qspy_wrap(all, "all")(gen()) is False
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


def _is_empty_literal(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return not node.elts
    if isinstance(node, ast.Dict):
        return not node.keys
    return isinstance(node, ast.Constant) and node.value == 0 and node.value is not False


def _empty_assert_subjects(fn):
    """Expressions this test asserts are EMPTY -- the ones that pass when the scan saw nothing."""
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in _EMPTY_ASSERTS and len(n.args) >= 2:
                if _is_empty_literal(n.args[1]):
                    out.append(ast.unparse(n.args[0]))
                elif _is_empty_literal(n.args[0]):
                    out.append(ast.unparse(n.args[1]))
            elif n.func.attr == "assertFalse" and n.args:
                out.append(ast.unparse(n.args[0]))
        elif isinstance(n, ast.Assert) and isinstance(n.test, ast.UnaryOp) \
                and isinstance(n.test.op, ast.Not):
            out.append(ast.unparse(n.test.operand))
    return out


def _has_witness(fn, subjects):
    """Any assertion about something OTHER than the empty-checked collection.

    Deliberately generous: a bare `assert <expr>`, or any positive unittest assertion whose subject
    is not the collection under test, counts. The point is not to grade the witness -- it is that
    SOMETHING in the test says "I saw candidates", so a scan that silently stops matching goes red."""
    subs = set(subjects)
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in _POSITIVE and n.args and ast.unparse(n.args[0]) not in subs:
                return True
            if n.func.attr in _EMPTY_ASSERTS and len(n.args) >= 2 \
                    and not _is_empty_literal(n.args[0]) and not _is_empty_literal(n.args[1]) \
                    and ast.unparse(n.args[0]) not in subs:
                return True
        elif isinstance(n, ast.Assert):
            if not (isinstance(n.test, ast.UnaryOp) and isinstance(n.test.op, ast.Not)):
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
# empty shape). The ceiling is set to 154 so the ratchet does not go red the moment #386 lands --
# stated rather than hidden, because a ceiling with undisclosed headroom is how a ratchet quietly
# stops ratcheting. Drop it back to the measured value once #386 is on main.
# GOING DOWN IS ALWAYS FINE -- lower it whenever you add a witness. Going UP means a new test was
# written that passes without looking at anything, which is the whole point of this file.
_WITNESSLESS_CEILING = 154


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
        "non-empty -- or say here why this one cannot have it. New offenders: %r"
        % (len(witnessless), _WITNESSLESS_CEILING, witnessless[-6:]))


def test_the_lint_flags_a_planted_witnessless_body(tmp_path):
    """RED CASE for the ratchet itself."""
    p = tmp_path / "test_planted.py"
    p.write_text("def test_x():\n    bad = []\n    for i in []:\n        bad.append(i)\n"
                 "    assert not bad\n", encoding="utf-8")
    total, witnessless = _scan([str(p)])
    assert total == 1 and len(witnessless) == 1, (total, witnessless)


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
