# BRIEF: SERIALIZED contract change — reveal-all-maps under map_option=give (#5 optional polish)

⚠️ **RUN THIS ALONE.** It changes the slot_data contract and therefore touches **all three repos**
plus the beta.N version range. Do NOT run it concurrently with any other contract-touching work.
The four coding briefs in BRIEF-PARALLEL-INDEX.md are contract-free and can run alongside each other,
but a contract bump must be the only contract change in flight. TODO #5 (OPTIONAL POLISH section).

This is **optional polish**, not a bug — the map-check LEAK is already fixed apworld-side
(`_is_location_available` returns False for `map=True` locations under `map_option: give`). This brief
only removes the map FRAGMENT items from inventory clutter: under `give`, reveal the maps without
granting the fragment items at all.

## What you're building
Under `map_option: give`: stop precollecting the map fragment items; instead emit a `reveal_all_maps`
signal in slot_data, and have the client set the reveal flags directly on connect (no item grant).
Net result: all regions revealed, zero map fragment items in the bag.

## The three coordinated changes (all land together, one beta.N bump)

1. **apworld** (`Archipelago/worlds/eldenring`):
   - Under `map_option == give` (value 1), stop precollecting the map items (the current path
     precollects + reveals; drop the precollect for the give case only).
   - Add `reveal_all_maps` (bool, true only when give) to the slot_data dict in `fill_slot_data`
     (`__init__.py` ~2755+, next to `regionGraces`/`dungeonSweeps`). Keep it absent/false otherwise.
   - REGENERATE to take effect.

2. **client** (`Dark-Souls-III-Archipelago-client/archipelago-client`, C++, **CRLF — patch via
   Python**, [[crlf-edit-truncation]]):
   - Parse `reveal_all_maps` in the slot_connected handler (`ArchipelagoInterface.cpp`, alongside the
     `regionGraces` / `dungeonSweeps` parse blocks ~85–110).
   - On connect, if set, set every reveal flag directly — **reuse `kMapUnlockFlags`** in
     `GameHook.cpp` (~27–41; the base + DLC 62080–62084 table) by calling
     `er_ap::game::SetEventFlag(flag, true)` for each value. Mirror the grace-flush pattern
     (`CCore::FlushPendingGraceFlags`, `Core.cpp` ~734): queue on connect, set on a loaded tick
     (event-flag setter is invalid before the world loads). Idempotent + save-persisted, so reconnect
     re-apply is harmless.
   - Bump the client's implemented contract version to the new beta.N (it checks at connect).

3. **randomizer** (`SoulsRandomizers`, C#): bump the contract version range it enforces at bake to the
   new beta.N. Confirm no bake step depends on the map items being in the pool under give (the give
   path already drops them as checks; this drops them as items too).

## Version lockstep (the whole point of "serialize")
Per HANDOFF: every contract change bumps `>=0.1.0-beta.2 <0.1.0-beta.3` across apworld + randomizer +
client AT ONCE. Choose the next value (beta.3 ⇒ range `>=0.1.0-beta.3 <0.1.0-beta.4`) and apply it in
all three. A mismatch = connect refusal. This is exactly why this brief can't run next to another
contract change.

## Test plan
1. Bake + deploy a `map_option: give` seed on the new contract version.
2. Connect: client log shows `reveal_all_maps` parsed; reveal flags SET on the loaded tick; NO map
   fragment items appear in the Key Items tab; the world map is fully revealed.
3. Bake a `map_option` ≠ give seed: `reveal_all_maps` absent/false, maps behave as before (fragments
   granted + revealed normally). No regression.
4. Reconnect mid-run: maps stay revealed, no errors, no duplicate grants.

## Out of scope
The `map_option != give` behavior; the already-fixed check leak; any non-map contract key.

---

## VERIFIED / DONE (2026-06-14, Cowork session)

Implemented solo (no other contract change in flight), contract bumped **beta.2 → beta.3**.

**apworld** (`worlds/eldenring/__init__.py`, CRLF-safe Python patch):
- Removed the map-fragment **precollect** under `map_option=give` (the old `using_table` loop). Safe
  for pool balance: under give, map-pillar locations are already excluded as checks
  (`_is_location_available`), so map items were never in the pool — they only entered via that
  precollect. Now nothing grants them.
- `fill_slot_data` emits **`"reveal_all_maps": self.options.map_option.value == 1`** (real JSON bool,
  next to `regionGraces`). True only for give.
- `"versions"` → **`">=0.1.0-beta.3 <0.1.0-beta.4"`**. `py_compile` clean.

**client** (CRLF via Python; `GameHook.*` are LF via Edit):
- `ArchipelagoInterface.cpp`: parse `reveal_all_maps` → `Core->revealAllMapsPending` (one-shot, re-armed
  each connect). Also wired an **advisory version check**: `ER_CLIENT_CONTRACT_VERSION="0.1.0-beta.3"`
  checked against `slot_data["versions"]` via the existing (previously unused) `er_version_check.h`;
  **warns + banners on mismatch, does not refuse** (hardening to a refusal is a follow-up once the
  client build is tested).
- `GameHook.cpp/.h`: `CGameHook::revealAllMaps(includeDlc)` sets every `kMapUnlockFlags` reveal flag,
  skipping DLC maps (base id ≥ 2000000) unless DLC; returns false if the flag holder isn't ready so
  the caller retries. Mirrors the grace-flush robustness.
- `Core.cpp/.h`: loaded block drains `revealAllMapsPending` via `revealAllMaps(dEnableDLC)` until it
  succeeds. Idempotent + save-persisted, so reconnect re-apply is harmless.

**LOCKSTEP REALITY (important):** enforcement is only half-wired today, so the bump is mostly a record.
- The **randomizer**'s `ArchipelagoForm.CheckVersionRange` short-circuits in dev (`Version == null`)
  and otherwise compares a DS3-era `3.0.x` number (never satisfies a `0.1.0-beta.N` range) — so it's
  inert for dev bakes regardless of beta.2 vs beta.3. NOT modified here (touching it risks the bake);
  reconciling it to the ER beta numbering is a separate cleanup.
- The **client** check is the new advisory warn above; it did not previously check at all.
- So the apworld's emitted `versions` is the de-facto source of truth; the new client warn makes a
  mismatch visible going forward.

**Build/test (Windows):** `build.ps1 -Client` (can't compile in the Linux sandbox), bake a
`map_option: give` seed, then run the test plan above. Watch for `reveal_all_maps: map N reveal flag
… SET` and an empty Key Items map section.
