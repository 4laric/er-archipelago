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
resolves m18_00 -> Limgrave through the grace join).

NINE MORE FIXED 2026-07-25, and the way the premise got checked is the point. Eight were
m40/m41/m42/m43 flags that region_map.csv filed under m18_00 -- the tutorial cave swallowing checks
from unrelated dungeons -- and one was an m21_01 flag filed under m20_00. Re-homing them meant
trusting `dungeon_regions.tsv` when it said m40_00 -> Gravesite, i.e. a DLC region for what LOOKS
like a base-game catacomb number, and that was held back a commit because nobody had verified it.

Alaric: "should be grace checkable". It is. Every one of those maps contains exactly one grace, and
the grace NAME is the game telling you where you are:

    m40_00 Fog Rift Catacombs        m41_00 Belurat Gaol            m42_00 Ruined Forge Lava Intake
    m40_01 Scorpion River Catacombs  m41_02 Lamenter's Gaol         m42_03 Taylew's Ruined Forge
    m40_02 Darklight Catacombs       m21_01 Messmer's Dark Chamber  m43_00 Rivermouth Cave

All nine are Shadow of the Erdtree locations. m40-m43 are the DLC's small-dungeon ranges; the
base-game catacombs/caves/tunnels are m30/m31/m32. The "base-game dungeon number" reading was mine
and it was wrong, and one grace-name lookup settled it. 9/9 corroborate dungeon_regions.tsv.

Only the `map` column is corrected. The coarse `region` label is set to the one that map's sibling
rows already use.

## CORRECTION, measured after the regen -- what that fix did NOT do

The commit that made it claimed it "moves nine checks by fixing ONE wrong field", and predicted the
straddle pins would fall again. **Both were wrong, and neither had been measured.** After the regen:
all nine checks have the SAME region they had before (Gravesite, Rauh Base, Scadu Altus, Shadow Keep),
and the straddle pins did not move (39 / 98 either way).

The reason is in gen_data itself. For interior flag prefixes -- including 40/41/42/43 and 21 -- it
ALREADY decodes the map from the flag and overwrites the row's `map` (`_rec = f"m{_fs[:2]}_{_fs[2:4]}
_00_00"`, guarded on DUNGEON_REGION_OVERRIDE). So the wrong column never reached region resolution:
region_map.csv said m18_00, gen_data quietly corrected it to m40_00, and the region was right the
whole time.

What the wrong column DID reach is the layer-4 DESCRIPTION, which reads the raw value. That is the
real, verified effect: nine checks stopped being described by the tutorial cave. "Gravesite :: Anvil
Hammer - around Cave of Knowledge" is now "around Ruined Forge Lava Intake".

Which means this screen is NOT a region bug-finder. It is a consistency check between the committed
input and the correction gen_data already applies in memory, and it protects the description layer,
which has no such correction. Worth keeping and worth stating accurately -- a fix whose claimed
mechanism is wrong is a comment that will mislead the next reader even though the diff was fine.
That is the same "confident wrong answer" this file exists to catch, produced by the person writing
the catcher.

ONE disagreement remains, pinned: flag 10007452 encodes m10_00 (Stormveil) and region_map.csv files
it under m11_10 (Roundtable Hold). m10_00 has no dungeon_regions entry, so the grace check that
settled the other nine cannot settle this one -- and a flag allocated in one map's band CAN be
awarded by a common event somewhere else, which is exactly the case this pin exists to keep visible.

DO NOT raise the pin. Lower it by fixing rows.
"""
import csv
import os

import pytest

pytest.importorskip("worlds.eldenring")

# Measured on main 2026-07-25 after the Cave of Knowledge fix and the nine grace-corroborated
# re-homings. A RATCHET: it may only go DOWN.
MAX_FLAG_MAP_DISAGREEMENTS = 1


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


def test_the_regraced_dungeon_rows_stay_fixed():
    """The nine rows re-homed on grace-name corroboration. Named so a regen that reinstates the EMEVD
    attribution says WHICH claim it is contradicting."""
    rows = {r["flag"]: r for r in _region_map_rows()}
    expected = {
        "21017800": "m21_01_00_00", "40007000": "m40_00_00_00", "40017000": "m40_01_00_00",
        "40027000": "m40_02_00_00", "41007000": "m41_00_00_00", "41027000": "m41_02_00_00",
        "42007000": "m42_00_00_00", "42037000": "m42_03_00_00", "43007000": "m43_00_00_00",
    }
    for flag, want in expected.items():
        assert flag in rows, f"{flag} vanished from region_map.csv"
        assert rows[flag]["map"] == want, (
            f"{flag} is on {rows[flag]['map']}; its flag encodes {want}, and that map's own grace "
            "(see the module docstring) confirms the DLC location.")


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
