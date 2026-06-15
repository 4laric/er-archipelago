# BRIEF: notifications v2 — defer grants in boss fights (#11) + suppress/replace native popup

Follow-up to `BRIEF-client-notify-cleanup.md` (Task A pacing + Task B removeFromInventory, both DONE
2026-06-13). That brief proved the "received item" toast is the **native game popup**, not our
render, and bought breathing room with grant pacing (`kMaxGrantsPerTick=5`, `kInterGrantDelayMs=350`).
This brief is the next layer Alaric asked for: stop popups from interrupting **boss fights**, and
(bigger) suppress the native popup entirely in favor of ER's own bottom-center event banner.

Scope order: **Task A first** (cheap, high value, self-contained). Task B is a larger RE effort —
do it only after A lands and is playtested.

Memory: [[er-defer-grants-in-boss-fight]], [[er-ap-notify-banner-size]], [[er-client-inventory-removal]].

---

## Task A — defer item grants while a boss healthbar is on screen

**One sentence:** hold AP item grants while the player is in a boss fight; drain the queue once the
boss bar clears, so the native acquisition popup never pops mid-fight.

**Why it's cheap:** the grant drain is in ONE place — `Core.cpp` ~443-456, the loop gated on
`GameHook->isEverythingLoaded()`. The received queue (`ItemRandomiser->receivedItemsQueue`) already
PERSISTS across ticks, so deferring loses nothing — items just arrive later. The whole behavior
change is a second guard:

```cpp
if (loaded && !GameHook->isBossActive()) { /* existing paced drain */ }
```

**The actual work = implement `isBossActive()`** (does not exist; client only knows boss DEFEAT
flags today, for check polling / dungeon sweep — not display state). RE against the pinned exe
`elden_ring_artifacts/eldenring.exe` (sha256 3410…ddb, matches `er_hooks.h`). Reuse the memory-RE
pattern already proven for removeFromInventory (GameDataMan global `0x03D5DF38` chain,
VirtualQuery-validated reads).

Detection options, best first:
- **HUD boss HP-gauge / boss-display manager** (preferred): find the structure driving the on-screen
  boss bar(s). ER stacks up to 3 bars; "any bar shown / active count > 0" = boss active. Most
  reliable across bosses. Add an AOB or a pointer-chain like the existing hooks; expose
  `bool CGameHook::isBossActive()` in `GameHook.h/.cpp`.
- Alt: an EMEVD `DisplayBossHealthBar`-driven flag/var, IF one reads stably — but not every bar maps
  to a clean event flag, so the HUD structure wins.
- Avoid: inferring from WorldChrMan aggro/combat — noisy, false positives on trash mobs.

**Required safety / edge handling:**
- Multi-phase bosses: the bar persists across phases — that's desired, keep deferring; don't drain
  between phases.
- Death/clear cutscene: fine to keep deferring until the bar is truly gone.
- **Starvation cap (mandatory):** a max defer window (e.g. drain anyway after N seconds, tunable
  const like the pacing dials) so a mis-read "bar visible" state can never permanently block grants.
- No change to grant counts / received-index — every item still arrives, just reordered after fights.

**Deliverable:** `isBossActive()` implemented + the one-line guard in the drain loop + a named
starvation-cap constant. Log the discovered offset/AOB in the brief's VERIFIED note for the next
session.

**Test:** trigger several incoming items (multiworld partner sends, or a starting flood) while
entering a boss arena; confirm nothing pops until the bar clears, then the queue drains at the paced
rate. Verify multi-phase (e.g. Godrick, Rennala) keeps deferring across phases, and that the cap
fires if you camp in an arena without engaging.

---

## Task B — suppress the native acquisition popup + replace with the event banner (bigger)

**One sentence:** stop the vanilla "item acquired" popup from firing on AP grants, and surface
received items through ER's native bottom-center EVENT-TEXT banner instead (the one Alaric likes the
size of — currently seen as the `?EventTextForMap?` failsafe).

