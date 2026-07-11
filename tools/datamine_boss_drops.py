#!/usr/bin/env python3
r"""datamine_boss_drops.py -- derive the "Boss" location class = boss-healthbar enemy DROPS
(field/evergaol/dragon bosses), EXCLUDING remembrance/great-rune bosses (those are their own classes).

Matt-free, params+EMEVD only (no MSB needed). ER's common boss-handler events carry BOTH the boss
entity AND its reward item-lot as InitializeCommonEvent arguments:

    $Event(90005860, Restart, function(eventFlagId, eventFlagId2, chrEntityId, value, itemLotId, ...))
        ... HandleBossDefeatAndDisplayBanner(chrEntityId, TextBannerType.EnemyFelled); ...

So we: (1) auto-discover the boss-handler common events from common_func (any $Event whose body calls
HandleBossDefeatAndDisplayBanner AND whose signature has an `itemLotId` param) + the arg index of the
entity and the lot; (2) scan every map event for $InitializeCommonEvent of those handlers -> (entity,
rewardLot); (3) rewardLot -> ItemLotParam_map (base + consecutive rows) -> getItemFlagId -> region_map
AP location; (4) drop remembrance/great-rune rewards (major bosses). Handlers WITHOUT an itemLotId
(9005840 Demigod) are major bosses with no item drop -> naturally excluded.

Emits greenfield/eldenring/boss_drops.py: BOSS_DROP_FLAGS (getItemFlagId set) + BOSS_DROP_AP (ap ids).
gen_data.py tags these 'Boss' (retiring the old boss_arena->Boss). Run on Windows (fast local I/O):
    python tools/datamine_boss_drops.py            # regenerate boss_drops.py
    python tools/datamine_boss_drops.py --list      # print the reviewable list, write nothing
"""
import csv, re, glob, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR   = os.path.join(REPO, "elden_ring_artifacts")
VV   = os.path.join(AR, "vanilla_er", "vanilla_er")
EVT  = os.path.join(AR, "event")
GF   = os.path.join(REPO, "greenfield")
OUT  = os.path.join(GF, "eldenring", "boss_drops.py")

_REMEMBRANCE = ("remembrance",)  # name guards for the excluded major-boss rewards
def _is_excluded_item(name):
    n = (name or "").lower()
    return ("remembrance" in n) or ("great rune" in n)


def boss_handlers():
    """{commonEventId: (entityArgIdx, itemLotArgIdx)} for common events that display a boss banner
    AND carry an itemLotId param. Parsed from common_func so it survives param-order changes."""
    cf = open(os.path.join(EVT, "common_func.emevd.dcx.js"), encoding="utf-8").read()
    ev = re.compile(r"\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)\s*\{", re.S)
    idxs = [(m.group(1), m.group(2), m.start()) for m in ev.finditer(cf)]
    out = {}
    for i, (eid, params, start) in enumerate(idxs):
        end = idxs[i + 1][2] if i + 1 < len(idxs) else len(cf)
        body = cf[start:end]
        if "HandleBossDefeatAndDisplayBanner" not in body:
            continue
        pl = [p.strip() for p in params.split(",")] if params.strip() else []
        if "itemLotId" not in pl:
            continue
        m = re.search(r"HandleBossDefeatAndDisplayBanner\(\s*(\w+)", body)
        if not m or m.group(1) not in pl:
            continue
        out[int(eid)] = (pl.index(m.group(1)), pl.index("itemLotId"))
    return out


def map_lot_flags(mlot, flagcols, base):
    out = []
    for off in range(0, 16):  # a reward lot is a consecutive block from the base id
        r = mlot.get(base + off)
        if not r:
            break
        out += [int(r[c]) for c in flagcols
                if r[c].strip().lstrip("-").isdigit() and int(r[c]) > 0]
    return out


def datamine():
    handlers = boss_handlers()
    mp = list(csv.DictReader(open(os.path.join(VV, "ItemLotParam_map.csv"))))
    mlot = {int(r["ID"]): r for r in mp}
    flagcols = [c for c in mp[0].keys() if c.startswith("getItemFlagId")]
    rm = {int(r["flag"]): r for r in csv.DictReader(open(os.path.join(GF, "region_map.csv")))
          if r["flag"].strip().lstrip("-").isdigit()}
    call = re.compile(r"\$InitializeCommonEvent\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")
    seen_lot = set()
    rows = []  # (entity, lot, flag, item, region, method)
    for f in sorted(glob.glob(os.path.join(EVT, "m*.js"))):
        t = open(f, encoding="utf-8").read()
        for m in call.finditer(t):
            cid = int(m.group(1))
            if cid not in handlers:
                continue
            args = [a.strip() for a in m.group(2).split(",")]
            ei, li = handlers[cid]
            try:
                ent, lot = int(args[ei]), int(args[li])
            except (ValueError, IndexError):
                continue
            if lot <= 0 or lot in seen_lot:
                continue
            seen_lot.add(lot)
            for fl in map_lot_flags(mlot, flagcols, lot):
                loc = rm.get(fl)
                if loc and not _is_excluded_item(loc["item_name"]):
                    rows.append((ent, lot, fl, loc["item_name"], loc["region"], loc["method"]))
    # dedup by flag (a lot can list the same flag twice for MP)
    uniq = {}
    for r in rows:
        uniq[r[2]] = r
    return handlers, sorted(uniq.values(), key=lambda r: (r[4], r[3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the reviewable list, write nothing")
    a = ap.parse_args()
    handlers, rows = datamine()
    flags = sorted({r[2] for r in rows})
    print(f"boss-handler common events: {sorted(handlers)}")
    print(f"Boss-drop AP locations: {len(rows)}  (distinct flags {len(flags)}, items {len({r[3] for r in rows})})")
    if a.list:
        for ent, lot, fl, item, region, method in rows:
            print(f"  ent {ent:<11} flag {fl:<9} {item[:34]:34} | {region[:26]} | {method}")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write('"""AUTO-GENERATED (tools/datamine_boss_drops.py). Boss-healthbar enemy DROPS\n')
        f.write('(field/evergaol/dragon bosses; remembrance/great-rune majors excluded). getItemFlagId\n')
        f.write('set + names for gen_data to tag \'Boss\'. Matt-free (EMEVD common-event args + params)."""\n')
        f.write("BOSS_DROP_FLAGS = frozenset({\n")
        for _e, _l, fl, item, _r, _m in rows:
            f.write(f"    {fl},  # {item}\n")
        f.write("})\n")
    print(f"wrote {OUT}: {len(flags)} boss-drop flags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
