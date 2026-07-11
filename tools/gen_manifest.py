#!/usr/bin/env python3
"""gen_manifest.py -- the ONE definition of the greenfield gen-input content hash.

Both `greenfield/gen_data.py` (which stamps the hash into every generated module) and the build
gate (`build.ps1` / `gen-greenfield.ps1`, via `python -m tools.gen_manifest`) call THIS file, so the
hash means the same thing on Linux and on Windows. See SPEC-gen-input-hash-gate-20260710.md.

The hash covers everything a regen depends on: the tracked inputs (region_map.csv, item_tiers.tsv,
optional region_overrides.tsv), the licensing-restricted datamined artifacts (grace tables, the EMEVD
event dir, the item-name FMG xml, the two ShopLineupParam csvs), the datamine INTERMEDIATES
(boss_drops.py / boss_healthbars.py -- so a stale datamine step is caught), and gen_data.py ITSELF
(the transform is part of the input; a code change with unchanged data must invalidate the stamp).

Determinism across OSes:
  * relpaths are forward-slash, sorted.
  * text inputs are newline-normalized (CRLF/CR -> LF) before hashing, so a Windows autocrlf checkout
    and a Linux LF checkout of the same logical file hash identically.
  * a declared-but-absent input hashes as the literal "ABSENT" (well-defined either way) and is also
    reported in `missing`, so a caller can refuse to *verify* when artifacts aren't present rather
    than trust a hash computed over a partial input set.

CLI:
  python -m tools.gen_manifest                 # print "sha256:...."  (stdout, for PS to capture)
  python -m tools.gen_manifest --json          # full manifest as JSON
  python -m tools.gen_manifest --verify FILE   # compare against _gen_stamp.json / a module's stamp;
                                               #   exit 0 match, 3 mismatch, 4 cannot-verify(missing)
"""
import argparse
import glob
import hashlib
import json
import os
import sys

# Repo-root-relative input declaration. Concrete files + globs. Order here is irrelevant (sorted).
FILE_INPUTS = [
    "greenfield/gen_data.py",
    "greenfield/region_map.csv",
    "item_tiers.tsv",
    "greenfield/region_overrides.tsv",                 # optional (SPEC-provenance-oracle); ABSENT-ok
    "greenfield/eldenring_gf/boss_drops.py",
    "greenfield/eldenring_gf/boss_healthbars.py",
    "elden_ring_artifacts/grace_flags.tsv",
    "elden_ring_artifacts/vanilla_er/vanilla_er/ShopLineupParam.csv",
    "elden_ring_artifacts/vanilla_er/vanilla_er/ShopLineupParam_Recipe.csv",
]
GLOB_INPUTS = [
    "elden_ring_artifacts/grace_region_map_*.tsv",
    "elden_ring_artifacts/event/**/*",
    "elden_ring_artifacts/msg/item-msgbnd-dcx/*Name*.fmg.xml",
    "elden_ring_artifacts/msg/item_dlc01-msgbnd-dcx/*Name*.fmg.xml",
    "elden_ring_artifacts/msg/item_dlc02-msgbnd-dcx/*Name*.fmg.xml",
]
# Inputs allowed to be absent without making the whole manifest "unverifiable" (they're genuinely
# optional / not-yet-created). Everything else missing sets the `missing` flag.
OPTIONAL = frozenset({"greenfield/region_overrides.tsv"})

_TEXT_EXTS = {".csv", ".tsv", ".xml", ".py", ".js", ".md", ".json", ".txt", ".ps1", ".sh"}


def _norm_repo(repo_root):
    return os.path.abspath(repo_root)


def _file_digest(abspath):
    """sha256 of a file; text files are newline-normalized so CRLF vs LF doesn't change the hash."""
    with open(abspath, "rb") as fh:
        data = fh.read()
    if os.path.splitext(abspath)[1].lower() in _TEXT_EXTS:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _resolve_inputs(repo_root):
    """Return sorted list of (relpath, abspath) for every declared input that resolves to a file."""
    repo_root = _norm_repo(repo_root)
    found = {}                                          # relpath -> abspath (dedup)
    declared_present = set()                            # which FILE_INPUTS/globs matched
    for rel in FILE_INPUTS:
        ap = os.path.join(repo_root, rel)
        if os.path.isfile(ap):
            found[rel.replace("\\", "/")] = ap
            declared_present.add(rel)
    for pat in GLOB_INPUTS:
        matched = False
        for ap in glob.glob(os.path.join(repo_root, pat), recursive=True):
            if os.path.isfile(ap):
                rel = os.path.relpath(ap, repo_root).replace("\\", "/")
                found[rel] = ap
                matched = True
        if matched:
            declared_present.add(pat)
    return found, declared_present


