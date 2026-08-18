#!/usr/bin/env python3
"""Build/install the AP flower from the player's own Elden Ring files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

WITCHY_VERSION = "3.0.1.0"
WITCHY_URL = ("https://github.com/ividyon/WitchyBND/releases/download/"
              f"{WITCHY_VERSION}/WitchyBND-{WITCHY_VERSION}-win-x64.zip")
WITCHY_SHA256 = "a3e6b2a0f7eac13f5e83b6602a1149322439c0662baa140ecdd84be28af50364"
MARKER = ".er-ap-flower.json"
OUTPUTS = (Path("menu/hi/01_common.tpf.dcx"), Path("menu/low/01_common.tpf.dcx"))
DATA_MARKERS = ("regulation.bin", "event", "msg", "script", "map", "param")
DFLT_FIELDS = {"dfltUnk04": "69632", "dfltUnk10": "68", "dfltUnk14": "76",
               "dfltUnk30": "9", "dfltUnk38": "21"}


class InstallError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise InstallError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_game_dir() -> Path:
    if os.name == "nt":
        return Path(r"C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game")
    candidates = [Path.home() / ".steam/steam/steamapps/common/ELDEN RING/Game",
                  Path.home() / ".local/share/Steam/steamapps/common/ELDEN RING/Game"]
    return next((path for path in candidates if path.is_dir()), candidates[0])


def looks_like_data_mod(path: Path) -> bool:
    try:
        names = {entry.name.lower() for entry in path.iterdir()}
    except OSError:
        return False
    return (any(name.endswith(".randomizeopt") for name in names)
            or any(marker in names for marker in DATA_MARKERS))


def detect_destination(script_dir: Path, cwd: Path) -> Path:
    """Prefer a nearby Matt/data-mod root; otherwise use the bundled me3 package."""
    seen: set[Path] = set()
    for start in (cwd, script_dir):
        for candidate in (start, *list(start.parents)[:3]):
            candidate = candidate.resolve()
            if candidate not in seen and looks_like_data_mod(candidate):
                return candidate
            seen.add(candidate)
    return script_dir / "ap-package"


def remove_installed(root: Path) -> bool:
    marker = root / MARKER
    if not marker.is_file():
        return False
    record = json.loads(marker.read_text(encoding="utf-8-sig"))
    for relative in record.get("files", []):
        path = root / relative
        if path.is_file():
            path.unlink()
    marker.unlink()
    return True


def get_witchy(explicit: Path | None, cache: Path) -> Path:
    if explicit:
        if not explicit.is_file():
            fail(f"--witchy does not exist: {explicit}")
        return explicit.resolve()
    root, exe = cache / f"WitchyBND-{WITCHY_VERSION}", cache / f"WitchyBND-{WITCHY_VERSION}/WitchyBND.exe"
    if exe.is_file():
        return exe
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as stream:
        archive = Path(stream.name)
    try:
        print(f"Downloading pinned WitchyBND {WITCHY_VERSION} ...")
        urllib.request.urlretrieve(WITCHY_URL, archive)
        actual = sha256(archive)
        if actual != WITCHY_SHA256:
            fail(f"WitchyBND archive hash mismatch (got {actual}); refusing to execute it")
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(root)
        found = next(root.rglob("WitchyBND.exe"), None)
        if found is None:
            fail("verified WitchyBND archive contained no WitchyBND.exe")
        if found != exe:
            for child in found.parent.iterdir():
                shutil.move(str(child), root / child.name)
        if not exe.is_file():
            fail(f"could not stage WitchyBND.exe under {root}")
        return exe
    finally:
        archive.unlink(missing_ok=True)


class Witchy:
    def __init__(self, exe: Path, oodle: Path, wine: str | None):
        self.exe, self.wine = exe, wine
        self.env = os.environ.copy()
        self.env["PATH"] = str(oodle.parent) + os.pathsep + self.env.get("PATH", "")
        if os.name != "nt":
            if not wine:
                fail("WitchyBND needs Wine on Linux; install wine or pass --wine /path/to/wine")
            # Wine does not reliably translate its Unix PATH for LoadLibrary. This is a local cache
            # copy of the player's DLL, never a distributed artifact.
            shutil.copy2(oodle, exe.parent / oodle.name)

    def path_arg(self, path: Path) -> str:
        if os.name == "nt":
            return str(path)
        winepath = shutil.which("winepath")
        if not winepath:
            return str(path)
        result = subprocess.run([winepath, "-w", str(path)], text=True, capture_output=True)
        return result.stdout.strip() if result.returncode == 0 else str(path)

    def run(self, args: list[str], purpose: str) -> None:
        command = ([str(self.exe)] if os.name == "nt" else [self.wine, str(self.exe)])
        command += ["-s", *(self.path_arg(Path(arg)) if Path(arg).is_absolute() else arg for arg in args)]
        if subprocess.run(command, env=self.env).returncode:
            fail(f"WitchyBND failed during {purpose}")

    def expand(self, source: Path, folder: Path) -> Path:
        folder.mkdir(parents=True)
        local = folder / source.name
        shutil.copy2(source, local)
        self.run(["-u", str(local)], f"unpack of {source}")
        prefix = local.stem.split(".")[0]
        dirs = [p for p in folder.iterdir() if p.is_dir() and p.name.startswith(prefix)]
        if len(dirs) != 1:
            fail(f"expected one unpacked directory beside {local}, found {len(dirs)}")
        return dirs[0]


def find_flower_rect(root: Path) -> tuple[str, int, int, int, int]:
    hits = []
    for file in root.rglob("*.xml"):
        try:
            nodes = ET.parse(file).getroot().iter()
        except ET.ParseError:
            continue
        for node in nodes:
            attrs, name = node.attrib, node.attrib.get("name", "")
            number = name.removeprefix("ItemIcon_").lstrip("0")
            width, height = attrs.get("width", attrs.get("w")), attrs.get("height", attrs.get("h"))
            if name.startswith("ItemIcon_") and number == "92" and attrs.get("x") is not None and attrs.get("y") is not None and width and height:
                hits.append((file.stem + ".dds", int(attrs["x"]), int(attrs["y"]), int(width), int(height)))
    if len(hits) != 1:
        fail(f"expected one ItemIcon 92 layout entry, found {len(hits)}")
    return hits[0]


def write_blocks(dds: Path, rect: tuple[str, int, int, int, int], payload: bytes) -> None:
    head = dds.read_bytes()[:148]
    if len(head) < 148 or head[:4] != b"DDS ":
        fail(f"{dds} is not a complete DDS")
    height, width, mips = struct.unpack_from("<III", head, 12)
    fourcc, dxgi = head[84:88], struct.unpack_from("<I", head, 128)[0]
    if fourcc != b"DX10" or dxgi not in (98, 99) or mips != 1:
        fail(f"expected one-mip BC7 DX10 atlas, found fourcc={fourcc!r} dxgi={dxgi} mips={mips}")
    _atlas, x, y, w, h = rect
    if any(n <= 0 or n % 4 for n in (x, y, w, h)) or x + w > width or y + h > height:
        fail("flower rect is not positive, block aligned, and inside the atlas")
    row_bytes, rows, stride = w // 4 * 16, h // 4, width // 4 * 16
    if len(payload) != row_bytes * rows:
        fail("payload size does not match layout rect")
    with dds.open("r+b") as stream:
        for row in range(rows):
            stream.seek(148 + (y // 4 + row) * stride + x // 4 * 16)
            stream.write(payload[row * row_bytes:(row + 1) * row_bytes])


def set_dflt(root: Path) -> None:
    hits = []
    for file in root.rglob("*.xml"):
        try:
            tree = ET.parse(file)
        except ET.ParseError:
            continue
        if tree.getroot().find("compression") is not None:
            hits.append((file, tree))
    if len(hits) != 1:
        fail(f"expected one Witchy compression manifest, found {len(hits)}")
    file, tree = hits[0]
    root_node = tree.getroot()
    root_node.find("compression").text = "DCX_DFLT"
    for name in ("compressionLevel", "oodleCompressorType"):
        old = root_node.find(name)
        if old is not None:
            root_node.remove(old)
    for name, value in DFLT_FIELDS.items():
        child = root_node.find(name)
        if child is None:
            child = ET.SubElement(root_node, name)
        child.text = value
    tree.write(file, encoding="utf-8", xml_declaration=True)


def install(args: argparse.Namespace) -> None:
    script_dir = Path(__file__).resolve().parent
    destination = (args.destination or detect_destination(script_dir, Path.cwd())).resolve()
    if args.uninstall:
        removed = remove_installed(destination)
        print(("Removed AP flower override from " if removed else "No AP flower marker under ") + str(destination))
        return
    game = args.game_dir.resolve()
    payload = (args.payload or next((p for p in (script_dir / "ap_flower_160.bc7", script_dir / "ap_icon_src/ap_flower_160.bc7") if p.is_file()), script_dir / "ap_flower_160.bc7")).resolve()
    menu = game / "menu"
    oodle = next(iter(sorted(game.glob("oo2core*_win64.dll"))), None)
    if not menu.is_dir() or oodle is None:
        fail(f"--game-dir must contain Elden Ring's menu and oo2core DLL: {game}")
    if not payload.is_file() or payload.stat().st_size != 25_600:
        fail(f"BC7 payload is missing or not exactly 25,600 bytes: {payload}")
    cache = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / "ERArchipelago/tools"
    witchy = Witchy(get_witchy(args.witchy, cache), oodle, args.wine)
    with tempfile.TemporaryDirectory(prefix="er-ap-flower-") as tmp:
        work, staged = Path(tmp), Path(tmp) / "output"
        for bundle in ("hi", "low"):
            source, layout = menu / bundle / "01_common.tpf.dcx", menu / bundle / "01_common.sblytbnd.dcx"
            if not source.is_file() or not layout.is_file():
                fail(f"missing installed atlas or layout under {menu / bundle}")
            rect = find_flower_rect(witchy.expand(layout, work / f"{bundle}-layout"))
            tpf_root = witchy.expand(source, work / bundle)
            dds = list(tpf_root.rglob(rect[0]))
            if len(dds) != 1:
                fail(f"layout names {rect[0]}, TPF yielded {len(dds)} matches")
            write_blocks(dds[0], rect, payload.read_bytes())
            set_dflt(tpf_root)
            witchy.run([str(tpf_root)], f"DFLT repack of {bundle} atlas")
            built = tpf_root.parent / "01_common.tpf.dcx"
            if not built.is_file() or b"DCP\0DFLT" not in built.read_bytes()[:192]:
                fail(f"Witchy produced no valid DFLT output at {built}")
            target = staged / "menu" / bundle / built.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(built, target)
        owned = (destination / MARKER).is_file()
        for relative in OUTPUTS:
            if (destination / relative).exists() and not owned and not args.force:
                fail(f"{destination / relative} exists without an AP marker; pass --force to replace it")
        if owned:
            remove_installed(destination)
        for relative in OUTPUTS:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged / relative, target)
        destination.mkdir(parents=True, exist_ok=True)
        record = {"schema": 1, "generatedBy": "er-archipelago", "witchy": WITCHY_VERSION,
                  "payloadSha256": sha256(payload), "files": [p.as_posix() for p in OUTPUTS]}
        (destination / MARKER).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"AP flower override installed under {destination}")
    print("Restart Elden Ring to load the new menu atlas.")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game-dir", type=Path, default=default_game_dir())
    ap.add_argument("--destination", type=Path)
    ap.add_argument("--payload", type=Path)
    ap.add_argument("--witchy", type=Path)
    ap.add_argument("--wine", default=None if os.name == "nt" else shutil.which("wine"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    return ap


if __name__ == "__main__":
    try:
        install(parser().parse_args())
    except (InstallError, OSError, subprocess.SubprocessError) as error:
        print(f"install_ap_flower: {error}", file=sys.stderr)
        raise SystemExit(1)
