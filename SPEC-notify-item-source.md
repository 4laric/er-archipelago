# SPEC: show the item SOURCE (sender) in AP receive notifications

**One sentence:** carry the sending player's name (and the AP item name) from the receive handler
through `receivedItemsQueue` to the grant-time notification, so a received item reads
`Golden Rune [10] from bubbles` instead of an anonymous grant.

Companion to the notifications work: [[er-ap-notify-banner-size]] (the bottom-center event banner is
where this text ultimately renders) and `BRIEF-notify-boss-defer.md` Task B (popup suppression +
banner). This spec is the **data half**; Task B is the **render half**. They can ship independently —
the data half is useful immediately via a grant-time console line even before the banner exists.

> **STATUS: data half IMPLEMENTED 2026-06-14** (code-complete, syntax-checked, NOT yet built on
> Windows / playtested). `SReceivedItem` carries `sender`/`itemName`/`ownItem`; the receive handler
> populates them; `GiveNextItem` builds `"X from Y"` and routes it through `showBanner` (which logs a
> grant-time line today). Open decisions below were resolved as: own/server items drop the "from"
> (no `(you)` suffix), notification fires at grant time, location omitted from the note. **Remaining =
> Task B only**: make `showBanner` render the bottom-center banner instead of just logging. Files
> changed: `ItemRandomiser.h`, `ArchipelagoInterface.cpp`, `GameHook.cpp`, `Core.cpp` (/give debug).

---

## Current state (why the source is lost today)

The receive handler **already resolves everything we need** — `ArchipelagoInterface.cpp:184-189`:

```cpp
for (const auto& item : items) {
    std::string itemname = ap->get_item_name(item.item, ap->get_player_game(item.player));
    std::string sender   = ap->get_player_alias(item.player);        // <-- "bubbles"
    std::string location = ap->get_location_name(item.location, ap->get_player_game(item.player));
    spdlog::info("#{}: {} from {} - {}", item.index, itemname, sender, location);   // logged ONCE here
    ...
    ItemRandomiser->receivedItemsQueue.push_front({ ds3IdSearch->second, count });  // <-- only {address,count}
}
```

`SReceivedItem` (`ItemRandomiser.h:12`) carries only the ER goods id + count:

```cpp
struct SReceivedItem { DWORD address; DWORD count; };
```

So `sender` and `itemname` are computed, logged once at **receive** time, then **discarded**. By the
time the item is actually granted — `GameHook::GiveNextItem()` (`GameHook.cpp:45`), drained by the
paced/boss-deferred loop in `Core.cpp` ~442 — the notification point has only the numeric goods id
and no idea who sent it. Note the receive-time log and the grant are **decoupled in time**: pacing
([[er-ap-notify-banner-size]] / `kMaxGrantsPerTick`) and the new boss-defer gate
([[er-defer-grants-in-boss-fight]]) mean an item can be granted seconds/minutes after it was
received. A source-aware notification therefore has to travel **with the item**, on the queue.

## The data is free — APIs already in use

- **Sender name:** `ap->get_player_alias(item.player)`. Slot `0` → `"Server"` (starting inventory /
  server grants). `item.player == ap->get_player_number()` → **your own slot** (self-found item).
- **Item name (AP canonical):** `ap->get_item_name(item.item, ap->get_player_game(item.player))` →
  e.g. `"Golden Rune [10]"`. Use this verbatim — it's exactly what every AP client/tracker shows, and
  it already encodes any quantity descriptor. **Do NOT re-append `SReceivedItem::count`** (that's the
  ER grant multiplier; appending it would double-count, e.g. `Golden Rune [10] x10`).
- **Flags:** `item.flags` (0b001 progression, 0b010 useful, 0b100 trap). Out of scope here (banner is
  plain text per the brief), but capture it now if cheap — it's the natural hook for later
  color/emphasis without another protocol round-trip.

## Design

### 1. Extend the queue element

```cpp
struct SReceivedItem {
    DWORD       address;     // ER goods id (unchanged)
    DWORD       count;       // ER grant multiplier (unchanged)
    std::string sender;      // get_player_alias(item.player); "" if unresolved
    std::string itemName;    // get_item_name(...); AP canonical, verbatim
    bool        ownItem;     // item.player == get_player_number()  (self-found)
    // optional now, free later: unsigned flags;   // item.flags
};
```

