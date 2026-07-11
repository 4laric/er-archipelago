#!/usr/bin/env python3
r"""datamine_boss_healthbars.py -- authoritative boss set = every entity that gets a boss HEALTHBAR.

Matt-free, EMEVD + NpcName FMG only (no MSB needed). ER shows a boss healthbar via
    DisplayBossHealthBar(Enabled, <chrEntityId>, <slot>, <nameId>)
either literally in a map's emevd or through a common template (auto-discovered from common_func).
The boss's DEFEAT event flag == its entity id (bosses do SetEventFlagID(<entity>, ON) on death), so
the entity id is BOTH the sweep trigger flag and (for overworld) the tile encoder:
    overworld entity 10.XX.YY.LLLL  -> tile m60_XX_YY  ;  legacy entity AABB.LLLL -> map mAA_BB.
We also read the containing emevd filename (mAA_BB) as the authoritative placement map.

Class (by map): m30=catacomb, m31=cave, m32=tunnel, m60=field, everything else=legacy/interior.
gen_data.py consumes this to scope sweeps per class (region-wide for legacy, map-local for
catacomb/cave/tunnel, own-tile+filler-only for field). nameId -> boss name via NpcName.fmg.xml
(Witchy XML); names are advisory (empty if the FMG is absent). Run on Windows (fast local I/O):
    python tools/datamine_boss_healthbars.py            # regenerate boss_healthbars.py
    python tools/datamine_boss_healthbars.py --list      # print the reviewable list, write nothing
"""
import csv, re, glob, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR   = os.path.join(REPO, "elden_ring_artifacts")
EVT  = os.path.join(AR, "event")
MSG  = os.path.join(AR, "msg")
GF   = os.path.join(REPO, "greenfield")
OUT  = os.path.join(GF, "eldenring", "boss_healthbars.py")

_MAPFILE = re.compile(r"(m\d\d)_(\d\d)_\d\d_\d\d\.emevd\.dcx\.js$")   # mAA_BB from a map emevd filename
_LIT     = re.compile(r"DisplayBossHealthBar\(\s*(?:Enabled|1)\s*,\s*(\d+)\s*,\s*\d+\s*,\s*(\d+)")
_INITC   = re.compile(r"\$InitializeCommonEvent\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")


# Minor dungeons that sweep MAP-LOCAL (their own map's checks), like catacombs. Beyond m30/31/32
# these are the Divine Towers (m34), Ruin-Strewn Precipice (m39), and the DLC minor dungeons
# (m40 catacombs / m41 gaols / m42 forges / m43 caves). The region-MAJOR legacy dungeons (m10
# Stormveil, m11 Leyndell, m13 Farum, m14 Raya Lucaria, m15 Haligtree, m16 Volcano, m19 Fractured
# Marika, m20 Belurat, m21 Shadow Keep, m35 Shunning-Grounds, ...) stay region-wide.
_MINOR_DUNGEON_MAPS = {"m34", "m39", "m40", "m41", "m42", "m43"}
def _class(map_ab):
    p = map_ab[:3]
    named = {"m30": "catacomb", "m31": "cave", "m32": "tunnel", "m60": "field"}
    if p in named:
        return named[p]
    return "dungeon" if p in _MINOR_DUNGEON_MAPS else "legacy"


def hb_handlers():
    """{commonEventId: (entityArgIdx, nameIdArgIdx|None)} for common events that Enable a boss
    healthbar with a parameter entity. Parsed from common_func so param-order changes don't break it."""
    cf = open(os.path.join(EVT, "common_func.emevd.dcx.js"), encoding="utf-8").read()
    ev = re.compile(r"\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)\s*\{", re.S)
    idx = [(m.group(1), m.group(2), m.start()) for m in ev.finditer(cf)]
    out = {}
    for i, (eid, params, start) in enumerate(idx):
        end = idx[i + 1][2] if i + 1 < len(idx) else len(cf)
        body = cf[start:end]
        m = re.search(r"DisplayBossHealthBar\(\s*(?:Enabled|1)\s*,\s*(\w+)\s*,\s*\w+\s*,\s*(\w+)", body)
        if not m:
            continue
        pl = [p.strip() for p in params.split(",")] if params.strip() else []
        if m.group(1) not in pl:
            continue
        out[int(eid)] = (pl.index(m.group(1)), pl.index(m.group(2)) if m.group(2) in pl else None)
    return out


