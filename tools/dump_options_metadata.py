#!/usr/bin/env python3
"""
dump_options_metadata.py -- extract the ER apworld's full option surface to JSON.

The yaml options wizard (wizard/wizard.html) renders ENTIRELY from this JSON, and the
standalone presets/*.yaml are emitted from the same run, so this tool is the single source
of truth for "what options exist and what they do".

WHY THIS IMPORTS THE WORLD (it used to ast-parse a static options.py)
--------------------------------------------------------------------
As of v0.2 the option surface is DYNAMIC: `GFOptions` is built at import time with
`make_dataclass(registry.collect_option_fields(...) minus FROZEN_OPTIONS)` (core.py). There
is no static `options.py` with an `EROptions` dataclass to parse -- the yaml-settable surface
only exists once the world is imported and the freeze is applied. So we install the world
into a pinned upstream Archipelago (via tools/gf_test.py, the one installer) and introspect
the REAL `GFOptions` dataclass. Zero drift: the wizard describes exactly the options the world
generates from.

Emitted per option: yaml key (canonical dataclass order), class name, kind
(choice/toggle/range/set/list/dict/text), display_name, docstring, default, choice values,
range bounds, valid_keys.

Usage (needs the pinned AP env; --ap-dir defaults to .ap-test/, bootstrapped on demand):
    python tools/dump_options_metadata.py              # write wizard/options-metadata.json
    python tools/dump_options_metadata.py --presets    # also write presets/*.yaml
    python tools/dump_options_metadata.py --inject     # also inline the JSON into wizard/wizard.html
    python tools/dump_options_metadata.py --check      # exit 1 if committed JSON is stale (CI drift gate)
    python tools/dump_options_metadata.py --ap-dir DIR # reuse an existing upstream AP checkout

Round-trip guarantee: every field appears in the JSON with a non-empty description
(enforced here AND by worlds/eldenring/tests/test_options_descriptions.py).
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
OUT_JSON = os.path.join(ROOT, "wizard", "options-metadata.json")
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
PRESETS_DIR = os.path.join(ROOT, "presets")
GAME = "Elden Ring"

# ---------------------------------------------------------------------------
# PRESETS -- the wizard's starting points, also written as presets/*.yaml.
# Values use yaml-facing names (choice names as strings, toggles as bools). Validated
# against the extracted metadata below, so a stale key/value/non-deviation fails loudly.
# Every preset carries ONLY deviations from the option defaults.
#
# NOTE: enable_dlc defaults ON (the class is DefaultOnToggle), but base game is the
# recommended/supported v0.2 config (DLC is experimental), so the base-game presets set
# `enable_dlc: false` explicitly -- that is a real deviation and the intended footprint.
# ---------------------------------------------------------------------------
PRESETS = [
    {
        "id": "first_run",
        "title": "First Run",
        "tagline": "Base game, a bounded first seed.",
        "description": "Your first randomizer seed: the base game with eight regions in play "
                       "(a real progression graph, but not the whole Shattering). Start at "
                       "Roundtable Hold, open regions as their Locks arrive.",
        "values": {"enable_dlc": False, "num_regions": 8},
    },
    {
        "id": "short_solo",
        "title": "Short Solo",
        "tagline": "A tight ~evening run: four regions.",
        "description": "Base game with only four regions kept -- a short, quick-to-finish "
                       "solo seed. Leyndell (the goal region) is always kept, so it stays "
                       "winnable.",
        "values": {"enable_dlc": False, "num_regions": 4},
    },
    {
        "id": "multiworld_sync",
        "title": "Multiworld Sync",
        "tagline": "A polite footprint for playing with friends.",
        "description": "Base game with six regions -- a moderate check pool that keeps your "
                       "slice of a shared multiworld reasonable while still being a real run.",
        "values": {"enable_dlc": False, "num_regions": 6},
    },
    {
        "id": "base_shattering",
        "title": "Base Shattering",
        "tagline": "The whole base game: all 17 regions.",
        "description": "The full base-game Shattering -- every base region in play "
                       "(num_regions 0), DLC off. The balanced default marathon.",
        "values": {"enable_dlc": False},
    },
    {
        "id": "dlc_only",
        "title": "DLC Only (experimental)",
        "tagline": "Only the Shadow of the Erdtree regions.",
        "description": "Every base-game region is sealed; only the 14 DLC regions are in "
                       "play, and the goal becomes holding every kept DLC Lock. DLC is "
                       "experimental in v0.2.",
        "values": {"dlc_only": True},
    },
]


# ---------------------------------------------------------------------------
# Import the live GFOptions from a pinned, upstream Archipelago with the world installed.
# ---------------------------------------------------------------------------
def load_gfoptions(ap_dir):
    """Install the current world into a pinned upstream AP (via gf_test, the one installer) and
    import its live GFOptions dataclass. Returns (GFOptions, pin)."""
    sys.path.insert(0, HERE)
    import gf_test  # the canonical installer; keeps AP pin + install logic in one place
    from pathlib import Path
    ap = Path(ap_dir).resolve()
    pin = gf_test.ap_pin()
    gf_test.ensure_ap(ap, pin)      # bootstrap the pinned upstream checkout if absent (refuses forks)
    gf_test.install_world(ap)       # copy the current world in
    # AP runs from its own root and its world loader scans ALL worlds -- some unrelated worlds fail
    # to import for missing native deps (harmless; eldenring loads). Silence that noise, and feed
    # a closed stdin so ModuleUpdate's "install missing dep?" prompt raises EOFError (caught by the
    # loader) instead of hanging.
    import contextlib
    sys.path.insert(0, str(ap))
    os.chdir(ap)
    sys.stdin = open(os.devnull, "r")
    import logging
    logging.disable(logging.CRITICAL)
    with open(os.devnull, "w") as devnull, \
            contextlib.redirect_stderr(devnull), contextlib.redirect_stdout(devnull):
        from worlds.eldenring.core import GFOptions
    return GFOptions, pin


def describe(key, cls):
    """Introspect one live Option subclass into the wizard's metadata shape."""
    import inspect
    from Options import (Choice, Toggle, Range, NamedRange, OptionSet, OptionList, OptionDict)
    doc = (inspect.getdoc(cls) or "").strip()
    d = {
        "key": key, "class": cls.__name__,
        "display_name": getattr(cls, "display_name", cls.__name__),
        "description": doc, "kind": None, "base": cls.__mro__[1].__name__,
        "default": None, "choices": None, "range": None, "valid_keys": None,
        "casefold": False, "group": None, "group_collapsed": False,
    }
    # Order matters: Range before Choice (NamedRange is a Range), Toggle before Choice
    # (a Toggle is a Choice subclass in AP).
    if issubclass(cls, (Range, NamedRange)):
        d["kind"] = "range"
        d["range"] = {"start": int(cls.range_start), "end": int(cls.range_end)}
        d["default"] = int(cls.default) if isinstance(cls.default, int) else cls.default
    elif issubclass(cls, Toggle):  # incl. DefaultOnToggle
        d["kind"] = "toggle"
        d["default"] = bool(cls.default)
    elif issubclass(cls, Choice):
        d["kind"] = "choice"
        seen, choices = set(), []
        for nm, val in getattr(cls, "options", {}).items():
            if val in seen:      # 'off'/'false' aliases collapse to one entry
                continue
            seen.add(val)
            choices.append({"name": nm, "value": val})
        d["choices"] = choices
        d["default"] = getattr(cls, "name_lookup", {}).get(cls.default, cls.default)
    elif issubclass(cls, OptionSet):
        d["kind"] = "set"
        d["valid_keys"] = sorted(getattr(cls, "valid_keys", []) or [])
        d["default"] = sorted(cls.default) if cls.default else []
    elif issubclass(cls, OptionList):
        d["kind"] = "list"
        d["valid_keys"] = sorted(getattr(cls, "valid_keys", []) or [])
        d["default"] = list(cls.default) if cls.default else []
    elif issubclass(cls, OptionDict):
        d["kind"] = "dict"
        d["valid_keys"] = sorted(getattr(cls, "valid_keys", []) or [])
        d["default"] = dict(cls.default) if isinstance(cls.default, dict) else {}
    else:
        d["kind"] = "text"
        d["default"] = getattr(cls, "default", "")
    return d


