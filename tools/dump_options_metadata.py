#!/usr/bin/env python3
"""
dump_options_metadata.py -- extract the ER apworld's full option surface to JSON, ast-only.

The yaml options wizard (wizard/wizard.html) renders ENTIRELY from this JSON, so it is
structurally incapable of describing an option that doesn't exist in options.py. Never
hand-edit wizard/options-metadata.json; re-run this instead.

Parses Archipelago/worlds/eldenring/options.py with `ast` (NO import of AP, NO regex
string-pairing -- runs on any Python 3.8+, no AP env). Core classes used directly as
EROptions fields (DeathLink) are resolved by ast-parsing Archipelago/Options.py, with a
built-in fallback if the core file is absent.

Extracted per option class: yaml key (EROptions field name, canonical order), class name,
base kind (choice/toggle/range/set/list/text), display_name, full docstring, default,
choice values, range bounds, valid_keys (including the `valid_keys = valid_keys | {...}`
folding pattern), and group membership from `option_groups`.

Also the single source of truth for the wizard PRESETS: emitted into the JSON and,
with --presets, written out as standalone presets/*.yaml.

Usage:
    python tools/dump_options_metadata.py              # write wizard/options-metadata.json
    python tools/dump_options_metadata.py --presets    # also write presets/*.yaml
    python tools/dump_options_metadata.py --inject     # also inline the JSON into wizard/wizard.html
    python tools/dump_options_metadata.py --check      # exit 1 if committed JSON is stale (CI drift gate)

Round-trip guarantee: every EROptions field appears in the JSON with a non-empty
description (enforced here AND by worlds/eldenring/tests/test_options_descriptions.py).
"""
import ast
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
OPTIONS_REL = os.path.join("Archipelago", "worlds", "eldenring", "options.py")
OPTIONS = os.path.join(ROOT, OPTIONS_REL)
CORE_OPTIONS = os.path.join(ROOT, "Archipelago", "Options.py")
OUT_JSON = os.path.join(ROOT, "wizard", "options-metadata.json")
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
PRESETS_DIR = os.path.join(ROOT, "presets")

# Leaf base classes we understand, mapped to the wizard's control kinds.
LEAF_KINDS = {
    "Choice": "choice", "TextChoice": "choice",
    "Toggle": "toggle", "DefaultOnToggle": "toggle",
    "Range": "range", "NamedRange": "range",
    "OptionSet": "set", "ItemSet": "set", "LocationSet": "set",
    "OptionList": "list",
    "FreeText": "text",
}

# Fallback metadata for core classes if Archipelago/Options.py can't be parsed.
CORE_FALLBACK = {
    "DeathLink": {
        "base": "Toggle",
        "display_name": "Death Link",
        "description": "When you die, everyone who enabled death link dies. Of course, "
                       "the reverse is true too.",
        "default": False,
    },
}

# ---------------------------------------------------------------------------
# PRESETS -- the wizard's starting points, also written as presets/*.yaml.
# Values use yaml-facing names (choice names as strings). Validated against the
# extracted metadata below, so a stale key or value fails the dump loudly.
# ---------------------------------------------------------------------------
PRESETS = [
    {
        "id": "first_run",
        "title": "First Run",
        "tagline": "Base game, forgiving, smaller check pool.",
        "description": "Your first randomizer seed. Trimmed check pool (skips low-value "
                       "filler pickups), no weapon stat requirements, received weapons "
                       "arrive fully upgraded, and leveling works from the start.",
        "values": {
            "location_pool": "trimmed",
            "no_weapon_requirements": True,
            "auto_upgrade": True,
            "early_leveling": True,
        },
    },
    {
        "id": "short_solo",
        "title": "Short Solo",
        "tagline": "A 3-4 hour Capital run: four regions, then Morgott.",
        "description": "The short 'reach Leyndell and defeat Morgott' goal with only four "
                       "overworld regions kept. Trimmed pool and early leveling keep the "
                       "pace up.",
        "values": {
            "ending_condition": "capital",
            "num_regions": 4,
            "location_pool": "trimmed",
            "early_leveling": True,
        },
    },
    {
        "id": "multiworld_sync",
        "title": "Multiworld Sync",
        "tagline": "A polite footprint for playing with friends.",
        "description": "Tuned for a shared session: the trimmed pool keeps your slice of "
                       "the multiworld reasonable, and no weapon requirements means "
                       "whatever the other worlds send you is immediately usable.",
        "values": {
            "location_pool": "trimmed",
            "no_weapon_requirements": True,
        },
    },
    {
        "id": "full_dlc_journey",
        "title": "Full DLC Journey",
        "tagline": "Everything: base game + Shadow of the Erdtree.",
        "description": "The complete tour. DLC regions, checks, and items join the pool, "
                       "and you won't be required to enter the Land of Shadow until after "
                       "reaching the Consecrated Snowfield.",
        "values": {
            "enable_dlc": True,
            "dlc_timing": "late",
        },
    },
]


