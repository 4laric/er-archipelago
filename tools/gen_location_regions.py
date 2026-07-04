#!/usr/bin/env python3
"""Generate the AP location metadata table for the tracker (SPEC-item-tracker.md).

Emits `crates/er-logic/src/tracker_regions.rs`. Sources (Windows AP env; the sandbox mount
truncates the 6k-line locations.py):
  - locations.py    : location_tables (ids + fine region), region_order headers, prominent/missable
  - map_region_data.py : coarse region keys that carry an open flag
  - grace_data.py   : REGION_LOCK_ITEM (coarse region -> lock item name)

Per AP location it emits: fine region (grouping), coarse region (the open-flag key that decides
in-logic), big_ticket (prominent), missable. Plus coarse-region -> lock-item, so the client can
resolve each coarse region to a live open-state flag via its region_open_flags table.

    python tools/gen_location_regions.py            # regenerate + wire lib.rs
    python tools/gen_location_regions.py --check     # CI drift gate
"""
import sys, os, types, importlib.util, argparse, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ELD = os.path.join(REPO, "Archipelago", "worlds", "eldenring")
LOCATIONS_PY = os.path.join(ELD, "locations.py")
MAP_REGION_PY = os.path.join(ELD, "map_region_data.py")
GRACE_DATA_PY = os.path.join(ELD, "grace_data.py")
OUT_RS = os.path.join(REPO, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "tracker_regions.rs")
LIB_RS = os.path.join(REPO, "from-software-archipelago-clients",
                      "crates", "er-logic", "src", "lib.rs")
MOD_LINE = "pub mod tracker_regions;"

# Base-game section-header -> coarse region key (or "" = always open). Alaric 2026-07-04.
HEADER_COARSE = {
    "Limgrave": "Limgrave", "The hold": "", "Weeping": "Weeping Peninsula",
    "Siofra": "Siofra River", "Liurnia": "Liurnia of The Lakes", "Caelid": "Caelid",
    "Nokron": "Nokron, Eternal City Start", "Ainsel": "Ainsel River", "Altus": "Altus Plateau",
    "Mt Gelmir": "Mt. Gelmir", "Volcano Manor": "Mt. Gelmir", "Capital Outskirts": "Altus Plateau",
    "Leyndell": "Leyndell, Ashen Capital", "forbidden lands": "Forbidden Lands",
    "Mountaintops": "Mountaintops of the Giants", "Farum Azula": "Farum Azula",
    "Snowfield": "Consecrated Snowfield", "Haligtree": "Miquella's Haligtree",
}
# Per-fine-region overrides (win over header + self rule). Alaric 2026-07-04. The three shared
# play_region buckets (REGION_ID_MAP.md) follow their owner's open flag.
FINE_OVERRIDE = {
    "Mohgwyn Palace": "Mohgwyn Palace",
    "Moonlight Altar": "Liurnia of The Lakes",
    "Sellia Crystal Tunnel": "Caelid",
    "Fog Rift Fort": "Scadu Altus",
    "Recluses' River": "Scadu Altus",
}


def coarse_keys():
    t = open(MAP_REGION_PY, encoding="utf-8").read()
    return set(re.findall(r'"([^"]+)"\s*:\s*\{\s*"area_ids"', t))


def region_lock_items():
    """coarse region name -> lock item name (grace_data.REGION_LOCK_ITEM). Pure data module."""
    spec = importlib.util.spec_from_file_location("er_grace_data", GRACE_DATA_PY)
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    return dict(gd.REGION_LOCK_ITEM)


def header_buckets():
    """fine region name -> section header, from region_order + region_order_dlc."""
    t = open(LOCATIONS_PY, encoding="utf-8").read()
    out = {}
    for name in ("region_order", "region_order_dlc"):
        m = re.search(r'\n' + name + r'\s*=\s*\[(.*?)\n\]', t, re.S)
        if not m:
            continue
        cur = None
        for line in m.group(1).splitlines():
            s = line.strip()
            if s.startswith("#"):
                cur = s.lstrip("#").strip()
            else:
                nm = re.match(r'"([^"]+)"', s)
                if nm:
                    out[nm.group(1)] = cur
    return out


def build_fine2coarse():
    keys = coarse_keys()
    buckets = header_buckets()
    f2c = {}
    for fine in set(buckets) | set(FINE_OVERRIDE):
        if fine in FINE_OVERRIDE:
            f2c[fine] = FINE_OVERRIDE[fine]
        elif fine in keys:
            f2c[fine] = fine
        else:
            f2c[fine] = HEADER_COARSE.get(buckets.get(fine), "")
    return f2c


