# Elden Ring Archipelago — Setup (v0.2)

Get a **Shattering** seed running from scratch. Two halves: **A. Make the seed**
(Archipelago side) and **B. Install & play** (game side). Budget ~15 minutes the
first time.

> **The flagship mode is The Shattering** — the Lands Between is broken into a
> handful of regions and each region's key arrives as a multiworld item. The
> included `EldenRing.yaml` is already set up for it. Just change `name:` and you
> have a valid seed.

> **New in v0.2:** this is the **provenance-clean rebuild**. The world's location
> data is derived directly from vanilla game files, with no third-party
> randomizer data or code in the shipped apworld. The AP game id is **unchanged**
> CHANGED from v0.1 — now **`Elden Ring`** (`game: Elden Ring`); greenfield is promoted to
> BE the published `Elden Ring` world, so the old matt-lineage world is retired.
> See `CHANGELOG.md` and `ATTRIBUTION.md`.

---

## What's in this release

| File | What it is |
|---|---|
| `eldenring.apworld` | The Archipelago world (data-derived, matt-free). Goes in your Archipelago install. |
| `EldenRing.yaml` | The flagship player config (The Shattering). |
| `eldenring_archipelago.dll` | The runtime client (MIT) that talks to the live game. Ships on Nexus. |
| `er_static_detection_table.json` | Static check-detection table the client reads. |
| `SETUP.md` | This file. |
| `CHANGELOG.md` | What's new in v0.2. |
| `ATTRIBUTION.md` | Credits, licensing, and the matt-free provenance. |
| `KNOWN-ISSUES.md` | Current known issues and by-design non-features. |

You also need, separately:

- **Elden Ring** on PC (Steam).
- **Archipelago** — download from [archipelago.gg](https://archipelago.gg).
- **ModEngine3 (me3)** — the loader that injects the client into the game.

---

## A. Make the seed (Archipelago side)

1. **Install the apworld.** Double-click `eldenring.apworld` so Archipelago
   registers it, *or* drop it into `Archipelago/custom_worlds/`.

2. **Add your config.** Copy `EldenRing.yaml` into `Archipelago/Players/`. Open
   it and set `name:` to your slot name. That's the only edit you need — the
   defaults are a tuned Shattering run.

   Want a longer shatter? Raise `num_regions` (or set `0` for the full open map).
   Prefer a fixed early path over a random one? Set `num_regions_order: spine`.
   Want a Great-Rune finish? Set `ending_condition: great_runes`. See the comments
   in the yaml for every option and `KNOWN-ISSUES.md` for the by-design no-ops.

3. **Generate.** Run `ArchipelagoGenerate` (or **Generate** in the launcher).
   You'll get an `AP_<...>.zip` output. For a solo game you can host it locally;
   for a multiworld, upload it to [archipelago.gg](https://archipelago.gg) and
   note the **room server address** and **port**.

---

## B. Install & play (game side)

1. **Install ModEngine3.** Follow its own install instructions so the `me3`
   launcher is available.

2. **Drop in the runtime client.** Put `eldenring_archipelago.dll` (and
   `er_static_detection_table.json` next to it) where your ModEngine3 profile
   loads it, and launch Elden Ring through ModEngine3 with the client loaded.
   The client is the same MIT Rust client v0.1 shipped — v0.2 rides it unchanged
   (no client fork).

3. **Point it at your room.** Use the in-game **Connection** overlay (menu bar)
   to enter the server address, slot name, and password after launch — or your
   existing `apconfig.json` if you kept one from v0.1:

   ```json
   {"url":"localhost:38281","slot":"YourName","seed":"","client_version":null,"password":null}
   ```

   (use your `archipelago.gg` room address instead of `localhost:38281` for a
   hosted game).

4. **Play.** Start a character, connect, and the overlay confirms the slot.
   Received items appear in the game's own bottom-center event banner; every check
   you find is sent to the multiworld. In The Shattering you begin at Roundtable
   Hold with one region already open — find a region's Lock, fast-travel in, clear
   it, and work toward the goal region.

### Handy client console commands
- `/warp <id>` — teleport (e.g. to drop into a freshly unlocked region if a grace
  hasn't lit yet).
- **Connection** (overlay menu bar) — re-enter server / slot / password without
  editing config, even while already connected, to switch rooms. Open it from a
  game menu or the main menu (not while moving) so stray keys don't leak in-world.

---

## Tracking your seed

**Built-in tracker.** The client has an in-game tracker window — press **F6**, or
use the **Tracker** entry in the overlay menu bar, to toggle it. It shows your
checks grouped by region with `done/total`, dims locked regions and names their
gate item, and highlights your current region. No extra install.

---

## Variants

- **Longer / full shatter:** raise `num_regions`, or set `0` for the whole map.
- **Fixed vs random path:** `num_regions_order: spine` keeps a fixed early path;
  `rolled` (default) keeps random regions.
- **Great-Rune goal:** `ending_condition: great_runes` + `great_runes_required: N`
  (needs `item_shuffle: true`).
- **DeathLink:** set `death_link: true` (works both directions).
- **DLC (experimental):** `enable_dlc: true` (regions eligible) or `dlc_only: true`
  (only Land of Shadow). Base game is the recommended, supported way to play — see
  `KNOWN-ISSUES.md` for DLC caveats.

Questions or a broken seed? Bring the spoiler log and your yaml.
