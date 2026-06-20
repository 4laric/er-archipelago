# SPEC: test coverage strategy for er-archipelago

Status: draft 2026-06-14. Owner: Alaric. Scope: the whole superrepo (apworld, randomizer,
runtime client, libs). Goal: turn the current ad-hoc, manual-bake verification into a layered,
mostly-automated safety net — prioritized so the highest-risk, highest-churn surface gets covered
first.

## 1. Current state (what exists today)

There is **no coverage instrumentation** anywhere — no line-% is measured. This is a survey of test
*surface*: what suites exist, what they exercise, and whether CI enforces them.

| Component | Tests | Covers | Run / enforced |
|---|---|---|---|
| ER apworld (`Archipelago/worlds/eldenring/tests/TestER.py`) | ~5 ER methods + AP's generic per-world suite | location/item defs & uniqueness; region access/logic (Enia, equip chamber, loc access) | `pytest`; runs in AP `unittests.yml` CI |
| Runtime client C++ (`Dark-Souls-III-Archipelago-client/tests/`) | 4 host binaries (~33+13+7+19 checks): decode core & version check, goods-row offsets, `RecombineLocationId` vs 7 golden vectors, full gamehook decode through a fake param repo | item decode / param walk / id codec | `make test` — **manual only**; CI `test.yaml` just *builds* the mod |
| **SoulsRandomizers (C#)** | **none** | — | — |
| SoulsFormats / SoulsIds (libs) | none vendored here | — | — |
| nightreign-enemy-rando | test *data* + dev scripts only | — | — |
| Superrepo (root) | none | — | no root CI |

**Headline risk:** the C# randomizer — the largest, highest-churn component, and where every recent
bug lived (#7 volcano loop, the `GetSlotData` timeout, the stale-URL bake) — has zero automated
tests. The #7 fix was only validated by an ad-hoc Python port of the algorithm and by manual
`build.ps1 -LoopTest` integration runs; nothing in-repo guards a regression.

Secondary gaps: the C++ client tests are good but **not gated in CI** (a logic regression wouldn't
fail a PR), and end-to-end baking is covered only by manual `-LoopTest` runs.

## 2. Principles

- **Cover the churn, not the line count.** Prioritize code that changes often and breaks bakes
  (key-item logic, slot-data parsing, the id codec) over stable/vendored code.
- **Pure logic first.** Extract pure, dependency-free cores (graphs, exprs, decoders) and unit-test
  those; they run fast, deterministically, cross-platform, and pin behavior exactly.
- **Every fixed bug earns a regression test.** A test that fails on the pre-fix code and passes
  after — so the fix can't silently revert.
- **CI must actually run what exists** before adding more. An unenforced test is documentation.

## 3. Prioritized roadmap

### P0 — RandomizerCommon unit tests (in progress, this change)
The blind spot with the worst track record. Start with the two pure, already-public-ish cores:

- **`Expr`** (`AnnotationData.Expr`, public): `FreeVars`, `Needs` (AND=any / OR=all semantics —
  the exact property the #7 cut heuristic relies on), `Substitute`, `Simplify` (TRUE/FALSE
  absorption, dedup, flattening). Cheap, high-value: these are the primitives the whole logic graph
  is built on.
- **`CollapseReqs` cycle handling (#7)**: extract the cycle-cut + simplify into a pure
  `internal static CollapseReqs(SortedDictionary<string,Expr>, loops)` core and test it with
  synthetic graphs — including a graph that **crashed the old single-pass** (`a:(c OR d); b:a; c:b;
  d:b`) and now resolves, a volcano-shaped graph whose abduction branch must be cut, an acyclic
  no-op, and a genuinely unsolvable hard loop (asserts the existing "Unsolvable seed" throw).

Deliverable: `SoulsRandomizers/RandomizerCommon.Tests` (xUnit, net6.0-windows). Run via
`dotnet test` or `build.ps1 -Test`. Effort: ~half a day. **Done in this change for Expr + #7.**

### P1 — Enforce the C++ client tests in CI — DONE
Added a `host-tests` job (ubuntu-latest) to `Dark-Souls-III-Archipelago-client/.github/workflows/
test.yaml` running `make test` in `tests/`, alongside the existing Windows build job. The four host
suites (decode, goods-row, id-codec golden vectors, gamehook walk) now gate PRs. Verified green on
Linux (39+12+7+18). Caught a real issue en route: `walk_test` was stale after today's RE fix to the
`GoodsBlobFromRepo` deref chain (the header now derefs `+0x80` twice; the test still wired one hop) --
fixed the test to add the intermediate struct hop so all four pass.

### P2 — Grow RandomizerCommon coverage outward from the cores
Once the harness exists, add tests for the next pure-ish units, each ideally paired with a past bug:
- slot-data parsing in `ArchipelagoForm` (the GEM-nibble `unchecked((int)(uint))` overflow, the
  bool-only options filter) — extract the parse into a static helper taking a `JObject` and test it.
- `Expr.Flatten` / weight/`AdjustWeight` math if it keeps changing.
- region-gating logic (`world_logic: region_lock`) reachability invariants.

### P3 — Bake integration test (semi-automated) — DONE
`build.ps1 -LoopTest` now writes a timestamped `looptest_<ts>.log` (header + pass/fail table +
PASS/FAIL verdict), same pattern as `-Preflight`. It's wired into the pre-sync checklist
(SYNC-RUNBOOK §5) as a release gate: run a base-off + DLC-on batch, all must be `OK`. Can't run in
cloud CI (needs the game + Windows), so it stays a local pre-release gate / candidate scheduled task,
not a PR gate.

### P4 — apworld depth + nightreign — DONE (apworld; nightreign deferred)
Added `worlds/eldenring/tests/TestEROptionMatrix.py`: WorldTestBase classes for the shipping option
matrix (base-game region_lock, DLC region_lock, base-game open_world) that assert each config
generates a beatable seed (inherited reachability/fill), plus `ERSlotDataContract` asserting the
apworld↔randomizer↔client wire contract -- required keys, the `versions` range
(`>=0.1.0-beta.3 <0.1.0-beta.4`), parseable `apIdsToItemIds`/`locationIdsToKeys`, and that
`swap_multiboss`/`boss_runes_match` are suppressed under DLC. Verified: 18/18 pass (ran in-sandbox
via the ModuleUpdate 3.11-guard workaround; `pip install schema` needed there).
- nightreign: out of scope for the ER AP loop unless it re-enters active development.

## 4. What we explicitly do NOT test
- Vendored upstreams (SoulsFormats, SoulsIds, third-party `subprojects/`) — trust upstream.
- WinForms UI wiring, the live Archipelago socket, and on-disk game-file output (regulation.bin,
  *.dcx) — covered by manual bake + `-LoopTest`, not unit tests.

## 5. How to run (current)
- apworld: `cd Archipelago && python -m pytest worlds/eldenring/tests/` (Py 3.11+).
- client: `cd Dark-Souls-III-Archipelago-client/tests && make test` (Linux or MSYS2).
- randomizer (new): `cd SoulsRandomizers && dotnet test` or `build.ps1 -Test`.
