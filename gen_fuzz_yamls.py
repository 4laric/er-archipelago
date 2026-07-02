#!/usr/bin/env python3
"""
gen_fuzz_yamls.py -- random-yaml emitter for the CONTRIBUTING headline gate:
"flip any yaml option, in any combination -> clean gen or graceful reject".

Emits N yamls, each assigning a random-but-VALID value to a random subset of
ER options (plus the AP common options declared on the dataclass). Values are
sampled from the option classes themselves -- choices from cls.options, ranges
from range_start..range_end (edge-biased), sets/lists from valid_keys -- parsed
LIVE from worlds/eldenring/options.py, so new options are fuzzed automatically.

Every emitted value is individually valid; what's being fuzzed is the
COMBINATION. Expected outcomes downstream (gen_fuzz.ps1): clean generation, or
a raised OptionError. FillError / traceback / hang = a headline-gate failure,
and the yaml file itself is the reproducer.

Reproducibility: the whole batch is a pure function of --fuzz-seed (case i uses
Random(fuzz_seed * 1000003 + i)). The seed is printed, embedded in each yaml
header, and recorded in manifest.csv.

Usage (Windows, from the repo root -- needs the Archipelago checkout env):
    python gen_fuzz_yamls.py --count 50 --out gen-test\\fuzz-yamls-<ts>
    python gen_fuzz_yamls.py --count 50 --fuzz-seed 12345 --density 0.4
    python gen_fuzz_yamls.py --count 20 --full                # set EVERY option
    python gen_fuzz_yamls.py --count 50 --pin enable_dlc=false --pin ending_condition=\"capital\"

Normally driven by gen_fuzz.ps1.
"""
from __future__ import annotations
import argparse, dataclasses, datetime, importlib.util, os, random, sys, typing

HERE = os.path.dirname(os.path.abspath(__file__))
AP_DIR = os.path.join(HERE, "Archipelago")
OPTIONS_PY = os.path.join(AP_DIR, "worlds", "eldenring", "options.py")

# Free-form / dict-shaped AP common options: no finite value domain to sample.
# (OptionSet/OptionList fields with empty valid_keys are also auto-skipped.)
SKIP_KEYS = {
    "local_items", "non_local_items", "start_inventory", "start_inventory_from_pool",
    "start_hints", "start_location_hints", "exclude_locations", "priority_locations",
    "item_links", "plando_items",
}


