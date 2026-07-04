# Elden Ring Archipelago — Setup (v0.1)

Get a **Shattering** seed running from scratch. Two halves: **A. Make the seed**
(Archipelago side) and **B. Install & play** (game side). Budget ~15 minutes the
first time.

> **The flagship mode is The Shattering** — the Lands Between is broken into a
> handful of regions and each region's key arrives as a multiworld item. The
> included `EldenRing-Shattering.yaml` is already set up for it. Just change
> `name:` and you have a valid seed.

---

## What's in this release

| File | What it is |
|---|---|
| `eldenring.apworld` | The Archipelago world. Goes in your Archipelago install. |
| `EldenRing-Shattering.yaml` | The flagship player config (The Shattering). |
| `me3/` bundle | The runtime that talks to the live game: `ap.me3`, `eldenring_archipelago.dll` (MIT), `ap-package/`, `er_static_detection_table.json`, `apconfig.json`. |
| `SETUP.md` | This file. |
| `CHANGELOG.md` | What's in v0.1. |
| `CHECKS-AND-PROGRESSION.md` | How checks, progression, and filler work (with real counts). |

You also need, separately:

- **Elden Ring** on PC (Steam).
- **Archipelago** — download from [archipelago.gg](https://archipelago.gg).
- **ModEngine3 (me3)** — the loader that injects the client into the game.

---

## A. Make the seed (Archipelago side)

1. **Install the apworld.** Double-click `eldenring.apworld` so Archipelago
   registers it, *or* drop it into `Archipelago/custom_worlds/`.

2. **Add your config.** Copy `EldenRing-Shattering.yaml` into
   `Archipelago/Players/`. Open it and set `name:` to your slot name. That's the
   only edit you need — the defaults are a tuned ~3-4 hour Shattering run.

   Want a longer shatter? Raise `num_regions` (up to 9). Own the DLC and want the
   Messmer campaign instead? See "Variants" at the bottom. New to Archipelago and
   wondering what actually gets randomized? `CHECKS-AND-PROGRESSION.md` breaks down
   checks, progression, and filler with real numbers.

3. **Generate.** Run `ArchipelagoGenerate` (or **Generate** in the launcher).
   You'll get an `AP_<...>.zip` output. For a solo game you can host it locally;
   for a multiworld, upload it to [archipelago.gg](https://archipelago.gg) and
   note the **room server address** and **port**.

---

## B. Install & play (game side)

1. **Install ModEngine3.** Follow its own install instructions so the `me3`
   launcher is available.

2. **Drop in the runtime bundle.** Put the `me3/` folder from this release next
   to your ModEngine3 setup (or point ModEngine3 at `ap.me3`). The bundle already
   references the client DLL and the icon package:

   ```
   ap.me3                       <- ModEngine3 profile (launches the game + client)
   eldenring_archipelago.dll    <- the runtime client (MIT)
   ap-package/                  <- in-world overrides (item icons)
   er_static_detection_table.json
   apconfig.json                <- server / slot / password
   ```

3. **Point it at your room.** Either edit `apconfig.json`:

   ```json
   {"url":"localhost:38281","slot":"YourName","seed":"","client_version":null,"password":null}
   ```

   (use your `archipelago.gg` room address instead of `localhost:38281` for a
   hosted game) — **or** leave it and use the in-game connect overlay to type the
   server, slot and password after launch.

4. **Launch through ModEngine3** using the `ap.me3` profile. Elden Ring starts
   with the client loaded; it connects and the overlay confirms the slot.

5. **Play.** Start a character on the `AP_me3.sl2` save. Received items appear in
   the game's own bottom-center event banner; every check you find is sent to the
   multiworld. In The Shattering you begin in Limgrave — find a region's key,
   fast-travel in, clear it, and work your way to Leyndell and Morgott.

### Handy client console commands
- `/warp <id>` — teleport (e.g. to drop into a freshly unlocked region if a grace
  hasn't lit yet).
- Connect overlay — re-enter server/slot without editing `apconfig.json`.

---

## Tracking your seed

**Built-in tracker (recommended).** The client has an in-game tracker window —
press **F6**, or use the **Tracker** entry in the overlay menu bar, to toggle it.
It shows your checks grouped by region with `done/total`, dims locked regions and
names their gate item, highlights your current region, marks hinted locations, and
flags big-ticket checks. Filters let you show only currently-reachable regions or
only the prominent checks. No extra install — it's part of the client.

**PopTracker (optional).** Prefer a separate window or a full map view? A
**PopTracker pack** lives in the repo (`poptracker/`) — it's not in this download,
grab it from the repo if you want it:

1. Install the [PopTracker](https://github.com/black-sliver/PopTracker) app.
2. Grab the ER pack (`poptracker/`) from the repo and load it.
3. Connect it to the **same Archipelago room** for auto-tracking, including a
   DLC-only map variant for Land of Shadow runs.

## Known issues in v0.1

- **Spirit Calling Bell** may be unusable in-game (summons gated). Not a blocker
  for a solo Shattering run; noted for a point release.
- **Map fragments on connect** — you may receive a few map-piece items the moment
  you connect. Harmless: it's just a small handful of free checks at the start.
- **Item icons** — AP items show the vanilla Telescope icon for now; the custom
  Archipelago flower icon is coming in a point release.

Full detail in `CHANGELOG.md`.

---

## Variants

- **Longer shatter:** raise `num_regions` toward 9 for more regions in play.
- **DLC / Messmer campaign (experimental):** set `enable_dlc: true`, `dlc_only: true`,
  `ending_condition: messmer`. Compact Shadow of the Erdtree run ending at Messmer.
  DLC is **largely untested in v0.1** — base-game (DLC off) is the recommended,
  supported way to play. Treat this as experimental and expect rough edges.
- **DeathLink:** set `death_link: true` (works both directions).

Questions or a broken seed? Bring the spoiler log and your yaml.
