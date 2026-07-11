# Greenfield Elden Ring — DLC (Shadow of the Erdtree) Playtest-Readiness Audit

**Date:** 2026-07-08 · **Repo HEAD:** `6311281` (clean tree) · **Auditor:** provision-gen + static inspection (no client runtime available)
**Scope:** the 6 DLC regions in `region_spine.py` — Land of Shadow, Belurat, Scadu Altus, Shadow Keep, Jagged Peak, Abyssal Woods.

> This is an **audit only** — no feature code was changed. Findings are grounded in an actual Linux
> provision-gen (stock ArchipelagoMW runtime, `~/.greenfield-ci`) plus reads of the generated
> data/slot_data. Client (`crates/eldenring-archipelago`) runtime behavior could NOT be executed
> here; anything requiring the live game is called out as an in-game UNKNOWN.

---

## What was actually run

1. `bash greenfield/provision-linux-env.sh` → Python 3.11.15 + stock AP clone at `~/.greenfield-ci/ap` (READY).
2. Installed world: `git archive HEAD:greenfield/eldenring | tar -x` into `.../ap/worlds/eldenring`.
3. Four full generations (build a solo `MultiWorld`, run `generate_early…pre_fill`, `distribute_items_restrictive`, `post_fill`, then `fill_slot_data()`), dumping location placements, item pool, and every DLC-relevant slot_data key:
   - **A. `enable_dlc:1, num_regions:0`** (all 21 regions kept) → **WINNABLE, no FillError.** 3958 locations, 21 kept.
   - **B. `dlc_only:1, num_regions:0`** (6 DLC regions kept) → **WINNABLE, no FillError.** 1097 locations, 6 kept.
   - **C. `dlc_only:1 + ending_condition:great_runes + item_shuffle:1`** → **WINNABLE**; goal collapsed to `region_locks`, `great_runes_required→0` (as documented).
   - **D. `enable_dlc:1 + ending_condition:great_runes + item_shuffle:1`** → **WINNABLE**; 6 Great Runes ×2 in pool, requirement 5.
4. Pytest: `test_gf_dlc.py`, `test_gf_dlc_pool_leak.py`, `test_gf_grace_region_correctness.py` → **61 passed, 7 skipped** (skips = documented grace skip-list cases).

---

## Per-region readiness matrix

Legend: 🟢 Solid · 🟡 Rough (works, granular/thin) · 🔴 Broken/blocking · ⚪ N/A-by-design

| Region | Checks (gen count) | Item payout | Lock+Open+Grace bundle | Kick-watch geometry | Boss coverage | Scaling | Verdict |
|---|---|---|---|---|---|---|---|
| **Land of Shadow** | 🟡 **536** (mega; absorbs sub-area overworld) | 🟢 | 🟢 own bundle (76800–76960) | 🟢 5 play_ids | 🟢 2 (Radahn, Putrescent Knight) | 🟢 | 🟡 **Rough (over-stuffed)** |
| **Shadow Keep** | 🟢 159 | 🟢 | 🟢 own bundle (72102–72120) | 🟢 3 play_ids | 🟢 1 (Messmer) | 🟢 | 🟢 **Solid** |
| **Belurat** | 🟢 34 | 🟢 | 🟢 own bundle (74100–74351) | 🟢 2 play_ids | 🟢 2 (Dancing Lion, Rellana) | 🟢 | 🟢 **Solid** |
| **Scadu Altus** | 🟡 23 (+~17 of its checks live in LoS bucket) | 🟢 | 🔴 **NO own bundle** — folded into Land of Shadow | 🟢 4 play_ids | 🟢 4 (Metyr, Romina, Shadow Sunflower, Gaius) | 🟢 | 🟡 **Rough (hollow lock)** |
| **Jagged Peak** | 🟡 **6** (very thin) | 🟢 | 🔴 **NO own bundle** — folded into Land of Shadow | 🟢 2 play_ids | ⚪ none (Bayle excluded by design) | 🟢 | 🟡 **Rough (hollow lock, thin)** |
| **Abyssal Woods** | 🔴 **3** (near-empty) | 🟢 | 🔴 **NO own bundle** — folded into Land of Shadow | 🟢 2 play_ids | 🟢 1 (Midra) | 🟢 | 🟡 **Rough (hollow lock, thin)** |

All location **names are real and meaningful** (cookbooks, sorceries/incantations, remembrances, gear with `[fNNNN]` flags) — **no placeholder/empty `"check"` names, no `PENDING` map ids** in any DLC region.

---

## Dimension-by-dimension detail (grounded in the gen)

### 1. Checks
- **Distribution is severely lopsided** (from gen A/B, identical both seeds):
  Land of Shadow **536** · Shadow Keep **159** · Belurat **34** · Scadu Altus **23** · Jagged Peak **6** · Abyssal Woods **3**.
