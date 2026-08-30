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
# ONE definition of the boss-class taxonomy, imported rather than restated (a second copy would
# drift, and this one is already the input to DungeonSweep's rungs).
import importlib.util as _ilu
_hbspec = _ilu.spec_from_file_location("_dm_hb", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                             "datamine_boss_healthbars.py"))
_hb = _ilu.module_from_spec(_hbspec); _hbspec.loader.exec_module(_hb)
_class = _hb._class
_geography = _hb._geography

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR   = os.path.join(REPO, "elden_ring_artifacts")
VV   = os.path.join(AR, "vanilla_er", "vanilla_er")
EVT  = os.path.join(AR, "event")
GF   = os.path.join(REPO, "greenfield")
OUT  = os.path.join(GF, "eldenring", "boss_drops.py")
MIN_DROP_ROWS = 88
MIN_DROP_MAPS = 71

# One reward lot can be initialized at more than one encounter. The general dedup is first-call
# wins, but Lansseax's lot 30300 is present at both the Coffin apparition and the terminal
# Rampartside fight. Sweep ownership must follow the terminal kill flag/entity; otherwise killing
# her normally never pays the sweep. This is deliberately lot-shaped and guarded below.
_CANONICAL_REUSED_LOT_ENTITY = {30300: 1041520800}

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
    rows = []  # (entity, lot, flag, item, region, method, emevd_map)
    for f in sorted(glob.glob(os.path.join(EVT, "m*.js"))):
        # The CONTAINING emevd is the authoritative placement map (datamine_boss_healthbars says so
        # and classifies off it). m10_00.emevd.dcx.js -> m10_00 -> class 'legacy'.
        emap = os.path.basename(f).split(".")[0]
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
            canonical = _CANONICAL_REUSED_LOT_ENTITY.get(lot)
            if canonical is not None and ent != canonical:
                continue
            if lot <= 0 or lot in seen_lot:
                continue
            seen_lot.add(lot)
            for fl in map_lot_flags(mlot, flagcols, lot):
                loc = rm.get(fl)
                if loc and not _is_excluded_item(loc["item_name"]):
                    rows.append((ent, lot, fl, loc["item_name"], loc["region"], loc["method"], emap))
    # dedup by flag (a lot can list the same flag twice for MP)
    uniq = {}
    for r in rows:
        uniq[r[2]] = r
    found_canonical = {lot: ent for ent, lot, *_ in rows if lot in _CANONICAL_REUSED_LOT_ENTITY}
    assert found_canonical == _CANONICAL_REUSED_LOT_ENTITY, (
        "canonical reused boss lots stopped matching their terminal call sites: %r" % found_canonical)
    return handlers, sorted(uniq.values(), key=lambda r: (r[4], r[3]))


def require_complete_rows(rows):
    """Refuse a large-looking result that silently lost a map/event family (#531)."""
    maps = {row[6] for row in rows}
    missing = []
    if len(rows) < MIN_DROP_ROWS:
        missing.append(f"drops={len(rows)} (minimum {MIN_DROP_ROWS})")
    if len(maps) < MIN_DROP_MAPS:
        missing.append(f"maps={len(maps)} (minimum {MIN_DROP_MAPS})")
    if missing:
        raise SystemExit(
            "FATAL: boss-drop derivation is incomplete: "
            + ", ".join(missing)
            + ". Refusing to publish an answer."
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the reviewable list, write nothing")
    a = ap.parse_args()
    handlers, rows = datamine()
    require_complete_rows(rows)
    flags = sorted({r[2] for r in rows})
    print(f"boss-handler common events: {sorted(handlers)}")
    print(f"Boss-drop AP locations: {len(rows)}  (distinct flags {len(flags)}, items {len({r[3] for r in rows})})")
    if a.list:
        for ent, lot, fl, item, region, method, emap in rows:
            print(f"  ent {ent:<11} flag {fl:<9} {_geography(emap):11} {emap:11} "
                  f"{item[:30]:30} | {region[:22]} | {method}")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write('"""AUTO-GENERATED (tools/datamine_boss_drops.py). Boss-healthbar enemy DROPS\n')
        f.write('(field/evergaol/dragon bosses; remembrance/great-rune majors excluded). getItemFlagId\n')
        f.write('set + names for gen_data to tag \'Boss\'. Matt-free (EMEVD common-event args + params)."""\n')
        f.write("BOSS_DROP_FLAGS = frozenset({\n")
        for _e, _l, fl, item, _r, _m, _mp in rows:
            f.write(f"    {fl},  # {item}\n")
        f.write("})\n")
        f.write('\n# flag -> the boss ENTITY that drops it, and the CLASS of the map it stands in.\n')
        f.write('# The entity and the lot arrive together in the same common-event args\n')
        f.write('# ($Event(90005860, ..., chrEntityId, ..., itemLotId, ...)), and this tool has always\n')
        f.write('# read both -- it just discarded the entity, so nothing could join a boss CHECK to its\n')
        f.write('# boss. That join is what LegacyBoss/Underground/FieldBoss need, and it could not be\n')
        f.write('# recovered downstream: DUNGEON_SWEEPS is filler-only by construction, so a boss reward\n')
        f.write('# check is never inside its own sweep (measured: legacy sweeps x Boss-tagged aps = 0).\n')
        f.write('# GEOGRAPHY is WHERE THE BOSS STANDS, via datamine_boss_healthbars._geography --\n')
        f.write('# field (m60 + m61, both overworlds) / underground (catacomb, cave, tunnel, minor\n')
        f.write('# dungeon) / legacy. ONE definition, imported, not restated.\n')
        f.write('# 🛑 NOT the same question as _class, which answers "how should this boss SWEEP?" and\n')
        f.write('# must keep calling m61 legacy so its sweeps survive (see _class docstring). Using the\n')
        f.write('# sweep class for geography labelled 15 DLC OVERWORLD boss checks legacy-dungeon.\n')
        f.write("BOSS_DROP_ENTITY = {\n")
        for ent, _l, fl, item, _r, _m, _mp in rows:
            f.write(f"    {fl}: {ent},  # {_mp} {item}\n")
        f.write("}\n")
        f.write("BOSS_DROP_GEOGRAPHY = {\n")
        for _e, _l, fl, _item, _r, _m, mp in rows:
            f.write(f"    {fl}: {_geography(mp)!r},\n")
        f.write("}\n")
    print(f"wrote {OUT}: {len(flags)} boss-drop flags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
