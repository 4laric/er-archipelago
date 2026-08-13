"""gf_multiworld_sweep.py -- MEASURE what a multiworld-facing option actually does, across its range.

This is an INSTRUMENT, not a gate. It prints a table and exits 0 whatever it finds. gf_multiworld_
smoke.py already asserts the cross-world properties we have decided on; this exists for the step
BEFORE that -- deciding what the option does at all, on numbers rather than on the docstring.

WHY IT EXISTS (2026-08-13). The smoke pins exactly two `confine_foreign_progression` values, 100 on
slot 1 and 50 on slot 2, and asserts a property of each. That is enough to catch a regression and not
enough to notice that slot 1 was receiving 7 of a partner's 93 placed advancement items while slot 2
took 86 -- a 7.5% share that any perturbation of the ER pool can drive to zero, which is exactly what
happened on PR #628. A pass/fail gate cannot tell "the option works" from "the option barely works".

THE DESIGN, and the one thing that makes it honest: every value gets its OWN ER SLOT IN ONE
MULTIWORLD. Not one generation per value -- that would compare across seeds, and fill is chaotic
enough that a cross-seed delta means nothing. Same seed, same partner, same competition, N slots
differing only in the option under test. The values then also compete WITH EACH OTHER, which is not a
confound: it is the multiworld condition, and it is precisely the condition the 7-vs-86 asymmetry
showed up in.

🛑 READ THE SHARE, NOT THE COUNT. A slot's raw "received 86" says nothing without the total placed
across the seed -- a partner with more advancement inflates every row. The SHARE column is the
comparable number, and the totals are printed so a share of a tiny total announces itself.
"""
import argparse
import glob
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load_smoke(ap_dir):
    """Import the smoke's plumbing rather than re-implementing generation and multidata parsing.

    One definition of "how we build a multiworld" -- if the smoke's yaml handling or its multidata
    read changes, this instrument moves with it instead of quietly measuring a different thing."""
    sys.path.insert(0, os.path.abspath(ap_dir))
    import gf_multiworld_smoke as smoke  # noqa: PLC0415
    return smoke


def _set_option(yaml_text, option, value):
    """Set `option: value` in the SHIPPED template, and refuse if it is not there.

    A silent no-op here would produce a table of identical rows and read as "the option does
    nothing", which is the most expensive possible wrong answer from an instrument."""
    out, n = re.subn(r"^(\s*)%s:.*$" % re.escape(option),
                     r"\g<1>%s: %s" % (option, value), yaml_text, count=1, flags=re.M)
    if not n:
        sys.exit("FAIL: release/EldenRing.yaml carries no `%s:` line, so this sweep would have "
                 "measured the DEFAULT %d times and called it a range. Add the option to the "
                 "template, or name one that is in it." % (option, 0))
    return out


