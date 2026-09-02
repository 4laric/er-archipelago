#!/usr/bin/env python3
"""Validate the pinned Golden Seed marginal-coverage corpus."""
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
def main() -> int:
    with (AUDIT / "eldenpedia-golden-seed-pages.tsv").open(encoding="utf-8", newline="") as h: pages=list(csv.DictReader(h,delimiter="\t"))
    with (AUDIT / "eldenpedia-golden-seed-check-leads.tsv").open(encoding="utf-8", newline="") as h: leads=list(csv.DictReader(h,delimiter="\t"))
    coverage=json.loads((AUDIT / "eldenpedia-golden-seed-coverage.json").read_text())
    assert len(pages)==1 and len(leads)==28 and pages[0]["revision_sha1"]=="b3afda3a6fffbe96085e7a5be21d87427129fdc1"
    assert coverage["ap_checks"]==43 and coverage["prior_union_checks"]==10 and coverage["union_after"]==38 and coverage["remaining_unbound"]==5
    assert set(coverage["refused_ap_checks"])=={"7772847","7772848","7772897","7772898","7773716"}
    assert len({r["subject_id"] for r in leads})==28 and all(r["disposition"]=="lead_only" for r in leads)
    assert all(json.loads(r["normalized_value"])["item_name"]=="Golden Seed" for r in leads)
    print("Eldenpedia Golden Seed leads: OK -- 28 new exact bindings, union 38/43, 5 explicit refusals"); return 0
if __name__ == "__main__": raise SystemExit(main())
