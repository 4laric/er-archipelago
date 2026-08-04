"""The Liurnia Isolated Merchant's stock is barred from hosting progression -- #252.

A player hit `Liurnia :: Fevor's Cookbook [2] - from Isolated Merchant [f68220]` holding a Stormveil
Lock, on a seed whose spoiler listed it in sphere 1. The merchant sits behind the Academy Glintstone
Key (reporter, and Alaric in game 2026-08-01), so a Lock placed on his stock strands the run.

WHY THIS FILE, RATHER THAN TRUSTING THE LIST IN gen_data. The gate is on the MERCHANT: 16 checks sit
behind that one door, and the report named one of them. A list that drifts from the merchant's actual
stock would re-open the hole silently -- so this re-derives the population from the committed tables
every run and fails if the two disagree in either direction.

🛑 AND THE TRAP THAT MAKES THE DERIVATION LOOK WRONG. All 16 rows list TWO sellers -- the Isolated
Merchant AND the Twin Maiden Husks at the HUB -- which reads as "always reachable, nothing to fix".
It is not: the Twin Maidens only stock a merchant's inventory once you hand them that merchant's BELL
BEARING, which drops from the merchant, behind the same door. `merchant_shops.tsv` attributes at
BLOCK level (#220): it records who CAN open a row, never whether their stock is unlocked.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
pytestmark = pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)

# The merchant instance, by the only key that identifies him uniquely: name + the map tile he
# stands on. "Isolated Merchant" alone is ambiguous -- the game reuses it on three tiles
# (m60_35_45, m60_48_41, m60_41_32) and only this one is Academy-gated.
MERCHANT = "Isolated Merchant"
TILE = "m60_35_45"


def _tsv(path):
    hdr = None
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if hdr is None:
                hdr = parts
                continue
            yield dict(zip(hdr, parts))


def _derived_flags():
    gf = os.path.join(_ROOT, "greenfield")
    rows = {r["row_id"] for r in _tsv(os.path.join(gf, "merchant_shops.tsv"))
            if r.get("merchant_name") == MERCHANT and r.get("map_id") == TILE}
    assert rows, (
        f"no ShopLineupParam rows attributed to {MERCHANT} on {TILE}. Either merchant_shops.tsv "
        "was re-emitted with different columns, or the merchant moved -- do not 'fix' this by "
        "deleting the assertion (an empty derivation is a FAILURE, not a clean run).")
    flags = set()
    for r in _tsv(os.path.join(gf, "shop_rows.tsv")):
        if r["row_id"] in rows and str(r.get("stock_flag", "")).strip().isdigit():
            flags.add(int(r["stock_flag"]))
    return rows, flags


def _excluded():
    """`gen_data._SURFACE_EXCLUDE_FLAGS`, read by AST rather than by import.

    🛑 `import gen_data` DIES in any environment without the Windows artifacts -- it SystemExits on
    "finale derivation needs event/common.emevd.dcx.js", by design (an empty finale would silently
    drop 10 checks). Importing it here would make this gate pass only on Alaric's box and fail in
    CI, which is the dormant-gate shape this repo keeps paying for. The declared set is source, so
    read the source."""
    import ast
    src = os.path.join(_ROOT, "greenfield", "gen_data.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_SURFACE_EXCLUDE_FLAGS" for t in node.targets):
            # frozenset({...}) -- take the literal set inside the call.
            call = node.value
            assert isinstance(call, ast.Call), "_SURFACE_EXCLUDE_FLAGS is no longer frozenset({...})"
            out = {int(e.value) for e in call.args[0].elts if isinstance(e, ast.Constant)}
            assert out, "parsed an EMPTY exclusion set -- the literal moved, this is not a pass"
            return out
    raise AssertionError("_SURFACE_EXCLUDE_FLAGS not found in gen_data.py")


def test_the_derivation_sees_the_merchant():
    """Rule 2: an empty result is a failure. If this shrinks, the join broke, not the game."""
    rows, flags = _derived_flags()
    assert len(rows) >= 15, f"only {len(rows)} shop rows for {MERCHANT}@{TILE}"
    assert len(flags) >= 15, f"only {len(flags)} check flags derived; expected the full stock"


def test_every_flag_this_merchant_sells_is_barred_from_progression():
    _, flags = _derived_flags()
    missing = sorted(flags - _excluded())
    assert not missing, (
        f"{len(missing)} check(s) sold by {MERCHANT}@{TILE} can still host progression: {missing}. "
        "The gate is the merchant, not the item -- add them to gen_data._SURFACE_EXCLUDE_FLAGS.")


def test_the_reported_check_is_covered_end_to_end():
    """Rule 11: the case that motivated the gate is the acceptance test, by name and number."""
    _, flags = _derived_flags()
    assert 68220 in flags, "the derivation no longer sees f68220, the flag #252 was filed about"
    assert 68220 in _excluded(), "f68220 -- the reported check -- is not barred"


def test_the_academy_seed_is_regioned_not_barred():
    """1035467100 was excluded HERE 2026-07-31 on suspicion of the same Academy gate, released
    2026-08-01 on a "WALKED AND CLEARED" that was a MISATTRIBUTION (that day its descriptor read
    "near Academy Gate Town", 872 m off; the seed actually collected was 1036447300 -- see the note
    at gen_data._SURFACE_EXCLUDE_FLAGS), then ruled key-gated by Alaric in game 2026-08-04. The
    suspicion was RIGHT and this bar is still the WRONG TOOL for it: SURFACE_EXCLUDE trims the
    advertised surface but is absent from core._NO_PROGRESSION_APS, so it never stopped fill
    (#350). The binding fix is the REGION -- FLAG_REGION_OVERRIDE -> Raya Lucaria Academy, gated by
    test_gf_academy_key_pocket.py. Keeping the flag OUT of this set is load-bearing: present here
    it would read as "handled" while binding nothing."""
    assert 1035467100 not in _excluded(), (
        "f1035467100 is region-gated (Raya Lucaria Academy, test_gf_academy_key_pocket); a surface "
        "bar on top would double-book the check and bind nothing fill obeys")
