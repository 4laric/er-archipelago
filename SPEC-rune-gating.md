# SPEC: In-game Great Rune gating wired to apworld options

Status: FUTURE PROJECT, not started. (Alaric, 2026-06-11)

## Context

The apworld has `great_runes_required` (1-7, default 2: runes to enter Leyndell, ignored
under region lock) — but it's LOGIC-ONLY. Meanwhile the static randomizer already ships
real in-game enforcement machinery the AP path never invokes:

- `runes_end` / `runereq` (MiscSetup ~1168): edits the m19_00_00_00 fog-gate event
  (19002500) so the final boss door physically refuses entry below N Great Runes,
  using the game's own rune-count flags (180+N; e.g. 187 = all 7) and showing the
  vanilla "You cannot proceed without more Great Runes" dialog. PROVEN pattern —
  copy-extend, don't reinvent.
- `runes_leyndell` / `runes_rold` exist only in the fork's OWN item logic
  (KeyItemsPermutation), which AP bypasses entirely — no in-game edit for them today.
  Note Leyndell's VANILLA gate is already "2 Great Runes" in-game, so the apworld
  default (2) is accidentally enforced; any other value currently desyncs game vs logic.

## Goal

Make the apworld's rune options physically real and add the missing knobs:

1. **Leyndell gate = great_runes_required.** Find the vanilla "two Great Runes" check
   (the main gate / draconic sentinel encounter event) and patch its condition to flag
   `180 + N`, mirroring the runes_end technique. This is the main net-new event
   archaeology in this project.
2. **Final boss gate (new apworld option `final_boss_runes`, 0-7, default 0=off).**
   Enforcement already exists (`runes_end`); just plumb the count through slot_data
   and set `opt["runes_end"]` in ConvertRandomizerOptions. Logic side: add the
   corresponding rule to the apworld Victory/entrance (mirror _has_enough_great_runes).
3. **Optional: Rold bypass (`rold_runes`, off by default):** Mountaintops via N runes
   instead of (or in addition to) the Rold Medallion — the fork models this in its own
   logic (runes_rold) but has no in-game event edit either; vanilla gates the lift on
   the medallion. Needs the lift event patched to accept the rune flag as an
   alternative. Defer unless wanted; medallion-in-pool already works fine.

## Design notes

- **Counting is free:** the game maintains rune-count flags natively (180+N) and Great
  Runes only count after activation at their divine towers — decide whether logic
  should model tower access too (suggest YES eventually; today _has_enough_great_runes
  presumably counts the ITEM, so a rune the player can't activate yet could be a logic
  lie. Audit this while in here.)
- **slot_data plumbing:** `great_runes_required` is already in slot_data options (as a
  0-7 int — fine, read it via the slotData JObject like random_start, NOT the bool-only
  dict). New options follow the same path.
- **ConvertRandomizerOptions:** `opt["runes_leyndell"]`-style int options are set via
  RandomizerOptions' int mechanism (see opt.GetInt usage); confirm the setter API
  before assuming string-keyed bools are the only kind.
- **Region lock interplay:** apworld ignores great_runes_required under region_lock
  (Leyndell Lock supersedes). The bake should mirror that: skip the Leyndell event
  patch when world_logic is region_lock so the door isn't double-gated by a count the
  logic isn't modeling.
- **Messaging:** the runes_end patch reuses vanilla dialog 20003; the Leyndell patch
  should do the same. No custom FMG needed unless we want exact counts shown.

## Work items

1. Apworld: add `final_boss_runes` (and optionally `rold_runes`); logic rules; slot_data.
2. Randomizer: read the three counts from slotData in ConvertRandomizerOptions; set
   `runes_end`; implement the Leyndell event patch (new); optional Rold patch (new).
3. Audit `_has_enough_great_runes` vs tower-activation reality.
4. Test seeds: leyndell=0 (open), 7 (max) under open-world logic; region_lock seed
   confirming no double gate; final boss at 7 confirming the vanilla-dialog refusal.

Effort: the runes_end plumbing is an hour; the Leyndell event hunt is the real task
(use the runes_end edit as the template — find event, find condition index, insert
skip/refuse block). Rold is a second, similar hunt.
