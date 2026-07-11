"""Gen-input STAMP gate (tier A) -- SPEC-gen-input-hash-gate-20260710.md.

The two-machine split (Linux sandbox derives + tests; Windows packages the resident bytes) admits a
bug class no ordinary test can see: green CI and a stale/truncated/empty PACKAGE simultaneously,
because tests validate freshly-derived data, never the shipped artifact. `gen_data.py` stamps every
generated module with `_GEN_STAMP` (the hash of the inputs it derived from + a body checksum) and
writes a sibling `_gen_stamp.json`. This gate asserts the invariants that make that class impossible:

  A. ALL modules + the json carry ONE identical `inputs_hash` (a partial/mixed regen -- the
     truncation / crash-mid-run signature -- diverges here).
  B. Each module's body checksum still matches (a module TRUNCATED or edited after generation fails).
  C. Semantic non-emptiness floors (an encoding fault that ships an EMPTY catalog -- the cp1252
     regression -- drops a count below its floor).
  D. FRESHNESS: the stamped `inputs_hash` equals the hash recomputed from the inputs on disk NOW
     (a commit whose generated data lags its inputs fails). Skipped only when the licensing-restricted
     artifacts aren't present (that machine can't recompute the artifact-dependent hash).

Run:  python -m pytest greenfield/eldenring/tests/test_gf_gen_stamp.py
  or: python greenfield/eldenring/tests/test_gf_gen_stamp.py
"""
import ast
import hashlib
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                      # .../greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)               # .../greenfield
REPO = os.path.dirname(GREENFIELD)                 # .../er-archipelago
STAMP_JSON = os.path.join(GF_PKG, "_gen_stamp.json")


def _find_up(rel, start):
    """Walk up from `start` to find a file/dir at relative path `rel`; None if not found."""
    d = os.path.abspath(start)
    for _ in range(8):
        cand = os.path.join(d, rel)
        if os.path.exists(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None

MODULES = ["data.py", "region_open_flags.py", "boss_data.py", "region_graces.py", "shop_data.py",
           "missable_locations.py", "item_ids.py", "item_tiers.py", "location_tags.py",
           "boss_sweeps.py"]

# Non-emptiness floors (comfortably below observed: locations~4800, item_catalog~2000, filler~226,
# regions=20, sweeps~193). A floor breach = a catalog shipped empty/partial (encoding/truncation).
COUNT_FLOORS = {"locations": 2000, "regions": 15, "item_catalog": 1000, "filler_pool": 100,
                "sweeps": 100}

_SENTINEL = "\n_GEN_STAMP = "


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _split_stamp(src):
    """Return (body_text, stamp_dict) for a generated module; stamp is the last _GEN_STAMP assign."""
    assert _SENTINEL in src, "module has no _GEN_STAMP trailer"
    body, _, tail = src.rpartition(_SENTINEL)
    stamp = ast.literal_eval(tail.strip())
    return body, stamp


def _body_sha(body_text):
    data = body_text.encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


class GenStampGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.missing = [m for m in MODULES if not os.path.isfile(os.path.join(GF_PKG, m))]
        cls.have_json = os.path.isfile(STAMP_JSON)
        cls.stamps = {}
        for m in MODULES:
            p = os.path.join(GF_PKG, m)
            if os.path.isfile(p):
                cls.stamps[m] = _split_stamp(_read(p))     # (body, stamp)

    def test_all_modules_present_and_stamped(self):
        self.assertFalse(self.missing, f"generated modules missing (regen): {self.missing}")
        self.assertTrue(self.have_json, "_gen_stamp.json missing -- regenerate")

    def test_A_single_inputs_hash(self):
        hashes = {st["inputs_hash"] for _b, st in self.stamps.values()}
        j = json.load(open(STAMP_JSON, encoding="utf-8"))
        hashes.add(j["inputs_hash"])
        self.assertEqual(len(hashes), 1,
                         f"modules disagree on inputs_hash (partial/mixed regen): {hashes}")
        self.assertNotIn("sha256:UNAVAILABLE", hashes,
                         "stamp inputs_hash=UNAVAILABLE -- tools/gen_manifest was not importable at gen time")

    def test_B_body_checksums_intact(self):
        j = json.load(open(STAMP_JSON, encoding="utf-8"))
        for m, (body, st) in self.stamps.items():
            recomputed = _body_sha(body)
            self.assertEqual(recomputed, st["body_sha256"],
                             f"{m}: body checksum mismatch -- module truncated/edited after generation")
            self.assertEqual(st["body_sha256"], j["modules"].get(m),
                             f"{m}: body sha disagrees with _gen_stamp.json")

    def test_C_counts_above_floor(self):
        j = json.load(open(STAMP_JSON, encoding="utf-8"))
        counts = j.get("counts", {})
        for k, floor in COUNT_FLOORS.items():
            self.assertGreaterEqual(counts.get(k, 0), floor,
                                    f"count '{k}'={counts.get(k)} below floor {floor} "
                                    f"-- empty/partial catalog (encoding fault?)")

    def test_D_freshness_vs_disk(self):
        """Recompute the input hash from disk; must equal the stamp. Skip if artifacts absent."""
        gm_path = _find_up(os.path.join("tools", "gen_manifest.py"), GF_PKG)
        if not gm_path:
            self.skipTest("tools/gen_manifest.py not found (installed world) -- freshness runs in source tree")
        spec = importlib.util.spec_from_file_location("_gen_manifest", gm_path)
        gm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gm)
        man = gm.compute_manifest(os.path.dirname(os.path.dirname(gm_path)))
        if man["missing"]:
            self.skipTest(f"inputs absent, cannot verify freshness: {man['missing']}")
        j = json.load(open(STAMP_JSON, encoding="utf-8"))
        self.assertEqual(j["inputs_hash"], man["inputs_hash"],
                         "STALE: generated data lags the inputs on disk -- regenerate "
                         "(python greenfield/gen_data.py). This is the check that retires "
                         "'NEEDS WINDOWS REGEN'.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
