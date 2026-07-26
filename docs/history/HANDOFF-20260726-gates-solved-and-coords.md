# Handoff — 2026-07-26 (the gate hunt, solved; check coordinates, started)

**Read this adversarially. Its predecessor's central example was WRONG and cost two sessions.**

That is not a figure of speech. The 2026-07-25 handoff opened by warning that *"this document is
where an assumption gets laundered into a requirement"* — and then did exactly that, in its own §4,
in a sentence with no attribution. Two sessions chased it. So: **verify COMMANDS, not RESULTS.**
Everything below is labelled VERIFIED (and how) or INFERRED. §6 is what I got wrong; it is long.

Heads: world `906b3e1`. Client untouched this session (`9c4e3d9`, gitlink current).
🔴 **`main` is RED and that is EXPECTED — see §5. It needs a regen on Alaric's box, not a code fix.**

---

## 0. Summary

The "checks gated behind another region" hunt is **solved**. The gate was never where two sessions
looked, and the reason is a single mechanism: **the gate flag is a literal at the
`$InitializeCommonEvent` CALL SITE, while the test that consumes it lives in the CALLEE, on a
parameter.** Every literal-only scan saw ~1% of the relevant corpus.

Also: a new MSB table (163 `StartDisabled` treasures), a new ESD table (2408 NPC-state flags), and a
scoped-out exclusion of 8 questline-gated checks. Coordinates work is specified but barely begun.

---

## 1. 🛑 THE EXEMPLAR WAS WRONG — the single most important thing here

The predecessor said: *"`f67050`, the cookbook Roderika leaves at Stormhill Shack ... the pickup does
not EXIST until you rest at a grace in Liurnia."*

**f67050 is ungated.** VERIFIED five ways:
- `Event/Treasure/宝死体000.xml` → `StartDisabled=0`, `EntityID=0`
- `Part/Asset/AEG099_610_9000.xml` → `NeverDisable`, `MapStudioLayer=0xFFFFFFFF`,
  `DisableWhenMapLoadedMapID` all `-1`, no condition
- flag AND lot `1040390000` appear NOWHERE in all 589 decompiled EMEVD (word-boundary)
- ESD-set flags are disjoint from pickup acquisition flags
- `flag_lots` has one unconditional row

Fextralife and Game8 both place it on "a dead man sitting" at the collapsed bridge to Stormveil, with
**no Roderika involvement**.

**The real check is the GOLDEN SEED, `f400191`** — *"in Stormhill Shack where Roderika was sitting, if
the player rests at any site of grace in Liurnia of the Lakes, or by giving her Chrysalids' Memento."*
Alaric's in-game report was correct the whole time; it had been welded to the wrong flag. He supplied
the correction from a screenshot. **Live-game truth is his; file-truth is ours. Ask him.**

## 2. ⭐ THE MECHANISM (VERIFIED — this is the session's real result)

```
m60_41_38_00.emevd.dcx.js:
  $InitializeCommonEvent(0, 90005750, 1041381702, 4350, 101910, 400191, 400191, 3708, 0)
                                                       ^lot  ^acq   ^acq   ^GATE
  (called 3x: gates 3708 / 3709 / 1041389414 = the three ways to trigger it)

common_func.emevd.dcx.js:
  $Event(90005750, ..., function(assetEntityId, actionButtonParameterId, itemLotId,
                                 eventFlagId, eventFlagId2, eventFlagId3, sfxId) {
      WaitFor(EventFlag(eventFlagId3) && !AllBatchEventFlags(eventFlagId, eventFlagId2));
      ... AwardItemsIncludingClients(itemLotId);
```

**Measured blind spot:** 185 of 256 common events test a parameter as an event flag; **3676 of 10449
`$InitializeCommonEvent` call sites** target one of them.

**SECOND, INDEPENDENT blind spot: the award verb set was wrong.** Corpus counts —
`AwardItemsIncludingClients` **205**, `AwardGesture` 29, `AwardItemLot` **26**. The tool knew only the
minority verb. So the predecessor's *"AwardItemLot is RARE (19 sites) — scripted awards are not the
mechanism in ER"* was **a fact about the SCAN, not about the game.** Both fixed in `49b16b3`.