def load_names():
    """nameId(int) -> boss name, merged over every NpcName*.fmg.xml under elden_ring_artifacts/msg."""
    names = {}
    if not os.path.isdir(MSG):
        return names
    txt = re.compile(r'<text id="(\d+)"[^>]*>(.*?)</text>', re.S)
    for f in sorted(glob.glob(os.path.join(MSG, "**", "NpcName*.fmg.xml"), recursive=True)):
        for m in txt.finditer(open(f, encoding="utf-8").read()):
            v = re.sub(r"&lt;\?null\?&gt;|<[^>]*>", "", m.group(2)).strip()
            if v:
                names.setdefault(int(m.group(1)), v)  # base wins; DLC only fills gaps
    return names


def datamine():
    handlers = hb_handlers()
    bosses = {}   # entity -> {"map": mAA_BB, "class": ..., "nameId": int|None}
    for f in sorted(glob.glob(os.path.join(EVT, "m*.js"))):
        fn = os.path.basename(f)
        mm = _MAPFILE.match(fn)
        if not mm:
            continue
        map_ab = f"{mm.group(1)}_{mm.group(2)}"
        t = open(f, encoding="utf-8").read()
        for m in _LIT.finditer(t):
            ent, nid = int(m.group(1)), int(m.group(2))
            b = bosses.setdefault(ent, {"map": map_ab, "class": _class(map_ab), "nameId": None})
            if b["nameId"] is None and nid:
                b["nameId"] = nid
        for m in _INITC.finditer(t):
            cid = int(m.group(1))
            if cid not in handlers:
                continue
            args = [a.strip() for a in m.group(2).split(",")]
            ei, ni = handlers[cid]
            if ei >= len(args) or not args[ei].lstrip("-").isdigit():
                continue
            ent = int(args[ei])
            b = bosses.setdefault(ent, {"map": map_ab, "class": _class(map_ab), "nameId": None})
            if b["nameId"] is None and ni is not None and ni < len(args) and args[ni].lstrip("-").isdigit():
                b["nameId"] = int(args[ni])
    names = load_names()
    for ent, b in bosses.items():
        b["name"] = names.get(b["nameId"] or -1, "")
        if b["class"] == "field":                      # overworld entity 10.XX.YY.LLLL -> tile
            s = str(ent)
            b["tile"] = f"m60_{s[2:4]}_{s[4:6]}" if len(s) == 10 and s.startswith("10") else b["map"]
        else:
            b["tile"] = b["map"]
    return bosses


def _write(bosses):
    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        f.write('"""AUTO-GENERATED by tools/datamine_boss_healthbars.py -- DO NOT EDIT (regenerate: '
                'python tools/datamine_boss_healthbars.py; see gen-greenfield.ps1).\n')
        f.write("Every entity that gets a boss healthbar (DisplayBossHealthBar). Key = entity id = boss\n")
        f.write('defeat event flag = sweep trigger. Matt-free (EMEVD + NpcName FMG). name is advisory."""\n')
        f.write("# entity_flag: (map, tile, class, name)\n")
        f.write("BOSS_HEALTHBARS = {\n")
        for ent in sorted(bosses):
            b = bosses[ent]
            f.write("    %d: (%r, %r, %r, %s),\n" % (ent, b["map"], b["tile"], b["class"], ascii(b["name"])))
        f.write("}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the reviewable list; write nothing")
    a = ap.parse_args()
    bosses = datamine()
    from collections import Counter
    c = Counter(b["class"] for b in bosses.values())
    print("boss_healthbars: %d entities across %d maps | %s" % (
        len(bosses), len({b["map"] for b in bosses.values()}), dict(c)))
    if a.list:
        for ent in sorted(bosses):
            b = bosses[ent]
            print(f"  {ent}  {b['tile']:12} {b['class']:9} {b['name']}")
        return
    _write(bosses)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
