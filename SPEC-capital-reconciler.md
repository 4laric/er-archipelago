# SPEC-capital-reconciler — keep flag 9116 matched to the capital the player is actually in

**Status: BUILT on `agent/capital-reconciler` (2026-07-14), ships as a unit with
`agent/gestures-and-finale` (the finale is what makes every goal seed burn). Client half on the
matching client branch. ⚠ Gated on ONE unverified assumption (§ The assumption) — default ON,
one-flag disable `capital_reconciler: false`.**

## Ground truth (Alaric, in-game 2026-07-14 + EMEVD — do not re-derive)

Leyndell ships as **two mutually exclusive map versions** selected by one save-persisted event
flag, **9116**:

| 9116 | active version | play_region bucket | contents |
|------|----------------|--------------------|----------|
| OFF  | Leyndell, Royal Capital (`m11_00`) | 11000 | Morgott + ~152 checks |
| ON   | Leyndell, Ashen Capital (`m11_05`) + Elden Throne (`m19_00`) | 11050, 19000 | THE FINALE: Gideon 510060, Godfrey 510070, Elden Beast 510230, + 7 m11_05 map lots |

* Sole vanilla setter: **Maliketh's death** — `m13_00_00_00.emevd:409` `SetEventFlagID(9116, ON)`
  (the only setter in all 589 EMEVD; re-derived by `gen_data._finale_derive` on every regen).
* The burn sequence: `common.emevd` **$Event(900)** waits on 9116, then plays the cutscene, warps
  the player into `m11_05` (region 11052010), **clears the Royal grace warp flags
  (`BatchSetEventFlags(71100, 71110, OFF)`)**, and latches **flag 118** ON as its LAST step.
  118 is monotonic — nothing in any EMEVD clears it. `m13`'s own setter (event 13002800) ends
  itself once 118 is on, so **post-burn nothing in the event layer touches 9116 again**.
* A grace warp **cannot** reach `m11_00` while 9116 is set; you get Royal back by UNSETTING 9116.
  We are pure-runtime: 9116 is ours to write.

## The strand this fixes

In region-lock play the **Farum Azula Lock lets the player kill Maliketh without clearing Royal
first** — the burn then strands the ~152 Royal checks permanently. The finale (goal) sits PAST
the burn, so **every finale seed burns**. Pre-reconciler mitigation: `ERDTREE_BURN_APS`
(location_tags.py) barred all 138 burn-strandable APs from carrying progression — a fill-side
patch over a runtime problem.

## The design (approved; two mechanisms, both client-side, both kick-watch-shaped)

**9116 default OFF (Royal is the default capital). ON only while the player is in — or warping
to — the Ashen Capital / Elden Throne.** Reconcile-don't-dispatch: decide from observable state,
write only on readback mismatch, re-apply per tick until it sticks, no cursor ever advances.

1. **Warp-target intercept.** When a warp is initiated, decide from the TARGET before the load
   resolves: Ashen/Throne target → 9116 ON; **any other resolvable target (including Royal
   m11_00) → OFF**. The player always loads the correct version. Client-initiated warps (region
   kick, random start, `!warp`) get this today via `warp.rs::warp_to_grace`; game-menu fast
   travel rides the `capital_pending_warp_target()` seam (§ Crate-API seams) and, until that
   seam is filled, converges via the latch one tick after the load instead of before it.
2. **Per-tick latch.** Standing in an Ashen bucket → hold ON; in a Royal bucket → hold OFF;
   **elsewhere → leave the flag alone** (`None`). The latch defends against anything flipping
   9116 mid-session (the map version would swap under the player on the next load).

Two refinements over the approved sketch, both blast-radius reductions:

* **Arming gate (flag 118).** The reconciler is INERT until the vanilla burn has completed once.
  Pre-burn, 9116-OFF *is* vanilla (nothing to reconcile), and writing 9116 between Maliketh's
  death and 118 would fight the in-flight burn sequence ($Event(900) and m13's event 13002800
  are both mid-timeline there). Derived, not assumed: 118 is $Event(900)'s own entry-check +
  final-step latch (`gen_data._capital_derive`).