def compute_manifest(repo_root):
    """Return dict: {inputs_hash, gen_data_sha, n_files, missing:[...], files:{rel:digest}}."""
    repo_root = _norm_repo(repo_root)
    found, declared_present = _resolve_inputs(repo_root)

    # Which REQUIRED declarations produced nothing? (globs that matched zero files, or missing files.)
    missing = []
    for rel in FILE_INPUTS:
        if rel not in found and rel not in OPTIONAL:
            missing.append(rel)
    for pat in GLOB_INPUTS:
        if pat not in declared_present:
            missing.append(pat)

    files = {rel: _file_digest(ap) for rel, ap in found.items()}
    # Absent required inputs participate in the hash as "ABSENT" so the hash is well-defined and a
    # partial-input machine can't collide with a full-input one.
    for rel in missing:
        files.setdefault(rel, "ABSENT")

    material = "\n".join(f"{rel}\0{files[rel]}" for rel in sorted(files)).encode("utf-8")
    inputs_hash = "sha256:" + hashlib.sha256(material).hexdigest()
    gd = os.path.join(repo_root, "greenfield/gen_data.py")
    gen_data_sha = "sha256:" + _file_digest(gd) if os.path.isfile(gd) else None
    return {
        "inputs_hash": inputs_hash,
        "gen_data_sha": gen_data_sha,
        "n_files": len([r for r in files if files[r] != "ABSENT"]),
        "missing": missing,
        "files": files,
    }


def compute_inputs_hash(repo_root):
    """Convenience: just the inputs_hash string."""
    return compute_manifest(repo_root)["inputs_hash"]


def _find_repo_root(start=None):
    """Walk up from `start` (or this file) to the dir containing greenfield/gen_data.py."""
    d = os.path.abspath(start or os.path.dirname(__file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "greenfield", "gen_data.py")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    # fallback: parent of tools/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _extract_stamp_hash(path):
    """Pull an inputs_hash out of a _gen_stamp.json OR a generated .py module's _GEN_STAMP block."""
    with open(path, "r", encoding="utf-8") as fh:
        txt = fh.read()
    if path.endswith(".json"):
        return json.loads(txt).get("inputs_hash")
    # crude but dependency-free: find the sha256:... after "inputs_hash"
    import re
    m = re.search(r'inputs_hash["\']?\s*[:=]\s*["\'](sha256:[0-9a-f]+)["\']', txt)
    return m.group(1) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="greenfield gen-input content hash")
    ap.add_argument("--repo", default=None, help="repo root (default: auto-detect)")
    ap.add_argument("--json", action="store_true", help="print full manifest JSON")
    ap.add_argument("--verify", metavar="STAMP", help="compare hash against a _gen_stamp.json / module")
    args = ap.parse_args(argv)
    repo = _find_repo_root(args.repo)
    man = compute_manifest(repo)

    if args.verify:
        want = _extract_stamp_hash(args.verify)
        have = man["inputs_hash"]
        if man["missing"]:
            sys.stderr.write(
                "gen_manifest: CANNOT VERIFY -- required inputs absent: %s\n" % ", ".join(man["missing"])
            )
            return 4
        if want != have:
            sys.stderr.write(
                "gen_manifest: STALE -- stamp %s != current inputs %s\n"
                "  regenerate: python greenfield/gen_data.py (or build.ps1 -Greenfield)\n" % (want, have)
            )
            return 3
        sys.stdout.write("gen_manifest: OK %s\n" % have)
        return 0

    if args.json:
        print(json.dumps(man, indent=2, sort_keys=True))
    else:
        print(man["inputs_hash"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
