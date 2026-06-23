# SPEC — Packaging & Distribution

*Draft 2026-06-23. How to turn the dev pipeline into something a player (specifically: a streamer) can install and run. Companion to RELEASE-CHECKLIST.md, whose "Non-code gates" section this expands.*

---

## 0. The one fact that decides everything

There are two kinds of artifact in this project, and they have **opposite** licensing fates:

| Artifact | License | Distributable? |
|---|---|---|
| Runtime client (DLL) | MIT | ✅ yes |
| `eldenring.apworld` | AP-ecosystem (lBedrock lineage) | ✅ likely — confirm w/ upstream author |
| SoulsIds | Apache-2.0 | ✅ yes |
| **The forked baker / SoulsRandomizers** | thefifthmatt: *"Do not distribute the randomizer, forks of the randomizer programs, or forks of config files."* | ❌ **NO** |
| **Baked game output** (regulation.bin + *.emevd.dcx + msg) | derivative of the above | ⚠️ **gray zone** |

`ship.ps1` already encodes this — it pushes SoulsRandomizers to a **PRIVATE** remote precisely because of the thefifthmatt license. Any packaging plan that hands a player the baker is a non-starter. The entire design below is built around **never shipping the baker, only its output.**

This is also why "just zip up build.ps1" doesn't work: `build.ps1` is a dev pipeline (it builds the baker from source and runs it locally). Confirmed by RELEASE-CHECKLIST line 62 — it is not, and should not become, the player installer.

---

## 1. What a player actually needs to run a seed

From `deploy_manifest.txt` (the live deploy set) and `apconfig.json`, a playable install = four things dropped onto a stock Elden Ring:

1. **Baked map content** — `regulation.bin`, `event/*.emevd.dcx` (+ `.js` sidecars), and `msg/` text. These are the *output of the baker* and are **seed/option-specific** (region_lock, dlc_only, scaling each bake different bytes).
2. **The runtime client DLL** (MIT) — talks to the live game, grants received items, reports checks.
3. **`apconfig.json`** — per-seed client config: `url`, `slot`, `seed`, and the `location_flags` map. **Seed-specific** (the flag map is baked per generation).
4. **A live AP server** to connect to (self-host, or archipelago.gg room).

Item 1 + 3 are seed-bound. That is the crux: **there is no single static "mod" that works for every seed.** A package is always *a specific generated seed*, or a tool to produce one — and the tool is the part we can't ship.

---

## 2. Three distribution models (and which to pick)

### Model A — Self-host full pipeline
Player installs apworld, generates, serves, **runs the baker + client themselves**.
- ❌ Requires distributing the baker → license-blocked.
- ❌ Heavy: 6-stage build, .NET toolchain, ~zero streamer would do it.
- **Reject.**

### Model B — Pre-baked seed pack  ⭐ recommended for star0chris
*You* generate + bake a seed on your machine; you ship only the **outputs** wrapped as a ModEngine2 overlay + the MIT client + `apconfig.json` + connect info.
- ✅ Streamer install ≈ extract, set one path, double-click a `.bat`, connect. The "5-minute install."
- ✅ Baker tool never leaves your machine.
- ⚠️ Licensing narrows to "is baked *output* a 'fork of config files'?" — defensible (this is how the ER rando community already shares seeds: players exchange generated seed files, not the program). Still wants a conscious risk call and ideally thefifthmatt's nod. See §6.

### Model C — On-demand seed packs / hosted multiworld
Model B productized: you host the room and hand each participant a per-seed pack. Natural when you're the host for a multiworld-with-friends or a stream event.
- Same licensing footing as B; just an operational wrapper.

**Decision: ship Model B as the streamer-facing artifact.** Optionally publish a **Host Pack** (apworld + template yaml, the freely-licensed half) for people who want to generate their own. Long-term clean fix = **upstream the AP changes** so a license-clean official tool carries them and Model A becomes legal.

---

## 3. The two packages