- Land of Shadow is a **coarse mega-bucket**: it contains **13 locations named `Scadu…` and 4 named `Rauh…`** (Scadu Altus / Rauh Ruins overworld), i.e. the Scadu Altus overworld checks are *split* between the Scadu Altus region (23) and the Land of Shadow bucket. This is the deliberate coarse DLC bucketing noted in `SPEC-PARITY.md` §265 ("already buckets DLC into coarse regions … DLC rides as plain lock gates"). Not broken — every check is still reachable and winnable — but the region granularity is misleading.
- Jagged Peak (6) and Abyssal Woods (3) are thin enough that their Locks gate almost nothing.

### 2. Item payout / filler quality
- DLC catalog items **do enter the pool and pay out**: gen A had **836 DLC-item copies / 54 distinct** (`DLC_ITEM_NAMES`); gen B **241 / 53**. Examples: Shadow Realm Rune [1]/[2], greases (Dragon Communion, Dragonbolt, Royal Magic), Spiritgrave Stone, Deep-Purple Lily, Scarlet Bud.
- DLC-region check contents look healthy in samples (Golden Runes, smithing stones, cookbooks, greases, remembrances). No obvious junk-only starvation.

### 3. Region Lock + open flag + grace bundle
- **All 6 DLC regions have a `<Region> Lock` progression item and a `regionOpenFlags` entry** (Land of Shadow 76800, Belurat 74100, Scadu Altus 76900, Shadow Keep 72102, Jagged Peak 76850, Abyssal Woods 76860).
- **`regionGraces` (own grace bundle / start door) exists for only 3 of 6:** Land of Shadow, Belurat, Shadow Keep. **Scadu Altus, Jagged Peak, Abyssal Woods have NO own bundle** — `region_graces.py` has no key for them. Their graces (including their open flags 76900 / 76850 / 76860) are **folded into Land of Shadow's bundle** (76800–76960).
- **Consequence:** receiving **Land of Shadow Lock blooms the whole DLC overworld**, which sets 76900/76850/76860 → Scadu Altus / Jagged Peak / Abyssal Woods open *at the same time*. Those three regions' own Locks are therefore **access-redundant** (the region is already reachable) but still **goal-required** (`set_rules` needs every kept Lock). Effectively the DLC behaves as **~3 lock-regions**: Land of Shadow (+Scadu/Jagged/Abyssal), Belurat, Shadow Keep.

### 4. Kick-watch / play_region coverage
- `features/area_locks.REGION_PLAY_IDS` covers **all 6 DLC regions** (DLC table: LoS 6800/6830/6840/20010/22000; Belurat 6820/20000; Jagged 6850/6851; Abyssal 6860/28000; Scadu 6900/6920/6940/6950; Shadow Keep 21000/21001/21010).
- `areaLockFlags` emitted **52 ranges** (all regions with a resolved open flag, kept or sealed — the 2026-07-08 dead-drop fix). The gen-time coverage gate (`AreaLocks.slot_data`) would hard-fail on a kept region that resolved an open flag but had no geometry; **none did.**
- **`REGION_OPEN_PENDING` is now empty** — the memory note that Abyssal Woods / Jagged Peak / Scadu Altus are `map=PENDING` is **STALE**; all 6 DLC open flags are resolved. (Resolution was to key them to the Land-of-Shadow-bloomed grace flags — see §3, which is why their bundles are folded.)

### 5. Boss coverage (`boss_data.REGION_BOSSES` → `bossLocations`)
- **10 DLC remembrance bosses covered:** Belurat 2 (Dancing Lion, Twin Moon Knight/Rellana), Land of Shadow 2 (God-and-a-Lord/Radahn, Putrescence), Scadu Altus 4 (Mother of Fingers/Metyr, Saint of the Bud/Romina, Shadow Sunflower, Wild Boar Rider/Gaius), Shadow Keep 1 (Impaler/Messmer), Abyssal Woods 1 (Lord of Frenzied Flame/Midra).
- **Jagged Peak has no boss** — Bayle intentionally excluded per `er-boss-locks-v01`. ⚪ by design.
- `bossLockItems` (synthetic Felled tracker): **16 emitted under enable_dlc, 0 under dlc_only** — Felled/Boss-Keys are base-only for v0.2 by design, so dlc_only has none.

### 6. Grace-region correctness
- `test_gf_grace_region_correctness.py` **passes** — the LoS folding is NOT flagged, because the oracle checks the overworld *cluster* (thousands-prefix), and the folded DLC graces stay within the 76xxx DLC space. So no *cross-cluster misbundle* — but the folding is still a granularity smell the oracle is not designed to catch.

