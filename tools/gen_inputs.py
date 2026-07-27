#!/usr/bin/env python3
"""gen_inputs.py -- pack the (small) gen_data inputs into ONE sqlite file, and unpack them back.

THE POINT
---------
`gen_data.py` is the one step that needs `elden_ring_artifacts/`, which is why regen is a
hand-off to Alaric's Windows box every single time. But the artifacts gen_data actually reads are
NOT the whole game -- enumerated from its read sites (2026-07-27):

    13 param CSVs   BonfireWarpParam, EquipMtrlSetParam, EquipParamAccessory, EquipParamGoods,
                    EquipParamProtector, EquipParamWeapon, GestureParam, ItemLotParam_enemy,
                    ItemLotParam_map, NpcParam, PlayRegionParam, ShopLineupParam,
                    ShopLineupParam_Recipe
    15 FMG XMLs     {Weapon,Protector,Accessory,Goods,Gem}Name x {base, dlc01, dlc02}
       event/       the decompiled EMEVD (*.emevd.dcx.js)
       talk|esd_py/ the decompiled talk ESD (optional; the esd_* datamines)

That is text, and it compresses hard. The MSBs (mapstudio/, map/) are deliberately NOT here: they
are the unwieldy half, and only the Tier-2 MSB datamines need them -- those stay on the box with
the artifacts (AGENTS §5a). This bundle is aimed at `gen_data` and the param/EMEVD/ESD datamines,
which is where the regen bottleneck actually is.

DESIGN: A MIRROR, NOT A DISTILLATION -- and that choice is load-bearing.
The obvious version of this is "parse the params and keep the columns we read". Don't. The moment
gen_data needs a column the bundle dropped, the artifact dependency comes back -- silently, mid-
change, at the worst possible time. So this stores each needed file VERBATIM (zlib blob + sha256)
and `--extract` writes a real `elden_ring_artifacts/` tree back out. gen_data is then UNCHANGED and
cannot tell the difference, so a bundle regen and an artifact regen are byte-identical by
construction rather than by hope. Every column is kept, including the ones nothing reads yet.

WHY SQLITE and not a zip: random access per file, a manifest you can query, sha256 per entry, and
one file to move. `--verify` re-checks every hash without unpacking.

    python tools/gen_inputs.py --build                     # on the box WITH artifacts
    python tools/gen_inputs.py --verify  gen_inputs.db
    python tools/gen_inputs.py --extract elden_ring_artifacts   # anywhere else, then regen
    python tools/gen_inputs.py --selftest                  # round-trip on synthetic files

🛑 WHERE THE BUNDLE LIVES IS NOT THIS TOOL'S CALL. Committing it to a public repo's history means
every re-emit is a new multi-MB blob forever. A pinned release asset or a sibling repo (fetched by
sha256, the way `.ap-version` pins Archipelago) keeps history clean and the input reproducible.
Decide that once; the tool works either way.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
import sqlite3
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ARTIFACTS = os.path.join(REPO, "elden_ring_artifacts")
DEFAULT_DB = os.path.join(REPO, "gen_inputs.db")

PARAM_CSVS = ["BonfireWarpParam.csv", "EquipMtrlSetParam.csv", "EquipParamAccessory.csv",
              "EquipParamGoods.csv", "EquipParamProtector.csv", "EquipParamWeapon.csv",
              "GestureParam.csv", "ItemLotParam_enemy.csv", "ItemLotParam_map.csv",
              "NpcParam.csv", "PlayRegionParam.csv", "ShopLineupParam.csv",
              "ShopLineupParam_Recipe.csv"]
FMG_XMLS = [f"{stem}Name{suf}.fmg.xml"
            for suf in ("", "_dlc01", "_dlc02")
            for stem in ("Weapon", "Protector", "Accessory", "Goods", "Gem")]

# (relative dir, [exact names] or None, glob) -- None names = take everything matching the glob.
SPEC = [
    (os.path.join("vanilla_er", "vanilla_er"), PARAM_CSVS, None),
    (os.path.join("msg", "item-msgbnd-dcx"), [f for f in FMG_XMLS if "dlc" not in f], None),
    (os.path.join("msg", "item_dlc01-msgbnd-dcx"), [f for f in FMG_XMLS if "dlc01" in f], None),
    (os.path.join("msg", "item_dlc02-msgbnd-dcx"), [f for f in FMG_XMLS if "dlc02" in f], None),
    ("event", None, "*.emevd.dcx.js"),
    ("talk", None, "*.py"),
    ("esd_py", None, "*.py"),
]
# Dirs whose ABSENCE is fine (optional corpora). Everything else missing is a hard error: a bundle
# that is quietly missing ItemLotParam_map would produce a "successful" regen of a smaller world.
OPTIONAL_DIRS = {"talk", "esd_py"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta  (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, size INTEGER, sha256 TEXT, blob BLOB);
"""