def load_er_options_module():
    """Load worlds/eldenring/options.py standalone (its only imports are dataclasses
    and AP's Options module), with the Archipelago dir on sys.path for the latter.
    Avoids triggering the full worlds/__init__ loader."""
    if not os.path.isfile(OPTIONS_PY):
        sys.exit(f"gen_fuzz_yamls: options.py not found at {OPTIONS_PY} -- run from the repo root.")
    sys.path.insert(0, AP_DIR)
    spec = importlib.util.spec_from_file_location("er_fuzz_options", OPTIONS_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enumerate_options(mod):
    """-> list of (field_name, option_class) from the EROptions dataclass, in order."""
    hints = typing.get_type_hints(mod.EROptions)
    return [(f.name, hints[f.name]) for f in dataclasses.fields(mod.EROptions)]


def sample_value(rng: random.Random, cls, APO):
    """Sample one valid value for an option class.
    Returns (kind, value) or None if the option has no finite domain (skip).
    kind: 'choice' | 'bool' | 'int' | 'list'"""
    # Choice first (TextChoice etc. included) -- emit the NAME, quoted downstream
    # so yaml can't bool-ify off/on/yes/no.
    if isinstance(cls, type) and issubclass(cls, APO.Choice):
        names = sorted(cls.options)
        if not names:
            return None
        return ("choice", rng.choice(names))
    # NamedRange before Range (subclass): sometimes pick a special name.
    named_range = getattr(APO, "NamedRange", None)
    if named_range and isinstance(cls, type) and issubclass(cls, named_range):
        specials = sorted(getattr(cls, "special_range_names", {}) or {})
        if specials and rng.random() < 0.30:
            return ("choice", rng.choice(specials))
        return ("int", _sample_range(rng, cls))
    if isinstance(cls, type) and issubclass(cls, APO.Range):
        return ("int", _sample_range(rng, cls))
    if isinstance(cls, type) and issubclass(cls, APO.Toggle):
        return ("bool", rng.random() < 0.5)
    if isinstance(cls, type) and issubclass(cls, (APO.OptionSet, APO.OptionList)):
        vk = sorted(getattr(cls, "valid_keys", None) or [])
        if not vk:
            return None  # free-form -- nothing safe to invent (no invented IDs/names)
        n = rng.randint(0, min(4, len(vk)))
        return ("list", sorted(rng.sample(vk, n)))
    return None


def _sample_range(rng: random.Random, cls) -> int:
    start = int(getattr(cls, "range_start", 0))
    end = int(getattr(cls, "range_end", start))
    dflt = getattr(cls, "default", start)
    dflt = int(dflt) if isinstance(dflt, (int, bool)) else start
    # Edge-biased: min and max are where combos break.
    roll = rng.random()
    if roll < 0.25:
        return start
    if roll < 0.50:
        return end
    if roll < 0.60:
        return max(start, min(end, dflt))
    return rng.randint(start, end)


def yaml_scalar(kind: str, v) -> str:
    if kind == "bool":
        return "true" if v else "false"
    if kind == "int":
        return str(v)
    if kind == "choice":
        return f'"{v}"'  # ALWAYS quoted: the unquoted off/on/yes/no yaml-bool footgun
    if kind == "list":
        return "[" + ", ".join(f'"{x}"' for x in v) + "]"
    raise ValueError(kind)


def parse_pins(pin_args, valid_names):
    pins = {}
    for p in pin_args or []:
        if "=" not in p:
            sys.exit(f"gen_fuzz_yamls: --pin needs key=value, got {p!r}")
        k, v = p.split("=", 1)
        k = k.strip()
        if k not in valid_names:
            sys.exit(f"gen_fuzz_yamls: --pin key {k!r} is not an EROptions field")
        pins[k] = v.strip()  # written verbatim -- caller controls quoting
    return pins


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--count", type=int, default=50, help="number of yamls to emit (default 50)")
    ap.add_argument("--fuzz-seed", type=int, default=0, help="batch seed; 0 = roll one and print it")
    ap.add_argument("--density", type=float, default=0.4,
                    help="probability each option is included per case (default 0.4)")
    ap.add_argument("--full", action="store_true", help="set EVERY option in every case (density 1.0)")
    ap.add_argument("--out", default="", help="output dir (default gen-test/fuzz-yamls-<timestamp>)")
    ap.add_argument("--pin", action="append", metavar="KEY=VALUE",
                    help="force KEY: VALUE in every case (repeatable; value written verbatim)")
    args = ap.parse_args(argv)

    mod = load_er_options_module()
    import Options as APO  # resolvable now: AP_DIR is on sys.path

    opts = enumerate_options(mod)
    fuzz_seed = args.fuzz_seed or random.SystemRandom().randrange(1, 2**31)
    density = 1.0 if args.full else max(0.0, min(1.0, args.density))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or os.path.join(HERE, "gen-test", f"fuzz-yamls-{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    pins = parse_pins(args.pin, {n for n, _ in opts})

    samplable = [(n, c) for n, c in opts if n not in SKIP_KEYS]
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
            sv = sample_value(rng, cls, APO)
            if sv is None:
                if i == 1:
                    skipped_nodomain.append(name)
                continue
            kind, val = sv
            lines.append(f"  {name}: {yaml_scalar(kind, val)}")
            chosen.append(f"{name}={val if kind != 'list' else ','.join(val) or '(empty)'}")
        for k, v in pins.items():
            lines.append(f"  {k}: {v}")
            chosen.append(f"{k}={v}")

        fname = f"ER-fuzz-{fuzz_seed}-{i:04d}.yaml"
        body = "\n".join([
            f"# gen_fuzz_yamls.py -- fuzz-seed {fuzz_seed} case {i}/{args.count} -- {stamp}",
            f"# reproduce this exact file: python gen_fuzz_yamls.py --fuzz-seed {fuzz_seed} --count {i} --density {density}",
            f"# options set: {len(lines)}",
            f"name: Fuzz{i:04d}",
            f"description: fuzz-seed {fuzz_seed} case {i}",
            "game: EldenRing",
            "EldenRing:",
        ] + (lines if lines else ["  {}  # all defaults -- valid fuzz case"])) + "\n"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        manifest_rows.append((fname, i, len(lines), " ".join(chosen)))

    man_path = os.path.join(out_dir, "manifest.csv")
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("file,case,noptions,options_set\n")
        for fname, case, n, desc in manifest_rows:
            f.write(f'{fname},{case},{n},"{desc}"\n')

    print(f"fuzz-seed : {fuzz_seed}")
    print(f"out dir   : {out_dir}")
    print(f"cases     : {args.count}   density: {density}   samplable options: {len(samplable)}")
    if pins:
        print(f"pinned    : {', '.join(f'{k}={v}' for k, v in pins.items())}")
    if skipped_nodomain:
        print(f"skipped (no finite domain): {', '.join(skipped_nodomain)}")
    print(f"manifest  : {man_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
