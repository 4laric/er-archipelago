#!/usr/bin/env python3
"""Make a staged me3 profile agree with the package directories beside it.

The repository's development profile names ``ap-package`` because local builds generate that
directory from the player's game. Release bundles instead carry authenticated assets under
``flower-package``. Preview bundles can carry neither. This module is the one packaging-time
translation point, shared by the Windows and CI packagers, and it validates the finished stage.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
import tomllib


class ProfileError(ValueError):
    """The staged profile cannot be made portable without guessing."""


_TABLE_HEADER = re.compile(r"^\s*\[\[?[A-Za-z0-9_.-]+\]?\]\s*(?:#.*)?$")
_TEMPLATE_PACKAGE_NAMES = {"ap-package", "flower-package"}


def _load(profile_path: Path) -> dict:
    try:
        text = profile_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ProfileError(f"could not read {profile_path}: {exc}") from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"invalid TOML in {profile_path}: {exc}") from exc


def _package_tables(document: dict, profile_path: Path) -> list[dict]:
    packages = document.get("packages", [])
    if not isinstance(packages, list) or any(not isinstance(row, dict) for row in packages):
        raise ProfileError(f"{profile_path} has an invalid [[packages]] shape")
    return packages


def _replace_template_package(profile_path: Path, package_name: str | None) -> None:
    document = _load(profile_path)
    packages = _package_tables(document, profile_path)
    if len(packages) != 1:
        raise ProfileError(
            f"{profile_path} must contain exactly one template [[packages]] table; found {len(packages)}"
        )
    if set(packages[0]) != {"path"}:
        raise ProfileError(
            f"{profile_path} template [[packages]] table has unsupported keys: "
            f"{', '.join(sorted(packages[0]))}"
        )
    old_name = packages[0]["path"]
    if old_name not in _TEMPLATE_PACKAGE_NAMES:
        raise ProfileError(f"{profile_path} names unexpected template package {old_name!r}")

    text = profile_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "[[packages]]":
            index += 1
            continue
        start = index
        index += 1
        while index < len(lines) and not _TABLE_HEADER.match(lines[index].rstrip("\r\n")):
            index += 1
        spans.append((start, index))
    if len(spans) != 1:
        raise ProfileError(
            f"{profile_path} text must contain exactly one [[packages]] block; found {len(spans)}"
        )

    newline = "\r\n" if "\r\n" in text else "\n"
    replacement = ""
    if package_name is not None:
        if not package_name or "/" in package_name or "\\" in package_name:
            raise ProfileError(f"release package must be one directory name, got {package_name!r}")
        replacement = f"[[packages]]{newline}path = '{package_name}'{newline}{newline}"
    start, end = spans[0]
    rewritten = "".join(lines[:start]) + replacement + "".join(lines[end:])
    try:
        with profile_path.open("w", encoding="utf-8", newline="") as stream:
            stream.write(rewritten)
    except OSError as exc:
        raise ProfileError(f"could not write {profile_path}: {exc}") from exc


def validate_release_profile(
    profile_path: Path, package_root: Path, expected_package: str | None
) -> list[str]:
    """Require every package path in the staged profile to be portable and present."""
    packages = _package_tables(_load(profile_path), profile_path)
    paths: list[str] = []
    for index, package in enumerate(packages, 1):
        value = package.get("path")
        if not isinstance(value, str) or not value:
            raise ProfileError(f"{profile_path} package #{index} has no string path")
        if "\\" in value:
            raise ProfileError(f"{profile_path} package path must use portable '/' separators: {value!r}")
        relative = PurePosixPath(value)
        if relative.is_absolute() or PureWindowsPath(value).is_absolute() or ".." in relative.parts:
            raise ProfileError(f"{profile_path} package path must stay inside me3/: {value!r}")
        normalized = relative.as_posix()
        candidate = package_root.joinpath(*relative.parts)
        if not candidate.is_dir():
            raise ProfileError(
                f"{profile_path} references missing package directory {normalized!r} beside the profile"
            )
        paths.append(normalized)

    expected = [] if expected_package is None else [expected_package]
    if paths != expected:
        raise ProfileError(
            f"{profile_path} package paths are {paths!r}; finished bundle requires {expected!r}"
        )
    return paths


def configure_release_profile(
    profile_path: Path, package_root: Path, package_name: str | None
) -> list[str]:
    """Translate the local template and immediately validate the staged result."""
    _replace_template_package(profile_path, package_name)
    return validate_release_profile(profile_path, package_root, package_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument(
        "--package",
        default=None,
        help="staged package directory; omit to remove [[packages]] for an asset-free preview",
    )
    args = parser.parse_args()
    try:
        paths = configure_release_profile(args.profile, args.profile.parent, args.package)
    except ProfileError as exc:
        print(f"package_me3_profile: {exc}", file=sys.stderr)
        return 1
    rendered = paths[0] if paths else "<none>"
    print(f"package_me3_profile: {args.profile} -> {rendered} (validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
