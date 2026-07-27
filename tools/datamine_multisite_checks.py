#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_multisite_checks.py -- checks obtainable in MORE THAN ONE REGION. Emits a missable set.

Writes greenfield/multisite_checks.tsv. AP-free; reads only committed tsvs + data.py.

THE HAZARD. A check is filed in exactly one AP region, and the region-lock reachability model
treats it as reachable when THAT region opens. Some event-awarded checks are obtainable in
several places, and WHICH ONE you get it at is decided by the order you happen to do things --
nothing in the data decides it. File such a check in region A, let a seed put a required item on
it, and a player whose route takes them to region B (still locked) is stranded.

Fire Knight Queelign is the clean example (Alaric, from the wiki; msb_flag_region agrees): he is
fightable at the Church of the Crusade OR in Belurat and drops the Crusade Insignia first and the
Prayer Room Key second, wherever those two fights land. So f400694 is filed Belurat and f400696
Scadu Altus, and for half of all players those are the wrong way round.

THE DERIVATION. msb_flag_region's `source=event` rows record every map whose EMEVD awards a flag.
Map -> AP region comes from check_maps.tsv by majority vote of the checks on that map. A check
whose maps span more than one region is a multi-site check.

⭐ WHY THIS IS TRUSTWORTHY: it re-derives 7 flags that were ALREADY hand-tagged missable, one at a
time, by two earlier audits -- Lord of Blood's Favor, Shabriri Grape, Sword of Milos, Freyja's
Greatsword, Falx, Moore's Bell Bearing, Verdigris Greatshield. Finding a hand-audited set by
derivation is the corroboration that makes the NEW members credible; the tool prints the split so
neither the overlap nor a set that has stopped contributing anything can hide.

🛑 IT CAN OVER-TAG, AND THE COST IS ASYMMETRIC. A flag SET by several maps' EMEVD is not proof the
item is obtainable in all of them -- cross-map bookkeeping would look identical here. So this is a
MISSABLE tag, never an access rule: a tagged check stays randomised and obtainable and loses only
the right to host REQUIRED progression. Per the standing call on the Patches chest pair: "tagging
costs a filler slot; assuming wrong costs an unwinnable seed."

Run:  python tools/datamine_multisite_checks.py
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_check_browser import read_tsv, load_module_consts, data_stamp  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    gf = os.path.join(args.repo, "greenfield")
    er = os.path.join(gf, "eldenring")

    LOC = load_module_consts(os.path.join(er, "data.py"), {"LOCATIONS"})["LOCATIONS"]
    flag_region, flag_names = {}, defaultdict(list)
    for region, v in LOC.items():
        for name, _ap, f in v:
            flag_region[f] = region
            flag_names[f].append(name)

    try:
        MISS = load_module_consts(os.path.join(er, "missable_locations.py"),
                                  {"MISSABLE_LOCATIONS"})["MISSABLE_LOCATIONS"]
    except Exception:
        MISS = {}
    ap_of_flag = defaultdict(list)
    for region, v in LOC.items():
        for _n, apid, f in v:
            ap_of_flag[f].append(apid)

    # map -> AP region, by majority of the checks that live on that map.
    votes = defaultdict(Counter)
    for r in read_tsv(os.path.join(gf, "check_maps.tsv")):
        if r.get("flag", "").isdigit() and int(r["flag"]) in flag_region:
            votes[r["map_id"]][flag_region[int(r["flag"])]] += 1
    map_region = {m: c.most_common(1)[0][0] for m, c in votes.items() if c}

    sites = defaultdict(set)
    for r in read_tsv(os.path.join(gf, "msb_flag_region.tsv")):
        if r.get("source") != "event" or not r.get("flag", "").isdigit():
            continue
        f = int(r["flag"])
        if f in flag_region:
            sites[f].add(r["map_id"])

    rows = []
    for f, maps in sites.items():
        if len(maps) < 2:
            continue
        regions = sorted({map_region[m] for m in maps if m in map_region})
        if len(regions) < 2:
            continue
        already = any(a in MISS for a in ap_of_flag[f])
        rows.append({
            "flag": f,
            "filed_region": flag_region[f],
            "obtainable_regions": ",".join(regions),
            "maps": ",".join(sorted(maps)),
            "already_missable": "yes" if already else "no",
            "name": flag_names[f][0],
        })
    rows.sort(key=lambda r: r["flag"])

    corroborated = [r for r in rows if r["already_missable"] == "yes"]
    new = [r for r in rows if r["already_missable"] == "no"]

    out_path = args.out or os.path.join(gf, "multisite_checks.tsv")
    hdr = ["flag", "filed_region", "obtainable_regions", "maps", "already_missable", "name"]
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_multisite_checks.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# Checks obtainable in MORE THAN ONE AP REGION, where which site you get it at\n")
        fh.write("# depends on the ORDER you do things. Filed in one region, the reachability model\n")
        fh.write("# believes that region is enough -- so a required item here can strand a seed.\n")
        fh.write("# -> tag MISSABLE (stays randomised and obtainable; only loses REQUIRED progression).\n")
        fh.write(f"# {len(corroborated)} of these were ALREADY hand-tagged missable by earlier audits,\n")
        fh.write("#   which is what makes the rest credible. 🛑 A flag SET by several maps' EMEVD is\n")
        fh.write("#   not PROOF it is obtainable in all of them -- this can over-tag, and that is the\n")
        fh.write("#   cheap direction to be wrong in.\n")
        fh.write(f"# data.py inputs_hash at emit: {data_stamp(os.path.join(er, 'data.py'))}\n")
        fh.write("\t".join(hdr) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[h]) for h in hdr) + "\n")

    print(f"wrote {out_path}  ({len(rows)} multi-region checks)")
    print(f"  ALREADY missable (corroborates the derivation): {len(corroborated)}")
    for r in corroborated:
        print(f"      f{r['flag']:<12} {r['name'].split(' :: ')[-1][:52]}")
    print(f"  NEW -- would gain a missable tag: {len(new)}")
    for r in new[:12]:
        print(f"      f{r['flag']:<12} filed {r['filed_region']:<14} obtainable {r['obtainable_regions']}")
    if len(new) > 12:
        print(f"      ... and {len(new) - 12} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
