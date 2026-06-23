#!/usr/bin/env python3
"""
patch_apworld_trap_grace_flags_20260622.py

Root-cause fix for the "warp/respawn strands you behind a one-way boss fog" softlock
(reported: Liurnia Caves Lock -> Lakeside Crystal Cave grace 73105, which sits PAST the
Bloodhound Knight's exit fog).

The real bug is list drift: there were FOUR independent grace-skip sets and the
BUNDLE_LOCK_GRACES path honored NONE of them, so a trap grace could ride a bundle lock
straight into a fog-sealed arena. (The dict's own comment even claimed "none are
boss/border" -- false for 73105 Lakeside and 73900 Magma Wyrm Makar.)

This patch introduces ONE source of truth -- grace_data.TRAP_GRACE_FLAGS -- and:
  1. grace_data.py: defines TRAP_GRACE_FLAGS (boss-arena + post-boss-fog graces) and
     auto-filters BUNDLE_LOCK_GRACES against it at module load (so no bundle lock can
     ever warp/light a trap grace, even once the bundle-grace merge is wired).
  2. __init__.py: unions TRAP_GRACE_FLAGS into the grace_rando builder's _gr_SKIP and
     fill_slot_data's _BOSS_GRACE_FLAGS so all three live code paths share the set and
     can't drift again.

Safe / count-neutral / slot_data-only. Idempotent, CRLF-preserving, non-clobbering
backups (.bak_trapgrace, .bak_trapgrace2, ...). Run on Windows from the repo root:
    python patch_apworld_trap_grace_flags_20260622.py
Then rebuild the apworld (build.ps1 -Apworld) and gen-test a region_lock seed.

To exclude another trap grace in the future, add its flag to TRAP_GRACE_FLAGS below --
it is then honored by grace_rando, fill_slot_data, and every bundle lock at once.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.join(HERE, "Archipelago", "worlds", "eldenring")
GRACE = os.path.join(WORLD, "grace_data.py")
INIT  = os.path.join(WORLD, "__init__.py")

# New trap graces to add on top of the boss-arena flags already used in __init__.
#   73105 = Lakeside Crystal Cave -- grace is PAST the Bloodhound Knight's one-way exit fog
#   73900 = Magma Wyrm Makar      -- in-arena boss grace (Ruin-Strewn Precipice)
NEW_TRAPS = (73105, 73900)
# The boss-arena set that already lives in __init__'s _BOSS_GRACE_FLAGS / _gr_SKIP.
EXISTING_BOSS = (71240, 71401, 76415, 76422, 76508, 76509, 76852, 76853, 76930, 76931)


def backup(path):
    i, dst = 1, path + ".bak_trapgrace"
    while os.path.exists(dst):
        i += 1
        dst = path + ".bak_trapgrace%d" % i
    with open(path, "rb") as f:
        data = f.read()
    with open(dst, "wb") as f:
        f.write(data)
    return dst


def read_keep_newlines(path):
    # newline='' preserves CRLF/LF exactly inside the returned string.
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write_keep_newlines(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def patch_grace_data(text):
    if "TRAP_GRACE_FLAGS" in text:
        return text, "SKIP (TRAP_GRACE_FLAGS already present)"
    nl = "\r\n" if "\r\n" in text else "\n"

    # Find the end of the BUNDLE_LOCK_GRACES dict: the closing brace on its own line
    # right after the "Spelunker's Torch" entry (last key in the literal).
    m = re.search(r'"Spelunker\'s Torch":[^\n]*\r?\n\}', text)
    if not m:
        raise RuntimeError("anchor (BUNDLE_LOCK_GRACES closing brace) not found")
    insert_at = m.end()

    boss = ", ".join(str(x) for x in EXISTING_BOSS)
    block_lines = [
        "",
        "",
        "# --- SINGLE SOURCE OF TRUTH for graces that must never be a lit/warp target -------",
        "# Boss-arena graces (warping in loads a dormant, no-AI boss behind a combat fog) and",
        "# post-boss-fog graces (warp/respawn strands you behind a ONE-WAY fog). Consumed by the",
        "# grace_rando builder (_gr_SKIP), fill_slot_data's region bundler (_BOSS_GRACE_FLAGS), and",
        "# the BUNDLE_LOCK_GRACES filter below. Add a flag here to exclude it EVERYWHERE at once.",
        "TRAP_GRACE_FLAGS = frozenset({",
        "    %s," % boss,
        "    73105,  # Lakeside Crystal Cave -- grace sits PAST the Bloodhound Knight one-way exit fog",
        "    73900,  # Magma Wyrm Makar -- in-arena boss grace (Ruin-Strewn Precipice)",
        "})",
        "",
        "# Strip any trap grace from every bundle: a bundle lock must never warp/light one. (The",
        "# 'none are boss/border' comment above was wrong for 73105 Lakeside and 73900 Makar.)",
        "BUNDLE_LOCK_GRACES = {",
        "    _lock: [_f for _f in _flags if _f not in TRAP_GRACE_FLAGS]",
        "    for _lock, _flags in BUNDLE_LOCK_GRACES.items()",
        "}",
    ]
    block = nl.join(block_lines) + nl
    return text[:insert_at] + block + text[insert_at:], "OK"


def patch_init(text):
    notes = []

    # 1) import TRAP_GRACE_FLAGS
    if "BUNDLE_LOCK_GRACES, TRAP_GRACE_FLAGS" not in text:
        new = text.replace(
            "REGION_GRACE_POINTS, BUNDLE_LOCK_GRACES",
            "REGION_GRACE_POINTS, BUNDLE_LOCK_GRACES, TRAP_GRACE_FLAGS",
            1,
        )
        if new == text:
            raise RuntimeError("import anchor 'REGION_GRACE_POINTS, BUNDLE_LOCK_GRACES' not found")
        text = new
        notes.append("import OK")
    else:
        notes.append("import SKIP")

    # 2) _gr_SKIP = frozenset({...})   -> union in TRAP_GRACE_FLAGS
    def union_set(name, t):
        pat = re.compile(r'(' + name + r'\s*=\s*frozenset\(\{[^}]*\}\))(\s*\|\s*TRAP_GRACE_FLAGS)?')
        mm = pat.search(t)
        if not mm:
            raise RuntimeError("anchor '%s = frozenset({...})' not found" % name)
        if mm.group(2):
            return t, "%s SKIP" % name
        new = t[:mm.end(1)] + " | TRAP_GRACE_FLAGS" + t[mm.end(1):]
        return new, "%s OK" % name

    text, n = union_set("_gr_SKIP", text);            notes.append(n)
    text, n = union_set("_BOSS_GRACE_FLAGS", text);   notes.append(n)
    return text, ", ".join(notes)


def parses(path, text):
    import ast
    try:
        ast.parse(text)
        return True
    except SyntaxError as e:
        print("  !! syntax error in patched %s: %s" % (os.path.basename(path), e))
        return False


def main():
    if not (os.path.exists(GRACE) and os.path.exists(INIT)):
        print("ERROR: run from the repo root (expected %s)" % WORLD)
        sys.exit(2)

    for path, fn in ((GRACE, patch_grace_data), (INIT, patch_init)):
        src = read_keep_newlines(path)
        out, note = fn(src)
        name = os.path.basename(path)
        if out == src:
            print("%-14s %s -- no change written" % (name, note))
            continue
        if not parses(path, out):
            print("%-14s ABORT: patched text does not parse; file untouched" % name)
            sys.exit(1)
        b = backup(path)
        write_keep_newlines(path, out)
        print("%-14s %s -- patched (backup %s)" % (name, note, os.path.basename(b)))

    # ---- verification: exec the patched grace_data in isolation and assert the cut ----
    ns = {}
    exec(compile(read_keep_newlines(GRACE), GRACE, "exec"), ns)
    trap = ns["TRAP_GRACE_FLAGS"]
    blg = ns["BUNDLE_LOCK_GRACES"]
    assert 73105 in trap and 73900 in trap, "TRAP_GRACE_FLAGS missing new flags"
    leaked = {lk: [f for f in fl if f in trap] for lk, fl in blg.items()}
    leaked = {lk: v for lk, v in leaked.items() if v}
    assert not leaked, "trap grace still in a bundle: %r" % leaked
    liur = blg.get("Spelunker's Ghostflame Torch", [])
    print("\nVERIFY: TRAP_GRACE_FLAGS = %s" % sorted(trap))
    print("VERIFY: Liurnia Caves bundle now = %s  (73105/73900 removed)" % liur)
    print("VERIFY: no trap grace remains in any bundle.  OK")


if __name__ == "__main__":
    main()