def extract(ap_dir):
    import dataclasses
    GFOptions, pin = load_gfoptions(ap_dir)
    from Options import PerGameCommonOptions
    # The yaml-tunable ER surface = the fields GFOptions ADDS on top of PerGameCommonOptions
    # (make_dataclass order = registry order, already minus FROZEN_OPTIONS).
    common = {f.name for f in dataclasses.fields(PerGameCommonOptions)}
    fields = [(f.name, f.type) for f in dataclasses.fields(GFOptions) if f.name not in common]

    options = [describe(k, c) for (k, c) in fields]

    missing = [o["key"] for o in options if not o["description"].strip()]
    if missing:
        sys.exit("[FAIL] options with no description: %s (fix the docstrings)" % ", ".join(missing))

    validate_presets(options)

    field_order = [k for k, _ in fields]
    # Deterministic surface hash (no timestamps) so --check can byte-compare.
    surface = json.dumps([[o["key"], o["kind"], o["default"], o["choices"], o["range"],
                           o["valid_keys"]] for o in options], sort_keys=True, default=str)
    return {
        "schema": 1,
        "game": GAME,
        "source": "greenfield/eldenring core.py -> GFOptions (imported, upstream AP %s)" % pin,
        "source_sha256": hashlib.sha256(surface.encode("utf-8")).hexdigest(),
        "field_order": field_order,
        "groups": [],
        "ungrouped": field_order,
        "options": options,
        "presets": PRESETS,
    }