def sweep(ap_dir, option, values, partner_slug, natural, keep):
    smoke = _load_smoke(ap_dir)   # puts the AP root on sys.path too -- multidata() imports Utils
    partner = next((p for p in smoke.PARTNERS if p.dir == partner_slug), None)
    if partner is None:
        sys.exit("FAIL: unknown partner %r; known: %s"
                 % (partner_slug, ", ".join(p.dir for p in smoke.PARTNERS)))
    work = tempfile.mkdtemp(prefix="gf_sweep_")
    players, outdir = os.path.join(work, "Players"), os.path.join(work, "out")
    os.makedirs(players); os.makedirs(outdir)
    try:
        base = open(os.path.join(ROOT, "release", "EldenRing.yaml"), encoding="utf-8").read()
        by_slot = {}
        for i, v in enumerate(values, start=1):
            s = re.sub(r"^name:.*$", "name: Erdtree%d" % i, base, count=1, flags=re.M)
            s = re.sub(r"^(\s*)num_regions:\s*\d+\s*$", r"\g<1>num_regions: 4", s, count=1, flags=re.M)
            if natural:
                s = re.sub(r"^(\s*)natural_progression:\s*false\s*$",
                           r"\g<1>natural_progression: true", s, count=1, flags=re.M)
            s = _set_option(s, option, v)
            open(os.path.join(players, "er%d.yaml" % i), "w", encoding="utf-8").write(s)
            by_slot[i] = v
        open(os.path.join(players, "partner.yaml"), "w", encoding="utf-8").write(
            smoke._partner_yaml(partner, 1))

        zpath = smoke.generate(ap_dir, players, outdir)
        slot_info, slot_data, locations = smoke.multidata(zpath)

        er_players = [p for p, info in slot_info.items() if info.game == "Elden Ring"]
        adv, useful = smoke._FLAG_ADVANCEMENT, smoke._FLAG_USEFUL
        # Denominators, printed so a big share of a small number cannot masquerade as a big number.
        total_foreign_adv = sum(
            1 for p in er_players for _l, (_i, ip, fl) in (locations.get(p) or {}).items()
            if ip != p and (fl & adv))
        print("\n== %s sweep: %s | partner %s | natural_progression %s | seed %s =="
              % (option, ",".join(str(v) for v in values), partner.game,
                 "ON" if natural else "off", smoke.SEED))
        print("   foreign advancement landing in ANY ER slot this seed: %d" % total_foreign_adv)
        print("\n   %-6s %-8s %8s %8s %7s %9s %9s %9s"
              % ("slot", option[:8], "recv", "share", "onsurf", "offsurf", "exported", "exp-usefl"))
        for p in sorted(er_players):
            rows = locations.get(p) or {}
            # 🛑 THE KEY IS `progressionSurfaceLocations`. Reading a name that is not there returns
            # an EMPTY set, every foreign item then counts as off-surface, and the column reads 0
            # on-surface for every value -- a meaningless answer that looks like a finding. It did
            # exactly that on the first run of this tool. The smoke guards the same way; a degraded
            # read has to announce itself rather than print a plausible zero.
            surface = set((slot_data.get(p) or {}).get("progressionSurfaceLocations") or ())
            if not surface:
                sys.exit("FAIL: slot %d emitted an EMPTY progressionSurfaceLocations, so the "
                         "on/off-surface split would be fabricated. Fix the read before trusting "
                         "any row of this table." % p)
            foreign = [(l, ip) for l, (_i, ip, fl) in rows.items() if ip != p and (fl & adv)]
            off = [l for l, _ip in foreign if l not in surface]
            exported = [(l, pl) for pl, r in locations.items() if pl != p
                        for l, (_i, ip, _f) in r.items() if ip == p]
            exp_useful = sum(1 for pl, r in locations.items() if pl != p
                             for _l, (_i, ip, fl) in r.items() if ip == p and (fl & useful))
            share = (100.0 * len(foreign) / total_foreign_adv) if total_foreign_adv else 0.0
            print("   %-6d %-8s %8d %7.1f%% %7d %9d %9d %9d"
                  % (p, by_slot.get(p, "?"), len(foreign), share,
                     len(foreign) - len(off), len(off), len(exported), exp_useful))
        print("\n   recv      = foreign ADVANCEMENT items placed in that ER slot")
        print("   share     = that slot's share of all foreign advancement placed in ER this seed")
        print("   onsurf    = of those, how many sat on the slot's progression surface")
        print("   exported  = that slot's own items placed in ANY other world")
        print("   exp-usefl = of those, how many are USEFUL-classified (the gear-reaches-them check)")
        if keep:
            print("\n   kept: %s" % work)
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ap-dir", required=True, help="an AP checkout with the world installed")
    ap.add_argument("--option", default="confine_foreign_progression")
    ap.add_argument("--values", default="0,25,50,75,100")
    ap.add_argument("--partner", default="doom_1993")
    ap.add_argument("--natural", action="store_true", help="natural_progression ON")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    vals = [v.strip() for v in a.values.split(",") if v.strip()]
    sweep(os.path.abspath(a.ap_dir), a.option, vals, a.partner, a.natural, a.keep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
