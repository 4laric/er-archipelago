#!/usr/bin/env python3
"""Regenerate tools/upgrade_costs_data.py from vanilla ER params + elden_ring_artifacts cost tables.

Matt-free, all data-derived:
  * STANDARD_UPGRADE / SOMBER_UPGRADE     <- EquipMtrlSetParam + ReinforceParamWeapon (param-exact)
  * LEVEL_RUNE_COST_TABLE                 <- runes_per_level.txt              (cost to REACH level L)
  * FLASK_BASE_CHARGES / _SEED_COST       <- golden_seed_per_level.txt
  * SCADUTREE_FRAGMENT_COST               <- scadufrags_per_level.txt
  * REVERED_ASH_COST                      <- revered_spirit_ash_per_level.txt

    python tools/gen_upgrade_costs.py       # writes tools/upgrade_costs_data.py
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(HERE)                                  # greenfield/eldenring_gf
REPO = os.path.abspath(os.path.join(GF, "..", ".."))
AR = os.path.join(REPO, "elden_ring_artifacts")
SLP = os.path.join(AR, "vanilla_er", "vanilla_er")
OUT = os.path.join(HERE, "upgrade_costs_data.py")


def _catalog():
    ns = {}
    exec(open(os.path.join(GF, "item_ids.py"), encoding="utf-8").read(), ns)
    return {(v & 0x0FFFFFFF): k for k, v in ns["ITEM_CATALOG"].items() if (v & 0xF0000000) == 0x40000000}


def _weapon_tables():
    id2name = _catalog()
    ms = {}
    for r in csv.DictReader(open(os.path.join(SLP, "EquipMtrlSetParam.csv"), newline="", encoding="utf-8", errors="replace")):
        try: mid = int(r["ID"])
        except (KeyError, ValueError): continue
        mats = []
        for i in range(1, 7):
            m = int(r.get(f"materialId0{i}") or -1); n = int(r.get(f"itemNum0{i}") or 0)
            if m > 0 and n > 0: mats.append((m, n))
        ms[mid] = mats
    rp = {}
    for r in csv.DictReader(open(os.path.join(SLP, "ReinforceParamWeapon.csv"), newline="", encoding="utf-8", errors="replace")):
        try: rp[int(r["ID"])] = int(r["materialSetId"])
        except (KeyError, ValueError): continue
    standard = [(lvl, id2name[ms[rp[lvl]][0][0]], ms[rp[lvl]][0][1]) for lvl in range(1, 26)]
    somber = [(lvl, id2name[ms[2200 + lvl][0][0]], ms[2200 + lvl][0][1]) for lvl in range(1, 11)]
    return standard, somber


def _rune_table():
    reach = {}
    for line in open(os.path.join(AR, "runes_per_level.txt"), encoding="utf-8"):
        p = [c.strip().replace(",", "") for c in line.split("\t")]
        if len(p) < 2 or not p[0].isdigit():
            continue
        try: reach[int(p[0])] = int(p[-1])
        except ValueError: continue
    mx = max(reach)
    return {L: reach[L] - reach.get(L - 1, 0) for L in range(2, mx + 1) if L in reach}


def _flask():
    base, steps = 4, []
    for line in open(os.path.join(AR, "golden_seed_per_level.txt"), encoding="utf-8"):
        m = re.search(r"start with (\d+) Flask", line)
        if m: base = int(m.group(1))
        m = re.search(r"You need (\d+) Seeds? for upgrades increasing to (\d+) total", line)
        if m: steps += [int(m.group(1))] * 2
    return base, steps


def _xN(fname, kind):
    costs, tot = [], []
    for line in open(os.path.join(AR, fname), encoding="utf-8"):
        p = [c.strip() for c in line.split("\t")]
        if not p or not p[0].isdigit() or int(p[0]) == 0:
            continue
        m = re.search(rf"x(\d+)\s*{kind}", line)
        costs.append(int(m.group(1))); tot.append(int(p[-1].replace(",", "")))
    assert [sum(costs[:i + 1]) for i in range(len(costs))] == tot, f"{fname} cumulative mismatch"
    return costs


def main():
    if not os.path.isdir(SLP):
        sys.exit(f"artifacts absent: {SLP}")
    standard, somber = _weapon_tables()
    rune = _rune_table()
    fbase, fseed = _flask()
    scad = _xN("scadufrags_per_level.txt", "Scadutree")
    rev = _xN("revered_spirit_ash_per_level.txt", "Revered")
    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        f.write('"""AUTO-GENERATED (tools/gen_upgrade_costs.py). Data-derived ER upgrade costs.\n')
        f.write('Weapons: EquipMtrlSetParam+ReinforceParamWeapon. Runes/flask/scadutree/revered: the\n')
        f.write('elden_ring_artifacts/*_per_level.txt tables. tools/upgrade_costs.py consumes this."""\n')
        f.write(f"STANDARD_UPGRADE = {standard!r}\n\n")
        f.write(f"SOMBER_UPGRADE = {somber!r}\n\n")
        f.write(f"FLASK_BASE_CHARGES = {fbase!r}\n")
        f.write(f"FLASK_CHARGE_SEED_COST = {fseed!r}\n")
        f.write(f"SCADUTREE_FRAGMENT_COST = {scad!r}\n")
        f.write(f"REVERED_ASH_COST = {rev!r}\n\n")
        f.write("LEVEL_RUNE_COST_TABLE = {\n")
        for L in sorted(rune):
            f.write(f"    {L}: {rune[L]},\n")
        f.write("}\n")
    print(f"wrote {OUT}: standard={len(standard)} somber={len(somber)} rune_levels={len(rune)} "
          f"flask_steps={len(fseed)} scadutree={len(scad)} revered={len(rev)}")


if __name__ == "__main__":
    main()
