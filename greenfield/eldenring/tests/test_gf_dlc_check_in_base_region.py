"""No base-game region may hold a check whose pickup is inside a DLC map.

THE MOTIVATING CASE (rule 11). Alaric, 2026-08-14, reading his own tracker on an `enable_dlc: false`
seed: `* Limgrave :: Hefty Cracked Pot - near Bonny Gaol [f66930]`. Bonny Gaol is Shadow of the
Erdtree. The check was live, in logic, and on the progression surface, so the fill could have put a
Region Lock on a pickup that seed can never reach -- an unwinnable seed with no warning.

Flag 66930's only lot is 41010000 (m41_01 Bonny Gaol) and its nearest grace is Bonny Gaol itself,
but the EMEVD provenance chain gave it an m18 fallback -> "Stormveil (assoc.)" and from there a
Limgrave home. `gen_data._REGION_CONFIRMED_FLAGS` already carried that fix for m41_00 and m41_02;
m41_01 was missed because 66930 does not share their `X0SS7000` flag shape.

🛑 THE PREDICATE IS A GRACE JOIN, NOT ARITHMETIC ON THE LOT ID. Deriving a map by slicing digits off
a lot (`m{lot[:2]}_{lot[2:4]}`) is wrong the moment a lot is not 8 digits -- it invented a nonexistent
"m21_40" for lot 214000991 and produced a second, fictional offender while this was being measured.
`nearest_grace` -> `grace_flags` is two committed derived tables and is the same join
`_REGION_CONFIRMED_FLAGS`'s own comment calls authoritative.
"""
import os
import re

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS, REGIONS  # noqa: E402
from worlds.eldenring.region_spine import DLC_REGIONS  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))

#: Map-id prefixes that only exist in Shadow of the Erdtree.
DLC_MAP_PREFIXES = ("m20_", "m21_", "m22_", "m41_", "m50_", "m51_")


def _tsv(name):
    """A committed derived table, from beside the installed package or the repo."""
    for cand in (os.path.join(_HERE, "..", name), os.path.join(_HERE, "..", "..", "..", name)):
        if os.path.isfile(cand):
            with open(cand, encoding="utf-8") as f:
                return [l.rstrip("\n").split("\t") for l in f if l.strip() and not l.startswith("#")]
    return []


def _grace_map_of_flag():
    """flag -> the MAP its nearest grace lives in. Both hops are committed derived tables."""
    grace_of = {r[0]: r[2] for r in _tsv("nearest_grace.tsv") if len(r) >= 3 and r[2].isdigit()}
    map_of = {r[0]: r[1] for r in _tsv("grace_flags.tsv") if len(r) >= 2}
    return {flag: map_of.get(g, "") for flag, g in grace_of.items()}


def test_the_join_actually_resolves():
    """WITNESS. Both tables ship beside the package; if either goes missing the gate below reports
    zero offenders, which is indistinguishable from clean."""
    gm = _grace_map_of_flag()
    assert len(gm) > 500, (
        f"the nearest_grace -> grace_flags join resolved only {len(gm)} flag(s) -- one of the two "
        f"tables is missing or reshaped, and the gate below would pass vacuously.")
    assert any(m.startswith(DLC_MAP_PREFIXES) for m in gm.values()), (
        "no flag resolves to a DLC map at all, so the gate cannot fire even in principle.")


def test_no_base_game_region_holds_a_check_whose_pickup_is_in_the_DLC():
    """THE GATE. A base-game region's check must not sit physically inside a DLC map.

    Such a check survives the `enable_dlc: false` filter -- the filter drops DLC REGIONS, and this
    check is not in one -- so it ships in a base-game seed pointing at ground the player cannot
    reach. On the progression surface that is a placement the fill is allowed to make.
    """
    base_regions = [r for r in REGIONS if r not in DLC_REGIONS]
    assert base_regions, "no base-game regions found -- the loop below would not run"

    grace_map = _grace_map_of_flag()
    checked = 0
    offenders = []
    for region in base_regions:
        for entry in LOCATIONS.get(region, ()):
            # (name, ap_id, flag) with flag last; tolerate longer shapes.
            flag = str(entry[2]) if len(entry) > 2 else None
            if flag is None:
                continue
            gm = grace_map.get(flag, "")
            if not gm:
                continue
            checked += 1
            if gm.startswith(DLC_MAP_PREFIXES):
                offenders.append((region, flag, gm, str(entry[0])[:70]))

    assert checked > 200, (
        f"only {checked} base-region check(s) resolved a grace map -- the scan is blind, and an "
        f"empty offender list below would mean nothing.")

    assert offenders == [], (
        f"{len(offenders)} check(s) sit in a base-game region but pick up inside a DLC map:\n  "
        + "\n  ".join(f"{r}: flag {f} -> {m} -- {n}" for r, f, m, n in offenders)
        + "\n\nA seed with enable_dlc: false ships these and cannot reach them; progression placed "
          "on one makes the seed unwinnable. Fix by adding the flag to "
          "gen_data._REGION_CONFIRMED_FLAGS with its real region (the m41_00 / m41_02 entries "
          "there are the precedent) and regenerating, NOT by widening this gate.")
