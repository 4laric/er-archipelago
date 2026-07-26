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

RESULT, 2026-07-26: **8 cross-region gates among the pairs where BOTH sides resolve to a region, and
all 8 are missable-tagged.** The class is PRESENT in the game and this screen's job is to keep every
member neutralised, not to report zero.

Only a minority of gate flags decode to a region at all -- the decode rule covers interior `MMSS7NNN`
and tile-encoded overworld flags, and many gates are neither (a band of them sit in the 1k-10k
common/progress range, whose flags name no map). So the claim this test pins is: *among the gates we
can place, none is foreign to its check AND unprotected*. It is silent on the ones that do not decode,
and `decodable` below is asserted so that silence cannot grow unnoticed.

⚠️ SCOPE, because a green test here is easy to over-read:
  * 🛑 The old version of this paragraph read "the scan covers 19 literal `AwardItemLot` sites ...
    scripted awards are RARE in ER." **That was a fact about the SCAN, not about the game**, and it
    is the single claim that kept two sessions away from the answer. Corpus counts:
    `AwardItemsIncludingClients` 205, `AwardGesture` 29, `AwardItemLot` 26 -- the tool knew only the
    minority verb. Fixed in `49b16b3`, along with common-event ARGUMENT resolution, which took the
    table from 104 pairs / 23 checks to 617 pairs / 408 distinct checks.
  * 148 `ForceCharacterTreasure` sites (corpse-carried pickups) are NOT covered -- they need a
    character-entity join that does not exist yet.
  * A treasure asset with `EntityID 0` cannot be named by the EMEVD at all, so whatever gates it
    works some other way and is invisible here. `f67050` is one of those -- and it is also
    genuinely UNGATED, five ways (see above).
  So this passing does NOT mean every member of the class is caught. It means every member we can
  currently SEE is neutralised, which is a much smaller claim and the honest one.

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
import warnings

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS  # noqa: E402

# WHAT THIS SCREEN DEMANDS, and why it is not "zero".
# The 8 checks it first caught (2026-07-25) are all NPC-QUESTLINE drops -- item in region A,
# prerequisite in region B. `906b3e1` EXCLUDED them; Alaric reversed that on 2026-07-26 ("it's fine
# for all the quest stuff to be randomized and missable. probably better than excluding it"), and he
# is right: the check is not the hazard. The hazard is fill placing REQUIRED progression on it. So
# the demand is not that the class be ABSENT, it is that every member be NEUTRALISED --
# missable-tagged, which makes features/missable_locations.py forbid advancement items there.
#
# That is a strictly stronger screen than `<= 0` was: it re-derives the population every run, so a
# NEW cross-region gate surfaced by a better datamine fails here instead of silently shipping, and
# it does so without deleting 8 real pickups from the pool.
#
# ⚠️ MEASURED 2026-07-25 by the previous session's report of this screen; NOT re-run in the agent
# sandbox (it needs the AP world package + a real regen). If the first real run reports a different
# number, CONFIRM the true one and update this constant -- do not just lower it. A SHRINK means the
# screen has gone BLIND, not that the game changed.
EXPECTED_CROSS_REGION_GATES = 8

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

    def from_map(gate_map):
        """Resolve the `gate_map` column: the map(s) whose EMEVD SET the gate flag.

        Decoding a flag's NUMBER only works for map-encoded flags, so NPC/questline state flags
        (3708, 3709, 3409 -- bare 4-digit ids) resolved to nothing and their pairs were dropped,
        87 of 104 of them. A flag we cannot decode can still be LOCATED by where it is set, which
        is what datamine_lot_gates now emits.

        A `|`-joined value is a genuine one-to-many. If the maps disagree about the region this
        REFUSES rather than picking one -- an ambiguous gate resolved by first-wins is the
        confident-wrong-answer this whole screen exists to catch.
        """
        regions = set()
        for mid in (gate_map or "").split("|"):
            mid = mid.strip()
            m = re.match(r"(m6[01])_(\d\d)_(\d\d)", mid)
            if m:
                regions.add(tile_region.get((m.group(1), int(m.group(2)), int(m.group(3)))))
            elif re.match(r"m\d\d_\d\d", mid):
                regions.add(dungeon.get(mid[:6]))
        regions.discard(None)
        return regions.pop() if len(regions) == 1 else None

    resolve.from_map = from_map
    return resolve


