# SPEC: Reverse-engineering thefifthmatt's latest ER enemy rando — adapt newer features for Archipelago

Status: PLAN (research done 2026-06-13). Scope: identify what's new in thefifthmatt's
*Elden Ring* Item & Enemy Randomizer (Nexus mod 428) since the v0.8 source our AP fork
sits on, and lay out a clean-room path to fold the enemy-side features — chiefly DLC
(Shadow of the Erdtree) enemy randomization — into the Archipelago stack. Personal-use /
interoperability work only; see Legal guardrails. This is the enemy-rando companion to
the already-filed integration notes; it supersedes nothing in the apworld/client yet.

## The actual situation (what "old" and "latest" really are)

The phrasing "I have an older version of the source" is true but the gap is narrower and
weirder than it sounds. Three facts from `git ls-remote` + local history:

- **His public source is frozen at v0.8.** `thefifthmatt/SoulsRandomizers` master tip is
  `140f724` "Elden Ring Randomizer v0.8 update" dated **2023-11-28**. That is the newest
  public commit. The `er` branch (`811a75d`) is a 2022 relic, older than master — a dead
  end, not the latest.
- **Our fork already carries that exact v0.8 merge-base.** `4laric/SoulsRandomizers`
  (`archipelago` branch, the source bundled in `Elden Ring Randomizer-428-v0-11-4.../SoulsRandomizers/`)
  merged `thefifthmatt/master` at `c0efece`, whose upstream parent is `140f724`. So our
  C# "old source" *is* his latest public C# source. The two `EnemyRandomizer.cs` copies in
  the repo are byte-identical (8,464 lines, v0.8).
- **The shipped mod is far ahead: v0.11.4 (DLC era).** `randomizer/EldenRingRandomizer.exe`
  is the current Nexus build with full Shadow of the Erdtree support. The delta v0.8 → v0.11.4
  is **not in public source** — it lives in (a) the mod's shipped *plaintext* config/annotation
  files, (b) the compiled `.exe`, and (c) two new companion DLLs.

So "reverse-engineering the latest" is really: **recover the v0.8 → v0.11.4 enemy delta from
the shipped artifacts you already own**, since he never pushed it to GitHub. Most of it is
sitting in readable text in the 428 folder right now.

## Legal guardrails (read before forking anything)

His license is the landmine noted in project memory: source-available but **not freely
licensed** — *"Do not distribute the randomizer, forks of the randomizer programs, or forks
of config files."* Our posture, which keeps us clean:

- **Personal use and interoperability RE are fine.** Reading shipped config, decompiling the
  `.exe` to understand behavior, and adapting *concepts* into our own MIT code is standard
  interop work. Keep a local copy; don't redistribute his programs or config forks.
- **Data vs. expression.** Enemy *facts* — model IDs (`c5130`), map names (`m21_01_00_00`),
  defeat/start event flags, arena coordinates, NpcName FMG ids — are FromSoftware game data,
  not his copyrightable expression. Those we can and should derive **from the game's own
  params/MSBs/EMEVD** (we already unpack these), not by shipping his `enemy.txt`. His config
  is a convenient *reference to check our derivation against*, not a source to vendor.
- **The bright line for anything public** (the apworld, the client, anything on
  `4laric/*` that others install): do not commit his `enemy.txt`/`events.txt`/preset files
  or a decompiled dump of his code. Ship our own derived data + our own code. Using his files
  locally to *validate* our derivation is the safe middle path.
- **Companion DLLs** (`RandomizerCrashFix.dll`, `RandomizerHelper.dll`) are his redistributables;
  reference them by download, don't rebundle them in a public release without permission.

## Where the newer features actually live (the RE surface, quantified)

Diffing our v0.8-era fork config (`SoulsRandomizers/diste/`) against the v0.11.4 shipped
config (`randomizer/diste/`) localizes the entire enemy delta to two files:

| File | v0.8 lines | v0.11.4 lines | Δ | What it is |
|------|-----------:|--------------:|---:|-----------|
| `Base/enemy.txt` | 98,551 | 101,692 | **+3,141** | enemy class taxonomy + per-placement catalog (incl. DLC) |
| `Base/events.txt` | 17,753 | 17,849 | **+96** | enemy/boss event templates (incl. DLC scripted intros) |
| `Base/annotations.txt` | 2,983 | 2,983 | 0 (identical) | item-side config — unchanged |
| `Base/itemslots.txt` | 34,282 | 34,282 | 0 (identical) | item locations — unchanged |