def _walk(src, report=None):
    """[(relpath, abspath)] for everything SPEC asks for. Raises on a missing required dir/file.

    RECURSES for the glob entries. The first version used os.listdir, which is flat -- and the
    decompiled talk ESD is nested one level down (talk/m11_10_00_00-only/t320001110.py), so it
    matched NOTHING and, because `talk` is optional, said nothing about it. The first real build
    packed 617 files (28 params/FMGs + 589 EMEVD) and reported success with the entire ESD corpus
    missing. That is the exact quiet-success failure this tool's other guards exist to stop, so an
    OPTIONAL dir that is PRESENT but yields ZERO files is now reported loudly -- "absent" and
    "present and empty" are different facts.
    """
    out, missing, notes = [], [], []
    for rel, names, glob in SPEC:
        d = os.path.join(src, rel)
        if not os.path.isdir(d):
            if rel not in OPTIONAL_DIRS:
                missing.append(f"{rel}/ (directory)")
            else:
                notes.append(f"{rel}/: ABSENT (optional) -- not bundled")
            continue
        if names:
            n_before = len(out)
            for n in names:
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    out.append((os.path.join(rel, n).replace("\\", "/"), p))
                else:
                    missing.append(os.path.join(rel, n))
            notes.append(f"{rel}/: {len(out) - n_before} file(s)")
        else:
            n_before = len(out)
            for dirpath, _dirs, fnames in os.walk(d):
                for n in sorted(fnames):
                    if not fnmatch.fnmatch(n, glob):
                        continue
                    ap = os.path.join(dirpath, n)
                    rp = os.path.relpath(ap, src).replace("\\", "/")
                    out.append((rp, ap))
            got = len(out) - n_before
            notes.append(f"{rel}/: {got} file(s) matching {glob}")
            if got == 0:
                msg = (f"{rel}/ EXISTS but matched ZERO {glob} files. Present-and-empty is not the "
                       f"same as absent -- check the layout before trusting this bundle.")
                if rel in OPTIONAL_DIRS:
                    notes.append("  WARNING: " + msg)
                else:
                    missing.append(msg)
    if report is not None:
        report.extend(notes)
    if missing:
        raise SystemExit("FATAL: gen inputs missing from %s:\n  %s\n"
                         "A bundle built without these would regen a SMALLER world and call it a "
                         "success. Refusing." % (src, "\n  ".join(missing)))
    return out


def build(src, db_path):
    report = []
    files = _walk(src, report)
    for line in report:
        print("  " + line)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript(_SCHEMA)
    raw = 0
    for rel, p in files:
        data = open(p, "rb").read()
        raw += len(data)
        con.execute("INSERT INTO files VALUES (?,?,?,?)",
                    (rel, len(data), hashlib.sha256(data).hexdigest(),
                     zlib.compress(data, 9)))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('n_files', ?)", (str(len(files)),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('raw_bytes', ?)", (str(raw),))
    con.commit()
    con.close()
    packed = os.path.getsize(db_path)
    print(f"built {db_path}: {len(files)} file(s), {raw/1e6:.1f} MB raw -> {packed/1e6:.1f} MB "
          f"({100.0*packed/raw:.0f}%)")
    print(f"  sha256(bundle) = {hashlib.sha256(open(db_path,'rb').read()).hexdigest()}")
    return 0


