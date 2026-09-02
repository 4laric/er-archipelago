#!/usr/bin/env python3
import csv,json
from pathlib import Path
A=Path(__file__).resolve().parents[1]/"greenfield"/"evidence"/"wiki-audit"
def main():
 with (A/"eldenpedia-memory-stone-pages.tsv").open() as h:p=list(csv.DictReader(h,delimiter="\t"))
 with (A/"eldenpedia-memory-stone-check-leads.tsv").open() as h:l=list(csv.DictReader(h,delimiter="\t"))
 c=json.loads((A/"eldenpedia-memory-stone-coverage.json").read_text());assert len(p)==1 and len(l)==2 and p[0]["revision_sha1"]=="4f64ec6ea32191ef7a2cd67d727d0b8665d4e3ef"
 assert c=={"ap_checks":9,"explicit_refusals":0,"new_union_checks":2,"prior_union_checks":7,"source_bindings":2,"union_after":9};assert {r["subject_id"] for r in l}=={"7770020","7770021"};assert all(r["disposition"]=="lead_only" for r in l)
 print("Eldenpedia Memory Stone leads: OK -- union 7/9 -> 9/9, no refusals");return 0
if __name__=="__main__":raise SystemExit(main())