### 3a. Player Pack  (`ER-AP_<seedname>_<date>.zip`) — Model B, streamer-facing
Non-destructive **ModEngine2 overlay** so the player never overwrites their real game files (`deploy_manifest.txt` writes straight into `Game\` — fine for your dev box, unacceptable to ship).

```
ER-AP_<seedname>/
  launchmod_eldenring.bat        # ModEngine2 launcher (edits 0 files in Game\)
  modengine2/                    # ME2 runtime (redistributable)
  config_eldenring.toml          # points mods + external_dlls at the folders below
  mod/                           # <-- baked OUTPUT only (regulation.bin, event/, msg/, map/)
  client/
    <client>.dll                 # MIT runtime client
    apconfig.json                # this seed's url/slot/seed/location_flags
  poptracker-pack/               # optional, the PopTracker pack (auto-track)
  README-FIRST.txt               # 6-line setup, from the Player Guide
  LICENSES/                      # MIT (client), Apache-2.0 (SoulsIds), AP, + attribution
```

Player steps (target: under 5 minutes, zero compiler):
1. Own Elden Ring on Steam (correct app version — pin it; see §5).
2. Extract anywhere outside the game folder.
3. Edit one line in `config_eldenring.toml` if their game path is nonstandard (or auto-detect Steam).
4. Make sure `apconfig.json` `url` points at the room (you prefill it).
5. Run `launchmod_eldenring.bat`. Connect. Play.

### 3b. Host Pack  (`ER-AP-host_<version>.zip`) — freely distributable
For anyone generating their own seeds (license-clean half only):

```
ER-AP-host/
  eldenring.apworld             # fresh build — the checked-in one is STALE
  EldenRing-template.yaml       # one known-good config (from EldenRing-MASTER-template.yaml)
  ER-OPTIONS-REFERENCE.yaml     # annotated options
  HOST-SETUP.md                 # install apworld, generate, host
  LICENSE
```
Note: the Host Pack alone does **not** let someone play — they still need a baked Player Pack from you (or, eventually, a license-clean baker). Be explicit about that in HOST-SETUP so nobody thinks it's the whole thing.

---

## 4. Build tool: `package.ps1` (new — do not overload build.ps1)

`build.ps1` stays the dev pipeline. Add a thin assembler that consumes its outputs.

```
package.ps1
  -PlayerPack  -Seed <name>     # assemble 3a from the last bake of <seed>
  -HostPack                     # assemble 3b
  -OutDir dist\
  -Version <semver>
```

`-PlayerPack` steps:
1. Verify a clean bake exists for `<seed>` (regulation + emevd + apconfig present, timestamps consistent — reuse the dump-timestamp discipline).
2. Copy baked outputs into `mod/` **as a ME2 overlay**, not into `Game\`. (Re-map deploy_manifest paths → relative `mod/` paths.)
3. Drop in ME2 runtime + a templated `config_eldenring.toml` (relative paths, `external_dlls = client\<client>.dll`).
4. Copy MIT client + `apconfig.json`; scrub `apconfig.json` `url` to the intended room (or a `REPLACE_ME`).
5. Stage `LICENSES/`, README-FIRST, optional PopTracker pack.
6. **Refuse to include** anything under `SoulsRandomizers/` — hard guard (fail the build if a baker binary/source is in the tree being zipped). This is the license tripwire; make it loud.
7. Zip → `dist/ER-AP_<seed>_<date>.zip`; print a manifest + total size.

`-HostPack` steps:
1. Force a **fresh** `eldenring.apworld` build (never reuse the stale checked-in one).
2. Copy template yaml + options reference + HOST-SETUP + LICENSE; zip.

Both: write a timestamped copy alongside the canonical name (matches the always-timestamp-dumps convention).

---

## 5. Version pinning (the silent killer)

Elden Ring updates break baked regulation.bin. A Player Pack is only valid for the **exact** game version it was baked against.
- Record the target app version in README-FIRST **and** in the zip name.
- Recommend the player pin via Steam (disable auto-update / use the matching depot) before launching modded.
- ModEngine2 overlay (non-destructive) means a wrong version fails safe — it won't corrupt their install, it just won't load — but a clear version note prevents the support spiral.

---

## 6. Licensing checklist before any hand-off

Even a 1:1 send to star0chris is "distribution." Settle these first:
- [ ] **Baked-output call.** Decide (and ideally get thefifthmatt's read on) whether shipping baked `regulation.bin`/emevd output — without the baker — is acceptable. Community precedent: players share generated seeds, not the program. Document the decision.
- [ ] **Hard guard in package.ps1** that no baker source/binary can enter a zip (§4 step 6).
- [ ] **Confirm apworld license** with the lBedrock-lineage upstream before publishing the Host Pack (RELEASE-CHECKLIST line 61).
- [ ] **Bundle LICENSES/** with MIT (client), Apache-2.0 (SoulsIds), AP, and a FromSoftware fan-project disclaimer (the Player Guide footer is good copy).
- [ ] If unsure on the baked-output call → keep it a **private** hand to one trusted streamer, not a public drop, and say so.
- [ ] **Upstreaming** remains the only path that makes a fully public, self-serve release clean. Track separately.

---

## 7. Open decisions
1. **Server model for the stream:** do you host the room (you control uptime, easiest for him) or hand him a room on archipelago.gg? Prefill `apconfig.json` accordingly.
2. **Single-seed vs his own multiworld:** is star0chris playing solo-AP, or a multiworld with his community? Solo → one Player Pack. Multiworld → Host Pack to whoever generates + a Player Pack per ER player.
3. **Which goal leads the demo:** Godrick mini-campaign is the cleanest watchable first seed (short, self-contained, verified) — recommend baking *that* as the first Player Pack.
4. **Scope cut:** ship only the verified-green feature subset (RELEASE-CHECKLIST §"Verified green"); gate experimental behind the template yaml's defaults so his first seed can't hit a rough edge live.

---

## 8. Minimal path to a shippable Player Pack
1. Finish the v1 blockers (summoning bell; goal playthrough confirms) — RELEASE-CHECKLIST §🔴.
2. Make the baked deploy a **ModEngine2 overlay** instead of in-place `Game\` writes.
3. Write `package.ps1 -PlayerPack` (§4) with the license guard.
4. Bake a Godrick seed; assemble; **test the pack on a clean machine / second account** (no dev tree present) — this is the real verification that nothing depends on your build environment.
5. Settle §6 licensing; then DM the pack + the Player-Guide hook.
