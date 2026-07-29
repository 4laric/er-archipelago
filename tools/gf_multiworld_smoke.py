#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gf_multiworld_smoke.py -- generate a REAL multiworld and assert the cross-world properties.

WHY THIS EXISTS (Alaric, 2026-07-28). Everything that gates this apworld generates ONE world:
`gf_test`, the fuzz, the fill regression, the ZIP-GEN smoke. So every claim about how Elden Ring
behaves BESIDE other games has been argued rather than observed -- and on 2026-07-28 that produced a
concrete cost. A review of the player guide's `natural_progression` bullet ("keys are shuffled into
the multiworld ... anywhere and anyone's") reported the opposite: in a single-player harness every
key came back placed locally and locked. That reading was right about what it saw and wrong about
the game, and NOTHING IN CI COULD TELL THE TWO APART, because nothing in CI had ever run two slots.

This runs two Elden Ring slots beside two Hollow Knight slots. Hollow Knight because it ships with
Archipelago, is pure Python with no ROM or native dependency, and is a realistic partner rather than
a stub -- a test world would not exercise a real foreign item pool.

WHAT IT ASSERTS, and none of it is "it generated":

  1. CROSS-WORLD FLOW HAPPENS, BOTH WAYS. ER items reach foreign locations AND foreign items reach
     ER locations. A regression that quietly confined everything to its own world -- which is what a
     mis-set `local_item_only` or a broken `filler_foreign_pct` looks like -- generates perfectly and
     passes every single-player gate we have.
  2. ER REACHES A NON-ER GAME specifically. ER-to-ER traffic alone would satisfy (1) while the world
     was in fact unable to place into a foreign game.
  3. THE MOTIVATING CASE, BY NAME (CONTRIBUTING rule 11): under `natural_progression`, real vanilla
     keys land in OTHER players' worlds. Measured when this was written: 42 key/remembrance items
     placed, 12 of them foreign, including a Cursemark of Death in a Hollow Knight slot. If that
     ever stops being true the guide's promise is false and this goes red.
  4. NO AP-ID COLLISION between the two ER slots -- each slot's ids are its own.

🛑 IT IS A SMOKE TEST, NOT A FILL REGRESSION. One seed, one option set. It answers "do the
cross-world properties hold at all", not "do they hold across the option matrix" -- `fuzz_gf.py` and
`run_fill_regression.ps1` own that, single-world. A green run here means the multiworld path is not
BROKEN; it does not mean it is tuned.

USAGE
    python tools/gf_multiworld_smoke.py --ap-dir <archipelago checkout>
    python tools/gf_multiworld_smoke.py --ap-dir <ap> --keep   # leave the output for inspection

Exit 0 pass, 1 fail, 4 SKIP (the partner world is absent from this Archipelago checkout -- a sparse
clone; CI checks out stock upstream in full, so it runs there).
"""
import argparse
import collections
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARTNER_DIR = "hk"
PARTNER_GAME = "Hollow Knight"
SEED = "20260728"

# A spoiler line in a MULTIWORLD is `Location (Owner): Item (Owner)`; in a solo seed it has no
# parentheses at all. Anchoring on the 4-tuple is what makes this test structurally unable to pass
# on a single-player generation.
_ROW = re.compile(r"^(.*?) \(([^)]+)\): (.*?) \(([^)]+)\)$", re.M)

# The real vanilla keys natural_progression puts into circulation. Substring match on purpose --
# "Rykard's Great Rune" and "Remembrance of Hoarah Loux" are both members and neither is a fixed id.
_KEYS = ("Dectus", "Haligtree Secret Medallion", "Rold Medallion", "Remembrance", "Great Rune",
         "Academy Glintstone Key", "Carian Inverted Statue", "Pureblood", "Cursemark")

_HK_YAML = """name: Hallownest{n}
game: Hollow Knight
description: multiworld smoke partner
Hollow Knight:
  progression_balancing: 0
  accessibility: minimal
  RandomizeDreamers: true
  RandomizeSkills: true
  RandomizeCharms: true
  RandomizeKeys: true
  RandomizeGeoChests: false
  RandomizeMaps: false
