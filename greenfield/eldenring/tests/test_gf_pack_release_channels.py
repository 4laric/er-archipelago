"""Stable bundles ship authenticated Flower atlases; dev bundles may omit them."""
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


def test_stable_bundle_requires_the_packaged_installer_and_assets(tmp_path):
    pr = _pack_release()
    with pytest.raises(SystemExit):
        pr.gate_stage(str(_minimal_stage(tmp_path)), unofficial=False)


def test_unofficial_channel_accepts_installer_without_release_assets(tmp_path):
    pr = _pack_release()
    pr.WARNINGS.clear()
    stage = _minimal_stage(tmp_path)
    me3 = stage / "me3"
    (me3 / "install-ap-flower.ps1").write_text("# installer", encoding="ascii")
    (me3 / "install_ap_flower.py").write_text("# installer", encoding="ascii")
    pr.gate_stage(str(stage), unofficial=True)
    assert (me3 / "install-ap-flower.ps1").stat().st_size > 0


def test_a_generated_fromsoft_atlas_is_rejected(tmp_path):
    pr = _pack_release()
    stage = _minimal_stage(tmp_path)
    me3 = stage / "me3"
    (me3 / "install-ap-flower.ps1").write_text("# installer", encoding="ascii")
    (me3 / "install_ap_flower.py").write_text("# installer", encoding="ascii")
    sheet = me3 / "ap-package/menu/hi/01_common.tpf.dcx"
    sheet.parent.mkdir(parents=True)
    sheet.write_bytes(b"game data")
    with pytest.raises(SystemExit):
        pr.gate_stage(str(stage), unofficial=False)


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
def test_main_publishes_a_named_moving_dev_prerelease():
    from pathlib import Path
    root = Path(_FOUND)
    workflow = (root / ".github/workflows/er-release.yaml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "ICON_REPO_TOKEN" in workflow
    assert "me3/flower-package/menu" in workflow
    assert "git tag -f dev" in workflow
    assert "gh release upload dev" in workflow
    assert "ER-Archipelago-dev.zip" in workflow