def _entries(db_path):
    if not os.path.isfile(db_path):
        raise SystemExit(f"FATAL: no bundle at {db_path}")
    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT path, size, sha256, blob FROM files ORDER BY path").fetchall()
    con.close()
    if not rows:
        raise SystemExit(f"FATAL: {db_path} has zero files -- an empty bundle is a failure, "
                         f"not a clean build.")
    return rows


def verify(db_path):
    bad = []
    for path, size, sha, blob in _entries(db_path):
        data = zlib.decompress(blob)
        if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
            bad.append(path)
    n = len(_entries(db_path))
    if bad:
        print(f"VERIFY FAILED: {len(bad)}/{n} entr(ies) corrupt: {bad[:10]}")
        return 1
    print(f"verify OK: {n} file(s), every sha256 matches")
    return 0


def extract(db_path, dest):
    n = 0
    for path, size, sha, blob in _entries(db_path):
        data = zlib.decompress(blob)
        if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
            raise SystemExit(f"FATAL: {path} fails its sha256 -- refusing to write a corrupt "
                             f"input. A silently wrong param CSV is the worst thing this tool "
                             f"could hand gen_data.")
        out = os.path.join(dest, *path.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(data)
        n += 1
    print(f"extracted {n} file(s) -> {dest}")
    print("  gen_data.py is UNCHANGED by this: it reads the same tree it always did, so a bundle "
          "regen and an artifact regen are byte-identical by construction. Confirm it anyway -- "
          "compare eldenring/_gen_stamp.json against a regen from the real artifacts.")
    return 0


def selftest():
    """Round-trip on synthetic files. No artifacts, no game data -- so the packer is not shipping
    unexercised just because its input only exists on one machine."""
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="gen_inputs_selftest_")
    ok = True
    try:
        src = os.path.join(root, "art")
        made = []
        for rel, names, glob in SPEC:
            d = os.path.join(src, rel)
            # NEST the glob dirs one level down -- that nesting is the bug this fixture reproduces
            # (the decompiled talk ESD lives in talk/<map>-only/*.py and a flat listdir missed it).
            sub = "" if names else "m11_10_00_00-only"
            os.makedirs(os.path.join(d, sub) if sub else d, exist_ok=True)
            for n in (names or [f"m10_00_00_00{glob[1:]}"]):
                rp = os.path.join(rel, sub, n) if sub else os.path.join(rel, n)
                open(os.path.join(src, rp), "w", encoding="utf-8").write(f"synthetic {n}\n" * 50)
                made.append(rp)
        db = os.path.join(root, "b.db")
        build(src, db)
        if verify(db) != 0:
            ok = False
        dest = os.path.join(root, "out")
        extract(db, dest)
        for rp in made:
            a, b = os.path.join(src, rp), os.path.join(dest, rp)
            if not os.path.isfile(b) or open(a, "rb").read() != open(b, "rb").read():
                ok = False
                print(f"  FAIL round-trip lost or altered a NESTED file: {rp}")
        if len(made) != 31:
            ok = False
            print(f"  FAIL fixture built {len(made)} files, expected 31")
        # a REQUIRED file going missing must be a hard refusal, not a smaller bundle
        os.remove(os.path.join(src, "vanilla_er", "vanilla_er", "ItemLotParam_map.csv"))
        try:
            _walk(src)
            ok = False
            print("  FAIL missing required param did NOT refuse")
        except SystemExit:
            print("  ok   missing required param refuses the build")
        print("selftest:", "OK" if ok else "FAILED")
        return 0 if ok else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--verify", nargs="?", const=DEFAULT_DB)
    ap.add_argument("--extract", metavar="DEST")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--artifacts", default=ARTIFACTS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.build:
        return build(a.artifacts, a.db)
    if a.verify:
        return verify(a.verify)
    if a.extract:
        return extract(a.db, a.extract)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
