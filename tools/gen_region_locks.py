#!/usr/bin/env python3
"""Generate the BAKED region-lock table for the client (bedrock interop).

Emits `crates/er-logic/src/region_locks.rs` from the apworld's OWN region-lock sources -- the
same two tables every seed's slot_data is built from:
  - greenfield/eldenring/region_open_flags.py  : REGION_OPEN_FLAGS (region -> warp-grace open flag)
  - greenfield/eldenring/region_play_ids.py    : REGION_PLAY_IDS  (region -> play_region ids,
    generated from greenfield/region_groups.py -- THE spine)

WHY A CLIENT COPY EXISTS AT ALL (and why it must be generated): both tables are STATIC GAME
DATA -- identical for every seed and every apworld. A foreign apworld (Bedrock's) has region
lock in AP logic but emits neither regionOpenFlags nor areaLockFlags, so the client had no way
to enforce it in-game. With the constants baked, a foreign world only has to NAME its lock
items "<Region> Lock" and enforcement works with zero slot_data support. slot_data still WINS
when present (region.rs parse); the baked table is a fallback for seeds that ship neither key.
A HAND-typed client copy of this geometry drifted repeatedly (see test_gf_data.py
GreenfieldAreaLockGeometry) -- which is why this file may only ever be written by this tool,
exactly like tools/gen_location_regions.py owns tracker_regions.rs.

AP-env-free: both are generated pure-data modules and import clean.

    python tools/gen_region_locks.py            # regenerate + wire lib.rs
    python tools/gen_region_locks.py --check    # CI drift gate (0 ok / 1 stale / 4 no client)
"""
import argparse
import ast
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GF = os.path.join(REPO, "greenfield", "eldenring")
AREA_LOCKS_PY = os.path.join(GF, "features", "area_locks.py")
OUT_RS = os.path.join(REPO, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "region_locks.rs")
LIB_RS = os.path.join(REPO, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "lib.rs")
MOD_LINE = "pub mod region_locks;"


