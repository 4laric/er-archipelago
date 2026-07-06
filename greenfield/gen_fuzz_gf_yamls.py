#!/usr/bin/env python3
"""
gen_fuzz_gf_yamls.py -- random-yaml emitter for the GREENFIELD headline gate:
"flip any yaml option, in any combination -> clean gen or graceful reject".

Greenfield twin of ../gen_fuzz_yamls.py. It REUSES that module's game-agnostic
value samplers verbatim (gz.sample_value / gz._sample_range / gz.yaml_scalar /
gz.parse_pins / gz.SKIP_KEYS) -- only the OPTION SOURCE and GAME NAME differ:

  * options come from the INSTALLED greenfield world's dataclass (GFOptions),
    read via `worlds.eldenring_gf.GreenfieldEldenRingWorld.options_dataclass`,
    NOT a standalone options.py -- greenfield builds its dataclass dynamically
    from core + self-registered features, so we must read the live world.
  * the emitted game key is `Elden Ring (Greenfield)` (QUOTED -- spaces/parens).

Every emitted value is individually valid; what's fuzzed is the COMBINATION.
Expected downstream outcome (fuzz_gf.py): clean generation, or a raised
OptionError (graceful reject). FillError / traceback / hang / contract-violation
= a headline-gate failure, and the yaml file itself is the reproducer.

Reproducibility matches gen_fuzz_yamls exactly: case i uses
Random(fuzz_seed * 1000003 + i). The seed is printed, embedded in each yaml
header, and recorded in manifest.csv.

Usage (from the repo root, in an env with the greenfield world installed):
    python greenfield/gen_fuzz_gf_yamls.py --count 50 --out /tmp/gf-fuzz
    python greenfield/gen_fuzz_gf_yamls.py --count 20 --fuzz-seed 1 --full
    python greenfield/gen_fuzz_gf_yamls.py --count 50 --pin num_regions=0

Normally driven by fuzz_gf.py.
"""
from __future__ import annotations
import argparse
import dataclasses
import datetime
import os
import random
import sys
import typing

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

# Reuse the existing fuzzer's game-agnostic samplers -- do NOT reinvent them.
sys.path.insert(0, REPO_ROOT)
import gen_fuzz_yamls as gz  # noqa: E402

GAME = "Elden Ring (Greenfield)"


def load_gf_options_dataclass():
    """Return the greenfield GFOptions dataclass by importing the installed world.

    Unlike stock ER (a static options.py), greenfield assembles its dataclass at
    class-definition time from core + every self-registered feature, so the only
    faithful source is the live world's options_dataclass. Requires the AP env on
    sys.path (the orchestrator sets cwd to the AP dir before invoking us)."""
    try:
        from worlds.eldenring_gf import GreenfieldEldenRingWorld as W
    except Exception as e:  # pragma: no cover -- surfaces a clear message to the caller
        sys.exit(
            "gen_fuzz_gf_yamls: could not import worlds.eldenring_gf "
            "(run from the AP checkout dir with the world installed): " + repr(e)
        )
    return W.options_dataclass


def enumerate_options(dc):
    """-> list of (field_name, option_class) from the GFOptions dataclass, in order.
    Mirrors gen_fuzz_yamls.enumerate_options but on the greenfield dataclass."""
    hints = typing.get_type_hints(dc)
    return [(f.name, hints[f.name]) for f in dataclasses.fields(dc)]


def main(argv=None):
    ap = argparse.ArgumentParser(description="greenfield random-yaml fuzz emitter")
    ap.add_argument("--count", type=int, default=50, help="number of yamls to emit (default 50)")
    ap.add_argument("--fuzz-seed", type=int, default=0, help="batch seed; 0 = roll one and print it")
    ap.add_argument("--density", type=float, default=0.4,
                    help="probability each option is included per case (default 0.4)")
    ap.add_argument("--full", action="store_true", help="set EVERY option in every case (density 1.0)")
    ap.add_argument("--out", default="", help="output dir (default gen-test/gf-fuzz-yamls-<timestamp>)")
    ap.add_argument("--pin", action="append", metavar="KEY=VALUE",
                    help="force KEY: VALUE in every case (repeatable; value written verbatim)")
    args = ap.parse_args(argv)

    dc = load_gf_options_dataclass()
    import Options as APO  # resolvable: AP dir is on sys.path (orchestrator ensures it)

    opts = enumerate_options(dc)
    fuzz_seed = args.fuzz_seed or random.SystemRandom().randrange(1, 2 ** 31)
    density = 1.0 if args.full else max(0.0, min(1.0, args.density))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or os.path.join(HERE, "gen-test", "gf-fuzz-yamls-" + stamp)
    os.makedirs(out_dir, exist_ok=True)
    pins = gz.parse_pins(args.pin, {n for n, _ in opts})

    samplable = [(n, c) for n, c in opts if n not in gz.SKIP_KEYS]
    skipped_nodomain = []
    manifest_rows = []

    for i in range(1, args.count + 1):
        rng = random.Random(fuzz_seed * 1000003 + i)
        lines = []
        chosen = []
        for name, cls in samplable:
            if name in pins:
                continue
            if rng.random() >= density:
                continue
            sv = gz.sample_value(rng, cls, APO)
            if sv is None:
                if i == 1:
                    skipped_nodomain.append(name)
                continue
            kind, val = sv
            lines.append("  " + name + ": " + gz.yaml_scalar(kind, val))
            if kind == "list":
                chosen.append(name + "=" + (",".join(val) or "(empty)"))
            else:
                chosen.append(name + "=" + str(val))
        for k, v in pins.items():
            lines.append("  " + k + ": " + v)
            chosen.append(k + "=" + v)

        fname = "GF-fuzz-" + str(fuzz_seed) + "-" + ("%04d" % i) + ".yaml"
        header = [
            "# gen_fuzz_gf_yamls.py -- fuzz-seed " + str(fuzz_seed)
            + " case " + str(i) + "/" + str(args.count) + " -- " + stamp,
            "# reproduce: python greenfield/gen_fuzz_gf_yamls.py --fuzz-seed "
            + str(fuzz_seed) + " --count " + str(i) + " --density " + str(density),
            "# options set: " + str(len(lines)),
            "name: GFFuzz" + ("%04d" % i),
            "description: greenfield fuzz-seed " + str(fuzz_seed) + " case " + str(i),
            'game: "' + GAME + '"',
            '"' + GAME + '":',
        ]
        body_lines = lines if lines else ["  {}  # all defaults -- valid fuzz case"]
        body = "\n".join(header + body_lines) + "\n"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        manifest_rows.append((fname, i, len(lines), " ".join(chosen)))

    man_path = os.path.join(out_dir, "manifest.csv")
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("file,case,noptions,options_set\n")
        for fname, case, n, desc in manifest_rows:
            f.write(fname + "," + str(case) + "," + str(n) + ',"' + desc + '"\n')

    print("fuzz-seed : " + str(fuzz_seed))
    print("out dir   : " + out_dir)
    print("cases     : " + str(args.count) + "   density: " + str(density)
          + "   samplable options: " + str(len(samplable)))
    if pins:
        print("pinned    : " + ", ".join(k + "=" + v for k, v in pins.items()))
    if skipped_nodomain:
        print("skipped (no finite domain): " + ", ".join(skipped_nodomain))
    print("manifest  : " + man_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
