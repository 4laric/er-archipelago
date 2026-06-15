#!/usr/bin/env python3
"""Tune the grace 'complement' thresholds against check-nearest-grace.csv.

Two knobs:
  FIELD_GOOD : a Tier-2 check is 'well-bossed' if its field boss is within this (world units).
               Beyond it (or a capstone-only check) the boss layer is WEAK -> complement candidate.
  GRACE_CAP  : a check gets a grace trigger only if a grace is within this distance.

complement mode adds a grace trigger ONLY to weak-boss checks. Goal: minimise 'still-poor'
(weak checks with no nearby grace either -> stuck on a far boss / great-rune capstone), without
bloating the added-trigger count (which trivialises exploration).
"""
import csv, statistics as st
BASE="/sessions/hopeful-fervent-wozniak/mnt/er-archipelago"
rows=list(csv.DictReader(open(f"{BASE}/check-nearest-grace.csv",encoding="utf-8")))
def fnum(x): return float(x) if x not in ("",None) else None
for r in rows:
    r["fd"]=fnum(r["field_dist_u"]); r["gd"]=fnum(r["grace_dist_u"])
N=len(rows)
dungeon=[r for r in rows if r["tier"] in ("1mini","1legacy")]
field  =[r for r in rows if r["tier"]=="2field"]
capst  =[r for r in rows if r["tier"]=="4capstone"]
print(f"checks={N}  dungeon(Tier1)={len(dungeon)}  field(Tier2)={len(field)}  capstone(Tier4)={len(capst)}")
print("dungeon checks are always boss-covered; tuning concerns the {} open-world checks.\n".format(len(field)+len(capst)))

print(f"{'FIELD_GOOD':>10} {'GRACE_CAP':>9} | {'weak':>5} {'rescued':>7} {'still_poor':>10} | {'addedTrig':>9} {'fullTrig':>8} {'overlapOK':>9}")
print("-"*78)
for FIELD_GOOD in (150,250,400,99999):
    for GRACE_CAP in (100,140,180,240):
        weak=rescued=0
        for r in field+capst:
            is_weak = (r["tier"]=="4capstone") or (r["fd"] is not None and r["fd"]>FIELD_GOOD) or (r["tier"]=="2field" and r["fd"] is None)
            if is_weak:
                weak+=1
                if r["gd"] is not None and r["gd"]<=GRACE_CAP: rescued+=1
        still_poor=weak-rescued
        # full mode: every open-world check with a grace in cap gets a trigger
        full_trig=sum(1 for r in field+capst if r["gd"] is not None and r["gd"]<=GRACE_CAP)
        # overlap: well-bossed checks that ALSO get a grace in full mode (trivialisation risk avoided by complement)
        well=[r for r in field if not((r["fd"] is not None and r["fd"]>FIELD_GOOD))]
        overlap=sum(1 for r in well if r["gd"] is not None and r["gd"]<=GRACE_CAP)
        print(f"{FIELD_GOOD:>10} {GRACE_CAP:>9} | {weak:>5} {rescued:>7} {still_poor:>10} | {rescued:>9} {full_trig:>8} {overlap:>9}")
    print()

# grace association sanity: distance distribution
gds=sorted(r["gd"] for r in rows if r["gd"] is not None)
print("nearest-grace distance percentiles (all checks):",
      {p:round(gds[int(p/100*len(gds))-1]) for p in (50,75,90,95,99)})
print("field-boss distance percentiles (Tier-2):",
      {p:round(sorted(r['fd'] for r in field if r['fd'] is not None)[int(p/100*len(field))-1]) for p in (50,75,90,95)})
