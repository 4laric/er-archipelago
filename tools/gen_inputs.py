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

⭐ PARAMS AND MSG ARE NOW TAKEN BY GLOB (2026-07-27): the bundle carries EVERY *.csv in the params
dir and EVERY *.fmg.xml under msg/, not just the lists above. Those lists are now the REQUIRED
FLOOR -- missing one is still a hard refusal -- but anything else the box has rides along, so
"carry one more input to answer a question" stops being a code change plus a regen. The build
prints the extras and their sizes, because with a glob the bundle's WEIGHT is the thing to watch
and this .db is committed to a public repo.

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
import json
import hashlib
import os
import sqlite3
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ARTIFACTS = os.path.join(REPO, "elden_ring_artifacts")
DEFAULT_DB = os.path.join(REPO, "gen_inputs.db")

# Params are taken by GLOB now -- every *.csv in the params dir goes into the bundle. The list
# below is no longer the selection, it is the FLOOR: these must be present or the build refuses.
#
# WHY GLOB. The list was the selection until 2026-07-27, and it made "carry one more param" a code
# change plus a regen, which is exactly the friction that keeps a question unanswered. It also made
# the bundle silently narrower than the box it was built from: nobody could tell, from the bundle,
# whether a param was ABSENT from the game or merely never listed. Globbing inverts that -- what
# the box has, the bundle has -- and it costs ~nothing, because the packer already stores zlib
# blobs and params compress ~10x.
#
# WHY THE FLOOR STAYS. A glob alone cannot fail. Drop ItemLotParam_map.csv on the source box and a
# pure-glob packer builds a smaller bundle and calls it success, which regenerates a SMALLER WORLD
# and calls THAT a success too -- the exact quiet-success failure the rest of this file is built to
# refuse. So the names below are still checked, individually, and their absence is still FATAL.
REQUIRED_PARAM_CSVS = ["BonfireWarpParam.csv", "EquipMtrlSetParam.csv", "EquipParamAccessory.csv",
              "EquipParamGoods.csv", "EquipParamProtector.csv", "EquipParamWeapon.csv",
              "GestureParam.csv", "ItemLotParam_enemy.csv", "ItemLotParam_map.csv",
              "NpcParam.csv", "PlayRegionParam.csv", "ShopLineupParam.csv",
              "ShopLineupParam_Recipe.csv",
              # NOT read by gen_data.py -- carried so the ENEMY-SCALING LADDERS can be DERIVED.
              # Both the base ladder (7010..7100) and the DLC one (20007000..20007310) are today
              # hand-transcribed into er-logic/src/scaling.rs from an offline dump, and mirrored
              # AGAIN into greenfield/eldenring/scaling_ladder.py. Nothing checks either copy against
              # the game, and the HP rates are load-bearing: completion_scaling_floor converts
              # THROUGH them, so a wrong rung silently moves every player's difficulty floor. The DLC
              # rates are known only from three numbers in a code comment.
              #
              # ~9 MB raw (Alaric, 2026-07-27), so ~1 MB on top of a 3.6 MB bundle. I briefly
              # proposed distilling just the ~42 ladder rows into a tsv instead and was wrong twice
              # over: the size did not justify it, and it is precisely what the DESIGN note above
              # says not to do ("A MIRROR, NOT A DISTILLATION" -- the moment something needs a column
              # the distillation dropped, the artifact dependency comes back silently). Mirror it.
              "SpEffectParam.csv"]
FMG_XMLS = [f"{stem}Name{suf}.fmg.xml"
            for suf in ("", "_dlc01", "_dlc02")
            for stem in ("Weapon", "Protector", "Accessory", "Goods", "Gem")]

