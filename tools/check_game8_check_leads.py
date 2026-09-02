#!/usr/bin/env python3
"""Validate the conservative Game8 legacy-dungeon lead registry."""
import csv, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; AUDIT=ROOT/"greenfield/evidence/wiki-audit"
HEADERS=("lead_id","subject_kind","subject_id","claim_kind","normalized_value","source_ids","independence_families","disposition","game_version","exact_citations","summary","limitations")
def main():
 with (AUDIT/"sources.tsv").open(encoding="utf-8",newline="") as fh: sources={r["source_id"] for r in csv.DictReader(fh,delimiter="\t")}
 with (AUDIT/"game8-check-leads.tsv").open(encoding="utf-8",newline="") as fh:
  reader=csv.DictReader(fh,delimiter="\t"); assert tuple(reader.fieldnames or ())==HEADERS; rows=list(reader)
 spec=importlib.util.spec_from_file_location("_game8_check_data",ROOT/"greenfield/eldenring/data.py"); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
 current={str(ap):(region,name) for region,checks in mod.LOCATIONS.items() for name,ap,_flag in checks}
 ids=[r["lead_id"] for r in rows]; subjects=[r["subject_id"] for r in rows]
 assert ids==sorted(ids) and len(ids)==len(set(ids)); assert len(subjects)==len(set(subjects))
 assert len(rows)>=33,"Game8 coverage unexpectedly collapsed below the 33-check legacy-dungeon corpus"
 for row in rows:
  assert row["subject_kind"]=="check" and row["claim_kind"]=="identity_region"
  assert row["subject_id"] in current and row["source_ids"] in sources
  assert row["independence_families"]=="gameplay-guide:game8"
  assert row["disposition"]=="lead_only" and row["game_version"]=="unknown"
  value=json.loads(row["normalized_value"]); assert value["region"]==current[row["subject_id"]][0]
  assert row["exact_citations"].startswith("game8:") and row["summary"] and row["limitations"]
 print(f"Game8 check leads: OK -- {len(rows)} exact check bindings"); return 0
if __name__=="__main__": raise SystemExit(main())
