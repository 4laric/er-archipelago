#!/usr/bin/env python3
"""Generate the sweep-flag -> boss-name table for the client's F6 tracker.

Emits `crates/er-logic/src/sweep_boss_names.rs` from `greenfield/eldenring/tables/boss_healthbars.py`
(BOSS_HEALTHBARS: defeat flag -> (map, arena_map, kind, display name)).

WHY THIS EXISTS. The tracker's sweep rows already prefer a boss name over a region name -- the
field is `SweepGroupView::boss` and `group_label` has always used it. But the client only ever
learns a name from `bossLockItems`, which a seed emits only when boss LOCKS are on. Every other
seed reports `0 boss-lock def(s)` and every row degrades to its region, so boblerrr's Scadu Altus
read as EIGHT rows all called "Scadu Altus", separable only by a raw flag number:

    Scadu Altus -- 0/3 checks [flag 25000800] -- waiting on the boss
    Scadu Altus -- 0/19 checks [flag 41010800] -- waiting on the boss
    Scadu Altus -- 1/22 checks [flag 2047450800] -- waiting on the boss

He asked, reasonably: "would be nice if this said what boss it is".

WHY A BAKED TABLE AND NOT A SLOT KEY. The names are STATIC GAME DATA -- seed-invariant, identical
for every apworld. A new slot_data key would move CONTRACT_HASH and force a lockstep version bump
in both repos to carry a label. This is the same argument (and the same generator shape) as
tools/gen_region_locks.py and tools/gen_location_regions.py.

PRECEDENCE IS UNCHANGED: `bossLockItems` still WINS when present. This is a FALLBACK for the
seeds that ship none, which is most of them.

ASCII ONLY, ENFORCED BELOW. Tracker rows are drawn by the GAME, whose font has no glyph for an
em-dash (the 2026-07-31 "Altus ? enemy scaling" screenshot). All 231 names are ASCII today; the
generator refuses rather than shipping a row that renders as a box.

    python tools/gen_sweep_boss_names.py            # regenerate + wire lib.rs
    python tools/gen_sweep_boss_names.py --check    # CI drift gate (0 ok / 1 stale / 4 no client)
"""
import argparse
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GF = os.path.join(REPO, "greenfield", "eldenring")
OUT_RS = os.path.join(REPO, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "sweep_boss_names.rs")
LIB_RS = os.path.join(REPO, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "lib.rs")
MOD_LINE = "pub mod sweep_boss_names;"


