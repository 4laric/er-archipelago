# SPEC — Closing the correspondence gap: three test tiers for semantic correctness (2026-07-06)

Postmortem + forward plan for a specific question: *why has every greenfield bug since
the arch-review fixes been found one-at-a-time in live playtest, and what changes that?*

Synthesis of the Opus main-thread diagnosis and an independent Fable 5 review. Where they
disagreed, Fable's correction is adopted and marked **[Fable]**.

---

## 1. The diagnosis: we fixed *absence*, the residue is *wrongness*

The arch-review fixes hardened the gen→client contract seam: emission is contract-gated,
features announce "armed with N / inert because X" at connect, shapes are validated on both
sides. That closed the failure class where **nothing happens** — a missing key, a wrong path,
a dark feature.

The dozen bugs since are a different class. Map_lot pickups mislabeled to the hub, weapon
shop slots granting the vanilla good, Torch clobbered on load, flask double-grant on reload,
torrent mount missing on region-lock starts — none of these are absence-of-behavior. **The
feature is armed, the telemetry is green, and the behavior is still wrong.** Loud-arming
detects absence. It is blind to wrongness. So no amount of contract-tightening moves this
curve; we already catch everything the contract can catch.

**The gates check internal consistency; nothing checks correspondence to the actual game.**
"Does gen emit what the client reads," "are the shapes right," "is the seed winnable on
paper" — all internal. What no gate checks: does that flag really reveal that map, does that
location really sit in that region, does that grant really survive a save-load. The only
artifact with ground truth about the real game is the running game — so every semantic bug
first surfaces in-game, and each playtest walks one path through (topology × options ×
timeline). That is a random walk through a huge state space; defects appear at the rate we
step on them. One at a time is structural, not bad luck.

### The Fable correction that reshapes the fix

