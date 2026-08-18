#!/usr/bin/env python3
"""Install packaged AP Flower atlases into Matt's randomizer output."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sys, tempfile
from pathlib import Path
from typing import Any

MARKER = ".er-ap-flower.json"
BACKUPS = ".er-ap-flower-backups"
EXPECTED = (Path("menu/hi/01_common.tpf.dcx"), Path("menu/low/01_common.tpf.dcx"))
DATA_MARKERS = ("regulation.bin", "event", "msg", "script", "map", "param")

class InstallError(RuntimeError): pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def safe_relative(value: object) -> Path:
    path = Path(str(value))
    if path.is_absolute() or ".." in path.parts:
        raise InstallError(f"unsafe manifest path: {value}")
    return path

def load_package(root: Path) -> tuple[dict[str, Any], dict[Path, dict[str, Any]]]:
    path = root / "manifest.json"
    if not path.is_file():
        raise InstallError("Release does not include AP Flower assets")
    try: manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc: raise InstallError(f"invalid manifest: {exc}") from exc
    if manifest.get("schema") != 1 or not isinstance(manifest.get("asset_version"), str):
        raise InstallError("manifest needs schema 1 and asset_version")
    records = {safe_relative(row.get("path")): row for row in manifest.get("files", [])
               if isinstance(row, dict)}
    if set(records) != set(EXPECTED) or len(manifest.get("files", [])) != 2:
        raise InstallError("manifest must list exactly the hi and low 01_common atlases")
    for relative, row in records.items():
        source, size, digest = root / relative, row.get("size"), str(row.get("sha256", "")).lower()
        if not source.is_file() or not isinstance(size, int) or size < 1 or len(digest) != 64:
            raise InstallError(f"missing or invalid packaged asset: {relative}")
        if source.stat().st_size != size or sha256(source) != digest:
            raise InstallError(f"packaged asset failed size/hash validation: {relative}")
    return manifest, records

def fingerprint(path: Path) -> tuple[int, str] | None:
    try: names = {p.name.lower() for p in path.iterdir()}
    except OSError: return None
    opts = sorted(n for n in names if n.endswith(".randomizeopt"))
    if opts: return 2, opts[0]
    markers = sorted(n for n in DATA_MARKERS if n in names)
    return (1, ", ".join(markers)) if markers else None

def resolve_destination(starts: list[Path], explicit: Path | None = None,
                        max_parents: int = 5) -> tuple[Path, str]:
    if explicit is not None: return explicit.resolve(), "explicit --destination"
    found: dict[Path, tuple[int, int, str]] = {}
    for start in starts:
        start = start.resolve()
        for distance, candidate in enumerate((start, *list(start.parents)[:max_parents])):
            hit = fingerprint(candidate)
            if hit:
                score = (hit[0], -distance, hit[1])
                if candidate not in found or score > found[candidate]: found[candidate] = score
    if found:
        best_score = max(value[:2] for value in found.values())
        best = [(path, value[2]) for path, value in found.items() if value[:2] == best_score]
        if len(best) != 1:
            raise InstallError("ambiguous Matt roots: " + ", ".join(str(x[0]) for x in best)
                               + "; pass --destination")
        return best[0][0], f"Matt/data-mod fingerprint: {best[0][1]}"
    raise InstallError("could not locate Matt's randomizer output; pass --destination")

def prompt_destination() -> Path:
    if not sys.stdin.isatty():
        raise InstallError("could not locate Matt's randomizer output; rerun with --destination PATH")
    print("Could not automatically find Matt's randomizer output folder.")
    value = input("Enter the folder containing the .randomizeopt/regulation.bin: ").strip().strip('"')
    if not value:
        raise InstallError("no destination supplied")
    destination = Path(value).expanduser().resolve()
    if fingerprint(destination) is None:
        raise InstallError(f"that folder does not look like Matt's randomizer output: {destination}")
    return destination

def read_marker(destination: Path) -> dict[str, Any] | None:
    path = destination / MARKER
    if not path.is_file(): return None
    try: record = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc: raise InstallError(f"invalid ownership marker: {exc}") from exc
    if record.get("schema") != 1 or record.get("destination") != str(destination.resolve()):
        raise InstallError("ownership marker does not match this destination")
    return record

def owned_hashes(marker: dict[str, Any] | None) -> dict[Path, str]:
    if not marker: return {}
    return {safe_relative(row["path"]): str(row["sha256"]).lower()
            for row in marker.get("files", []) if isinstance(row, dict)}

def install(package: Path, destination: Path, replace_existing: bool = False,
            fail_after: int | None = None) -> str:
    manifest, records = load_package(package)
    destination = destination.resolve()
    marker = read_marker(destination)
    owned = owned_hashes(marker)
    conflicts = [p for p in EXPECTED if (destination / p).exists() and p not in owned]
    if conflicts and not replace_existing:
        raise InstallError("Existing UI atlas conflict: " + ", ".join(map(str, conflicts)))
    desired = {p: str(records[p]["sha256"]).lower() for p in EXPECTED}
    if marker and all((destination/p).is_file() and sha256(destination/p) == h for p, h in desired.items()):
        return "already installed"
    destination.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".er-ap-flower-stage-", dir=destination))
    rollback, committed = stage / "rollback", []
    backups = list(marker.get("backups", [])) if marker else []
    try:
        for relative in EXPECTED:
            staged = stage / "new" / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package / relative, staged)
            if staged.stat().st_size != records[relative]["size"] or sha256(staged) != desired[relative]:
                raise InstallError(f"staged asset failed validation: {relative}")
        for relative in EXPECTED:
            target = destination / relative
            if target.is_file():
                old = rollback / relative; old.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(target, old)
                if relative in conflicts:
                    backup = destination / BACKUPS / relative; backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                    backups.append({"path": str(relative), "backup": str(Path(BACKUPS)/relative),
                                    "sha256": sha256(target)})
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / "new" / relative, target); committed.append(relative)
            if fail_after is not None and len(committed) >= fail_after: raise InstallError("simulated failure")
        record = {"schema": 1, "asset_version": manifest["asset_version"],
                  "destination": str(destination),
                  "files": [{"path": str(p), "sha256": desired[p]} for p in EXPECTED],
                  "backups": backups}
        staged_marker = stage / "marker.json"
        staged_marker.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        os.replace(staged_marker, destination / MARKER)
        return "installed; restart Elden Ring"
    except Exception:
        for relative in reversed(committed):
            target, old = destination / relative, rollback / relative
            if old.is_file(): os.replace(old, target)
            else: target.unlink(missing_ok=True)
        raise
    finally: shutil.rmtree(stage, ignore_errors=True)

def uninstall(destination: Path) -> list[str]:
    destination = destination.resolve(); marker = read_marker(destination)
    if marker is None: return ["not installed"]
    messages = []
    for relative, expected in owned_hashes(marker).items():
        target = destination / relative
        if target.is_file() and sha256(target) == expected: target.unlink()
        elif target.exists(): messages.append(f"retained modified file: {relative}")
    for row in marker.get("backups", []):
        relative, backup = safe_relative(row["path"]), safe_relative(row["backup"])
        source, target = destination / backup, destination / relative
        if source.is_file(): target.parent.mkdir(parents=True, exist_ok=True); os.replace(source, target); messages.append(f"restored backup: {relative}")
    (destination / MARKER).unlink()
    return messages or ["uninstalled"]

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path); p.add_argument("--destination", type=Path)
    p.add_argument("--start", action="append", type=Path, default=[])
    p.add_argument("--replace-existing", action="store_true"); p.add_argument("--uninstall", action="store_true")
    args = p.parse_args(argv); script_dir = Path(__file__).resolve().parent
    try:
        try:
            destination, reason = resolve_destination(args.start or [Path.cwd(), script_dir], args.destination)
        except InstallError:
            if args.destination is not None:
                raise
            destination, reason = prompt_destination(), "path supplied by user"
        print(f"AP Flower destination: {destination} ({reason})")
        print("; ".join(uninstall(destination)) if args.uninstall else
              install((args.package or script_dir/"flower-package").resolve(), destination, args.replace_existing))
        return 0
    except InstallError as exc: print(f"install_ap_flower: {exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