⭐ Same defect Fable had already found in `datamine_esd_flags.py` (constant at the call site, use in
the callee). **When one tool has it, check the others.** `datamine_boss_drops.py` and
`datamine_shop_rows.py` are UNAUDITED for this — INFERRED that they may share it; go look.

## 3. What shipped

| commit | what |
|---|---|
| `bc376fc` | AGENTS.md §2 (main IS the live branch; the table has rotted 3x) + §4 (`api.github.com` IS reachable, unauthenticated — the old "you cannot read CI" claim was false and had cost a red `cargo fmt`) |
| `8a44a41`,`e0cb0fe` | `datamine_esd_flags.py` + `esd_flags.tsv` — 2408 NPC-state flags |
| `cc4d1f6` | `datamine_msb_gated_treasures.py` + `msb_gated_treasures.tsv` — 163 rows / **136 DISTINCT** live checks with `StartDisabled=1` |
| `49b16b3`,`a322f40` | `lot_gates` common-event ARGUMENT resolution + role classification |
| `906b3e1` | `_QUESTLINE_GATED` — 8 checks excluded |

## 4. 🟠 THE 135 — best next target

Of the **136** MSB `StartDisabled=1` live checks, **exactly ONE** has a known gate. 135 start absent
at map load with **no known enabler**. That is the highest-risk population left (a check that cannot
exist, placed as reachable). The join to try: `TreasurePartName → Part/Asset → EntityID →
EnableAssetTreasure`, now including common-event args. INFERRED that it will resolve; not attempted.

## 5. 🔴 WHY MAIN IS RED — do not "fix" it in code

`test_gf_lot_gates_cross_region` fails: the 8 questline-gated checks are excluded in
`gen_data._QUESTLINE_GATED`, but `data.py` is GENERATED and still lists them. **It needs
`build.ps1 -Greenfield` (or `-All`) on Alaric's box.** The artifacts are not in the sandbox; I did not
fake a regen. Dropping checks also renumbers downstream ap-ids.

🛑 **Do NOT raise `MAX_CROSS_REGION_GATES`.** Going green by raising it discards the only real result
the hunt produced. The excluded 8 are all NPC-questline drops (Freyja, Moore, Ansbach, Ranni, Dung
Eater, Edgar/Irina) — item in region A, prerequisite in region B. **Questlines are out of scope
(Alaric)**, which is also why Roderika's gesture and jellyfish ashes are not checks. If questlines are
ever scoped IN: delete the set and write an access rule per questline in `core.py` — **the regions are
right; the reachability claim is not.**

## 6. Things I got WRONG — do not inherit them

1. **"559 shop rows are never spatial."** Alaric: *"the merchant has a location."* 140 of them have
   exactly one merchant map; the other 379 are **multi**-spatial, not non-spatial. I asserted a
   ceiling instead of measuring one, then quoted a "74.4% real coverage" built on it. **Every coverage
   number I gave moved once it met the data. Don't quote one until the direct joins are proven.**
2. **Reported 224/224 "cross-region"** from a standalone stand-in that compared RAW `region_map`
   labels against RESOLVED region names — the identical artifact §5.6 of the previous handoff
   documents. One session later, same trap. The real test needs the AP world package; **CI is the
   gate, and CI is readable (§3).**
3. **My first common-arg pass fabricated gates**, turning CI red with 27. `AllBatchEventFlags(a,b)` is
   the ACQUISITION RANGE, not a prerequisite (check 400381 was "gated" on 400382 — the other end of
   its own range; an `arg == check` guard cannot see that, a RANGE guard can). `EndIf(EventFlag(p))`
   is a bail-out with INVERTED polarity. **A false gate is an unwinnable seed; a false non-gate is
   only a miss.**
4. **Then I over-corrected and deleted the known-true case.** My negation guard searched the whole
   body, and 90005750 contains `flag = !EventFlag(eventFlagId3)` further down, so an unrelated line
   removed f400191. ⭐ **Caught only because I checked a KNOWN-TRUE control survived.** Both controls
   now run on every emit (f400191 present, 400381→400382 absent). **Keep them.**