`<string>` is already available via `ItemRandomiser.h`'s includes. The two existing initializer-list
push sites just gain fields; everything else that reads `address`/`count` is unaffected.

### 2. Populate at receive time

In the `set_items_received_handler` loop (`ArchipelagoInterface.cpp:213`), the strings are already in
scope — just store them:

```cpp
ItemRandomiser->receivedItemsQueue.push_front({
    ds3IdSearch->second,
    count,
    sender,
    itemname,
    item.player == ap->get_player_number()
});
```

Also update the **debug `/give` path** (`Core.cpp:620`) and `ItemRandomiser.cpp:21` drain to compile
with the new fields (the debug path can pass `"", "(debug)", true`).

### 3. Emit at grant time (the actual notification)

`GiveNextItem()` already pops the `SReceivedItem`; build the line there (or return it to the
`Core.cpp` drain loop) and route it to `GameHook->showBanner(...)`:

```cpp
std::string note = item.ownItem ? item.itemName            // self-found: no "from"
                                 : item.itemName + " from " + item.sender;
GameHook->showBanner(note);          // Task B turns this into the bottom-center banner
spdlog::info("Granted: {}", note);   // grant-time console line (useful NOW, before the banner exists)
```

`showBanner` is a no-op/log today (`GameHook.cpp:110`); this spec only requires it to **receive the
right string** — standing it up as a real banner is Task B. So step 3 delivers value immediately as a
grant-time log line and "just works" once the banner lands.

### Recommended format

| Case | Notification |
|---|---|
| Foreign sender | `Golden Rune [10] from bubbles` |
| Self-found (`item.player == own slot`) | `Golden Rune [10]` (no "from") |
| Server / starting inventory (slot 0) | `Golden Rune [10]` (suppress "from Server" — it's noise) |
| Sender unresolved (`"Unknown"`/empty) | fall back to item name only, never print `from Unknown` |

## Edge cases / caveats

- **Threading (pre-existing):** `receivedItemsQueue` is written by the network thread
  (`push_front`) and read by the game-loop thread (`pop_back`) with **no lock** today (see the
  `Core.h` cross-thread note). Adding `std::string` fields makes each element heap-allocating, so
  copies are larger but the race profile is unchanged — `std::deque` concurrent push/pop is already
  technically UB here. **Out of scope** to fix, but if we ever add a mutex, this is the struct that
  motivates it. Flagging so the bigger string copies aren't mistaken for the cause of a future crash.
- **Reconnect dedup unaffected:** `pLastReceivedIndex` / `SkipAlreadyReceivedItems`
  (`Core.cpp:510`) pop by count off the back; extra fields don't change that. Items still arrive
  exactly once.
- **Long names:** sender aliases and item names can be long; the banner (Task B) owns truncation, not
  this spec. The console line is unbounded.
- **Boss-defer / pacing ordering:** because the note travels on the queue, the "from bubbles" text is
  correct even when the grant is reordered after a boss fight — the banner shows the right source at
  the moment the item actually lands.
- **Region-lock sentinels (er_code 99999):** these are logic-only and skipped in `GiveNextItem`
  (no in-game grant). Decide whether they get a banner at all — recommend **suppress** (they already
  have their own region-received log line at `ArchipelagoInterface.cpp:201`).

## Open decisions (pick during implementation)

1. **Own-item wording:** bare item name (recommended) vs `Golden Rune [10] (you)` vs `(self)`.
2. **Surface timing:** ship the grant-time **console line now** (independent of Task B) — recommended
   — vs hold everything until the banner exists.
3. **Include the check/location?** The receive log shows `… - <location>`; a banner with
   `Golden Rune [10] from bubbles (Stormveil — Margit drop)` is richer but longer. Recommend **omit**
   from the banner (keep it readable); keep it in the console line.

## Files touched (estimate: ~1 small struct + 3 call sites + 1 banner string)

- `ItemRandomiser.h` — extend `SReceivedItem` (+`sender`, `itemName`, `ownItem`).
- `ArchipelagoInterface.cpp` ~213 — populate the new fields from the already-computed strings.
- `GameHook.cpp` `GiveNextItem` (~45) — build the `"X from Y"` note, call `showBanner` + grant-time log.
- `Core.cpp` ~620 (`/give` debug) and `ItemRandomiser.cpp` ~21 — update push/drain sites to the new struct.
- (Task B) `GameHook.cpp` `showBanner` — render the note in the event banner.
```
