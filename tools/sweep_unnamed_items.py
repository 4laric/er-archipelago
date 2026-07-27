#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sweep_unnamed_items.py -- for every item id we cannot NAME, record what was SEARCHED.

WHY. `flag_lots.tsv` has rows whose `name` column is empty, and gen_data renders those checks
with the item name literally `check` -- the worst row a tracker can show. Asked "what have we
searched?", the honest answer on 2026-07-27 was NOTHING SYSTEMATIC: the only evidence was a
self-join inside flag_lots ("none of these ids are named on any other row"), which is one table
looking at itself and proves almost nothing. This tool is the record that claim needed.

CONTRIBUTING: "Absence is invisible. Go looking for it." A blank name is an absence, so the
output is a PROVENANCE table -- one row per (item id, corpus) with what was looked for and what
came back -- not a list of failures. `corpora_searched` is emitted even when everything missed,
because "we looked in all of these and found nothing" is a finding and "we never looked" is not.

CORPORA (all AP-free, all from the committed gen_inputs.db bundle -- no artifacts needed):
  EquipParam{Weapon,Goods,Protector,Accessory}.csv   does a param ROW exist for the id?
  {Weapon,Goods,Protector,Accessory,Gem}Name.fmg.xml  base + dlc01 + dlc02: is there a NAME?
  ItemLotParam_map.csv / ItemLotParam_enemy.csv       is the lot real, and what does it grant?
  event/*.emevd.dcx.js        (589 files)             does anything script the lot or flag?
  talk/**/*.esd.py            (365 files)             does dialogue award it?

🛑 NOT SEARCHED HERE, and the report says so per row rather than implying coverage:
  the witchy'd MSBs (mapstudio/, map/). They are deliberately not in the bundle -- too large --
  and stay on the Windows box. `--emit-msb-worklist` writes the exact id/lot list to grep there,
  so the MSB half is a named gap with a work item, not a silence.

The category -> FMG family mapping is DERIVED, not assumed: ids that DO resolve are used to learn
which family each ItemLotParam category draws from, and the learned mapping is printed. A category
we have no evidence for is reported as unknown rather than guessed.

Run:  python tools/sweep_unnamed_items.py [--inputs DIR] [--out greenfield/unnamed_item_sweep.tsv]
      python tools/sweep_unnamed_items.py --emit-msb-worklist msb_worklist.txt