The signal is clean: **the enemy roster/placement data and the event templates are the whole
story; the item side and the enemy *class taxonomy* are untouched.** DLC-tagged enemy entries
grew from 583 to 647 (+64 marquee additions). This is the cheapest, highest-value RE surface —
it's plaintext, it's already on disk, and it isn't compiled.

What is *not* recoverable from config (must come from the `.exe`): any change to the
randomization *algorithm* itself — new enemy-type handling, DLC-specific placement guards,
crash-avoidance logic, helper-ID allocation changes. The `.exe` is .NET (RandomizerCommon is
C# 100%), so ILSpy/dnSpy reconstructs near-source for a direct diff against our v0.8 tree.

## Feature catalog: v0.8 → v0.11.4 (enemy side)

1. **DLC enemy & boss randomization (the headline).** New maps `m20_*` (Gravesite Plain /
   Scadu Altus tier), `m21_*`, `m61_*`; new swap classes and placements for Messmer, Bayle,
   Romina, Midra, Metyr, Rellana, Gaius, Golden Hippopotamus, Divine Beast Dancing Lion,
   Putrescent Knight, and their retinues. Each placement record carries `DefeatFlag` /
   `StartFlag` — directly consumable as AP location flags. This aligns with our filed
   "next deliverable: DLC enemy rando."
2. **DLC event templates** (`events.txt` +96 lines) — scripted-intro / boss-arena event
   wiring for the new bosses. Relevant because AP location hooks ride on these flags, and
   because scripted intros are where cross-content placements tend to CTD.
3. **`RandomizerCrashFix.dll`** — shipped companion, *specifically recommended when base +
   DLC enemies are randomized together*. Adopt in our me3/ModEngine profile to stop CTDs
   when AP-shuffled DLC enemies land in base maps and vice-versa.
4. **`RandomizerHelper.dll` (+ `RandomizerHelper_config.ini`, plaintext)** — auto-equip /
   auto-upgrade QoL (equip weapons/armor/spells/tears on pickup; `+0` auto-upgrade). Config
   is human-readable and hot-reloaded. Optional for AP, but auto-equip is a genuine QoL win
   for AP runs where loadout arrives piecemeal from other worlds.
5. **Preset surface** — the enemy preset format (Oops All, boss-replacement %, reverse order,
   etc.) is stable from v0.8; the new content just extends the pools the presets draw from.

## Adapting each feature for Archipelago

| Feature | Where it lands in our stack | Notes |
|---|---|---|
| DLC enemy roster | AP enemy-shuffle pool + `enemy` derivation; new DLC boss `DefeatFlag`s → apworld locations / `location_flags`; client `PollLocationFlags` already polls flags | Derive model/map/flag data from game params+MSB+EMEVD, validate against his `enemy.txt` locally |
| DLC event templates | client/apworld location-flag hooks for DLC boss kills; `__init__.py fill_slot_data` | Confirm DLC defeat flags aren't already covered by base flag-poll set (likely new ranges) |
| RandomizerCrashFix.dll | me3 / ModEngine profile load order (reference download, don't rebundle public) | Required once DLC+base enemies mix under AP shuffle |
| RandomizerHelper auto-equip | optional AP YAML/slot_data option; or skip and rely on AP item-receipt UX | Hot-reload `.ini` style is a nice pattern to mirror |
| DLC region/boss gating | folds into existing `SPEC-scadu-in-base` / `SPEC-region-boss-gating` logic | DLC access already needs Scadutree handling — gate DLC enemy locations behind it |

The layering is the same insight as the base game: his randomizer is the **placement/roster**
authority; our AP work is the **logic + check/flag + slot_data** layer on top. Adopt his DLC
*roster and flags as data*, his crash-fix dll *as a runtime dependency*, and reimplement any
*algorithm* change in our own C#/apworld code rather than vendoring his.

## RE workflow (tiered, cheapest first)

**Tier 1 — config diff (do this first; hours, plaintext, already-owned).**
```
OLD="SoulsRandomizers/diste/Base"; NEW="randomizer/diste/Base"
diff "$OLD/enemy.txt"  "$NEW/enemy.txt"  > dlc_enemy.diff      # +3,141 lines
diff "$OLD/events.txt" "$NEW/events.txt" > dlc_events.diff     # +96 lines
```
Parse the `enemy.txt` additions into our own DLC roster table (schema in Appendix). Extract
every new `DefeatFlag`/`StartFlag` for DLC bosses → candidate AP locations. Cross-check each
derived `c####` model id and `m##_##` map against Paramdex/our own MSB dump so the public
artifact is *our* derivation, not his file.

**Tier 2 — decompile-diff the engine (when config can't explain a behavior).**
Open `randomizer/EldenRingRandomizer.exe` in ILSpy/dnSpy, export `RandomizerCommon`, and diff
its `EnemyRandomizer.cs` / `EnemyAnnotations.cs` / `EventConfig.cs` against our v0.8 tree
(`SoulsRandomizers/RandomizerCommon/*.cs`). Focus on: DLC map enable lists, new
`ParentClasses`, helper/writeable-ID allocation (the `tmpBase`/`writeBase` band logic), and
any DLC scripted-intro guards. Reimplement deltas in our fork; never publish his decompiled
source.

**Tier 3 — companion DLL behavior (only if adopting, not cloning).**
`RandomizerCrashFix.dll` / `RandomizerHelper.dll` are native redistributables. Treat as
black-box dependencies: wire into the me3/ModEngine profile, read `RandomizerHelper_config.ini`
for the option surface, and capture `RandomizerHelper_log.txt` to see what it equips. Only RE
the binary if we need to replicate crash-fix behavior independently.

## Deliverables

1. `dlc_enemy.diff` / `dlc_events.diff` + a derived `data/er_dlc_enemy_roster.json`
   (our own derivation: model id, map, defeat flag, start flag, class, arena coords).
2. Decompiled-vs-v0.8 engine diff notes (local only) cataloging algorithm changes worth porting.
3. apworld changes: DLC boss locations + DLC enemy pool gating behind Scadutree/region logic.
4. client changes: confirm DLC `DefeatFlag` ranges are in the polled flag set.
5. me3/ModEngine profile: `RandomizerCrashFix.dll` load-order entry + doc note.

## Open questions / risks

- **Flag-range overlap:** do DLC `DefeatFlag`s (e.g. `21010800`) collide with any AP synthetic
  flag bands our fork allocates? Verify before wiring locations.
- **Crash-fix necessity under AP shuffle:** our shuffle is Part-level and may already avoid the
  worst cross-content cases the dll guards; measure CTD rate with/without before declaring it required.
- **Version drift:** v0.11.4 is current as of this dump; if 428 updates again post-DLC patch,
  re-pull and re-diff config — the workflow above is repeatable.
- **DLC unpack:** our derivation needs the DLC maps/EMEVD unpacked (`m20_/m21_/m61_`); confirm
  Paramdex/MSB coverage matches the 647 DLC-tagged entries before trusting the roster.

## Tier-2 findings: engine decompile (done 2026-06-13)

Method: extracted the embedded assemblies from the v0.11.4 single-file bundle (it's a
self-contained **.NET 6 / win-x64** app — `RandomizerCommon.dll` 1.4 MB came out uncompressed),
decompiled `EnemyRandomizer`, `EnemyAnnotations`, `EventConfig`, `Preset` with ilspycmd 8.2
(ICSharpCode.Decompiler), and diffed the API surface + DLC code paths against our fork's v0.8
`RandomizerCommon/*.cs`. Tooling lives in `/tmp` (sandbox, ephemeral); see Reproduce below.
Decompiled output is **reference for understanding only** — reimplement in our own code, do
not vendor it.

What the config diff (Tier 1) could not show — the *algorithm* changes — resolve to these:

- **DLC area-silo partitioning (the central new mechanism).** v0.11.4 adds
  `LocationData.AreaSiloType` with a `DLC` value and a new `dlcsilo` option. The enemy pass
  computes `areaSiloType = (opt["dlc"] && (opt["dlcsilo"] || anyDupeEnabled)) ? DLC : None`,
  and a preset can force it via `preset.OverallSilo`. The silo decides **whether DLC enemies
  shuffle into base maps or stay partitioned to DLC areas**. This is the single most important
  thing to mirror in AP: it's the exact base↔DLC mixing decision, and it maps onto our existing
  region/Scadutree gating. (Note: `opt["dlc1"]`/`opt["dlc2"]` in the same area are the *DS3*
  code path — m45 Ariandel, m50/m51 Ringed City — not ER. ER uses the singular `dlc` + `dlcsilo`.)
- **DLC param/regulation fixups.** When anything is randomized, the engine forces
  `dlcGameClearSpEffectID = -1` (neutralizes a DLC completion-gate speffect), and handles DLC
  name FMGs (`NPC名_dlc1`/`NPC名_dlc2`) for swapped-enemy healthbar names. Our AP bake must
  replicate these param/FMG edits whenever DLC enemies are in the pool, or healthbars/clear
  gates misbehave. DLC count: **31 `dlc` code sites in v0.11.4 vs 10 in our fork.**
- **Clever-name grammar system.** New name-formatting modes — `proper`, `adjective`, `partial`,
  `sourcefull`, `none` — drive `CalculateCleverName`/`DefaultDescription` so a swapped enemy gets
  a grammatically sensible generated name. Cosmetic; low priority for AP but cheap to adopt.
- **Enemy tagging.** New `AddTag`/`GetNamedTag`/`SetTags` on the annotation model — richer
  per-enemy metadata than v0.8's flat fields. Could feed our AP logic categorization of DLC
  enemies (boss/field/grace-gated) instead of maintaining a parallel tag table.
- **Preset/config version migration.** New `MigrateVersion` auto-upgrades old presets to the
  current schema — relevant only if our AP option surface piggybacks on his preset format
  (then we inherit the version field and migration path).
- **Event-ID allocation expansion.** `AllocateWritableEventIDs`/`NewEventID`/`isFakeId` widen the
  synthetic event-ID space for the added DLC content — watch for collisions with the AP fork's
  own event/flag allocations (ties back to the Tier-1 DefeatFlag-range open question).

AP port priority from this: (1) the `dlcsilo` mixing decision → a slot option + bake logic;
(2) the DLC speffect/FMG fixups → mandatory bake steps when DLC enemies randomize; everything
else is QoL.

### Deep-dive: the DLC silo path (concrete apworld port target)

Full trace from the decompile. The mechanism is a **bucketed permutation**: every enemy
placement belongs to an `AreaSilo`, and a swap only ever happens between placements in the
same bucket. The bucket key is `(EnemyClass, AreaSilo.Type, AreaSilo.Index)` (the `CompareTo`
at EnemyRandomizer.cs:347 sorts on exactly this tuple).

`LocationData.AreaSiloType { None, DLC, Region }`, and silos are minted by a factory:
```csharp
new AreaSilo(AreaSiloType.None, 0)                              // one global bucket — everything mixes
new AreaSilo(AreaSiloType.DLC, dlc ? 1 : 0, dlc ? "dlc":"base") // two buckets: base(0) and dlc(1)
bool IsDlc() => Type == AreaSiloType.DLC && Index == 1;
```
So **DLC silo = two buckets**: non-DLC placements land in `base` (Index 0), DLC-map placements
(`m20_/m21_/m61_`) land in `dlc` (Index 1); base enemies can't swap into DLC slots and vice
versa. `None` = one bucket, full cross-content mixing (Messmer can land in Limgrave). `Region`
is a defined-but-dormant third mode (per-region buckets); the live ER path is None vs DLC.

The decision (EnemyRandomizer.cs:1906):
```csharp
areaSiloType = (opt["dlc"] && (opt["dlcsilo"] || anyDupeEnabled)) ? DLC : None;
if (opt["dlc"] && areaSiloType == None && preset != null)
    areaSiloType = preset.OverallSilo;          // preset can force DLC/Region even if option off
```
- `opt["dlcsilo"]` is the user checkbox **"DLC bosses and enemies randomized separately"**
  (`Preset_dlcsilo`).
- `anyDupeEnabled` (`EnemyMultiplier > 1` or any per-class dupe count > 0) **forces DLC silo** —
  dupes mustn't pull cross-content into a constrained pool.
- Presets override at two levels: `OverallSilo` (whole pool) and per-class `ClassSilo`
  (EnemyRandomizer.cs:3091 — `areaSiloType2 = classAssignment2.ClassSilo`), so a preset can keep,
  say, only bosses separated while basics mix.

**Port target for our AP bake.** This is entirely bake-side — it never reaches the client or
`fill_slot_data`; it shapes which enemy lands where before the files are written. To adopt it
in our v0.8-based fork (which has `opt["dlc"]` but not the silo system):

1. Add `AreaSilo`/`AreaSiloType` + `IsDlc()` to our LocationData equivalent; stamp each ER area
   DLC vs base from the map id (see the verified prefix table below). Data-driven, derivable from
   our own MSB set — no need to copy his config.

   **DLC map prefixes (verified, with names).** Sources: thefifthmatt's own pre-DLC base-game
   map-name list (gist `gracenotes/9c3f7979…`) for the base set, and the Souls Modding Wiki
   DLC-updated map overview (`soulsmodding.com/doku.php?id=er-refmat:map-overview`) for the SOTE
   names, cross-referenced with the v0.11.4 `enemy.txt` map set. **Base** = `m10`–`m19`,
   `m30`–`m39`, `m60`. **DLC** = `IsDlc` ⇔ map-number ∈ {20–28, 40–45, 61}:

   | Prefix | DLC area(s) |
   |--------|-------------|
   | `m20` | Belurat Tower Settlement (`m20_00`), Enir-Ilim (`m20_01`) |
   | `m21` | Shadow Keep (`_00`), Specimen Storehouse (`_01`), Shadow Keep West Rampart (`_02`) |
   | `m22` | Stone Coffin Fissure |
   | `m25` | Finger Birthing Grounds |
   | `m28` | Midra's Manse |
   | `m40` | DLC catacombs — Fog Rift / Scorpion River / Darklight |
   | `m41` | DLC gaols — Belurat / Bonny / Lamenter's |
   | `m42` | DLC ruined forges — Lava Intake / Starfall Past / Taylew's |
   | `m43` | DLC caves — Rivermouth Cave / Dragon's Pit |
   | `m45` | Colosseums — Royal / Caelid / Limgrave |
   | `m61` | Realm of Shadow overworld (Land of Shadow tiles) |

   ⚠️ Earlier drafts said only `m20_/m21_/m61_` — that under-counts and would leak
   `m22/m25/m28/m40–m43` into the base silo. Two caveats: `m45` (Colosseums) shipped in a *free*
   base-game update, not the paid DLC, and is PvP with negligible randomizable enemy content —
   classify it however is convenient, it barely affects the pass. And `m20_01` is **Enir-Ilim**,
   not `m22` (a correction to my first pass). Validate against the live diste roster before locking.
2. Make the enemy permutation bucket on `(class, silo.Type, silo.Index)` instead of `(class)`.
3. Expose an AP slot option, e.g. `dlc_enemy_silo: separate | mixed` (+ optional `region`),
   threaded options.py → apconfig → the bake's `opt["dlcsilo"]`. Keep the `anyDupeEnabled`
   force-rule.
4. **Default `separate`.** Two reasons: (a) stability — full mixing is the cross-content CTD
   case `RandomizerCrashFix.dll` exists to patch; (b) **AP-logic correctness** — under `mixed`,
   a DLC-tier boss can land on a base-game *required-path* slot, forcing a DLC-difficulty fight
   before DLC access and distorting early spheres. `separate` keeps DLC enemies behind DLC
   access, which aligns with our `SPEC-scadu-in-base` / region-boss-gating. Offer `mixed` as an
   explicit chaos opt-in.

The `Region` mode is worth noting as prior art for our region-gating work — same bucketing
machinery, keyed on region index instead of DLC flag.

### Reproduce (sandbox)
```
# extract assemblies from the single-file bundle
python3 extract_bundle.py EldenRingRandomizer.exe ./asm        # -> asm/RandomizerCommon.dll
# decompiler: .NET 8 runtime + ilspycmd 8.2 (net6.0 tool, roll-forward)
dotnet-install.sh --runtime dotnet --channel 8.0 --install-dir ./dotnet
# ilspycmd.$V.nupkg from nuget flatcontainer, unzip
DOTNET_ROLL_FORWARD=Major dotnet ilspycmd.dll asm/RandomizerCommon.dll \
    -t RandomizerCommon.EnemyRandomizer -o decomp
# then diff decomp/*.cs API surface vs fork RandomizerCommon/*.cs
```

## Implementation sketch: wiring `dlc_enemy_silo`

Verified against the current fork. The plumbing is three small diffs; the load-bearing
work is the engine port (step 4), without which the flag is inert — our v0.8
`EnemyRandomizer.cs`/`LocationData.cs` have **zero** `AreaSilo`/`opt["dlc"]` references, and
the ER bake never sets `opt["dlc"]` at all (only `game.KeepDlcMaps`).

**1. `worlds/eldenring/options.py`** — new toggle by the other enemy sub-toggles (~L313),
registered in `EROptions` (~L408) and the "Enemy Randomizer" `OptionGroup` (~L453):
```python
class DLCEnemySilo(DefaultOnToggle):
    """Enemy randomizer: keep DLC bosses/enemies in DLC maps and base enemies in base
    maps (no cross-content mixing). On by default — for stability (full mixing is the
    cross-content CTD case RandomizerCrashFix.dll patches) and so a DLC-tier boss can't
    land on a base required-path slot and gate an early sphere. Off = full chaos.
    Only has an effect with Enemy Randomizer + Enable DLC on."""
    display_name = "Separate DLC Enemies"
# EROptions:        dlc_enemy_silo: DLCEnemySilo
# OptionGroup(...):     DLCEnemySilo,
```

**2. `worlds/eldenring/__init__.py`** — in `fill_slot_data`'s `"options"` dict, next to
`impolite_enemies` (~L2697). Real `bool` so it survives ArchipelagoForm's bool-only filter:
```python
                "dlcsilo": bool(self.options.dlc_enemy_silo.value),
```

**3. `SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs`** — `ConvertRandomizerOptions`,
ER case. Add the silo flag inside the `randomize_enemies` block after `impolite` (~L912),
and set `opt["dlc"]` (the silo decision reads it) before the ER `break;` (~L926):
```csharp
                        opt["dlcsilo"] = archiOptions.GetValueOrDefault("dlcsilo", true);
                    // ...still in the ER case, outside the randomize_enemies block:
                    opt["dlc"] = archiOptions.GetValueOrDefault("enable_dlc", false);
```

**4. Engine port (the actual feature) — `EnemyRandomizer.cs` + `LocationData.cs`.** The
above only feeds an option the v0.8 engine doesn't read yet. Reimplement per the Deep-dive:
add `AreaSiloType{None,DLC,Region}` + `AreaSilo`/`IsDlc()`; stamp each area DLC by map prefix
(verified set: `m20 m21 m22 m25 m28 m40 m41 m42 m43 m45 m61`; base = `m10`–`m19`,`m30`–`m39`,`m60`);
key the enemy permutation bucket on `(class, silo.Type, silo.Index)`; and
gate it on `opt["dlc"] && (opt["dlcsilo"] || anyDupeEnabled)`. This is our own
reimplementation (not a copy of his decompiled source). Until it lands, the DLC enemy pass
runs as `None` (full mix) regardless of the toggle.

Sequencing: ship 1–3 with the toggle defaulting **on** but documented as a no-op pending the
engine port, or hold all four until step 4 is done so the option never lies about its effect.
The latter is cleaner for a release; the former is fine on a feature branch for the rebuild.

## Appendix — `enemy.txt` record schema (the parse target)

Two record kinds matter. **Class/taxonomy** (top section):
```
- Name: Messmer the Impaler
  ParentClasses:
  - Boss
  Count: 1
```
**Placement** (lower section — the AP-relevant one):
```
- ID: 21010800
  Map: m21_01_00_00
  Name: c5130_9001
  Class: Boss
  DefeatFlag: 21010800
  StartFlag: 21012802
```
Plus boss display metadata (`ExtraName`/`FullName`/`PartName`/`NpcName`/`ExtraArenas` coords)
used for healthbar names and arena placement. `DefeatFlag` is the join key to AP locations;
`Name: c####_####` gives the model (`c5130` = Messmer) for pool/class membership.
