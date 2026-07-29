#!/usr/bin/env python3
"""Composite the Archipelago flower into Elden Ring's SB_Icon atlas at a given icon id.

REWRITTEN 2026-07-29. The original was lost (RELEASE-CHECKLIST-v0.1.md, 2026-07-04: "the generator
build_ap_icon.py is lost"), and the flower has shipped as a vanilla Telescope ever since -- which a
player finally reported as "telescope icon but i dont know what ap item it is". See
docs/AP-ICON-PIPELINE.md for what may and may not be committed.

WHY THIS IS A WITCHYBND WRAPPER AND NOT A FORMAT IMPLEMENTATION
    menu\\{hi,low}\\01_common.tpf.dcx is DCX/**KRAK** -- Oodle Kraken. Verified on the real files:
    magic DCX\\0 ... DCP\\0 KRAK. Oodle is proprietary and Windows-side; WitchyBND already carries it.
    So witchy does the (de)compression and this script does only the pixels.

🛑 THIS SCRIPT HAS NEVER BEEN RUN. It was written in a Linux sandbox with no Oodle, no witchy, no
texconv and no way to open the input. Every path here is UNVERIFIED. That is exactly why --probe
exists and why it is the default: run it FIRST, read what it found, and only then let it write.

    python tools/build_ap_icon.py --probe --menu "<game>\\menu"
    python tools/build_ap_icon.py --icon01 --icon-id 92 --bundles hi,low --menu "<game>\\menu"

🛑 --black-to-alpha is accepted and IGNORED by default, deliberately. build.ps1's inherited command
line passes it, but the committed art (tools/ap_icon_src/ap_flower.webp) already has a real alpha
channel -- keying transparency off black would punch holes in the dark parts of the petals. Pass
--force-black-to-alpha if you actually mean it.
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_ART = os.path.join(HERE, "ap_icon_src", "ap_flower.png")
SHEET = "01_common.tpf.dcx"


def die(msg):
    raise SystemExit("build_ap_icon: FATAL: " + msg)


def need_tool(name, hint):
    exe = shutil.which(name)
    if not exe:
        die("%s not on PATH. %s" % (name, hint))
    return exe


def unpack(witchy, src, workdir):
    """witchy -u <file> -> a sibling directory. Returns the unpacked dir."""
    os.makedirs(workdir, exist_ok=True)
    local = os.path.join(workdir, os.path.basename(src))
    shutil.copy2(src, local)
    r = subprocess.run([witchy, "-u", local], capture_output=True, text=True)
    if r.returncode != 0:
        die("witchybnd -u failed on %s (exit %d)\n%s%s" % (local, r.returncode, r.stdout, r.stderr))
    # witchy names the output after the file with dots -> dashes (AGENTS.md documents this shape
    # for MSBs: <name>-msb-dcx/). Do not guess it -- find the directory it actually created.
    made = [d for d in os.listdir(workdir)
            if os.path.isdir(os.path.join(workdir, d)) and d.startswith(os.path.basename(src).split(".")[0])]
    if len(made) != 1:
        die("expected exactly one unpacked directory in %s, found %r. Witchy's naming changed; "
            "fix this rather than guessing." % (workdir, made))
    return os.path.join(workdir, made[0])


def dds_files(unpacked):
    out = []
    for root, _dirs, files in os.walk(unpacked):
        for f in files:
            if f.lower().endswith(".dds"):
                out.append(os.path.join(root, f))
    return sorted(out)


def dds_size(path):
    """(width, height) from the DDS header. Header is fixed-layout: magic, size, flags, h, w."""
    import struct
    with open(path, "rb") as fh:
        head = fh.read(20)
    if len(head) < 20 or head[:4] != b"DDS ":
        return None
    height, width = struct.unpack_from("<II", head, 12)
    return (width, height)


def probe(menu, bundles, icon_id, cell, witchy, workdir):
    """Report what is actually in the atlas. WRITES NOTHING.

    The layout is the one thing this script must not assume: which SB_Icon sheet holds icon N, and
    at what cell size. Getting it wrong paints the flower over some unrelated item's icon and
    nothing errors. So: unpack, list every sheet with its real dimensions, and show the arithmetic.
    """
    print("PROBE -- no files will be written.\n")
    for b in bundles:
        src = os.path.join(menu, b, SHEET)
        if not os.path.isfile(src):
            die("no %s (looked for the atlas this tool edits)" % src)
        up = unpack(witchy, src, os.path.join(workdir, b))
        sheets = dds_files(up)
        if not sheets:
            die("unpacked %s but found no .dds inside. An empty result is a FAILURE, not a clean "
                "run -- witchy's output layout is not what this expects." % src)
        print("[%s] %s -> %d dds" % (b, src, len(sheets)))
        for p in sheets:
            wh = dds_size(p)
            name = os.path.basename(p)
            if not wh:
                print("    %-28s (no readable DDS header)" % name)
                continue
            w, h = wh
            fits = (w % cell == 0 and h % cell == 0)
            per = (w // cell) * (h // cell) if fits else 0
            print("    %-28s %5dx%-5d  cell %d -> %s" % (
                name, w, h, cell,
                ("%d icons/sheet (%dx%d grid)" % (per, w // cell, h // cell)) if fits
                else "NOT divisible by cell size"))
        print("\n  For --icon-id %d you now need to say which sheet and which cell. Read the grid\n"
              "  above, confirm against the game, and pass --sheet/--cell-index explicitly.\n"
              % icon_id)


def composite(art, sheet_png, cell, col, row, out_png, force_black_alpha):
    from PIL import Image
    src = Image.open(art).convert("RGBA")
    if force_black_alpha:
        px = src.load()
        for y in range(src.height):
            for x in range(src.width):
                r, g, b, a = px[x, y]
                if r < 8 and g < 8 and b < 8:
                    px[x, y] = (r, g, b, 0)
    # letterbox, never non-uniform scale: the art is 2034x2112 and cells are square
    box = src.copy()
    box.thumbnail((cell, cell), Image.LANCZOS)
    tile = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
    tile.paste(box, ((cell - box.width) // 2, (cell - box.height) // 2), box)

    sheet = Image.open(sheet_png).convert("RGBA")
    x, y = col * cell, row * cell
    if x + cell > sheet.width or y + cell > sheet.height:
        die("cell (%d,%d) at size %d falls outside the %dx%d sheet -- refusing to write outside the "
            "atlas." % (col, row, cell, sheet.width, sheet.height))
    # CLEAR the cell first. The flower is mostly transparent between its petals, so a plain
    # alpha-composite would leave the VANILLA icon (the Telescope) showing through the gaps -- a
    # flower with a telescope behind it, which is worse than either. Caught by running this against
    # a synthetic sheet: the target cell still read as background colour between the petals.
    sheet.paste((0, 0, 0, 0), (x, y, x + cell, y + cell))
    sheet.paste(tile, (x, y), tile)
    sheet.save(out_png, "PNG")
    return out_png


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--menu", required=True, help=r'the game\menu directory')
    ap.add_argument("--art", default=DEFAULT_ART)
    ap.add_argument("--icon-id", type=int, default=92)
    ap.add_argument("--bundles", default="hi,low")
    ap.add_argument("--cell", type=int, default=160, help="icon cell size in px (VERIFY with --probe)")
    ap.add_argument("--sheet", help="dds file name inside the tpf that holds the target cell")
    ap.add_argument("--cell-index", type=int, help="0-based cell index within --sheet")
    ap.add_argument("--out", default=os.path.join(REPO, "build", "ap_icon01", "menu"))
    ap.add_argument("--work", default=os.path.join(REPO, "build", "ap_icon01", "_work"))
    ap.add_argument("--probe", action="store_true", help="report the atlas layout, write nothing")
    ap.add_argument("--icon01", action="store_true", help="accepted for the inherited command line")
    ap.add_argument("--black-to-alpha", action="store_true",
                    help="ACCEPTED AND IGNORED -- the committed art already has alpha (see module docstring)")
    ap.add_argument("--force-black-to-alpha", action="store_true", help="really do the black->alpha keying")
    a = ap.parse_args()

    bundles = [b.strip() for b in a.bundles.split(",") if b.strip()]
    if not os.path.isdir(a.menu):
        die("no menu directory at %s" % a.menu)
    if not os.path.isfile(a.art):
        die("no art at %s (expected the committed flower; see tools/ap_icon_src/README.md)" % a.art)
    witchy = need_tool("witchybnd", "It supplies the Oodle/KRAK codec these atlases need; this "
                                    "script deliberately does not implement DCX.")
    if a.black_to_alpha and not a.force_black_to_alpha:
        print("build_ap_icon: NOTE --black-to-alpha ignored (art already has an alpha channel). "
              "Pass --force-black-to-alpha to override.", file=sys.stderr)

    if a.probe or a.sheet is None or a.cell_index is None:
        if not a.probe:
            print("build_ap_icon: --sheet/--cell-index not given; probing instead of guessing.\n",
                  file=sys.stderr)
        probe(a.menu, bundles, a.icon_id, a.cell, witchy, a.work)
        return 0

    die("the write path is not implemented yet ON PURPOSE. --probe first and report the atlas "
        "layout; the compositing half (texconv DDS<->PNG round trip, then witchy repack) gets "
        "written against a KNOWN layout rather than a guessed one. composite() above is ready and "
        "unit-testable; what is missing is only the DDS codec call, which needs the real sheet "
        "names and cell geometry that --probe prints.")


if __name__ == "__main__":
    sys.exit(main())
