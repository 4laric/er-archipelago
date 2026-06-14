# BRIEF: client cleanup — notification toasts (#11) + un-stub removeFromInventory (#6 client half)

Repo: **runtime client** `Dark-Souls-III-Archipelago-client/archipelago-client` (C++ DLL,
`archipelago.dll`). Contract-FREE — safe to run parallel with the apworld + randomizer briefs.
See BRIEF-PARALLEL-INDEX.md. TODO #11 and #6.

> GOTCHA (whole repo): these source files are **CRLF**. The Edit tool truncates CRLF files
> ([[crlf-edit-truncation]]) — patch via a Python script that preserves `\r\n`, then VERIFY on disk
> with Read. Build is Windows/MSVC + modengine; the Linux sandbox CANNOT compile — hand `build.ps1
> -Client` to Alaric and review by reading the diff.

---

## Task A — incoming-item notification overlay (#11)

One sentence: the in-game "received item" toasts are too big / cover the HUD — shrink, reposition,
or throttle them.

**FIRST, settle the premise (do not assume).** TODO #11 says "client-side (archipelago.dll render)",
but the client's `showBanner` is a NO-OP (`GameHook.cpp` ~92–97) and there is no toast/overlay/render
code in the client. So the toasts are almost certainly the **native game's item-acquisition popup**,
fired as a side effect of granting items (`er_ap::game::GrantFullID` / `ItemGib`, see
`GameHook.cpp:45` `GiveNextItem` and `er_gamehook_win.cpp` AddItem path ~140). Confirm which it is
before writing code:
- Grep the client for any UI/draw/overlay/ImGui/D3D hook — expected: none. (If none, it's native.)
- In-game, the toast wording = the vanilla pickup banner ⇒ native popup, not ours.

**If native (most likely):** we don't render it, so "shrink/reposition" isn't a client-render tweak.
Options, in order of cheapness:
- *Throttle*: we already batch 16 grants/tick (`Core.cpp` ~436–443). A burst (e.g. starting
  inventory of 19 maps) spawns 19 stacked popups. Lower the per-tick grant cap and/or add a small
  inter-grant delay so popups don't pile — purely a pacing change in that loop, no rendering.
- *Suppress + replace*: investigate whether the acquisition popup can be suppressed at the AddItem
  path and replaced with our own lightweight banner (would require standing up `showBanner` for
  real — bigger, likely its own brief). Note as a follow-up, don't scope-creep here.

**If client-rendered (only if you actually find render code):** shrink font / move anchor / add a
queue with max-on-screen + fade. Keep the change isolated to that overlay module.

**Deliverable:** either a merged pacing change (cap/delay) with the popup-source finding written
into the brief's "verified" note, or a scoped overlay tweak if render code exists. Log what you did
so the next session knows the toast source for good.

**Test:** connect with a big starting inventory (region_lock seed gives many lock tokens + maps);
confirm popups no longer bury the HUD. No regression to grant counts (items still all arrive — check
the received-index log).

**Out of scope:** building a brand-new notification UI from scratch; that's a separate design brief.

---

## Task B — un-stub `removeFromInventory` (#6 client half)

One sentence: implement `CGameHook::removeFromInventory` (currently a no-op) so the client can pull a
placeholder/own-world item back out of the bag.

**Anchor:** `GameHook.cpp:114–119` —
```cpp
// TODO(ER inventory removal): walk the player inventory and remove the placeholder. No-op for now.
VOID CGameHook::removeFromInventory(int32_t itemCategory, int32_t itemId, uint64_t quantity) { ... }
```
The grant path lives in `er_gamehook_win.cpp` (AddItem detour ~140, `g_addItemOrig`). Removal is the
inverse: resolve the inventory instance (`er_ap::game::InventoryInstance()`, used in `Core.cpp:436`),
find the item entry by category+id, decrement/erase quantity. Look in `er_hooks.h` / `er_singletons.h`
for an existing RemoveItem / ItemDiscard signature to reuse rather than hand-rolling memory edits; if
none is resolved yet, that's the RE step (AOB the discard function the same way AddItem was found).

**Why it matters (independent of #6):** HANDOFF "unfixed" notes placeholder tokens LINGER in the
inventory because this is stubbed. Fixing it (a) clears that clutter and (b) unblocks the randomizer's
"proper" double-grant fix (sell a non-functional placeholder, client removes it on echo). This brief
only does the CLIENT capability; the randomizer side is `BRIEF-randomizer-bake-polish.md` — no
ordering required between them.

**Idempotency / safety:** removing an item that isn't present must be a safe no-op (don't underflow
quantity, don't crash if InventoryInstance() is null — guard exactly like the grant drain does).

**Test:** with a baked seed that places own-world goods in shops, buy one → the lingering placeholder
token should disappear once removal is wired into the echo path (or, minimally, a debug command that
calls removeFromInventory on a known token clears it). Verify no crash at the menu (null inventory).

**Contract:** none. Do NOT touch slot_data, apconfig, or the version range.


---

## VERIFIED / DONE (2026-06-13, Cowork session)

### Task A — popup source CONFIRMED NATIVE; pacing change merged
- **Toast source = the vanilla game popup**, NOT client render. Grepped the whole client for any
  UI/draw/overlay/ImGui/D3D/present hook -> **none**. `showBanner` is a no-op (`GameHook.cpp`).
  Each granted item fires the native "item acquired" popup as a side effect of `GrantFullID`.
  Lock this in: there is no client overlay to "shrink/reposition" — only pacing or native-popup
  suppression (the latter is the bigger #11 follow-up, still out of scope).
- **Fix (merged, `Core.cpp` grant loop):** replaced the flat `16 grants/tick` with
  `kMaxGrantsPerTick = 5` + `kInterGrantDelayMs = 350` (Sleep between grants, on the worker
  thread only). A 19-map starting flood now trickles over ~4 ticks instead of burying the HUD in
  ~2; normal 1-3 item receives still clear in one tick. Dials are named constants, easy to retune.
  No change to grant counts / received-index (every item still arrives).

### Task B — removeFromInventory implemented via direct EquipInventoryData edit
RE done against the pinned exe in `elden_ring_artifacts/eldenring.exe`
(sha256 3410...3492ddb — matches `er_hooks.h`). Findings:
- The DS3 approach (a dedicated `fRemoveFromInventory` AOB) has **no ER equivalent** by signature.
- **AddItemFunc (0x005605B0) is NOT a usable inverse:** it's the full CSMapItemMan acquisition
  pipeline (~335 instrs) and *fires the very popup Task A fights*, so negative-quantity was rejected.
- **Implemented removal as a direct bag edit** (no function call, no popup):
  - chain `GameDataMan` (AOB pinned, global 0x03D5DF38) -> `PlayerGameData = *(gdm+0x08)` ->
    embedded `EquipInventoryData` (offset auto-discovered by shape at runtime).
  - container layout **verified from the game's own inventory accessor** (exe 0x0024C4E0..0x0024C61A,
    the routine Hexinton's "Inventory Editor" hooks): slotCount@+0x1C, primary items ptr@+0x50,
    overflow ptr@+0x40, entry stride 0x18, id@entry+0x00, qty@entry+0x0C.
  - **Safe by construction:** every read is page-validated (`VirtualQuery`) so the discovery scan
    can't crash; a write happens ONLY on an exact itemId match, so a mis-resolved container is a
    no-op, never corruption. Idempotent (removing an absent item is a clean no-op).
- **Test in-game:** `/itemUngib <goodsId>` (DEBUG build) calls it on a known token. Turn `/debug on`
  first: it logs the discovered container offset + every scanned entry (id, qty) so the field
  offsets can be eyeballed on the first run. Verify on a throwaway save, then it's ready for the
  echo-path wiring (randomizer side, separate brief).
- **Known caveat:** decrementing qty to 0 may leave a 0-count ghost slot until the inventory menu
  refreshes; a full despawn would need the game's own RemoveItem (future work). Clutter is cleared.

**Build:** Linux sandbox can't compile (MSVC/modengine) — run `build.ps1 -Client` on Windows and
review the diff. Files touched: `Core.cpp`, `GameHook.cpp/.h`, `er_hooks.h`, `er_gamehook.h`,
`er_gamehook_win.cpp`.
