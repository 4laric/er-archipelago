# Moore / Enia shop fix — build & verify runbook

## What changed
`SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs` → `FindMatchingSlotKey`.

**Root cause:** not a structural scope collapse. The scrape already carries every shop row
as a distinct candidate. `FindMatchingSlotKey` disambiguates them by
`game.BaseName(candidate.Item) == ItemNameForLocation(apLocation)`, but AP location names
embed a stack-quantity suffix (`"GP/MGC: Rune Arc x3 - Moore Shop"` → `"Rune Arc x3"`) that
`BaseName` lacks (`"Rune Arc"`). Equality fails for every stacked shop item, so it falls
through to `candidates.First()` and all rows of the shop bind to one slot + one event flag
(apconfig: `320500→13`, `320700→12`, Enia `290270→21`). Kalé/nomads mostly sell quantity-1
items, so they matched and looked fine.

**Fix:** strip a trailing `" xN"` on both sides before comparing (`StackQtyRe` + `normName`),
and enrich the ambiguous-location warning to log the wanted name + candidate base names + count.
Applied by `patch_moore_shop_namematch.py` (idempotent, CRLF/BOM-safe).

No changes to `itemslots.txt`, `locations.py`, scopes, or the client DLL.

## Build (Windows)
```powershell
cd C:\Users\alari\Documents\er-archipelago
.\build.ps1 -Randomizer            # rebuilds RandomizerCommon (clean). Client DLL untouched.
```
Then a full pipeline reusing the existing client + a normal (non-dlc_only) seed:
```powershell
.\build.ps1 -All -NoClient
```
(Kill any stale server on :38281 first if the bake hangs.)

## Verify
1. **Collapse check** — run against the freshly baked apconfig:
   ```powershell
   python .\check_shop_collapse.py .\apconfig.json
   ```
   PASS = Moore grocery, Moore poison, **and Kalé/nomads** all read `ok (distinct rows)`,
   no `COLLAPSED`. (On a full seed Kalé is present, so it should say `ok`, not `ABSENT`.)
   Also confirm `320500` / `320700` / `290270` are no longer in the "top reused flags" list.

2. **Warning sweep** — in the randomizer console output / bake log:
   ```powershell
   Select-String -Path .\generate_*.log,.\*bake*.log -Pattern "ambiguous location"
   ```
   Expect ~none for shop items. Any hit now prints `want '<name>' among ['<cand>', ...] (n=<count>)`
   — that tells us exactly which item still mismatches and what its candidates were.

3. **In-game** — Moore's shop shows `[Placeholder]`/foreign items across the stock (not vanilla),
   and buying each item reports its own check once (no 13-at-once misfire).

## If a quantity-1 row STILL collapses (residual)
The enriched warning fires only when `candidates.Count > 1`. If a non-stacked row still shows
vanilla AND no warning fired for it, the candidate list was reduced to 1 by the base-filter in
`data.Location(targetScope)`. Fix = switch the placement call (~L473) from
`data.Location(targetScope)` to `data.Locations[targetScope]` (the full member list, same source
the `itemsToRemove` call already uses), rebuild `-Randomizer`, rebake. Send me the `(n=…)` line and
I'll confirm before you touch it.
