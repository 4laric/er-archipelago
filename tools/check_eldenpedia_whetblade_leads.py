#!/usr/bin/env python3
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];A=ROOT/"greenfield"/"evidence"/"wiki-audit"
def main():
 with (A/"eldenpedia-whetblade-pages.tsv").open() as h:p=list(csv.DictReader(h,delimiter="\t"))
 with (A/"eldenpedia-whetblade-check-leads.tsv").open() as h:l=list(csv.DictReader(h,delimiter="\t"))
 c=json.loads((A/"eldenpedia-whetblade-coverage.json").read_text());assert len(p)==6 and len(l)==7
 assert c=={"ap_checks":7,"explicit_refusals":0,"new_union_checks":1,"prior_union_checks":6,"source_bindings":7,"union_after":7}
 assert len({r["subject_id"] for r in l})==7 and all(r["disposition"]=="lead_only" for r in l)
 assert sum(json.loads(r["normalized_value"])["item_name"]=="Whetstone Knife" for r in l)==2
 print("Eldenpedia whetblade leads: OK -- 7/7 source bindings, union 6/7 -> 7/7");return 0
if __name__=="__main__":raise SystemExit(main())
