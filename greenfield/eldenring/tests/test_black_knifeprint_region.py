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
