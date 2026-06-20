# SPEC: Task B — suppress the native acquisition popup + stand up the event banner

**One sentence:** stop the vanilla "item acquired" popup from firing on AP grants, and surface
received items (with sender, from [[er-notify-item-source]]) through ER's native bottom-center
EVENT-TEXT banner — the one driven by `DisplayGenericDialog` / FMG `EventTextForMap`.

Follow-up to `BRIEF-notify-boss-defer.md` Task B and the data half in `SPEC-notify-item-source.md`
(sender/itemName already reach `showBanner` as a string). This spec is the **render + suppress**
half. Memory: [[er-ap-notify-banner-size]], [[er-eventtextformap-failsafe]],
[[er-client-inventory-removal]], [[er-notify-item-source]].

> ## ⚠️ REVISED TARGET — live feedback 2026-06-14 (supersedes the banner direction below)
>
> Seeing it in-game changed the goal. On an AP grant THREE things appeared:
> 1. our bottom-center banner ("Archipelago: item received") — **blocking-ish, redundant**;
> 2. the native right-side **item-gain ticker** ("Golden Rune [4] x1") — non-blocking, no input,
>    already shows the item name;
> 3. the native full-screen **"NEW … Y:OK" acquisition modal** — blocking, needs a button press.
>
> **New goal: keep only #2 (the ticker). Remove #1 and #3.**
> - #1 (our banner): **DONE — reverted** (client trigger + bake event/FMG/flag all removed). The whole
>   custom-banner direction (Phases 1–2 below) is **abandoned**: the native ticker already is the good
>   on-screen notification, so dynamic FMG text is moot. The sender ("from bubbles") stays in the
>   client console line (already shipped).
> - #3 (full acquisition modal): **SOLVED 2026-06-14 via a safe param edit — no runtime hook, no CE
>   RE.** Breakthrough (Alaric): crafting materials (Rowa Fruit etc.) already pick up ticker-only.
>   Two independent per-item paramdef fields exist on every grantable item type
>   (`EquipParamGoods/Weapon/Protector/Accessory/Gem`): `showLogCondType` (acquisition **log** = the
>   ticker; default 1 = on → LEAVE ON) and `showDialogCondType` (acquisition **dialog** = the
>   "NEW Y:OK" modal; enum `GET_DIALOG_CONDITION_TYPE`, default 2 = "new only" → set to **0 = None**).
>   The bake now sets `showDialogCondType = 0` on all rows of those 5 param types (MiscSetup.cs
>   `EldenCommonPass`); editing only the 2-bit dialog field leaves the ticker field untouched, so
>   every pickup becomes ticker-only and the modal never fires. Gen-testable, reversible, zero
>   client/runtime change, zero crash risk. This **retires** the additive-bag-edit / menu-hook routes
>   and the CE hunt. Game-wide by nature (modal is keyed on the item param, not the acquisition
>   source). **Gen-test check:** Rowa Fruit's `showDialogCondType` should read 0; a fresh AP-granted
>   item shows ticker only.
>
> **Status:** modal suppression **CONFIRMED WORKING IN-GAME 2026-06-14** (incoming AP items show in
> the native ticker, no modal). Phase 1 banner
> REVERTED. Phase 0 singleton resolve-and-log IMPLEMENTED (read-only; `CSItemGetMenuMan` no longer
> needed by the chosen fix but harmless). The `AddItemFunc`/async finding stands as history.
>
> ---
> _(Original banner spec retained below for history; the banner direction is superseded.)_

---

## Mechanism (confirmed by RE)

**The banner** Alaric likes is the centered event-text dialog. The randomizer drives it via EMEVD
instruction **`2007[01]` = `DisplayGenericDialog(messageId, promptType, numButtons, ?, seconds)`**
(`MiscSetup.cs:1158`, `RuntimeParamChecker.EditEvents`), with the text pulled from FMG
**`Menu / EventTextForMap`** by **message id**. The randomizer reserves two ids
(`RuntimeParamChecker.cs`): `RestartMessageId = 666400`, `FogMessageId = 666401`. So the banner shows
a **pre-existing FMG string addressed by id** — it does NOT take a raw string.

**The native popup** ("Golden Rune [10]" sliding in on pickup) is the **item-get log / system
announce**, owned by **`CSItemGetMenuMan`** (params `itemGetLogAliveTime`,
`systemAnnounceScrollSpeed`, …). It fires as a side effect of the full acquisition pipeline
`AddItemFunc` (`0x005605B0`) — which is exactly why `removeFromInventory` was done as a direct bag
edit ([[er-client-inventory-removal]]).

