# SPEC — wake the cross-side contract gate, and deal with what it finds

**Status:** teed up 2026-07-28, nothing built. Written while the context was warm, by the session
that moved the tracker's region model into slot_data (`697ed00` / client `b102e91`) and tripped over
this on the way past.

**One-line version:** `test_gf_client_contract_paths.py` has never run in CI, and when you run it
it is RED with 10 orphan read-paths — three of which are **client features our seeds can never turn
on**.

---

## 1. Why the gate is dormant — it is one word, and it is not the bug

The gate parses the CLIENT Rust for every `slot_data` read-path and asserts each is DECLARED in
`contract.py`. An undeclared read is a *dark feature*: the client `.get()`s a key nobody emits,
falls back to a default, and gen reports a clean contract. It exists because that is exactly how the
options-subdict gap shipped (`auto_upgrade` and friends emitted top-level, read under
`/options/…`, every one inert while the contract validated green).

It runs in neither CI job, for two different reasons:

| job | client source present? | gate invoked? | result |
|---|---|---|---|
| `generators` | **yes** — `.github/workflows/tests.yaml:146` checks the client out to `from-software-archipelago-clients/` | **no** — the loop at line 177 is `for t in check_browser desc_triage provenance_gate questline_dag` | never runs |
| `tests` | no — `gf_test.py --install-only` installs the world into `_ap/worlds/eldenring` with no `crates/` beside it | yes, via pytest | `setUpClass` raises `SkipTest` |

So it skips in one job and is not called in the other. **Adding `client_contract_paths` to the
`generators` loop is the entire wiring fix** — the client is already checked out there and
`CRATES` resolves.

🛑 Do that LAST. It goes red immediately; §2 is the work.

> **Correction to an earlier note.** A previous session recorded this as "one of the orphans has a
> TRAILING SPACE = scanner bug". That is **wrong**, and it matters because it made the whole list
> look like tooling noise. The trailing space is in the CLIENT SOURCE, deliberately, with a comment
> (`key_resolver.rs:126-127`): it reads `"locationIdsToTargets"` and then
> `.or_else(|| sd.get("locationIdsToTargets "))` because some producer emits the key with a trailing
> space. The scanner is reporting the source faithfully.

## 2. The 10 orphans, triaged — three buckets, and only one of them is a gate problem

Reproduce (from a repo checkout with the client cloned to `from-software-archipelago-clients/`):

```bash
python greenfield/eldenring/tests/test_gf_client_contract_paths.py
```

### Bucket A — 🔴 THREE CLIENT FEATURES OUR SEEDS CANNOT TURN ON. This is the find.

`er-logic/options.rs` reads three option sub-keys, and `core.rs` **arms a real feature off each**:

| option read | armed at | world option |
|---|---|---|
| `options.no_equip_load` | `core.rs:660 no_equip_load::set_enabled(...)` | **none** |
| `options.no_fall_damage` | `core.rs:662 no_fall_damage::set_enabled(...)` | **none** |
| `options.auto_equip` | `core.rs:669 auto_equip::set_enabled(...)` | **none** |

The apworld defines no option of any of those names (`options.py` + every `features/*.py`). So all
three are permanently `false` for every greenfield seed — shipped code, wired, armed, and
unreachable. There are whole modules behind them (`auto_equip.rs` in both crates,
`no_fall_damage.rs`, `no_equip_load.rs`).

And two of them carry a client doc-comment asserting the opposite:

> `/// options.no_equip_load (int-or-bool). Same option name on both our apworld and Bedrock/fswap's.`
> `/// options.auto_equip (int-or-bool). Same option name on both our apworld and Bedrock/fswap's.`

That is a false claim in a comment, which CONTRIBUTING rule 10 says must have a test that fails when
it stops being true. **This gate IS that test** — it has just never been switched on.

**Decide per feature, and it is a design call, not a cleanup:** either add the option to the apworld
(these look like desirable QoL — no fall damage, auto-equip, no equip load) or accept them as
Bedrock-only and declare them under the `bedrock` profile so the gate stops calling them orphans.
🛑 Do not "fix" this by adding ALLOW entries: that buries three features nobody can use.

### Bucket B — 🟡 Bedrock swap-target keys, declared inconsistently

Four top-level reads, all foreign-apworld interop, none emitted by greenfield:

| key | read at | note |
|---|---|---|
| `goal` | `goal.rs:101` | Bedrock's `"goal": [boss.flag …]`. Greenfield emits `goalLocations` (declared, BOTH). |
| `graceItems` | `region.rs:154` | Bedrock's grace-rando. Greenfield emits `regionGraces` (declared). |
| `locationIdsToTargets` | `key_resolver.rs:126-127` | **sibling of `locationIdsToKeys`, which IS declared** as a bedrock key. One of the pair was declared and the other was not. |
| `regionAttunement` | `core.rs:1097` | parsed by `parse_region_attunement`; greenfield emits nothing. |

The profile system already exists for exactly this — `contract.py` declares bedrock keys and the
gate reports them separately as "declared, greenfield-inert" rather than as orphans. These four
simply were not declared. **Cheapest correct fix: declare them `(BEDROCK,)` with a one-line doc.**

### Bucket C — 🟡 The trailing-space key, which is a real producer bug somewhere

`locationIdsToTargets ` (trailing space) is read only as an `.or_else` fallback. Questions for
whoever picks this up, in order:

1. **Whose producer emits it?** If it is Bedrock's, that is an upstream bug report
   ([[bedrock-apworld-interop]] — read to cross-check, never ingest).
2. **Can the workaround be retired?** The comment says "exact name first so a future fix wins", so
   the intent was always to delete the fallback once upstream fixes it.
3. Until then it needs an ALLOW entry **with the justification written down** — this is the one
   orphan for which ALLOW is the honest answer, because the key is deliberately misspelled.

## 3. Suggested order

1. Triage bucket A **with Alaric** — it is a product decision (three QoL features, ship or disown).
2. Declare bucket B under the `bedrock` profile.
3. ALLOW bucket C with its justification, and file the upstream question.
4. **Then** add `client_contract_paths` to the `generators` loop in `tests.yaml:177` — one word.
5. Re-run and confirm the only remaining output is the "declared, greenfield-inert" report.

## 4. Rules of engagement

- **A gate that skips is not a gate.** The whole point of this file is that a green CI run said
  nothing about the cross-side contract for as long as it has existed. Do not close this by making
  the gate quieter; close it by making it run.
- **ALLOW is a last resort with a written reason.** It currently has zero entries and the docstring
  says so. Bucket C is the only candidate.
- **Do not delete a feature to silence the gate.** Bucket A is three working features missing their
  switch, not three mistakes.
- The gate reads the CLIENT at its own `main`, not the pinned gitlink — same as everything else in
  the `generators` job, so a stale submodule pointer cannot make it pass.
