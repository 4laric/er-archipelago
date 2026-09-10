"""Package optional offline HTML tools separately from the playable release bundle."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ARCHIVE_NAME = "Optional-Offline-Tools.zip"
PAGES = (
    "er-options-wizard.html",
    "er-archipelago-check-browser.html",
    "er-archipelago-evidence-browser.html",
    "er-archipelago-questline-dag.html",
    "er-archipelago-region-second-opinion.html",
    "er-archipelago-desc-triage.html",
)
README = """OPTIONAL OFFLINE TOOLS

These HTML tools are optional. You do not need this archive to install or play.
This archive does not contain eldenring_archipelago.dll.

To play: download the versioned ER-Archipelago client bundle from the release.
To host/generate: download eldenring.apworld.

Extract this archive, then open an HTML file in your browser:
- er-options-wizard.html: create player settings (YAML).
- er-archipelago-check-browser.html: browse checks.
- er-archipelago-evidence-browser.html: inspect check evidence.
- er-archipelago-questline-dag.html: inspect questline dependencies.
- er-archipelago-region-second-opinion.html: review region assignments.
- er-archipelago-desc-triage.html: review check descriptions.

These tools describe the release they were downloaded with.
"""


def package(directory: Path) -> Path:
    # Validate the complete set before opening the destination.
    entries = {name: (directory / name).read_bytes() for name in PAGES}
    if any(not data.strip() for data in entries.values()):
        raise ValueError("An offline HTML tool is empty")
    entries["README.txt"] = README.encode("utf-8")
    output = directory / ARCHIVE_NAME
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    print(package(parser.parse_args().directory))
