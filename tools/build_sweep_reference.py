#!/usr/bin/env python3
"""Build the offline player sweep reference from the authoritative generated tables.

This is potential coverage, before seed region, rung and progression-surface cuts.
Known non-firing triggers are excluded using the same contract as boss_locks.rung_sweeps.
Run: python tools/build_sweep_reference.py [--repo ROOT] [--out PATH]
"""
import argparse
import ast
from collections import Counter
import csv
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "greenfield"))
import gen_manifest
from desc_sources import split_sweep_clause

OUTPUT = "er-archipelago-sweep-reference.html"


def constants(path):
    """Generated data only; no imports of the AP world or execution of table code."""
    result = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        result[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return result


def tsv(path):
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader((line for line in stream if not line.startswith("#")),
                                   delimiter="\t"))


def build_payload(repo):
    manifest = gen_manifest.compute_builder_manifest(str(repo), "sweep_reference")
    if manifest["missing"]:
        raise ValueError("Missing sweep reference inputs: " + ", ".join(manifest["missing"]))
    tables = repo / "greenfield/eldenring/tables"
    sweep = constants(tables / "boss_sweeps.py")
    healthbars = constants(tables / "boss_healthbars.py")["BOSS_HEALTHBARS"]
    locations = constants(tables / "data.py")["LOCATIONS"]
    contract = runpy.run_path(str(repo / "greenfield/eldenring/contract.py"))
    skips = contract["runtime_sweep_skips"]()
    map_names = {row["tile"]: row["name"] for row in tsv(repo / "greenfield" / "map_names.tsv")}
    nearest = {int(row["flag"]): row for row in tsv(repo / "greenfield" / "nearest_grace.tsv")}
    checks = {}
    for region, rows in locations.items():
        for name, ap_id, flag in rows:
            if ap_id in checks:
                raise ValueError(f"Duplicate check AP ID {ap_id}")
            checks[ap_id] = {"id": ap_id, "flag": flag, "region": region,
                             "name": split_sweep_clause(name)[0],
                             "grace": nearest.get(flag, {}).get("grace_name", "")}
    groups = []
    used = set()
    for flag, members in sorted(sweep["DUNGEON_SWEEPS"].items()):
        if flag in skips:
            continue
        if not members:
            raise ValueError(f"Empty sweep {flag}")
        missing = set(members) - checks.keys()
        if missing:
            raise ValueError(f"Sweep {flag} refers to missing checks: {sorted(missing)}")
        info = healthbars.get(flag)
        map_id, tile, kind, boss = info if info else ("", "", "unknown", "")
        region = sweep["SWEEP_REGION"][flag]
        arena_region = sweep["SWEEP_ARENA_REGION"].get(flag)
        candidate = sorted(set(members))
        used.update(candidate)
        landmarks = Counter(checks[ap]["grace"] for ap in candidate if checks[ap]["grace"])
        groups.append({"flag": flag, "boss": boss or "Unnamed sweep",
                       "region": arena_region or region, "member_region": region,
                       "arena_audited": arena_region is not None, "kind": kind,
                       "arena": map_names.get(tile) or map_names.get(map_id) or tile or map_id,
                       "map": tile or map_id,
                       "rungs": [key for key, kinds in contract["SWEEP_RUNGS"].items()
                                 if kind in kinds or (info is None and key == "bosses")],
                       "landmarks": [name for name, _ in sorted(landmarks.items(),
                                      key=lambda pair: (-pair[1], pair[0]))[:4]],
                       "checks": candidate})
    if not groups:
        raise ValueError("The sweep reference has no live sweep groups")
    groups.sort(key=lambda group: (group["region"], group["boss"], group["flag"]))
    return {"groups": groups, "checks": {str(ap): checks[ap] for ap in sorted(used)},
            "meta": {"inputs_hash": manifest["inputs_hash"], "skipped": len(
                     set(skips) & sweep["DUNGEON_SWEEPS"].keys())}}


def render(repo, payload):
    template = (repo / "tools/sweep_reference_template.html").read_text(encoding="utf-8")
    # A check name containing </script> must remain data, not executable markup.
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return template.replace("__SWEEP_PAYLOAD__", encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    payload = build_payload(repo)
    output = args.out or repo / OUTPUT
    output.write_text(render(repo, payload), encoding="utf-8", newline="\n")
    print(f"Sweep reference: {len(payload['groups'])} bosses, {len(payload['checks'])} candidate "
          f"checks; {payload['meta']['skipped']} non-firing triggers excluded -> {output}")


if __name__ == "__main__":
    main()