def load_healthbars():
    """BOSS_HEALTHBARS from the generated pure-data module (no AP env needed)."""
    spec = importlib.util.spec_from_file_location(
        "er_gf_boss_healthbars", os.path.join(GF, "tables", "boss_healthbars.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    table = dict(mod.BOSS_HEALTHBARS)
    if not table:
        raise SystemExit("FATAL: boss_healthbars.py has an empty BOSS_HEALTHBARS")
    return table


# DISPLAY-ONLY fallbacks for the five entries whose DisplayBossHealthBar nameId has no NpcName FMG
# row, so BOSS_HEALTHBARS carries a blank name for them. Without these the tracker draws each of
# their sweep rows as `unidentified boss -- checks hidden until fired [flag 34110800]`.
#
# 🛑 THESE LIVE HERE AND NOT IN boss_healthbars.py, AND THE DISTINCTION IS LOAD-BEARING. A BLANK
# NAME IN THAT TABLE IS A SEMANTIC MARKER, NOT A MISSING LABEL: `contract.sweep_slot_skips()`
# DERIVES its skip set from it ("a trigger BOSS_HEALTHBARS cannot name ... we cannot vouch for one"),
# which is the #672 fix for bobler's two stranded progression checks, and gen_data's
# `_unspawned_candidate` reads it as one of the unspawned-boss tells. Filling the names at the
# source was tried on 2026-09-09 and un-skipped 34100800 and 34110800 -- the exact regression #672
# exists to prevent -- and turned 29 location NAMES red by growing a `may be sweep-granted by` tail
# on triggers the world has ruled it cannot vouch for. So the world keeps its blank, and only the
# CLIENT'S DISPLAY STRING is filled in, which is all the tracker ever wanted.
#
# 🛑 EVERY ONE IS THE ARENA, NOT A CHARACTER. Four of the five are exactly the entries
# `greenfield/arena_graces.tsv` files under `# unresolved_bosses`, and 34150800 was falsified IN
# GAME as EMEVD-only (2026-08-05, test_gf_unspawned_field_boss.py). There is no character to name:
# an invented plausible one would put a name on a row the player will never see standing there,
# which is worse than the flag number it replaces. That also fits what this table already IS -- see
# the emitted doc comment below: a sweep row names WHICH FIGHT PAYS THIS OUT, not who is on screen.
DISPLAY_NAME_FALLBACKS = {
    # m30_13 = Auriza Side Tomb: every member of DUNGEON_SWEEPS[30130810] in tables/data.py reads
    # "... Auriza Side Tomb". 30130800 in the same map is 'Grave Warden Duelist'; the 810 is that
    # map's second healthbar entity and the corpus names no occupant for it.
    30130810: "Auriza Side Tomb boss",
    # m34_10 = Divine Tower of Limgrave -- named outright by
    # greenfield/eldenring/tests/test_gf_sweep_slot_skips.py ("`34100800` is the Divine Tower of
    # Limgrave: BOSS_HEALTHBARS records an EMPTY name"), and by its members' place names.
    34100800: "Divine Tower of Limgrave boss",
    # m34_11 = Divine Tower of Liurnia: m34_12/13/14 are the West Altus / Caelid / East Altus Divine
    # Towers per data.py's location names, and this one's arena region is 'Liurnia'. Its five
    # members all read "Study Hall Entrance", the tower's Carian Study Hall approach.
    34110800: "Divine Tower of Liurnia boss",
    # m34_15 = Isolated Divine Tower -- named outright by
    # greenfield/eldenring/tests/test_gf_unspawned_field_boss.py.
    34150800: "Isolated Divine Tower boss",
    # m60_41_33 = Fourth Church of Marika, Weeping Peninsula -- named outright by boss_sweeps.py's
    # own note on this flag, and by its members ("Sacred Tear - Fourth Church of Marika").
    1041330800: "Fourth Church of Marika boss",
}


def load_rows():
    """(flag, name) sorted by flag. Non-ASCII names are a hard error, not a warning."""
    rows = []
    healthbars = load_healthbars()
    for flag in DISPLAY_NAME_FALLBACKS:
        if flag not in healthbars:
            print(f"WARNING: DISPLAY_NAME_FALLBACKS has flag {flag}, which BOSS_HEALTHBARS does not "
                  "key -- stale fallback, delete it.")
        elif str(healthbars[flag][3] or "").strip():
            print(f"WARNING: DISPLAY_NAME_FALLBACKS has flag {flag}, which BOSS_HEALTHBARS now NAMES "
                  f"({healthbars[flag][3]!r}) -- the game's own name wins; delete the fallback.")
    for flag, entry in healthbars.items():
        name = entry[3] if len(entry) > 3 else None
        # The datamined name always wins; the fallback only speaks where the FMG had no row.
        name = name or DISPLAY_NAME_FALLBACKS.get(int(flag))
        if not name:
            continue
        if not name.isascii():
            raise SystemExit(
                f"FATAL: boss name for flag {flag} is not ASCII ({name!r}). In-game text is drawn "
                "by the game's own font, which has no glyph for non-ASCII -- fix the source name "
                "in boss_healthbars.py rather than relaxing this check.")
        rows.append((int(flag), name))
    return sorted(rows)


def render_rs(rows):
    out = [
        "// @generated by tools/gen_sweep_boss_names.py -- DO NOT EDIT BY HAND.",
        "// Source: greenfield/eldenring/tables/boss_healthbars.py (BOSS_HEALTHBARS).",
        "// Regenerate: python tools/gen_sweep_boss_names.py   (AP-env-free, pure greenfield data)",
        "//",
        "// STATIC GAME DATA: boss-defeat flag -> display name. Seed-invariant, so it is baked",
        "// rather than carried in slot_data -- a new wire key would move CONTRACT_HASH to ship a",
        "// label. `bossLockItems` still WINS when a seed provides it; this is the fallback for the",
        "// seeds that do not, which is most of them.",
        "",
        "/// Boss-defeat flag -> display name, sorted by flag (binary search).",
        "///",
        "/// 🛑 THIS IS THE ARENA'S VANILLA BOSS, which is the right answer for a SWEEP row and not",
        "/// always the thing the player is looking at. Sweeps are ARENA-keyed -- the reward follows",
        "/// the room, not the character -- so naming the room's boss says WHICH FIGHT PAYS THIS OUT.",
        "/// Under enemy randomisation someone else is standing there, and the row will not match the",
        "/// health bar on screen. That is a known and accepted mismatch: a name that is sometimes",
        "/// wrong about the occupant beats a bare flag number that is never right about anything.",
        f"pub const SWEEP_BOSS_NAMES: [(u32, &str); {len(rows)}] = [",
    ]
    for flag, name in rows:
        # 🛑 json.dumps, NOT repr()+quote-swap. Python's repr switches to DOUBLE quotes when the
        # string contains an apostrophe, so swapping ' -> " turned `Rogier's Rapier` into
        # `"Rogier"s Rapier"` and the crate would not parse ("prefix `Rogier` is unknown"). JSON
        # string escaping is a subset of Rust's for this data (quotes and backslashes), and it is
        # the escaping rule rather than a guess about quoting style.
        out.append(f"    ({flag}, {json.dumps(name)}),")
    out += [
        "];",
        "",
        "/// Display name for a sweep trigger flag, if this is a known boss-defeat flag.",
        "pub fn boss_name(flag: u32) -> Option<&'static str> {",
        "    SWEEP_BOSS_NAMES",
        "        .binary_search_by_key(&flag, |&(f, _)| f)",
        "        .ok()",
        "        .map(|i| SWEEP_BOSS_NAMES[i].1)",
        "}",
        "",
        "#[cfg(test)]",
        "mod tests {",
        "    use super::*;",
        "",
        "    /// binary_search demands it, and the generator sorts -- but a hand edit would not.",
        "    #[test]",
        "    fn the_table_is_sorted_by_flag() {",
        "        assert!(SWEEP_BOSS_NAMES.windows(2).all(|w| w[0].0 < w[1].0));",
        "    }",
        "",
        "    /// Tracker rows are drawn by the GAME's font, which has no glyph for non-ASCII.",
        "    #[test]",
        "    fn every_name_is_ascii() {",
        "        for (flag, name) in SWEEP_BOSS_NAMES {",
        "            assert!(name.is_ascii(), \"flag {flag} name {name:?} is not ASCII\");",
        "        }",
        "    }",
        "",
        "    #[test]",
        "    fn an_unknown_flag_has_no_name() {",
        "        assert_eq!(boss_name(1), None);",
        "    }",
        "}",
        "",
    ]
    return "\n".join(out)


def lib_has_mod():
    try:
        return MOD_LINE in open(LIB_RS, encoding="utf-8").read()
    except OSError:
        return False


def wire_lib_rs():
    if lib_has_mod():
        return False
    src = open(LIB_RS, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    mods = [i for i, l in enumerate(lines) if l.startswith("pub mod ")]
    at = max(mods) + 1 if mods else len(lines)
    for i in mods:                      # keep the list alphabetical (rustfmt orders them)
        if lines[i] > MOD_LINE + "\n":
            at = i
            break
    lines.insert(at, MOD_LINE + "\n")
    open(LIB_RS, "w", encoding="utf-8", newline="\n").write("".join(lines))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rows = load_rows()
    new = render_rs(rows)
    if args.check:
        if not os.path.isdir(os.path.dirname(OUT_RS)):
            print("SKIP: the client submodule is not checked out -- cannot compare "
                  "sweep_boss_names.rs (git submodule update --init).")
            return 4
        try:
            cur = open(OUT_RS, encoding="utf-8").read()
        except FileNotFoundError:
            cur = ""
        if cur.replace("\r\n", "\n") != new or not lib_has_mod():
            print("STALE: sweep_boss_names.rs does not match boss_healthbars.py. "
                  "Run: python tools/gen_sweep_boss_names.py  (then commit the client submodule)")
            return 1
        print(f"OK: up to date ({len(rows)} bosses).")
        return 0
    try:
        _cur = open(OUT_RS, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    except OSError:
        _cur = None
    _wrote = _cur != new
    if _wrote:
        open(OUT_RS, "w", encoding="utf-8", newline="\n").write(new)
    wired = wire_lib_rs()
    print(f"{'Wrote' if _wrote else 'Unchanged'} {OUT_RS}: {len(rows)} bosses.")
    print("Wired lib.rs." if wired else "lib.rs already wired.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
