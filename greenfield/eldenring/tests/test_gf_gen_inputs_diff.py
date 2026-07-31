"""The param-diff guard that has to work exactly once, months from now, on a day nobody planned for.

`tools/diff_gen_inputs.py` exists for game-patch day: re-dump the regulation with Smithbox, recompile
`gen_inputs.db`, and find out what moved. Most of its output is informational, but ONE branch is
load-bearing -- the watched-id guard, which fires when an id we have built runtime behaviour on gains
a reference it did not have before.

That matters because we REPURPOSE vanilla `SpEffectParam` rows: we rewrite their fields at runtime and
apply them to the player (`no_equip_load` 20012080, `no_fall_damage` 20010827, `scadu_blessing`
20012081). Each was claimed on the evidence that it occurs exactly once across all 239 param tables --
as its own row, referenced by nothing. If a patch adds a reference, we would be silently overwriting a
row the game reads, and the symptom is a balance bug in one area weeks later rather than a crash.

🛑 NO CORPUS REACHES THAT BRANCH. There is no patched regulation in the repo to diff against, so the
guard would sit unexercised until the exact moment it is needed
(`guard-absent-from-corpus-needs-a-direct-call`). These tests build synthetic bundles in memory and
call it directly -- including a MUTATION that plants a reference to a claimed row and asserts the tool
notices and exits non-zero.
"""
import csv
import io
import sqlite3
import sys
import zlib
from pathlib import Path

import pytest

from ._util import find_repo_root

# `gf_test.py` installs the world into a pinned AP checkout and copies NO `tools/`, so the tool under
# test is simply absent there -- find_repo_root returns None and we skip, exactly like the other
# cross-tree tests do. Running from a real checkout, it resolves and the tests run.
_ROOT = find_repo_root(Path(__file__))
if _ROOT is None:
    pytest.skip("not running from a repo checkout -- tools/ is not installed alongside the world",
                allow_module_level=True)
sys.path.insert(0, str(Path(_ROOT) / "tools"))

diff_gen_inputs = pytest.importorskip("diff_gen_inputs")

PARAM = "vanilla_er/vanilla_er/%s.csv"
SAFE_ROW = 20012081        # scadu_blessing's claimed clone row
LADDER_ROW = 20000100      # the Scadutree blessing ladder's base


def _bundle(path, tables):
    """A minimal gen_inputs.db: `files(path, blob)` with zlib'd CSV text, which is all the tool reads."""
    db = sqlite3.connect(str(path))
    db.execute("CREATE TABLE files (path TEXT PRIMARY KEY, size INT, sha256 TEXT, blob BLOB)")
    for name, text in tables.items():
        db.execute("INSERT INTO files VALUES (?,?,?,?)",
                   (PARAM % name, len(text), "", zlib.compress(text.encode("utf-8"))))
    db.commit()
    db.close()


def _csv(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def _invoke(tmp_path, extra):
    argv = [str(tmp_path / "old.db"), str(tmp_path / "new.db"), *extra]
    old_argv = sys.argv
    sys.argv = ["diff_gen_inputs.py", *argv]
    try:
        return diff_gen_inputs.main()
    finally:
        sys.argv = old_argv


BASE = {
    "SpEffectParam": _csv(["ID", "Name", "effectEndurance"],
                          [[SAFE_ROW, "", -1], [LADDER_ROW, "", 0.05]]),
    "EquipParamProtector": _csv(["ID", "Name", "residentSpEffectId"],
                                [[1100, "", -1], [1101, "", -1]]),
}


def test_identical_bundles_are_clean(tmp_path):
    """The base case. A patch that touches nothing must not produce noise -- a tool that cries wolf
    on a clean run is one people stop reading, which is how a real hit gets waved through."""
    _bundle(tmp_path / "old.db", BASE)
    _bundle(tmp_path / "new.db", BASE)
    assert _invoke(tmp_path, []) == 0


def test_a_new_unrelated_row_is_reported_but_does_not_fail(tmp_path):
    """A patch adds rows -- that is normal and informational. Only the watch list is a stop signal,
    otherwise every patch day ends in a red gate nobody can act on."""
    new = dict(BASE)
    new["SpEffectParam"] = _csv(["ID", "Name", "effectEndurance"],
                                [[SAFE_ROW, "", -1], [LADDER_ROW, "", 0.05], [29999999, "", 0]])
    _bundle(tmp_path / "old.db", BASE)
    _bundle(tmp_path / "new.db", new)
    assert _invoke(tmp_path, []) == 0


def test_a_NEW_REFERENCE_to_a_claimed_row_fails_the_run(tmp_path):
    """🛑 THE MUTATION. A new armour piece points `residentSpEffectId` at the row `scadu_blessing`
    repurposed. This is the exact shape of the failure the tool exists for, and it must exit 1."""
    new = dict(BASE)
    new["EquipParamProtector"] = _csv(["ID", "Name", "residentSpEffectId"],
                                      [[1100, "", SAFE_ROW], [1101, "", -1]])
    _bundle(tmp_path / "old.db", BASE)
    _bundle(tmp_path / "new.db", new)
    assert _invoke(tmp_path, []) == 1, (
        "a new reference to a repurposed row MUST fail the run -- rewriting a row the game reads is "
        "a silent balance bug, not a crash")


def test_the_row_merely_EXISTING_is_not_a_hit(tmp_path):
    """The subtlety that makes the guard usable. A repurposed row already occurs once, as its own
    row, in every dump. Presence would fire on every single run; only a RISING COUNT is a new
    reference. Pin it, because 'just check if the id appears' is the obvious wrong implementation."""
    new = dict(BASE)
    # same rows, one unrelated value changed -- the safe row is still present, still unreferenced
    new["SpEffectParam"] = _csv(["ID", "Name", "effectEndurance"],
                                [[SAFE_ROW, "", -1], [LADDER_ROW, "", 0.07]])
    _bundle(tmp_path / "old.db", BASE)
    _bundle(tmp_path / "new.db", new)
    assert _invoke(tmp_path, []) == 0


def test_the_watch_list_covers_every_row_we_repurpose(tmp_path):
    """Drift guard. The claimed rows live in the client's `safe_speffect_rows.rs`; this tool carries
    its own copy of the ids. If someone claims a fourth row and forgets to add it here, the guard is
    silently narrower than the thing it protects."""
    watched = {w for _, rng in diff_gen_inputs.WATCHED for w in rng}
    for row, owner in ((20012080, "no_equip_load"), (20010827, "no_fall_damage"),
                       (20012081, "scadu_blessing")):
        assert row in watched, (
            f"{row} ({owner}) is repurposed at runtime but is NOT in diff_gen_inputs.WATCHED -- a "
            "patch could start referencing it and this tool would say nothing")


def test_a_column_layout_change_is_called_out(tmp_path, capsys):
    """A header change invalidates every ordinal/offset assumption downstream, and a row-by-row diff
    against a shifted header is worse than useless -- it reports every row as changed. Say so."""
    new = dict(BASE)
    new["SpEffectParam"] = _csv(["ID", "Name", "effectEndurance", "brandNewColumn"],
                                [[SAFE_ROW, "", -1, 0], [LADDER_ROW, "", 0.05, 0]])
    _bundle(tmp_path / "old.db", BASE)
    _bundle(tmp_path / "new.db", new)
    _invoke(tmp_path, [])
    assert "COLUMN LAYOUT CHANGED" in capsys.readouterr().out
