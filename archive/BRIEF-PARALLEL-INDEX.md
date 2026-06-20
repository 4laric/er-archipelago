# PARALLEL WORK INDEX — remaining backlog split across the 3 repos

Alaric, 2026-06-13. Scope: **backlog minus the two big C# ports** (#1 DLC enemy engine port and
#2 CharacterWriter are NOT split here — they're multi-week, own future briefs). Each BRIEF below
is self-contained (paste into a fresh Claude). Read this index first to avoid collisions.

## The THREE collision rules (read before launching sessions)

1. **Repo = the safe parallel boundary.** The 3 repos are independent git repos, so one session
   per repo runs with zero VCS conflict. Two of the briefs live in the SAME repo
   (`SoulsRandomizers`): run them in **separate git worktrees** (Agent `isolation: worktree`) or
   sequence them — do NOT point two concurrent sessions at one working tree.
2. **The slot_data / apconfig CONTRACT is serialized.** Per HANDOFF beta.N lockstep, ANY wire-
   contract change bumps `>=0.1.0-beta.2 <0.1.0-beta.3` across apworld + randomizer + client at
   once. Only ONE contract-touching brief exists here (`BRIEF-contract-map-reveal`) and it must
   run ALONE — never concurrently with another contract change. The four coding briefs below are
   deliberately contract-FREE so they can all run at the same time.
3. **Shared ROOT docs are NOT safe to co-edit — append to your own HANDOFF, reconcile serially.**
   The root files every session is tempted to touch — `TODO.md`, `HANDOFF.md`, this index — live in
   NO git repo (they're untracked until the superrepo, and even then a last-writer-wins blob). Two
   sessions editing `TODO.md` at once = a silent lost update: it already happened (2026-06-14, the
   #14 readability section + #13 body were clobbered by the session that added #15). Rules:
   - **During a parallel run, do NOT edit `TODO.md`/`HANDOFF.md` in-flight.** Each session writes its
     own `HANDOFF-<track>.md` (e.g. `HANDOFF-apworld-content.md`, which already exists) and/or appends
     a `## VERIFIED / DONE` block to ITS OWN brief. Those are single-owner files → no collisions.
   - **Reconcile into `TODO.md`/`HANDOFF.md` SERIALLY afterward** — one session (or you) folds the
     per-track HANDOFFs into the shared backlog once the parallel run is done.
   - Code lives in the per-repo working trees (rule 1), so it's never at risk from this — only the
     shared prose docs are. If you must record something mid-run, put it in the per-track file.

## The tracks

| Brief | Repo | TODO items | Contract? | Run with |
|-------|------|-----------|-----------|----------|
| `BRIEF-client-notify-cleanup.md` | runtime client (C++) | #11, #6-client-half | none | anytime, parallel |
| `BRIEF-randomizer-bake-polish.md` | SoulsRandomizers (C#) | #12, #6 | none | anytime; worktree vs stability |
| `BRIEF-randomizer-bake-stability.md` | SoulsRandomizers (C#) | #7, #10 | none | anytime; worktree vs polish |
| `BRIEF-apworld-content.md` | apworld (Python) | #14, #13-remaining | none | anytime, parallel |
| `BRIEF-poptracker-pipeline.md` | `poptracker/` (Lua+gen, reads apworld) | #15 M1 | none | anytime, parallel |
| `BRIEF-contract-map-reveal.md` | ALL 3 | #5 (optional polish) | **YES — bump beta.N** | ALONE |

So you can run **five sessions concurrently** (client + apworld + poptracker + two randomizer
worktrees) with no collision. The contract brief is optional polish; do it solo on a quiet contract.

> **PopTracker M0 is already built** (this session): `poptracker/` has a generating, JSON-valid
> compact pack + `tools/gen_poptracker.py` (161 regions, 86 tracked items, `--check` for CI). It only
> READS slot_data, so it's contract-free and the M1 brief parallelizes cleanly. It also touches a
> different repo path than every other track → zero collision. See `poptracker/README.md`.

## The #6 soft-dependency (not a blocker)

Double-grant (#6) is split so neither side blocks the other:
- **client brief** un-stubs `removeFromInventory` (independently useful — also clears the lingering
  placeholder tokens noted in HANDOFF "unfixed").
- **randomizer polish brief** fixes the actual double-grant (interim = route own-world shop GOODS
  through the placeholder branch; single grant).
Each ships value alone; the *fully clean* outcome (single grant AND no lingering token) emerges once
both land. No ordering required.

## Integration gate (NOT a parallel coding brief — this is you, Alaric)

Region fusion (#13) client code is DONE (this session). Closing it out is a sequential, human-in-
the-loop validation, not a Claude track:
1. `build.ps1 -Client` on Windows (Linux sandbox can't compile the MSVC + modengine code).
2. Bake a `region_lock` seed with `graces_per_region: 1`, deploy.
3. In-game: receive a lock item → watch for `Region grace flag … SET` → open map → grace selectable.
4. Reconnect mid-run → graces stay set, no errors. Then test `graces_per_region: 3` and `0`.
5. Spot-check `warpUnlockFlag` is the right flag family (cross-ref Hexinton CT, like the DLC maps).
The apworld `region_lock` gen-test for deadlocks (part of #13) IS a Claude track — it's in
`BRIEF-apworld-content.md`. Run that before/alongside the playtest.

## Excluded (own future briefs, by your call)
- #1 DLC enemy randomization engine port (the v0.8→v0.11.4 delta) — big C#.
- #2 CharacterWriter class-rando regulation-corruption fix — C#, needs CharaInitParam audit.