* **The latch is scoped to the capital buckets** ("elsewhere → leave alone", not "hold OFF").
  Holding OFF globally would fight m13's setter during the burn and re-trigger $Event(900)'s
  wait gratuitously. Outside the capitals the *next warp's intercept* is what restores the
  Royal default — every warp anywhere except the 7 Ashen/Throne graces writes OFF.

**Entering the finale** is unchanged machinery: the finale region's entrance requires the Farum
Azula + Leyndell Locks (features/finale.py); the burn itself warps the player into Ashen the
vanilla way; goal-send fires on Godfrey/Elden Beast — in Ashen, where the latch holds ON.
Returning for Royal: warp anywhere (OFF restored), then walk in from Altus through the main gate
(the rune wall, unchanged) or warp to a Royal grace the player had touched.

## No fill constraint — the payoff

Because the reconciler restores Royal, **Royal is never permanently lost**. Therefore, while
`capital_reconciler` is ON:

* the `ERDTREE_BURN_APS` "may not carry progression" bar is **LIFTED** (core.`_add_locations`
  item_rule + progression_surface `_world_barred_aps` both carve it out), and
* **no new constraint replaces it** — Royal may carry progression, and Farum Azula is NOT gated
  on Morgott. Both mitigations existed only for the strand the reconciler ends. This is the
  payoff of pure-runtime: fix the runtime, delete the logic-side crutch.

With the option OFF the bar **snaps back** (same seed-time switch), so the kill switch also
restores the fill-side mitigation — seeds are winnable in both configurations.

## Derived data (no hand lists; id spaces named)

slot_data (contract.py, all 5 declared `required=False`, emitted only while the option is ON —
absent keys are the off-wire; the client logs `capital reconciler INERT`):

| key | value | derivation |
|-----|-------|-----------|
| `capitalBurnFlag` | 9116 | `gen_data._finale_derive` ($Event(900)'s one wait flag) |
| `capitalBurnDoneFlag` | 118 | `gen_data._capital_derive` ($Event(900)'s entry-checked + body-set latch, minus the burn flag; count-pinned to exactly one) |
| `capitalAshenPlayRegions` | [11050, 19000] | partition of `region_play_ids.py`'s MEASURED Leyndell buckets (KICK id space) by the map each encodes: `b//10 == 1105` or `b//1000 == 19` |
| `capitalRoyalPlayRegions` | [11000] | same partition, `b//10 == 1100`. **HARD-FAILS gen** (ContractError) on an unclaimed bucket or an empty side — a dropped bucket is a latch that is permissive exactly there |
| `capitalReleaseRows` | [[101516,9116,118] ×4] | shop_rows.tsv rows with `release_flag == 9116` AND `value > 0` (purchase checks); count-pinned to 4 |

Warp targets are **BONFIRE ENTITY ids** (`BonfireWarpParam.bonfireEntityId`, the space
`warp_to_grace` already speaks). Bucket rule `id/10_000*10` for 8-digit dungeon graces, verified
against **every** capital row of BonfireWarpParam.csv (2026-07-14):

* Royal `m11_00`: 9 graces `11001950-11001959` (rows 110000-110009, warp flags 71100-71109) → 11000
* Ashen `m11_05`: 6 graces `11051950-11051955` (rows 110500-110505, warp flags 71120-71125) → 11050
* Elden Throne `m19_00`: 1 grace `19001950` (row 190000, warp flag 71900) → 19000
* Roundtable `11102950` → 11100 (never a capital); 10-digit overworld tile ids → never a capital.

## The 9116-released shop rows

Four live shop checks — **Enia's Maliketh armor set**, ShopLineupParam rows **101516-101519**
(stock flags 250160/250170/250180/250190 = checks 7770500-7770503) — use
`eventFlag_forRelease = 9116` itself. Vanilla keeps 9116 ON forever post-burn so they stock; the
reconciler's OFF-default (Roundtable included: every warp home writes OFF) would de-stock them
permanently. Fix: the client re-keys those rows' release flag **9116 → 118** (monotonic, set
seconds after 9116 in the burn — same vanilla release timing, immune to our toggling).
`shop_flags.rs::run_capital_release`, write guarded (only rewrites a row whose live value is the
expected 9116; anything else is logged and left alone). The three `value = 0` rows that also
release on 9116 (101785 / 102710 / 102810 — remembrance-of-the-Black-Blade duplication trades,
not checks) stay vanilla: **duplicating Maliketh's remembrance is only offered while 9116 is ON**,
i.e. in practice while the player is in the Ashen Capital. Known cosmetic wart, listed below.

## ⚠ The assumption (unverified — the reason the option exists)

**Toggling 9116 at will has no bad side effects.** Alaric is deferring the in-game CE probe;
this feature is BUILT ON that assumption. Containment:

* Whole feature behind `capital_reconciler` (DefaultOnToggle, **default ON** — a deliberate
  exception to "new options default to no-change", because the strand is a live softlock on
  every finale seed and Alaric approved the design). **Disable = `capital_reconciler: false`**
  in the yaml: no slot_data keys → client INERT → vanilla one-way burn → progression bar back.
* Blast radius: the client only writes 9116 **post-burn** (118 gate) and only to MATCH the
  player's current/target capital. It never toggles gratuitously (write on readback mismatch
  only) and never touches the first burn.

