#!/usr/bin/env python3
"""Emit the v0.6 phase-1 identity/region census from the current generated corpus.

This is an adapter, not a new source of truth. It snapshots data.LOCATIONS and preserves
the lineage of an applicable region_overrides.tsv ruling. The generated location and its
override evidence deliberately share one family: data.py consumes that table, so their
agreement is not independent corroboration.

The record dictionaries intentionally use the field names in
SPEC-check-evidence-ledger-v060.md. Until #1210 lands, the four checked-in files are the
adapter's local interchange fixture. No runtime module consumes them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

import evidence_ledger

REVIEW_DATE = "2026-08-31"
GAME_VERSION = "1.17"
RADAHN_ACCESS_AP_IDS = (7770002, 7770665)
RADAHN_FESTIVAL_FLAG = 9410
FINGERSLAYER_ACCESS_AP_ID = 7771152
FINGERSLAYER_CHEST_GATE_FLAG = 1034509410
CARIAN_STATUE_ACCESS_FLAGS = frozenset({
    34117100, 34117110, 34117120, 34117400, 34117401,
    34117402, 34117403, 34117500, 34117710,
})
CARIAN_STATUE_ACCESS_AP_IDS = frozenset({
    7772312, 7772313, 7772314, 7772316, 7772317,
    7772318, 7772319, 7772320, 7772322, 7900218,
})
FINGER_RUINS_BELL_ACCESS = {
    7773581: (2050407000, "Jagged Peak"),
    7773656: (2053467600, "Scadu Altus"),
}


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _load_generated_locations(data_path: Path) -> tuple[list[dict], dict]:
    spec = importlib.util.spec_from_file_location("_v060_current_data", data_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated locations from {data_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stamp = dict(module._GEN_STAMP)
    rows = []
    for region, locations in module.LOCATIONS.items():
        for name, ap_id, flag in locations:
            rows.append({
                "ap_id": int(ap_id), "flag": int(flag), "name": str(name), "region": str(region),
            })
    rows.sort(key=lambda row: row["ap_id"])
    ap_ids = [row["ap_id"] for row in rows]
    if not rows:
        raise RuntimeError("generated location corpus is empty")
    if len(ap_ids) != len(set(ap_ids)):
        duplicates = sorted(ap for ap, count in Counter(ap_ids).items() if count > 1)
        raise RuntimeError(f"duplicate AP location ids in generated corpus: {duplicates[:10]}")
    return rows, stamp


def _load_flag_region_overrides(path: Path) -> tuple[dict[int, dict], int]:
    """Return flag-scoped rulings and the number of non-flag rows deliberately out of scope."""
    overrides: dict[int, dict] = {}
    non_flag = 0
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(
            (line for line in handle if line.strip() and not line.startswith("#")), delimiter="\t")
        for line_number, row in enumerate(rows, start=2):
            if row["key_kind"] != "flag":
                non_flag += 1
                continue
            flag = int(row["key"])
            if flag in overrides:
                raise RuntimeError(f"duplicate active flag ruling for {flag} in {path}")
            overrides[flag] = {
                "region": row["region"], "reason": row["reason"], "line": line_number,
            }
    return overrides, non_flag


def _load_map_lot_detection(path: Path) -> dict[int, list[dict]]:
    """Load exact ItemLotParam_map citations, grouped by their acquisition event flag."""
    by_flag: dict[int, list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        for line_number, row in enumerate(rows, start=2):
            if row["table"] != "map":
                continue
            flag = int(row["flag"])
            lot = int(row["lot"])
            existing_lots = {entry["lot"] for entry in by_flag.setdefault(flag, [])}
            if lot not in existing_lots:
                by_flag[flag].append({"lot": lot, "line": line_number})
    for rows in by_flag.values():
        rows.sort(key=lambda row: (row["lot"], row["line"]))
    return by_flag


def _load_stormhill_access(path: Path) -> list[dict[str, object]]:
    """Load the exact f400191 WaitFor sites without treating their join as detection evidence."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "400191" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_map": row["gate_map"], "gate_test_map": row["gate_test_map"],
            })
    matches.sort(key=lambda row: int(row["gate_flag"]))
    if [row["gate_flag"] for row in matches] != [3708, 3709, 1041389414]:
        raise RuntimeError(f"f400191 WaitFor corpus changed: {matches!r}")
    if {row["event_id"] for row in matches} != {90005750}:
        raise RuntimeError(f"f400191 WaitFor event changed: {matches!r}")
    return matches


