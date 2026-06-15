# BRIEF: finish region fusion — client grace-unlock (C++)

One self-contained session. The apworld half is DONE and shipping the contract; this session makes
the runtime client act on it. No apworld changes needed (the contract is consumable as-is).
See SPEC-region-chain.md, TODO #13, memory [[er-region-fusion]].

## What you're building (one sentence)

When the player receives a region **lock item**, set that region's **Site-of-Grace warp-unlock
event flags** so its fast travel lights up with the region — no Torrent slog.

## The contract (already emitted by the apworld)

`slot_data["regionGraces"]` = `{ lock_item_name: [grace_warp_unlock_flag, ...] }`, e.g.
`{"Liurnia Lock": [71000, 71001, ...], "Caelid Lock": [...], ...}`.
- Present only when region gating is active (`world_logic < 3`); absent/empty otherwise — guard for that.
- Count per region is controlled by the apworld `graces_per_region` option (already spread-selected;
  the client just sets whatever flags it's handed). 25 lock items, ~29–210 flags total.
- Keyed by item **name**, which the client already has at receive time (see hook point).

## THE GOTCHA (read this first)

All region-lock keys share the **sentinel er_code 99999** (GameHook.cpp:49–53) — they're logic-only
items with no param row. So by the time an item reaches `GiveNextItem`, you CANNOT tell Liurnia Lock
from Caelid Lock. **Identity only exists in the received-items handler**, where you have `item.item`
(AP id) and `ap->get_item_name(...)`. Do the region→grace lookup THERE, not in the grant path.

## Anchors (Dark-Souls-III-Archipelago-client/archipelago-client/)

- **Parse the contract:** `ArchipelagoInterface.cpp` ~95, right after the `dungeonSweeps` block
  (lines 85–95). Mirror that pattern into a new `Core->regionGraces`.
- **Store it:** `Core.h` ~105, next to `dungeonSweeps` / `goalLocations`. Add
  `std::unordered_map<std::string, std::vector<uint32_t>> regionGraces;` plus a pending set
  (e.g. `std::vector<uint32_t> pendingGraceFlags;` or `std::unordered_set`).
- **Detect the lock item:** `ArchipelagoInterface.cpp:142–159` (the `set_items_received_handler`
  loop). You already compute `itemname` at 143. Add: `auto g = Core->regionGraces.find(itemname);
  if (g != end) for (f : g->second) Core->pendingGraceFlags.push_back(f);`
- **Flush on an in-game tick (where the flag setter is valid):** `Core.cpp:387` gates on
  `isEverythingLoaded()`; `GiveNextItem()` is called at 440 and `PollLocationFlags()` at 461. Drain
  `pendingGraceFlags` in that same loaded-block, calling
  `er_ap::game::SetEventFlag(flag, true)` per flag (the existing map-reveal setter,
  GameHook.cpp:61 / er_gamehook_win.cpp:151). Do NOT set flags directly in the network handler — the
  event-flag function may be unresolved before the world loads.

## Timing / persistence / idempotency

- `SetEventFlag(flag, true)` is **idempotent** and the flag persists in the game save once set, so
  re-applying on reconnect/replay is harmless. You do NOT need last_received_index dedup for graces.
- On reconnect the received stream re-runs → flags get re-queued → re-set. Fine. (Optionally track a
  session-set set to skip redundant calls / log noise.)
- Log each set like the map-fragment line (GameHook.cpp:62) so you can verify in-game:
  `spdlog::info("Region grace flag {} {}", flag, ok ? "SET" : "FAILED")`.

## Verify the grace FLAG IDS are warp-unlock flags

`grace_data.py` flags come from `elden_ring_artifacts/grace_flags.tsv` column `warpUnlockFlag`
(NOT rowId). Spot-check a couple in-game: receive Liurnia Lock → the Liurnia graces should become
selectable on the map. If a grace doesn't unlock, confirm warpUnlockFlag is the right flag family
(cross-ref the Hexinton CT, same way the DLC map flags were verified — GameHook.cpp:35).

## Version lockstep

Adding a slot_data consumer doesn't change the wire contract, but if you bump the apworld
`versions` range for any reason, bump the client's implemented contract version too (the client
checks it at connect). Otherwise leave `>=0.1.0-beta.2 <0.1.0-beta.3` alone.

## Test plan

1. Build client (`build.ps1 -Client`), bake a region_lock seed with `graces_per_region: 1` (fewest
   flags = easiest to eyeball), deploy.
2. In-game: confirm regionGraces parsed (connect log), receive a lock item, watch for the "Region
   grace flag … SET" log, open the map → that region's grace(s) selectable for fast travel.
3. Reconnect mid-run → graces stay set, no errors.
4. Then test `graces_per_region: 3` and `0` (all) for coverage.

## Out of scope (other sessions)

volcano_town loop (#7), notification UI (#11), pickup VFX (#12), DLC enemy port (#1). Region gating
changes t