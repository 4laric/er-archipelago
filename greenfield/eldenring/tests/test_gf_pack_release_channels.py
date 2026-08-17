"""The development channel may omit the private icon sheet; stable packaging never may."""
from pathlib import Path

import pytest

from tools import pack_release

ROOT = Path(__file__).resolve().parents[3]


def _minimal_stage(tmp_path):
    me3 = tmp_path / "me3"
    me3.mkdir()
    (me3 / "eldenring_archipelago.dll").write_bytes(b"x" * 1024)
    (me3 / "ap.me3").write_text("loader", encoding="ascii")
    return tmp_path


def test_stable_bundle_still_requires_the_flower_icon(tmp_path):
    with pytest.raises(SystemExit):
        pack_release.gate_stage(str(_minimal_stage(tmp_path)), unofficial=False)


def test_development_bundle_can_explicitly_omit_the_flower_icon(tmp_path):
    pack_release.WARNINGS.clear()
    stage = _minimal_stage(tmp_path)
    pack_release.gate_stage(str(stage), unofficial=True, allow_missing_ap_icon=True)
    marker = stage / "DEVELOPMENT-BUILD-NO-AP-ICON.txt"
    assert marker.is_file()
    assert "Telescope" in marker.read_text(encoding="ascii")
    assert any("intentionally omitted" in warning for warning in pack_release.WARNINGS)


def test_main_publishes_a_named_moving_dev_prerelease():
    workflow = (ROOT / ".github/workflows/er-release.yaml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "--allow-missing-ap-icon" in workflow
    assert "git tag -f dev" in workflow
    assert "gh release upload dev" in workflow
    assert "ER-Archipelago-dev.zip" in workflow