**Two consequences that shape the whole design:**
1. Showing the banner needs a *message id*, so dynamic text ("… from bubbles") requires editing an
   FMG entry **at runtime** (via `MsgRepository`) — the single hard RE item here.
2. The popup and the banner are **different systems** (`CSItemGetMenuMan` vs `DisplayGenericDialog`),
   so suppression and banner are independent and can ship separately.

## Singletons (resolved for 2.6.2.0)

Slot RVAs derived from the Hexinton v6.0 table's `UserdefinedSymbols` (absolute addrs), converting
with image base `0x7FF60E390000` — cross-checked against two values the client already pins
(`CSEventFlagMan` 0x03D68448, `SoloParamRepository`/ParamBase 0x03D81EE8). **Confirm at runtime via
the name-anchored FD4 resolver in `er_singletons.h`** (find class-name string in .rdata → the single
LEA that references it → slot mov 0x11 bytes before) rather than trusting the static RVA blind.

| Singleton | Slot RVA | Source | Role |
|---|---|---|---|
| `CSItemGetMenuMan` | `0x03D6C3D8` | name-anchored (ground truth) | native item-acquired popup — Phase 3 suppression target |
| `CSMenuMan` | `0x03D6B800` | name-anchored (ground truth) | menu manager (e.g. `+0x13C` save-disable flag) |
| `MsgRepository` | `~0x03D7D4F8` **UNCONFIRMED** | CE-derived only | FMG text store (Phase 2) — **not** name-anchorable; needs a dedicated AOB |

**Phase 0 finding (2026-06-14):** the client's FD4 name-anchored resolver (`er_gamehook_win.cpp`,
logs at `Init`) resolves `CSItemGetMenuMan`/`CSMenuMan` cleanly and **corrected** the earlier
CE-table-derived guesses (which were 0x28–0x50 off — the CE absolute symbols point at something other
than the FD4 BSS slot). `MsgRepository` has no uniform accessor (its name string is referenced from
many non-accessor sites), so its slot stays unconfirmed and Phase 2 must AOB its accessor directly.

## Sub-problem 1 — drive the banner

### Approach A (RECOMMENDED for Phase 1 — zero blind native calls): EMEVD-flag trigger

The client already sets event flags reliably (`SetEventFlag`, shipped & used for map reveal / grace
flags). So **let the bake own the `DisplayGenericDialog` call** and have the client just set a flag:

- **Bake (randomizer):** add a `common` EMEVD event: `IfEventFlag(AP_BANNER_FLAG) → DisplayGenericDialog(reservedMsgId, …) → reset AP_BANNER_FLAG → restart`. This is the exact pattern
  `RuntimeParamChecker.EditEvents` already uses for the fog/restart banners — copy it. Reserve a new
  message id (e.g. `666402`) + a dedicated event flag.
- **Client:** `showBanner()` → `er_ap::game::SetEventFlag(AP_BANNER_FLAG, true)`. Done. No native
  dialog call, no signature guessing, no crash surface beyond `SetEventFlag` (already proven).

Phase-1 text is the reserved id's **fixed** FMG string (e.g. "Archipelago: item received — see
log"). The per-item detail ("Golden Rune [10] from bubbles") stays in the already-shipped console
line until Phase 2 lands dynamic text. This is a real, demonstrable, low-risk banner.

### Approach B (pure client, needed only for per-grant timing precision): call DisplayGenericDialog

Resolve and call the native `DisplayGenericDialog` (EMEVD `2007[01]` handler) directly with a message
id. **Open RE item — NOT yet located:** its address/signature isn't in the CE table and can't be
pinned from EMEVD statically without the dispatch map; needs a live RE pass (breakpoint the handler
when a fog banner fires, or trace `2007/01` through the EMEVD interpreter). Lower priority than A —
A already gets per-grant timing because the client controls when it sets the flag.

### Dynamic text (Phase 2, the one hard RE item): runtime FMG edit via MsgRepository

To show the actual item+sender, overwrite the reserved id's FMG entry just before triggering:
- `MsgRepository` exposes a `GetMessage(fmgGroup, msgId) -> const wchar_t*`. **Open RE item:** find
  the lookup method offset/signature (live: breakpoint reads of `EventTextForMap` when a fog banner
  shows). The returned pointer is into the FMG blob.
- Overwriting **in place is bounded by the existing string's allocation** — risky (longer text
  overruns). Safer: have the bake seed the reserved id with a long padding string (N spaces) so there
  is guaranteed headroom, then the client writes ≤N wchars + NUL. Page-validate every write
  (`SafeRead`/equivalent), and **never** write if the entry can't be confirmed by re-reading it.
- Build the wide string from the same `"X from Y"` the data half already produces (UTF-8 → UTF-16).

