# Greenfield ER — in-game validation checklist

Everything below is gen-tested green (276 world tests). This is the in-game proof pass. Work the
tiers in order — Tier 0 must pass before the rest means anything. Each seed is a one-region-per-line
yaml; gen with `.\build.ps1 -Greenfield` (installs the world + gens against greenfield\players).

## 0. Prerequisites (once)

1. **Regenerate data on Windows** so the generated files match the committed gen_data:
   `python greenfield\gen_data.py`  (writes data.py, region_open_flags.py [22/22], boss_data.py,
   region_graces.py, boss_sweeps.py, shop_data.py, item_ids.py [98.9%], item_tiers.py).
2. **Apply the client sweep patch + rebuild the DLL** (needed for Tier 2 sweeps):
   `python patch_p3b_client.py --apply`
   `cargo test -p eldenring-archipelago`  → then build the runtime `.dll` as usual.
3. **Confirm green**: `.\run_ci.ps1 -OnlyGreenfield` (or `bash greenfield/ci-linux.sh` in WSL).
4. Put each test yaml below in `greenfield\players\` (one at a time, or a few), gen, connect the DLL.

Base yaml shape:
```yaml
name: GFTest
game: "Elden Ring (Greenfield)"
"Elden Ring (Greenfield)":
  <options>
```

---

## Tier 0 — BOOT (must pass first)

**T0.1 — Filler grant + region-open + check registration.** Options: none (defaults, but turn
item_shuffle OFF and dungeon_sweep none to isolate boot):
```yaml
  item_shuffle: false
  grace_rando: false
  dungeon_sweep: none
```
- Connect a fresh seed. **PASS:** the client logs "flag-poll table: N location flags"; you spawn and
  can play; picking up a randomized check **sends a check** (server sees it). 
- Receive a **"<Region> Lock"** item (have a co-op partner send one, or self-give via the client). 
  **PASS:** that region's front-door grace lights (you can warp there) — this is `regionOpenFlags`.
- Receive a **Rune** filler. **PASS:** you get a Golden Rune [1] in inventory (`apIdsToItemIds`).
- **FAIL signs:** checks never send (locationFlags not applied), lock receipt does nothing (open flag
  wrong), filler grants nothing.

---

## Tier 1 — CORE MODES

**T1.1 — Item shuffle (real vanilla items).**
```yaml
  item_shuffle: true
  grace_rando: false
  dungeon_sweep: none
```
- **PASS:** checks now pay out **real ER items** (weapons/armor/goods), not just Runes; receiving one
  grants the correct game item. ~98.9% of checks carry a real item; the rest give Rune (expected).
- Spot-check a known location's item is a real item of the right category.

**T1.2 — num_regions sealing.**
```yaml
  num_regions: 3
  num_regions_order: spine
```
- **PASS:** only Limgrave / Weeping Peninsula / Stormveil Castle + Leyndell are "in play" (their locks
  gate them); the goal completes on collecting those 4 locks; seed is winnable end-to-end.
- Try `num_regions_order: rolled` too — a different random 3(+goal) set, still winnable.

---

## Tier 2 — DUNGEON SWEEPS (validates the client patch)

**T2.1 — Sweep on boss kill.** REQUIRES the `patch_p3b_client.py` DLL from Prereq 2.
```yaml
  item_shuffle: true
  dungeon_sweep: all
```
- Enter a catacomb/cave, kill its boss. **PASS:** the dungeon's OTHER checks all register at once
  (the client watches the boss-defeat flag via `dungeonSweepFlags` → grants the members). Client log:
  a burst of "flag-poll: N new check(s)" right after the boss dies.
- **FAIL sign:** boss dies but the dungeon's other checks don't auto-send → the client patch isn't in
  the running DLL (rebuild), or the boss-defeat flag differs (note the dungeon + report back).
- **Not expected to work:** location-keyed sweeps (`dungeonSweeps`) and boss-lock gating
  (`sweepLockGates`) are empty by design — only flag-keyed sweeps fire. That's correct.

---

## Tier 3 — FEATURES

**T3.1 — Grace freebie + scatter.**
```yaml
  grace_rando: true    # default; freebie mode
  item_shuffle: true
