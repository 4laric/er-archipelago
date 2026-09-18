# Task: Leyndell becomes an ordinary Lock region ("option one", Alaric 2026-09-14)

Read AGENTS.md and CONTRIBUTING.md first. Work only in this worktree (branch feat/leyndell-lock-only).
World repo only. Do NOT touch the client submodule dir. Commit in small steps with clear messages.

## Decision
Leyndell, Royal Capital is no longer a gated child. Its grace bundle rides the `Leyndell Lock`
exactly like every ungated region (same ruling already applied to Raya Lucaria Academy on
2026-08-16, see features/graces.py docstring). The physical two-Great-Rune seal is taken down
by the client on receipt of the Leyndell Lock (client half is a separate PR; the world only has
to carry the intent in slot_data / contract). Great Runes gate NOTHING in Leyndell any more:
they remain in the pool and are progression only under `ending_condition: great_runes`.

## World changes
1. Retire `features/leyndell_gate.py` and the option `leyndell_runes_required`.
   - Remove the synthetic rune wall (generate_early sample, set_rules entrance/location rules,
     item_rule cycle-breaker, gf_leyndell_runes / gf_leyndell_injected).
   - Keep the option NAME accepted as a deprecated no-op so old YAMLs still generate; log once
     that it is ignored. Follow the pattern used for other deprecated options in this repo.
2. `features/graces.py`: Leyndell's WALL_ARMED predicate becomes False in every seed (like Raya);
   the Leyndell Lock's regionGraces bundle is the full capital bundle. Update the docstring
   history (do not delete history, append a dated SUPERSEDED note as the file already does).
3. `region_spine.py` REGION_PARENT: KEEP `"Leyndell": "Altus"` for geography (Alaric's call),
   but fix its comment (no rune gate any more). Check `features/natural_progression.py`
   GAME_NATIVE_GATE = {"Leyndell"}: natural_progression mints no Locks, so the game's own
   two-rune wall is still the wall THERE. Leave that mode's behaviour intact and say so.
4. `features/great_runes.py`: the seven-rune top-up may stay. Remove any reference to the
   Leyndell wall as a consumer. Make sure runes are classified progression ONLY when the
   great_runes ending needs them (check core._class_for).
5. Contract / slot_data: add ONE key the client can read to open the seal on Lock receipt.
   Prefer reusing an existing seam (e.g. regionOpenFlags["Leyndell Lock"] plus a bloomed flag
   list including 105 and 182), otherwise add `leyndellSealFlags: [105, 182]` under the
   Leyndell Lock. Document it in contract.py the way other keys are documented, and mark the
   retired rune-wall keys DEAD there if any are still declared. Bump the contract hash per
   CONTRIBUTING.md rules (removals/renames rule: read the "AP ids" and contract notes).
6. `Elden-Ring-Archipelago-Player-Guide.md`: rewrite the Leyndell / gated-children paragraphs
   (lines ~38-58) and the stale line ~87 "The goal region -- Leyndell -- is always among the
   kept ones" (false since 2026-08-06). Add one sentence on Great Runes: possession only,
   activation never counts, they gate only the great_runes ending.
7. Update the wizard / presets / EldenRing.yaml template if they mention leyndell_runes_required.
8. KNOWN-ISSUES / CHANGELOG entry per repo convention.

## Tests
Rewrite or delete (do not patch around): tests/test_gf_gated_children.py,
test_gf_leyndell_rune_floor.py, test_gf_grace_gates.py, test_gf_goal_required_runes_surfaced.py,
plus anything else grepping `leyndell_gate` / `gf_leyndell`. Add a test that the Leyndell Lock's
regionGraces bundle is non-empty in a default seed and that a seed with Leyndell kept and ZERO
runes reachable is still beatable under logic.
Run the full suite the way CONTRIBUTING.md says (run_ci.ps1 or pytest under .ap-test) and make
it green. Run a few generations with the fuzz yamls (gen_fuzz.ps1) and confirm no OptionError.

## Out of scope
Client repo. Raya Lucaria. Ashen Capital / finale. Do not remove Great Runes from the pool.

## Deliverable
Commits on this branch and a short summary in docs/TASK-leyndell-lock-only-REPORT.md:
what changed, contract hash before/after, test results, anything you could not finish.
