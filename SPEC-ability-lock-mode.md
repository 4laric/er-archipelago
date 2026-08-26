# SPEC — ability lock mode

**Status:** probes ANSWERED, 2026-08-21 (findings inline in §4.2, from three sessions / 4,389
basket samples in Alaric's v0.4.11 acceptance logs). Enforcement is unblocked except for one
field test: apply SpEffect 9621 outside a sanctuary zone and record what it disables.
**Owner:** Alaric rules. This document is a proposal with its prerequisites stated, not a plan of
record.

---

## 1. What the mode is

Alaric, 2026-08-20: *"unlock items in the multiworld for like, heal, dodge roll, jump, crouch, r1,
r2, l1, l2."*

Eight player abilities start **locked** and each has an AP item in the pool that unlocks it:

| ability | proposed AP item name | what locking means |
|---|---|---|
| dodge roll | `Dodge Roll` | the roll/backstep button does nothing |
| jump | `Jump` | the jump button does nothing |
| crouch | `Crouch` | the crouch button does nothing |
| heal | `Heal` | flasks hold **0 charges** |
| R1 | `Light Attack` | no right-armament light attack |
| R2 | `Heavy Attack` | no right-armament heavy attack |
| L1 | `Guard` | no left-armament guard/attack |
| L2 | `Weapon Skill` | no weapon skill |

Movement (walking, sprinting, Torrent) and item use (Square/X — consumables, throwing pots) are
**never** locked; they are what makes a fully-locked start survivable rather than a softlock.

Two couplings the names must not paper over:

- **Casting rides the attack buttons.** A seal or staff casts through R1/L1, so locking all four
  attack buttons also locks sorceries and incantations. That is correct for the mode, but the
  item descriptions should say so.
- **Fists are an R1/R2.** "The player always has unarmed" is why the four attack locks only bite
  as a set; any one of them unlocked restores a melee damage source.

## 2. Option and item model (world side)

One new feature module, `greenfield/eldenring/features/ability_locks.py`, on the standard
registry pattern (`features/README.md`):

- **OPTIONS — eight Toggles**, `ability_lock_dodge_roll`, `ability_lock_jump`,
  `ability_lock_crouch`, `ability_lock_heal`, `ability_lock_light_attack`,
  `ability_lock_heavy_attack`, `ability_lock_guard`, `ability_lock_weapon_skill`, all default off.
  Per-ability toggles over a bundled Choice (`off | movement | combat | all`) because a bundle
  cannot express "roll only", which is the obvious first playtest configuration. (Open question
  §9.1 — a bundle Choice is the fallback if eight options is judged too much yaml surface.)
- **ITEMS — eight synthetic names, no `ITEM_GRANTS`.** Exactly the trap/region-Lock shape: the
  item has no game FullID; the client acts on the **name** at receipt. `ItemClassification` is
  `progression` for all eight — see §3 for why the non-combat four are not merely `useful`.
- **Pool entry is count-neutral.** `create_items` returns one copy per enabled toggle; core sizes
  the filler tail off `len(pool)`, so each unlock displaces one filler (the `boss_locks.py` mode-B
  precedent). All toggles off ⇒ empty list ⇒ the seed is byte-identical to HEAD.
- **Contract: one new key.** `abilityLockFlags = {item_name: flag_id}` — the `regionOpenFlags`
  shape, one synthetic event flag per ability. The client's existing receipt path
  (`region.rs`: `flags::set_event_flag(open_flag, true)` on lock receipt) generalises to it, and
  `flags.rs`'s `virtual_memory_flag` accepts arbitrary ids and is **save-persisted and
  replay-idempotent**, so reconnect/save-load needs no ledger — the same free lunch region locks
  already eat.
- **Flag ids:** reserve a contiguous synthetic block (proposal: `76990..76997`), next to the
  region-lock synthetics (`76980`/`76981`) and declared in **one** place — the feature module —
  with a unit test pinning the eight values. `region_open_flags.py` is *generated*, so the test is
  what stops a future region from claiming a neighbour id.

## 3. Logic model

The question that decides whether the mode can generate an unwinnable seed: **what can a player
with everything locked still do?** Walk, sprint, ride Torrent, talk, warp, level up, buy, and —
critically — **use consumables and spirit ashes**. So the game is never formally uncompletable,
but AP logic must model *guaranteed* capability, and finite consumables plus a Spirit Calling
Bell the player may not own yet are not a guarantee.

- **Damage rule (the load-bearing one).** If all four attack toggles are on, every boss-kill
  check, every Great Rune, and the goal require `has_any(Light Attack, Heavy Attack, Guard,
  Weapon Skill)`. Conservative on purpose: it assumes nothing about ashes or consumables. If
  Alaric rules that ash/bell access is guaranteed enough to count (§9.3), the rule relaxes to
  nothing — the items stay `progression` either way, so relaxing is a logic edit, not a re-pool.
  If fewer than four attacks are locked, no rule is needed: an unlocked attack button is a damage
  source at start (fists).
- **SHIPPED (#1035, Alaric 2026-08-25): the conservative half of the damage rule.** The
  reachability rule above is still open; what ships is the `early_items` mitigation. When all four
  attack inputs are locked and the mode is progressive, `create_items` declares `Unlock: R1` to
  AP's `early_items` (exportable, the Roll seam from #980), so a weapon attack is guaranteed early
  wherever in the multiworld it lands, without touching the reachability graph. **Spells do not
  count and get no carve-out** — Alaric: *"spells don't count, you need an L or R button to cast a
  spell"* (a staff or seal casts on an attack button, so a caster with all four locked is exactly
  as weaponless). §9.3's open question is therefore answered for spells; ashes/consumables remain
  open, and #1035 stays open for whether the full logic rule is still wanted on top.
- **Roll, crouch, heal: no logic rules.** They make the game harder, not incompletable — the same
  standing precedent as `no_equip_load`/`no_fall_damage`, which are difficulty options with zero
  logic footprint. Their items are still `progression` (not `useful`) so fill treats them as
  things the player wants early rather than trash: with roll locked, "where is my Dodge Roll" is
  the seed's central question and fill should answer it honestly.
- **Jump: needs an audit before the mode ships, and that audit is phase-0 world work.** Torrent
  covers open-world verticality and is never locked, so the exposure is *indoor* jump-gated
  checks. If the audit finds any, those locations get `has(Jump)`; if it finds none, the spec
  says so with the list it checked. What we must not do is ship "jump probably gates nothing" —
  an out-of-logic jump-gated check holding progression is exactly a softlock the generator cannot
  see. (Prior art for the audit shape: the sweep-scoping oracles in `tools/`.)
- **Item use stays unlocked** (it is the safety valve), so `Flask of Wondrous Physick` — an
  item-use, not a flask-charge consumer — still works under `Heal` lock unless Alaric rules
  otherwise (§9.4).

## 4. Client enforcement (the hard half)

### 4.1 What is already free

Receipt → flag → per-frame gate is the region-lock architecture end to end, and the client owns
every piece of it. **Heal is tier 1**: `flask.rs` already reconciles `max_hp_flask`/`max_fp_flask`
every tick (`GameDataMan+0x8 -> +0x101/+0x102`, proven cleanly writable, not recomputed by the
game). A heal lock is a clamp of the reconcile target to **0** while the flag is down; grace
refills fill to max, and max is 0. It should live *in* `flask.rs` — a second writer to the same
two fields is how reconcile fights start.

### 4.2 🛑 The menu-context problem — the blocker for everything input-masked

The other seven abilities have no field to clamp; their mechanism is **per-button input
masking**, and the infra for it exists: `input.rs` hooks `XInputGetState`, DirectInput
`GetDeviceState`, and `GetKeyboardState`/`GetKeyState` — version-independent Windows APIs, not
RVAs — and already zeroes state by device class. Masking buttons instead of devices is a small
change to data it already touches.

The problem is that **ER reuses the same buttons in menus**: Circle/B is dodge *and* "back",
RB/LB are R1/L1 *and* menu tab-switchers. Blind masking locks the player out of their own
inventory. So every input-masked ability gates on a **menu-open predicate the client does not
yet have**. (The overlay's imgui `want_capture` gate is not it — that covers *our* UI, not the
game's.)

**Probe 1 — menu context. ✅ ANSWERED 2026-08-21** (`ability_probe.rs`, change-logged basket;
protocol run through pause/equipment/map/merchant/gestures/dialogue/Roundtable):

- **Dead candidates, by evidence of silence where change-logging guarantees signal:**
  `CSMenuManImp.popup_menu.is_some()` never read false across three sessions (an always-present
  pointer, not a menu bit), and `sel_goods`/`sel_magic` never read anything but `None`.
- **The predicate is `ChrMenuFlags`.** Resting gameplay reads `1`; every menu state observed
  sets bit 2 or bit 3: non-pause menus read 5/7, the pause family 9/11/13/15, the map 25/27 —
  and `pause_menu_state` corroborates bit 3 in all 4,389 samples. So *game menu open* =
  `chr_menu_flags & 0b1100 != 0`. Because the probe logs on EVERY field change, the absence of
  any other gameplay value is evidence, not a sampling gap.
- **Dialogue caveat for the roll lock:** if an NPC dialogue reads as gameplay (`1`), B-as-back
  needs the belt the client already has — `esd_probe`'s talk-activity clock
  (`LAST_TALK_ACTIVITY_MS`). Mask roll only when the flags predicate is clear AND the talk clock
  is stale.

**Probe 2 — the Roundtable lead. ✅ ANSWERED 2026-08-21, one field test left.** The mechanism is
**SpEffect 9621**, and it is a *zone-applied* effect, not a Roundtable map special:

- present on the player in **187/187** Roundtable samples (play_region 1110000), absent in all
  ~4,200 samples elsewhere, and it flips exactly at the region transitions in and out;
- present in a **second region** (play_region 1600012, 25 samples) — a second sanctuary zone,
  which is what promotes it from "Roundtable trivia" to "the game's own no-combat lever";
- **negative finding:** `ChrDebugFlags` (disabled_hit / disabled_secondary_actions / ...) sat
  all-false inside the Roundtable — that family is ruled out.

The client already owns apply/strip-SpEffect infrastructure (the serpent-hunter 1908 work), so
if applying 9621 in the field disables attacks, R1/R2/L1/L2 lock with **no input masking at
all**. The one remaining measurement, per this spec's own read-back rule: apply 9621 outside a
sanctuary, swing, and record everything it blocks — TOO BROAD is the live risk (if it also eats
rolls, items or spells, it is one lever where §4.3 wants four, and the fine-grained locks fall
back to input masking behind the probe-1 predicate).

### 4.3 Per-ability mechanisms

| ability | preferred mechanism | confidence | notes |
|---|---|---|---|
| heal | `flask.rs` charge-target clamp to 0 | **high** — fields proven, infra shipped | the only one with no input component |
| jump | input mask | medium-high | jump is near-useless in menus; even the weak in-world gate may suffice |
| crouch | input mask | medium-high | stick-click; same menu profile as jump |
| dodge roll | input mask + menu predicate | medium-high | **unblocked**: mask when `chr_menu_flags & 0b1100 == 0` AND the talk clock is stale |
| R1 / L1 | SpEffect 9621, else input mask + predicate | medium-high | **unblocked pending the 9621 field test**; input masking is the fallback |
| R2 / L2 | SpEffect 9621, else input mask + predicate | medium-high | same as R1/L1 |

Two rejected/conditional paths, named so nobody re-walks them:

- **Roll via forced overload** (the inverse of `no_equip_load`: a repurposed SpEffectParam row
  with `equipWeightChangeRate` huge). ER only disables rolling at **>100%** equip load, which
  *also* collapses walk speed — "no roll" is not separable from "overloaded crawl" on this axis.
  Rejected unless probe 1 comes back empty.
- 🛑 **Any SpEffect/field path must prove the field is READ, not just the row unreferenced.**
  `no_equip_load` spent a month writing `allItemWeightChangeRate` — a sentinel no code reads —
  and logging success. Every mechanism above ships with an observable read-back (equip-load
  ratio, flask charges, a button-press probe log) or it does not ship.

**Rebinding caveat, stated once:** input-layer masking sees *physical* buttons. A player who
rebinds roll to an unmasked key evades the lock. Accepted for v1 (the mode is self-imposed
difficulty; the honour system is already load-bearing), noted in the option docstring.

## 5. Version skew

`requiresClientFeatures: ["ability_lock"]`, emitted when **any** of the eight toggles is on —
this is not optional garnish. An old client on an ability-lock seed would connect, ignore
`abilityLockFlags`, and hand the player a *normal* game while their unlock items sit in the
multiworld: the mode silently absent, which is the worst failure direction a difficulty option
has (the `no_equip_load: medium` lesson, #548).

Sequencing rule from `body_tuning.py`, verbatim in consequence: the tag must exist in the
client's `client_features.rs` SUPPORTED list **before** any world emits it, or the seed refuses
every client in circulation including the playtester's. So: client enforcement lands and ships
first (§7), world side follows in the same release.

## 6. Generator and contract impact

- `contract.py`: one `ContractKey` (`abilityLockFlags`, `{str: int}`, producer
  `ability_locks`). `tools/regen_all.py` then re-emits `CONTRACT.md`, `contract.json`, and the
  client's `contract_gen.rs` — no hand edits anywhere.
- Options ride the central `_options_echo`; the feature never writes `/options/*` itself.
- `gen_data.py` is untouched — eight hand-declared flags in the feature module, pinned by a unit
  test (§2).
- `test_gf_client_contract_paths.py` gains the new key on both sides of the gate.

## 7. Sequencing

0. **World, safe to land immediately:** the jump audit (§3) — its answer shapes the rules and it
   needs no client. Also the eight-flag reservation test.
1. ~~**Client probes 1 and 2**~~ ✅ DONE 2026-08-21 — findings inline in §4.2. One residue:
   the 9621 apply-test in the field, which decides the attack rows' mechanism in §4.3.
2. **Client enforcement**, heal first (no probe dependency), then the input-masked set behind the
   menu predicate; `ability_lock` added to SUPPORTED; read-back logging per ability.
3. **World feature** (§2, §3) emitting `abilityLockFlags` + the tag, with the option-matrix gen
   tests (every toggle combination, plus every-toggle-off byte-identity).
4. **Playtest matrix:** solo all-locked; solo roll-only; one multiworld seed with another
   player's `Dodge Roll` in our sphere 2.

## 8. Acceptance

- [ ] All toggles off ⇒ slot_data and pool byte-identical to HEAD.
- [ ] With a toggle on, the ability is dead from frame one **in world**, and the game's menus —
      inventory, equipment, map, system — remain fully navigable (the acceptance that bites).
- [ ] Receiving the unlock item restores the ability without reconnect; the log shows flag set →
      gate open.
- [ ] Heal lock: `max_hp_flask + max_fp_flask` reads 0 after a grace rest, every tick, until
      `Heal` is received; the flask ladder converges normally afterwards.
- [ ] Save-quit-reconnect mid-seed preserves lock state with no double-grant (virtual-memory
      flags are save-persisted; assert it, don't trust this sentence).
- [ ] An old client connecting to an ability-lock seed **refuses** and names the missing feature.
- [ ] All-four-attacks-locked: 100-seed gen sweep, every boss/Great-Rune check provably behind
      `has_any(attacks)`; zero FillErrors.
- [ ] The jump audit's list is in the repo and every location on it carries its rule.
- [ ] Every enforcement mechanism logs an observable read-back, not a write (§4.3's 🛑).

## 9. Open questions for Alaric

1. **Eight toggles vs a bundle Choice.** Spec recommends toggles; a bundle is less yaml surface
   but cannot say "roll only".
2. **Item names.** The §1 table's (`Light Attack`, `Guard`, …) vs button-explicit
   (`R1: Light Attack`) — the latter survives players forgetting which button casts.
3. **Do ashes/consumables count as a damage source in logic?** Conservative answer (no) is in
   §3; relaxing it later is a logic-only edit. **Spells: RULED, 2026-08-25 — they do not count.**
   *"spells don't count, you need an L or R button to cast a spell"* (Alaric). Ashes/consumables
   are still open.
4. **Does `Heal` lock the Physick too?** Item-use says no by default; thematically arguable.
5. **Scope confirmations:** sprint, Torrent, and item-use stay unlocked forever, per §1 — flag
   now if any of those was meant to be lockable.

## 10. Provenance

- The request: Alaric, 2026-08-20 (this conversation).
- Receipt→flag→enforce architecture: client `region.rs` (`set_event_flag` on lock receipt),
  `flags.rs` (virtual-memory flags, save-persisted, idempotent); world `features/area_locks.py`,
  `region_open_flags.py` (synthetic ids 76980/76981 in use).
- Synthetic-item pattern (no `ITEM_GRANTS`, act-on-name): `features/traps.py`,
  `features/boss_locks.py`; id allocation: `registry.py`, `core.py` (`collect_item_classes`,
  `allocate_item_ids`).
- Heal mechanism: client `flask.rs` (charge reconcile, writable `max_hp/max_fp` at
  `GameDataMan+0x8 -> +0x101/+0x102`).
- Input infra: client `input.rs` (XInputGetState / DirectInput / GetKeyboardState hooks,
  version-independent; per-device today, per-button struct fields already in hand).
- The wrong-field lesson: client `no_equip_load.rs` module doc (`allItemWeightChangeRate` was
  inert for a month; `equipWeightChangeRate` is the live lever; read-back or it didn't happen).
- Feature-tag sequencing: `features/body_tuning.py` (#548), `features/auto_equip.py`.
- Difficulty-options-carry-no-logic precedent: `no_equip_load`, `no_fall_damage`.
- SPEC format and the probe-first posture: `SPEC-spare-goods-pool-growth.md`.