# (relative dir, [required names] or None, glob or None)
#   names + no glob  -> take exactly these; each missing one is FATAL
#   glob  + no names -> take everything matching
#   BOTH             -> take everything matching the glob, and REQUIRE the named ones (params)
SPEC = [
    (os.path.join("vanilla_er", "vanilla_er"), REQUIRED_PARAM_CSVS, "*.csv"),
    # msg/ is now ONE RECURSIVE GLOB over every *.fmg.xml, whatever msgbnd dirs are present --
    # same reasoning as the params glob. The 15 item-NAME FMGs stay the required floor (gen_data
    # reads them); everything else rides along.
    #
    # WHAT THIS UNLOCKS (2026-07-27): the bundle carried only the 15 item-name FMGs, which is the
    # naming half of several things we can now derive but not LABEL -- GameAreaParam gives boss
    # flags and arena coords but boss names live in NpcName; WorldMapPointParam gives 472 map
    # markers with textIds but the strings live in PlaceName; the 365-file talk ESD corpus is
    # unreadable without TalkMsg. Those FMGs are in menu.msgbnd / other msgbnds, which this glob
    # picks up without anyone having to enumerate them.
    ("msg", FMG_XMLS, "*.fmg.xml"),
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
        if names and not glob:
            n_before = len(out)
            for n in names:
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    out.append((os.path.join(rel, n).replace("\\", "/"), p))
                else:
                    missing.append(os.path.join(rel, n))
            notes.append(f"{rel}/: {len(out) - n_before} file(s)")
        elif names and glob:
            # GLOB FOR BREADTH, NAMES FOR THE FLOOR. Take everything matching, then check the
            # required set separately -- a glob cannot fail, and a params dir quietly missing
            # ItemLotParam_map would otherwise build a smaller bundle and report success.
            #
            # RECURSIVE, and required names match on BASENAME. params/ is flat but msg/ is not
            # (msg/item-msgbnd-dcx/WeaponName.fmg.xml), and the flat-listdir version of this is
            # the same bug that once packed the ESD corpus as zero files and called it success.
            n_before = len(out)
            found = {}
            for dirpath, _dirs, fnames in os.walk(d):
                for n in sorted(fnames):
                    if not fnmatch.fnmatch(n, glob):
                        continue
                    ap = os.path.join(dirpath, n)
                    found.setdefault(n, os.path.relpath(ap, d).replace("\\", "/"))
                    out.append((os.path.relpath(ap, src).replace("\\", "/"), ap))
            for n in names:
                if n not in found:
                    missing.append(os.path.join(rel, n) + "  (REQUIRED)")
            extra = sorted(set(found) - set(names))
            notes.append(f"{rel}/: {len(out) - n_before} file(s) matching {glob} "
                         f"({len(names)} required, {len(extra)} extra)")
            if extra:
                # Report SIZES for the extras. Globbing makes bundle weight the new failure mode --
                # this repo is public and the .db is committed -- so the cost of each ride-along has
                # to be visible at build time, not discovered in a git push.
                sized = sorted(((os.path.getsize(os.path.join(d, found[n])), n) for n in extra),
                               reverse=True)
                tot = sum(s for s, _ in sized)
                notes.append(f"  extra (carried, not read by gen_data): {len(extra)} file(s), "
                             f"{tot / 1e6:.1f} MB raw")
                for s, n in sized[:8]:
                    notes.append(f"      {s / 1e6:8.2f} MB  {n}")
                if len(sized) > 8:
                    notes.append(f"      ... and {len(sized) - 8} more")
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
    # gen_manifest opens this bundle through a separate read-only connection below.  Publish the
    # file table first; without this boundary that reader sees the pre-transaction empty database
    # and cannot derive the canonical bundle identity during --build.
    con.commit()
    # ---- record the SOURCE box's gen_manifest, so the stamp can self-diagnose -------------------
    # A bundle regen reproduces the generated modules byte-for-byte (proved 2026-07-27: 11/11 body
    # hashes identical) but the _GEN_STAMP `inputs_hash` still differed between the two boxes, and
    # working out WHY cost a round-trip through Alaric -- exactly what this tool exists to stop.
    # gen_manifest declares the input set; capture its per-file digests HERE, where the real
    # artifacts are, and --diff-manifest on the other side names the differing file instead of
    # leaving two opaque hashes to stare at.
    try:
        sys.path.insert(0, HERE)
        import gen_manifest as _gm
        man = _gm.compute_manifest(REPO)
        con.execute("INSERT OR REPLACE INTO meta VALUES ('gen_manifest', ?)",
                    (json.dumps(man, sort_keys=True),))
        print(f"  gen_manifest recorded: inputs_hash={man['inputs_hash'][:26]}... "
              f"{man['n_files']} declared input(s), missing={man['missing']}")
    except Exception as _e:
        print(f"  WARNING: gen_manifest unavailable ({_e!r}) -- bundle has no manifest, so "
              f"--diff-manifest cannot explain a stamp mismatch on the other side.")
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


def diff_manifest(db_path, repo):
    """Compare THIS tree's gen_manifest against the one recorded when the bundle was built.

    Reports the differing DECLARED INPUTS by name. `inputs_hash` is a hash of the whole input set,
    so two boxes disagreeing tells you nothing about WHICH input moved -- this does."""
    con = sqlite3.connect(db_path)
    row = con.execute("SELECT v FROM meta WHERE k='gen_manifest'").fetchone()
    con.close()
    if not row:
        print("this bundle carries no recorded manifest (built before that was added). Re-run "
              "--build on the box with the artifacts and the next one will explain itself.")
        return 2
    theirs = json.loads(row[0])
    sys.path.insert(0, HERE)
    import gen_manifest as _gm
    mine = _gm.compute_manifest(repo)
    print(f"bundle-side inputs_hash : {theirs['inputs_hash']}  ({theirs['n_files']} files)")
    print(f"this-tree  inputs_hash : {mine['inputs_hash']}  ({mine['n_files']} files)")
    if theirs["inputs_hash"] == mine["inputs_hash"]:
        print("MATCH -- a regen here stamps identically to one on the source box.")
        return 0
    tf, mf = theirs["files"], mine["files"]
    only_t = sorted(set(tf) - set(mf))
    only_m = sorted(set(mf) - set(tf))
    differ = sorted(k for k in set(tf) & set(mf) if tf[k] != mf[k])
    if only_t:
        print(f"  declared inputs present on the SOURCE box and absent here ({len(only_t)}):")
        for k in only_t[:20]:
            print(f"    {k}")
    if only_m:
        print(f"  present HERE and not on the source box ({len(only_m)}): {only_m[:20]}")
    if differ:
        print(f"  same path, DIFFERENT content ({len(differ)}):")
        for k in differ[:20]:
            print(f"    {k}")
    print("\nNOTE a stamp mismatch does NOT mean the regen is wrong: compare the module "
          "body_sha256 values in _gen_stamp.json -- those are the generated CONTENT, and on "
          "2026-07-27 all 11 matched across boxes while only inputs_hash differed.")
    return 1


def ensure(db_path, dest):
    """Extract only if the tree is not already there. The one-liner CI and a fresh sandbox both
    want: no artifacts -> materialise them; artifacts present -> leave the real ones alone."""
    marker = os.path.join(dest, "vanilla_er", "vanilla_er", "ItemLotParam_map.csv")
    if os.path.isfile(marker):
        print(f"gen inputs already present at {dest} -- leaving them alone")
        return 0
    return extract(db_path, dest)


def verify_regen(repo, ref="HEAD"):
    """Did a regen HERE reproduce the committed generated modules?

    Compares `_gen_stamp.json`'s per-module body_sha256 against `ref`'s, and IGNORES inputs_hash on
    purpose: inputs_hash covers the whole declared input set, which legitimately differs between a
    box with the real artifacts and one running off the bundle (the bundle carries what gen_data
    READS, not the MSBs). body_sha256 is the generated CONTENT, and that is what must match. Proven
    2026-07-27: 11/11 body hashes identical across Windows-artifacts and Linux-bundle regens while
    inputs_hash differed. A gate on the raw file diff would have called that a failure."""
    import subprocess
    rel = "greenfield/eldenring/_gen_stamp.json"
    now = json.load(open(os.path.join(repo, rel), encoding="utf-8"))
    was = json.loads(subprocess.run(["git", "-C", repo, "show", f"{ref}:{rel}"],
                                    capture_output=True, text=True, check=True).stdout)
    bad = sorted(k for k in set(now["modules"]) | set(was["modules"])
                 if now["modules"].get(k) != was["modules"].get(k))
    if now["counts"] != was["counts"]:
        print(f"COUNTS DIFFER: committed {was['counts']} -> regen {now['counts']}")
    if bad:
        print(f"REGEN DRIFT: {len(bad)} generated module(s) differ from {ref}: {bad}")
        print("  The committed generated data is STALE (or this tree changed a generator). "
              "Regenerate and commit; do not edit the modules by hand.")
        return 1
    print(f"regen verified: {len(now['modules'])} module body hashes match {ref}; counts match. "
          f"(inputs_hash intentionally not compared -- see verify_regen docstring.)")
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
        extras_made = []      # (relpath, label) -- one unlisted file per names+glob entry
        for rel, names, glob in SPEC:
            d = os.path.join(src, rel)
            # NEST the glob-only dirs one level down -- that nesting is the bug this fixture
            # reproduces (the decompiled talk ESD lives in talk/<map>-only/*.py and a flat
            # listdir missed it). The names+glob dir (params) is FLAT, like the real one.
            sub = "" if names else "m11_10_00_00-only"
            os.makedirs(os.path.join(d, sub) if sub else d, exist_ok=True)
            fixture = list(names) if names else [f"m10_00_00_00{glob[1:]}"]
            if names and glob:
                # The unlisted file must MATCH THIS ENTRY'S GLOB. Planting a .csv in msg/ (which
                # globs *.fmg.xml) makes the fixture, not the packer, the thing that is broken.
                unlisted = "ZZUnlisted" + glob.lstrip("*")
                fixture.append(unlisted)
                extras_made.append(os.path.join(rel, unlisted).replace("\\", "/"))
            for n in fixture:
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
        # DERIVED, not hardcoded. This was a literal 31, which went red the moment SpEffectParam.csv
        # joined PARAM_CSVS (2026-07-27) -- a true statement about the old SPEC masquerading as an
        # invariant. What the check is actually for is that the fixture covers every SPEC entry
        # (named files AND the glob dirs), so count that instead: adding an input can no longer
        # break the selftest, and DROPPING one still does.
        want = sum((len(names) + (1 if glob else 0)) if names else 1
                   for _rel, names, glob in SPEC)
        if len(made) != want:
            ok = False
            print(f"  FAIL fixture built {len(made)} files, expected {want} (one per SPEC entry)")
        # THE POINT OF THE GLOB: an unlisted file must ride along without a code change,
        # in EVERY globbed dir (params and msg), not just the one I happened to test.
        for rp in extras_made:
            if not os.path.isfile(os.path.join(dest, rp)):
                ok = False
                print(f"  FAIL unlisted {rp} was NOT bundled -- that dir's glob is not working")
            else:
                print(f"  ok   unlisted {rp} picked up by the glob")
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
    ap.add_argument("--diff-manifest", nargs="?", const=DEFAULT_DB, metavar="DB",
                    help="explain an inputs_hash mismatch by naming the differing declared input")
    ap.add_argument("--ensure", metavar="DEST", help="extract only if the inputs are not there")
    ap.add_argument("--verify-regen", nargs="?", const="HEAD", metavar="REF",
                    help="assert a regen here reproduced the committed modules (body hashes)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.diff_manifest:
        return diff_manifest(a.diff_manifest, REPO)
    if a.ensure:
        return ensure(a.db, a.ensure)
    if a.verify_regen:
        return verify_regen(REPO, a.verify_regen)
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