"""
import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_check_browser import load_module_consts, read_tsv, data_stamp  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_RE = re.compile(r"^(?P<r>.*?) :: (?P<rest>.*?) \[f(?P<f>\d+)\]$")
ORD_RE = re.compile(r"\s\((\d+)\)$")
FMG_FAMILIES = ("Weapon", "Goods", "Protector", "Accessory", "Gem")
FMG_DIRS = (("base", "item-msgbnd-dcx", ""),
            ("dlc01", "item_dlc01-msgbnd-dcx", "_dlc01"),
            ("dlc02", "item_dlc02-msgbnd-dcx", "_dlc02"))
PARAM_OF_FAMILY = {"Weapon": "EquipParamWeapon", "Goods": "EquipParamGoods",
                   "Protector": "EquipParamProtector", "Accessory": "EquipParamAccessory"}


def load_fmgs(inputs):
    """family -> {id: name}, merged across base/dlc01/dlc02 (later wins only if base is blank)."""
    out = {}
    for fam in FMG_FAMILIES:
        ids = {}
        for _tag, d, suf in FMG_DIRS:
            p = os.path.join(inputs, "msg", d, f"{fam}Name{suf}.fmg.xml")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                for m in re.finditer(r'<text id="(\d+)">(.*?)</text>', fh.read(), re.S):
                    val = m.group(2)
                    if val and val not in ("%null%", "[ERROR]"):
                        ids.setdefault(int(m.group(1)), val)
        out[fam] = ids
    return out


def load_param_ids(inputs, name):
    p = os.path.join(inputs, "vanilla_er", "vanilla_er", name + ".csv")
    if not os.path.exists(p):
        return None                      # distinguish "absent corpus" from "searched, empty"
    ids = set()
    with open(p, encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(fh)
        for row in rd:
            if row and row[0].strip().lstrip("-").isdigit():
                ids.add(int(row[0]))
    return ids


def grep_corpus(root, needles, exts):
    """needle -> sorted list of files mentioning it. One pass over the corpus, not one per id."""
    hits = defaultdict(set)
    pat = re.compile(r"\b(" + "|".join(re.escape(n) for n in needles) + r")\b") if needles else None
    if pat is None or not os.path.isdir(root):
        return hits
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(exts):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in set(pat.findall(text)):
                hits[m].add(os.path.relpath(fp, root))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--inputs", default=os.path.join(os.path.dirname(REPO), "inputs"),
                    help="extracted gen_inputs.db tree (tools/gen_inputs.py --extract)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--emit-msb-worklist", default=None,
                    help="write the ids/lots that still need a Windows-side MSB grep")
    args = ap.parse_args()
    gf = os.path.join(args.repo, "greenfield")
    er = os.path.join(gf, "eldenring")

    # --- the population: checks rendering with no item name -------------------------
    LOCATIONS = load_module_consts(os.path.join(er, "data.py"), {"LOCATIONS"})["LOCATIONS"]
    unnamed_flags = {}
    for region, v in LOCATIONS.items():
        for name, _ap, flag in v:
            m = NAME_RE.match(name)
            if not m:
                continue
            rest = m.group("rest")
            o = ORD_RE.search(rest)
            if o:
                rest = rest[:o.start()]
            item = rest.split(" - ", 1)[0] if " - " in rest else rest
            if item.strip() == "check":
                unnamed_flags[flag] = region

    lots_by_flag = defaultdict(list)
    named_pairs = []                      # (category, item_id) that DID resolve -> learns the map
    for r in read_tsv(os.path.join(gf, "flag_lots.tsv")):
        try:
            f, cat, iid = int(r["flag"]), r.get("category", ""), r.get("item_id", "")
        except (KeyError, ValueError):
            continue
        lots_by_flag[f].append(r)
        if r.get("name", "").strip() and cat and iid.isdigit():
            named_pairs.append((cat, int(iid), r["name"].strip()))

    fmgs = load_fmgs(args.inputs)

    # --- LEARN category -> FMG family from the rows that already resolve -------------
    votes = defaultdict(Counter)
    for cat, iid, nm in named_pairs:
        for fam, ids in fmgs.items():
            if ids.get(iid) == nm:
                votes[cat][fam] += 1
    learned = {cat: c.most_common(1)[0][0] for cat, c in votes.items() if c}
    print("category -> FMG family, DERIVED from rows that already resolve:")
    for cat in sorted(votes, key=lambda x: (len(x), x)):
        tot = sum(votes[cat].values())
        best, n = votes[cat].most_common(1)[0]
        print(f"  category {cat:>2} -> {best:<10} ({n}/{tot} agree)")
    unknown_cats = sorted({r.get("category", "") for f in unnamed_flags
                           for r in lots_by_flag.get(f, [])} - set(learned))
    if unknown_cats:
        print(f"  🛑 no evidence for categor{'y' if len(unknown_cats)==1 else 'ies'} "
              f"{', '.join(unknown_cats)} -- reported as unknown, NOT guessed")

    # --- the ids we cannot name -----------------------------------------------------
    targets = []                          # (flag, region, row)
    for f, region in sorted(unnamed_flags.items()):
        for r in lots_by_flag.get(f, []):
            if not r.get("name", "").strip():
                targets.append((f, region, r))
    ids = sorted({int(r["item_id"]) for _f, _rg, r in targets if r.get("item_id", "").isdigit()})
    lots = sorted({r["lot"] for _f, _rg, r in targets if r.get("lot")})
    print(f"\n{len(unnamed_flags)} checks render as `check`; "
          f"{len(targets)} unnamed lot rows; {len(ids)} distinct item ids to explain.")

    # --- corpora ---------------------------------------------------------------------
    params = {n: load_param_ids(args.inputs, n) for n in
              ("EquipParamWeapon", "EquipParamGoods", "EquipParamProtector",
               "EquipParamAccessory", "ItemLotParam_map", "ItemLotParam_enemy")}
    needles = [str(i) for i in ids] + [str(l) for l in lots]
    print(f"grepping {len(needles)} needles through event/ and talk/ ...")
    emevd = grep_corpus(os.path.join(args.inputs, "event"), needles, (".js",))
    talk = grep_corpus(os.path.join(args.inputs, "talk"), needles, (".py", ".esd", ".txt"))

    searched = ("EquipParam{Weapon,Goods,Protector,Accessory}|"
                "FMG{Weapon,Goods,Protector,Accessory,Gem}x{base,dlc01,dlc02}|"
                "ItemLotParam_{map,enemy}|event/*.emevd.dcx.js|talk/**")
    out_path = args.out or os.path.join(gf, "unnamed_item_sweep.tsv")
    rows = []
    for flag, region, r in targets:
        iid = int(r["item_id"]) if r.get("item_id", "").isdigit() else None
        cat = r.get("category", "")
        fam = learned.get(cat, "")
        in_params = sorted(n for n, s in params.items()
                           if s is not None and iid is not None and iid in s)
        in_fmg = sorted(f for f, d in fmgs.items() if iid is not None and iid in d)
        # WEAPON REINFORCEMENT. ItemLotParam carries the upgrade level in the last two digits:
        # 2550001..2550010 are ONE weapon (2550000, "Sword of Light") at +1..+10, not ten items.
        # Proven by EMEVD, which calls them PlayerHasItem(ItemType.Weapon, 2550001). A lookup that
        # does not strip this misses every upgraded weapon in the table.
        base = (iid // 100) * 100 if iid is not None else None
        in_fmg_base = sorted(f for f, d in fmgs.items()
                             if base is not None and base != iid and base in d)
        own = fmgs.get(fam, {})
        if iid in own:
            verdict = "NAMABLE: own-category FMG"
        elif base in own:
            verdict = f"NAMABLE: own-category FMG after stripping reinforcement (base {base})"
        elif in_fmg or in_fmg_base:
            verdict = ("WRONG FAMILY: id resolves only in " + ",".join(in_fmg + in_fmg_base)
                       + f" -- the category {cat} -> family map is the open question")
        else:
            verdict = "ABSENT from every param and FMG here -- MSBs are the only stone left"
        rows.append({
            "flag": flag, "region": region, "lot": r.get("lot", ""), "category": cat,
            "item_id": r.get("item_id", ""),
            "expected_fmg_family": fam or "UNKNOWN(category unseen in resolved rows)",
            "verdict": verdict,
            "fmg_hit": ",".join(in_fmg) or "-",
            "fmg_hit_base_id": ",".join(in_fmg_base) or "-",
            "name_if_found": (own.get(iid) or own.get(base)
                              or next((d[iid] for d in fmgs.values() if iid in d),
                                      next((d[base] for d in fmgs.values() if base in d), ""))) or "-",
            "param_row_exists": ",".join(in_params) or "-",
            "emevd_files": ",".join(sorted(emevd.get(str(iid), []))[:3]) or "-",
            "lot_in_emevd": ",".join(sorted(emevd.get(r.get("lot", ""), []))[:3]) or "-",
            "talk_files": ",".join(sorted(talk.get(str(iid), []))[:3]) or "-",
            "corpora_searched": searched,
            "msb_searched": "NO -- witchy MSBs are not in gen_inputs.db; see --emit-msb-worklist",
        })

    hdr = list(rows[0].keys()) if rows else []
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/sweep_unnamed_items.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# One row per UNNAMED item-lot row, recording every corpus that was searched\n")
        fh.write("# for it. A '-' means SEARCHED AND ABSENT, not 'not looked at'.\n")
        fh.write("# 🛑 msb_searched is NO for every row: the witchy'd MSBs stay on the Windows\n")
        fh.write("#    box. That half is a NAMED GAP, not a silence.\n")
        fh.write("# data.py inputs_hash at sweep time: %s\n" % data_stamp(os.path.join(er, "data.py")))
        fh.write("# Re-run: python tools/gen_inputs.py --extract && python tools/sweep_unnamed_items.py\n")
        fh.write("\t".join(hdr) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[h]) for h in hdr) + "\n")

    # --- what the sweep concluded ----------------------------------------------------
    from collections import Counter as _C
    verdicts = _C(r["verdict"].split(":")[0].split(" --")[0] for r in rows)
    no_param = [r for r in rows if r["param_row_exists"] == "-"]
    no_fmg = [r for r in rows if r["fmg_hit"] == "-"]
    nowhere = [r for r in rows if r["param_row_exists"] == "-" and r["fmg_hit"] == "-"
               and r["emevd_files"] == "-" and r["talk_files"] == "-"
               and r["lot_in_emevd"] == "-"]
    print(f"\nwrote {out_path}  ({len(rows)} rows)")
    print("  verdicts:")
    for k, n in verdicts.most_common():
        print(f"      {n:5d}  {k}")
    print(f"  no EquipParam row at all      : {len(no_param)}")
    print(f"  no FMG name in any family     : {len(no_fmg)}")
    print(f"  absent from EVERY corpus here : {len(nowhere)}  <- MSBs are the only stone left")
    by_cat = Counter(r["category"] for r in rows)
    print(f"  by ItemLotParam category      : {dict(sorted(by_cat.items()))}")

    if args.emit_msb_worklist:
        with open(args.emit_msb_worklist, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Grep these through the witchy'd MSBs on the Windows box:\n")
            fh.write("#   Select-String -Path <msb-xml-dir>\\*.xml -Pattern (Get-Content this-file)\n")
            for r in sorted({x["item_id"] for x in nowhere} | {x["lot"] for x in nowhere}):
                if r:
                    fh.write(r + "\n")
        print(f"  wrote MSB worklist -> {args.emit_msb_worklist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
