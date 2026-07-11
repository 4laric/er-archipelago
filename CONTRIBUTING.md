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

## Feature architecture — one self-registered file per feature

The apworld's world logic is a **registry of features**, not a monolithic
`__init__.py`. Each feature is a single file under `eldenring/features/`: a
`Feature` subclass decorated `@register`, auto-imported at load. It declares its
own options (`OPTIONS`), item classes (`ITEMS`), and only the lifecycle hooks it
needs (`generate_early` / `create_items` / `create_regions` / `set_rules` /
`slot_data`). The registry aggregates them and **raises on collision** — a
duplicate option field or `slot_data` key fails generation, it does not silently
clobber.

This structure came directly out of the AI workflow: parallel agents can't
co-edit one `__init__.py` without stepping on each other, so features had to
become non-overlapping, self-contained files. It turned out to be the better
architecture regardless — loose coupling, each feature testable in isolation,
and drift that fails loudly instead of merging silently. New world features
follow it.

- **One file, self-registered, no shared edits.** A new feature is a new file in
  `features/`; it does not touch `core.py` or other features. If your change
  needs to edit a shared module, that's a smell — push the logic into the feature
  and expose a hook instead.
- **A feature owns its own fill-safety.** Anything that can over-constrain the
  fill (e.g. forcing non-filler onto tagged locations) gates itself on what the
  pool can actually supply — it never assumes the rest of the seed.
  `important_locations` skipping enforcement when the pool is degenerate is the
  model; the fuzz gate is what proves it across combinations.
- **`slot_data` keys are declared in the contract, once.** Every key a feature
  emits is declared in `contract.py` — the single source of truth for name,
  shape, required-ness, producer, and client consumer. `fill_slot_data`
  validates against it and fails generation on drift; the client validates the
  same contract on connect. The client-side mirror (`contract_gen.rs`), the docs
  (`CONTRACT.md`), and the integration spec are **generated** from `contract.py`
  — regenerate them, never hand-edit.

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
- The greenfield gen prints a per-slot **check breakdown** to the generate log
  (`[greenfield] <slot>: N checks | progression P | useful U | local filler LF |
  foreign filler FF | foreign useful FU`). Read it: a healthy seed has real
  progression and useful spread, not a wall of filler. A collapse to near-all
  filler, or progression dropping to zero, is a regression to explain — the same
  bar as a sphere-0 balloon.

## Verification — code-reading is not evidence

Anything that touches **live game state** (flags, grants, warps, equipment,
notifications) is *unproven* until it has been confirmed in-game and the
confirmation is written down. Reading the code — or having an LLM assert it's
correct — does not count.

- **Bidirectional features need both directions proven.** DeathLink is the
  cautionary tale: incoming was confirmed while outgoing sat unverified for a
  long time. Send *and* receive each need a live demonstration before the
  feature is called done.

## Runtime visibility — a feature is armed, or it says why not

The 2026-07-01 playtest lesson. Seven features were broken at once and not one
of them crashed, warned, or logged: the defensive style everywhere in the client
(`unwrap_or(false)`, fallback-to-empty, discarded write results, retry loops
that absorb failures) converts every fault into *absence of behavior* — and
absence of behavior is indistinguishable from "feature turned off" until a
human notices gameplay feels wrong. Graceful degradation without telemetry is
just silent failure with better manners.

- **Tolerance requires telemetry.** Any code path that can degrade to a no-op
  must announce its status once at startup/connect: "armed with N entries" or
  "inert because X." A tolerant parse that falls back logs what it fell back
  to. The one-time confirm-log (`inventory-ptr CONFIRM`) is the house pattern —
  apply it to every feature, not just the dangerous ones. A feature whose
  failure mode is a polite `false` is a fail at review time.
- **Reconcile, don't dispatch.** The game rejects writes at menus and clobbers
  state on save-loads. Fire-and-forget flag writes with an advancing watermark
  lose events unrecoverably. Game-state application must latch on *observable
  state* (read the flag back; re-apply per tick until it sticks) — never
  advance a cursor past a write you didn't verify landed.
- **Validation claims carry an environment manifest and a date.** "Confirmed
  in-game" is only meaningful if it states what was on disk: vanilla snapshot
  or baked leftovers, which mods loaded, which build. Every pre-pure-runtime
  confirmation in this project silently depended on baked files providing half
  of each feature — the claims were true, then the environment changed and
  nothing forced a re-check. Ground truth expires; date it like a dump file.
