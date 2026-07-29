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


def find_witchy(explicit=None):
    """Locate WitchyBND without requiring anyone to edit PATH.

    It already ships inside this project: elden_ring_artifacts\\WitchyBND.exe, with
    oo2core_6_win64.dll beside it -- that dll IS the Oodle codec these KRAK atlases need, and
    tools/datamine_merchant_shops.py already documents invoking it from there. So look in the
    obvious places before demanding a PATH entry.
    """
    tried = []
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("WITCHYBND"):
        cands.append(os.environ["WITCHYBND"])
    for name in ("WitchyBND.exe", "witchybnd.exe", "WitchyBND", "witchybnd"):
        cands.append(os.path.join(REPO, "elden_ring_artifacts", name))
    for name in ("witchybnd", "WitchyBND", "witchybnd.exe", "WitchyBND.exe"):
        found = shutil.which(name)
        if found:
            cands.append(found)
    for c in cands:
        tried.append(c)
        if c and os.path.isfile(c):
            _warn_if_no_oodle(c)
            return c
    die("WitchyBND not found. It supplies the Oodle/KRAK codec these atlases need; this script "
        "deliberately does not implement DCX. Looked at:\n  " + "\n  ".join(tried) +
        "\nPass --witchy <path>, set WITCHYBND, or drop it in elden_ring_artifacts\\.")


def _warn_if_no_oodle(witchy_exe):
    """KRAK needs oo2core beside witchy. Absent, the unpack fails with a confusing error -- say so
    up front rather than letting it surface as 'witchybnd -u failed'."""
    d = os.path.dirname(os.path.abspath(witchy_exe))
    if not any(f.lower().startswith("oo2core") for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))):
        print("build_ap_icon: WARNING no oo2core*.dll beside %s -- these atlases are DCX/KRAK "
              "(Oodle) and the unpack will fail without it." % witchy_exe, file=sys.stderr)


_PROMPTPLUS = "requires a terminal"
_NEEDS_CONSOLE = [False]   # latched on first refusal: witchy 3.0.1.0 refuses even with -s


def run_witchy(witchy, args, what):
    """Run WitchyBND, coping with its interactive console layer.

    🛑 WitchyBND draws its UI with PromptPlus, which REFUSES to start when stdio is redirected --
    and capture_output=True redirects stdio. First run of this script died with
    "PromptPlus requires a terminal/console without redirection!" and exit 1, which reads like a
    witchy failure rather than a plumbing one.

    `-s` (silent) exists precisely for "an environment that does not support its console output", so
    try that first and still capture. If a witchy build predates or ignores the flag, fall back to
    INHERITING the console: no capture, so PromptPlus is happy. We only need the exit code and the
    directory it produced, never its stdout, so inheriting costs nothing but noise.
    """
    if _NEEDS_CONSOLE[0]:
        r0 = subprocess.run([witchy] + args)      # learned already; skip the wasted attempt
        if r0.returncode != 0:
            die("%s failed (exit %d)" % (what, r0.returncode))
        return r0
    r = subprocess.run([witchy, "-s"] + args, capture_output=True, text=True)
    if r.returncode == 0:
        return r
    blob = (r.stdout or "") + (r.stderr or "")
    if _PROMPTPLUS in blob or "redirection" in blob:
        if not _NEEDS_CONSOLE[0]:
            print("build_ap_icon: witchy refused redirected stdio even with -s; attaching to this "
                  "console for the rest of the run.", file=sys.stderr)
        _NEEDS_CONSOLE[0] = True
        r2 = subprocess.run([witchy] + args)
        if r2.returncode == 0:
            return r2
        die("%s failed (exit %d) with witchy attached to the console -- this is a real witchy "
            "error, not the PromptPlus redirection problem." % (what, r2.returncode))
    die("%s failed (exit %d)\n%s" % (what, r.returncode, blob))


def unpack(witchy, src, workdir):
    """witchy -u <file> -> a sibling directory. Returns the unpacked dir."""
    os.makedirs(workdir, exist_ok=True)
    local = os.path.join(workdir, os.path.basename(src))
    shutil.copy2(src, local)
    run_witchy(witchy, ["-u", local], "witchybnd -u on %s" % local)
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


LAYOUT = "01_common.sblytbnd.dcx"


