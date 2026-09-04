"""The boss-reward review inventory stays complete and regenerated."""
import importlib.util
import json
from pathlib import Path

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(__file__, marker="tools/build_boss_reward_category_coverage.py")
ROOT = Path(_ROOT) if _ROOT is not None else None
if ROOT is None:
    import pytest
    pytest.skip(REPO_ONLY_REASON, allow_module_level=True)
TOOL = ROOT / "tools/build_boss_reward_category_coverage.py"
SPEC = importlib.util.spec_from_file_location("_boss_reward_category_coverage", TOOL)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(BUILDER)


def test_boss_reward_category_inventory_is_current_and_complete():
    committed = json.loads(BUILDER.OUTPUT.read_text(encoding="utf-8"))
    assert committed == BUILDER.build()
    categories = committed["categories"]
    assert categories["all_boss_reward_checks"]["total"] == 269
    assert categories["fixed_boss_drop"]["total"] == 237
    assert categories["remembrance"]["total"] == 25
    assert categories["great_rune"]["total"] == 7


def test_dlc_boss_guide_closes_one_coherent_remembrance_tail():
    remaining = set(json.loads(BUILDER.OUTPUT.read_text(encoding="utf-8"))
                    ["categories"]["remembrance"]["remaining_check_ids"])
    assert remaining == {7770655}
