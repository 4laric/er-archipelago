"""The suite is sharded across CI jobs (#865) -- these are the red cases that split can produce.

MOTIVATING CASE (CONTRIBUTING rule 11). Sharding the `tests` job is a four-line workflow change and
a one-line partition. What makes it dangerous is that this suite carries two gates whose subject is
a RUN, and a shard is not a run:

  * the skip census demands an exact per-family count, which no single shard can satisfy;
  * the vacuous-quantifier spy's STALE half fails in the direction of a FALSE RED -- a waived site
    that is genuinely empty in shard 3 is merely non-empty in shard 1, so shard 1 reports the
    waiver as protecting nothing and goes red for a reason that is an artifact of the split.

The second one is the reason this file exists. A false red trains people to weaken the gate, and
the weakening that makes CI green is "stop passing --quantifier-spy to the shards" -- after which
the spy is still in the tree, still looks armed, and examines nothing. That is the exact disease
this suite already named twice (a lint rule whose options vanished; a waiver that matches nothing).
"""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


def _conftest():
    spec = importlib.util.spec_from_file_location("gf_conftest_shard_under_test",
                                                  os.path.join(HERE, "conftest.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FILES = ["test_a.py", "test_b.py", "test_c.py", "test_d.py", "test_e.py", "test_f.py", "test_g.py"]


def test_every_file_lands_in_exactly_one_shard():
    """The partition is TOTAL and DISJOINT -- the property that makes 'did every test run?'
    answerable by arithmetic instead of by trust."""
    m = _conftest()
    for total in (1, 2, 3, 4, 5, 8, 13):
        owner = m.gf_shard_owner(FILES, total)
        assert sorted(owner) == sorted(FILES), "a file was dropped or invented at total=%d" % total
        assert all(1 <= v <= total for v in owner.values()), "shard index out of range"


def test_no_shard_is_empty_while_files_remain():
    """An empty shard is a job that spends a minute of setup to run nothing, and -- worse -- it is
    indistinguishable from a shard whose tests vanished."""
    m = _conftest()
    for total in (2, 3, 4):
        used = set(m.gf_shard_owner(FILES, total).values())
        assert used == set(range(1, total + 1)), "shard(s) %s got no files at total=%d" % (
            sorted(set(range(1, total + 1)) - used), total)


def test_alphabetical_neighbours_are_split_apart():
    """Round-robin, not contiguous blocks. Cost here is concentrated in a few generation-heavy
    modules, and alphabetically adjacent files are the ones most likely to be siblings of one
    expensive feature -- contiguous blocks pile those into a single shard, and the slowest shard IS
    the wall time."""
    m = _conftest()
    owner = m.gf_shard_owner(FILES, 4)
    ordered = sorted(FILES)
    for a, b in zip(ordered, ordered[1:]):
        assert owner[a] != owner[b], "%s and %s share a shard" % (a, b)


@pytest.mark.parametrize("spec", ["0/4", "5/4", "4", "a/b", "", "-1/4", "1/0"])
def test_a_malformed_shard_spec_is_refused_not_guessed(spec):
    """A shard spec that is quietly coerced runs the wrong slice and reports success. '0/4' is the
    one that matters: off-by-one is the likeliest hand-typed mistake, and under a silent coercion
    it would run shard 4's files while every artifact claimed it was shard 0."""
    m = _conftest()
    with pytest.raises(ValueError):
        m._gf_parse_shard(spec)


def test_a_correct_waiver_is_called_stale_by_one_shard_but_not_by_the_union():
    """🛑 THE RED CASE THE WHOLE DEFERRAL EXISTS FOR.

    One waived site. In shard 1 it ran and was never empty; in shard 2 it ran and WAS empty, which
    is why the waiver is correct. Judge shard 1 alone and the waiver reads as protecting nothing.
    Judge the union and it reads as exactly what it is.
    """
    m = _conftest()
    site = "test_x.py::f all()"
    waived = {site: "empty under dlc_only, which only shard 2 exercises"}

    shard1_unwaived, shard1_stale = m._qspy_verdict(empty=set(), seen={site}, waived=waived)
    assert shard1_stale == [site], (
        "the premise of this test has changed: shard 1 alone no longer reports the waiver as "
        "stale, so the deferral in conftest/gf_shard_verdict may now be guarding nothing")
    assert shard1_unwaived == []

    union_unwaived, union_stale = m._qspy_verdict(empty={site}, seen={site}, waived=waived)
    assert union_stale == [], "the union must not call a correct waiver stale"
    assert union_unwaived == [], "a waived empty site must not be reported as unwaived"


def test_deferral_leaves_a_real_hit_for_the_aggregator_rather_than_swallowing_it():
    """Deferring must not be a quiet amnesty. An UNWAIVED empty site found in any one shard has to
    survive into the union, or sharding would turn a red gate green."""
    m = _conftest()
    site = "test_y.py::g any()"
    union_unwaived, _ = m._qspy_verdict(empty={site}, seen={site}, waived={})
    assert union_unwaived == [site]
