# Plan: parallelize the arch-review fixes across Fable agents

**Date:** 2026-07-06 · Source: `FABLE-ARCH-REVIEW-FINDINGS-20260706.md`
**Division of labor:** Fable agents own all **greenfield Python** work and **self-validate** it with
`bash greenfield/ci-linux.sh` (provisions its own venv + AP runtime in the Linux sandbox — gen +
world tests + fuzz, no Windows). **Alaric owns client `cargo build`/`test`** (now has WSL/Ubuntu on
the laptop too). Fable may touch generated `.rs` output but never compiles it — that's the handoff line.

## The four findings → who fixes what

| # | Finding | Side | Fix owner |
|---|---|---|---|
| F1 | Client reads `sd["options"][...]` sub-dict; greenfield emits keys **top-level** → death_link, no_weapon_reqs, DLC map-reveal, scaling, scadutree, upgrades all silently dark | greenfield only (client already reads correctly) | Spine agent |
| F2 | Validator doesn't gate: `contract.py:246` ignores unknown keys, `registry.py:70` merges any → "slot_data OK" while features dark | greenfield | Spine agent |
| F3 | Completion scaling inert: client reads `regionSphereTargetRanges` (no producer); greenfield emits `regionSphereTargets` (region-name+float, unparseable) | greenfield emit + client spec | Scaling agent |
| F4 | `tracker_regions.rs` generated from OLD apworld 7,000,000 id space → tracker shows "(unknown region)" under greenfield | `tools/gen_location_regions.py` (Python) + regenerated `.rs` (Alaric compiles) | Tracker agent |

## Why it parallelizes cleanly — file ownership is disjoint

The clobber risk (see the "parallel shared-doc clobber" rule) is entirely in three **spine** files:
`greenfield/eldenring_gf/contract.py`, `core.py` (fill_slot_data), `registry.py`. **One agent owns
those exclusively.** Everyone else owns non-spine files:

- Spine agent → `contract.py`, `core.py`, `registry.py` **only**
- Scaling agent → `features/scaling.py` + a client spec `.md` (no client edit)
- Tracker agent → `tools/gen_location_regions.py` + its generated `.rs` (Alaric compiles)

The one coupling point — new key *declarations* — all live in `contract.py`, owned by the spine
agent. Scaling/Tracker agents **hand their required declarations to the spine agent via the frozen
delta doc** (below); they never edit `contract.py` themselves. No two agents write the same file.

---

## Wave 1 — Recon (2 Fable agents, parallel, READ-ONLY, zero conflict)

**R1 — Contract reconciliation.** Enumerate (a) every slot_data key the client reads across
`crates/er-logic/src/*` + `crates/eldenring-archipelago/src/*` with file:line, whether it's read
top-level or under `sd["options"]`, and expected shape; (b) every key greenfield emits, its producer
file, and shape. Output a gap table: keys the client wants but greenfield doesn't emit (or emits at
the wrong nesting/name). → `RECON-contract-keys-20260706.md`

**R2 — Tracker + scaling deep-dive.** (a) F4: document greenfield's actual ap_id space (from
`eldenring_gf/data.py`) vs the 7,000,000 space `tracker_regions.rs` was built on; specify exactly how
`tools/gen_location_regions.py` must be re-pointed to source greenfield's `data.py` +
`region_open_flags.py` instead of `Archipelago/worlds/eldenring/`. (b) F3: quote the exact struct the
client parses in `crates/er-logic/src/scaling.rs` (~150-165) and write the exact greenfield emission
shape needed. → `RECON-tracker-scaling-20260706.md`

**Serial reconcile (Opus):** merge R1+R2 into one frozen **`CONTRACT-DELTA-20260706.md`** — the single
authoritative list of key names/shapes/nesting for Wave 2. This is the anti-clobber handshake.

## Wave 2 — Implement (3 Fable agents, parallel, disjoint files)

**I1 — Spine** (`contract.py` + `core.py` + `registry.py`): (1) add a central `sd["options"] = {…}`
echo built from the world's options object, covering every option key R1 found the client reads under
`options` (fixes F1 for all of them at once); (2) make the validator strict — reject any emitted key
not declared in `contract.py`, and fail gen if any declared-required key is missing (fixes F2);
(3) declare every key from `CONTRACT-DELTA` including the scaling range key. **Validate:**
`bash greenfield/ci-linux.sh` must stay green (fuzz gate will catch over-strict rejections).

**I2 — Scaling** (`features/scaling.py` + spec md): emit `regionSphereTargetRanges` in the shape from
R2; hand the key declaration to I1 via the delta doc. Write `SPEC-client-scaling-20260706.md` noting
whether `scaling.rs` needs any change (likely none if greenfield now emits the expected shape).
**Validate:** run `ci-linux.sh`; confirm the key appears in a generated seed's slot_data.

**I3 — Tracker** (`tools/gen_location_regions.py` + regenerated `tracker_regions.rs`): re-point the
generator at greenfield's data, regenerate the `.rs`, sanity-check the id space now matches
greenfield. **Do NOT cargo-build** — leave the regenerated `.rs` for Alaric. Write
`SPEC-client-tracker-20260706.md` listing what Alaric must `cargo build`/`test` to confirm.

**Serial merge (Opus):** I1 owns `contract.py`; if I2/I3 produced declaration deltas, Opus applies
them to `contract.py` after I1 lands (or folds them into I1's brief up front so I1 declares them in
one pass — preferred). Run `ci-linux.sh` once more on the merged tree.

## Handoff line to Alaric (client cargo)

After Wave 2: (1) `cargo build`/`test` the regenerated `tracker_regions.rs`; (2) confirm a live
greenfield connect now logs real regions + fires the previously-dark features (death_link, scaling,
weapon_reqs, DLC map-reveal). Everything greenfield-side is already gen-verified by the agents.

## Fable run notes
- model `fable`, tiny context — each agent gets the delta doc + its file list, not the whole repo.
- every agent ends with the required back-to-Opus block (path written, one-line verdict, ci-linux
  result, anything needing Alaric's cargo).
- Fable can be out of credits → fall back to Opus for that agent.

## Sequencing summary
Wave 1 (R1‖R2) → Opus reconcile → Wave 2 (I1‖I2‖I3, each self-validates via ci-linux.sh) → Opus
merge + final ci-linux.sh → Alaric cargo confirm.
