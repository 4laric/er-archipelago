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

- Extend `greenfield/eldenring/tests/test_gf_options.py` so the new
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

- **Options are declared where they are owned, and assembled once.** A core option
  is a class in `core.py`, listed in `_CORE_OPTION_FIELDS`. A feature's option is a
  class in that feature's own `features/<name>.py`, listed in its `OPTIONS` dict.
  `core.GFOptions` is then assembled from both by `registry.collect_option_fields`,
  minus anything in `defaults.FROZEN_OPTIONS`. Nothing else defines options — a new
  option goes in exactly one of those two places, never a third.
  (This bullet named a central `options.py` until 2026-07-28. No such file exists in
  the greenfield world, and the stale name had already leaked into a spec written
  from this document.)
- **New options default to vanilla / no-change.** Default to `OFF`, `0`, or
  otherwise "the game behaves as it did before this option existed." A fresh yaml
  that doesn't mention your option must generate identically to before.
- **Docstrings match behavior.** Every option's docstring describes what it
  actually does. A docstring that lies is a bug, and it feeds the yaml
  comprehension/reference layer (`wizard/options-metadata.json`,
  `release-v0.2/EldenRing.yaml`) — keep those in sync.
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

- Explicit reachability rules in `greenfield/eldenring/core.py` (a `can_reach` / rule
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

- [ ] New/changed options live in `core.py` (listed in `_CORE_OPTION_FIELDS`) or in the
      owning `features/<name>.py` (listed in its `OPTIONS`) -- never a third place --
      default to no-change, and have accurate docstrings.
- [ ] The option matrix (`test_gf_options.py`) covers the new option and its
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
- [ ] Any `reset()` / re-arm added to the client is CALLED on the in-world edge (or exempt with a
      reason) -- `test_gf_client_resets_are_called` enforces it. A load reverts param writes.
- [ ] For a player-reported bug, the claim states the LAST stage actually observed ("slot_data is
      correct" is not "the player sees it"), and every unchecked stage downstream is named.
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
- [ ] No fix re-ranks, prioritises, or special-cases the item/class that happened to break: if the
      model's *arity* is wrong (one flag ↔ many lots, two id spaces, two map versions), the model
      changed, not a tiebreak.
- [ ] Every constraint the change designs around names its owner — GAME / ARCHIPELAGO / US — with a
      citation for the first two; anything handed to a subagent or a future session is labelled
      assumption-vs-invariant, never silently hardened into a brief.
- [ ] Player-visible change? Its `release-v0.2/CHANGELOG.md` line is in THIS commit, under the
      current `## v<version> — <date>` heading, and `BLURB-v<version>.md` grew with it --
      `python tools/check_release_notes.py` is green (rule 14).
- [ ] A merged spec's acceptance list is pasted into a tracking issue, one checkbox per line, each
      marked shipped / partial / absent with the command or file that proves it. Prose in
      `docs/specs/` is not a gate. Build the bullets that need a NEW test tier first — those are the
      ones whose absence nothing else will reveal.

---

## The silent wrong answer

Read the bug list in this file. Almost none are crashes. **Every one is a derivation that returned a
confident, complete, WRONG answer instead of failing.** Everything below is one prescription: *make
not-knowing louder than knowing.* A crash costs an hour; a confident wrong answer costs three months
and a playtest.

### The canonical shape

> The play_region bucket table was keyed on `BonfireWarpParam.bonfireSubCategoryId`, on this comment:
> *"equals the runtime play_region_id — verified against every empirically captured id."*
>
> True, and **vacuous**: no DLC id had ever been captured, because nobody had played the DLC. The kick
> compares `play_region_id / 100`, so 27 of 53 buckets could never match — and it is **permissive on an
> unknown bucket**, so a miss is a shrug, not a crash. The DLC region locks never fired, **Weeping's
> lock had never enforced anything in any seed, ever**, and the same table silently inerted the
> Scadutree floor and DLC enemy scaling.
>
> Nothing errored. Nothing logged. For months.

Note the two halves, because they always travel together: **a false claim in a comment**, and **a
consumer that treats "no answer" as "no problem."**

### Rules

**1. A derivation that cannot answer must FAIL, not answer.**
Never return a plausible value on missing input. `tile_pr()` is a nearest-neighbour: it *never fails*, so
a coarse LOD tile got a confident wrong region. If the answer is unknown, say `DEFAULTED` and bar it from
carrying progression.

**2. An empty result is a FAILURE, not a clean run.**
A join that matches nothing reports "0 rows" and looks like success. Zero, empty, and "nothing to do" are
the three most dangerous outputs in this repo — every one of them must be an explicit, loud decision.
*(A tool joined on renumbered ap-ids — 777xxxx vs 700xxxx, zero overlap — and reported "0 buckets" as a
finding.)*

**3. A wrong id space does not error. It just never matches.**
`check_lots_table` keyed suppression by the RAW `lotItemId` while the client's detour reads the **FullID**
(`category nibble | raw`). Weapons have nibble `0x0`, so **they worked** — and that is precisely why it
hid. Armour, talismans and every Ash of War leaked their vanilla copy for months while the log cheerfully
said `vanilla suppressor ARMED for 865 check item ids`.
**Whenever two components exchange ids, name the SPACE in the type, the key, or the comment — and assert it.**

**4. Silent input loss is the same bug upstream.**
`if not m.startswith("m"): continue` quietly discarded **40% of the input rows** and the tool ran green.
If you skip rows, COUNT them and print the count. A filter with no tally is a lie.

**5. RUN the tool. Do not read it.**
One derivation tool in this repo produced **eight** separate confident-wrong outputs — imported the wrong
package, joined on a drifted key, parsed a table inside-out, mangled `Charo's` into `'s`, used the wrong
discriminator, dropped 40% of rows, mis-decoded interiors, truncated LOD tiles. **None of them threw.**
Every one was caught by running it and looking at the output. None would have been caught by reading it,
and several were written *while* reading it.

**6. Check the output for what is MISSING.**
A diff shows you what changed; it cannot show you what was never there. The bug nothing automated caught
was a human noticing *"I don't see Raya Lucaria in here"* — a whole region silently absent from a
derivation's output. **Absence is invisible. Go looking for it.**

**7. Verify the fix by breaking it.**
A passing test proves nothing until you have seen it fail. Disable your fix, confirm the gate goes red,
re-enable. If you cannot make it fail, you have not tested anything. *(The `EarlyGuarantee` gate was only
trustworthy once the guarantee was switched off and it reported `guaranteed 12, found 7`.)*

**8. Guard the right thing.**
A guard is a derivation too, and it will lie to you just as happily. One written here asserted "the ids
should exist in `ITEM_CATALOG`" — but the catalog only holds what the world can *grant*, so it measured
**coverage** and blocked a **correct** table. Ask: *what would make this guard pass while the bug is
present, and what would make it fail while the code is right?*

**9. Never half-apply an edit.**
A scripted edit whose pattern does not match must **raise**, not skip. One that silently no-op'd shipped a
table of `[[cat, raw]]` pairs instead of ints — valid JSON, wrong shape, suppressing **nothing**. Assert
the edit landed, and assert the OUTPUT SHAPE before writing a file another component parses.

**10. A comment that asserts a fact is a claim, and claims rot.**
*"Verified against every empirically captured id"* was the sentence that cost the most this year. If a
comment states an invariant, **there must be a test that fails when it stops being true** — otherwise it
is folklore with syntax highlighting.

**11. The case that motivated the work is the acceptance test. Assert the screen SEES it.**
The 2026-07-26 lesson, expensive because every part looked green.

> A day on `f400191` -- the Stormhill Shack Golden Seed, which does not exist until you have
> progressed past the Roundtable. We found its gate, wrote `datamine_lot_gates.py`, confirmed the
> vocabulary with `--vocab`, resolved common-event ARGUMENTS to see past a blind spot, emitted the
> table, and built `test_gf_lot_gates_cross_region` to screen exactly this class.
>
> The next build shipped `f400191` **still miscategorised**.
>
> Nothing was broken. The datamine FOUND the gate and wrote all three flags. The screen READ the
> table -- then resolved a gate flag's region by decoding its NUMBER, which only works for
> map-encoded flags, and `continue`d past every pair it could not decode. The flags gating `f400191`
> are bare 4-digit NPC state ids. The finding was produced, stored, and silently dropped by its own
> consumer, and the suite went green.

**A pipeline whose stages are each individually correct can still drop the exact input that caused
it to be built.** Producer coverage and consumer coverage are different numbers and nobody checks
the composition. So: **when you build a tool or a gate because of a specific case, add that case as
a fixture and assert the finished pipeline still reports it** -- end to end, by name. If the
exemplar cannot be a fixture, say in the test how you would know it was still covered.

Corollary, and the part that stings: **the coverage number was already written down and stated
honestly.** The screen's own floor read *"17 of 104 decode today"* -- 84% blind, in a comment, in
the assertion message, committed. Nobody drew the conclusion. **A self-reported coverage number is
not a safeguard unless something ACTS on it.** A screen that knows it is partial must say so on a
GREEN run (`warnings.warn`, not `print` -- stdout is captured), and a coverage floor should be a
ratchet you are made to justify, not a number that only fires when it gets worse.

**12. A CORRECT WIRE IS NOT A CORRECT FEATURE. Measuring upstream of the game measures nothing.**
The 2026-07-29 lesson, and the most humbling here because the data was *good* the whole way down.

> A player reported three times that no rune in any shop was ever priced below its value. The
> generator's roll is `randint(0, 2 x worth)`; measured over three seeds it was a clean uniform --
> median 1.03, 50% below worth, minimum 0.002x. I extracted his ACTUAL seed and read the slot_data
> out of the multidata: 117 rune slots, 38% below worth, a Golden Rune [5] priced at **4 runes**. I
> matched two prices from his screenshot to their exact ShopLineupParam rows, proving the client
> applied what we sent. Every measurement I could take said the feature worked.
>
> I told him it was a sampling artifact. He said it again. I found a second pricing path with a real
> 10x bug, fixed it, told him again. He said it a third time.
>
> The client's `shop_stock::reset()` was never called. A map load streams the param back in and
> reverts our writes; the module latches `DONE` after one pass, so the 455 rerolled rows applied
> once on connect and were gone for the session. Every below-value price in the seed lived in that
> table. His observation was not noisy -- it was **exact**.

**The generator being right is not the feature being right, and a seed file is not a screen.** Every
number I produced was true and none of them were evidence about the thing being reported.

- **When a report survives your explanation, the report wins.** A second identical report should
  move your prior off your own analysis; a third should end it. The person watching the game is the
  only one seeing the output. "Unlucky sample" is the hypothesis to reach for LAST, because it is
  unfalsifiable from where you are standing.
- **Trace to the last stage you can observe, then say which stages you did not check.** "slot_data
  is correct; I have not verified the client applies it per load" was writable on day one. That
  sentence is the whole bug.
- **A `reset()` with no caller is a predicate with no caller** (see *Regression by replay*). Same
  shape one level down, and it has cost three features: `shop_sell` (2026-07-24, found in playtest),
  `shop_icon` and `shop_stock` (2026-07-29). `test_gf_client_resets_are_called` makes it mechanical.
  Three times is a class, and a class gets a gate.

**13. A spec's acceptance list is a TO-DO LIST until something checks it.**
The 2026-08-01 lesson, and the cheapest to prevent.

> `SPEC-global-scadutree-blessing` shipped with ten acceptance criteria, five automated and five
> in-game. A month later, an audit found **five of the ten missing or partial**. One had never been
> built at all: the fragment INJECTION the whole feature's cap exists to bound. The cap shipped, the
> injection did not, and nothing noticed -- so at the shipped default only **1 seed in 40** could
> reach the cap the option advertises.

Note the shape, because it was the same in every case: **the half of each bullet that needed a NEW
test tier is the half that did not land.** The contract key shipped (an existing pattern). The
options rejection did not (nothing to copy). The floor Policy shipped; the cap Policy, which needed
a new term in the replay model, did not.

- **A merged spec's acceptance list belongs in a tracking issue, pasted verbatim, one checkbox per
  line.** Prose in `docs/specs/` is not a gate; nothing reads it and nothing goes red.
- **State shipped / partial / absent per line, with the command or file that proves it.** "Partial"
  is the answer that matters -- it is what "shipped" degrades into when the easy half lands first.
- **The bullets that need a new test tier are the ones to build FIRST**, precisely because there is
  no existing pattern to copy and therefore nothing to make their absence obvious.

**14. The release notes are part of the CHANGE, not part of the release.**
The 2026-08-02 lesson, and the only one here that destroys its own evidence as it happens.

> v0.3.0 shipped 2026-08-01. By the next morning `main` carried five more player-visible fixes --
> two of them straight off Nexus bug reports -- with **no v0.3.1 changelog section and no blurb**.
> There was no `BLURB-v0.3.0.md` either: the blurb series had quietly stopped at v0.2.18, five
> releases back, and nothing anywhere said so because nothing anywhere was looking.
>
> Reconstructing the notes took a walk of `v0.3.0..main` plus four commit bodies. A commit body
> answers *what I changed*. A release note answers *why it mattered to you*, and that answer existed
> exactly once -- in the head of the person who landed the fix, on the day they landed it.

**The moment a fix lands is the only moment anyone knows why it mattered.** Everything after that is
reconstruction from a diff: lossy, expensive, and paid for by whoever is least able to pay -- someone
reading four commit bodies at tag time to guess at a sentence the author could have written in
fifteen seconds. That reconstruction cost is what killed the blurb series. Nobody decided to stop
writing blurbs; the price of starting one just kept going up until it was always tomorrow's job.

- **Every player-visible change lands its CHANGELOG line in the SAME commit.**
  `release-v0.2/CHANGELOG.md` (historical directory name -- it holds v0.3.x too), under the current
  `## v<version> — <date>` heading. Not "before the tag", not "when the window closes": the same
  commit, because that is the only commit whose author has both the change and the reason.
- **The blurb is drafted as the window FILLS, not at tag time.**
  `release-v0.2/BLURB-v<version>.md` opens on the first change of a version and grows with it. A
  blurb written from scratch afterwards is the reconstruction above, wearing a deadline.
- **Per rule 13's own logic, the two bullets above are a to-do list until something checks them.**
  `tools/check_release_notes.py` is that something: AP-free, wired into CI and `run_ci.ps1`, red the
  moment `APWORLD_VERSION` names a version with no changelog section, an EMPTY one (rule 2), or no
  blurb. It carries a documented ratchet of pre-gate exemptions -- currently v0.3.0's missing blurb,
  and only its blurb. Nothing may be added to that set: an exemption you can extend is a gate you
  have switched off.

### The tell

When a number looks wrong, **do not reason about it. Instrument it.**

Shops resolved 78 distinct flags where 410 were expected. Three rounds of plausible theories produced
three wrong answers. One log line — a tally of *why* each row was skipped — produced the truth in a single
run. `resolved.len()` had been counting **locations**, not flags, and had been read as flags for three
messages straight.

**Log DISTINCT counts, not totals. Log why things were skipped, not just that they were.**

## Provenance — derive the datum, don't pin the symptom

A bug report is a *symptom*. The fix is not to add the symptom to a list; it is to find the **datum
the game already knows** and derive the answer from it. The game ships the truth in its params,
EMEVD, MSBs and FMGs. If we are guessing, we have not looked hard enough.

**A guess wearing the costume of a fact is the failure mode.** Two shipped bugs, same shape:

* `tile_pr()` is a nearest-neighbour -- it **never fails**. Hand it a coarse LOD tile and it returns
  a confident, *wrong* region. Six checks landed in the wrong region; one was culled with a sealed
  region and the player picked up the vanilla item in Limgrave, with the client logging nothing.
* HUB-quarantining a check whose region we couldn't resolve was justified as *"reachable-from-start,
  never a false gate."* It is the opposite: it asserts a reachability we do not have, and fill put a
  region Lock on it. Unwinnable seed.

**Refusing to answer beats answering confidently wrong.** If the region is unknown, say so
(`DEFAULTED_REGION_APS`) and bar it from carrying progression.

### When the data contradicts the model, the MODEL changes

**Messmer's Kindling went missing from the pool.** The generator modelled checks as **one event
flag, one check**. The game does not work that way: a flag can award **several** item lots, so a
flag with N meaningful items is N checks. Under a 1:1 model every sibling but one is silently
dropped, and a key item is one unlucky draw from vanishing. Nothing errored -- the seed genned and
the item simply was not there (Rule 6).

The proposed fix was **"rank key-item drops higher"** so the survivor would be the Kindling. It
would have worked. On that flag. That is the entire problem:

> **A fix that re-ranks, prioritises, or special-cases the item that happened to break is a hand pin
> wearing an algorithm's clothes.** It buys back the one symptom you know about, leaves the wrong
> model in place still dropping every sibling you *haven't* noticed, and now with a heuristic on top
> that looks like a deliberate design decision.

The real fix changes the shape of the model to the shape of the data: **N co-firing checks per
shared flag**, with the meaningful/junk split taken from a param the game already ships
(`EquipParamGoods.isDiscard`), not a curated list of item names. Bigger diff, no whack-a-mole, and
it fixes the siblings nobody reported.

So when a check, a count, or an item comes out wrong, ask **in this order**:

1. **What does the game datum actually look like?** Not "what value should I set" -- what is the
   *cardinality and shape*? (one flag → many lots; one lot → many items; two id spaces; two map
   versions.) Most of this file's worst bugs were a model with the wrong arity, not a wrong constant.
2. **Does my model have that shape?** If not, changing the model IS the fix.
3. **Only if the derivation genuinely cannot reach** the datum may a hand entry exist -- under the
   redundancy hard-error below.

### Constraint ownership — say who owns it before you obey it

The same incident produced a worse artefact than the bad fix. Working from the 1:1 model, the agent
**handed the task to a subagent with "checks must stay one-to-one" as a HARD CONSTRAINT.**

That rule was never a constraint. Not the game (it shares flags across lots), not Archipelago (happy
with N locations per trigger) -- **ours**, undocumented, probably accidental. Promoting it to a
requirement in a handoff makes the actual fix *unreachable* for the next worker, who must violate
their brief to be right and cannot tell an inherited guess from a real invariant.

- **Before you design around a constraint, name its owner: the GAME, ARCHIPELAGO, or US.** Only the
  first two are non-negotiable, and both are checkable -- cite the param/EMEVD row or the AP API. If
  the answer is "us", it is a design choice on the table and the right move may be to delete it.
- **Never hand an unowned assumption to another agent (or a future session) as a constraint.** Write
  it as what it is: *"current code assumes 1:1 flag→check; I have not verified that this is
  required."* A handoff is where assumptions get laundered into requirements, and a subagent cannot
  audit a premise it was told to hold fixed.
- **A constraint that makes the bug unfixable is evidence the constraint is the bug.**

### A REDUNDANT MANUAL OVERRIDE IS A FAILURE

Hand lists are allowed **only** where the derivation genuinely cannot reach. The moment the
derivation catches up the hand entry must be **deleted** -- and the only way that reliably happens
is if leaving it in **fails the build**.

A redundant override is not harmless belt-and-braces. It is a **lie about why the code works**: the
next reader cannot tell which entries are load-bearing, so nobody dares delete any, and the crutch
calcifies into permanent scar tissue.

So `gen_data` **hard-errors** on overlap between a hand list and the set that derives it. This has
fired for real: re-mining boss drops against all 589 EMEVD (54 → 88 flags) made 4 of the 7
`_BOSS_DROP_EXTRAS` redundant -- exactly the drops hand-added *because the scan, then reading only
380 EMEVD, could not see them*. Deleted. `TAG_COUNTS["Boss"]` stayed 93, which is the proof.

**But only delete where the derivation is COMPLETE:**

| derivation | complete? | hand list |
|---|---|---|
| boss drops (all 589 EMEVD, no other dependency) | ✅ | must be empty of redundancy -- **hard error** |
| arena graces (needs an unpacked MSB; 66 of 118 boss maps have one) | ❌ **lower bound** | a real safety net -- **keep**, and guard the floor |

For an incomplete derivation the hazard runs the other way: re-run the tool without its inputs and
the derived set silently *shrinks*, taking real coverage with it. Guard that too (`_ARENA_FLOOR`) --
a shrinking oracle must fail loudly, not quietly stop protecting you.

### Stale inputs are the same bug wearing a different hat

A derivation is only as good as what it read. `boss_drops` and `boss_healthbars` were mined when
**380 of 589** EMEVD were decompiled -- ~35% of the game's award sites invisible, unnoticed for
weeks because the numbers *looked* plausible. When a derived count moves, the first question is
**"did an input get better?"**, not "what should I set the constant to." A count that grows because
ground truth improved is fine; a count that grows because a predicate got looser is a bug.
**Rebaselining without answering which one it is, is how you launder a regression into a test.**