def find_sprite(unpacked_layout, icon_id):
    """iconId -> (texture, x, y, w, h) from the sprite LAYOUT, not from grid arithmetic.

    🛑 THIS IS THE WHOLE POINT. The first probe run falsified the grid model outright: the atlases
    are 4096x2048 and no sensible cell size was even a divisor of the default 160. Worse, the sheets
    are irregular -- SB_Icon_02, _02_A, _02_B, _03, _03_A, _07_dlc, _07_dlc_A -- so "icon N lives at
    sheet N//per_sheet" cannot be right either, and a wrong answer here paints over an unrelated
    item's icon and errors nothing.

    The game does not do arithmetic: 01_common.sblytbnd.dcx sits beside the atlas and names, per
    sprite, its texture and rect. So read it. Schema is parsed defensively -- ANY element carrying
    x/y/width/height and mentioning the id -- and --probe dumps what it matched so a wrong parse is
    visible rather than silent.
    """
    import re
    import xml.etree.ElementTree as ET
    hits = []
    for root, _d, files in os.walk(unpacked_layout):
        for fn in files:
            if not fn.lower().endswith((".xml", ".layout")):
                continue
            path = os.path.join(root, fn)
            try:
                tree = ET.parse(path)
            except Exception:
                continue
            for el in tree.iter():
                a = el.attrib
                if not all(k in a for k in ("x", "y")):
                    continue
                w = a.get("width") or a.get("w")
                h = a.get("height") or a.get("h")
                if not (w and h):
                    continue
                # MATCH THE NAME, NOT EVERY ATTRIBUTE. The first real run matched
                # MENU_MAP_DropSoul and MENU_FL_SlotBase_Shop because their HEIGHT is 92, and in
                # the low bundle a dozen SB_BigRunes sprites (height 92) crowded the real entry
                # past the print truncation. An id lives in the sprite NAME; a dimension that
                # happens to equal it is noise -- the wrong-id-space trap, one field over.
                name = a.get("name") or ""
                if re.search(r"ItemIcon_0*%d(?!\d)" % icon_id, name):
                    hits.append((os.path.basename(path), el.tag, dict(a), True))
                elif re.search(r"(?<!\d)0*%d(?!\d)" % icon_id, name):
                    hits.append((os.path.basename(path), el.tag, dict(a), False))
    hits.sort(key=lambda h: not h[3])   # exact ItemIcon matches first
    return hits


def probe(menu, bundles, icon_id, cell, witchy, workdir):
    """Report where icon `icon_id` actually lives. WRITES NOTHING."""
    print("PROBE -- no files will be written.\n")
    for b in bundles:
        src = os.path.join(menu, b, SHEET)
        lay = os.path.join(menu, b, LAYOUT)
        if not os.path.isfile(src):
            die("no %s (looked for the atlas this tool edits)" % src)

        if os.path.isfile(lay):
            up = unpack(witchy, lay, os.path.join(workdir, b, "layout"))
            hits = find_sprite(up, icon_id)
            print("[%s] %s" % (b, lay))
            if hits:
                print("  sprite entries mentioning %d -- CHECK these name the right item:" % icon_id)
                exact = [h for h in hits if h[3]]
                for fn, tag, attrs, is_exact in (exact or hits)[:12]:
                    print("    %-26s %s <%s %s>" % (
                        fn, "ITEMICON" if is_exact else "loose   ", tag,
                        " ".join("%s=%r" % (k, v) for k, v in sorted(attrs.items()))))
                if exact:
                    fn, _t, attrs, _e = exact[0]
                    print("  => TARGET  atlas=%-20s x=%s y=%s w=%s h=%s" % (
                        os.path.splitext(fn)[0] + ".dds", attrs["x"], attrs["y"],
                        attrs.get("width"), attrs.get("height")))
                elif len(hits) > 12:
                    print("    ... %d more (all loose; none is an ItemIcon)" % (len(hits) - 12))
            else:
                print("  no sprite entry matched %d. Dumping the layout's shape so the parse can be"
                      " fixed rather than guessed:" % icon_id)
                shown = 0
                for r, _d, fs in os.walk(up):
                    for fn in sorted(fs):
                        print("    %s" % os.path.join(os.path.relpath(r, up), fn))
                        shown += 1
                        if shown >= 15:
                            break
                    if shown >= 15:
                        break
        else:
            print("[%s] NO %s beside the atlas -- falling back to the grid report." % (b, LAYOUT))

        up = unpack(witchy, src, os.path.join(workdir, b))
        sheets = [p for p in dds_files(up) if "sb_icon" in os.path.basename(p).lower()]
        if not sheets:
            die("unpacked %s but found no SB_Icon*.dds inside. An empty result is a FAILURE, not a "
                "clean run." % src)
        print("  SB_Icon atlases (%d):" % len(sheets))
        for p in sheets:
            wh = dds_size(p)
            print("    %-24s %s" % (os.path.basename(p),
                                    ("%dx%d" % wh) if wh else "(no readable DDS header)"))
        print()


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
    ap.add_argument("--witchy", help="path to WitchyBND.exe (default: elden_ring_artifacts, then PATH)")
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
    witchy = find_witchy(a.witchy)
    print("build_ap_icon: using witchy at %s" % witchy, file=sys.stderr)
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