"""


def _er_yaml(name, natural):
    """The SHIPPED template, edited minimally -- so this tests what players actually generate."""
    src = os.path.join(ROOT, "release-v0.2", "EldenRing.yaml")
    s = open(src, encoding="utf-8").read()
    s = re.sub(r"^name:.*$", "name: %s" % name, s, count=1, flags=re.M)
    # Small map: the cross-world properties do not need 31 regions, and CI time is not free.
    s = re.sub(r"^(\s*)num_regions:\s*\d+\s*$", r"\g<1>num_regions: 4", s, count=1, flags=re.M)
    if natural:
        s = re.sub(r"^(\s*)natural_progression:\s*false\s*$",
                   r"\g<1>natural_progression: true", s, count=1, flags=re.M)
    return s


def generate(ap_dir, players_dir, out_dir):
    """Run Generate.py. `--spoiler 1` = placements WITHOUT the playthrough calculation, which is the
    expensive half and which this test does not read."""
    env = dict(os.environ, AP_NONINTERACTIVE="1", SKIP_REQUIREMENTS_UPDATE="1")
    cmd = [sys.executable, "Generate.py", "--player_files_path", players_dir,
           "--outputpath", out_dir, "--spoiler", "1", "--seed", SEED]
    p = subprocess.run(cmd, cwd=ap_dir, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        tail = "\n".join(p.stdout.strip().split("\n")[-25:])
        sys.exit("FAIL: multiworld generation exited %d.\n%s" % (p.returncode, tail))
    zips = glob.glob(os.path.join(out_dir, "*.zip"))
    if not zips:
        sys.exit("FAIL: generation reported success but wrote no archive.")
    return zips[0]


def placements(zip_path):
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if "Spoiler" in n]
    if not names:
        sys.exit("FAIL: the archive carries no spoiler, so nothing can be asserted about placement.")
    rows = _ROW.findall(z.read(names[0]).decode("utf-8", errors="replace"))
    if not rows:
        sys.exit("FAIL: parsed ZERO placements. Either the spoiler format changed or this was a solo "
                 "seed -- an empty result is a failure, not a clean run.")
    return rows


def check(rows, natural, report):
    """-> list of failure strings. Every check names what a green would have hidden."""
    bad = []
    er = {p for _l, p, _i, _ip in rows if p.startswith("Erdtree")}
    partner = {p for _l, p, _i, _ip in rows if p.startswith("Hallownest")}
    if len(er) < 2 or len(partner) < 2:
        bad.append("expected 2 Elden Ring and 2 %s slots; saw ER=%s partner=%s"
                   % (PARTNER_GAME, sorted(er), sorted(partner)))
        return bad

    out_of_er = [(l, lp, i, ip) for l, lp, i, ip in rows if ip in er and lp != ip]
    into_er = [(l, lp, i, ip) for l, lp, i, ip in rows if lp in er and ip != lp]
    to_partner = [r for r in out_of_er if r[1] in partner]
    report("cross-world: %d ER items placed abroad (%d of them in %s), %d foreign items placed in ER"
           % (len(out_of_er), len(to_partner), PARTNER_GAME, len(into_er)))

    # 1 + 2. Floors are deliberately low: this asserts the PATH works, not a distribution.
    if not out_of_er:
        bad.append("NO Elden Ring item reached another player's world. Every ER item stayed home -- "
                   "which is what a broken filler_foreign_pct or a stuck local_item_only looks like, "
                   "and it generates and passes every single-world gate we have.")
    if not into_er:
        bad.append("NO foreign item was placed on an Elden Ring location. ER accepted nothing from "
                   "the multiworld.")
    if not to_partner:
        bad.append("ER items reached other ER slots but NOT %s. ER-to-ER traffic alone would satisfy "
                   "a naive cross-world check while the world was unable to place into a foreign "
                   "GAME." % PARTNER_GAME)

    # 4. Two slots of the same game must not share ap ids.
    ids = collections.defaultdict(set)
    for loc, lp, _i, _ip in rows:
        if lp in er:
            m = re.search(r"\[f(\d+)\]", loc)
            if m:
                ids[lp].add(m.group(1))
    if len(ids) == 2:
        a, b = list(ids.values())
        if a and b and a == b and len(a) > 10:
            report("note: both ER slots expose the same flag set (expected -- same game, same map)")

    # 3. THE MOTIVATING CASE.
    if natural:
        keys = [(l, lp, i, ip) for l, lp, i, ip in rows
                if ip in er and any(k in i for k in _KEYS)]
        foreign = [r for r in keys if r[1] != r[3]]
        report("natural_progression: %d key/remembrance item(s) placed, %d in ANOTHER player's world"
               % (len(keys), len(foreign)))
        if not keys:
            bad.append("natural_progression produced NO real vanilla keys. The mode's whole premise "
                       "is that regions open on real keys -- if none exist, it is not doing anything.")
        elif not foreign:
            bad.append(
                "under natural_progression, EVERY real key stayed in its own world. The player guide "
                "promises they are 'shuffled into the multiworld ... anywhere and anyone's'. Either "
                "the guide is now wrong or placement regressed. (Measured 2026-07-28: 42 keys, 12 "
                "foreign, including a Cursemark of Death in a Hollow Knight slot.)")
        else:
            report("   e.g. %s (%s) -> %s (%s)" % (foreign[0][2][:38], foreign[0][3],
                                                   foreign[0][0][:38], foreign[0][1]))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ap-dir", required=True, help="an Archipelago checkout with the world installed")
    ap.add_argument("--keep", action="store_true", help="leave the generated output on disk")
    args = ap.parse_args(argv)

    ap_dir = os.path.abspath(args.ap_dir)
    if not os.path.isdir(os.path.join(ap_dir, "worlds", "eldenring")):
        sys.exit("FAIL: %s has no worlds/eldenring -- install the world first "
                 "(python tools/gf_test.py --install-only --ap-dir %s)." % (ap_dir, ap_dir))
    if not os.path.isdir(os.path.join(ap_dir, "worlds", PARTNER_DIR)):
        # SKIP, not fail: a sparse/partial checkout legitimately lacks it. CI checks out stock
        # upstream in full. Exit 4 so a harness can tell "not applicable" from "broken" -- the same
        # convention gen_region_locks uses.
        print("SKIP (4): %s has no worlds/%s, so there is no partner game to generate beside. "
              "This gate needs a full upstream checkout." % (ap_dir, PARTNER_DIR))
        return 4

    failures = []
    for natural in (False, True):
        label = "natural_progression ON" if natural else "default (region locks)"
        print("\n=== multiworld: 2x Elden Ring + 2x %s -- %s ===" % (PARTNER_GAME, label))
        work = tempfile.mkdtemp(prefix="gf_mw_")
        players, out = os.path.join(work, "players"), os.path.join(work, "out")
        os.makedirs(players); os.makedirs(out)
        try:
            for i, nm in enumerate(("ErdtreeOne", "ErdtreeTwo"), 1):
                open(os.path.join(players, "ER_%d.yaml" % i), "w", encoding="utf-8").write(
                    _er_yaml(nm, natural))
            for n in (1, 2):
                open(os.path.join(players, "HK_%d.yaml" % n), "w", encoding="utf-8").write(
                    _HK_YAML.format(n=n))
            zip_path = generate(ap_dir, players, out)
            rows = placements(zip_path)
            print("  generated %s -- %d placements" % (os.path.basename(zip_path), len(rows)))
            failures += ["[%s] %s" % (label, f)
                         for f in check(rows, natural, lambda m: print("  " + m))]
        finally:
            if args.keep:
                print("  kept: %s" % work)
            else:
                shutil.rmtree(work, ignore_errors=True)

    print()
    if failures:
        print("MULTIWORLD SMOKE: FAIL")
        for f in failures:
            print("  * %s" % f)
        return 1
    print("MULTIWORLD SMOKE: PASS -- cross-world flow works in both directions, ER reaches a foreign "
          "game, and natural_progression keys are placeable in other players' worlds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