def load_locations():
    """[(ap_code, fine_region, prominent, missable)] via a stubbed import of locations.py."""
    d = ELD

    class _Meta(type):
        def __getattr__(cls, n):
            return 0

    class ItemClassification(metaclass=_Meta):
        pass

    bc = types.ModuleType("BaseClasses")
    bc.Item = type("Item", (), {})
    bc.Location = type("Location", (), {})
    bc.Region = type("Region", (), {})
    bc.ItemClassification = ItemClassification
    sys.modules["BaseClasses"] = bc

    pkg = types.ModuleType("eld")
    pkg.__path__ = [d]
    sys.modules["eld"] = pkg
    # real items/grace_data load via __path__ (item_table needed at import).

    spec = importlib.util.spec_from_file_location("eld.locations", LOCATIONS_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["eld.locations"] = mod
    spec.loader.exec_module(mod)

    rows = []
    for region, table in mod.location_tables.items():
        for loc in table:
            code = getattr(loc, "ap_code", None)
            if code is None:
                continue
            rows.append((int(code), region,
                         bool(getattr(loc, "prominent", False)),
                         bool(getattr(loc, "missable", False))))
    return sorted(set(rows))


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_rs(rows, f2c, lock_items):
    lines = []
    a = lines.append
    a("// @generated by tools/gen_location_regions.py -- DO NOT EDIT BY HAND.")
    a("// Sources: Archipelago/worlds/eldenring/{locations,map_region_data,grace_data}.py.")
    a("// Regenerate: python tools/gen_location_regions.py   (Windows AP env)")
    a("//")
    a("// Per AP location: fine region (grouping), coarse region (open-flag key for in-logic;")
    a('// "" = always accessible), big_ticket (prominent), missable. See SPEC-item-tracker.md.')
    a("")
    a("use std::collections::{HashMap, HashSet};")
    a("")
    a("use crate::tracker::RegionId;")
    a("")
    a("/// (id, fine_region, coarse_region, big_ticket, missable), sorted by id.")
    a("pub const LOCATION_META: &[(u64, &str, &str, bool, bool)] = &[")
    for code, region, prom, miss in rows:
        coarse = f2c.get(region, "")
        a(f'    ({code}, "{esc(region)}", "{esc(coarse)}", {str(prom).lower()}, {str(miss).lower()}),')
    a("];")
    a("")
    a("/// Coarse region name -> its region-lock ITEM name. The client resolves each to a live")
    a("/// open-state flag via `region_open_flags` (absent lock = region unlocked this seed).")
    a("/// Source: grace_data.REGION_LOCK_ITEM (seed-independent).")
    a("pub const COARSE_LOCK_ITEMS: &[(&str, &str)] = &[")
    for r, l in sorted(lock_items.items()):
        a(f'    ("{esc(r)}", "{esc(l)}"),')
    a("];")
    a("")
    a("/// location id -> fine region name (the tracker's grouping).")
    a("pub fn location_region_table() -> HashMap<u64, RegionId> {")
    a("    LOCATION_META.iter().map(|(id, r, _, _, _)| (*id, (*r).to_string())).collect()")
    a("}")
    a("")
    a('/// location id -> coarse region key ("" = always accessible). In-logic keys off this.')
    a("pub fn location_coarse_table() -> HashMap<u64, RegionId> {")
    a("    LOCATION_META.iter().map(|(id, _, c, _, _)| (*id, (*c).to_string())).collect()")
    a("}")
    a("")
    a("/// Big-ticket (prominent) location ids.")
    a("pub fn big_ticket_set() -> HashSet<u64> {")
    a("    LOCATION_META.iter().filter(|(_, _, _, b, _)| *b).map(|(id, ..)| *id).collect()")
    a("}")
    a("")
    a("/// Missable location ids.")
    a("pub fn missable_set() -> HashSet<u64> {")
    a("    LOCATION_META.iter().filter(|(_, _, _, _, m)| *m).map(|(id, ..)| *id).collect()")
    a("}")
    a("")
    a("/// coarse region name -> lock item name.")
    a("pub fn coarse_lock_item_table() -> HashMap<RegionId, String> {")
    a("    COARSE_LOCK_ITEMS.iter().map(|(r, l)| ((*r).to_string(), (*l).to_string())).collect()")
    a("}")
    a("")
    a("#[cfg(test)]")
    a("mod generated_tests {")
    a("    use super::*;")
    a("")
    a("    #[test]")
    a("    fn nonempty_unique_sorted() {")
    a("        assert!(!LOCATION_META.is_empty());")
    a("        assert!(LOCATION_META.windows(2).all(|w| w[0].0 < w[1].0));")
    a("        assert_eq!(location_region_table().len(), LOCATION_META.len());")
    a("    }")
    a("")
    a("    #[test]")
    a("    fn coarse_keys_have_lock_items() {")
    a("        // every non-blank coarse key a location uses must resolve to a lock item")
    a("        let locks = coarse_lock_item_table();")
    a("        for (_, _, c, _, _) in LOCATION_META {")
    a("            if !c.is_empty() {")
    a('                assert!(locks.contains_key(*c), "coarse {c} has no lock item");')
    a("            }")
    a("        }")
    a("    }")
    a("}")
    a("")
    unmapped = sorted({r[1] for r in rows if r[1] not in f2c})
    return "\n".join(lines), unmapped


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
    anchor = "pub mod tracker;"
    new = text.replace(anchor, anchor + nl + MOD_LINE, 1) if anchor in text \
        else text.rstrip("\r\n") + nl + MOD_LINE + nl
    open(LIB_RS, "w", encoding="utf-8", newline="").write(new)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    f2c = build_fine2coarse()
    lock_items = region_lock_items()
    rows = load_locations()
    new, unmapped = render_rs(rows, f2c, lock_items)
    if args.check:
        try:
            cur = open(OUT_RS, encoding="utf-8").read()
        except FileNotFoundError:
            cur = ""
        if cur.replace("\r\n", "\n") != new or not lib_has_mod():
            print("STALE: run python tools/gen_location_regions.py")
            return 1
        print(f"OK: up to date ({len(rows)} locations).")
        return 0
    open(OUT_RS, "w", encoding="utf-8", newline="\n").write(new)
    wired = wire_lib_rs()
    bt = sum(1 for r in rows if r[2])
    coarse = len({f2c.get(r[1], "") for r in rows} - {""})
    print(f"Wrote {OUT_RS}: {len(rows)} locations, {bt} big-ticket, {coarse} coarse regions, "
          f"{len(lock_items)} lock items.")
    print("Wired lib.rs." if wired else "lib.rs already wired.")
    if unmapped:
        print(f"NOTE: {len(unmapped)} fine regions default to coarse=\"\": "
              + ", ".join(unmapped[:10]) + (" ..." if len(unmapped) > 10 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
