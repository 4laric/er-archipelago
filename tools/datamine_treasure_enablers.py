#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_treasure_enablers.py -- what actually enables a StartDisabled=1 MSB treasure.

THE QUESTION IT WAS BUILT TO ANSWER, AND THE ANSWER IT GOT
----------------------------------------------------------
greenfield/msb_gated_treasures.tsv lists 163 MSB Event/Treasure records with StartDisabled=1 --
155 rows = 136 DISTINCT live AP checks. The standing reading was: "the pickup does not exist at map
load, so 135 checks are placed as reachable while the player cannot open them -- fill can put
progression behind a door that is not there."

MEASURED, THAT READING IS WRONG, and the control that breaks it is in the producing tool's own
output. The whole-corpus (InChest, StartDisabled) cross-tab is:

    InChest=0  StartDisabled=0 : 3112      InChest=0  StartDisabled=1 :   1
    InChest=1  StartDisabled=0 :  117      InChest=1  StartDisabled=1 : 141
    InChest=2  StartDisabled=0 :  502      InChest=2  StartDisabled=1 :  21

162 of the 163 StartDisabled=1 records are InChest>=1. Of the 3113 pickups that are NOT in a
container, exactly ONE is StartDisabled -- 0.03%. StartDisabled tracks the CONTAINER, not access.

The independent confirmation is structural, and it is the reason this tool exists rather than a
hand-written list. `EnableAssetTreasure` is addressed by an ENTITY ID. 54 of the 136 distinct live
checks have NO entity id at all -- the Treasure event's EntityID is 0 AND the Part/Asset's EntityID
is 0 -- so no EMEVD instruction in the game can ever name them. They are nonetheless ordinary loot:
Stormveil's Godslayer's Seal and Curved Sword Talisman, Leyndell's Blessed Dew Talisman, five Farum
Azula chests, Roundtable Hold's Assassin's Prayerbook. A flag whose only documented meaning is
"an event must enable this" cannot mean that on 54 checks that no event can address.

So StartDisabled=1 on a chest is the ordinary closed-chest mechanic: the item is not in the world
until the lid opens. It is not a gate, and msb_gated_treasures.tsv is not a risk list.

WHAT IS LEFT AFTER THAT -- and it is small, and it is real
---------------------------------------------------------
This tool does the join anyway, because "the premise is wrong" is not a substitute for the number.
It resolves every treasure-enable site in the decompiled EMEVD to a concrete entity id and joins it
back to the gated treasures. What survives is a handful of genuinely event-driven pickups.

🛑 THE VOCABULARY IS MEASURED, AND THE OBVIOUS VERB IS THE MINORITY ONE. Corpus counts:
    EnableAssetTreasure 34   DisableAssetTreasure 29   ForceCharacterTreasure 190
    EnableObjAct       124   DisableObjAct        191
`EnableObjAct` is not a treasure verb at all -- it toggles whether a chest can be INTERACTED with --
and it is how the single most interesting case in the set is gated. f114, the Dark Moon Ring chest
in the Raya Lucaria Grand Library, has no EnableAssetTreasure anywhere; it is `DisableObjAct` until
the post-Rennala warp sequence runs `EnableObjAct(14001606, 199630)`. Scanning only the treasure
verbs would have filed it under "unexplained".

🛑 AND THE ENTITY KEY IS TWO KEYS. EnableAssetTreasure accepts EITHER entity space:
    m15_00  EnableAssetTreasure(15001810)   -> the Part/Asset EntityID
    m60_39_53 EnableAssetTreasure(1039533501) -> the Treasure EVENT's EntityID, whose asset is a
              different id (1039531480), enabled separately by EnableAsset on the adjacent line
Joining on one key alone drops the other family. Both are tried and `key_space` records which hit.

🛑 AND THE ARGUMENT IS USUALLY A PARAMETER. 194 of the 224 enable sites pass a param, not a literal;
the literal lives at the $InitializeCommonEvent / $InitializeEvent CALL SITE. This is the same
indirection documented in datamine_lot_gates.py. A literal-only scan sees 30 of 224 sites.

