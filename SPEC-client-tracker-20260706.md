# SPEC-client-tracker-20260706 -- tracker_regions.rs re-pointed to greenfield

Wave 2 I3 of FABLE-FIX-PARALLELIZATION-PLAN-20260706. Fixes: tracker showed
"(unknown region)" under greenfield because `tracker_regions.rs` was generated from
the OLD apworld (ids 7,000,000+) while greenfield emits ids 7,770,000-7,773,956.

## What changed

1. `tools/gen_location_regions.py` -- rewritten to source GREENFIELD pure-data modules:
   - `greenfield/eldenring_gf/data.py` (LOCATIONS: ids + region membership)
   - `greenfield/eldenring_gf/location_tags.py` (Boss/Remembrance -> big_ticket)
   - `greenfield/eldenring_gf/missable_locations.py` (missable ids)
   - `greenfield/eldenring_gf/region_open_flags.py` (sanity gate: every region has a flag)
   AP-env-free: no Archipelago import, plain `importlib` file loads, runs on any Python 3
   (verified in the Linux sandbox). `--check` drift-gate mode kept.
2. `from-software-archipelago-clients/crates/er-logic/src/tracker_regions.rs` -- regenerated.
   OUTPUT SHAPE UNCHANGED (same tuple layout, same fn/test names); only data + Sources line differ.

## Data mapping (frozen)

- LOCATION_META `(id, fine_region, coarse_region, big_ticket, missable)` sorted by id:
  3957 rows, ids 7770000..7773956.
- fine == coarse == greenfield region name (23 fine buckets = 22 REGIONS + Roundtable Hold).
  Roundtable Hold keeps its name as the FINE grouping but coarse = "" (always accessible;
  it has no lock item, matching the old ""-semantics).
- COARSE_LOCK_ITEMS: `region -> "<Region> Lock"` for the 22 REGIONS -- byte-identical to the
  keys greenfield emits in slot_data `regionOpenFlags` (core.py fill_slot_data:
  `{f"{r} Lock": REGION_OPEN_FLAGS[r] ...}`), so the client's existing
  lock-item -> region_open_flags resolution works unchanged.
- big_ticket = LOCATION_TAGS Boss OR Remembrance = 29 ids (25 Boss + 25 Remembrance, 21 overlap).
  Greenfield has no `prominent` marker; this is the documented default.
- missable = MISSABLE_LOCATIONS keys = 29 ids (19 dragon_heart + 10 deathroot).

## What Alaric must run to confirm (Windows)

```powershell
cd C:\Users\alari\Documents\er-archipelago\from-software-archipelago-clients
cargo test -p er-logic            # generated_tests::nonempty_unique_sorted + coarse_keys_have_lock_items
cargo build                       # full client compile (er-logic is a dep of eldenring-archipelago)
```

Then in-game (greenfield seed): connect and confirm the tracker resolves real region names
(e.g. Limgrave / Stormveil Castle) instead of "(unknown region)", and that region in-logic
flips when a "<Region> Lock" arrives.

Drift gate (optional, CI): `python tools\gen_location_regions.py --check` -> "OK: up to date (3957 locations)."

## Caveats

- If the client tracker code assumed the old fine-region names (e.g. "Stormveil Throne")
  anywhere outside tracker_regions.rs, cargo test/build will surface it -- I changed no
  client code, only the generated table.
- tracker_regions.rs consumers note: coarse buckets went 23-ish-old-world -> 22 greenfield
  regions; DLC sub-areas (Abyssal Woods, Jagged Peak, Belurat, ...) are now first-class coarse keys.
