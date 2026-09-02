#!/usr/bin/env python3
"""Validate exact Fextralife acquisition-anchor bindings."""
from __future__ import annotations
import csv, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AUDIT=ROOT/"greenfield/evidence/wiki-audit"
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m
def main():
 with (AUDIT/"fextralife-acquisition-check-leads.tsv").open(encoding="utf-8",newline="") as h:rows=list(csv.DictReader(h,delimiter="\t"))
 sources={}
 for name in ("fextralife-acquisition-pages.tsv","fextralife-item-pages.tsv"):
  with (AUDIT/name).open(encoding="utf-8",newline="") as h:
   for r in csv.DictReader(h,delimiter="\t"):sources[r["source_id"]]=r
 data=load("_data",ROOT/"greenfield/eldenring/data.py");current={str(ap):(region,flag) for region,entries in data.LOCATIONS.items() for _name,ap,flag in entries};detections={}
 with (ROOT/"greenfield/evidence/v060-current/claims.tsv").open(encoding="utf-8",newline="") as h:
  for r in csv.DictReader(h,delimiter="\t"):
   if r["claim_kind"]=="detection" and r["active"]=="true":detections[r["subject_id"]]=json.loads(r["value"])
 assert len(rows)>=240 and [r["lead_id"] for r in rows]==sorted(r["lead_id"] for r in rows) and len({r["subject_id"] for r in rows})==len(rows)
 for r in rows:
  v=json.loads(r["normalized_value"]);s=sources[r["source_ids"]]
  assert r["disposition"]=="lead_only" and r["claim_kind"]=="identity_region" and r["independence_families"]=="gameplay-wiki:fextralife"
  assert current[r["subject_id"]]==(v["region"],v["flag"]);assert detections[r["subject_id"]]=={"flag":v["flag"],"mechanism":"ItemLotParam_map.getItemFlagId"}
  assert s["title"]==v["item_name"] and len(v["acquisition_anchor"].split())>=2 and "does not prove access" in r["limitations"]
 print(f"Fextralife acquisitions: OK -- {len(rows)} exact anchor/map-lot bindings");return 0
if __name__=="__main__":raise SystemExit(main())