def test_no_check_is_gated_on_another_regions_flag():
    check_region = {str(f): r for r, locs in LOCATIONS.items() for (_n, _a, f) in locs}
    check_name = {str(f): n for _r, locs in LOCATIONS.items() for (n, _a, f) in locs}
    resolve = _gate_region_resolver()

    pairs = list(_rows("lot_gates.tsv"))
    assert pairs, "lot_gates.tsv parsed to ZERO pairs -- an empty screen is a failure, not a pass"

    check_ap = {str(f): a for _r, locs in LOCATIONS.items() for (_n, a, f) in locs}
    assert MISSABLE_LOCATIONS, (
        "missable_locations.MISSABLE_LOCATIONS is EMPTY -- the protection this screen checks for does "
        "not exist, so every cross-region gate would read as 'neutralised' by an empty set. An empty "
        "oracle is a FAILURE, not a pass.")

    cross, unprotected, decodable = [], [], 0
    by_flag = by_setter = ambiguous = no_handle = 0
    for row in pairs:
        cf, gf = row.get("check_flag"), row.get("gate_flag")
        creg, greg = check_region.get(cf), resolve(gf)
        gate_map = (row.get("gate_map") or "").strip()
        if greg:
            by_flag += 1
        elif gate_map:
            # SECOND HANDLE: where the flag is SET. Covers everything the numeric decode cannot.
            greg = resolve.from_map(gate_map)
            if greg:
                by_setter += 1
            else:
                ambiguous += 1
        else:
            no_handle += 1
        if not creg or not greg:
            continue
        decodable += 1
        if creg != greg:
            where = ("check %s [%s] %s <- gate %s [%s] ctx=%s"
                     % (cf, creg, check_name.get(cf, "")[:40], gf, greg, row.get("context")))
            cross.append(where)
            if check_ap.get(cf) not in MISSABLE_LOCATIONS:
                unprotected.append(where)
    # A screen that decodes nothing would pass silently. Say what it actually examined.
    # Floor MEASURED, not guessed: 17 of 104 decode today. Set just below so a real collapse in the
    # decode rule fails loudly, without pretending the coverage is better than it is.
    # `print` in a PASSING pytest goes into a void (stdout is captured); the warnings summary is the
    # one channel pytest always shows. Coverage has to be legible on a GREEN run -- that is the whole
    # point of a screen that knows how blind it is.
    warnings.warn(
        "[lot-gates screen] %d/%d pairs resolvable -- %d by flag-number decode, %d by setter-map, "
        "%d ambiguous (several maps, different regions -- REFUSED, not guessed), %d with no handle "
        "at all." % (decodable, len(pairs), by_flag, by_setter, ambiguous, no_handle), stacklevel=2)
    if not by_setter and no_handle:
        warnings.warn(
            "lot_gates.tsv has no usable `gate_map` column, so this screen is still running on the "
            "flag-number decode alone (%d of %d pairs invisible). Re-emit with "
            "`python tools/datamine_lot_gates.py --emit` to widen it -- and expect newly-visible "
            "unprotected gates to turn this test red, which is the gate working."
            % (no_handle, len(pairs)), stacklevel=2)
    assert decodable >= 15, (
        "only %d of %d pairs had both sides resolvable (17 did on 2026-07-25, by flag-number decode "
        "alone) -- BOTH handles have failed: the flag-decode rule stopped matching, and the "
        "`gate_map` setter column is absent or unresolvable. This screen is now looking at too "
        "little to mean anything." % (decodable, len(pairs)))
    # THE GATE: cross-region is allowed, UNPROTECTED cross-region is not.
    assert not unprotected, (
        "%d check(s) are gated on a flag from ANOTHER region and are NOT missable-tagged -- each is a "
        "check claiming an early reachability it does not have, which is how fill puts progression "
        "behind a lock the player cannot open. Add the flag to gen_data's _QUESTLINE_GATED (folded "
        "into QUEST_GATED_FLAGS -> MISSABLE) and regen, or give it a real access rule in core.py. NOT "
        "a region change -- the region is right; the reachability claim is not:\n  %s"
        % (len(unprotected), "\n  ".join(unprotected)))
    # A screen that stops FINDING the class passes for the wrong reason (CONTRIBUTING: "an empty
    # result is a FAILURE, not a clean run"). Guard the floor the way _ARENA_FLOOR does.
    assert len(cross) >= EXPECTED_CROSS_REGION_GATES, (
        "this screen found only %d cross-region gate(s); %d were known on 2026-07-25 and all of them "
        "are still supposed to be here (they are randomised + missable now, not excluded). A SHRINK "
        "means the derivation went blind -- lot_gates.tsv, the region decode, or the check->region "
        "join stopped working. Confirm what changed before touching this number:\n  %s"
        % (len(cross), EXPECTED_CROSS_REGION_GATES, "\n  ".join(cross)))