def validate_presets(options):
    by_key = {o["key"]: o for o in options}
    for p in PRESETS:
        for k, v in p["values"].items():
            o = by_key.get(k)
            if o is None:
                sys.exit(f"[FAIL] preset {p['id']}: unknown option '{k}'")
            if o["kind"] == "choice":
                names = {c["name"] for c in o["choices"]}
                if v not in names:
                    sys.exit(f"[FAIL] preset {p['id']}: {k}={v!r} not in {sorted(names)}")
            elif o["kind"] == "toggle":
                if not isinstance(v, bool):
                    sys.exit(f"[FAIL] preset {p['id']}: {k}={v!r} should be a bool")
            elif o["kind"] == "range":
                if not (isinstance(v, int) and o["range"]["start"] <= v <= o["range"]["end"]):
                    sys.exit(f"[FAIL] preset {p['id']}: {k}={v!r} outside "
                             f"{o['range']['start']}..{o['range']['end']}")
            # presets should only carry deviations from the defaults
            if v == o["default"]:
                sys.exit(f"[FAIL] preset {p['id']}: {k}={v!r} equals the default -- drop it "
                         "(presets carry deviations only)")


# ---------------------------------------------------------------------------
# yaml emission (same shape the wizard emits; kept dependency-free on purpose)
# ---------------------------------------------------------------------------
def yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    # Quote all strings: guards the unquoted on/off/yes/no yaml-bool footgun.
    return '"%s"' % str(v).replace('"', '\\"')


def preset_yaml(meta, preset):
    lines = [
        "# %s -- %s" % (preset["title"], preset["tagline"]),
        "# Generated by tools/dump_options_metadata.py from %s" % meta["source"],
        "# (do not hand-edit; re-run the dump to regenerate)",
        "",
        "name: Player",
        "description: ER options wizard preset - %s" % preset["title"],
        "game: %s" % GAME,
        "",
        "%s:" % GAME,
    ]
    by_key = {o["key"]: o for o in meta["options"]}
    for k in meta["field_order"]:
        if k not in preset["values"]:
            continue
        v = preset["values"][k]
        o = by_key[k]
        if isinstance(v, list):
            lines.append("  %s: [%s]" % (k, ", ".join(yaml_scalar(x) for x in v)))
        else:
            lines.append("  %s: %s" % (k, yaml_scalar(v)))
        lines.append("  # ^ %s (default: %s)" % (o["display_name"], o["default"]))
    lines.append("")
    return "\n".join(lines)


def write_presets(meta):
    os.makedirs(PRESETS_DIR, exist_ok=True)
    for p in meta["presets"]:
        path = os.path.join(PRESETS_DIR, p["id"].replace("_", "-") + ".yaml")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(preset_yaml(meta, p))
        print("[ok] wrote %s" % os.path.relpath(path, ROOT))


def dumps(meta):
    # Deterministic (no timestamps) so --check can byte-compare. "</" escaped so the
    # blob is safe to inline inside a <script> tag.
    return json.dumps(meta, indent=1, ensure_ascii=False).replace("</", "<\\/") + "\n"


def inject(meta):
    if not os.path.isfile(WIZARD_HTML):
        sys.exit("[FAIL] --inject: %s not found" % WIZARD_HTML)
    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
    blob = ('<script id="er-options-metadata" type="application/json">\n'
            + dumps(meta) + "</script>")
    pat = re.compile(
        r'<script id="er-options-metadata" type="application/json">.*?</script>',
        re.S)
    if not pat.search(html):
        sys.exit("[FAIL] --inject: metadata <script> block not found in wizard.html")
    html = pat.sub(lambda _m: blob, html, count=1)
    with open(WIZARD_HTML, "w", encoding="utf-8", newline="") as f:
        f.write(html)
    print("[ok] injected metadata into %s" % os.path.relpath(WIZARD_HTML, ROOT))


def main(argv):
    ap_dir = os.path.join(ROOT, ".ap-test")
    if "--ap-dir" in argv:
        i = argv.index("--ap-dir")
        ap_dir = argv[i + 1]

    meta = extract(ap_dir)
    fresh = dumps(meta)

    if "--check" in argv:
        stale = []
        if not os.path.isfile(OUT_JSON):
            stale.append("wizard/options-metadata.json missing")
        elif open(OUT_JSON, "r", encoding="utf-8", newline="").read().replace("\r\n", "\n") != fresh:
            stale.append("wizard/options-metadata.json differs from a fresh dump")
        if os.path.isfile(WIZARD_HTML):
            html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
            if fresh.replace("\r\n", "\n") not in html.replace("\r\n", "\n"):
                stale.append("wizard/wizard.html inlined metadata differs from a fresh dump")
        if stale:
            print("[STALE] " + "; ".join(stale))
            print("        fix: python tools/dump_options_metadata.py --presets --inject")
            return 1
        print("[ok] wizard metadata is current (%d options)" % len(meta["options"]))
        return 0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(fresh)
    print("[ok] wrote %s (%d options)" % (os.path.relpath(OUT_JSON, ROOT), len(meta["options"])))
    if "--presets" in argv:
        write_presets(meta)
    if "--inject" in argv:
        inject(meta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
