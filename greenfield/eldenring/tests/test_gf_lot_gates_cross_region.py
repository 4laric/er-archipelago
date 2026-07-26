"""No check is gated on a flag that belongs to ANOTHER region.

THE BUG THIS SCREENS FOR. A check regioned CORRECTLY that still cannot EXIST yet: the generator
asserts a reachability it does not have, and fill may place progression there in a seed where the real
prerequisite is locked. Not a misregion -- a missing ACCESS RULE, invisible to every region oracle we
have, precisely because the region is right.

⚠️ THE EXEMPLAR IN THIS DOCSTRING WAS WRONG UNTIL 2026-07-25, and it sent two sessions to the wrong
place. It read: "`f67050` -- the cookbook Roderika leaves at Stormhill Shack -- ... the pickup does not
EXIST until you rest at a grace in Liurnia." **f67050 is ungated**: its MSB Treasure has
`StartDisabled=0`, its asset is `NeverDisable` with no condition, the flag and its lot appear NOWHERE
in all 589 decompiled EMEVD, and Fextralife/Game8 both place it on a dead man at the collapsed bridge
to Stormveil with no Roderika involvement at all.

The REAL exemplar is the GOLDEN SEED, **`f400191`** (`Golden Seed - around Stormhill Shack`, lot
101910) -- "in Stormhill Shack where Roderika was sitting, if the player rests at any site of grace in
Liurnia of the Lakes, or by giving her Chrysalids' Memento". The behaviour reported was real; it was
attached to the wrong flag. Its gate is now in lot_gates.tsv three times over (flags 3708 / 3709 /
1041389414 -- the three ways to trigger it), found only once the scan learned to resolve
common-event ARGUMENTS.

`tools/datamine_lot_gates.py` finds candidates by scanning decompiled EMEVD for "check flag X
co-occurs with a test of flag Y". This test takes its output and asks the only question that matters:
does Y belong to a DIFFERENT region than X? If so, X claims an early reachability it cannot support.

RESULT, 2026-07-25: **0 cross-region, out of the 17 pairs where BOTH sides resolve to a region.**

Read that number carefully, because it is the honest one and it is much smaller than "0 of 104". Only
17 of the 104 gate flags decode to a region at all -- the decode rule covers interior `MMSS7NNN` and
tile-encoded overworld flags, and most gates are neither (13 sit in the 1k-10k common/progress band,
whose flags name no map). So the claim this test pins is: *among the gates we can place, none is
foreign to its check*. It is silent on the other 87.

⚠️ SCOPE, because a green test here is easy to over-read:
  * The scan covers 19 literal `AwardItemLot` sites, 1 common event, and 21 of 38 resolvable
    `EnableAssetTreasure` sites. Scripted awards are RARE in ER.
  * 148 `ForceCharacterTreasure` sites (corpse-carried pickups) are NOT covered -- they need a
    character-entity join that does not exist yet.
  * f67050 itself is NOT in the population: its treasure asset has EntityID 0, so the EMEVD cannot
    name it by asset at all, and whatever gates it works some other way.
  So this passing does NOT mean the class is absent from the game. It means it is absent from the
  slice we can currently see, which is a much smaller claim and the honest one.

Both sides are resolved regions -- the check's from the GENERATED data, the gate's by decoding the
flag's own map (the `MMSS7NNN` rule, same as test_gf_flag_map_agreement). An earlier pass compared a
raw region_map LABEL against a resolved region and produced 19 "cross-region" hits, every one a
label-granularity artifact ('Overworld m60_48_57_00' vs 'Mountaintops of the Giants' is the same
place). Comparing a coarse label to a resolved name manufactures findings.
"""
import collections
import csv
import os
import re

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS  # noqa: E402

MAX_CROSS_REGION_GATES = 0

_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rows(name):
    path = os.path.join(_PKG, name)
    if not os.path.isfile(path):
        pytest.skip("%s not installed beside the package -- oracle would run BLIND" % name)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(
            (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t")


def _gate_region_resolver():
    """flag -> region, by decoding the flag's OWN map. Interior `MMSS7NNN` -> mMM_SS via
    dungeon_regions; overworld `1XXYY....`/`2XXYY....` -> tile via the grace anchors."""
    import importlib
    play2ap = importlib.import_module("worlds.eldenring.region_groups").PLAY2AP
    dungeon = {(r.get("map_id") or "").strip(): (r.get("region") or "").strip()
               for r in _rows("dungeon_regions.tsv")}
    tiles = {(r.get("warpUnlockFlag") or "").strip(): (r.get("mapTile") or "").strip()
             for r in _rows("grace_flags.tsv")}
    play = {(r.get("grace_flag") or "").strip(): (r.get("play_region_id") or "").strip()
            for r in _rows("grace_region_map.tsv")}
    votes = collections.defaultdict(collections.Counter)
    for warp, tile in tiles.items():
        region = play2ap.get(play.get(warp, ""))
        m = re.match(r"(m6[01])_(\d\d)_(\d\d)", tile or "")
        if region and m:
            votes[(m.group(1), int(m.group(2)), int(m.group(3)))][region] += 1
    tile_region = {k: c.most_common(1)[0][0] for k, c in votes.items()}
    assert len(tile_region) > 100, "the grace->tile->region join has drifted; refusing to screen blind"

    def resolve(flag):
        s = str(flag)
        if len(s) == 8 and s[4] == "7":
            return dungeon.get("m%s_%s" % (s[0:2], s[2:4]))
        if len(s) == 10 and s[0] == "1":
            return tile_region.get(("m60", int(s[2:4]), int(s[4:6])))
        if len(s) == 10 and s[0] == "2":
            return tile_region.get(("m61", int(s[2:4]), int(s[4:6])))
        return None

    return resolve


def test_no_check_is_gated_on_another_regions_flag():
    check_region = {str(f): r for r, locs in LOCATIONS.items() for (_n, _a, f) in locs}
    check_name = {str(f): n for _r, locs in LOCATIONS.items() for (n, _a, f) in locs}
    resolve = _gate_region_resolver()

    pairs = list(_rows("lot_gates.tsv"))
    assert pairs, "lot_gates.tsv parsed to ZERO pairs -- an empty screen is a failure, not a pass"

    cross, decodable = [], 0
    for row in pairs:
        cf, gf = row.get("check_flag"), row.get("gate_flag")
        creg, greg = check_region.get(cf), resolve(gf)
        if not creg or not greg:
            continue
        decodable += 1
        if creg != greg:
            cross.append("check %s [%s] %s <- gate %s [%s] ctx=%s"
                         % (cf, creg, check_name.get(cf, "")[:40], gf, greg, row.get("context")))
    # A screen that decodes nothing would pass silently. Say what it actually examined.
    # Floor MEASURED, not guessed: 17 of 104 decode today. Set just below so a real collapse in the
    # decode rule fails loudly, without pretending the coverage is better than it is.
    assert decodable >= 15, (
        "only %d of %d pairs had both sides resolvable (17 did on 2026-07-25) -- the flag-decode rule "
        "has stopped matching lot_gates.tsv's gate_flag column, and this screen is now looking at too "
        "little to mean anything." % (decodable, len(pairs)))
    assert len(cross) <= MAX_CROSS_REGION_GATES, (
        "%d check(s) are gated on a flag from ANOTHER region -- each is a check claiming an early "
        "reachability it does not have, which is how fill puts progression behind a lock the player "
        "cannot open. These need an access rule in core.py, NOT a region change (the region is "
        "right; the reachability claim is not):\n  %s" % (len(cross), "\n  ".join(cross)))
