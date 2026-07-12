#!/usr/bin/env python3
r"""datamine_boss_reward_lots.py -- derive the MINI-DUNGEON / scripted BOSS-REWARD lot family.

WHY THIS EXISTS (Alaric, playtest 2026-07-12): he killed the Unsightly Catacombs duo (m30_12), got
the vanilla Perfumer Tricia ash, and no check fired -- while all five of that map's TREASURE checks
randomised correctly. The boss's reward is NOT reachable from the boss:

    NpcParam[34600930].itemLotId_enemy = -1     (Misbegotten Warrior)
    NpcParam[37011930].itemLotId_enemy = -1     (Perfumer Tricia)

...and m30_12's EMEVD calls HandleBossDefeatAndDisplayBanner INLINE with no itemLotId anywhere near
it. There is nothing in the map, and nothing on the enemy, to find.

The award lives in common.emevd:

    // ボス撃破_アイテム取得_YY -- Defeat boss_obtain item_YY
    $Event(1200, Default, function(eventFlagId, itemLotId, itemLotId2, eventFlagId2) {
        WaitFor(EventFlag(eventFlagId));
        AwardItemsIncludingClients(itemLotId);
    });
    $InitializeEvent(11, 1200, 9211, 20110, 0, 520110);      <- registered IN common.emevd

and the map merely flips the reward flag:

    m30_12  ...  HandleBossDefeatAndDisplayBanner(30120800, EnemyFelled);
                 SetEventFlagID(9211, ON);                    <- reward flag

So the join is  map EMEVD SetEventFlagID(rewardFlag) -> common.emevd $InitializeEvent(_, H, rewardFlag,
itemLotId, itemLotId2, getItemFlag) -> ItemLotParam_map[itemLotId].getItemFlagId.

tools/datamine_boss_drops.py CANNOT see this family: it scans MAP events for $InitializeCommonEvent of
handlers taking an itemLotId. This family is registered with $InitializeEvent inside common.emevd
ITSELF, so the map-side scan is structurally blind to it -- which is why BOSS_DROP_FLAGS has 88 entries
and ZERO catacomb/cave/tunnel/dungeon bosses. It was never a coverage gap in the SCAN; it is a
different mechanism.

Handlers are AUTO-DISCOVERED (any common.emevd $Event whose body awards an item lot and whose signature
is (eventFlagId, itemLotId, itemLotId2, eventFlagId2)) rather than hardcoded to 1100/1200, so a sibling
handler cannot hide from this tool the way this family hid from the other one.

Emits greenfield/eldenring/boss_reward_lots.py:
    BOSS_REWARD_TILE  {getItemFlagId: "mBB_SS"}   -- gen_data._recover_tile decodes the family with this
    BOSS_REWARD_LOT   {getItemFlagId: itemLotId}  -- provenance / audit

    python tools/datamine_boss_reward_lots.py            # regenerate
    python tools/datamine_boss_reward_lots.py --list     # print the reviewable list, write nothing
"""
import re, glob, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR   = os.path.join(REPO, "elden_ring_artifacts")
EVT  = os.path.join(AR, "event")
GF   = os.path.join(REPO, "greenfield")
OUT  = os.path.join(GF, "eldenring", "boss_reward_lots.py")

# (eventFlagId, itemLotId, itemLotId2, eventFlagId2) -- the shape of the award handlers we accept.
_SIG = ("eventFlagId", "itemLotId", "itemLotId2", "eventFlagId2")
_AWARD = ("AwardItemsIncludingClients", "AwardItemLot")


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def award_handlers(common_src):
    """{eventId: comment} for common.emevd $Event bodies that award a lot off a flag with sig _SIG.

    Discovered, not hardcoded: the whole point of this tool is that a handler hid from the other one.
    """
    out = {}
    for m in re.finditer(r"(//[^\n]*\n)?\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)(.*?)\n\}\);",
                         common_src, re.S):
        cmt, eid, params, body = m.group(1) or "", m.group(2), m.group(3), m.group(4)
        if not any(a in body for a in _AWARD):
            continue
        if tuple(p.strip() for p in params.split(",")) != _SIG:
            continue
        out[int(eid)] = cmt.strip().lstrip("/ ").strip()
    return out


def registrations(common_src, handlers):
    """[(handler, rewardFlag, lot, lot2, getFlag)] from $InitializeEvent(slot, H, ...) in common.emevd."""
    out = []
    for h in sorted(handlers):
        pat = (r"\$InitializeEvent\(\s*\d+\s*,\s*%d\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)" % h)
        for m in re.finditer(pat, common_src):
            rf, lot, lot2, gf = (int(x) for x in m.groups())
            out.append((h, rf, lot, lot2, gf))
    return out