POLARITY IS NOT ASSIGNED. `gate_verbatim` is the construct, copied out. `gate_kind` is a HINT from
the construct's vocabulary, never a prerequisite claim: `AssetDestroyed(x)` means "break this pot
where it stands" and is NOT a cross-region requirement; `EndIf(EventFlag(p))` is a bail-out with
inverted sense. A false gate is an unwinnable seed; a missed one is only a miss.

USAGE
    python tools/datamine_treasure_enablers.py --vocab   # LOOK first. Emits nothing.
    python tools/datamine_treasure_enablers.py --emit
    ER_EVENT_DIR=<dir> lets the decompiled EMEVD be staged outside the repo (AGENTS.md 5).
OUTPUT: greenfield/treasure_enablers.tsv

## THE ASSET-DISABLE CLASS IS NOW FULLY SWEPT (2026-07-26) -- closed, with the score

`StartDisabled` is one way to hide a treasure; the other is an event that turns it OFF
(`DisableAssetTreasure` / `DisableObjAct`) and only turns it on later. No award site is involved, so
`datamine_lot_gates.py` structurally cannot see that class. Resolving those sites through their
`$InitializeEvent` CALL SITES takes 137 literal ObjAct sites to 1670 -- the same call-site blind spot
as the lot gates, for the fourth time.