The naive move — "assert emitted data against the game's static files" — is **partly
circular**. `gen_data.py` already consults those files (EMEVD map-scan, grace anchors,
ShopLineupParam). The map_lot bug did not happen because game data was unconsulted; it
happened because a heuristic ignored a ground-truth column *already in its own input*
(`flag_source == 'map_lot'`). **[Fable]** *An oracle that shares its derivation code with the
thing it checks is not an oracle.* A real correspondence check needs either (a) an
**independent** source (e.g. MSB/ItemLot placement vs the region label `gen_data` derived), or
(b) a cheaper substitute: **output-distribution invariants** ("no map_lot row may land in the
hub"; "quarantine count ≤ budget") that would have screamed when HUB went 388→336.

And the vehicle matters — but here Fable was half-wrong and **[Alaric]** corrected it. Fable
called fuzzing "Windows-only, ~900s/case" because it reviewed `gen_fuzz.ps1`. But AP generation
is pure Python and **already runs on Linux**: `greenfield/ci-linux.sh` provisions a 3.11 venv and
runs the whole pipeline — data-drift, pure unit (`test_gf_data.py`), isolated `Generate.py`, the
WorldTestBase suite, and `greenfield/fuzz_gf.py` (a portable yaml-fuzz scorer, ~90s/gen). So a
semantic fuzz sweep on Linux CI is cheap and viable. The real decomposition is:

- **Option-INDEPENDENT semantic bugs** (map_lot label wrong in *every* seed) → a single
  deterministic assertion in `test_gf_data.py` (ci-linux.sh step **b**). Don't fuzz what one test
  proves. *(This much of Fable stands.)*
- **Option-DEPENDENT semantic bugs** (only appear under some num_regions/DLC/shuffle combo) →
  need option-space coverage, and that is cheap here because gen is Python. The gap is narrow:
  `fuzz_gf.py`'s oracle today is **fill/crash only** (SUCCESS/REJECT/FILLERROR/HANG/CRASH). Add a
  **post-gen semantic assertion pass** — open the emitted `AP_*.zip` slot_data + placement and run
  the Class A/B invariants — so the existing sweep also catches semantic wrongness.
- **Free coverage for Class B:** the contract validator is already wired into `fill_slot_data`, so
  any cross-side invariant added to `contract.py` (§Class B) fires inside *every* fuzzed gen and
  shows up as a CRASH in `fuzz_gf.py` with no harness change at all.

---

## 2. Three bug classes → three currently-untested layers

| Class | Example bugs | Ground truth lives in | Currently tested? |
|---|---|---|---|
| **A. Data-value-wrong** | map_lot region label; region mislabels | the game world (MSB/ItemLot placement); its own output distribution | No — only shape/presence |
| **B. Cross-side semantic contract** | weapon shop slot leaks vanilla good | *neither* codebase alone — the two sides' assumptions conflict | No |
| **C. Grant sequencing / timing** | Torch clobber, flask double-grant, torrent mountless | the live game's state timeline (menus, load, clobber) | No — this glue has zero host tests |

The migration didn't just break the contract seam. It exposed that the whole **correctness
stratum** — data distribution, cross-side meaning, grant sequencing — was only ever tested by
the running game.

### Class A — data-value-wrong → gen-side invariants + independent cross-check

Fix in `greenfield/eldenring_gf/tests/test_gf_data.py` (ci-linux.sh step **b**, `run_ci.ps1`
greenfield gate; deterministic; runs on Linux under the provisioned 3.11 venv):

1. **Output-distribution invariants** (cheap, do first): assert region-membership counts stay
   within tracked budgets; assert no `map_lot`/overworld pickup lands in the hub; assert the
   quarantine set is empty for placed-tile items. These catch a *shift* even when we don't
   have an independent per-item oracle. Option-independent → deterministic test, not the fuzzer.
2. **Independent cross-check** (where a second source exists): diff the region label
   `gen_data` assigned against the MSB/ItemLot tile the item physically occupies (in
   `elden_ring_artifacts/`: `mapstudio/`, `m10_00_00_00-msb-dcx`, regulation params via
   `WitchyBND`). Independence is the whole point — do **not** re-run the same EMEVD scan
   `gen_data` used, or the check inherits the bug.
3. **Option-dependent invariants** → add a post-gen semantic pass to `greenfield/fuzz_gf.py`
   (already in ci-linux.sh step **e**): after each fuzzed `Generate.py`, open the emitted
   `AP_*.zip` slot_data and assert the same invariants across the swept option space.

### Class B — cross-side semantic contract → executable invariants in `contract.py`

The weapon-shop leak is not a game-data problem; the game data is consistent. Gen violated a
constraint only the **client** knows (`SHOP_CTD_GUARD` skips weapon→non-weapon rows). This is
the contract seam going one layer deeper — from validating *shape* to validating *meaning*.

Add executable cross-side invariants to `greenfield/eldenring_gf/contract.py`, checked at gen
time against the emitted slot_data + `ShopLineupParam`: e.g. "every weapon-row shop slot's
placed item is itself a weapon." Each such invariant is a client assumption made executable on
the gen side. Harvest them by grepping the client for every silent guard/`unwrap_or` and
asking "what does gen have to guarantee for this to be safe?"

### Class C — grant sequencing / timing → headless replay harness + framework enforcement

**[Fable] This is the biggest hole, and no gen-side oracle will ever touch it.** All four
timing bugs live in `crates/eldenring-archipelago/src/{core,detour}.rs` — the live-crate glue
— which has **no `tests/` directory**, while `crates/er-logic` (pure decisions) does. The
pure/live split drew the test boundary at "pure function," so all grant *sequencing* sits in
untested glue.

Two moves:

1. **Headless client replay harness.** Feed a real seed's slot_data through the
   grant/shop/startgrant paths against a *fake game-state model* — a flags map plus injected
   menu / load / save-clobber / reconnect events. This catches Torch, flask, and torrent
   offline. It is the missing test tier under the largest untested surface.
2. **Framework-level reconcile.** `CONTRIBUTING.md` already mandates "Reconcile, don't
   dispatch — never advance a cursor past a write you didn't verify landed." The timing bugs
   are violations of house law fixed one at a time. Make the grant framework *enforce*
   reconcile-until-observed for **every** grant, so the whole class dies at once instead of
   Torch, then flask, then the next thing.

---

## 3. Priority

1. **Class C — headless replay harness + reconcile enforcement.** Largest untested surface;
   the timing class can *only* be caught here; kills multiple latent bugs per fix.
2. **Class B — cross-side semantic invariants in `contract.py`.** Cheap, and it converts silent
   client guards into loud gen-time failures — the same "declare the meaning, not just the
   shape" move that closed the options-subdict incident, one layer deeper.
3. **Class A — output-distribution invariants**, then independent-source cross-checks where a
   second source exists. Put them in `test_gf_data.py`, **not** `gen_fuzz`.

## 4. What each tier will NOT catch (honesty)

- Class A invariants catch *shifts* and gross mislabels, not every subtly-wrong single item
  unless an independent oracle exists for it.
- Class B catches assumption conflicts we've *thought to encode*; an un-encoded client
  assumption is still invisible. Drive the list from a client-side audit of guards.
- Class C's harness is only as good as the game-state model; a real-game behavior we don't
  model (a clobber trigger we haven't seen) still escapes to playtest. It shrinks the
  playtest surface; it doesn't eliminate it.

The meta-point: the discovery curve doesn't move by adding one oracle. It moves by putting a
test tier under each of the three correctness layers that currently has none — with the
headless grant-path harness first, because that's the biggest dark surface and the one no
offline data oracle can ever reach.
