# TEST PLAN — BRIEF-randomizer-bake-polish (#12 glow + #6 shop double-grant)

Status: **code changes applied**, not built/baked (this box is Linux; the randomizer is
`net6.0-windows` and the bake needs the game's regulation/params). Build + in-game verification
below is the Windows half you run.

## What changed

All changes are in `SoulsRandomizers/RandomizerCommon/`, contract-FREE (regulation/param output
only — no slot_data / apconfig / version-range touch).

**Task A — glow on AP-check pickups (#12)** — `PermutationWriter.cs`
- New constant `ApGlowRarity = 3` (ER legendary tier) near the `Diag()` helper (~L84).
- In `AddSyntheticCopy` (~L2341): every synthetic that carries an `archipelagoLocationId` (i.e. an
  AP check — world treasure, enemy drop, shop entry, foreign-world item, NPC gift) gets its
  `rarity` field set to legendary, so it shows the gold pickup aura / world light pillar and a
  legendary frame in shops & inventory. ER-gated, null-guarded.
- Lot-level belt-and-suspenders: `AddLot` gained a `bool apCheckGlow` param (~L2623); when set it
  forces `LotItemRarity` to legendary so the in-world pillar shows even on lots whose vanilla
  rarity was an explicit (non `-1`) value. The placement loop computes `isApCheckGlow` (~L594) and
  passes it at the world/enemy `AddLot` call (~L743).
- Kill switch: `AP_SYNTH_DIAG=noglow` disables **both** halves at runtime (no rebuild).

**Task B — own-world shop GOODS double-grant (#6)** — `ArchipelagoForm.cs` (~L494-512)
- Added one clause to the placeholder-branch condition: `|| (type == FromGame.ER &&
  targetScope.ShopIds.Count > 0)`. Own-world ER GOODS sold in **shops** now route through the
  placeholder token (`AddSyntheticItem`) like every other shop item → **single grant** (buy =
  placeholder, echo = real item).
- Surgical on purpose: crow GOODS (`ShopIds.Count == 0`) are left on the functional copy
  (`AddSyntheticCopy`) — they're not flag-polled the same way and are out of scope for #6. Non-GOOD
  shop items and foreign-player items are unaffected (already placeholder / junk token).
- Known tradeoff (per the brief): a lingering placeholder token remains until the client's
  `removeFromInventory` ships (`BRIEF-client-notify-cleanup.md` Task B). Strictly better than a
  double-grant today; the token auto-cleans once that lands.

## Build (Windows)

```powershell
.\build.ps1 -Randomizer      # dotnet build -c "Release (Archipelago)" --no-incremental
```
Expect a clean build. If the compiler flags anything, it'll be in the two edited files.

## Bake a test seed

Use a `location_pool: lean` yaml that places **own-world runes/goods in a shop** (for #6) and has a
spread of check kinds (world treasure, enemy drop, shop, gift) for #12.

```powershell
.\build.ps1 -Bake -Deploy     # AP server must be listening on localhost:38281 (or use -Serve)
```

After the bake, check the timestamped diag in `SoulsRandomizers/`:
- `ap_diag_<ts>.txt` → **"items with NO PARAM ROW" count must be 0** (no new entries vs the last
  known-good bake). Glow sets an existing field; it must not introduce NO-PARAM-ROW items.
- `ap_phantom_items_<ts>.txt` → no new phantom warnings.

## In-game checks

### Task A — glow (#12)  ← the one piece I could not verify from the param dump
1. Load the seed. At a few **world treasure** AP checks: the pickup shows the gold legendary aura /
   light pillar; nearby **non-check** world pickups do **not** glow.
2. Confirm the glow also appears on the other check kinds: **enemy drop**, **shop** entry
   (legendary name/frame in the shop list), **NPC gift**.
3. Cross-check the glowing spots against the location list in `apconfig.json` — glow set ⇔ AP check.
4. If the world **pillar** specifically doesn't show but the menu frame does, the item-`rarity`
   path works and the lot path needs the tier value adjusted — `ApGlowRarity` (PermutationWriter.cs
   ~L84) is the single knob; the `LotItemRarity` enum may use a different legendary value than the
   item `rarity` enum. If glow misbehaves entirely, bake with `AP_SYNTH_DIAG=noglow` to confirm it's
   isolated to this change.

### Task B — shop double-grant (#6)
1. Buy an **own-world good/rune** from a shop. It must arrive **exactly once** — watch the client's
   received-index log and the inventory count (was: +2, now: +1).
2. Regression guard (the brief's "Watch"): use a shop that sells an **own-world good AND a weapon**.
   Buying must not NPE / crash (the old `AddSyntheticCopy` Vagrant-field NPE that originally forced
   the functional-copy treatment). The placeholder path bases on a GOOD, so it should be safe —
   confirm.
3. Confirm **foreign-player** shop items and **non-GOOD** own items are unchanged (single grant /
   junk token as before).

## Rollback
- Glow only: bake with `AP_SYNTH_DIAG=noglow` (runtime, no rebuild).
- Either change: revert the edits in `PermutationWriter.cs` / `ArchipelagoForm.cs` (both are small,
  self-contained, commented with `BRIEF #12` / `BRIEF #6`).
