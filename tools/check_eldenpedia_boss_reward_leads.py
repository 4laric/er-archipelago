#!/usr/bin/env python3
"""Validate Eldenpedia boss-reward leads against current AP and committed boss joins."""
from __future__ import annotations
import csv, importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    assert spec.loader; spec.loader.exec_module(mod); return mod

def main() -> int:
    with (AUDIT / "eldenpedia-boss-reward-check-leads.tsv").open(encoding="utf-8", newline="") as h:
        rows = list(csv.DictReader(h, delimiter="\t"))
    with (AUDIT / "eldenpedia-combatant-pages.tsv").open(encoding="utf-8", newline="") as h:
        sources = {r["source_id"]: r for r in csv.DictReader(h, delimiter="\t")}
    data = load("_data", ROOT / "greenfield/eldenring/data.py")
    drops = load("_drops", ROOT / "greenfield/eldenring/boss_drops.py").BOSS_DROP_ENTITY
    rewards = load("_rewards", ROOT / "greenfield/eldenring/boss_reward_lots.py").BOSS_REWARD_DEFEAT
    current = {str(ap): (region, flag) for region, entries in data.LOCATIONS.items()
               for _name, ap, flag in entries}
    assert len(rows) >= 20
    assert [r["lead_id"] for r in rows] == sorted(r["lead_id"] for r in rows)
    assert len({r["subject_id"] for r in rows}) == len(rows)
    for row in rows:
        value = json.loads(row["normalized_value"]); flag = value["flag"]
        assert row["source_ids"] in sources
        assert row["disposition"] == "lead_only" and row["claim_kind"] == "identity_region"
        assert current[row["subject_id"]] == (value["region"], flag)
        assert flag in drops or flag in rewards
        assert "does not prove access" in row["limitations"]
        assert sources[row["source_ids"]]["title"] == value["boss"]
    print(f"Eldenpedia boss rewards: OK -- {len(rows)} exact boss/flag bindings")
    return 0

if __name__ == "__main__": raise SystemExit(main())
