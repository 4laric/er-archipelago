"""The development channel may omit the private icon sheet; stable packaging never may."""
import os
import sys
import unittest

import pytest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
ROOT = _FOUND


def _pack_release():
    if _FOUND is None:
        raise unittest.SkipTest(REPO_ONLY_REASON)
    sys.path.insert(0, os.path.join(_FOUND, "tools"))
    import pack_release as _pr
    return _pr


def _minimal_stage(tmp_path):
    me3 = tmp_path / "me3"
    me3.mkdir()
    (me3 / "eldenring_archipelago.dll").write_bytes(b"x" * 1024)
    (me3 / "ap.me3").write_text("loader", encoding="ascii")
    return tmp_path


def test_stable_bundle_still_requires_the_flower_icon(tmp_path):
    pr = _pack_release()
    with pytest.raises(SystemExit):
        pr.gate_stage(str(_minimal_stage(tmp_path)), unofficial=False)


def test_development_bundle_can_explicitly_omit_the_flower_icon(tmp_path):
    pr = _pack_release()
    pr.WARNINGS.clear()
    stage = _minimal_stage(tmp_path)
    pr.gate_stage(str(stage), unofficial=True, allow_missing_ap_icon=True)
    marker = stage / "DEVELOPMENT-BUILD-NO-AP-ICON.txt"
    assert marker.is_file()
    assert "Telescope" in marker.read_text(encoding="ascii")
    assert any("intentionally omitted" in warning for warning in pr.WARNINGS)


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
def test_main_publishes_a_named_moving_dev_prerelease():
    from pathlib import Path
    root = Path(_FOUND)
    workflow = (root / ".github/workflows/er-release.yaml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "--allow-missing-ap-icon" in workflow
    assert "git tag -f dev" in workflow
    assert "gh release upload dev" in workflow
    assert "ER-Archipelago-dev.zip" in workflow