- **Emitted-but-unconsumed is a half-feature.** Every slot_data key needs a
  live consumer in the client, or an explicit `CONTRACT: DEAD` /
  `CONTRACT: PORT-GAP` tag saying why not. A key that is emitted and parsed by
  nothing looks exactly like a finished feature from the gen side — the
  contract ledger is what catches it before a player does. In greenfield that
  ledger is `contract.py`, validated on both sides (gen-time and client connect);
  see *Feature architecture*.

## Regression by replay — a fix is a predicate, and production must call it

The 2026-07-06 greenfield-migration lesson. After the slot_data contract was
hardened, a dozen bugs still shipped — and every one was found one-at-a-time in
playtest. None were *absence* of behavior (the contract ledger and the arming
logs catch those now); they were *wrong* behavior with full presence: the
feature armed, the log green, but a grant fired a tick too early, a latch keyed
on the wrong flag, a shared acquisition flag leaked its neighbour. Presence and
shape checks are blind to this class — the value is well-formed and merely
wrong. The only oracle that separates "off because the player chose off" from
"off because the wire is broken" was a human watching the game, so the game is
where they were found: one seed-path at a time.

The fix is a test tier that hands that oracle to CI. A sequencing / timing /
reconcile / state-application bug lives in a *timeline*, so it gets a
host-tested **replay harness** in `er-logic`:

- **Lift the decision into a pure predicate.** The fix is a `pub fn` —
  `start_items_settled`, `region_bloom_settled`, `should_apply_incoming_deathlink`
  — that takes state and returns a decision with no game or I/O, so it compiles
  and `cargo test`s on any host.
- **Model the timeline, not a single tick.** A `#[cfg(test)] mod replay` defines
  its OWN game-state model over the `GameHook`/`NetHook` seam (never the shared
  single-tick mock — it can't represent a later save-load or reconnect), an `Ev`
  enum for the frames that matter (load screen, bulk-load clobber, save-load,
  reconnect, holder-not-ready), and a `replay(events, policy)` driver. The bug is
  reproduced as a **failing-without-the-fix / passing-with-it** pair, the policy
  flag toggling old vs new behaviour.
- **A green predicate with no production caller is not a fix — it is a spec.**
  The client must *call* the pure predicate, not keep its own inline copy;
  test/prod drift is the exact failure this tier exists to kill.
  `region_bloom_settled` was green for days while `region.rs` still latched on
  the open flag — the harness proved the fix and the client stayed broken.
  Wiring the caller is part of the change, and CI runs `cargo test -p er-logic`
  (both `run_ci.ps1` and `ci-linux.sh`).
- **Name the test after the bug mechanism.**
  `interior_graces_are_stranded_by_the_open_flag_latch` plus the predicate that
  turns it green is a machine-readable fix spec: it carries the mechanism, the
  fix shape, and the function to call. Write it to be legible to a teammate — or
  a fresh agent — on nothing but the test output.

This is the correspondence half of *Runtime visibility*: the arming logs tell
you a feature is present; the replay tier tells you it is *correct*.

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
- [ ] Every new degrade/no-op path logs its status once (armed with N / inert
      because X); no silent fallbacks.
- [ ] Game-state writes reconcile against read-back state; no watermark advances
      past an unverified write.
- [ ] Sequencing/timing/reconcile bugs land with a host-tested `*_replay` harness:
      a pure decision fn plus a timeline that reproduces the bug
      failing-without-fix / passing-with-fix, named after the bug mechanism.
- [ ] Every fix predicate has a production caller — the client calls the pure fn,
      no inline copy; a green replay with no caller is a spec, not a fix.
- [ ] In-game confirmations record the environment (vanilla/baked, mods, build)
      and date.
- [ ] New slot_data keys have a live consumer or an explicit CONTRACT tag.
- [ ] New world features are a single self-registered file in `features/`, not
      edits to `core.py` or a shared module; anything that can over-constrain the
      fill gates itself on the pool.
- [ ] Every slot_data key is declared in `contract.py` and validated both sides;
      the generated mirrors (`contract_gen.rs`, `CONTRACT.md`, handoff spec) are
      regenerated from it, not hand-edited.
- [ ] No game data or build outputs staged; `git diff --cached --stat` reviewed.
- [ ] Item-pool changes are count-neutral.