Known 9116 consumers a probe must clear (grepped from common.emevd + params, 2026-07-14 — cited,
not interpreted):

* `common.emevd:209` — $Event(1100) slot 16: 9116 → Maliketh boss-reward lot 10160 / remembrance
  510160. **Expected benign** (the reward fires at the kill, while 9116 is genuinely ON).
* `common.emevd:2620` — a tutorial-popup event branches on 9116 (grants goods 710600).
* `common.emevd:5063, 7268, 7315, 7319, 7403` — NPC/quest conditions combining 9116 with quest
  flags (e.g. 1051569361, 11109921). **This is the real risk surface: NPC states while 9116 is
  OFF post-burn.**
* `m13_00_00_00.emevd` event 13002805 — bonfire/ambience state 3227 keyed on 9116 (Farum Azula
  cosmetics).
* `ShopLineupParam` release rows (§ above — handled).
* Enia's remembrance duplication of the Black Blade (§ above — offered only while ON).

Derived warts (facts, not assumptions — from $Event(900)'s body):

1. **Burn-cutscene replay on re-entry.** A session that loads with 9116 OFF arms $Event(900)'s
   wait; the next OFF→ON transition (warping back to Ashen) replays the skippable burn cutscene
   and lands the player at the Ashen entry grace (11052010) instead of their chosen grace, and
   re-clears warp flags 71100-71110. Functionally correct destination; degraded UX. If the probe
   confirms this is intolerable, the mitigation is a load-window hold (keep 9116 ON through
   common-event init when 118 is set, reconcile after) — NOT built, deliberately: it has its own
   failure mode (a save made inside Royal loading against a forced-ON flag) and needs the probe
   first.
2. **Royal grace warp flags are wiped by every burn/replay** (`BatchSetEventFlags(71100,71110,
   OFF)`). The reconciler does NOT re-light them — that would hand out warp targets past the
   rune wall the graces feature deliberately withholds (features/graces.py). The player re-earns
   Royal warp points by walking in and touching graces; Royal is still never *lost*.
3. **Ashen grace map visibility with 9116 OFF is unknown** (vanilla can never be in that state).
   If the map hides touched Ashen graces while OFF, returning to the finale needs the one grace
   the burn replay provides (11052010) — still reachable, still correct-version. Probe item.

### The CE probe that retires the assumption (hand Alaric this list)

On a post-burn save, via CE/`!flag` primitives:
1. Unset 9116 → warp to a Royal grace / walk in from Altus: does m11_00 load, with Morgott's
   state and the ~152 checks live?
2. With 9116 OFF post-burn, tour the 9116-conditioned NPCs (the `common.emevd:5063/7268/7315/
   7319/7403` quest lines) — any stuck/duplicated dialogue or quest regressions?
3. Set 9116 ON (via an Ashen-grace warp) → does the burn-replay wart (§ above) fire, and is it
   tolerable? Do touched Ashen graces stay visible on the map while 9116 is OFF?
4. After Elden Beast / goal-send, unset 9116: does the ending state survive?
5. Enia at Roundtable with the re-keyed rows: Maliketh armor purchasable post-burn regardless of
   9116? (`capital release re-key` log line confirms the write.)

Each PASS gets a dated line in `greenfield/IN-GAME-VALIDATION.md`; all five passing retires this
section and (follow-up) lets `ERDTREE_BURN_APS` itself be deleted from gen_data as a tag.

## Crate-API seams (Alaric fills; everything else compiles as written)

* **`region.rs::capital_pending_warp_target() -> Option<u32>`** — currently `return None`. Needs:
  the pending fast-travel destination while a GAME-menu grace warp is resolving (the value the
  engine's own warp machinery was handed — CSLuaEventManager's queued warp arg or the GameMan
  equivalent), converted to the **bonfire ENTITY id** space (if the crate surfaces a
  BonfireWarpParam ROW id, read the row's `bonfireEntityId`; the spaces differ: row 110500 vs
  entity 11051950). Until filled the reconciler self-degrades gracefully (latch-after-load).
* No other new crate symbols: the flag writes ride `flags.rs` (`CSEventFlagMan`), the shop
  re-key rides shop_flags.rs's existing typed-row + documented-offset pattern
  (`eventFlag_forRelease @ +0x10`, same row base the probe-confirmed `+0x0C` stock writes use —
  the `capital release re-key` log line is its in-game confirmation).

## Verification status

* **er-logic (host, sandbox-run):** `cargo test -p er-logic` → **324 passed** (313 baseline + 11
  new: `capital::tests` ×7, `capital_replay` ×4). Break-it: with the reconciler policy disabled
  in the sim, `royal_capital_is_stranded_by_the_one_way_burn_flag` goes red with
  `left: 11050, right: 11000` — the Royal-grace warp landing in the Ashen version, i.e. the
  strand — and the round-trip fails at "latch re-asserts ON". Clippy (`-p er-logic -- -D
  warnings`) clean.
* **apworld (sandbox-run):** `tools/gf_test.py` — new suite green (partition, pins, ON/OFF/rolled
  seeds); break-it: disabling the core carve-out turns
  `CapitalOnSeed::test_royal_capital_may_carry_progression` red. Full-suite + coverage numbers
  in the landing report.
* **Client `.rs` (eldenring-archipelago) cannot compile in the sandbox** (Windows-gated crate);
  the Windows-cargo CI on push is the build gate — poll it before handover.
* **Windows regen** (data.py additions): `python greenfield/gen_data.py` — expected new stdout
  line: `capital: burn flag 9116, done latch 118; 4 release row(s) re-keyed ([101516, 101517,
  101518, 101519])`; data.py gains `CAPITAL_BURN_FLAG / CAPITAL_BURN_DONE_FLAG /
  CAPITAL_RELEASE_ROWS`, and `test_gf_capital_reconciler::test_generated_data_and_fallbacks_agree`
  stops skipping (it pins generated == fallback; a drifted fallback fails, not lingers).

## One line to disable if the assumption proves false

```yaml
capital_reconciler: false
```

(vanilla one-way burn returns; the Royal progression bar snaps back; the client goes INERT and
never writes 9116.)
