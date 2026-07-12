# SPEC — Suppress the Erdtree burn until there is Ashen Capital logic

**Status:** SPEC. Not started.
**Date:** 2026-07-11
**Reported by:** Alaric, playtest — *"when you kill Maliketh it sets ashen capital and warps you there,
we probably suppress that until we have ashen capital logic"*
**Shipped stopgap:** `ERDTREE_BURN_APS` — the 79 destroyed checks may not carry progression. That kills
the softlock. It does **not** stop the player losing 79 checks.

---

## 1. What actually happens

`common.emevd` `$Event(900)` — 天変地異_世界樹炎上, *"Natural disaster: World tree in flames"*:

```js
$Event(900, Default, function() {
    EndIf(!PlayerIsInOwnWorld());
    GotoIf(L0, !EventFlag(9116));       // 9116 = Maliketh dead (m13_00 sets it on his defeat)
    GotoIf(L1, !EventFlag(118));        // 118 = transition already done
    EndEvent();
L0:
    WaitFor(PlayerIsInOwnWorld() && EventFlag(9116));
    SetSpEffect(10000, 4280); SetSpEffect(10000, 4282);
    SetPlayerRespawnPoint(13002020);
    SaveRequest();
    WaitFixedTimeSeconds(5.2);
L1:
    EndIf(CharacterDead(10000));
    DisableCharacterDefaultBackread(13000800);
    SetEventFlagID(300, ON);                    // ← the Erdtree BURNS
    SetEventFlagID(301, ON);
    SetEventFlagID(302, OFF);
    SetEventFlagID(71300, ON);                  // Maliketh's grace
    BatchSetEventFlags(71100, 71110, OFF);      // ← Leyndell's graces SWITCHED OFF
    DisableTextOnLoadingScreen();
    PlayCutsceneToPlayerAndWarp(13000050, Skippable, 11052010, 11050000, 10000, 13000, true);
    SetPlayerRespawnPoint(11052010);            // ← respawn moved into m11_05
    SetEventFlagID(118, ON);                    // done-latch
});
```

So killing Maliketh **permanently**: burns the Erdtree, turns **Leyndell's graces (71100–71110) OFF**,
warps you into **m11_05 (Leyndell, Ashen Capital)**, and moves your respawn there. Normal Leyndell
(`m11_00`) ceases to exist, and its **79 checks become unreachable**.

Vanilla hides this because you always clear Leyndell before you can reach Maliketh. **`num_regions` does
not**: it can unseal Farum Azula while Leyndell is still sealed, so the player is free to burn the
Erdtree with 79 Leyndell checks uncollected.

Same class as the Radahn festival: **the GAME puts a check permanently out of reach while AP still
believes it is available.**

---

## 2. ⚠️ You cannot pre-empt Event 900. Do not try.

The obvious move — hold `9116` OFF, or pre-set the `118` done-latch — **does not work**, and it is worth
writing down so nobody burns an afternoon on it:

* `L0` does `WaitFor(EventFlag(9116))`. That fires in the **same frame** Maliketh's own defeat handler
  (`m13_00`, line 409) sets 9116. A flag poll cannot reliably win that race.
* After the `WaitFor` passes, control **falls through into `L1` unconditionally**. Clearing 9116 during
  the 5.2 s window changes nothing — the check already happened.
* `118` is only tested at **event init** (the "catch-up on load" path). On the `L0` path it is never
  re-checked, so pre-setting it does not gate the transition.

**Therefore suppression must be an UNDO, applied after the fact.**

---

## 3. The design: undo the burn

The client already polls flags and can warp (`warp::warp_to_grace`, used by the region-lock KICK). On
seeing the done-latch `118` (or `300`) go ON while suppression is enabled:

1. **Clear** `300`, `301`, `118` — the Erdtree-burn state. The `m11_00` / `m11_05` map variant is
   selected from these, so clearing them restores normal Leyndell on the next load.
2. **Set** `302` back ON (the transition turned it OFF).
3. **Restore** graces `71100`–`71110` (the batch turned them OFF) — otherwise the player has silently
   lost every Leyndell warp point, which is the region-grace-loss bug in a different hat.
4. **Warp the player out of `m11_05`** — they are standing in a map that should no longer exist. Warp
   to a Farum Azula grace (`13002020`, which the event itself had just set as the respawn point) or to
   the hub.
5. **Reset the respawn point** away from `11052010`.

Leave `71300` (Maliketh's grace) alone — it is an arena grace and already in the skip list.

**Cost:** the cutscene still plays and the player briefly sees the Ashen Capital before being pulled
back. Ugly, but recoverable, and it costs 7 `m11_05` checks instead of 79 `m11_00` ones.

**Gate it behind an option** (`suppress_erdtree_burn`, default ON) so it can be turned off the moment
real Ashen Capital logic exists.

---

## 4. The real fix (later)

Model the Ashen Capital as a **world state**, not an accident:

* `m11_05` becomes its own region (7 checks) reachable only after the burn.
* `m11_00`'s 79 checks become **missable-on-burn**, which is what they actually are.
* The burn becomes a deliberate, logic-visible transition — possibly even an AP item/goal step.

At that point `ERDTREE_BURN_APS` and this suppression both retire, and `_ARENA_GRACE_FLAGS`'s
`71300` entry can be re-examined.

---

## 5. Definition of done

1. Option `suppress_erdtree_burn` (default ON) → slot_data.
2. Client `erdtree_burn.rs`: watch `118`; on rising edge, do §3 (1)–(5).
3. In-game: kill Maliketh with Leyndell sealed → confirm you end up back in Farum Azula, Leyndell's
   graces still lit, `m11_00` still loadable, its checks still collectable.
4. Confirm the burn does not re-fire on reload (the undo must be idempotent — 9116 stays ON, so
   Event 900's init path will see `9116 && !118` and try again; **the undo must therefore re-run, or
   118 must be left ON while 300/301 are cleared**. Decide which, and test a save/reload.)

> ⚠️ (4) is the sharp edge of this spec. `9116` cannot be cleared (Maliketh really is dead), so on every
> map load Event 900 re-evaluates `GotoIf(L1, !EventFlag(118))`. If the undo clears 118, the transition
> **fires again on the next load**. So the undo must most likely *keep* `118` ON (the game thinks it has
> transitioned) while clearing `300`/`301`/restoring graces — i.e. lie to the latch, not to the state.
> Verify which flag actually selects the `m11_00` / `m11_05` variant before implementing.
