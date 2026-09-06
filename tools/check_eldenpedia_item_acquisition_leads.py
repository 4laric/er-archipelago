#!/usr/bin/env python3
"""Validate exact Eldenpedia item-acquisition anchor bindings."""
from __future__ import annotations
import csv, importlib.util, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; AUDIT = ROOT / "greenfield/evidence/wiki-audit"
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def main():
    with (AUDIT/"eldenpedia-item-acquisition-check-leads.tsv").open(encoding="utf-8",newline="") as h: rows=list(csv.DictReader(h,delimiter="\t"))
    with (AUDIT/"eldenpedia-item-acquisition-pages.tsv").open(encoding="utf-8",newline="") as h: sources={r["source_id"]:r for r in csv.DictReader(h,delimiter="\t")}
    data=load("_data",ROOT/"greenfield/eldenring/data.py")
    current={str(ap):(region,flag) for region,entries in data.LOCATIONS.items() for _name,ap,flag in entries}
    detections={}
    with (ROOT/"greenfield/evidence/v060-current/claims.tsv").open(encoding="utf-8",newline="") as h:
        for row in csv.DictReader(h,delimiter="\t"):
            if row["claim_kind"]=="detection" and row["active"]=="true": detections[row["subject_id"]]=json.loads(row["value"])
    assert len(rows)>=164
    assert [r["lead_id"] for r in rows]==sorted(r["lead_id"] for r in rows)
    assert len({r["subject_id"] for r in rows})==len(rows)
    for row in rows:
        value=json.loads(row["normalized_value"]); source=sources[row["source_ids"]]
        assert row["disposition"]=="lead_only" and row["claim_kind"]=="identity_region"
        assert current[row["subject_id"]]==(value["region"],value["flag"])
        assert detections[row["subject_id"]]=={"flag":value["flag"],"mechanism":"ItemLotParam_map.getItemFlagId"}
        assert source["title"]==value["item_name"] and len(value["acquisition_anchor"].split())>=2
        assert "does not prove access" in row["limitations"] and "#Acquisition:" in row["exact_citations"]
    print(f"Eldenpedia item acquisitions: OK -- {len(rows)} exact anchor/map-lot bindings"); return 0
if __name__=="__main__": raise SystemExit(main())
