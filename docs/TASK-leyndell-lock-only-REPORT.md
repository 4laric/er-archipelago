# Report: Leyndell becomes an ordinary Lock region

Branch `feat/leyndell-lock-only`, drafted by `opencode-go/muse-spark-1.3-contributor` (opencode run,
2026-09-14) from docs/TASK-leyndell-lock-only.md, reviewed and finished by Claude.

## What changed
- `features/leyndell_gate.py`: the synthetic rune wall is deleted. The file is a deprecated-option
  shim: `leyndell_runes_required` still parses, every value is ignored, a non-default logs once.
- `features/graces.py`: Leyndell's WALL_ARMED predicate is False in every seed; the capital bundle
  (Shunning-Grounds included) rides the Leyndell Lock. Gated children whose open flag is synthetic
  now anchor attunement on the derived front door instead of a random draw.
- `features/area_locks.py`: `lockRevealFlags["Leyndell Lock"] = [105, 182]` when Leyndell is kept,
  so the client's existing generic lock-reveal write opens the physical two-rune seal on Lock
  receipt. Existing contract key, no hash move (CONTRACT_HASH stays 2aa64f43).
- `features/natural_progression.py`: that mode mints no Locks, so the game's two-rune wall is
  still the wall there; its AP-logic mirror (entrance rule, capital location rules, item_rule
  cycle-breaker) moved here as `gf_capital_runes`. Note: the rune sample now runs from this
  feature's generate_early rather than leyndell_gate's, so natural_progression seeds are not
  byte-identical to before; all other seeds are unaffected by the sample (it no longer runs).
- `region_spine.py`: Leyndell stays parented under Altus for geography only.
- `core.py`, `great_runes.py`, `item_categories.py`, `legacy_key_gates.py`: references retargeted.
- Docs: player guide (gated-children section, the stale "Leyndell is always kept" line, one Great
  Runes sentence: possession only, activation never counts), CHANGELOG + BLURB for v0.6.0.12,
  KNOWN-ISSUES entry about the Unborn rune miscount removed, release yaml / wizard metadata
  regenerated, deprecated option listed in tools/dump_options_metadata.py COMPATIBILITY_ONLY.
- `greenfield/evidence/v060-current`: regenerated (legacy_key_gates.py source hash moved).

## Client
No client change is required. The client parses lockRevealFlags generically, and its rune-count
seal path (keyitems.rs tick_leyndell_gate_flags) is Unmanaged whenever slot_data carries no
naturalKeyTriggers rune clause, which is every mode except natural_progression. The tracker text
for the compound Lock+rune gate becomes unreachable outside that mode; cleanup is optional.

## Tests
- `py -3.12 -m pytest worlds/eldenring/tests` in .ap-test: 3924 passed, 90 skipped, 6 failed.
  Five of the six also fail on main (test_gf_check_browser ReportAProblemLink,
  test_gf_evidence_ledger unicode row ids); the sixth was the stale evidence bundle, fixed by
  regenerating it. Rerun of the evidence + rewritten Leyndell test files: 101 passed.
- `tools/dump_options_metadata.py --check`, `tests/test_gf_data.py`, `tools/check_release_notes.py`
  pass under Python 3.12. `run_ci.ps1` on this machine picks Python 3.14 and has no Archipelago
  checkout in the worktree, so its ZIP-GEN / FUZZ steps fail for environmental reasons only.
- Fuzz: 25-yaml run, one FillError on an extreme combination (vanilla_pool + keep_local everything +
  keep_out_of_shops everything + accessibility none); the same yaml also fails to fill on main.
