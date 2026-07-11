# SPEC: configurable big-ticket locations (2026-07-08)

## Goal
Make the big-ticket location set CONFIGURABLE from the same class vocabulary that feeds
`important_locations`, while keeping Enia's remembrance store a permanent hard-exclude. Big-ticket
drives BOTH `curated_fill` (region-Lock placement) and the client F6 tracker, so the selection must
reach the client -- with ZERO drift between "where locks go" and "what the tracker flags".

## Vocabulary (shared with important_locations)
`Remembrance, Seedtree, Church, Boss, Fragment, Revered, Basin, Shop, Legendary, GreatRune, KeyItem`
Refactor this single list into one shared source (contract.py) that both `important_locations` and
`big_ticket_locations` import.

## Option
`big_ticket_locations` : OptionList, valid_keys = the 11 classes above,
DEFAULT = `Boss, Remembrance, Legendary, GreatRune, KeyItem` (the current hardcoded set -> behavior
is backward-compatible).

## Enia = hard exclude (never big-ticket, not selectable)
gen_data tags a shop slot whose vanilla item is Legendary (ITEM_TIERS rarity==3) with a distinct
`EniaShop` tag -- that is EXACTLY the remembrance store (58 slots; the only shop/legendary overlap).
`BIG_TICKET_EXCLUDE_TAGS = {"EniaShop"}` (was {"Shop"}). Selecting `Shop` now lights up the other
~446 shops but NEVER Enia; selecting `Legendary` keeps world-drop legendaries and still excludes Enia.
`EniaShop` is an internal tag, NOT in the user-facing vocabulary.

## Predicate (single source, contract.py)
`is_big_ticket(tags, selected=None)` -> `bool(selected & tags) and not (EXCLUDE & tags)`;
`selected` defaults to `BIG_TICKET_DEFAULT`. Consumers: `curated_fill` (passes the option) AND
`tools/gen_location_regions` (bakes the DEFAULT column as a fallback).

## Client sync (no drift, minimal Rust)
Big-ticket is now seed-VARIANT, so it cannot live only in the static baked table. Instead:
- `fill_slot_data` emits `bigTicketLocations` = sorted `[address for loc if is_big_ticket(tags, selected)]`
  as an INT_LIST (existing shape; same pattern as goalLocations). New contract key
  `bigTicketLocations` (INT_LIST, GREENFIELD, required=False for old-client tolerance).
- `core.rs`: after slot_data parse, if `bigTicketLocations` present, set `self.big_ticket` from it;
  else keep the static `tracker_regions::big_ticket_set()` default (backward-compatible). One small read
  mirroring the goalLocations array parse (`sd.get("bigTicketLocations").as_array() -> filter_map(as_i64)`).
- `tracker_regions.rs` big_ticket column stays as the DEFAULT fallback (regen bakes is_big_ticket(_, DEFAULT)).
- `options.rs` UNCHANGED (the client receives the computed id list, not the class selection).

## Verified against committed data (2026-07-08)
EniaShop slots = 58. default(5) -> 73 big-ticket, 0 Enia leaks (== current). default+Shop -> 519, 0
Enia leaks (turns on 446 non-Enia shops). Shop-only -> 446. empty -> 0. all-11 -> 622. Enia never leaks.

## Files
- contract.py: shared vocab + BIG_TICKET_DEFAULT + is_big_ticket(tags, selected) + EXCLUDE={EniaShop}
  + new `bigTicketLocations` ContractKey.
- features/important_locations.py: import shared vocab.
- features/big_ticket_locations.py (NEW feature): owns the OptionList + emits bigTicketLocations in merge_slot_data.
- features/curated_fill.py: select_priority uses is_big_ticket(tags, world.options.big_ticket_locations.value).
- gen_data.py: add EniaShop tag (shop & rarity==3).
- tools/gen_location_regions.py: is_big_ticket(tags, DEFAULT) for the fallback bool column.
- eldenring-archipelago/src/core.rs: read bigTicketLocations into self.big_ticket (fallback to static).
- tests: is_big_ticket 2-arg; EniaShop-exclude regression; Shop-turn-on; default==73; slot_data emit.

## Deliverable / order (mount + Windows workflow)
ONE patch does everything: `patch_gf_configurable_big_ticket_20260708.py` (idempotent, byte-safe,
ast-validated) patches the 6 Python files AND core.rs (insert_before the `slot_data_parsed = true`
latch; anchor verified unique). The Python side is verified in-sandbox against git-store data; the
core.rs op can't be sandbox-compiled (mount truncates the 2107-line file) but the anchor resolves and
cargo validates it on Windows. Run on Windows:
  python patch_gf_configurable_big_ticket_20260708.py --apply
  python tools/gen_location_regions.py        # rebakes the static fallback column
  .\build.ps1 -Rust                            # regen (now wired) + cargo test/build
  greenfield pytest                            # test_gf_curated_fill (config + Enia + slot_data)
