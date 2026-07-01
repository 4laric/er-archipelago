# Contributing to Elden Ring Archipelago

Most of this codebase is written with LLM assistance. These are the quality
standards I hold that code to before it lands — my own diffs first, and anyone
else's on the same terms. They exist because a plausible-looking machine-
generated diff can't be trusted on its face: it needs to clear the specific ways
code goes wrong *in this project*, not just read well.

The point isn't to disclose that a change was AI-assisted — assume it was. The
point is to prove it works. Every gate below is a place where "it looks right"
has burned this project before, so none of them accept "it looks right" as a
pass.

---

## The headline gate: every option combination gens clean or rejects gracefully

**You should be able to flip any yaml option, in any combination, and get either
a clean generation or a clear, actionable rejection — never a stack trace, never
a `FillError`, never a silent no-op.**

This is the single most important property of the apworld and the one most
likely to break. "It genned on my one yaml" is not evidence — most of the worst
bugs in this project have been ~1-in-80 fill failures that a single lucky seed
sailed right past.

Concretely, a change that touches options, item pool, region locks, or fill
logic must:

- Extend `Archipelago/worlds/eldenring/tests/TestEROptionMatrix.py` so the new
  option (and its meaningful combinations with existing ones) is exercised.
- Pass a **seed sweep**, not a single gen — run `gen_sweep.ps1` and, for
  anything touching fill/reachability, `run_fill_regression.ps1`. One green run
  is not a pass.
- Fail *loudly and specifically* on genuinely incompatible option combinations.
  A raised `OptionError` with a message a player can act on is a pass. A
  `FillError`, a `KeyError`, or a config that generates but is unwinnable is a
  fail.

If a combination truly can't be supported, reject it at options-validation time
with a message that names both options and says why — don't let it reach fill.

---

## Options hygiene

- **Options live in `options.py`, not `__init__.py`.** Accessibility settings,
  option definitions, and validation belong in `options.py`. `__init__.py`
  consumes them; it does not define them. Factor any option logic that has crept
  into `__init__.py` back out as part of your change.
- **New options default to vanilla / no-change.** Default to `OFF`, `0`, or
  otherwise "the game behaves as it did before this option existed." A fresh yaml
  that doesn't mention your option must generate identically to before.
- **Docstrings match behavior.** Every option's docstring describes what it
  actually does. A docstring that lies is a bug, and it feeds the yaml
  comprehension/reference layer (`ER-OPTIONS-REFERENCE.yaml`,
  `EldenRing-MASTER-template.yaml`) — keep those in sync.
- **Item-pool edits stay count-neutral.** The items-equals-locations invariant
  must hold. If you add items, remove or convert an equal number; if you
  replace, replace 1:1. `filler_replacement`-style changes are the model:
  count-neutral by construction.

## Data integrity — no invented IDs

This is the AI-contribution failure mode. Language models confidently emit
flag IDs, param IDs, and item IDs that look plausible and do nothing. Event
flags here are **group-allocated** — an invented ID silently no-ops, and nothing
crashes to tell you.

- **Every numeric game ID must trace to a source.** A flag/param/item/goods ID
  is only acceptable if it comes from game data (regulation, param CSVs, the
  static flag table) or the typed API — never guessed. Cite the source in the PR
  or the code comment, or back it with a probe→readback in a test.
- **Reuse the typed API; don't hand-roll offsets.** In the Rust client, prefer
  the `fromsoftware-rs` typed singletons/structs over raw pointer math or fresh
  AOB scans. Hand-walked offsets are unreviewable and rot across game patches.
- **Verify against the source of truth, not an intermediate artifact.** Check
  generation results against the generated spoiler / on-disk source — not a
  built `.apworld`, a zip, or a stale mount. Timestamp any dump you rely on so
  it can't be confused with an older one.

## Architecture — separate decision from I/O

