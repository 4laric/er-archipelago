#!/usr/bin/env python3
"""Validate Fextralife linked-place/map-lot bindings."""
from __future__ import annotations
import csv,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AUDIT=ROOT/"greenfield/evidence/wiki-audit"
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m
def main():
 with (AUDIT/"fextralife-linked-place-check-leads.tsv").open(encoding="utf-8",newline="") as h:rows=list(csv.DictReader(h,delimiter="\t"))
 sources={}
 for fn in ("fextralife-item-pages.tsv","fextralife-acquisition-pages.tsv"):
  with (AUDIT/fn).open(encoding="utf-8",newline="") as h:
   for r in csv.DictReader(h,delimiter="\t"):sources[r["source_id"]]=r
 data=load("_data",ROOT/"greenfield/eldenring/data.py");current={str(ap):(region,flag) for region,entries in data.LOCATIONS.items() for _name,ap,flag in entries};det={}
 with (ROOT/"greenfield/evidence/v060-current/claims.tsv").open(encoding="utf-8",newline="") as h:
  for r in csv.DictReader(h,delimiter="\t"):
   if r["claim_kind"]=="detection" and r["active"]=="true":det[r["subject_id"]]=json.loads(r["value"])
 assert len(rows)>=220 and [r["lead_id"] for r in rows]==sorted(r["lead_id"] for r in rows) and len({r["subject_id"] for r in rows})==len(rows)
 for r in rows:
  v=json.loads(r["normalized_value"]);assert r["source_ids"] in sources and r["disposition"]=="lead_only" and r["claim_kind"]=="identity_region"
  assert current[r["subject_id"]]==(v["region"],v["flag"]);assert det[r["subject_id"]]=={"flag":v["flag"],"mechanism":"ItemLotParam_map.getItemFlagId"}
  assert len(v["source_place_anchor"].split())>=2 and v["source_place_anchor"] in v["ap_description_anchor"] and "does not prove exact coordinates" in r["limitations"]
 print(f"Fextralife linked places: OK -- {len(rows)} exact place/map-lot bindings");return 0
if __name__=="__main__":raise SystemExit(main())