5. **`grep … | head -10` hid the answer.** My first look for 67050 in `greenfield/*.tsv` filled its 10
   hits from other files and I nearly reported "absent from msb_flag_region" — the "empty result reads
   as *the data isn't there*" failure. **A `head` on a grep is a truncating derivation.**
6. **A moved `REPO` silently disabled every guard** in `datamine_esd_flags.py` — found only by
   break-testing. Missing cross-check inputs are now FATAL.
7. **Counted ROWS and called them CHECKS** (155 vs 136) — verbatim the `resolved.len()` bug in
   CONTRIBUTING. Both numbers are printed now.
8. **Fable's review was wrong once too**: it said `SetEventFlagIf`'s target is arg 1. It is
   `(cond, TARGET, sense)` — arg 2. Its grep truncated at a nested paren. **Verify a reviewer's
   structural claims as well as your own.** (It was right about everything else, twice, and found a
   340-flag undercount. Keep using it.)

## 7. Working notes

- **`elden_ring_artifacts\{talk,event,mapstudio}` are MOUNTABLE.** Copy OUT before reading (mount
  reads truncate) and verify counts + byte totals. mapstudio is 2.2 GB / 1347 `*-msb-dcx` dirs.
- ⚠️ **A full mount walk exceeds the harness's hard 45 s bash cap** (`timeout_ms` is capped at 45000).
  Chunk with a checkpoint file in `/tmp` — `datamine_msb_gated_treasures.py --state` does this.
- **MSB schema, OBSERVED not guessed:** `<map>-msb-dcx/{Event,Part,Region,Route,Model}/` +
  `_witchy-msbe.xml`. `Event/Treasure/*.xml` → `ItemLotID` + `TreasurePartName` →
  `Part/Asset/<name>.xml` → `<Position>`. `_99` map variants exist for 32 maps and carry
  **Part/Asset but ZERO Treasure**.
- 🛑 **A `--depth N` clone makes `git rev-list --left-right` LIE** — the left count saturates at the
  clone depth, so every branch reports the same fabricated number. `--unshallow` before measuring.
- `ER_EVENT_DIR` (new) and `ER_ARTIFACTS_VV` stage artifacts outside the repo so an emit is the
  TOOL's output, never a path-patched copy.
- pytest is NOT installable in the sandbox (no PyPI). The apworld suite needs
  `greenfield/provision-linux-env.sh`; CI is the practical gate.

## 8. 🔵 Coordinates — specified, barely started

**DESIGN DECIDED (Alaric): one-to-many. `check → {(map_id, x, y, z, availability_condition)}`.**
His words: *"i don't want to get bit by oversimplifying the game in modelling again."* Same arity
lesson as Messmer's Kindling.

4849 live checks, 3192 with coords, **1657 without**: 672 in `msb_flag_region` (500 event / 111
treasure / 61 enemy) · 140 single-merchant shop rows · 379 multi-merchant · 40 unresolved · 428 in
neither table.

Two independent sources of many-ness, and they COMPOUND: 496/709 shop rows have >1 seller, **and
13 of 48 merchants appear on multiple maps** (Alaric: *"most of them don't move. check those DLC
fuckers Moore and Thiollier, Sellen."* — npc `130900` spans 5 maps).
⚠️ **`merchant_shops.tsv.merchant_name` is EMPTY** (holds npc_param_ids). Populating it is a
prerequisite for human triage — I could report that 130900 relocates 5x but not who it is.

**Availability comes from the ESD** (Alaric's idea): join `esd_gates.tsv`
(`talk_id → gate_flag → shop_begin..end`) to `merchant_shops.tsv` (`row_id → talk_id → map_id`) so
each *(row, merchant instance)* carries the flag that makes THAT instance live.

Agreed order: **(1)** the 111 treasure-source (cheapest, certain — prove the pipeline);
**(2)** MEASURE how many of the 500 `source=event` actually resolve to an asset part before promising
them — most likely assumption to collapse; **(3)** the 61 enemy-source via `Part/Enemy`;
**(4)** shop rows, after `merchant_name`.

**Payoff:** kills the `tile_pr` nearest-neighbour guess — 144 tiles / 640 checks currently regioned by
an oracle that never fails and therefore cannot refuse.