**Premise (confirmed earlier):** the popup is a side effect of the acquisition pipeline. `AddItemFunc`
(`0x005605B0`) IS the full CSMapItemMan acquisition path (~335 instrs) and is what fires the popup —
that's exactly why removeFromInventory was implemented as a direct bag edit instead of using it.
Grant currently goes through `GrantFullID` / `ItemGib` (see `GameHook.cpp:45` `GiveNextItem`,
`er_gamehook_win.cpp` AddItem path ~140); `showBanner` in the client is a NO-OP (`GameHook.cpp` ~92-97).

Two sub-problems, each non-trivial — investigate before committing:

1. **Suppress the native popup on grant.** Options to RE/evaluate:
   - Grant via a path that adds to inventory WITHOUT the popup (mirror the removeFromInventory direct
     `EquipInventoryData` edit, but additive) — fully bypasses `AddItemFunc` and its popup. Risk:
     must replicate stacking/overflow correctly; lots of items have quantity/stack rules.
   - OR hook/neuter the popup-display call inside the acquisition pipeline just for our grants (find
     the popup-trigger sub-call; gate it on an "AP grant in progress" flag). Risk: must not suppress
     legitimate native pickups.
   Decide which is safer; the additive-bag-edit path is most consistent with what already shipped.

2. **Drive the event-text banner for AP notifications.** The randomizer already writes
   `FMGCategory.Menu` "EventTextForMap" via `SetFMGEntry` (`MiscSetup.cs:932`, `Randomizer.cs:447`),
   and the banner is shown through the EventText/`RuntimeParamChecker.FogMessageId` mechanism. Goal:
   from the client, set a Menu/EventText FMG string to the received item name + show that banner per
   grant (throttled — reuse the Task A pacing so banners don't stack). This is where `showBanner`
   gets stood up for real. Confirm the banner can be triggered at runtime from the client without
   clobbering real game events, and that text can be set per-grant.

**Deliverable:** AP grants no longer fire the vanilla popup; received items show in the event banner,
paced (and respecting the Task A boss-defer gate). Keep it isolated; if either sub-problem balloons,
ship suppression and banner separately.

**Test:** receive a burst of items — no native popups; banners appear one at a time, readable, not
burying the HUD; nothing breaks normal native pickups (pick up a vanilla world item, confirm its real
popup/banner still works); no regression to grant counts.

**Out of scope:** a brand-new custom ImGui/D3D overlay (we confirmed there's no render layer and
don't want to build one); animations/icons beyond plain text in the native banner.

---

## VERIFIED / DONE

### Task A — boss-defer — ⚠️ REMOVED 2026-06-14 (obsoleted; see below)

**Update:** the entire boss-defer feature was deleted. Once Task B suppressed the blocking "NEW Y:OK"
acquisition modal game-wide (bake `showDialogCondType=0`, confirmed working in-game), there was no
blocking popup to keep out of fights — the native item-gain ticker is non-blocking, so grants no
longer need deferring. Removed: the Core.cpp boss-defer gate (back to plain paced drain),
`isBossActive`/`IsBossFightActive`, `kBossArenaPlayRegions`, FieldArea resolution, and the er_hooks.h
FieldArea constants. Kept: burst pacing + Phase-0 FD4 logging. The original implementation notes below
are retained as history (incl. the FieldArea AOB / RVA 0x03D691D8 / +0xE4 offset, if ever revived).

---

### Task A — boss-defer guard + starvation cap — (historical) CODE-COMPLETE 2026-06-14

**Dead end (documented so nobody re-walks it):** the on-screen boss HP-gauge manager has NO usable
signature on the pinned exe. The Hexinton "DisplayBossHPBar by Pavuk" AOBs —
`DisplayFunc = 25 EC 48 89 5C 24 08` and `DisplayDisableFunc = A7 40 53 48 83 EC 20 8B D9` — are
**stale in BOTH the v5.0 (tablever 2.6.1.0) and v6.0 (tablever 2.6.2.0) tables** and resolve **zero**
times in `eldenring.exe` (sha256 3410…3492ddb), confirmed by raw byte scan. The v6.0 table did not
update that script; its real boss contribution is a warp data table (boss → PlayRegion + BonfireFlags
+ `isBoss`), not a runtime bar read.

**Mechanism shipped — FieldArea PlayRegionId (the resolvable signal v6.0 actually carries):**
- Read the player's current PlayRegionId and gate on a set of known boss-arena PlayRegions.
- `PlayRegionId = *(s32*)( *(FieldArea_ptrloc) + 0xE4 )`.
- `FieldArea_AOB` (from the v6.0 aobList) = `48 8B 0D ?? ?? ?? ?? 48 ?? ?? ?? 44 0F B6 61 ?? E8 ?? ?? ?? ?? 48 63 87 ?? ?? ?? ?? 48 ?? ?? ?? 48 85 C0` — **VERIFIED UNIQUE** in this exe; `mov rcx,[rip+disp]`, ptr-loc resolves to **RVA 0x03D691D8**.
- PlayRegionId field offset **0xE4** (v6.0 table `FieldArea:PlayRegionId`).
- Boss-arena set (`kBossArenaPlayRegions`, er_gamehook_win.cpp) curated from the v6.0 `isBoss`
  arenas (17 major/remembrance bosses: Margit 6101010, Godrick 1000000, Makar 3920000, Rennala
  1400000, Rykard 1600000, Morgott 1100000, Hoarah Loux 1105000, Radagon 1900000, Elden Beast
  1900001, Radahn 6400040, Fire Giant 6502010, Malenia 1500000, Astel 1204000, Mohg 1205000,
  Fortissax 1203000, Placidusax 1300020, Maliketh 1300000).

**Why coarser-than-a-bar-read is OK:** a PlayRegion reads "active" from arena-entry until you leave,
so it can defer past the kill or before aggro. That is exactly what the **mandatory starvation cap**
bounds: `kMaxBossDeferMs = 30000` (Core.cpp). After 30 s of continuous deferral the queue drains
regardless of boss state, so a stuck/misread region can NEVER permanently block grants. This also
satisfies the brief's "camp in an arena without engaging → cap fires" test. No change to grant
counts / received-index — every item still arrives, just reordered after fights.

**Files touched:**
- `er_hooks.h` — `FieldArea_AOB`, `FieldArea_PtrLoc_RVA` (0x03D691D8), `FIELDAREA_PLAYREGION_OFF` (0xE4).
- `er_gamehook.h` / `er_gamehook_win.cpp` — `bool IsBossFightActive()` (page-validated SafeRead;
  resolves FieldArea in `Init()`, non-fatal if it misses; debug-logs the live PlayRegionId every call).
- `GameHook.h` / `GameHook.cpp` — `bool CGameHook::isBossActive()` → `IsBossFightActive()`.
- `Core.cpp` ~442 — second guard on the paced drain: defer while `isBossActive()`, drain on clear OR
  cap; named const `kMaxBossDeferMs = 30000`, per-tick `bossDeferSinceMs` window.

Syntax-checked the added bodies with `g++ -std=c++20 -fsyntax-only` (clean). NOT yet compiled in the
real Windows build (build.ps1) and NOT yet playtested — the boss-arena PlayRegion mapping needs one
live pass.

**Live verification recipe (next session, on Windows):**
1. Build the client (build.ps1); confirm the startup log line `er::Init FieldArea: match=… ptrLoc=…`
   shows a non-zero ptrLoc (≈ image_base + 0x03D691D8).
2. `/debug on`, enter a boss arena, and watch for `isBossActive: PlayRegionId=N -> BOSS/no`. Confirm
   the id during each fight matches the set; add any missing ids (esp. overworld/field bosses, which
   may not carry a distinct PlayRegion).
3. Flood incoming items mid-fight → confirm nothing pops until the bar clears (region exit / cap).
   Multi-phase (Godrick, Rennala) should keep deferring across phases (same PlayRegion). Camp without
   engaging → confirm the 30 s cap fires.
4. Tune `kMaxBossDeferMs` / `kBossArenaPlayRegions` from what the log shows.

### Task B — suppress native popup + event banner — NOT STARTED

Intentionally deferred per the brief's scope order (Task B follows A *after A is playtested*). A is
code-complete but un-playtested here (no game in this environment), so B is the next session's work.
