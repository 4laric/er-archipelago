import importlib.util
import json
from pathlib import Path

import pytest

try:
    from ._util import REPO_ONLY_REASON, find_repo_root
except ImportError:
    from _util import REPO_ONLY_REASON, find_repo_root

ROOT = find_repo_root(__file__, marker="tools/build_upgrade_blessing_review_batch.py")
SCRIPT = Path(ROOT) / "tools/build_upgrade_blessing_review_batch.py" if ROOT else None
pytestmark = pytest.mark.skipif(ROOT is None, reason=REPO_ONLY_REASON)


def load_builder():
    assert SCRIPT is not None
    spec = importlib.util.spec_from_file_location("upgrade_blessing_review", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_blessing_review_is_partitioned_and_complete():
    rows, summary = load_builder().build()
    assert rows
    assert len(rows) == len({row["check_id"] for row in rows})
    assert {row["category"] for row in rows} == {
        "glovewort", "golden_seed", "revered_spirit_ash", "sacred_tear",
        "scadutree_fragment", "smithing_stone",
    }
    assert all(row["flag"] and row["access_disposition"] for row in rows)
    assert all(row["review_status"] in {
        "trusted", "audited_one_family", "remaining_unreviewed",
        "region_taxonomy_conflict"} for row in rows)
    assert sum(group["audited"] for group in summary["by_category"].values()) == len(rows)
    assert summary["totals"]["audited"] == len(rows)
    assert summary["totals"]["audited"] == (
        summary["totals"]["trusted"] + summary["totals"]["held"])
    assert summary["totals"]["conflicted"] == 2
    conflicts = {row["check_id"] for row in rows
                 if row["review_status"] == "region_taxonomy_conflict"}
    assert conflicts == {"7773495", "7773939"}


def test_upgrade_blessing_generated_files_are_current():
    builder = load_builder()
    rows, summary = builder.build()
    assert builder.OUT_PATH.read_text(encoding="utf-8") == builder.render_tsv(rows)
    assert json.loads(builder.SUMMARY_PATH.read_text(encoding="utf-8")) == summary
