# ER Archipelago — Project Handoff

Updated 2026-06-13. Supersedes the goods-MVP handoff.

## TL;DR — current state

Full Elden Ring Archipelago loop WORKING and VALIDATED end-to-end, base + DLC (preflight-PASS
playtest 2026-06-13): pickup/shop/gift checks, item delivery (all categories), base+DLC map
fragments reveal + grant, base+DLC enemy rando, dungeon sweep, precollected starts
(bell/physick/maps -- note goodsType=1 keys land in the KEY ITEMS tab). Big options batch
landed this session (details in TODO.md + SPEC-*.md): Tier A enemy sub-toggles, great-rune
thresholds (final boss / Mountaintops), important_locations break-bug fix + Boss class,
bell_physick_option, flask/blessing tri-states, deathless routing (recursion fix), gear/rune
useful-reclassification, DLC ruins sweep. Pipeline gained `build.ps1 -Preflight` (seed/slot/
deploy cross-checks; auto-run in -All) + a DLC footgun guard.

KNOWN constraints: enemy-rando swap toggles (swap_multiboss / boss_runes_match) crash vs DLC
enemies (v0.8 scaling, EnemyRandomizer.cs:8202) -> apworld force-suppresses them when DLC is
on (TODO #1). `map_option: give` auto-completes every map-pillar check at spawn (TODO #5).
Conservative base-game sync is reasonable now with AP `!release` armed as the safety net.

## Architecture — three repos + two libs under this root

1. **apworld** — `Archipelago/worlds/eldenring` (Python; full AP source checkout, generate
   in-tree). Upstream: lBedrockl/Archipelago (quiet since 2026-02). Origin: 4laric fork.
2. **static randomizer** — `SoulsRandomizers` (C#, build config `"Release (Archipelago)"`).
   ArchipelagoForm connects to AP at bake time, places items, runs enemy rando, emits
   regulation.bin + event/msg/map/script + `..\apconfig.json`. Fork of fswap's DS3-AP
   branch of thefifthmatt's randomizer. **LICENSE: keep fork PRIVATE** (see Licensing).
3. **runtime client** — `Dark-Souls-III-Archipelago-client/archipelago-client` (C++ DLL,
   `archipelago.dll`). Hooks the live game; loaded by Elden Mod Loader from `Game\mods`.
4. Libs: `SoulsFormats` (branch dsms; has our zstd-DCX + MSBE fixes), `SoulsIds`
   (branch ap-fixes; ParseAdd padding). `Paramdex`, `yet-another-tab-control` siblings.

## Pipeline (repo root)

- `.\build.ps1 -All` = -Randomizer -Client -Generate -Serve -Bake -Enemies -Deploy.
  Individual switches exist; run with no args for usage. -Serve polls port 38281.
  Deploy targets the GAME ROOT (UXM) for game files; `Game\mods` for dll+apconfig.
- `.\push.ps1 -Status` / `-Message "..."` — scoped commit+push across all repos
  (bake outputs excluded by scoping; lock/detached-HEAD guards built in).
- Players YAML: `Archipelago\Players\EldenRing.yaml`. apworld options changed? REGENERATE.
- **Slot-name convention (bite this once, never again):** the bake autoconnect
  (ArchipelagoForm.cs:75) defaults the connect slot to **"Player1"** when the GUI name
  field is empty (the dev-loop case). So the Players yaml MUST be `name: Player1` for the
  solo loop, or the bake connects as the wrong slot and apconfig points at it. Preflight's
  "baked slot is an intended player" check catches the mismatch. The right fix is to read
  the slot name FROM the yaml instead of hardcoding it (needed for real syncs where each
  player has their own handle) -- see TODO.md item 3.
- **Preflight:** `.\build.ps1 -Preflight` (auto-run by -All) writes `preflight_<ts>.log`
  and cross-checks baked slot/seed vs the newest gen + the deploy. Run before any sync bake;
  all-PASS or don't trust the build.
- Regulation/event/etc. changed? rebake+deploy is enough; same seed keeps working.
- Diags: every bake writes timestamped `ap_*_<yyyymmdd-hhmmss>.txt` into SoulsRandomizers\
  (ap_diag has an "items with NO PARAM ROW" section worth checking each bake).

## Environment (critical, hard-won)

- **Game exe 2.6.2.0** (sha 34102b1c…, copy at `elden_ring_artifacts/eldenring.exe`),
  **UXM-unpacked AND PATCHED** (patch step was missed for days — loose files silently
  ignored; regulation.bin alone loads natively from Game root, which masked it).
- Loader: **Elden Mod Loader** (dinput8.dll) loads `Game\mods\archipelago.dll`.
  ModEngine3 is INCOMPATIBLE with this exe. lazyLoad.ini is unused.
- Client log: `%LOCALAPPDATA%\archipelago_client.log`; console shows er::Init BUILD
  stamp (verify freshness), "Loaded N location flags", sweep/goal lines at connect.
- **Vanilla param dump (gold!): `elden_ring_artifacts/vanilla_er/vanilla_er/*.csv`**
  (242 params). Use for any flag/def archaeology. Grace warp table already harvested to
  `elden_ring_artifacts/grace_flags.tsv` (422 graces: flags, tiles, positions, textIds).

## The beta.3 contract (slot_data; versions ">=0.1.0-beta.3 <0.1.0-beta.4")
# (beta.3 added `reveal_all_maps`; beta.2 base notes below still apply.)

- `apIdsToItemIds` values are CATEGORY-PACKED: top nibble == game gib encoding == C#
  ItemKey.FullID (weapon=0, armor=0x1, accessory=0x2, goods=0x4, ash/gem=0x8, <<28).
  C# reads as long + `unchecked((int)(uint)v)` (GEM nibble overflows int32). Client
  reads DWORD (safe).
- `items_handling = 7`: server echoes own-world items. SINGLE GRANT PATH: the AddItemFunc
  detour only suppresses the synthetic placeholder + sends the check; ALL items arrive
  via ReceivedItems -> GrantFullID, deduped by persisted last_received_index
  (`Game\archipelago\<seed>_<slot>.json`; delete it to force full regrant).
- New slot_data keys: `dungeonSweeps` {trigger loc: [member locs]}, `goalLocations`
  (ec 2/3), `no_weapon_requirements` (REAL bool — see gotcha below), `regionGraces`
  {lock-item name: [grace warp flags]} (region gating), `reveal_all_maps` (bool; beta.3,
  map_option=give → client sets map-reveal flags, no map items granted).
- Version enforcement is HALF-WIRED: apworld emits `versions`; the client now does an ADVISORY
  warn-only check (er_version_check.h); the randomizer's CheckVersionRange is dev-inert
  (Version==null) + DS3-numbered, so it doesn't gate dev bakes. apworld's emitted range is the
  de-facto source of truth until that's reconciled.
- **GOTCHA: ER apworld toggles serialize as 0/1 INTS.** The randomizer's `options` dict
  filters to JSON bools only — read ints from the slotData JObject directly
  (see random_start handling). no_weapon_requirements is deliberately a real bool.

## Client systems (all confirmed live except where noted)

- Flag polling (2s tick): apconfig `location_flags` (AP loc -> guarding event flag);
  detects shop/gift/offline checks; doubles as resync. GetEventFlag RVA 0x5F9400,
  EventFlagMan ptr 0x3D68448 (AOBs in er_hooks.h; survive the UXM patch).
- Dungeon sweep (UNTESTED): boss-drop trigger flag fires -> send all member checks.
- Goal: ec0/1 = defeat flag poll (PCR 20012802 / Elden Beast 19000800); ec2/3 = all
  goalLocations server-checked. UNTESTED.
- Map fragments: gib + set reveal flag (kMapUnlockFlags in GameHook.cpp; base table from
  MiscSetup, DLC 62080-84 CONFIRMED vs WorldMapPieceParam). UNTESTED in-game.
- Region-lock sentinel (er_code 99999): no grant, logged. Lock items land as shop
  placeholder tokens ("logic-only token" description).
- Grant drain GATED on InventoryInstance()!=0 (menu-time grants used to vanish);
  16 grants/tick; PromptYN auto-Y after 10s; UTF-8 console.

## Randomizer AP-path specifics

- ER bake opts (ConvertRandomizerOptions): enemy+scale, editnames, phasehp, bossbgm,
  nerfmalenia, nerfgargoyles, sombermode (1 stone/level), nooutfits, weaponreqs (from
  apworld option). **CharacterWriter (class rando) is WIRED BUT DISABLED — corrupts
  regulation -> boot crash** (fork's ER code predates DLC-era CharaInitParam def; audit
  vs vanilla_er CSV dump, then re-enable in ArchipelagoForm).
- DLC-install fixes: MapDupes mirrors written `_0x` maps onto `_1x` clones (game loads
  clones when DLC installed — vanilla-Tree-Sentinel bug); msg loads/writes
  item_dlc02/menu_dlc02 msgbnds (?GoodsName? bug).
- Shop pricing: sellValue floor + soul markup REMOVED for ER finite slots (rune items
  no longer cost >= their yield); floor kept on infinite slots (rune-printing guard).
- Synthetic items: Telescope icon (param-derived; 42/7039 are invalid ER atlas ids),
  blank unused FMGs, informative voucher descriptions. Phantom items -> ap_diag +
  placeholder fallback (never crash the bake).

## Pending validation (the rolled DLC seed)

DLC checks + items end-to-end; DLC enemy shuffle visual; dungeon sweep at any boss;
map reveal flags (watch "Map fragment N: set reveal flag" lines); no_weapon_requirements;
goal detection. Watch the connect banner: flags count should be ~4500+, "Dungeon sweep
enabled for N dungeon(s)" must appear (if absent, the YAML didn't take — that's exactly
what happened on reroll #1).

## Roadmap (SPEC-*.md in repo root)

- SPEC-grace-warp-rando.md — NEXT FEATURE (Lite tier first); data table already harvested.
- SPEC-rune-gating.md — in-game Great Rune gates; runes_end machinery exists, Leyndell
  event hunt is the work. Note: vanilla already enforces 2 runes = apworld default.
- SPEC-region-boss-gating.md — finish world_logic modes 1/2 (dead code + missing pct math).
- SPEC-ap-icon.md — real AP logo icon via menu TPF injection.
- SPEC-poptracker-pack.md — generated tracker pack; M2 needs declarative-rules refactor.
- SPEC-dungeon-sweep.md — implemented; kept for design record.
- Also unfixed: CharacterWriter audit (above); placeholder tokens linger in inventory
  (removeFromInventory stub); DeathLink stubbed; Universal Tracker recommended interim.

## Licensing (do not skip)

thefifthmatt's randomizer: "not freely licensed… do not distribute the randomizer, forks
of the randomizer programs, or forks of config files." Public repo is ~3yrs stale
(pre-DLC); v0.11.4 source unpublished. Our diste/ contains v0.11.4-package configs and
FromSoft msgbnds. **SoulsRandomizers fork: PRIVATE ONLY.** apworld/client/SoulsFormats/
SoulsIds are clean to publish. Public-release shape: own-code patches + user-supplied
Nexus package + game files; ask thefifthmatt first.

## Agent-side gotchas (for the next session)

- The sandbox file mount can serve STALE or TRUNCATED files after Windows-side edits —
  verify edits via the Read tool, not bash; git over the mount times out (use paste-able
  PowerShell for the user instead).
- **`Archipelago\Players\` is read WHOLESALE by Generate.py** — EVERY file, not just
  `*.yaml`. A `.bak` backup left in there was read as a second player (name `Player1`),
  causing a long phantom-slot / wrong-bake-slot chase (2026-06-13). Keep ONLY the intended
  player yaml(s) in `Players\`; stash backups elsewhere. Preflight's "Players\ has no
  stray files" check now guards this.
- Diag files are timestamped (`Util.ApRunStamp`) precisely to defeat stale-mount reads
  of uploaded artifacts.
- Memory (auto-memory space) has the full debugging history: er-apworld-key-mismatch is
  the master log; er-runtime-client-port-status is current-state; er-ecosystem-upstreams
  has the licensing/provenance recon.
