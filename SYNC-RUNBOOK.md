# ER Archipelago — Sync / Release Runbook

How to take this ER AP stack into a multiworld sync. See HANDOFF.md for dev state, TODO.md for
known issues, SPEC-*.md for designs.

## 0. The mental model (read once)

- **Generation is HOST-side.** One person collects every player's yaml, runs `Generate`, and
  hosts the resulting multiworld (archipelago.gg upload, or self-hosted `MultiServer.py`).
- **Baking + playing is PLAYER-side.** Each ER player bakes *their own* game against the host's
  server (their slot), which writes `apconfig.json`. The in-game client then connects to
  whatever `url` is in `apconfig.json`. So you point your client at a server by *baking against
  that server*.
- **Version lockstep.** slot_data carries a `versions` contract (currently
  `>=0.1.0-beta.2 <0.1.0-beta.3`), checked at bake AND connect. The apworld the host generates
  with must be the SAME fork build as your randomizer + client. Hand the host YOUR apworld.

## 1. Deliverables you give the host

1. **Your yaml** — `Archipelago\Players\EldenRing.yaml`, renamed to `<YourName>.yaml`
   (e.g. `Alaric.yaml`). Goes in the host's `Archipelago\Players\`.
2. **The ER apworld** — `eldenring.apworld`. Goes in the host's `Archipelago\custom_worlds\`.
   Must match your randomizer/client build (see lockstep above).

That's the whole bundle: `<YourName>.yaml` + `eldenring.apworld`.

### Packaging the apworld (PowerShell, from repo root)

```powershell
Remove-Item -Recurse -Force "Archipelago\worlds\eldenring\__pycache__" -EA SilentlyContinue
if (Test-Path eldenring.apworld) { Remove-Item eldenring.apworld }
Compress-Archive -Path "Archipelago\worlds\eldenring" -DestinationPath "eldenring.zip" -Force
Move-Item eldenring.zip eldenring.apworld -Force
# sanity: the zip must contain eldenring\__init__.py at top
```

Re-package every time you change an apworld option — the host needs the build you bake against.

## 2. Host generates (their job, for reference)

Host puts all `*.yaml` in `Players\` + `eldenring.apworld` in `custom_worlds\`, runs `Generate`,
hosts the output. They give each ER player: **server `host:port`**, **your slot name**, **room
password** (if any).

## 3. Bake against the central server (your job)

`build.ps1 -Serve`/`-Preflight` are for the LOCAL dev loop — skip them for a central sync
(no local server; preflight's seed check is local-only and will false-fail).

1. Build the randomizer + client if not current: `.\build.ps1 -Randomizer -Client`
2. Launch the bake GUI **without** autoconnect, from `SoulsRandomizers\`:
   ```powershell
   & ".\EldenRingRandomizer\bin\Release (Archipelago)\net6.0-windows\win-x64\EldenRingRandomizer.exe" /gui
   ```
3. In the form: **url = `host:port`**, **slot = your name**, **password = room pw**,
   tick **Save password** (so the in-game client can rejoin a locked room), enable enemies,
   click **Connect**. It bakes and writes `apconfig.json` (url = central).
   - If the bake throws **"Loop detection failed on volcano_town"** that's the seed-dependent
     TODO #7 bug — you CAN'T self-fix on a central seed; the host must reroll (or fix #7 first).
4. Deploy: `.\build.ps1 -Deploy`
5. Launch via Elden Mod Loader. The client connects to the central server.

## 4. Release escape hatch (already armed)

`Archipelago\host.yaml` is set to `release_mode: "enabled"` / `collect_mode: "enabled"` (manual:
players `!release` / `!collect` whenever). If you get stuck/softlocked: `!release` sends your
remaining checks to the pool so you don't block the table; `!collect` pulls your own owed items.

**IMPORTANT for a central sync:** your local `host.yaml` only governs seeds YOU host. When
someone else hosts, THEIR room's release_mode controls it — your local setting does nothing.
So **ask the host to enable manual release** on the room (release_mode `enabled` or
`auto-enabled`), or you won't be able to `!release` if you get stuck.

## 5. Pre-sync checklist

- [ ] yaml is the intended config (DLC on, Elden Beast goal, deathlink off, enemy rando,
      bell/physick/kit start, sweep). Slot name set.
- [ ] `eldenring.apworld` re-packaged from the CURRENT apworld (matches your randomizer/client).
- [ ] Did a solo local pass first (`build.ps1 -All`, preflight all-PASS, connect, eyeball spawn).
- [ ] Sent host: `<YourName>.yaml` + `eldenring.apworld`.
- [ ] Got from host: server `host:port`, slot name, room password.

## 6. Known constraints for a sync (current build)

- **DLC ON is the validated path.** Base-game (DLC off) baking is exposed to the volcano_town
  loop (TODO #7) and is less tested. Sync config uses DLC on.
- **Enemy-rando swap toggles** (`swap_multiboss`, `boss_runes_match`) crash vs DLC enemies and
  are force-suppressed under DLC anyway — leave off.
- **volcano_town loop is seed-dependent** (TODO #7) — the lurking central-sync risk: an unlucky
  host seed blocks your bake with no per-player fix. Fixing #7 removes the gamble.
- **`map_option: give`** = maps revealed + free, pillar checks dropped from the pool (no leak).
- **Shop rune double-grant** (TODO #6) — buying own-world goods from a shop grants twice;
  cosmetic/economy only, not blocking.
- **DeathLink** is stubbed client-side (off in yaml regardless).