def _base_name(b):
    if isinstance(b, ast.Name):
        return b.id
    if isinstance(b, ast.Attribute):
        return b.attr
    return None


def _class_attrs(cls):
    """Class-body simple assignments, with the `x = x | {...}` union-folding pattern."""
    out = {}
    for n in cls.body:
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)):
            continue
        name = n.targets[0].id
        v = n.value
        # frozenset() / set() with no args -> empty
        if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                and v.func.id in ("frozenset", "set") and not v.args):
            out[name] = []
            continue
        # x = x | {literal}  (ExtraRegionLocks valid_keys folding)
        if (isinstance(v, ast.BinOp) and isinstance(v.op, ast.BitOr)
                and isinstance(v.left, ast.Name) and v.left.id == name
                and name in out):
            try:
                out[name] = sorted(set(out[name]) | set(ast.literal_eval(v.right)))
            except Exception:
                pass
            continue
        try:
            val = ast.literal_eval(v)
        except Exception:
            continue
        if isinstance(val, (set, frozenset)):
            val = sorted(val)
        out[name] = val
    return out


def _parse_classes(path):
    # NUL-strip: a sandbox mount write can null-pad a shrinking overwrite; real Python
    # source never contains NULs, so stripping is safe (and idempotent on clean files).
    # source_sha256 is taken over the CLEANED text so all environments agree.
    src = open(path, "r", encoding="utf-8", errors="replace").read().replace("\x00", "")
    tree = ast.parse(src)
    return src, tree, {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}


def _resolve_base(name, local, core, seen=None):
    """Walk the inheritance chain (local classes, then core) to a leaf in LEAF_KINDS."""
    seen = seen or set()
    if name in LEAF_KINDS:
        return name
    for classes in (local, core):
        c = classes.get(name)
        if c is None:
            continue
        for b in c.bases:
            bn = _base_name(b)
            if bn is None or bn in seen:
                continue
            leaf = _resolve_base(bn, local, core, seen | {name})
            if leaf:
                return leaf
    return None


