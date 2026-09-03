"""Stable bundles ship authenticated Flower atlases; dev bundles may omit them."""
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tomllib
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


def _profile(package=None):
    package_block = "" if package is None else f"[[packages]]\npath = '{package}'\n\n"
    return (
        'profileVersion = "v1"\n\n'
        "[[supports]]\n"
        'game = "eldenring"\n\n'
        f"{package_block}"
        "[[natives]]\n"
        "path = 'eldenring_archipelago.dll'\n"
    )


def _minimal_stage(tmp_path, package=None):
    me3 = tmp_path / "me3"
    me3.mkdir()
    (me3 / "eldenring_archipelago.dll").write_bytes(b"x" * 1024)
    (me3 / "ap.me3").write_text(_profile(package), encoding="ascii")
    return tmp_path


def _installers(me3):
    (me3 / "install-ap-flower.ps1").write_text("# installer", encoding="ascii")
    (me3 / "install_ap_flower.py").write_text("# installer", encoding="ascii")


def _flower_package(pr, me3):
    package = me3 / "flower-package"
    for relative in ("menu/hi/01_common.tpf.dcx", "menu/low/01_common.tpf.dcx"):
        sheet = package / relative
        sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.write_bytes((relative + " game data").encode("ascii"))
    pr.flower_manifest(str(package), "0.4.9")
    return package


def _stage_args(tmp_path, me3, unofficial):
    apworld = tmp_path / "eldenring.apworld"
    apworld.write_bytes(b"apworld")
    return SimpleNamespace(
        apworld=str(apworld), me3=str(me3), version="0.4.9", unofficial=unofficial
    )


def test_stable_bundle_requires_the_packaged_installer_and_assets(tmp_path):
    pr = _pack_release()
    with pytest.raises(SystemExit):
        pr.gate_stage(str(_minimal_stage(tmp_path)), unofficial=False)


def test_unofficial_channel_accepts_installer_without_release_assets(tmp_path):
    pr = _pack_release()
    pr.WARNINGS.clear()
    stage = _minimal_stage(tmp_path)
    me3 = stage / "me3"
    _installers(me3)
    pr.gate_stage(str(stage), unofficial=True)
    assert (me3 / "install-ap-flower.ps1").stat().st_size > 0


def test_stable_stage_retargets_profile_to_the_packaged_flower(tmp_path, monkeypatch):
    pr = _pack_release()
    pr.WARNINGS.clear()
    source = tmp_path / "source"
    source.mkdir()
    me3 = _minimal_stage(source, package="ap-package") / "me3"
    _flower_package(pr, me3)
    monkeypatch.setattr(pr, "DOCS", [])
    monkeypatch.setattr(pr, "REL", str(tmp_path / "no-release-docs"))

    stage = tmp_path / "stable-stage"
    pr.stage(_stage_args(tmp_path, me3, unofficial=False), str(stage))

    profile = tomllib.loads((stage / "me3/ap.me3").read_text(encoding="utf-8"))
    assert [row["path"] for row in profile["packages"]] == ["flower-package"]
    assert not (stage / "me3/ap-package").exists()
    pr.gate_stage(str(stage), unofficial=False)


def test_unofficial_stage_removes_a_package_reference_when_assets_are_absent(
    tmp_path, monkeypatch
):
    pr = _pack_release()
    pr.WARNINGS.clear()
    source = tmp_path / "source"
    source.mkdir()
    me3 = _minimal_stage(source, package="ap-package") / "me3"
    monkeypatch.setattr(pr, "DOCS", [])
    monkeypatch.setattr(pr, "REL", str(tmp_path / "no-release-docs"))

    stage = tmp_path / "unofficial-stage"
    pr.stage(_stage_args(tmp_path, me3, unofficial=True), str(stage))

    profile = tomllib.loads((stage / "me3/ap.me3").read_text(encoding="utf-8"))
    assert "packages" not in profile
    pr.gate_stage(str(stage), unofficial=True)


def test_finished_stage_rejects_the_exact_ap_to_flower_name_mismatch(tmp_path):
    pr = _pack_release()
    stage = _minimal_stage(tmp_path, package="ap-package")
    me3 = stage / "me3"
    _installers(me3)
    _flower_package(pr, me3)

    with pytest.raises(SystemExit):
        pr.gate_stage(str(stage), unofficial=False)


def test_a_generated_fromsoft_atlas_is_rejected(tmp_path):
    pr = _pack_release()
    stage = _minimal_stage(tmp_path, package="flower-package")
    me3 = stage / "me3"
    _installers(me3)
    _flower_package(pr, me3)
    sheet = me3 / "ap-package/menu/hi/01_common.tpf.dcx"
    sheet.parent.mkdir(parents=True)
    sheet.write_bytes(b"game data")
    with pytest.raises(SystemExit):
        pr.gate_stage(str(stage), unofficial=False)


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
def test_main_publishes_a_named_moving_dev_prerelease():
    root = Path(_FOUND)
    workflow = (root / ".github/workflows/er-release.yaml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "ICON_REPO_TOKEN" in workflow
    assert "me3/flower-package/menu" in workflow
    assert "git tag -f dev" in workflow
    assert "gh release upload dev" in workflow
    assert "ER-Archipelago-dev.zip" in workflow


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
def test_tag_recovery_builds_the_immutable_pair_and_keeps_release_assets():
    """A stale-pin override may waive only the comparison with moving client main.

    Recovery still checks out the named immutable tag, builds that tag's gitlink, stages Flower,
    and attaches to the named release. Otherwise the tempting workaround is an unofficial dev ZIP
    whose identity and assets differ from the release it claims to repair.
    """
    workflow = (Path(_FOUND) / ".github/workflows/er-release.yaml").read_text(encoding="utf-8")
    assert "tag:" in workflow
    assert "allow_stale_pin:" in workflow
    assert "ref: ${{ github.event.inputs.tag || github.ref }}" in workflow
    assert "ALLOW_STALE_PIN: ${{ github.event.inputs.allow_stale_pin == 'true' && '1' || '0' }}" in workflow
    assert "(github.ref != 'refs/heads/main' || github.event.inputs.tag != '')" in workflow
    assert "tag_name: ${{ github.event.inputs.tag || github.ref_name }}" in workflow
    assert "if: github.ref == 'refs/heads/main' && github.event.inputs.tag == ''" in workflow


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
def test_both_release_packagers_share_the_profile_path_gate():
    root = Path(_FOUND)
    powershell = (root / "package_release.ps1").read_text(encoding="utf-8")
    portable = (root / "tools/pack_release.py").read_text(encoding="utf-8")
    assert "package_me3_profile.py" in powershell
    assert "configure_release_profile" in portable
    assert "validate_release_profile" in portable


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
def test_obsolete_poptracker_is_not_a_live_setup_or_package_path():
    root = Path(_FOUND)
    assert not (root / "poptracker").exists()

    # The offline audit pages still need their original SVG/calibration inputs, but those are
    # repository tooling rather than a player tracker pack.
    maps = root / "greenfield/maps"
    assert (maps / "lands_between_map.svg").is_file()
    assert (maps / "land_of_shadow_map.svg").is_file()
    assert (maps / "map_calibration.json").is_file()
    assert (maps / "map_calibration_dlc.json").is_file()

    package_script = (root / "package_release.ps1").read_text(encoding="utf-8")
    player_guide = (root / "release/PLAYER-GUIDE.md").read_text(encoding="utf-8")
    assert "PopTracker" not in package_script
    assert "Press **F6**" in player_guide
