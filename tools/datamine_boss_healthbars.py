#!/usr/bin/env python3
r"""datamine_boss_healthbars.py -- authoritative boss set = every entity that gets a boss HEALTHBAR.

Matt-free, EMEVD + NpcName FMG only (no MSB needed). ER shows a boss healthbar via
    DisplayBossHealthBar(Enabled, <chrEntityId>, <slot>, <nameId>)
either literally in a map's emevd or through a common template (auto-discovered from common_func).
KEY = the boss's SWEEP TRIGGER FLAG, and the entity id is (for overworld) the tile encoder:
    overworld entity 10.XX.YY.LLLL  -> tile m60_XX_YY  ;  legacy entity AABB.LLLL -> map mAA_BB.
We also read the containing emevd filename (mAA_BB) as the authoritative placement map.

TRIGGER-FLAG DERIVATION (2026-07-15): "defeat flag == entity id" was an ASSUMPTION, and for 14 of
84 field bosses it is FALSE -- their entity-keyed sweep triggers could NEVER fire. The real defeat
flag is what the death event passes to SetEventFlagID:
  * night-class bosses (entity suffix 03xx): 90005860 gets eventFlagId=10XXYY0800 but
    chrEntityId=10XXYY03xx (Death Rite Bird m60_36_45: entity 1036450340, flag 1036450800);
  * duo partners (Tree Sentinel / Mad Pumpkin Head / Nox / Misbegotten 801s): one shared flag for
    the pair -- the 801 partner has NO flag of its own (both entities fold into one entry here);
  * festival/scripted (Radahn 1052380800 -> 1252380800, Fire Giant 1052520800 -> 1252520800,
    Borealis 1054560800 -> 1254560800): the persistent defeat flag has a 12 prefix.
So for FIELD-class bosses the key is the EMEVD-derived defeat flag (parameterized defeat handlers
in common_func/map-local events, or a literal HandleBossDefeatAndDisplayBanner event's first
SetEventFlagID); a field boss whose flag cannot be derived is DROPPED LOUDLY (a trigger that never
fires is worse than none). Interior classes (legacy/catacomb/cave/tunnel/dungeon) keep the entity
id as key -- their sweeps are in-game confirmed; known residual: a few duo/phase PARTNER entities
(e.g. Rogier 12030810, Crucible Knight 30100801) carry entity-keyed triggers that never fire.

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


_DEAD_RE = re.compile(r"CharacterDead\((\w+)\)")
_HPV_RE  = re.compile(r"CharacterHPValue\((\w+)\)\s*[<=]=\s*0")
_SETF_RE = re.compile(r"Set(?:Networkconnected)?EventFlagID\((\w+),\s*ON\)")
_EV_RE   = re.compile(r"\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)\s*\{", re.S)
_INIT_RE = re.compile(r"\$Initialize(?:Common)?Event\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")


def _events(txt):
    """Yield (event_id, [param names], body) for every $Event in a DarkScript emevd .js."""
    idx = [(m.group(1), m.group(2), m.start()) for m in _EV_RE.finditer(txt)]
    for i, (eid, params, start) in enumerate(idx):
        end = idx[i + 1][2] if i + 1 < len(idx) else len(txt)
        yield int(eid), [p.strip() for p in params.split(",")] if params.strip() else [], txt[start:end]


def defeat_flags():
    """{entity id -> defeat event flag}, EMEVD-derived. Two derivations, in trust order:

    1. PARAMETERIZED defeat handlers -- any $Event (common_func 90005860/61/80... or a map-local
       variant like the Tree Sentinel duo's 1041512800) whose body waits on CharacterDead(p) /
       CharacterHPValue(p)<=0 for a PARAM and sets Set[Networkconnected]EventFlagID(q, ON) on a
       PARAM: every $Initialize[Common]Event call maps its entity arg(s) -> its flag arg. These are
       purpose-built defeat events; a handler-derived flag always wins.
    2. LITERAL defeat events -- an unparameterized $Event that waits on literal entity ids AND
       shows HandleBossDefeatAndDisplayBanner: flag = the first Set*EventFlagID after the banner
       (Radahn m60_52_38: banner(1052380800) ... SetEventFlagID(1252380800, ON)). The banner
       requirement keeps NPC-quest death events (e.g. Patches -> 3683) out.

    Ambiguity (an entity reaching two distinct flags within one derivation tier) resolves to the
    entity id itself if it is a candidate, else the entity is ABSENT from the result (caller
    decides: field-class bosses are dropped loudly)."""
    handler_flags = {}   # entity -> set(flags) via derivation 1
    literal_flags = {}   # entity -> set(flags) via derivation 2
    handlers = {}        # event id -> (flag arg idx, [entity arg idx, ...])
    files = sorted(glob.glob(os.path.join(EVT, "*.emevd.dcx.js")))
    for f in files:
        txt = open(f, encoding="utf-8", errors="replace").read()
        for eid, pl, body in _events(txt):
            ents = set(_DEAD_RE.findall(body)) | set(_HPV_RE.findall(body))
            if not ents:
                continue
            if pl:
                eidx = sorted({pl.index(e) for e in ents if e in pl})
                fidx = next((pl.index(m.group(1)) for m in _SETF_RE.finditer(body)
                             if m.group(1) in pl), None)
                if eidx and fidx is not None:
                    handlers[eid] = (fidx, eidx)
            elif "HandleBossDefeatAndDisplayBanner" in body:
                bpos = body.find("HandleBossDefeatAndDisplayBanner")
                m = _SETF_RE.search(body, bpos)
                if m and m.group(1).isdigit():
                    fl = int(m.group(1))
                    for e in ents:
                        if e.isdigit():
                            literal_flags.setdefault(int(e), set()).add(fl)
    for f in files:
        txt = open(f, encoding="utf-8", errors="replace").read()
        for m in _INIT_RE.finditer(txt):
            eid = int(m.group(1))
            if eid not in handlers:
                continue
            args = [a.strip() for a in m.group(2).split(",")]
            fidx, eidxs = handlers[eid]
            if fidx >= len(args) or not args[fidx].isdigit():
                continue
            fl = int(args[fidx])
            for ei in eidxs:
                if ei < len(args) and args[ei].isdigit():
                    handler_flags.setdefault(int(args[ei]), set()).add(fl)
    out = {}
    for ent in set(handler_flags) | set(literal_flags):
        for cands in (handler_flags.get(ent), literal_flags.get(ent)):
            if not cands:
                continue
            if len(cands) == 1:
                out[ent] = next(iter(cands))
            elif ent in cands:
                out[ent] = ent
            else:
                continue   # ambiguous at this tier; try the next / stay absent
            break
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
    # RE-KEY field entries by their EMEVD-derived defeat flag (the only flag that actually fires;
    # see module docstring). Duo partners share one flag -> merge to ONE entry (prefer the partner
    # whose entity id == the flag: it is the primary and names the fight). A field boss with no
    # derivable defeat flag is DROPPED LOUDLY -- an entity-keyed trigger that never fires would be
    # worse (a sweep is a convenience grant, never the only path to a check). Interior classes keep
    # their entity-id keys (in-game confirmed; changing them is churn on working sweeps).
    flags = defeat_flags()
    out, dropped = {}, []
    for ent, b in sorted(bosses.items()):
        if b["class"] != "field":
            out[ent] = b
            continue
        fl = flags.get(ent)
        if fl is None:
            dropped.append((ent, b["name"]))
            continue
        if fl in out and out[fl]["class"] == "field":
            if fl == ent:              # primary partner wins the entry
                out[fl] = b
            continue                   # duo partner folded into the primary's entry
        out[fl] = b
    for ent, name in dropped:
        print(f"[boss_healthbars] DROPPED field boss {ent} ({name or '?'}): no derivable defeat flag")
    return out


def _write(bosses):
    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        f.write('"""AUTO-GENERATED by tools/datamine_boss_healthbars.py -- DO NOT EDIT (regenerate: '
                'python tools/datamine_boss_healthbars.py; see gen-greenfield.ps1).\n')
        f.write("Every boss that gets a healthbar (DisplayBossHealthBar). Key = SWEEP TRIGGER = the boss's\n")
        f.write("defeat event flag: EMEVD-derived for field bosses (entity id != defeat flag for night/duo/\n")
        f.write('festival bosses; duo partners merge), entity id for interior classes. name is advisory."""\n')
        f.write("# defeat_flag: (map, tile, class, name)\n")
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
