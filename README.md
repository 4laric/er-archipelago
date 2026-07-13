# Elden Ring for Archipelago

**Vanilla game + an apworld + an MIT-licensed Rust runtime client.** This project
makes Elden Ring a first-class [Archipelago](https://archipelago.gg) multiworld
game: every meaningful item pickup in the Lands Between is a *check*, the items
you find go out to the multiworld, and your own items arrive in your inventory
mid-session. It works solo too.

It is **pure runtime**: the game stays completely vanilla on disk. No game files
are patched, no `regulation.bin` is modified, nothing is baked per seed. The
runtime client is a Rust DLL loaded by the ModEngine3 (me3) mod loader; it reads
the seed's layout from the Archipelago server at connect time and does everything
live -- detecting checks, granting items, lighting graces, and enforcing region
locks. This tree ships **no game assets** and contains **no code or data from any
other randomizer project**: the world is derived from scratch against vanilla
game data (see `release-v0.2/ATTRIBUTION.md` for provenance and credits).

---

## How progression works (the part everyone gets wrong)

The world is **Shattered**: carved into major regions -- **17 in the base game,
31 with the DLC** -- and each region is sealed behind an Archipelago item called
a **Region Lock** ("Limgrave Lock", "Caelid Lock", ...). You start at Roundtable
Hold with one region already open. When a region's Lock arrives from the
multiworld, that region opens: **all of its graces light up on your map, and you
warp in.** Walk into a region whose Lock you do not hold and the client warps
you back to Roundtable Hold.

**The Lock is the only way into a region.** Vanilla routes and vanilla key items
gate *nothing* in Archipelago logic. You never need the Rold Medallion to reach
the Mountaintops of the Giants; you never fight Mohg to enter the Land of
Shadow. The Lock arrives, the graces light, you warp in.

There are two vanilla-flavored exceptions, and they are layered **on top of** a
region's own Lock, never in place of it:

- **Raya Lucaria Academy** additionally needs the **Academy Glintstone Key**
  (shuffled into the pool like any other item);
- **Leyndell** additionally needs **Great Runes** (default 2, echoing the
  vanilla capital gate; auto-clamped to what is reachable this seed).

The headline dials, all documented inline in the shipped
`release-v0.2/EldenRing.yaml`:

- **`num_regions`** -- how many regions are in play. `0` = the full Shattering;
  `N > 0` seals the rest for a shorter run. This is the marquee mode: it turns
  the open world into an Archipelago progression graph.
- **`ending_condition`** -- `region_locks` (hold every Lock in play; the goal
  region, Leyndell, is always kept) or `great_runes` (also collect
  `great_runes_required` Great Runes).
- **`enable_dlc` / `dlc_only`** -- bring the 14 Shadow of the Erdtree regions
  into the pool, or play only them.

---

## Playing it

Start with **`release-v0.2/SETUP.md`** -- nothing to a running seed in about 15
minutes (Archipelago 0.6.7 + the apworld + the client DLL + ModEngine3). Then
read **`Elden-Ring-Archipelago-Player-Guide.md`** for how a run actually plays.
Every real option is explained in a comment next to it in
`release-v0.2/EldenRing.yaml`; rough edges live in `release-v0.2/KNOWN-ISSUES.md`.

You need Elden Ring on PC (Steam). The DLC is only needed if you enable the DLC
regions.

One rule worth repeating from the setup guide: the apworld and the client DLL
are a **hash-matched pair** -- the client checks a contract hash on connect and
loudly reports a mismatched apworld in its log. Always install both halves from
the same release (`release-v0.2/DISTRIBUTION.md` explains why).

---

## What is in this repo

- **`greenfield/eldenring/`** -- the apworld source: world logic, options,
  item/location data (generated from vanilla game data), features, tests.
  Packaged to `eldenring.apworld` by `build.ps1 -Apworld`.
- **`from-software-archipelago-clients/`** -- the runtime client (Rust), the
  repo's one git submodule. Builds `eldenring_archipelago.dll`.
- **`tools/`** -- datamining and generation tools, plus `gf_test.py` (the test
  harness).
- **`release-v0.2/`** -- everything player-facing: setup guide, shipped yaml,
  known issues, attribution, changelog.
- **`me3/`** -- the local ModEngine3 staging dir `build.ps1 -Me3Deploy` writes.
- **`greenfield/`** (above `eldenring/`) -- generation inputs, region curation
  tables, and `gen_data.py`, which derives the world's data.

---

## Contributor setup (Windows)

Prerequisites: **Git**, **Python 3.12** (what CI runs), the **Rust toolchain**
(the client is a cdylib), **PowerShell**. No .NET, no Visual Studio, no game
unpacking -- the pure-runtime model removed all of that.

### 1. Clone

```powershell
git clone --recurse-submodules https://github.com/4laric/er-archipelago.git
cd er-archipelago
```

One submodule: the Rust client. Everything else is this repo.

### 2. Bootstrap Archipelago

`.\Archipelago` is a **stock upstream checkout you create**, not something we
version-control:

```powershell
.\bootstrap-ap.ps1    # clones ArchipelagoMW/Archipelago into .\Archipelago
```

The version pin lives in **`.ap-version`** (currently `0.6.7`) and is read by
`bootstrap-ap.ps1`, by CI, and by the test harness, so the version you develop
against and the version CI gates on cannot drift. The bootstrap refuses to run
against any tree whose origin is not `ArchipelagoMW`. `.\Archipelago` is
gitignored; the world is installed into it by `build.ps1`.

`elden_ring_artifacts/` (game-derived data the generators read) is gitignored
and never distributed. You do not need it to build or test: the committed
generated data carries a freshness stamp (`tools/gen_manifest.py`) that CI and
`build.ps1 -Apworld` verify.

### 3. Build and run seeds

`build.ps1` is the whole pipeline:

```powershell
.\build.ps1 -All          # the dev loop: -Greenfield + -Rust + -Me3Deploy + -Serve
.\build.ps1 -PureRuntime  # -Generate + -Rust + -Me3Deploy + -Serve (alias: -Mvp)

# individual stages
.\build.ps1 -Greenfield   # regenerate the data-derived apworld (needs elden_ring_artifacts\)
.\build.ps1 -Apworld      # package greenfield\eldenring -> eldenring.apworld (stamp-gated)
.\build.ps1 -Generate     # regenerate the multiworld from Archipelago\Players\*.yaml
.\build.ps1 -Rust         # cargo test + build the client DLL
.\build.ps1 -Me3Deploy    # stage DLL + apconfig + profile into me3\ (the primary loader)
.\build.ps1 -Serve        # launch the AP server on the newest output zip
.\build.ps1 -Preflight    # sanity-check a generated seed
```

Player yamls for local generation go in `Archipelago\Players\`; start from
`release-v0.2/EldenRing.yaml`.

### 4. Test

```powershell
python tools/gf_test.py             # the apworld suite
python tools/gf_test.py -k shops    # extra args pass through to pytest
```

`gf_test.py` bootstraps its own pinned **upstream** Archipelago checkout into
`.ap-test/` (your working `.\Archipelago` is never touched or consulted),
installs the world into it, and runs the suite. It refuses to run against a
fork of Archipelago -- testing against the wrong tree produces answers to a
different question.

`run_ci.ps1` runs every automated gate from `CONTRIBUTING.md` in one command
(unit suite, fill regression, region diversity, generated-data freshness, gen
fuzz, the pure Rust crates). CI runs on every push and PR: the suite via
`gf_test.py`, plus a job proving the committed generated data is not stale.

Read **`CONTRIBUTING.md`** before opening a PR -- it is the quality bar, and it
does not accept "it looks right" as a pass.

---

*Elden Ring and Shadow of the Erdtree are property of FromSoftware / Bandai
Namco; this is a fan project, not affiliated with or endorsed by them. Code in
this repository and the runtime client are MIT-licensed. This project ships no
game assets and modifies no game files.*