def load_open_flags():
    """REGION_OPEN_FLAGS from the generated pure-data module (no AP env needed)."""
    spec = importlib.util.spec_from_file_location(
        "er_gf_region_open_flags", os.path.join(GF, "region_open_flags.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.REGION_OPEN_FLAGS)


def load_pending():
    """REGIONS_PENDING_BUCKET from the generated region_play_ids.py -- the regions whose play_region
    buckets are not measured yet. Empty for an apworld generated before that existed."""
    spec = importlib.util.spec_from_file_location(
        "er_gf_region_play_ids_p", os.path.join(GF, "region_play_ids.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return frozenset(getattr(mod, "REGIONS_PENDING_BUCKET", ()))


def load_play_ids():
    """REGION_PLAY_IDS from the GENERATED pure-data module (region_play_ids.py, emitted by
    gen_data.py as the inverse of greenfield/region_groups.py). It used to be AST-lifted from a
    hand table in features/area_locks.py; that table is gone -- one source now."""
    spec = importlib.util.spec_from_file_location(
        "er_gf_region_play_ids", os.path.join(GF, "region_play_ids.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    table = dict(mod.REGION_PLAY_IDS)
    if not table:
        raise SystemExit("FATAL: region_play_ids.py has an empty REGION_PLAY_IDS")
    return {str(k): [int(x) for x in v] for k, v in table.items()}


def load_rows():
    """[(region, lock_item, open_flag_or_None, [play_ids])] sorted by region.

    Invariants enforced here (a violation means the apworld's own tables are inconsistent,
    so FAIL the gen rather than bake a broken client table):
      - every region with an open flag has geometry (the same gap area_locks.slot_data
        hard-errors on for kept regions -- here it is checked for ALL of them);
      - no play_region id belongs to two regions (the kick-watch could not decide).
    Regions with geometry but NO open flag are kept (open_flag None): the client reports a
    matching foreign lock item as un-gateable instead of pretending the region cannot exist.
    """
    open_flags = load_open_flags()
    play_ids = load_play_ids()

    # PENDING regions: an open flag but no MEASURED kick geometry. This used to be FATAL, and the
    # instinct was right -- baking a region the client cannot enforce is how the Weeping and DLC locks
    # came to do nothing. But core._eligible_regions now DROPS these regions from the seed's pool
    # entirely (loudly), so no seed can contain one and the client will never be asked about it. A hard
    # stop here would block the bake for a region that cannot appear.
    #
    # So: SKIP them, and say so. They are excluded from the baked table exactly as they are excluded
    # from seeds -- the client reports an unmatched foreign lock as un-gateable rather than pretending
    # to enforce it. Anything flagged-without-geometry that is NOT on the declared pending list is still
    # FATAL: that is the real drift this guard exists to catch.
    pending = sorted(load_pending())
    flagged_without_geometry = sorted(set(open_flags) - set(play_ids))
    undeclared = [r for r in flagged_without_geometry if r not in pending]
    if undeclared:
        raise SystemExit("FATAL: region(s) with an open flag but no REGION_PLAY_IDS geometry, and NOT "
                         "declared in REGIONS_PENDING_BUCKET: " + ", ".join(undeclared))
    if flagged_without_geometry:
        print("WARNING: region(s) NOT baked -- their play_region buckets are unmeasured, so their locks "
              "cannot be enforced and core excludes them from seeds: "
              + ", ".join(flagged_without_geometry))
        open_flags = {r: f for r, f in open_flags.items() if r not in flagged_without_geometry}
    seen = {}
    for region, ids in play_ids.items():
        for pid in ids:
            if pid in seen:
                raise SystemExit(f"FATAL: play_region {pid} in both {seen[pid]!r} and {region!r}")
            seen[pid] = region
    return [(r, f"{r} Lock", open_flags.get(r), list(play_ids[r]))
            for r in sorted(play_ids)]


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_rs(rows):
    lines = []
    a = lines.append
    a("// @generated by tools/gen_region_locks.py -- DO NOT EDIT BY HAND.")
    a("// Sources: greenfield/eldenring/region_open_flags.py (REGION_OPEN_FLAGS) +")
    a("//          greenfield/eldenring/features/area_locks.py (REGION_PLAY_IDS).")
    a("// Regenerate: python tools/gen_region_locks.py   (AP-env-free, pure greenfield data)")
    a("//")
    a("// STATIC GAME DATA: region -> warp-grace open flag + play_region geometry. Seed-invariant;")
    a('// the only per-seed input is which "<Region> Lock" items exist. slot_data (areaLockFlags /')
    a("// regionOpenFlags) always WINS when present -- this table only feeds the foreign-apworld")
    a("// fallback (er_logic::region_lock::derive_region_locks).")
    a("")
    a("/// One baked region: its lock-item name, warp-grace open flag (None = geometry known but no")
    a("/// resolved open flag, so the region cannot be gated), and its play_region ids.")
    a("pub struct BakedRegionLock {")
    a("    pub region: &'static str,")
    a("    pub lock_item: &'static str,")
    a("    pub open_flag: Option<u32>,")
    a("    pub play_regions: &'static [i32],")
    a("}")
    a("")
    a("/// All baked regions, sorted by region name. play_region ids are globally unique")
    a("/// (generator-enforced), so a range derived per id can never point at two regions.")
    a("pub const REGION_LOCKS: &[BakedRegionLock] = &[")
    for region, lock, flag, ids in rows:
        f = f"Some({flag})" if flag is not None else "None"
        idl = ", ".join(str(i) for i in ids)
        a("    BakedRegionLock {")
        a(f'        region: "{esc(region)}",')
        a(f'        lock_item: "{esc(lock)}",')
        a(f"        open_flag: {f},")
        a(f"        play_regions: &[{idl}],")
        a("    },")
    a("];")
    a("")
    a('/// Look a lock-item NAME (e.g. "Caelid Lock") up in the baked table.')
    a("pub fn by_lock_item(name: &str) -> Option<&'static BakedRegionLock> {")
    a("    REGION_LOCKS.iter().find(|r| r.lock_item == name)")
    a("}")
    a("")
    a("#[cfg(test)]")
    a("mod generated_tests {")
    a("    use super::*;")
    a("")
    a("    #[test]")
    a("    fn nonempty_sorted_unique() {")
    a("        assert!(!REGION_LOCKS.is_empty());")
    a("        assert!(REGION_LOCKS.windows(2).all(|w| w[0].region < w[1].region));")
    a("        let mut ids: Vec<i32> = REGION_LOCKS.iter().flat_map(|r| r.play_regions.iter().copied()).collect();")
    a("        let n = ids.len();")
    a("        ids.sort_unstable();")
    a("        ids.dedup();")
    a('        assert_eq!(ids.len(), n, "play_region ids must be globally unique");')
    a("        assert!(REGION_LOCKS.iter().all(|r| !r.play_regions.is_empty()));")
    a("    }")
    a("")
    a("    #[test]")
    a("    fn lock_items_follow_the_naming_convention() {")
    a("        for r in REGION_LOCKS {")
    a('            assert_eq!(r.lock_item, format!("{} Lock", r.region));')
    a("            assert!(by_lock_item(r.lock_item).is_some());")
    a("        }")
    a('        assert!(by_lock_item("No Such Region Lock").is_none());')
    a("    }")
    a("}")
    a("")
    return "\n".join(lines)


def lib_has_mod():
    try:
        return MOD_LINE in open(LIB_RS, encoding="utf-8").read()
    except FileNotFoundError:
        return False


def wire_lib_rs():
    if lib_has_mod():
        return False
    text = open(LIB_RS, encoding="utf-8").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    # after region_lock_replay: rustfmt (reorder_modules) keeps `pub mod` lines sorted, and
    # region_lock_replay < region_locks bytewise -- anchoring after region_lock would unsort them.
    anchor = "pub mod region_lock_replay;"
    new = text.replace(anchor, anchor + nl + MOD_LINE, 1) if anchor in text \
        else text.rstrip("\r\n") + nl + MOD_LINE + nl
    open(LIB_RS, "w", encoding="utf-8", newline="").write(new)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rows = load_rows()
    new = render_rs(rows)
    if args.check:
        # Exit codes mirror tools/gen_location_regions.py / gen_manifest.py:
        #   0 = up to date | 1 = STALE (regenerate + commit) | 4 = submodule absent -> SKIP
        if not os.path.isdir(os.path.dirname(OUT_RS)):
            print("SKIP: the client submodule is not checked out -- cannot compare region_locks.rs "
                  "(git submodule update --init).")
            return 4
        try:
            cur = open(OUT_RS, encoding="utf-8").read()
        except FileNotFoundError:
            cur = ""
        if cur.replace("\r\n", "\n") != new or not lib_has_mod():
            print("STALE: region_locks.rs does not match the greenfield data it is generated FROM. "
                  "Run: python tools/gen_region_locks.py  (then commit the client submodule)")
            return 1
        print(f"OK: up to date ({len(rows)} regions).")
        return 0
    open(OUT_RS, "w", encoding="utf-8", newline="\n").write(new)
    wired = wire_lib_rs()
    flagged = sum(1 for r in rows if r[2] is not None)
    unflagged = [r[0] for r in rows if r[2] is None]
    pids = sum(len(r[3]) for r in rows)
    print(f"Wrote {OUT_RS}: {len(rows)} regions ({flagged} with open flags, {pids} play_region ids).")
    if unflagged:
        print("No open flag (geometry only, cannot be gated): " + ", ".join(unflagged))
    print("Wired lib.rs." if wired else "lib.rs already wired.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
