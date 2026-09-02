"""Machine-check the key-item families that produced grant incidents."""

import csv
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
GF_PKG = HERE.parent
GREENFIELD = GF_PKG.parent
GOODS = 0x40000000


def _table(name):
    path = next((base / name for base in (GF_PKG, GREENFIELD) if (base / name).is_file()), None)
    assert path, f"{name} must ship beside the installed world"
    return path


def _rows():
    with _table("key_item_contracts.tsv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader((line for line in fh if not line.startswith("#")), delimiter="\t"))


def _flags(value):
    return {int(v) for v in value.split(";") if v and v != "-"}


def _awards_by_flag():
    out = {}
    with _table("flag_lots.tsv").open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 6 and parts[0].isdigit() and parts[3] == "1" and parts[5].isdigit():
                out.setdefault(int(parts[0]), set()).add(int(parts[5]))
    return out


def _catalog():
    spec = importlib.util.spec_from_file_location("gf_contract_item_ids", GF_PKG / "item_ids.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ITEM_CATALOG


def test_contract_rows_are_unique_and_well_formed():
    rows = _rows()
    assert rows and len({row["item"] for row in rows}) == len(rows)
    for row in rows:
        assert row["recipe"] in {"goods_only", "goods+safe_flags", "BLOCKED_DUAL_USE_FLAG", "UNVERIFIED"}
        assert row["status"] in {"verified", "blocked", "unverified"}
        assert row["evidence_tier"] in {"in_game", "datamine", "assumed"}
        assert row["evidence"].strip()
        assert int(row["max_num"]) >= 1 and int(row["max_storage"]) >= 0
        if row["evidence_tier"] == "assumed":
            assert row["status"] == "unverified" and row["recipe"] == "UNVERIFIED"


def test_catalog_uses_canonical_rows_not_named_twins():
    catalog = _catalog()
    for row in _rows():
        if row["item"] not in catalog:
            continue
        actual = catalog[row["item"]] - GOODS
        assert actual == int(row["canonical_goods"]), (row["item"], actual, row["canonical_goods"])
        if row["twin_goods"] != "-":
            assert actual not in {int(v) for v in row["twin_goods"].split(";")}


def test_check_flags_award_declared_canonical_goods():
    awards = _awards_by_flag()
    for row in _rows():
        for flag in _flags(row["check_flags"]):
            assert int(row["canonical_goods"]) in awards.get(flag, set()), (row["item"], flag)


def test_safe_reconciliation_never_completes_a_randomized_check():
    for row in _rows():
        checks = _flags(row["check_flags"])
        capabilities = _flags(row["capability_flags"])
        safe = _flags(row["safe_connect_flags"])
        assert safe <= capabilities
        assert safe.isdisjoint(checks), f"{row['item']} would leak {safe & checks}"
        if checks & capabilities:
            assert row["recipe"] == "BLOCKED_DUAL_USE_FLAG"
            assert row["status"] == "blocked" and not safe


def test_initial_incident_families_are_populated():
    names = {row["item"] for row in _rows()}
    expected = {
        "Godrick's Great Rune", "Radahn's Great Rune", "Morgott's Great Rune",
        "Rykard's Great Rune", "Mohg's Great Rune", "Malenia's Great Rune",
        "Great Rune of the Unborn", "Iron Whetblade", "Red-Hot Whetblade",
        "Sanctified Whetblade", "Glintstone Whetblade", "Black Whetblade",
        "Academy Glintstone Key", "Messmer's Kindling",
    }
    assert expected <= names