def extract():
    src, tree, local = _parse_classes(OPTIONS)
    core = {}
    if os.path.isfile(CORE_OPTIONS):
        try:
            _, _, core = _parse_classes(CORE_OPTIONS)
        except Exception:
            core = {}

    ero = local.get("EROptions")
    if ero is None:
        sys.exit("[FAIL] EROptions dataclass not found in options.py")
    fields = [(n.target.id, n.annotation.id)
              for n in ero.body
              if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
              and isinstance(n.annotation, ast.Name)]

    # option_groups -> {ClassName: (group_name, collapsed)}
    group_of, groups = {}, []
    for n in tree.body:
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "option_groups"):
            continue
        for el in n.value.elts:
            if not (isinstance(el, ast.Call) and _base_name(el.func) == "OptionGroup"):
                continue
            gname = ast.literal_eval(el.args[0])
            members = [_base_name(e) for e in el.args[1].elts]
            collapsed = any(kw.arg == "start_collapsed" and ast.literal_eval(kw.value)
                            for kw in el.keywords)
            groups.append({"name": gname, "collapsed": collapsed, "classes": members})
            for m in members:
                group_of[m] = (gname, collapsed)

    def describe(cls_name):
        cls, is_core = local.get(cls_name), False
        if cls is None:
            cls, is_core = core.get(cls_name), True
        if cls is None:
            fb = CORE_FALLBACK.get(cls_name)
            if not fb:
                sys.exit(f"[FAIL] option class {cls_name} not found in options.py or core Options.py")
            return dict(fb, kind=LEAF_KINDS[fb["base"]], choices=None, range=None,
                        valid_keys=None, casefold=False)
        leaf = _resolve_base(cls_name, local, core)
        if leaf is None:
            sys.exit(f"[FAIL] cannot resolve base kind of {cls_name}")
        kind = LEAF_KINDS[leaf]
        cv = _class_attrs(cls)
        doc = ast.get_docstring(cls) or ""
        if not doc and is_core and cls_name in CORE_FALLBACK:
            doc = CORE_FALLBACK[cls_name]["description"]
        d = {
            "base": leaf, "kind": kind,
            "display_name": cv.get("display_name", cls_name),
            "description": doc,
            "choices": None, "range": None, "valid_keys": None, "casefold": False,
            "default": None,
        }
        if kind == "choice":
            opts = sorted((v, k[len("option_"):]) for k, v in cv.items()
                          if k.startswith("option_") and isinstance(v, int))
            d["choices"] = [{"name": nm, "value": v} for v, nm in opts]
            dft = cv.get("default", opts[0][0] if opts else 0)
            byval = {v: nm for v, nm in opts}
            d["default"] = byval.get(dft, dft)
        elif kind == "toggle":
            d["default"] = bool(cv.get("default", 1 if leaf == "DefaultOnToggle" else 0))
        elif kind == "range":
            d["range"] = {"start": cv.get("range_start", 0), "end": cv.get("range_end", 0)}
            d["default"] = cv.get("default", cv.get("range_start", 0))
        elif kind in ("set", "list"):
            vk = cv.get("valid_keys")
            if vk is None:
                vk = cv.get("valid_keys_casefold")
                d["casefold"] = vk is not None
            d["valid_keys"] = sorted(vk) if vk else []
            dflt = cv.get("default", [])
            d["default"] = list(dflt) if isinstance(dflt, (list, tuple)) else []
        else:  # text
            d["default"] = cv.get("default", "")
        return d

    options = []
    for key, cls_name in fields:
        d = describe(cls_name)
        g = group_of.get(cls_name)
        options.append({
            "key": key, "class": cls_name, "kind": d["kind"], "base": d["base"],
            "display_name": d["display_name"], "description": d["description"],
            "default": d["default"], "choices": d["choices"], "range": d["range"],
            "valid_keys": d["valid_keys"], "casefold": d["casefold"],
            "group": g[0] if g else None, "group_collapsed": g[1] if g else False,
        })

    # Round-trip guarantee: every field carries a non-empty description.
    missing = [o["key"] for o in options if not o["description"].strip()]
    if missing:
        sys.exit(f"[FAIL] options with no description: {', '.join(missing)} "
                 "(the wizard cannot explain these -- fix the docstrings)")

    validate_presets(options)

    return {
        "schema": 1,
        "game": "EldenRing",
        "source": OPTIONS_REL.replace(os.sep, "/"),
        "source_sha256": hashlib.sha256(src.encode("utf-8")).hexdigest(),
        "field_order": [k for k, _ in fields],
        "groups": [{"name": g["name"], "collapsed": g["collapsed"],
                    "options": [o["key"] for o in options if o["class"] in g["classes"]]}
                   for g in groups],
        "ungrouped": [o["key"] for o in options if o["group"] is None],
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
        "game: EldenRing",
        "",
        "EldenRing:",
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
    meta = extract()
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
        print("[ok] wizard metadata is current (%d options, %d groups, %d ungrouped)"
              % (len(meta["options"]), len(meta["groups"]), len(meta["ungrouped"])))
        return 0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(fresh)
    print("[ok] wrote %s (%d options, %d groups; ungrouped: %s)"
          % (os.path.relpath(OUT_JSON, ROOT), len(meta["options"]), len(meta["groups"]),
             ", ".join(meta["ungrouped"]) or "none"))
    if "--presets" in argv:
        write_presets(meta)
    if "--inject" in argv:
        inject(meta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
