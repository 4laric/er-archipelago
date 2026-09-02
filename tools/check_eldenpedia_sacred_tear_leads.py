#!/usr/bin/env python3
"""Validate the immutable Eldenpedia Sacred Tear acquisition corpus."""
import csv, importlib.util, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
EXPECTED = {"7772958": 1046387100, "7772917": 1044337100, "7772786": 1041337200,
            "7772881": 1043357100, "7772710": 1039397000, "7772585": 1036497000,
            "7772627": 1037497100, "7773077": 1050387020, "7772744": 1039527400,
            "7772767": 1040517400, "7773134": 1051537800, "7773205": 1054557800}

def main() -> int:
    with (AUDIT / "eldenpedia-sacred-tear-pages.tsv").open(encoding="utf-8", newline="") as h:
        pages = list(csv.DictReader(h, delimiter="\t"))
    with (AUDIT / "eldenpedia-sacred-tear-check-leads.tsv").open(encoding="utf-8", newline="") as h:
        leads = list(csv.DictReader(h, delimiter="\t"))
    assert len(pages) == 1 and len(leads) == 12
    page = pages[0]; assert page["source_id"] == "wiki:eldenpedia:page-13254:revision-99877"
    assert page["revision_sha1"] == "c7a13f72bb1579728cba9811dfbdddf1a97de308"
    assert page["acquisition_rows"] == "12" and page["disposition"] == "lead_only"
    spec = importlib.util.spec_from_file_location("_sacred_tear_check_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
    current = {str(ap_id): (region, name, flag) for region, checks in module.LOCATIONS.items() for name, ap_id, flag in checks}
    assert {r["subject_id"] for r in leads} == set(EXPECTED)
    assert [r["lead_id"] for r in leads] == sorted(r["lead_id"] for r in leads)
    for row in leads:
        subject = row["subject_id"]; value = json.loads(row["normalized_value"])
        assert current[subject][2] == EXPECTED[subject] == value["flag"]
        assert ":: Sacred Tear -" in current[subject][1] and value["item_name"] == "Sacred Tear"
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        assert re.fullmatch(r"eldenpedia:pageid-13254:revision-99877:#Acquisition:(?:[1-9]|1[0-2])", row["exact_citations"])
        assert "Ruin-Strewn Precipice" in row["limitations"]
    assert len({r["exact_citations"] for r in leads}) == 12
    print("Eldenpedia Sacred Tear leads: OK -- 1 immutable revision, 12 exact check bindings, 1 AP-only row refused")
    return 0

if __name__ == "__main__": raise SystemExit(main())