## Sub-problem 2 — suppress the native popup

The popup must stop for **our** grants without killing **legit** native pickups (vanilla world items
the player picks up).

- **Option 1 (RECOMMENDED — consistent with what shipped): additive direct bag edit.** Grant by
  writing into `EquipInventoryData` directly (the additive mirror of `removeFromInventory`,
  [[er-client-inventory-removal]]) instead of calling `AddItemFunc`. Bypasses the entire acquisition
  pipeline → no popup, inherently scoped to our grants only. **Risk:** must replicate ER's
  stack/overflow rules (match existing stack vs new slot; goods vs weapon/armor partitions; 9999
  cap). Build on the already-RE'd container layout; page-validate; write only on a confirmed slot.
  Verify counts in-game before trusting.
- **Option 2: flag-gate the popup enqueue.** Keep granting via `AddItemFunc`, but hook the
  `CSItemGetMenuMan` enqueue call and early-return while a global `g_apGrantInProgress` is set (set it
  around the grant, clear after). **Risk:** must find the exact enqueue sub-call inside the pipeline
  and not suppress concurrent legit pickups (race if the player grabs a world item mid-grant). More
  surgical but more RE.

Recommend **Option 1** (no popup by construction, no risk to legit pickups), accepting the
additive-grant RE cost; fall back to Option 2 if additive stacking proves too fiddly.

## Why a spec, not blind code (the Task A vs Task B asymmetry)

Task A shipped as code because its worst failure — a wrong PlayRegion read — is **bounded by the
starvation cap into a graceful delay**. Every Task B path's worst failure is **un-graceful**: calling
a misidentified `DisplayGenericDialog` with a guessed signature, overwriting FMG string memory with a
wrong layout, or a bad additive bag write → **crash or save corruption**. With no ability to run the
game here and the one required function (`DisplayGenericDialog`) not exposed by any reference, blind
implementation would be net-negative. The safe increments are: the bake-side EMEVD event (testable in
gen), `SetEventFlag`-driven trigger (already proven), and singleton resolve-and-log scaffolding.

## Phased rollout (each independently shippable + verifiable)

- **Phase 0 (safe, client) — DONE 2026-06-14:** name-anchored FD4 resolver in `er_gamehook_win.cpp`
  resolves + logs `CSItemGetMenuMan` (0x03D6C3D8) / `CSMenuMan` (0x03D6B800) at `Init`; corrected the
  CE guesses and confirmed `MsgRepository` isn't uniform-resolvable. Read-only, zero behavior change.
- **Phase 1 (low risk): fixed-text banner via Approach A.** Bake the AP_BANNER_FLAG → `DisplayGenericDialog(666402)` event; `showBanner()` sets the flag. Reuses shipped `SetEventFlag`.
  Test in gen + in-game: receive items → fixed banner appears, paced/boss-deferred via the existing
  drain. Verify it doesn't clobber the fog/restart banners (distinct id + flag).
- **Phase 2 (medium): dynamic text.** RE `MsgRepository.GetMessage`; overwrite the padded reserved
  entry per grant with `"X from Y"`; re-read to confirm before triggering.
- **Phase 3 (higher): popup suppression** via Option 1 (additive bag grant). Verify item counts,
  stacks, overflow (keys/quest), and that picking up a vanilla world item still shows its real popup.

## Live-RE shopping list (what a session with the running game must capture)

1. `DisplayGenericDialog` address + signature (only if doing Approach B).
2. `MsgRepository` instance + the `GetMessage(group,msgId)->wchar_t*` method offset; the FMG group id
   for `Menu/EventTextForMap`; the in-memory entry layout (ptr + capacity) for the safe overwrite.
3. `CSItemGetMenuMan` enqueue method (only if doing suppression Option 2).
4. Confirm the Phase-0 slot RVAs (`0x3D7D4F8` / `0x3D6C3B0`) resolve and are non-null in-world.

## Files (when implemented)

- `er_singletons.h` / `er_gamehook_win.cpp` — add `MsgRepository` + `CSItemGetMenuMan` resolution
  (name-anchored) and the FMG read/write + additive-grant helpers.
- `er_hooks.h` — reserved ids/flags (`AP_BANNER_FLAG`, `AP_BANNER_MSG_ID = 666402`), MsgRepository offsets.
- `GameHook.cpp` — `showBanner` → SetEventFlag trigger (Phase 1) + FMG text set (Phase 2); switch
  grant path to additive bag edit (Phase 3).
- Randomizer (`RuntimeParamChecker.cs` / `MiscSetup.cs`) — bake the AP_BANNER event + reserve the
  padded FMG entry. **This couples Task B to a randomizer bake change**, like the fog banners already do.