- **The client must not mix I/O with decision logic.** Networking, memory reads,
  and game writes are I/O; what-to-grant / what-counts-as-a-check / what-region-
  is-open is decision logic. Keep decision logic pure and testable so it can be
  exercised without a running game — mock the game *interface*, not the process.
  Pure logic belongs in the logic crate, not woven through the detour handlers.
- **User-facing strings are separated from logic and render-tested.** Item
  names, hints, and notifications route through their own layer, and a change
  that touches them is checked as *rendered in game*, not just as code — the
  `?EventTextForMap?` / `?Tag?` class of bug only shows up on screen.

## Region locks and reachability

Any new region lock, gate, or access rule ships with:

- Explicit reachability rules in `rules_mixin.py` (a `can_reach` / rule
  function), so the fill algorithm understands the gate — not just a placement.
- A guaranteed sphere-0 home for anything that must be reachable from the start.
  A lock with no early home is how you get the intermittent `FillError`.
- Coverage in the option matrix and a fill-regression run across seeds.

## Progression shape — not a billion checks in sphere 0

A seed that generates and is winnable can still be a bad seed. If sphere 0 (what's
reachable before you collect anything) holds a huge share of the checks, there's
no progression gradient — the whole game is effectively open from the start,
locks aren't doing their job, and the multiworld has nothing to hand out over
time. "It genned" does not mean "it plays."

- A change that touches locks, access rules, or the region graph must be checked
  for **sphere distribution**, not just whether it fills. Use the sphere dump
  (`ER_DUMP_SPHERES`) and look at the shape across seeds.
- Watch for sphere 0 ballooning — e.g. a lock silently spilling to start
  inventory (see the lock→start-inventory path), a region graph accidentally
  rooted so everything hangs off Limgrave, or a de-scoped lock leaving its region
  ungated. Any of these dumps the map into sphere 0 while still generating clean.
- Treat a sudden jump in sphere-0 check count (or spheres collapsing to 1-2) as a
  regression to explain, the same way you'd treat a `FillError`. The sweep should
  flag it, not a player discovering the game has no mid-game.

## Verification — code-reading is not evidence

Anything that touches **live game state** (flags, grants, warps, equipment,
notifications) is *unproven* until it has been confirmed in-game and the
confirmation is written down. Reading the code — or having an LLM assert it's
correct — does not count.

- **Bidirectional features need both directions proven.** DeathLink is the
  cautionary tale: incoming was confirmed while outgoing sat unverified for a
  long time. Send *and* receive each need a live demonstration before the
  feature is called done.

## Repo hygiene

- **Never commit game data or build outputs.** No provisioned game assets, no
  generated `event`/`msg`/`script`/`regulation.bin`, no `*.bak*`. These are
  outputs or copyrighted data, not source. Respect `.gitignore` and check
  `git diff --cached --stat` before committing — no blind `git add -A` on a tree
  that contains provisioned game data.
- **Preserve encoding and line endings.** Source here is CRLF-sensitive; a diff
  that silently rewrites line endings or corrupts encoding passes visual review
  and breaks the build. Keep `.gitattributes` behavior intact.

---

## Landing checklist

Run through this before a change lands (PR or direct):

- [ ] New/changed options live in `options.py`, default to no-change, and have
      accurate docstrings.
- [ ] The option matrix (`TestEROptionMatrix.py`) covers the new option and its
      combinations.
- [ ] `gen_sweep.ps1` passes; `run_fill_regression.ps1` passes for
      fill/reachability changes.
- [ ] Every incompatible combination rejects with a clear message — no
      `FillError`, no stack trace, no unwinnable-but-generating config.
- [ ] Every game ID traces to a source (cited) or a probe/readback test.
- [ ] Client changes keep decision logic pure and out of the I/O path.
- [ ] Live-game behavior was confirmed in-game (both directions, if bidirectional).
- [ ] No game data or build outputs staged; `git diff --cached --stat` reviewed.
- [ ] Item-pool changes are count-neutral.