```
- Receive a "<Region> Lock". **PASS:** exactly ONE grace lights in that region (front door).
- Receive a **"Grace: <Region> #k"** item (from the pool). **PASS:** that specific grace lights.
- Bundle mode: set `grace_rando: false` → a lock lights ALL that region's graces, no scatter items.

**T3.2 — Shops as checks.**
```yaml
  item_shuffle: true
```
- Buy an item from a merchant (Twin Maiden / Kalé / etc.). **PASS:** that shop slot registers as a
  check (`shopRowFlags` on the purchase's stock flag). Preview (scouting) shows the real vanilla good.
- **Not expected:** `merchant_bell_logic: logic_only` does NOTHING (bell→shop gating is an unresolved
  boundary — engine C++, not derivable). Leave it off; it's a documented no-op.

**T3.3 — Pool builder (juice).**
```yaml
  item_shuffle: true
  pool_builder: true
```
- **PASS:** high-tier items (rare/legendary weapons, talismans, armor) show up noticeably more than
  without it (they replace the Rune tail). Compare a check-heavy area vs a `pool_builder: false` seed.

**T3.4 — Great-Rune goal.**
```yaml
  item_shuffle: true
  ending_condition: great_runes
  great_runes_required: 2
```
- **PASS:** the seed's goal requires collecting 2 Great Runes (they're placed as progression, so
  reachable); you cannot "finish" until you have 2. (num_regions that seals all rune regions auto-drops
  the requirement — that's intended, not a bug.)

**T3.5 — Progressive items.**
```yaml
  item_shuffle: true
  progressive_flasks: true
```
- Receive a **"Progressive Golden Seed"**. **PASS:** flask **charges** increase by one each copy;
  **"Progressive Sacred Tear"** raises flask potency. Try `progressive_stonesword_keys: true` too.

**T3.6 — Start with Torch.**
```yaml
  start_with_torch: true   # default on
```
- **PASS:** you begin the game already holding a Torch (dark caves navigable before your first grace).
- Set `start_with_torch: false` → no Torch at start.

**T3.7 — Scaling floor.**
```yaml
  completion_scaling_floor: 30
```
- **PASS:** early regions are noticeably less trivial than floor 0 (enemies scaled up from the start).
  This is subtle — a feel check, not a hard pass/fail.

---

## Tier 4 — MULTIPLAYER / DLC

**T4.1 — Deathlink (needs 2 players).** `death_link: true` on both. **PASS:** one player's death kills
the other. (Confirm it respects the toggle: off = no propagation.)

**T4.2 — Local items (needs 2 players).** `local_item_only: true` + `item_shuffle: true`. **PASS:**
your shuffled ER items stay in YOUR world; other players' pools only see your Region Locks (+ Rune).

**T4.3 — DLC enable/only.**
- `enable_dlc: false` → no DLC region in play, base-game winnable.
- `dlc_only: true` → only Land of Shadow / Belurat / Scadu Altus / Shadow Keep / Jagged Peak /
  Abyssal Woods; goal collapses to DLC locks; still winnable (Land of Shadow carries all 6 Great Runes
  if you also set the great-runes goal).

---

## Known non-working / by-design (do NOT chase these)

- **Merchant-bell gating** (`merchant_bell_logic: logic_only`): no-op. Bell→shop mapping is engine C++,
  not in any param/EMEVD; needs a live flag-probe or a design call. Option ships inert.
- **Location-keyed sweeps** (`dungeonSweeps`) + **sweep lock gates** (`sweepLockGates`): empty by
  design — only flag-keyed sweeps (Tier 2) fire. The boss→reward-location join is a boundary (1/102).
- **~43 checks (1.1%)** give a Rune instead of a real item (item names not in the FMGs — quest notes,
  a source typo, non-item text). Expected.
- **Great Runes are "useful," not progression**, UNLESS `ending_condition: great_runes` requires them.

## When something fails

Grab the client log (the "flag-poll" lines + any warn/error), note the exact seed yaml + the in-game
action, and report. The gen side is proven green, so an in-game miss is almost always: the DLL doesn't
have the patch (rebuild), a flag mismatch (name the region/dungeon/shop), or a multiplayer-only feature
tested solo.
