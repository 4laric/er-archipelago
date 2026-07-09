# Elden Ring for Archipelago — collaborator setup

> **Private repo. Do not redistribute.** Access is granted individually. This tree includes a fork of thefifthmatt's SoulsRandomizers, which is **source-available but not freely licensed** — *"Do not distribute the randomizer, forks of the randomizer programs, or forks of config files."* Don't re-share this repo, the baker, or its outputs without asking first. The runtime client (MIT) and SoulsIds (Apache-2.0) are freely licensed; the baker is the part that stays private.

This is the working tree for making **Elden Ring a first-class [Archipelago](https://archipelago.gg) game.** Every meaningful pickup in the Lands Between becomes a *check*; received items appear in your inventory mid-session via a custom runtime client. The full loop (pickup → check → grant) is confirmed working end-to-end.

If you've been given access, this page gets you from a fresh clone to a running seed. For *what the randomizer does and why it's fun*, read **`Elden-Ring-Archipelago-Player-Guide.md`**. For every option and its gotchas, read **`ER-OPTIONS-REFERENCE.yaml`**. For running alongside thefifthmatt's randomizer (enemy shuffle OK, item rando + scaling off), read **`release-v0.1/USING-WITH-MATTS-RANDOMIZER.md`**.

---

## What you're building

A playable seed is assembled from a few separately-built pieces, all driven by `build.ps1`:

- **The baker** — the forked C# static randomizer (`SoulsRandomizers/EldenRingRandomizer`) that generates the seed-specific game files (`regulation.bin`, `event/`, `msg/`, `map/`).
- **The apworld** — `Archipelago/worlds/eldenring`, the Archipelago world definition (logic, options, item/location tables). Packaged to `eldenring.apworld`.
- **The runtime client** — a DLL (C++ today, Rust port in progress) that connects to the AP server, grants received items, and reports your checks.

There is no single static "mod": each seed bakes its own files. That's why this is a build pipeline, not a download.

---

## Prerequisites (Windows)

- **Elden Ring on Steam, version-pinned.** Baked files are valid only for the game version they were baked against; pin in Steam / don't auto-update mid-seed. (DLC only needed for DLC goals.)
- **UXM** to unpack the game's data archives (one-time — see below).
- **.NET SDK** (10.x builds the net6.0-windows target) for the baker.
- **Python 3.11+** (3.13 fine) for Archipelago generation. *Note: the AP toolchain refuses <3.11.*
- **For the C++ client:** Visual Studio 2022 (C++ workload) + vcpkg. *(Or the Rust toolchain for the Rust client spike — `build.ps1 -Rust`.)*
- **PowerShell** (Windows PowerShell is fine; `build.ps1` shims `pwsh` if PS7 is absent, but installing PS7 is cleaner: `winget install --id Microsoft.PowerShell`).
- **Git.**

---

## 1. Clone the superrepo

Full submodule mechanics are in **`SUPERREPO-SETUP.md`** — read it; the short version:

```powershell
git clone --recursive git@github.com:4laric/er-archipelago.git
cd er-archipelago
```

All dependency forks — including Paramdex and yet-another-tab-control — are submodules, so `--recursive` brings them in (with their build patches already baked into the forks). If you cloned without `--recursive`: `git submodule update --init --recursive`.

`elden_ring_artifacts/` (game-derived files, e.g. `oo2core_*.dll`) is gitignored — copy it in from a working machine.

The build references the dependency forks as **siblings of `SoulsRandomizers`** (`..\SoulsFormats`, `..\SoulsIds`, `..\yet-another-tab-control`); the recursive clone places them correctly. If a clean `-Randomizer` build doesn't go green on a fresh clone, ask me — there may be an environment-local dep shim that isn't yet committed to a fork.

---

## 2. One-time game-data staging (UXM)

The baker reads loose vanilla game data, and `-Deploy` overlays its output into your unpacked game:

1. **UXM-unpack** your Elden Ring install so the exe reads loose files from `Game\`.
2. Stage the vanilla data the baker needs under `diste\Vanilla` (regulation, `msg\engus`, map MSBs, event emevd, talk ESDs). Put the Oodle DLL (`oo2core_*.dll`) next to the randomizer exe.
3. Capture a pristine snapshot once, right after unpacking, so clean redeploys can restore vanilla:
   ```powershell
   .\build.ps1 -SnapshotVanilla
   ```

`build.ps1`'s config block (`$GameDir`, near the top) assumes the default Steam path — edit it if yours differs.

---

## 3. Build, generate, bake, deploy

`build.ps1` is the whole pipeline. It always builds **clean** (both toolchains silently produce stale builds otherwise); add `-Clean` if a change still isn't landing.

```powershell
# greenfield loop: gen the data-derived apworld + isolated multiworld, build the client, stage to me3, serve
.\build.ps1 -All
# (the old Generate.py full pipeline is now:  .\build.ps1 -PureRuntime -Apworld -Preflight)

# most common dev loop — everything EXCEPT the C++ client rebuild (reuse the deployed DLL)
.\build.ps1 -NoClient

# individual stages
.\build.ps1 -Randomizer      # build the C# baker
.\build.ps1 -Client          # build the C++ runtime client DLL
.\build.ps1 -Apworld         # package Archipelago\worlds\eldenring -> eldenring.apworld
.\build.ps1 -Generate        # regenerate the multiworld (required after apworld changes)
.\build.ps1 -Serve           # launch the AP server on the newest output zip (new window)
.\build.ps1 -Bake            # run the randomizer to bake the seed (needs the server up)
.\build.ps1 -Deploy          # copy bake outputs + client DLL + apconfig into the game
.\build.ps1 -CleanDeploy     # restore Game\ to the vanilla snapshot, THEN overlay (stops stale-file leak)
```

Generation reads player configs from `Archipelago\Players\*.yaml`. Start from `EldenRing-MASTER-template.yaml`, trim to a known-good slot (the Godrick mini-campaign is the cleanest first seed), and drop it in `Players/`. `-Bake` blocks until you close the randomizer window; deploy runs after. Use one server per port — close any old server window before `-Serve`.

---

## 4. Run a seed

1. Make sure the AP server is up (`-Serve`, or host your own / an [archipelago.gg](https://archipelago.gg) room).
2. Confirm `mods\apconfig.json` in your game folder points at the right room (`url`, `slot`, `seed`).
3. Launch Elden Ring (modded — via your usual EML/mod-loader setup so the client DLL loads from `mods\`).
4. Connect. Pick something up → it registers as a check; received items land in your inventory, with notifications in Elden Ring's own bottom-center event banner.

---

## Picking a goal & tuning options

Full annotated list in `ER-OPTIONS-REFERENCE.yaml`; the headline dials:

- **`ending_condition`** — scope. `godrick` (shortest base run, great first seed), `messmer` (DLC mini-campaign), or the long goals: `final_boss`, `elden_beast`, `all_remembrances`, `all_bosses`, `capital`.
- **`world_logic: region_lock`** — turns the open world into an item-gated graph; the map opens region by region as you receive keys (warp-enforced). Reuses the game's own keys where it fits (Academy Key, Dectus/Rold/Haligtree Medallions).
- **DLC-only mode** — restrict the entire pool to the Land of Shadow.
- **Footprint** (`all` / `trimmed` / `lean`) — how big a slice of the multiworld your ER world takes.
- **QoL** — auto-upgrade, auto-equip, progressive consumables/bell bearings, quick-start, randomized loadout, DeathLink.

---

## Status & gotchas

Actively developed; a large verified-working core (full loop, region locks, DLC-only, auto-upgrade, quick-start, pool builder, gear curation, progressive bell bearings, `trimmed` pool). In flight: progressive consumables, `lean` pool, the Godrick/Messmer goal confirmations, a summoning-bell fix. See `RELEASE-CHECKLIST.md` for the live cut.

Build gotchas worth knowing up front:
- **Stale builds** — `build.ps1` builds clean by design; reach for `-Clean` if a change won't land.
- **Version skew** — a baked `regulation.bin` matches one game version; an Elden Ring update breaks it.
- **Stale-file leak** — a prior bake's `map\` MSBs can hang a fresh new-game load; use `-CleanDeploy` to restore vanilla before overlaying.
- **Sandbox can't run AP** — generation needs Python 3.11+ on a real machine; CI/sandbox setups below 3.11 won't generate.

---

*Elden Ring and Shadow of the Erdtree are property of FromSoftware / Bandai Namco; this is a fan project, not affiliated with or endorsed by them. Runtime client: MIT. SoulsIds: Apache-2.0. The SoulsRandomizers baker fork is source-available and not freely licensed — keep it private.*
