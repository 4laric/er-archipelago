#!/usr/bin/env python3
"""Build the Smithbox delta that restores Elden Ring 1.17's Torrent param rows."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO / "elden_ring_artifacts/vanilla_er/vanilla_er/RideParam.csv"
DEFAULT_NPC_INPUT = REPO / "elden_ring_artifacts/vanilla_er/vanilla_er/NpcParam.csv"
DEFAULT_OUTPUT = REPO / "release/tarnished-torrent-rideparam-1.17.json"
ROW_TO_CHARACTER = {80020: 8002, 80030: 8003, 80040: 8004, 80050: 8005}
NPC_ROWS = (80020000, 80030000, 80040000, 80050000)
PARAM_VERSION_117 = 11_700_000
PROJECT_TYPE_ELDEN_RING = 8


class PatchError(RuntimeError):
    pass


def load_rows(path: Path) -> tuple[list[str], dict[int, dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            fields = [field for field in (reader.fieldnames or []) if field]
            rows = {int(row["ID"]): row for row in reader}
    except (OSError, KeyError, ValueError) as exc:
        raise PatchError(f"could not read RideParam CSV {path}: {exc}") from exc
    if not fields or "ID" not in fields:
        raise PatchError("RideParam CSV has no ID column")
    return fields, rows


def validate_117_rows(fields: list[str], rows: dict[int, dict[str, str]]) -> None:
    template = rows.get(80000)
    if template is None:
        raise PatchError("RideParam row 80000 (base Torrent) is absent")
    for row_id, character_id in ROW_TO_CHARACTER.items():
        row = rows.get(row_id)
        if row is None:
            raise PatchError(f"Elden Ring 1.17 RideParam row {row_id} is absent")
        if row.get("defChrId") != str(character_id):
            raise PatchError(
                f"RideParam {row_id} targets defChrId {row.get('defChrId')!r}, expected {character_id}"
            )
        differences = {
            field for field in fields
            if field not in {"ID", "defChrId"} and row.get(field) != template.get(field)
        }
        if differences:
            raise PatchError(
                f"RideParam {row_id} unexpectedly differs from base Torrent in: "
                + ", ".join(sorted(differences))
            )


def validate_npc_rows(fields: list[str], rows: dict[int, dict[str, str]]) -> None:
    template = rows.get(80000000)
    if template is None:
        raise PatchError("NpcParam row 80000000 (base Torrent) is absent")
    for row_id in NPC_ROWS:
        row = rows.get(row_id)
        if row is None:
            raise PatchError(f"Elden Ring 1.17 NpcParam row {row_id} is absent")
        if row.get("normalChangeAnimChrId") != "8000":
            raise PatchError(f"NpcParam {row_id} does not target base Torrent animations")
        differences = {
            field for field in fields
            if field not in {"ID", "normalChangeAnimChrId"} and row.get(field) != template.get(field)
        }
        if differences:
            raise PatchError(
                f"NpcParam {row_id} unexpectedly differs from base Torrent in: "
                + ", ".join(sorted(differences))
            )


def _delta(fields, row_id, row):
    return {
        "ID": row_id,
        "Index": 0,
        "Name": row.get("Name", ""),
        "Fields": [
            {"Field": field, "Value": row.get(field, "")}
            for field in fields if field not in {"ID", "Name", ""}
        ],
        "State": 0,
    }


def build_patch(path: Path, npc_path: Path) -> dict[str, object]:
    fields, rows = load_rows(path)
    validate_117_rows(fields, rows)
    npc_fields, npc_rows = load_rows(npc_path)
    validate_npc_rows(npc_fields, npc_rows)
    return {
        "ProjectType": PROJECT_TYPE_ELDEN_RING,
        "ParamVersion": PARAM_VERSION_117,
        "Tag": "ER Archipelago - Tarnished Edition compatibility",
        "Params": [
            {
                "Name": "RideParam",
                "Rows": [_delta(fields, row_id, rows[row_id]) for row_id in ROW_TO_CHARACTER],
            },
            {
                "Name": "NpcParam",
                "Rows": [_delta(npc_fields, row_id, npc_rows[row_id]) for row_id in NPC_ROWS],
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--npc-input", type=Path, default=DEFAULT_NPC_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_patch(args.input, args.npc_input), indent=2) + "\n"
    if args.check:
        try:
            current = args.output.read_text(encoding="utf-8")
        except OSError as exc:
            raise PatchError(f"could not read generated patch {args.output}: {exc}") from exc
        if current != rendered:
            raise PatchError(f"generated Torrent patch is stale: {args.output}")
        print(f"Torrent RideParam patch is current: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchError as exc:
        raise SystemExit(f"gen_torrent_rideparam_patch: FATAL: {exc}") from exc
