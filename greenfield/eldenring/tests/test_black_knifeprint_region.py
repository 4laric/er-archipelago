"""The examined knifeprint return and catacombs acquisition are distinct checks."""
from pathlib import Path
import runpy


def test_knifeprint_return_is_not_locked_behind_leyndell():
    data = runpy.run_path(str(Path(__file__).parents[1] / "tables" / "data.py"))
    by_flag = {
        flag: (region, ident)
        for region, rows in data["LOCATIONS"].items()
        for _name, ident, flag in rows
        if flag in (400357, 520210)
    }
    assert by_flag[400357] == ("Roundtable Hold", 7770607)
    assert by_flag[520210] == ("Liurnia", 7900139)


def test_relocating_npc_rewards_use_the_handover_region():
    data = runpy.run_path(str(Path(__file__).parents[1] / "tables" / "data.py"))
    expected = {
        400320: ("Caelid", 7770598),
        400391: ("Liurnia", 7773733),
        400600: ("Shadow Keep", 7773742),
        400722: ("Belurat", 7770649),
    }
    actual = {}
    for region, rows in data["LOCATIONS"].items():
        for name, ident, flag in rows:
            if flag in expected:
                assert flag not in actual, "One acquisition must not become two checks"
                actual[flag] = (region, ident)
                assert name.startswith(region + " :: ")
    assert actual == expected
