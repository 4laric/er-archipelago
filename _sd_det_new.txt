"""CI guard: slot_data must be emitted DETERMINISTICALLY across runs.

Several slot_data list values (areaLockFlags, regionSphereTargetRanges, ...) are
assembled by iterating string-keyed sets/dicts across multiple passes. Python
randomizes str/bytes hashing per process (PYTHONHASHSEED), so an UNSORTED such
list comes out in a different ORDER run-to-run -- which churns the shipped
slot_data_fixture.json and risks order-sensitive client behavior. The fix is to
sort each such list at its slot_data.py emit choke point; these tests lock it in.

WHY A SUBPROCESS: hash randomization is fixed once, at interpreter startup. So
calling fill_slot_data() twice inside ONE process uses the SAME hash seed and
cannot reveal the bug (false pass). We emit the table in two CHILD processes under
different PYTHONHASHSEED and assert the JSON is byte-identical.

Fixed seed 1706 + the flagship-ish options keep the payload stable, so any diff is
pure ordering nondeterminism, not seed variation.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from test.bases import WorldTestBase

_SEED = 1706
# Matches test_slot_data_fixture.py: region_lock + DLC arms the region-spine /
# sphere-scaling paths, so areaLockFlags AND regionSphereTargetRanges are populated.
_OPTIONS = {"enable_dlc": True, "world_logic": "region_lock"}
_EMIT_ENV = "ER_EMIT_SLOT_DATA"
# List values known to be assembled from unordered sources; must ship sorted.
_RANGE_LIST_KEYS = ("areaLockFlags", "regionSphereTargetRanges")


def _wire(o):
    # AP serializes Python sets as arrays; sort for byte-stable output.
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=str)
    raise TypeError("not JSON serializable: %s" % type(o).__name__)


class _EmitWorld(WorldTestBase):
    """Headless world builder. NOT a pytest test class (``__test__ = False``), so its
    inherited WorldTestBase generic tests never run in a normal collection."""
    __test__ = False
    game = "EldenRing"
    options = _OPTIONS

    def world_setup(self, *args, **kwargs):
        super().world_setup(seed=_SEED)

    def runTest(self):  # allows _EmitWorld("runTest") instantiation
        pass


def _build_slot_data():
    case = _EmitWorld("runTest")
    case.setUp()
    return case.world.fill_slot_data()


def _emit_json():
    return json.dumps(_build_slot_data(), sort_keys=True, indent=1, default=_wire)


def _diff_keys(text_a, text_b):
    """Return a list of 'key (kind)' strings for every top-level key whose value differs
    between the two JSON payloads. kind = 'reorder-only' (same multiset, just ordered
    differently -> fixable with sorted()) or 'content' (genuinely different data)."""
    ja, jb = json.loads(text_a), json.loads(text_b)
    out = []
    for k in sorted(set(ja) | set(jb)):
        va, vb = ja.get(k), jb.get(k)
        if va == vb:
            continue
        kind = "content"
        if isinstance(va, list) and isinstance(vb, list) \
                and sorted(map(repr, va)) == sorted(map(repr, vb)):
            kind = "reorder-only"
        out.append("%s (%s)" % (k, kind))
    return out


class TestSlotDataDeterminism(unittest.TestCase):
    """Emit the table in two child processes under different PYTHONHASHSEED and assert
    the JSON is byte-identical (order-stable)."""

    def test_slot_data_stable_across_hash_seeds(self):
        emit_target = os.environ.get(_EMIT_ENV)
        if emit_target:
            # CHILD MODE: this process was spawned to emit under a fixed PYTHONHASHSEED.
            with open(emit_target, "w", encoding="utf-8", newline="\n") as f:
                f.write(_emit_json())
            return

        # PARENT MODE: drive two emits under different hash seeds and diff them.
        ap_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        node = os.path.relpath(os.path.abspath(__file__), ap_root).replace(os.sep, "/") \
            + "::TestSlotDataDeterminism::test_slot_data_stable_across_hash_seeds"

        outputs = []
        tmp_paths = []
        try:
            for hash_seed in ("0", "1"):
                fd, path = tempfile.mkstemp(prefix="er_sd_%s_" % hash_seed, suffix=".json")
                os.close(fd)
                tmp_paths.append(path)
                env = dict(os.environ)
                env["PYTHONHASHSEED"] = hash_seed
                env[_EMIT_ENV] = path
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node],
                    cwd=ap_root, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                )
                self.assertEqual(
                    proc.returncode, 0,
                    "emit child (PYTHONHASHSEED=%s) failed:\n%s" % (hash_seed, proc.stdout[-3000:]),
                )
                with open(path, "r", encoding="utf-8") as f:
                    outputs.append(f.read())

            self.assertTrue(outputs[0], "emit produced empty output (child did not write the table)")
            if outputs[0] != outputs[1]:
                try:
                    offenders = _diff_keys(outputs[0], outputs[1])
                    detail = ", ".join(offenders) if offenders else "(whitespace/structure only)"
                except ValueError:
                    detail = "(could not parse payloads as JSON)"
                self.fail(
                    "slot_data differs across PYTHONHASHSEED -> NONDETERMINISTIC emission.\n"
                    "Offending key(s): %s\n"
                    "'reorder-only' keys are fixed by wrapping that value in sorted() at its "
                    "slot_data.py emit choke point (see patch_sort_*.py). 'content' keys mean the "
                    "nondeterminism changes DATA, not just order -- pin the source, not the emit."
                    % detail)
        finally:
            for path in tmp_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass


class TestSlotDataRangeListInvariant(unittest.TestCase):
    """Fast in-process guard: the known multi-source range lists must already be sorted
    on emit. Clearer/quicker failure for the lists we've fixed; the hash-seed test above
    catches any *new* nondeterministic list generally."""

    def test_known_range_lists_emitted_sorted(self):
        slot_data = _build_slot_data()
        unsorted = [k for k in _RANGE_LIST_KEYS if (slot_data.get(k) or []) != sorted(slot_data.get(k) or [])]
        self.assertEqual(
            unsorted, [],
            "these range lists are not emitted sorted -> nondeterminism risk; wrap each in "
            "sorted() at its slot_data.py emit choke point: %s" % ", ".join(unsorted))


if __name__ == "__main__":
    unittest.main()