Every live check that any event disables was chased. FINAL SCORE:

  * ~35 are COMMON events and are the ordinary lifecycle, not gates. Verified 90005560 =
    "[Common] Destruction asset treasure": the treasure is off until you smash the pot, then on.
  * the ObjAct-gated ones are same-map: 9 are `$Event(<map>0790)` "restrictions on opening boss-room
    reward chests" on that map's own boss, and f114 (Dark Moon Ring) is EnableObjAct after Rennala.
  * 🔥 TWO REAL FINDINGS, both now tagged missable in gen_data._NPC_STATE_GATED (6b64d3b):
      - EDGAR: m60_33_44 $Event(1033440705) disables f1033447000/7010/7020/7030/7040 ("Raw Meat
        Dumpling near Revenger's Shack" x5) until EventFlag(3409), a state in Edgar's state machine
        $Event(3419). Same shack and questline as f400061, which was already tagged -- these five
        were invisible to the screen that caught it.
      - PATCHES: m31_00 $Event(31002875) swaps a PAIR on EventFlag(3691), a state in Patches'
        $Event(3699). f31007010 "Cloth Garb" (Alaric: the chest Patches ambushes you at) and
        f31007030 "Glass Shard". Exactly one exists at a time.
  * and the last 8 map-local disables were chased on 2026-07-26 and are ALL BENIGN:
      f12017090  m12_01  gated on 12010593, same map
      f16007710  m16_00  mid-boss 16000850, same map
      f20007810  m20_00  boss 20000800, same map
      f21017120  m21_01  flags 72112/72113 -- both are m21_01 GRACES, same map
      f35007000  m35_00  swapped on flag 300 (the Erdtree burn) between assets 35001606 and
                         35001607 -- but BOTH carry the SAME flag AND the same lot 35000000, so the
                         check survives the burn on the other body. A map-version swap that
                         preserves the check: the benign form of the dup-lot family.
      f1048577810 m60_48_57  map-local warp event, same map
      f580410 / f580420  DLC: `EndIf(EventFlag(eventFlagId))` where the call site passes the check's
                         OWN flag -- an already-acquired bail, not a foreign gate.

So the class is closed. It produced exactly seven checks that needed protection, and they have it.
Reopen it only if the EMEVD corpus or the MSB tables improve.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
EVT = os.environ.get("ER_EVENT_DIR") or os.path.join(REPO, "elden_ring_artifacts", "event")
SRC = os.path.join(REPO, "greenfield", "msb_gated_treasures.tsv")
OUT = os.path.join(REPO, "greenfield", "treasure_enablers.tsv")

EVENT_RE = re.compile(r"\$Event\((\d+),\s*(\w+),\s*function\(([^)]*)\)\s*\{")
CALL_RE = re.compile(r"\$Initialize(?:Common)?Event\(\s*(-?\d+)\s*,\s*(\d+)\s*([^)]*)\)")
# ENABLE verbs only. The Disable* twins are deliberately NOT resolution sources: an asset that is
# only ever disabled is not thereby enabled, and treating Disable as evidence of an enabler is how a
# scan invents a gate. They are counted in --vocab so their absence is visible, never used to emit.
ENABLE_VERBS = ("EnableAssetTreasure", "ForceCharacterTreasure", "EnableObjAct")
DISABLE_VERBS = ("DisableAssetTreasure", "DisableObjAct")
VERB_RE = re.compile(r"\b(%s)\s*\(\s*([A-Za-z0-9_]+)" % "|".join(ENABLE_VERBS))

# Constructs that carry a condition. Recorded VERBATIM; the sense is never inferred here.
COND_RE = re.compile(r"^\s*(if|EndIf|WaitFor|SkipIf|Goto|GotoIf|\}\s*else)\b.*", re.M)
# The SETTER, never a test: an event that SETS a flag is not gated on it. Used by self_set_flags().
FLAG_SET_RE = re.compile(r"\b(SetEventFlagID|SetNetworkconnectedEventFlagID|BatchSetEventFlags|"
                         r"BatchSetNetworkconnectedEventFlags)\s*\(([^)]*)\)")
COND_TOKENS = ("EventFlag", "AssetDestroyed", "ObjActEventFlag", "CharacterDead", "CharacterHPValue",
               "PlayerIsInOwnWorld", "InArea", "AllPlayersInArea", "EntityInRadiusOfEntity")

# Floors. A join that matches nothing is a FAILURE, not a clean run -- and so is a parse that finds
# no events or no enable sites. Measured 2026-07-25: 589 files / 4893 events / 224 enable sites.
_FLOOR_EVENTS, _FLOOR_SITES = 3000, 100
# CONTROLS, asserted on every emit. KNOWN-TRUE: m60_39_53's literal EnableAssetTreasure. KNOWN-FALSE:
# an id that is not an entity anywhere. An over-broad guard that deletes the true case, or a
# match-everything bug that admits the false one, is caught here and nowhere else.
_CTRL_TRUE, _CTRL_FALSE = "1039533501", "999999999"


def load_src():
    if not os.path.exists(SRC):
        sys.exit("FATAL: %s missing. Run tools/datamine_msb_gated_treasures.py first." % SRC)
    rows = [l for l in open(SRC, encoding="utf-8") if not l.startswith("#")]
    R = list(csv.DictReader(rows, delimiter="\t"))
    if not R or "asset_entity_id" not in R[0]:
        sys.exit("FATAL: %s has no `asset_entity_id` column. That column IS the join key; an older\n"
                 "table carries only the Treasure event's EntityID, which is 0 on 161 of 163 rows\n"
                 "and joins to nothing. Re-emit the source table. Nothing written." % SRC)
    return R


def index_events(files):
    """(file, event id) -> {params, body lines}. Bodies are sliced between consecutive $Event heads."""
    events, byfile = {}, collections.defaultdict(list)
    for f in files:
        fb = os.path.basename(f)
        L = open(f, encoding="utf-8", errors="replace").read().split("\n")
        heads = []
        for i, l in enumerate(L):
            m = EVENT_RE.search(l)
            if m:
                heads.append((i, m.group(1), [p.strip() for p in m.group(3).split(",") if p.strip()]))
        for k, (i, evid, params) in enumerate(heads):
            end = heads[k + 1][0] if k + 1 < len(heads) else len(L)
            rec = {"file": fb, "id": evid, "params": params, "body": L[i:end]}
            events[(fb, evid)] = rec
            byfile[fb].append(rec)
    return events


def index_calls(files):
    """target event id -> [(caller file, [literal-or-name args])]."""
    calls = collections.defaultdict(list)
    n = 0
    for f in files:
        fb = os.path.basename(f)
        t = open(f, encoding="utf-8", errors="replace").read()
        for m in CALL_RE.finditer(t):
            rest = m.group(3).lstrip(",").strip()
            args = [a.strip() for a in rest.split(",") if a.strip() != ""] if rest else []
            calls[m.group(2)].append((fb, args))
            n += 1
    return calls, n


def setter_index(events, calls):
    """flag id -> set of MAP FILES whose events SET it.

    This is the column that answers "is the gate in the same region as the check?" mechanically
    instead of by hand. The enabling event lives in the check's own map almost by construction --
    it is the map's own script -- so "same file as the enabler" proves nothing. Where the GATE FLAG
    is SET is the question, and for the one genuine cross-region case in this table the answer is a
    different map entirely: f580600 sits in the DLC's Scaduview tiles and waits on flag 9146, which
    only m21_01 (Storehouse, First Floor) ever sets, on a DemigodFelled banner.
    """
    idx = collections.defaultdict(set)
    for rec in events.values():
        argmaps = [{}]
        for cf, args in calls.get(rec["id"], []):
            argmaps.append({n: args[i] for i, n in enumerate(rec["params"])
                            if i < len(args) and args[i].lstrip("-").isdigit()})
        for ln in rec["body"]:
            for m in FLAG_SET_RE.finditer(ln):
                for tok in re.findall(r"[A-Za-z0-9_]+", m.group(2)):
                    for am in argmaps:
                        v = _subst(tok, am)
                        if v.isdigit():
                            idx[v].add(rec["file"].split(".")[0])
    return idx


def enable_sites(events):
    """Every ENABLE_VERBS call, with its argument classified literal / param / UNKNOWN."""
    sites, stats = [], collections.Counter()
    for rec in events.values():
        for li, ln in enumerate(rec["body"]):
            for m in VERB_RE.finditer(ln):
                verb, arg = m.group(1), m.group(2)
                if arg.isdigit():
                    kind, pidx = "literal", -1
                elif arg in rec["params"]:
                    kind, pidx = "param", rec["params"].index(arg)
                else:
                    kind, pidx = "UNKNOWN", -1
                stats[(verb, kind)] += 1
                sites.append({"rec": rec, "line": li, "verb": verb, "arg": arg,
                              "kind": kind, "pidx": pidx})
    return sites, stats


def statements(body):
    """Collapse the decompiler's wrapped lines into whole statements: (first line no, text).

    🛑 REQUIRED, not tidiness. DarkScript3 wraps a long condition across lines, and the head line
    then carries no condition token at all:

        WaitFor(
            (PlayerIsInOwnWorld() && ObjActEventFlag(objactEventFlag)) || AssetDestroyed(assetEntityId));

    A line-at-a-time scan sees `WaitFor(`, finds no token, and drops the ONLY line that says what the
    mechanism is -- reporting the carriage pickups as flag-gated when they are "open it or break it
    where it stands", and losing the three-flag WaitFor on m60_39_53 entirely. Under-reporting a gate
    is the safe direction, but it is still wrong, and it silently changed gate_kind on 4 of 18 rows.
    """
    out, i, n = [], 0, len(body)
    while i < n:
        t = body[i].strip()
        start = i
        # A BLOCK HEAD (`$Event(...) {`, `if (...) {`) never balances -- its `(` closes lines later.
        # Only a WRAPPED statement is joined: unbalanced parens AND not a block opener.
        while (t.count("(") > t.count(")")) and not t.endswith("{") and i + 1 < n:
            i += 1
            t = (t + " " + body[i].strip()).strip()
        out.append((start, t))
        i += 1
    return out


def _subst(s, argmap):
    for name, val in argmap.items():
        s = re.sub(r"\b%s\b" % re.escape(name), val, s)
    return s


def gate_of(rec, upto, argmap):
    """Every verbatim condition in the WHOLE event, params substituted where known.

    🛑 A first cut of this read only the lines ABOVE the enable call and got the dominant family
    exactly backwards. Common event 90005560 is the destructible-container pattern:

        if (EventFlag(eventFlagId)) { ReproduceAssetDestruction(..); EnableAssetTreasure(..); EndEvent(); }
        DisableAssetTreasure(assetEntityId);
        WaitFor(AssetDestroyed(assetEntityId));      <- THE ACTUAL MECHANISM, below the enable
        SetNetworkconnectedEventFlagID(eventFlagId, ON);

    Reading upward stops at `if (EventFlag(eventFlagId))` and reports a flag prerequisite for what is
    really "break the pot where it stands". Lines below the call are marked `>` so the reader can see
    which side they came from without the tool deciding what that means.
    """
    out = []
    for i, t in statements(rec["body"]):
        if not COND_RE.match(t) or not any(k in t for k in COND_TOKENS):
            continue
        out.append(("> " if i > upto else "") + _subst(t, argmap))
    return " ;; ".join(out)


def self_set_flags(rec, argmap):
    """Flags this very event SETS. A gate flag that is also self-set is a MEMO ("already done"),
    not a prerequisite -- reporting it as a requirement would invent a gate, and a false gate is an
    unwinnable seed. Measured: this is the entire destructible-container family."""
    out = set()
    for ln in rec["body"]:
        for m in FLAG_SET_RE.finditer(ln):
            for tok in re.findall(r"[A-Za-z0-9_]+", m.group(2)):
                v = _subst(tok, argmap)
                if v.isdigit():
                    out.add(v)
    return out


def kind_of(txt):
    """HINT ONLY, from vocabulary. Never a prerequisite claim -- see the module docstring."""
    if not txt:
        return "no_condition"
    k = []
    if "AssetDestroyed" in txt:
        k.append("in_place_destroy")
    if "AllPlayersInArea" in txt or "EntityInRadiusOfEntity" in txt or "InArea" in txt:
        k.append("in_place_proximity")
    if "ObjActEventFlag" in txt:
        k.append("in_place_objact")
    if "CharacterDead" in txt or "CharacterHPValue" in txt:
        k.append("character_death")
    if "EventFlag" in txt:
        k.append("event_flag")
    return "+".join(k) if k else "REVIEW"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", action="store_true", help="LOOK. Emits nothing.")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if not (a.vocab or a.emit):
        sys.exit("pick --vocab (look first) or --emit")

    files = sorted(glob.glob(os.path.join(EVT, "*.js")))
    if not files:
        sys.exit("FATAL: no *.js under %s. This tool reads DarkScript3-decompiled EMEVD; a packed\n"
                 ".emevd.dcx tree is not readable here. Nothing scanned, nothing written." % EVT)
    events = index_events(files)
    calls, ncall = index_calls(files)
    sites, vstats = enable_sites(events)

    if a.vocab:
        print("files %d | events %d | $Initialize*Event call sites %d" % (len(files), len(events), ncall))
        print("\nENABLE verbs (the ones this tool resolves):")
        for v in ENABLE_VERBS:
            print("   %-24s %d" % (v, sum(n for (vv, _), n in vstats.items() if vv == v)))
        print("   by argument form:")
        for k in sorted(vstats):
            print("      %-24s %-8s %d" % (k[0], k[1], vstats[k]))
        print("\nDISABLE twins (COUNTED so their size is visible; never a resolution source):")
        for v in DISABLE_VERBS:
            print("   %-24s %d" % (v, sum(len(re.findall(r"\b%s\b" % v,
                  open(f, encoding="utf-8", errors="replace").read())) for f in files)))
        unk = [s for s in sites if s["kind"] == "UNKNOWN"]
        print("\nUNKNOWN argument form: %d (tallied, never dropped silently)" % len(unk))
        print("--vocab: nothing written.")
        return 0

    if len(events) < _FLOOR_EVENTS or len(sites) < _FLOOR_SITES:
        sys.exit("FATAL: %d events / %d enable sites, floors %d / %d. A degenerate parse writes a\n"
                 "table that looks fine and means nothing. Nothing written."
                 % (len(events), len(sites), _FLOOR_EVENTS, _FLOOR_SITES))

    # --- resolve every site to concrete entity ids, tallying every reason a site does not resolve
    resolved = collections.defaultdict(list)
    rstats = collections.Counter()
    for s in sites:
        rec = s["rec"]
        if s["kind"] == "literal":
            rstats["literal"] += 1
            resolved[s["arg"]].append({"verb": s["verb"], "via": "literal", "file": rec["file"],
                                       "evid": rec["id"], "callfile": "",
                                       "gate": gate_of(rec, s["line"], {}),
                                       "selfset": sorted(self_set_flags(rec, {}))})
            continue
        if s["kind"] == "UNKNOWN":
            rstats["unknown_arg_form"] += 1
            continue
        cs = calls.get(rec["id"], [])
        if not cs:
            rstats["param_with_no_callsite"] += 1
            continue
        for cf, args in cs:
            if s["pidx"] >= len(args):
                rstats["callsite_too_few_args"] += 1
                continue
            val = args[s["pidx"]]
            if not val.lstrip("-").isdigit():
                rstats["callsite_arg_not_literal"] += 1
                continue
            argmap = {n: args[i] for i, n in enumerate(rec["params"])
                      if i < len(args) and args[i].lstrip("-").isdigit()}
            rstats["resolved_via_callsite"] += 1
            resolved[val].append({"verb": s["verb"], "via": "param", "file": rec["file"],
                                  "evid": rec["id"], "callfile": cf,
                                  "gate": gate_of(rec, s["line"], argmap),
                                  "selfset": sorted(self_set_flags(rec, argmap))})

    if _CTRL_TRUE not in resolved:
        sys.exit("FATAL: KNOWN-TRUE control %s absent. m60_39_53_00 calls EnableAssetTreasure(%s) as\n"
                 "a bare literal; if the index cannot see that, it cannot see anything. Nothing "
                 "written." % (_CTRL_TRUE, _CTRL_TRUE))
    if _CTRL_FALSE in resolved:
        sys.exit("FATAL: KNOWN-FALSE control %s present -- the matcher is admitting non-entities.\n"
                 "Nothing written." % _CTRL_FALSE)

    setters = setter_index(events, calls)
    R = load_src()
    live = [r for r in R if r["is_live_check"] == "1"]
    out, cat = [], collections.Counter()
    for r in live:
        keys = [(k, sp) for k, sp in ((r["asset_entity_id"], "asset"),
                                      (r["entity_id"], "treasure_event"))
                if k and k not in ("0", "-1")]
        hit = next(((k, sp) for k, sp in keys if k in resolved), None)
        if hit:
            k, sp = hit
            e = resolved[k][0]
            verdict = "ENABLER_FOUND"
            # EXTERNAL = a flag the gate tests that this event does not set itself and that is not
            # the check's own acquisition flag. Anything else is a memo or a re-entry guard.
            gf = set(re.findall(r"EventFlag\((\d+)\)", e["gate"]))
            ext = sorted(gf - set(e["selfset"]) - {r["flag"]})
            where = sorted({m for f in ext for m in setters.get(f, ())})
            row = [r["flag"], r["map_id"], r["item_lot_id"], r["in_chest"], r["asset_model"],
                   verdict, k, sp, e["verb"], e["via"], e["evid"], e["file"], e["callfile"],
                   kind_of(e["gate"]), ",".join(e["selfset"]), ",".join(ext),
                   ",".join(where) or ("-" if ext else ""), e["gate"]]
        else:
            verdict = "NO_ENTITY_HANDLE" if not keys else "NO_ENABLER"
            row = [r["flag"], r["map_id"], r["item_lot_id"], r["in_chest"], r["asset_model"],
                   verdict, keys[0][0] if keys else "", keys[0][1] if keys else "",
                   "", "", "", "", "", "", "", "", "", ""]
        cat[verdict] += 1
        out.append(row)

    # ROWS and CHECKS are different numbers and both are printed, always.
    print("source rows %d | live rows %d | DISTINCT live checks %d"
          % (len(R), len(live), len({r["flag"] for r in live})))
    print("resolution stats: %s" % dict(rstats))
    print("DISTINCT entity ids ever treasure/objact-enabled anywhere in the corpus: %d" % len(resolved))
    for v in ("ENABLER_FOUND", "NO_ENABLER", "NO_ENTITY_HANDLE"):
        d = {r[0] for r in out if r[5] == v}
        print("  %-18s %3d rows / %3d DISTINCT checks" % (v, cat[v], len(d)))
    print("  CONTROLS: known-true %s present, known-false %s absent -- both OK" % (_CTRL_TRUE, _CTRL_FALSE))
    if not cat["ENABLER_FOUND"]:
        sys.exit("FATAL: zero enablers matched across %d live rows. An empty join is a FAILURE, not a\n"
                 "clean run -- the corpus has %d enable sites, so zero means the KEY is wrong.\n"
                 "Nothing written." % (len(live), len(sites)))

    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_treasure_enablers.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# What enables each StartDisabled=1 live AP check, joined EMEVD -> entity id.\n")
        fh.write("# 🛑 READ THE TOOL'S DOCSTRING BEFORE USING THIS AS A RISK LIST. StartDisabled=1 is\n")
        fh.write("#   a property of the CONTAINER, not an access gate: 162 of 163 such records are\n")
        fh.write("#   InChest>=1, and only 1 of 3113 loose pickups is StartDisabled (0.03%).\n")
        fh.write("# verdict NO_ENTITY_HANDLE = both entity ids are 0, so NO event can ever address\n")
        fh.write("#   this treasure. It is not 'unexplained gating'; it is proof of no gating.\n")
        fh.write("# gate_kind is a HINT from construct vocabulary. POLARITY IS NOT ENCODED:\n")
        fh.write("#   AssetDestroyed(x) = break it where it stands, NOT a cross-region prerequisite;\n")
        fh.write("#   EndIf(EventFlag(p)) is a bail-out with INVERTED sense. Read gate_verbatim.\n")
        fh.write("# self_set_flags: flags the enabling event SETS ITSELF. A gate flag listed here is\n")
        fh.write("#   a MEMO ('already done'), NOT a prerequisite -- do not build an access rule on\n")
        fh.write("#   it. `> ` in gate_verbatim marks a condition BELOW the enable call.\n")
        fh.write("# external_gate_flags: gate flags that are NOT self-set and NOT this check's own\n")
        fh.write("#   acquisition flag. external_flag_set_in names every map whose script SETS them,\n")
        fh.write("#   which is what decides same-region vs cross-region. `-` = nothing sets it.\n")
        fh.write("# MEASURED THIS RUN: %d live rows / %d distinct checks; %s\n"
                 % (len(live), len({r["flag"] for r in live}),
                    " ".join("%s=%d" % (k, v) for k, v in sorted(cat.items()))))
        fh.write("flag\tmap_id\titem_lot_id\tin_chest\tasset_model\tverdict\tentity_id_used\t"
                 "key_space\tverb\tvia\tenabler_event\tenabler_file\tcall_file\tgate_kind\t"
                 "self_set_flags\texternal_gate_flags\texternal_flag_set_in\tgate_verbatim\n")
        for row in sorted(out):
            fh.write("\t".join(row) + "\n")
    print("\nwrote %s (%d rows)" % (a.out, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