def _load_perfect_order_access(path: Path) -> dict[str, object]:
    """Load the one exact f9500 WaitFor site; its param join is not a detection witness."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "9500" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_map": row["gate_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 11059206:
        raise RuntimeError(f"f9500 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f9500 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_death_prince_access(path: Path) -> dict[str, object]:
    """Load only f9502's immediate WaitFor; the broader Fia cone remains unknown."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "9502" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_test_map": row["gate_test_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 4131:
        raise RuntimeError(f"f9502 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f9502 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_varres_bouquet_access(path: Path) -> dict[str, object]:
    """Load only f400037's immediate WaitFor; the broader Varre quest remains out of scope."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "400037" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_test_map": row["gate_test_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 12059166:
        raise RuntimeError(f"f400037 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f400037 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_taunters_tongue_access(path: Path) -> dict[str, object]:
    """Load f60300's immediate WaitFor without assigning meaning to its unlabeled gate flag."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "60300" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 11102180:
        raise RuntimeError(f"f60300 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005792:
        raise RuntimeError(f"f60300 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_purifying_tear_access(path: Path) -> dict[str, object]:
    """Load f65270's immediate WaitFor without assigning meaning to its unlabeled gate flag."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "65270" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 1039522181:
        raise RuntimeError(f"f65270 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005792:
        raise RuntimeError(f"f65270 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_ijis_bell_bearing_access(path: Path) -> dict[str, object]:
    """Load f400240's immediate WaitFor without expanding it into Iji's quest state."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "400240" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_test_map": row["gate_test_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 3768:
        raise RuntimeError(f"f400240 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f400240 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_frenzied_flame_seal_access(path: Path) -> dict[str, object]:
    """Load f400089's immediate WaitFor without expanding it into Hyetta's quest."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "400089" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_test_map": row["gate_test_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 35009211:
        raise RuntimeError(f"f400089 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f400089 WaitFor event changed: {matches!r}")
    return matches[0]


def _load_witch_crown_access(path: Path) -> dict[str, object]:
    """Load f400107's immediate WaitFor without assigning the NPC state to Sellen."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "400107" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_test_map": row["gate_test_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 3469:
        raise RuntimeError(f"f400107 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f400107 WaitFor event changed: {matches!r}")
    return matches[0]


def _source_records(
        repo: Path, data_path: Path, override_path: Path, lot_path: Path,
        stamp: Mapping[str, str]):
    body_hash = str(stamp["body_sha256"])
    family_id = f"project:current-locations:{body_hash.removeprefix('sha256:')}"
    generated_id = f"project:data.py:{body_hash.removeprefix('sha256:')}"
    override_hash = _sha256(override_path)
    override_id = f"project:region-overrides:{override_hash.removeprefix('sha256:')}"
    lot_hash = _sha256(lot_path)
    lot_id = f"game:param:ItemLotParam_map:{lot_hash.removeprefix('sha256:')}"
    data_display = data_path.relative_to(repo).as_posix()
    override_display = override_path.relative_to(repo).as_posix()
    lot_display = lot_path.relative_to(repo).as_posix()
    sources = [
        {
            "source_id": generated_id, "source_kind": "project_derivation",
            "family_id": family_id, "title": "Current generated Elden Ring locations",
            "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE, "revision": body_hash,
            "url_or_path": data_display, "license": "project-derived",
            "environment_id": "", "supersedes": "",
        },
        {
            "source_id": lot_id, "source_kind": "game_data",
            "family_id": "game:param:ItemLotParam_map",
            "title": "ItemLotParam_map acquisition flags",
            "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
            "revision": lot_hash, "url_or_path": lot_display,
            "license": "private-evidence", "environment_id": "", "supersedes": "",
        },
        {
            "source_id": override_id, "source_kind": "ruling",
            # Same family on purpose: data.py consumes this table.
            "family_id": family_id, "title": "Current project region rulings",
            "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
            "revision": override_hash,
            "url_or_path": override_display, "license": "project-derived",
            "environment_id": "", "supersedes": "",
        },
    ]
    sources.sort(key=lambda row: row["source_id"])
    return sources, {
        "family_id": family_id, "generated_id": generated_id, "override_id": override_id,
        "lot_id": lot_id, "body_hash": body_hash, "override_hash": override_hash,
        "lot_hash": lot_hash,
    }


def build_records(repo: Path) -> dict:
    data_path = repo / "greenfield" / "eldenring" / "data.py"
    override_path = repo / "greenfield" / "region_overrides.tsv"
    lot_path = repo / "greenfield" / "flag_lots.tsv"
    lot_gates_path = repo / "greenfield" / "lot_gates.tsv"
    locations, stamp = _load_generated_locations(data_path)
    overrides, non_flag_overrides = _load_flag_region_overrides(override_path)
    map_lots = _load_map_lot_detection(lot_path)
    stormhill_access = _load_stormhill_access(lot_gates_path)
    perfect_order_access = _load_perfect_order_access(lot_gates_path)
    death_prince_access = _load_death_prince_access(lot_gates_path)
    varres_bouquet_access = _load_varres_bouquet_access(lot_gates_path)
    taunters_tongue_access = _load_taunters_tongue_access(lot_gates_path)
    purifying_tear_access = _load_purifying_tear_access(lot_gates_path)
    ijis_bell_bearing_access = _load_ijis_bell_bearing_access(lot_gates_path)
    frenzied_flame_seal_access = _load_frenzied_flame_seal_access(lot_gates_path)
    witch_crown_access = _load_witch_crown_access(lot_gates_path)
    sources, source = _source_records(repo, data_path, override_path, lot_path, stamp)
    start_grace_path = repo / "greenfield" / "eldenring" / "features" / "start_grace.py"
    start_grace_hash = _sha256(start_grace_path)
    radahn_source_id = (
        f"project:radahn-start-flag:{start_grace_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": radahn_source_id, "source_kind": "ruling",
        "family_id": "project:radahn-access-ruling",
        "title": "Archipelago Radahn Festival start-flag bypass",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": start_grace_hash,
        "url_or_path": "greenfield/eldenring/features/start_grace.py",
        "license": "project-derived", "environment_id": "", "supersedes": "",
    })
    fingerslayer_source_id = (
        f"project:fingerslayer-start-flag:{start_grace_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": fingerslayer_source_id, "source_kind": "ruling",
        "family_id": "project:fingerslayer-access-ruling",
        "title": "Archipelago Fingerslayer Blade chest-gate bypass",
        "game_version": GAME_VERSION, "retrieved_at": "2026-09-01",
        "revision": start_grace_hash,
        "url_or_path": "greenfield/eldenring/features/start_grace.py",
        "license": "project-derived", "environment_id": "", "supersedes": "",
    })
    legacy_gate_path = repo / "greenfield" / "eldenring" / "features" / "legacy_key_gates.py"
    legacy_gate_hash = _sha256(legacy_gate_path)
    carian_statue_source_id = (
        f"project:carian-statue-gate:{legacy_gate_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": carian_statue_source_id, "source_kind": "ruling",
        "family_id": "project:carian-statue-access-rule",
        "title": "Archipelago Carian Inverted Statue access rule",
        "game_version": GAME_VERSION, "retrieved_at": "2026-09-01",
        "revision": legacy_gate_hash,
        "url_or_path": "greenfield/eldenring/features/legacy_key_gates.py",
        "license": "project-derived", "environment_id": "", "supersedes": "",
    })
    finger_ruins_source_id = (
        f"project:hole-laden-necklace-gate:{legacy_gate_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": finger_ruins_source_id, "source_kind": "ruling",
        "family_id": "project:hole-laden-necklace-access-rule",
        "title": "Archipelago Hole-Laden Necklace bell access rule",
        "game_version": GAME_VERSION, "retrieved_at": "2026-09-01",
        "revision": legacy_gate_hash,
        "url_or_path": "greenfield/eldenring/features/legacy_key_gates.py",
        "license": "project-derived", "environment_id": "", "supersedes": "",
    })
    lot_gates_hash = _sha256(lot_gates_path)
    lot_gates_source_id = (
        f"game:emevd-lot-gates:m60_41_38_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": lot_gates_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m60_41_38_00:90005750",
        "title": "Stormhill Shack f400191 WaitFor call sites",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    ijis_bell_bearing_source_id = (
        f"game:emevd-lot-gates:m60_34_49_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": ijis_bell_bearing_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m60_34_49_00:90005750",
        "title": "Iji's Bell Bearing f400240 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    frenzied_flame_seal_source_id = (
        f"game:emevd-lot-gates:m35_00_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": frenzied_flame_seal_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m35_00_00_00:90005750",
        "title": "Frenzied Flame Seal f400089 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    witch_crown_source_id = (
        f"game:emevd-lot-gates:m14_00_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": witch_crown_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m14_00_00_00:90005750",
        "title": "Witch's Glintstone Crown f400107 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    varres_bouquet_source_id = (
        f"game:emevd-lot-gates:m12_05_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": varres_bouquet_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m12_05_00_00:90005750",
        "title": "Varre's Bouquet f400037 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    taunters_tongue_source_id = (
        f"game:emevd-lot-gates:m11_10_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": taunters_tongue_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m11_10_00_00:90005792",
        "title": "Taunter's Tongue f60300 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    purifying_tear_source_id = (
        f"game:emevd-lot-gates:m60_39_52_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": purifying_tear_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m60_39_52_00:90005792",
        "title": "Purifying Crystal Tear f65270 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    death_prince_source_id = (
        f"game:emevd-lot-gates:m12_03_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": death_prince_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m12_03_00_00:90005750",
        "title": "Mending Rune of the Death-Prince f9502 immediate WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    perfect_order_source_id = (
        f"game:emevd-lot-gates:m11_05_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": perfect_order_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m11_05_00_00:90005750",
        "title": "Mending Rune of Perfect Order f9500 WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    sources.sort(key=lambda row: row["source_id"])
    environments: list[dict] = []
    evidence: list[dict] = []
    claims: list[dict] = []
    matched_override_flags: set[int] = set()
    matched_map_lot_flags: set[int] = set()

    for location in locations:
        ap_id, flag = location["ap_id"], location["flag"]
        identity_claim_id = f"check:{ap_id}/identity"
        region_claim_id = f"check:{ap_id}/region"
        # data.LOCATIONS exposes the AP id and event flag, but not a normalized lot/shop id.
        # Preserve that legacy key without pretending a second derived table is independent.
        identity_value = {"ap_id": ap_id, "flag": flag, "namespace": "flag", "id": flag}
        identity_evidence_id = (
            f"project:data.py:{source['body_hash'].removeprefix('sha256:')}:"
            f"check-{ap_id}:identity")
        evidence.append({
            "evidence_id": identity_evidence_id, "claim_id": identity_claim_id,
            "source_id": source["generated_id"],
            "stance": "supports", "value": _json(identity_value),
            "citation": f"greenfield/eldenring/data.py:LOCATIONS ap_id={ap_id} flag={flag}",
            "method": "tools/build_v060_current_evidence.py:current_locations",
            "independence_notes":
                "Generated location snapshot; downstream views of data.py are this same family.",
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes":
                "Legacy current-corpus key: data.py exposes an event flag, not a vanilla lot/shop id.",
        })
        claims.append({
            "claim_id": identity_claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "identity", "game_version": GAME_VERSION,
            "value": _json(identity_value),
            "status": "single_source", "risk": "medium",
            "adjudication": "automatic", "evidence_ids": identity_evidence_id,
            "last_reviewed": REVIEW_DATE, "review_issue": "#1211", "active": "true",
            "supersedes": "",
        })

        lot_rows = map_lots.get(flag, [])
        if lot_rows:
            matched_map_lot_flags.add(flag)
            detection_claim_id = f"check:{ap_id}/detection"
            detection_value = {"mechanism": "ItemLotParam_map.getItemFlagId", "flag": flag}
            detection_evidence_ids = []
            for lot_row in lot_rows:
                evidence_id = (
                    f"game:param:ItemLotParam_map:{lot_row['lot']}:"
                    f"getItemFlagId:check-{ap_id}")
                detection_evidence_ids.append(evidence_id)
                evidence.append({
                    "evidence_id": evidence_id, "claim_id": detection_claim_id,
                    "source_id": source["lot_id"], "stance": "supports",
                    "value": _json(detection_value),
                    "citation": (
                        f"greenfield/flag_lots.tsv:{lot_row['line']} table=map "
                        f"lot={lot_row['lot']} getItemFlagId={flag}"),
                    "method": "tools/build_v060_current_evidence.py:map_lot_detection",
                    "independence_notes": (
                        "Rows from ItemLotParam_map share one game:param family; multiple lot "
                        "rows are one witness, not corroboration."),
                    "valid_from": GAME_VERSION, "valid_to": "",
                    "notes": "Exact map-lot acquisition flag from the committed param census.",
                })
            claims.append({
                "claim_id": detection_claim_id, "subject_kind": "check",
                "subject_id": str(ap_id), "claim_kind": "detection",
                "game_version": GAME_VERSION, "value": _json(detection_value),
                "status": "single_source", "risk": "high", "adjudication": "automatic",
                "evidence_ids": ",".join(sorted(detection_evidence_ids)),
                "last_reviewed": REVIEW_DATE, "review_issue": "#1220", "active": "true",
                "supersedes": "",
            })

        region_value = location["region"]
        generated_region_evidence_id = (
            f"project:data.py:{source['body_hash'].removeprefix('sha256:')}:"
            f"check-{ap_id}:region")
        region_evidence_ids = [generated_region_evidence_id]
        evidence.append({
            "evidence_id": generated_region_evidence_id, "claim_id": region_claim_id,
            "source_id": source["generated_id"],
            "stance": "supports", "value": _json(region_value),
            "citation":
                f"greenfield/eldenring/data.py:LOCATIONS[{location['region']!r}] ap_id={ap_id}",
            "method": "tools/build_v060_current_evidence.py:current_locations",
            "independence_notes":
                "Current region is generated; its provenance inputs are not independent witnesses.",
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": "Current runtime filing; this adapter does not promote it into generation.",
        })

        ruling = overrides.get(flag)
        contradictory = False
        if ruling is not None:
            matched_override_flags.add(flag)
            ruling_value = ruling["region"]
            contradictory = ruling["region"] != location["region"]
            ruling_evidence_id = (
                f"project:region-overrides:{source['override_hash'].removeprefix('sha256:')}:"
                f"line-{ruling['line']}:check-{ap_id}:region")
            region_evidence_ids.append(ruling_evidence_id)
            evidence.append({
                "evidence_id": ruling_evidence_id, "claim_id": region_claim_id,
                "source_id": source["override_id"],
                "stance": "contradicts" if contradictory else "supports",
                "value": _json(ruling_value),
                "citation": f"greenfield/region_overrides.tsv:{ruling['line']} flag={flag}",
                "method": "tools/build_v060_current_evidence.py:flag_region_rulings",
                "independence_notes":
                    "Not independent of data.py: gen_data consumes region_overrides.tsv; "
                    "both records share one family and count once.",
                "valid_from": GAME_VERSION, "valid_to": "", "notes": ruling["reason"],
            })
        claims.append({
            "claim_id": region_claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "region", "game_version": GAME_VERSION,
            "value": _json(region_value),
            "status": "conflicted" if contradictory else "single_source", "risk": "high",
            "adjudication": "automatic",
            "evidence_ids": ",".join(sorted(region_evidence_ids)),
            "last_reviewed": REVIEW_DATE, "review_issue": "#1211", "active": "true",
            "supersedes": "",
        })

    stormhill = [row for row in locations if row["flag"] == 400191]
    if len(stormhill) != 1:
        raise RuntimeError(f"expected one current f400191 check, found {stormhill!r}")
    stormhill_ap_id = stormhill[0]["ap_id"]
    access_claim_id = f"check:{stormhill_ap_id}/access"
    access_value = {
        "type": "any",
        "conditions": [{"type": "flag", "flag": row["gate_flag"]}
                       for row in stormhill_access],
    }
    access_evidence_ids = []
    for row in stormhill_access:
        gate_flag = row["gate_flag"]
        evidence_id = (
            f"game:emevd:m60_41_38_00:90005750:f400191:gate-{gate_flag}:access")
        access_evidence_ids.append(evidence_id)
        locator = row["gate_map"] or row["gate_test_map"]
        evidence.append({
            "evidence_id": evidence_id, "claim_id": access_claim_id,
            "source_id": lot_gates_source_id, "stance": "supports",
            "value": _json(access_value),
            "citation": (
                f"greenfield/lot_gates.tsv:{row['line']} check_flag=400191 "
                f"gate_flag={gate_flag}; {row['source']} event={row['event_id']} "
                f"{row['context']} {row['evidence']} {locator}"
            ),
            "method": "tools/build_v060_current_evidence.py:stormhill_waitfor_access",
            "independence_notes": (
                "One of three OR arms in the same EMEVD common-event family; the f400191 "
                "association is joined through ItemLotParam/flag_lots and is not independent "
                "detection evidence."
            ),
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": "Positive WaitFor prerequisite; separate call sites form one any group.",
        })
    claims.append({
        "claim_id": access_claim_id, "subject_kind": "check",
        "subject_id": str(stormhill_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(access_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": ",".join(sorted(access_evidence_ids)),
        "last_reviewed": REVIEW_DATE, "review_issue": "#1226", "active": "true",
        "supersedes": "",
    })

    death_prince = [row for row in locations if row["flag"] == 9502]
    if len(death_prince) != 1:
        raise RuntimeError(f"expected one current f9502 check, found {death_prince!r}")
    death_prince_ap_id = death_prince[0]["ap_id"]
    death_prince_claim_id = f"check:{death_prince_ap_id}/access"
    death_prince_value = {"type": "flag", "flag": death_prince_access["gate_flag"]}
    death_prince_evidence_id = "game:emevd:m12_03_00_00:90005750:f9502:gate-4131:access"
    evidence.append({
        "evidence_id": death_prince_evidence_id, "claim_id": death_prince_claim_id,
        "source_id": death_prince_source_id, "stance": "supports",
        "value": _json(death_prince_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{death_prince_access['line']} check_flag=9502 "
            f"gate_flag=4131; {death_prince_access['source']} "
            f"event={death_prince_access['event_id']} {death_prince_access['context']} "
            f"{death_prince_access['evidence']} {death_prince_access['gate_test_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:death_prince_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f9502 association is joined "
            "through ItemLotParam/flag_lots and is not independent detection evidence. The "
            "questline extractor cone is a correlated projection with unknown group semantics."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f4131 prerequisite only; this is not the complete Fia quest chain."
        ),
    })
    claims.append({
        "claim_id": death_prince_claim_id, "subject_kind": "check",
        "subject_id": str(death_prince_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(death_prince_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": death_prince_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1237", "active": "true",
        "supersedes": "",
    })

    perfect_order = [row for row in locations if row["flag"] == 9500]
    if len(perfect_order) != 1:
        raise RuntimeError(f"expected one current f9500 check, found {perfect_order!r}")
    perfect_order_ap_id = perfect_order[0]["ap_id"]
    perfect_order_claim_id = f"check:{perfect_order_ap_id}/access"
    perfect_order_value = {"type": "flag", "flag": perfect_order_access["gate_flag"]}
    perfect_order_evidence_id = (
        "game:emevd:m11_05_00_00:90005750:f9500:gate-11059206:access")
    evidence.append({
        "evidence_id": perfect_order_evidence_id, "claim_id": perfect_order_claim_id,
        "source_id": perfect_order_source_id, "stance": "supports",
        "value": _json(perfect_order_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{perfect_order_access['line']} check_flag=9500 "
            f"gate_flag=11059206; {perfect_order_access['source']} "
            f"event={perfect_order_access['event_id']} {perfect_order_access['context']} "
            f"{perfect_order_access['evidence']} {perfect_order_access['gate_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:perfect_order_waitfor_access",
        "independence_notes": (
            "The one WaitFor call is one EMEVD family; the f9500 association is joined through "
            "ItemLotParam/flag_lots and is not independent detection evidence."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": "Positive WaitFor prerequisite; one call site has semantics=single.",
    })
    claims.append({
        "claim_id": perfect_order_claim_id, "subject_kind": "check",
        "subject_id": str(perfect_order_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(perfect_order_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": perfect_order_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1232", "active": "true",
        "supersedes": "",
    })

    varres_bouquet = [row for row in locations if row["flag"] == 400037]
    if len(varres_bouquet) != 1:
        raise RuntimeError(f"expected one current f400037 check, found {varres_bouquet!r}")
    varres_bouquet_ap_id = varres_bouquet[0]["ap_id"]
    varres_bouquet_claim_id = f"check:{varres_bouquet_ap_id}/access"
    varres_bouquet_value = {"type": "flag", "flag": varres_bouquet_access["gate_flag"]}
    varres_bouquet_evidence_id = (
        "game:emevd:m12_05_00_00:90005750:f400037:gate-12059166:access")
    evidence.append({
        "evidence_id": varres_bouquet_evidence_id,
        "claim_id": varres_bouquet_claim_id,
        "source_id": varres_bouquet_source_id, "stance": "supports",
        "value": _json(varres_bouquet_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{varres_bouquet_access['line']} check_flag=400037 "
            f"gate_flag=12059166; {varres_bouquet_access['source']} "
            f"event={varres_bouquet_access['event_id']} "
            f"{varres_bouquet_access['context']} {varres_bouquet_access['evidence']} "
            f"{varres_bouquet_access['gate_test_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:varres_bouquet_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f400037 association is "
            "joined through ItemLotParam/flag_lots and is not independent detection evidence. "
            "The questline DAG and condition cone are correlated projections of this family."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f12059166 prerequisite only; this is not the complete Varre "
            "quest and does not describe the Archipelago Mohg boss-sweep alternate."
        ),
    })
    claims.append({
        "claim_id": varres_bouquet_claim_id, "subject_kind": "check",
        "subject_id": str(varres_bouquet_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(varres_bouquet_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": varres_bouquet_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1244", "active": "true",
        "supersedes": "",
    })

    taunters_tongue = [row for row in locations if row["flag"] == 60300]
    if len(taunters_tongue) != 1:
        raise RuntimeError(f"expected one current f60300 check, found {taunters_tongue!r}")
    taunters_tongue_ap_id = taunters_tongue[0]["ap_id"]
    taunters_tongue_claim_id = f"check:{taunters_tongue_ap_id}/access"
    taunters_tongue_value = {"type": "flag", "flag": taunters_tongue_access["gate_flag"]}
    taunters_tongue_evidence_id = (
        "game:emevd:m11_10_00_00:90005792:f60300:gate-11102180:access")
    evidence.append({
        "evidence_id": taunters_tongue_evidence_id,
        "claim_id": taunters_tongue_claim_id,
        "source_id": taunters_tongue_source_id, "stance": "supports",
        "value": _json(taunters_tongue_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{taunters_tongue_access['line']} check_flag=60300 "
            f"gate_flag=11102180; {taunters_tongue_access['source']} "
            f"event={taunters_tongue_access['event_id']} "
            f"{taunters_tongue_access['context']} {taunters_tongue_access['evidence']}"
        ),
        "method": "tools/build_v060_current_evidence.py:taunters_tongue_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f60300 association is "
            "joined through ItemLotParam/flag_lots and is not independent detection evidence. "
            "The questline DAG is a correlated projection of this family."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f11102180 prerequisite only; the committed corpus does not label "
            "that flag, so this claim assigns it no Alberich or Roundtable meaning."
        ),
    })
    claims.append({
        "claim_id": taunters_tongue_claim_id, "subject_kind": "check",
        "subject_id": str(taunters_tongue_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(taunters_tongue_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": taunters_tongue_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1248", "active": "true",
        "supersedes": "",
    })

    purifying_tear = [row for row in locations if row["flag"] == 65270]
    if len(purifying_tear) != 1:
        raise RuntimeError(f"expected one current f65270 check, found {purifying_tear!r}")
    purifying_tear_ap_id = purifying_tear[0]["ap_id"]
    purifying_tear_claim_id = f"check:{purifying_tear_ap_id}/access"
    purifying_tear_value = {"type": "flag", "flag": purifying_tear_access["gate_flag"]}
    purifying_tear_evidence_id = (
        "game:emevd:m60_39_52_00:90005792:f65270:gate-1039522181:access")
    evidence.append({
        "evidence_id": purifying_tear_evidence_id,
        "claim_id": purifying_tear_claim_id,
        "source_id": purifying_tear_source_id, "stance": "supports",
        "value": _json(purifying_tear_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{purifying_tear_access['line']} check_flag=65270 "
            f"gate_flag=1039522181; {purifying_tear_access['source']} "
            f"event={purifying_tear_access['event_id']} "
            f"{purifying_tear_access['context']} {purifying_tear_access['evidence']}"
        ),
        "method": "tools/build_v060_current_evidence.py:purifying_tear_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f65270 association is "
            "joined through ItemLotParam/flag_lots and is not independent detection evidence. "
            "The questline DAG is a correlated projection of this family."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f1039522181 prerequisite only; the committed corpus does not "
            "label that flag, so this claim assigns it no Eleonora or broader quest meaning and "
            "does not describe the Archipelago Sanguine Noble boss-sweep alternate."
        ),
    })
    claims.append({
        "claim_id": purifying_tear_claim_id, "subject_kind": "check",
        "subject_id": str(purifying_tear_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(purifying_tear_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": purifying_tear_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1253", "active": "true",
        "supersedes": "",
    })

    ijis_bell_bearing = [row for row in locations if row["flag"] == 400240]
    if len(ijis_bell_bearing) != 1:
        raise RuntimeError(f"expected one current f400240 check, found {ijis_bell_bearing!r}")
    ijis_bell_bearing_ap_id = ijis_bell_bearing[0]["ap_id"]
    ijis_bell_bearing_claim_id = f"check:{ijis_bell_bearing_ap_id}/access"
    ijis_bell_bearing_value = {
        "type": "flag", "flag": ijis_bell_bearing_access["gate_flag"]}
    ijis_bell_bearing_evidence_id = (
        "game:emevd:m60_34_49_00:90005750:f400240:gate-3768:access")
    evidence.append({
        "evidence_id": ijis_bell_bearing_evidence_id,
        "claim_id": ijis_bell_bearing_claim_id,
        "source_id": ijis_bell_bearing_source_id, "stance": "supports",
        "value": _json(ijis_bell_bearing_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{ijis_bell_bearing_access['line']} check_flag=400240 "
            f"gate_flag=3768; {ijis_bell_bearing_access['source']} "
            f"event={ijis_bell_bearing_access['event_id']} "
            f"{ijis_bell_bearing_access['context']} {ijis_bell_bearing_access['evidence']} "
            f"{ijis_bell_bearing_access['gate_test_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:ijis_bell_bearing_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f400240 association is "
            "joined through ItemLotParam/flag_lots and is not independent detection evidence. "
            "The questline DAG and condition cone are correlated projections of this family."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f3768 prerequisite only; the generic committed flag label does "
            "not prove Iji's death or the complete Ranni/Iji quest, and this claim does not "
            "describe the Archipelago Royal Revenant boss-sweep alternate."
        ),
    })
    claims.append({
        "claim_id": ijis_bell_bearing_claim_id, "subject_kind": "check",
        "subject_id": str(ijis_bell_bearing_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(ijis_bell_bearing_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": ijis_bell_bearing_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1259", "active": "true",
        "supersedes": "",
    })

    frenzied_flame_seal = [row for row in locations if row["flag"] == 400089]
    if len(frenzied_flame_seal) != 1:
        raise RuntimeError(f"expected one current f400089 check, found {frenzied_flame_seal!r}")
    frenzied_flame_seal_ap_id = frenzied_flame_seal[0]["ap_id"]
    frenzied_flame_seal_claim_id = f"check:{frenzied_flame_seal_ap_id}/access"
    frenzied_flame_seal_value = {
        "type": "flag", "flag": frenzied_flame_seal_access["gate_flag"]}
    frenzied_flame_seal_evidence_id = (
        "game:emevd:m35_00_00_00:90005750:f400089:gate-35009211:access")
    evidence.append({
        "evidence_id": frenzied_flame_seal_evidence_id,
        "claim_id": frenzied_flame_seal_claim_id,
        "source_id": frenzied_flame_seal_source_id, "stance": "supports",
        "value": _json(frenzied_flame_seal_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{frenzied_flame_seal_access['line']} check_flag=400089 "
            f"gate_flag=35009211; {frenzied_flame_seal_access['source']} "
            f"event={frenzied_flame_seal_access['event_id']} "
            f"{frenzied_flame_seal_access['context']} "
            f"{frenzied_flame_seal_access['evidence']} "
            f"{frenzied_flame_seal_access['gate_test_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:frenzied_flame_seal_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f400089 association is "
            "joined through ItemLotParam/flag_lots and is not independent detection evidence. "
            "The questline DAG and condition cone are correlated projections of this family."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f35009211 prerequisite only; this does not prove the complete "
            "Hyetta or Frenzied Flame quest, and does not describe the Archipelago Mohg, the "
            "Omen boss-sweep alternate."
        ),
    })
    claims.append({
        "claim_id": frenzied_flame_seal_claim_id, "subject_kind": "check",
        "subject_id": str(frenzied_flame_seal_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(frenzied_flame_seal_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": frenzied_flame_seal_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1264", "active": "true",
        "supersedes": "",
    })

    witch_crown = [row for row in locations if row["flag"] == 400107]
    if len(witch_crown) != 1:
        raise RuntimeError(f"expected one current f400107 check, found {witch_crown!r}")
    witch_crown_ap_id = witch_crown[0]["ap_id"]
    witch_crown_claim_id = f"check:{witch_crown_ap_id}/access"
    witch_crown_value = {"type": "flag", "flag": witch_crown_access["gate_flag"]}
    witch_crown_evidence_id = (
        "game:emevd:m14_00_00_00:90005750:f400107:gate-3469:access")
    evidence.append({
        "evidence_id": witch_crown_evidence_id,
        "claim_id": witch_crown_claim_id,
        "source_id": witch_crown_source_id, "stance": "supports",
        "value": _json(witch_crown_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{witch_crown_access['line']} check_flag=400107 "
            f"gate_flag=3469; {witch_crown_access['source']} "
            f"event={witch_crown_access['event_id']} {witch_crown_access['context']} "
            f"{witch_crown_access['evidence']} {witch_crown_access['gate_test_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:witch_crown_immediate_waitfor",
        "independence_notes": (
            "The one immediate WaitFor call is one EMEVD family; the f400107 association is "
            "joined through ItemLotParam/flag_lots and is not independent detection evidence. "
            "The questline DAG and condition cone are correlated projections of this family."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "Immediate positive f3469 prerequisite only; the generic NPC state label does not "
            "prove Sellen's identity, death, or complete quest, and this claim does not describe "
            "the Archipelago Red Wolf of Radagon boss-sweep alternate."
        ),
    })
    claims.append({
        "claim_id": witch_crown_claim_id, "subject_kind": "check",
        "subject_id": str(witch_crown_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(witch_crown_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": witch_crown_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1267", "active": "true",
        "supersedes": "",
    })

    # AP does not model the three vanilla Radahn Festival routes as item/quest logic. The client
    # receives f9410 unconditionally through startGraces, so reaching the owning Caelid region is
    # sufficient for both progression-bearing Radahn rewards under every supported option set.
    radahn_value = {
        "type": "region", "region": "Caelid",
        "runtime_bypass": {"type": "start_flag", "flag": RADAHN_FESTIVAL_FLAG},
    }
    location_by_ap_id = {row["ap_id"]: row for row in locations}
    for ap_id in RADAHN_ACCESS_AP_IDS:
        location = location_by_ap_id.get(ap_id)
        if location is None or location["region"] != "Caelid":
            raise RuntimeError(f"Radahn access subject changed: ap_id={ap_id} row={location!r}")
        claim_id = f"check:{ap_id}/access"
        evidence_id = f"project:radahn-start-flag:f9410:check-{ap_id}:access"
        evidence.append({
            "evidence_id": evidence_id, "claim_id": claim_id,
            "source_id": radahn_source_id, "stance": "supports",
            "value": _json(radahn_value),
            "citation": (
                "greenfield/eldenring/features/start_grace.py:StartGrace.slot_data "
                "appends _RADAHN_FESTIVAL=9410 unconditionally; "
                "greenfield/eldenring/tests/test_gf_features_smoke.py:"
                "FeaturesSmoke.test_radahn_festival_flag_force_set"
            ),
            "method": "tools/build_v060_current_evidence.py:radahn_start_flag_access",
            "independence_notes": (
                "The regression test checks the same project runtime path and is not an "
                "independent witness; this is an explicit project access ruling."
            ),
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": (
                "The unconditional spawn flag discharges the vanilla Mistwood, Ranni's Rise, "
                "and story-flag alternatives; no additional AP item or quest predicate remains."
            ),
        })
        claims.append({
            "claim_id": claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "access", "game_version": GAME_VERSION,
            "value": _json(radahn_value), "status": "proven", "risk": "critical",
            "adjudication": "design_ruling", "evidence_ids": evidence_id,
            "last_reviewed": "2026-09-01", "review_issue": "#1271", "active": "true",
            "supersedes": "",
        })

    fingerslayer_location = location_by_ap_id.get(FINGERSLAYER_ACCESS_AP_ID)
    if fingerslayer_location is None or fingerslayer_location["region"] != "Siofra River":
        raise RuntimeError(f"Fingerslayer access subject changed: {fingerslayer_location!r}")
    fingerslayer_claim_id = f"check:{FINGERSLAYER_ACCESS_AP_ID}/access"
    fingerslayer_evidence_id = (
        f"project:fingerslayer-start-flag:f{FINGERSLAYER_CHEST_GATE_FLAG}:"
        f"check-{FINGERSLAYER_ACCESS_AP_ID}:access")
    fingerslayer_value = {
        "type": "region", "region": "Siofra River",
        "runtime_bypass": {
            "type": "start_flag", "flag": FINGERSLAYER_CHEST_GATE_FLAG,
        },
    }
    evidence.append({
        "evidence_id": fingerslayer_evidence_id, "claim_id": fingerslayer_claim_id,
        "source_id": fingerslayer_source_id, "stance": "supports",
        "value": _json(fingerslayer_value),
        "citation": (
            "greenfield/eldenring/features/start_grace.py:StartGrace.slot_data appends "
            "_FINGERSLAYER_CHEST_GATE=1034509410 unconditionally; "
            "greenfield/eldenring/tests/test_gf_features_smoke.py:"
            "FeaturesSmoke.test_fingerslayer_chest_gate_flag_force_set"
        ),
        "method": "tools/build_v060_current_evidence.py:fingerslayer_start_flag_access",
        "independence_notes": (
            "The regression test checks the same project runtime path and is not an independent "
            "witness; this is an explicit project access ruling."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": (
            "The unconditional spawn flag opens the Ranni-gated chest; no additional AP item or "
            "quest predicate remains once Siofra River is reachable."
        ),
    })
    claims.append({
        "claim_id": fingerslayer_claim_id, "subject_kind": "check",
        "subject_id": str(FINGERSLAYER_ACCESS_AP_ID), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(fingerslayer_value),
        "status": "proven", "risk": "critical", "adjudication": "design_ruling",
        "evidence_ids": fingerslayer_evidence_id, "last_reviewed": "2026-09-01",
        "review_issue": "#1271", "active": "true", "supersedes": "",
    })

    carian_locations = {
        row["ap_id"]: row for row in locations if row["flag"] in CARIAN_STATUE_ACCESS_FLAGS
    }
    if set(carian_locations) != CARIAN_STATUE_ACCESS_AP_IDS:
        raise RuntimeError(f"Carian Statue access subjects changed: {carian_locations!r}")
    carian_value = {
        "type": "all",
        "conditions": [
            {"type": "region", "region": "Liurnia"},
            {"type": "item", "name": "Carian Inverted Statue"},
        ],
        "when": {
            "item_shuffle": True,
            "legacy_dungeon_keys": True,
            "vanilla_placement": False,
        },
    }
    for ap_id in sorted(carian_locations):
        claim_id = f"check:{ap_id}/access"
        evidence_id = f"project:carian-statue-gate:check-{ap_id}:access"
        evidence.append({
            "evidence_id": evidence_id, "claim_id": claim_id,
            "source_id": carian_statue_source_id, "stance": "supports",
            "value": _json(carian_value),
            "citation": (
                "greenfield/eldenring/features/legacy_key_gates.py:"
                "_LEGACY_EXTRA['Carian Inverted Statue'] and LegacyKeyGates.set_rules; "
                "greenfield/eldenring/tests/test_gf_legacy_key_gate.py:"
                "LegacyKeyGateOn.test_carian_statue_gates_the_inverted_route_and_not_the_standard_hall"
            ),
            "method": "tools/build_v060_current_evidence.py:carian_statue_encoded_access",
            "independence_notes": (
                "The regression exercises the same project rule and is not an independent "
                "game-data witness; this claim records implemented Archipelago logic."
            ),
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": (
                f"Exact generated subject f{carian_locations[ap_id]['flag']}; the option guard "
                "is part of the claim and inactive modes remain unresolved in the census."
            ),
        })
        claims.append({
            "claim_id": claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "access", "game_version": GAME_VERSION,
            "value": _json(carian_value), "status": "proven", "risk": "critical",
            "adjudication": "design_ruling", "evidence_ids": evidence_id,
            "last_reviewed": "2026-09-01", "review_issue": "#1271", "active": "true",
            "supersedes": "",
        })

    finger_ruins_locations = {
        row["ap_id"]: row for row in locations if row["ap_id"] in FINGER_RUINS_BELL_ACCESS
    }
    if set(finger_ruins_locations) != set(FINGER_RUINS_BELL_ACCESS):
        raise RuntimeError(f"Finger Ruins bell access subjects changed: {finger_ruins_locations!r}")
    for ap_id, (flag, region) in sorted(FINGER_RUINS_BELL_ACCESS.items()):
        row = finger_ruins_locations[ap_id]
        if (row["flag"], row["region"]) != (flag, region):
            raise RuntimeError(f"Finger Ruins bell subject changed: {row!r}")
        value = {
            "type": "all",
            "conditions": [
                {"type": "region", "region": region},
                {"type": "item", "name": "Hole-Laden Necklace"},
            ],
            "when": {
                "item_shuffle": True,
                "legacy_dungeon_keys": True,
                "vanilla_placement": False,
            },
        }
        claim_id = f"check:{ap_id}/access"
        evidence_id = f"project:hole-laden-necklace-gate:check-{ap_id}:access"
        evidence.append({
            "evidence_id": evidence_id, "claim_id": claim_id,
            "source_id": finger_ruins_source_id, "stance": "supports",
            "value": _json(value),
            "citation": (
                "greenfield/eldenring/features/legacy_key_gates.py:"
                "_LEGACY_EXTRA['Hole-Laden Necklace'] and LegacyKeyGates.set_rules; "
                "greenfield/eldenring/tests/test_gf_legacy_key_gate.py:"
                "LegacyKeyGateOn.test_metyr_chain_needs_the_necklace_and_both_region_locks"
            ),
            "method": "tools/build_v060_current_evidence.py:finger_ruins_bell_encoded_access",
            "independence_notes": (
                "The regression exercises the same project rule and is not an independent "
                "game-data witness; this claim records implemented Archipelago logic."
            ),
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": (
                f"Exact generated subject f{flag}; ordinary {region} reachability supplies the "
                "region condition. The option guard is part of the claim and inactive modes "
                "remain unresolved in the census."
            ),
        })
        claims.append({
            "claim_id": claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "access", "game_version": GAME_VERSION,
            "value": _json(value), "status": "proven", "risk": "critical",
            "adjudication": "design_ruling", "evidence_ids": evidence_id,
            "last_reviewed": "2026-09-01", "review_issue": "#1271", "active": "true",
            "supersedes": "",
        })

    evidence.sort(key=lambda row: row["evidence_id"])
    claims.sort(key=lambda row: row["claim_id"])
    source_ids = {row["source_id"] for row in sources}
    claim_ids = {row["claim_id"] for row in claims}
    if len(claim_ids) != len(claims):
        raise RuntimeError("adapter emitted duplicate active claims")
    if any(row["source_id"] not in source_ids for row in evidence):
        raise RuntimeError("adapter emitted evidence with a dangling source")
    if any(row["claim_id"] not in claim_ids for row in evidence):
        raise RuntimeError("adapter emitted evidence with a dangling claim")

    content = {
        "sources": sources, "evidence": evidence, "claims": claims,
        "environments": environments,
    }
    return {
        **content,
        "diagnostics": {
            "locations": len(locations), "flag_overrides_total": len(overrides),
            "flag_overrides_matched": len(matched_override_flags),
            "flag_overrides_without_current_check": len(set(overrides) - matched_override_flags),
            "non_flag_overrides_out_of_scope": non_flag_overrides,
            "map_lot_rows": sum(len(rows) for rows in map_lots.values()),
            "map_lot_flags": len(map_lots),
            "map_lot_flags_matched": len(matched_map_lot_flags),
            "map_lot_flags_without_current_check": len(set(map_lots) - matched_map_lot_flags),
            "stormhill_access_claims": 1,
            "perfect_order_access_claims": 1,
            "death_prince_access_claims": 1,
            "varres_bouquet_access_claims": 1,
            "taunters_tongue_access_claims": 1,
            "purifying_tear_access_claims": 1,
            "ijis_bell_bearing_access_claims": 1,
            "frenzied_flame_seal_access_claims": 1,
            "witch_crown_access_claims": 1,
            "radahn_access_claims": len(RADAHN_ACCESS_AP_IDS),
            "fingerslayer_access_claims": 1,
            "carian_statue_access_claims": len(CARIAN_STATUE_ACCESS_AP_IDS),
            "finger_ruins_bell_access_claims": len(FINGER_RUINS_BELL_ACCESS),
        },
    }


def _write_tsv(path: Path, fields: Iterable[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields)
        for row in rows:
            values = [row.get(field, "") for field in fields]
            while values and values[-1] == "":
                values.pop()
            writer.writerow(values)


def write_bundle(repo: Path, out_dir: Path) -> dict:
    bundle = build_records(repo)
    table_rows = {
        "sources.tsv": bundle["sources"],
        "evidence.tsv": bundle["evidence"],
        "claims.tsv": bundle["claims"],
        "environments.tsv": bundle["environments"],
    }
    for name, rows in table_rows.items():
        _write_tsv(out_dir / name, evidence_ledger.HEADERS[name], rows)
    evidence_ledger.validate(out_dir)
    bundle["summary"] = evidence_ledger.summary(out_dir)
    (out_dir / "summary.json").write_text(
        json.dumps(bundle["summary"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-dir", type=Path, default=Path("greenfield/evidence/v060-current"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    out_dir = args.out_dir if args.out_dir.is_absolute() else repo / args.out_dir
    bundle = write_bundle(repo, out_dir)
    print(_json({**bundle["summary"], **bundle["diagnostics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
