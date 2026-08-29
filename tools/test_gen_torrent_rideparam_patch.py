import csv
import importlib.util
import json
from pathlib import Path

import pytest


PATH = Path(__file__).with_name("gen_torrent_rideparam_patch.py")
SPEC = importlib.util.spec_from_file_location("torrent_patch", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

FIELDS = [
    "ID", "Name", "atkChrId", "defChrId", "rideCamParamId", "atkChrAnimId",
    "defChrAnimId", "defAdjustDmyId", "defCheckDmyId", "diffAngMyToDef", "dist",
    "upperYRange", "lowerYRange", "diffAngMin", "diffAngMax", "pad",
]


def write_fixture(path: Path, mutate=None):
    base = {
        "Name": "", "atkChrId": "0", "defChrId": "8000", "rideCamParamId": "3010",
        "atkChrAnimId": "0", "defChrAnimId": "0", "defAdjustDmyId": "900",
        "defCheckDmyId": "-1", "diffAngMyToDef": "180", "dist": "5",
        "upperYRange": "5", "lowerYRange": "5", "diffAngMin": "-180",
        "diffAngMax": "180", "pad": "[0|0|0|0|0|0|0|0|0|0|0|0]",
    }
    rows = [dict(base, ID="80000")]
    rows += [dict(base, ID=str(row_id), defChrId=str(character_id))
             for row_id, character_id in MODULE.ROW_TO_CHARACTER.items()]
    if mutate:
        mutate(rows)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_npc_fixture(path: Path, mutate=None):
    fields = ["ID", "Name", "normalChangeAnimChrId", "other"]
    rows = [{"ID": "80000000", "Name": "", "normalChangeAnimChrId": "-1", "other": "same"}]
    rows += [
        {"ID": str(row_id), "Name": "", "normalChangeAnimChrId": "8000", "other": "same"}
        for row_id in MODULE.NPC_ROWS
    ]
    if mutate:
        mutate(rows)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_patch_contains_only_the_four_added_rows(tmp_path):
    source = tmp_path / "RideParam.csv"
    npc = tmp_path / "NpcParam.csv"
    write_fixture(source)
    write_npc_fixture(npc)
    patch = MODULE.build_patch(source, npc)
    assert patch["ProjectType"] == 8
    assert patch["ParamVersion"] == 11_700_000
    param, npc_param = patch["Params"]
    assert param["Name"] == "RideParam"
    assert [row["ID"] for row in param["Rows"]] == [80020, 80030, 80040, 80050]
    assert all(row["State"] == 0 for row in param["Rows"])
    assert [next(field["Value"] for field in row["Fields"]
                 if field["Field"] == "defChrId") for row in param["Rows"]] == [
                     "8002", "8003", "8004", "8005"]
    assert npc_param["Name"] == "NpcParam"
    assert [row["ID"] for row in npc_param["Rows"]] == list(MODULE.NPC_ROWS)


def test_missing_117_row_is_refused(tmp_path):
    source = tmp_path / "RideParam.csv"
    npc = tmp_path / "NpcParam.csv"
    write_fixture(source, lambda rows: rows.pop())
    write_npc_fixture(npc)
    with pytest.raises(MODULE.PatchError, match="80050 is absent"):
        MODULE.build_patch(source, npc)


def test_unexpected_row_change_is_refused(tmp_path):
    source = tmp_path / "RideParam.csv"
    npc = tmp_path / "NpcParam.csv"
    write_fixture(source, lambda rows: rows[1].update(dist="99"))
    write_npc_fixture(npc)
    with pytest.raises(MODULE.PatchError, match="unexpectedly differs.*dist"):
        MODULE.build_patch(source, npc)


def test_committed_patch_matches_verified_117_corpus():
    source = MODULE.DEFAULT_INPUT
    if not source.is_file():
        pytest.skip("gen_inputs.db has not been extracted")
    committed = json.loads(MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert committed == MODULE.build_patch(source, MODULE.DEFAULT_NPC_INPUT)
