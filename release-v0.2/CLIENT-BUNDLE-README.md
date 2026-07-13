# Elden Ring -- Archipelago client (standalone bundle)

A runtime client for Elden Ring. It hooks the **vanilla, unmodified** game via
[me3](https://github.com/garyttierney/me3) and talks to an Archipelago server. Nothing is baked: no
`regulation.bin` edits, no UXM, no patched game files. Delete the folder and your game is untouched.

The client is **apworld-agnostic**. It will drive any Elden Ring apworld, and it degrades to sensible
behaviour for anything your slot_data does not send. If you are testing your own apworld against it,
the contract is at the bottom of this file.

---

## Install

1. Install **me3** (link above). It launches the retail exe; you do **not** need UXM or modified
   game files. If you have previously UXM-patched Elden Ring, restore vanilla files first.
2. Unzip this folder anywhere.
3. (Optional) Put your server details in `apconfig.json`:
   ```json
   { "url": "localhost:38281", "slot": "YourName", "password": "" }
   ```
   Leaving it blank is fine -- the client shows a connect form in-game.
4. Launch:
   ```
   me3 launch --profile "<path to this folder>\ap.me3"
   ```

Start a **new character**. The client writes to its own save (`AP_me3.sl2`), so your normal saves are
not touched.

## What is in the folder

| file | what it is |
| --- | --- |
| `eldenring_archipelago.dll` | the client, loaded by me3 as a native |
| `ap.me3` | the me3 profile (`disable_arxan = true` -- the client hooks native code Arxan would otherwise revert) |
| `apconfig.json` | server / slot / password. Blank is valid. |
| `check_lots_table.json` | **vanilla suppression.** See below. |
| `shoplineup_flags.json` | **shop check detection.** See below. |
| `ap-package/` | cosmetic icon override (optional) |

**Both JSON tables are derived from the game's own params -- game data, not seed data.** That is why
one static copy works for every apworld and every seed. Keep them next to the DLL.

- `check_lots_table.json` maps each check's acquisition flag to the `ItemLotParam` row and slots that
  pay it out, so the client can blank the vanilla ware. **Without it, every check pays out the vanilla
  item AND the Archipelago item.**
- `shoplineup_flags.json` maps `ShopLineupParam` rows to their `eventFlag_forStock`, which is how a
  shop purchase becomes an observable check. **Without it, shop checks never fire.**

---

## The slot_data contract

Everything here is optional. The client uses what it finds and falls back for the rest.

### Locations

The client needs to know which event flag guards each location. Either form works:

| key | shape | notes |
| --- | --- | --- |
| `locationFlags` | `{ap_location_id: event_flag}` | direct, preferred |
| `locationIdsToKeys` | `{ap_location_id: "<lot>,<n>:<flag>:<rows>:"}` | the acquisition flag is field 1 |

**Shop locations** carry no acquisition flag. The client resolves them from the slot's own
`ShopLineupParam` row, which it reads from:

| key | shape |
| --- | --- |
| `locationIdsToTargets` | `{ap_location_id: ["shop:101927", ...]}` |

The row is looked up in `shoplineup_flags.json` to get its stock flag.

> **Use `targets` for shop rows, not the key's row list.** A merchant's wares often share one base row
> in the key, so resolving from the key alone collapses every ware at that merchant onto a single flag
> and most of the shop becomes undetectable. The per-slot row in `targets` is the one that works.
> (The client accepts both `"locationIdsToTargets"` and `"locationIdsToTargets "` -- with a trailing
> space -- so a typo on either side costs nothing.)

### Items

| key | shape | fallback if absent |
| --- | --- | --- |
| `apIdsToItemIds` | `{ap_item_id: er_item_id}` | received items cannot be granted |

### Goal

| key | shape | |
| --- | --- | --- |
| `goalLocations` | `[ap_location_id, ...]` | preferred |
| `goal` | `[event_flag, ...]` | used if `goalLocations` is absent |

If neither is present the seed cannot be completed, so the client warns loudly.

### Vanilla suppression

| key | shape | fallback if absent |
| --- | --- | --- |
| `checkLotBlankMap` / `checkLotBlankEnemy` | `{flag: {lot, slots}}` | **`check_lots_table.json`** |
| `checkItemFlags` | `{er_item_id: [flag, ...]}` | **`check_lots_table.json`** |

You do not need to emit these. The static table covers any apworld's flag set, because the mapping is
a property of the game, not of the seed.

### Region locks (optional)

If your apworld has region locking, name each lock item `<Region> Lock`. The client ships a baked
region table and arms enforcement on the **first lock item you actually send** -- so an apworld that
declares lock items but never grants them is not affected.

---

## Known limitations

- **Game name collision.** Every Elden Ring apworld registers the game as `Elden Ring`, and
  Archipelago allows only one world per game name. You cannot have two Elden Ring apworlds installed
  at once.
- **Shop previews for other players' items.** A shop slot holding a foreign or gem/ash reward still
  displays the vanilla ware's name and icon. You receive the correct item on purchase; only the shelf
  lies. Slots holding your own weapons/armour/talismans/goods display correctly.
- **DeathLink and event flag 76996.** The client's DeathLink kill flag currently collides with an
  in-game flag. Leave DeathLink off for now.
- The client is Windows-only (it hooks the retail x64 exe).

## Reporting a problem

The client writes a log next to the game. Please include:

- the **client SHA** (in this bundle's folder name, and printed in the log on connect)
- the connect banner (it dumps the slot_data keys it received)
- what you expected vs what the game did

The most useful single line is usually the one starting `shoplineup_flags:` or `check-lots:` -- those
say whether the static tables armed.
