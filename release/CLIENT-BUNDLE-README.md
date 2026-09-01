# Elden Ring -- Archipelago client (standalone bundle)

A runtime client for Elden Ring. [me3](https://github.com/garyttierney/me3) loads it into the
**vanilla, unmodified** game, and it connects to an Archipelago server. Nothing is baked into the
game: no `regulation.bin` edits, UXM, or patched files. Delete the folder and the game is untouched.

The client is **apworld-agnostic**. It can drive any Elden Ring apworld and uses sensible fallbacks
for data absent from `slot_data`. If you are testing your own apworld, the contract is at the bottom
of this file.

---

## Install

1. Install **me3** (link above). It launches the retail exe; you do **not** need UXM or modified
   game files. If you have previously UXM-patched Elden Ring, restore vanilla files first.
2. Unzip this folder anywhere.
3. Run Matt's randomizer, then run `powershell -ExecutionPolicy Bypass -File
   .\install-ap-flower.ps1 -Destination <randomizer-folder>`. It copies the authenticated hi/low
   overrides from `flower-package` into the folder Matt actually loads. It never downloads tools,
   unpacks Elden Ring, or writes into the stock game. Restart Elden Ring after installing.

   On Linux/Proton, run `python3 ./install_ap_flower.py --destination <randomizer-folder>`.
   Existing unowned atlas mods are refused unless you deliberately pass `--replace-existing`,
   which backs them up for a later `--uninstall`. If automatic detection cannot find Matt's output,
   an interactive run asks for the folder; non-interactive use must pass `--destination`.
   On Tarnished Edition 1.17 with Matt v0.11.4, also apply
   `tarnished-torrent-rideparam-1.17.json` using the instructions in
   `TARNISHED-TORRENT-REPAIR.md`; it restores the four missing Torrent rows without replacing
   Matt's other parameter edits.
4. (Optional) Put your server details in `apconfig.json`:
   ```json
   { "url": "archipelago.gg:12345", "slot": "YourName", "password": "" }
   ```
   `12345` stands in for your room's port. Find it on the room page; each room
   can use a different one. `38281` is only the default for a server you run at
   `localhost:38281`.
   Leaving it blank is fine. The client also shows a connect form in-game.
5. Launch:
   ```
   me3 launch --profile "<path to this folder>\ap.me3"
   ```

Start a **new character**. When launched through `ap.me3`, the game writes to the separate
`AP_me3.sl2` save. If that file does not exist, me3 creates it by copying your current
`ER0000.sl2`, so copies of your vanilla characters initially appear in the AP character list. The
files diverge after creation, and a new AP character will not appear in a vanilla launch. Do not
load a copied vanilla character while connected; create a new character for the seed.

The profile's `savefile` line provides this separation without the Alt Saves DLL. It applies only
when you launch through `ap.me3`. Another loader, including matt's randomizer, puts the Archipelago
character in your ordinary save unless you configure separate saves there.

For a standalone ModEngine2 or randomizer output instead of me3, point the installer at that loose
file root: `.\install-ap-flower.ps1 -Destination "<folder containing regulation.bin>"`. To remove
only files created by this installer, rerun it with the same destination and `-Uninstall`.

## What is in the folder

| file | what it is |
| --- | --- |
| `eldenring_archipelago.dll` | the client, loaded by me3 as a native |
| `ap.me3` | the me3 profile (`disable_arxan = true` -- the client hooks native code Arxan would otherwise revert) |
| `apconfig.json` | server / slot / password. Blank is valid. |
| `check_lots_table.json` | **vanilla suppression.** See below. |
| `shoplineup_flags.json` | **shop check detection.** See below. |
| `install-ap-flower.ps1` | thin Windows launcher for the packaged-asset installer |
| `install_ap_flower.py` | authenticated, transactional installer for Windows and Linux/Proton |
| `flower-package/` | release-only manifest plus complete hi/low AP Flower overrides; may be absent from dev bundles |
| `tarnished-torrent-rideparam-1.17.json` | four-row Smithbox delta restoring Tarnished Edition's Torrent variants after Matt v0.11.4 |
| `TARNISHED-TORRENT-REPAIR.md` | guarded Smithbox import instructions for that delta |

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
- The client is Windows-only (it hooks the retail x64 exe).

## Reporting a problem

The client writes a log next to the game. Please include:

- the **client SHA** (in this bundle's folder name, and printed in the log on connect)
- the connect banner (it dumps the slot_data keys it received)
- what you expected vs what the game did

The most useful single line is usually the one starting `shoplineup_flags:` or `check-lots:` -- those
say whether the static tables armed.