def flag_to_map():
    """{rewardFlag: {map_prefix}} -- every map EMEVD that flips a 4-digit reward flag ON."""
    out = {}
    for fp in glob.glob(os.path.join(EVT, "m*.emevd.dcx.js")):
        mp = os.path.basename(fp).split(".")[0]          # m30_12_00_00 / m60_43_37_00
        # Overworld tiles are addressed XX_YY: truncating to two parts (m60_43) throws the YY away and
        # region_of would then nearest-neighbour it to the wrong tile. Interiors really are 2 (m30_12).
        _p = mp.split("_")
        tile = "_".join(_p[:3]) if _p[0] in ("m60", "m61") else "_".join(_p[:2])
        for f in set(re.findall(r"SetEventFlagID\((\d{4}),\s*ON\)", _read(fp))):
            out.setdefault(int(f), set()).add(tile)
    return out


def derive():
    """[(getFlag, tile, lot, rewardFlag, handler, note)] -- note is '' when the join is unambiguous."""
    common = _read(os.path.join(EVT, "common.emevd.dcx.js"))
    handlers = award_handlers(common)
    f2m = flag_to_map()
    rows, skipped = [], []
    for h, rf, lot, lot2, gf in registrations(common, handlers):
        maps = sorted(f2m.get(rf, ()))
        if len(maps) == 1:
            rows.append((gf, maps[0], lot, rf, h, ""))
        elif not maps:
            skipped.append((gf, lot, rf, h, "no map EMEVD flips this reward flag"))
        else:
            # Ambiguous: more than one map flips it. Do NOT guess -- an invented attribution is how a
            # check lands in the wrong region and a progression item strands there.
            skipped.append((gf, lot, rf, h, "reward flag flipped by %d maps: %s" % (len(maps), ",".join(maps))))
    return handlers, sorted(rows), sorted(skipped)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the reviewable list, write nothing")
    a = ap.parse_args()
    handlers, rows, skipped = derive()

    print("award handlers discovered in common.emevd: %s" % ", ".join(
        "%d (%s)" % (h, c or "?") for h, c in sorted(handlers.items())))
    print("attributed: %d   unattributed: %d" % (len(rows), len(skipped)))
    if a.list:
        print("\n%-9s %-8s %-8s %-7s %s" % ("getFlag", "tile", "lot", "rwFlag", "handler"))
        for gf, tile, lot, rf, h, _n in rows:
            print("%-9d %-8s %-8d %-7d %d" % (gf, tile, lot, rf, h))
    if skipped:
        print("\nUNATTRIBUTED (left OUT of the table -- they stay unrecovered, as before):")
        for gf, lot, rf, h, why in skipped:
            print("    getFlag %-9d lot %-8d rewardFlag %-7d handler %-5d %s" % (gf, lot, rf, h, why))
    if a.list:
        return

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write('"""AUTO-GENERATED (tools/datamine_boss_reward_lots.py) -- DO NOT EDIT.\n\n')
        f.write("Mini-dungeon / scripted BOSS-REWARD lots: common.emevd awards these off a reward flag the\n")
        f.write("map EMEVD flips, so neither NpcParam nor the map-side common-event scan can see them.\n")
        f.write("BOSS_REWARD_TILE lets gen_data._recover_tile decode the 6-digit 5xxxxx flag family, which\n")
        f.write("carries no map encoding of its own and was therefore being dropped from the world.\n")
        f.write('"""\n')
        f.write("# handler -> what it is (auto-discovered by signature + award call, not hardcoded)\n")
        f.write("BOSS_REWARD_HANDLERS = %r\n\n" % {h: (c or "") for h, c in sorted(handlers.items())})
        f.write("BOSS_REWARD_TILE = {\n")
        for gf, tile, lot, rf, h, _n in rows:
            f.write("    %d: %r,   # lot %d, reward flag %d, handler %d\n" % (gf, tile, lot, rf, h))
        f.write("}\n\n")
        f.write("BOSS_REWARD_LOT = {\n")
        for gf, tile, lot, rf, h, _n in rows:
            f.write("    %d: %d,\n" % (gf, lot))
        f.write("}\n")
    print("\nwrote %s (%d flags)" % (OUT, len(rows)))


if __name__ == "__main__":
    main()
