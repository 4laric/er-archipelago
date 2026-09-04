import importlib.util
from pathlib import Path
import pytest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    from _util import find_repo_root, REPO_ONLY_REASON

ROOT = find_repo_root(__file__, marker="tools/build_dungeon_field_review_batch.py")
SCRIPT = Path(ROOT) / "tools/build_dungeon_field_review_batch.py" if ROOT else None
pytestmark = pytest.mark.skipif(ROOT is None, reason=REPO_ONLY_REASON)


def load_builder():
    assert SCRIPT is not None
    spec = importlib.util.spec_from_file_location("dungeon_field_review", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dungeon_field_review_batch_is_partitioned_and_complete():
    rows, summary = load_builder().build()
    assert rows
    assert len(rows) == len({row["check_id"] for row in rows})
    assert {row["category"] for row in rows} == {
        "unique_dungeon_pickup", "unique_field_pickup"}
    assert all(row["review_status"] in {
        "trusted", "audited_one_family", "remaining_unreviewed"} for row in rows)
    assert sum(group["total"] for group in summary["by_category"].values()) == len(rows)
    for group in summary["by_category"].values():
        assert group["total"] == group["trusted"] + group["held"]
        assert group["held"] == group["audited_one_family"] + group["remaining_unreviewed"]
        assert group["conflicted"] == 0


def test_dungeon_field_review_batch_generated_files_are_current():
    builder = load_builder()
    rows, summary = builder.build()
    assert builder.OUT_PATH.read_text(encoding="utf-8") == builder.render_tsv(rows)
    import json
    assert json.loads(builder.SUMMARY_PATH.read_text(encoding="utf-8")) == summary