### 7. Scaling / Scadutree
- `regionSphereTargetRanges` (live completion-scaling wire) covers **all DLC play_region buckets** (52 triples enable_dlc / 18 dlc_only). `global_scadutree_blessing` option is surfaced and echoed in `sd["options"]` (default 0). **DLC is covered by scaling.**

### 8. DLC physical entry — the key UNKNOWN
- **There is NO handling of the vanilla DLC-entry prerequisite** (defeat Mohg + Radahn, touch the Cocoon). Grep for cocoon / DLC-entry / prereq flags in the world returned nothing; `SPEC-PARITY.md` §265 confirms "DLC rides as plain lock gates."
- The world's model is **warp-in via grace-bloom**: Land of Shadow Lock lights DLC graces and you warp there. **Whether the game will actually load the DLC map / place you at a DLC grace when the vanilla cocoon-entry flag is unset is UNVERIFIED** (needs the live client + game). This is the single biggest in-game risk and cannot be settled from gen data alone.

---

## `dlc_only` backlog verification (what reproduces)

| Backlog claim (`er-dlc-only-base-lock-leak`) | Observed | Status |
|---|---|---|
| Base **Lock items** stay in the pool under `dlc_only` | Pool base-lock count = **{} (none)** | **Does NOT reproduce — fixed** |
| Base-region `areaLockFlags` ranges present under `dlc_only` | **34 base ranges present** | **Intended** (dead-drop fix seals base regions so player is kicked out) — not a leak |
| `great_runes` goal **collapses** to `region_locks` under `dlc_only` | `ending_condition→region_locks`, `great_runes_required→0`, still winnable | **Reproduces as documented** (working as intended) |
| Standalone runes-in-Land-of-Shadow goal under `dlc_only` | Not implemented | Scoped out of v0.2 (N/A) |

---

## Prioritized findings

### 🔴 Blocks playtest (must resolve/verify first)
1. **DLC physical-entry unverified (cocoon/Mohg gating).** The warp-in path assumes grace-bloom is enough to enter the DLC; the vanilla entry flag is never set. If the game refuses to load the DLC map without it, *no DLC region is reachable in-game* regardless of the (correct) slot_data. **Must be smoke-tested in-game before any DLC playtest.**

### 🟡 Playable-but-rough (ship to playtest with a caveat)
2. **Region-lock granularity collapse.** Scadu Altus / Jagged Peak / Abyssal Woods have no own grace bundle; their Locks are goal-required but access-redundant (they open when Land of Shadow Lock is received). The "num_regions marquee" therefore treats the DLC as ~3 effective lock-regions, not 6. Confusing but reachable + winnable.
3. **Land of Shadow 536-check mega-region** absorbs 13 `Scadu…` + 4 `Rauh…` overworld checks. Over-stuffed sphere; uneven pacing.
4. **Jagged Peak (6) and Abyssal Woods (3) are near-empty regions** — their Locks gate almost nothing.

### ⚪ Polish / by-design (no action for playtest)
5. Jagged Peak has no boss check (Bayle excluded — intended).
6. `bossLockItems`/Felled absent under `dlc_only` (base-only by design).
7. `global_scadutree_blessing` default 0 (off) — fine; a playtest may want to try 1/2.

---

## Minimum to start DLC playtests

1. **One in-game smoke test of DLC entry (the gate):** gen an `enable_dlc` (default) seed, connect the live client on a save that has **NOT** done the vanilla cocoon, receive **Land of Shadow Lock**, and confirm you can (a) warp to a Land-of-Shadow grace, (b) stand in Land of Shadow / Scadu Altus / Jagged Peak / Abyssal Woods without being kicked, and (c) load the DLC map at all. If entry fails, add the vanilla DLC-entry flag(s) to the Land of Shadow bloom before playtesting. **This is the only true blocker.**
2. **Playtest with `enable_dlc` (default), not `dlc_only`.** Both gen winnable, but `dlc_only` amplifies the hollow-lock and no-Felled roughness. `enable_dlc` embeds the DLC in a full run where the coarse buckets matter less.
3. **Brief the playtesters:** the DLC currently behaves as ~3 lock-gated regions (Land of Shadow [+Scadu Altus/Jagged Peak/Abyssal Woods], Belurat, Shadow Keep); expect a very front-loaded Land of Shadow.

**Bottom line:** the DLC **gens clean and winnable today** (enable_dlc *and* dlc_only), with correct kick geometry, boss data, scaling, and real-named checks. **Belurat and Shadow Keep are playtest-solid.** The DLC's data layer is playable; the two things standing between it and a smooth playtest are the **unverified in-game DLC-entry** (potential hard block — verify first) and the **coarse region granularity** (cosmetic/pacing — ship with a caveat).
