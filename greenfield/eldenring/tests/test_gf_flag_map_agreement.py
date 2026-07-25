"""FLAG vs MAP: the check's own flag encodes its map, so region_map.csv can be checked against it.

An item-lot event flag encodes the map it belongs to: `MMSS7NNN` -> `mMM_SS` (40017000 -> m40_01).
That is the GAME's datum, and it needs no artifacts, no MSBs and no play_region table -- which makes
it a free, independent screen on `region_map.csv`'s `map` column, whose values come from an EMEVD
attribution that assigns by the script the award appears IN rather than by the flag.

The attribution leaks. Found 2026-07-25 chasing Alaric's report that Cave of Knowledge shows as
Stormveil: flags 18007000 / 18007020 encode m18_00 (Cave of Knowledge) and region_map.csv had them
as m10_01_00_00 / "Stormveil Castle". Their six siblings on the same grace had no attribution at all
and fell through to a default that happened to say Limgrave -- so the CONFIDENT rows were the wrong
ones and the "don't know" rows were right, which is this repo's disease in miniature.

Those two are FIXED (m18_00_00_00, matching their siblings; `dungeon_regions.tsv` independently
resolves m18_00 -> Limgrave through the grace join). The rest are pinned below.

The remaining 10 are NOT fixed here on purpose. Nine of them are catacomb/cave/tunnel/gaol flags
(m40/m41/m42/m43) that region_map.csv attributes to m18_00 -- the tutorial cave swallowing checks
from unrelated dungeons. Re-homing them means trusting `dungeon_regions.tsv` for m40_00 -> Gravesite
and m40_01 -> Rauh Base, i.e. DLC regions for what read as base-game dungeon maps. That may well be
right, but it is a claim about map numbering nobody has verified, and moving 9 checks between
regions on an unverified premise is how a confident wrong answer ships. So: pin, name, and leave the
work visible.

DO NOT raise the pin. Lower it by fixing rows.
"""
import csv
import os

import pytest

pytest.importorskip("worlds.eldenring")

# Measured on main 2026-07-25 after the Cave of Knowledge fix. A RATCHET: it may only go DOWN.
MAX_FLAG_MAP_DISAGREEMENTS = 10


def _region_map_rows():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "region_map.csv")
    if not os.path.isfile(path):
        pytest.skip("region_map.csv not installed beside the package -- oracle would run BLIND")
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "region_map.csv parsed to ZERO rows -- an empty oracle is a failure, not a pass"
    return rows


def _map_from_flag(flag):
    """`MMSS7NNN` -> `mMM_SS_00_00`, else None. The 7 in position 4 is the item-lot marker."""
    s = str(flag)
    if len(s) == 8 and s[4] == "7":
        return "m%s_%s_00_00" % (s[0:2], s[2:4])
    return None


def _disagreements():
    out = []
    checked = 0
    for r in _region_map_rows():
        want = _map_from_flag(r.get("flag"))
        got = (r.get("map") or "").strip()
        if want is None or not got or got == "PENDING":
            continue
        checked += 1
        if got != want:
            out.append((r["flag"], want, got, r.get("region"), r.get("item_name")))
    # A filter with no tally is a lie (CONTRIBUTING rule 4): if the join ever stops matching, say so
    # rather than reporting a clean run.
    assert checked > 1000, (
        f"only {checked} rows had both a flag-encoded map and a concrete map column -- the join has "
        "drifted, and 0 disagreements out of nothing is not a pass")
    return out


def test_flag_map_disagreements_do_not_grow():
    d = _disagreements()
    assert len(d) <= MAX_FLAG_MAP_DISAGREEMENTS, (
        f"{len(d)} region_map.csv rows have a `map` that contradicts the map their own flag encodes "
        f"(pin {MAX_FLAG_MAP_DISAGREEMENTS}). The flag is the game's datum; the map column is an "
        "EMEVD attribution. Fix the row, do NOT raise the pin:\n  "
        + "\n  ".join("flag=%s flag_says=%s csv_says=%s region=%s %s" % x for x in d[:12]))


def test_the_cave_of_knowledge_rows_stay_fixed():
    """Alaric, 2026-07-25: Cave of Knowledge is Limgrave, all of it. Named so a regen that
    reintroduces the EMEVD attribution cannot quietly undo it."""
    rows = {r["flag"]: r for r in _region_map_rows()}
    for flag in ("18007000", "18007020"):
        assert flag in rows, f"{flag} vanished from region_map.csv"
        assert rows[flag]["map"] == "m18_00_00_00", (
            f"{flag} is back on {rows[flag]['map']} -- its flag encodes m18_00 (Cave of Knowledge). "
            "The EMEVD attribution put it in m10_01 and that read out as Stormveil.")


def test_every_cave_of_knowledge_check_agrees_with_its_siblings():
    """The actual player-visible property: one physical place, one region."""
    rows = [r for r in _region_map_rows() if str(r.get("flag", "")).startswith("18007")]
    assert len(rows) >= 8, f"expected the Cave of Knowledge check block, found {len(rows)}"
    concrete = {r["region"] for r in rows if (r.get("map") or "").strip() not in ("", "PENDING")}
    assert len(concrete) == 1, (
        f"Cave of Knowledge checks claim {sorted(concrete)} -- one cave cannot be in two regions")
