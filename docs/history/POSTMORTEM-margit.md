# Postmortem: why Margit's boundary survived repeated fixes

This postmortem was prompted on 2026-09-01 by Lew's report: the Castleward Tunnel grace was granted with Stormveil, but warping to it or entering Margit's fight could trigger a region kick. The repository evidence below was rechecked against `09882a06` and current main. Player testimony is identified as testimony rather than treated as a measured bucket.

## Follow-up: the ledger still missed the raw runtime ID (2026-09-15)

Pacificator66 reported another instant Roundtable ejection on entering Margit's intro with
Stormveil as the starting region. The ledger introduced after this postmortem checked all five
ownership tables, but did not execute the kick decision with asymmetric locks.

The earlier claim that Margit's fighting ground could not be separated from Stormhill was wrong.
The committed `gen_inputs.db` → `PlayRegionParam.csv` has distinct rows: `6101000` is ordinary
Stormhill (`pcPositionSaveLimitEventFlagId = 6001`), while `6101010` names Margit's defeat flag
`10000850`. An [August 11 kick-watch witness](https://github.com/4laric/er-archipelago/issues/523#issuecomment-5258517666)
already recorded `6101010 -> 1000001` after Margit's death. That session also loaded Matt's
randomizer, so it is historical runtime evidence, not a fresh vanilla reproduction.

The client discarded the distinction with integer `/100`: both raw rows became Limgrave bucket
`61010`. The ledger's Stormveil bucket `10000` therefore passed without testing the actual arena
input. Exact raw-ID adjudications now feed the shared runtime resolver, before coarse folding;
ordinary Stormhill keeps its original owner. The generated Rust witness calls the real kick and
lock-name functions with the owner alone open and alone closed. A separate Python witness joins
the arena raw ID to the boss flag in the committed game params, so a typo cannot pass merely by
landing in the right coarse bucket. The new Rust test failed on the old resolver for
`6101010: owner alone open` before the fix and passes with it.

This fixes the demonstrated arena classification error. The current report has no kick-watch
line, and this change has not been playtested in a live game. Castleward Tunnel's exact runtime
transition and the separate Tower Bridge case remain distinct from that evidence; #202 must not
be closed on this fix alone. The [actual superseding ruling](https://github.com/4laric/er-archipelago/issues/523#issuecomment-5317407211)
is dated August 17; the ledger previously linked a different comment ID and date.

## The one-sentence version

"Where is Margit?" was answered independently by check ownership, sweep ownership, kick geometry, grace bundles, and boss/arena tables; the project first recorded one ruling only in issue prose, later reversed it in a focused kick-geometry test, but never required all affected representations to agree with the active ruling.

## The representations at `09882a06`

| representation | keyed by | recorded answer |
|---|---|---|
| Talisman Pouch check `f60510` | `region_of()` ladder | **Limgrave** |
| Margit sweep triggers `10000800` / `10000850` | raw boss map | **Stormveil** |
| sweep annotations on nearby checks | boss map | **Stormveil** |
| arena and Castleward Tunnel bucket `10000` | shipped `region_play_ids.py` | **Stormveil** |
| Stormhill cliff bucket `61010` | shipped `region_play_ids.py` | **Limgrave** |
| Castleward Tunnel grace `71002` | `region_graces.py` | **Stormveil** |
| Margit's arena grace `71001` | `region_graces.py` | **unbundled** |

The split between bucket `10000` and the surrounding Stormhill cliff is deliberate: the cliff shares a coarse overworld tile with early Limgrave checks. The unintentional problem is that the other representations were not all pinned to the same adjudication. Lew's runtime kick report shows that a shipped configuration still exposed a disagreement, but the report did not include the kick-watch line, so it does not by itself prove which bucket acted.

## Timeline

- **2026-07-24 — #202:** the issue recorded “Margit is OUTSIDE” and described both kick and warp representations. That decision existed only in prose.
- **2026-08-17 — #803:** the Divine Tower / Tower Bridge mirror case was changed and the commit said it closed #202, while the Margit case remained independently observable.
- **2026-08-21/22 — #523:** the operator ruling was explicitly reversed. Commits `f6d89ce2` and `06ac88da` added an executable witness that bucket `10000` (Castleward Tunnel and Margit's arena) is Stormveil, while bucket `61010` (the Stormhill cliff) remains Limgrave.
- **2026-09-01:** Lew reported the mixed-lock symptom again. At `09882a06`, check ownership and grace coverage still disagreed with the active Stormveil model even though the focused kick-geometry test was green.

## Why the defect survived

1. **A local witness was mistaken for a class witness.** The #523 test correctly pins kick geometry, but cannot detect disagreement in check ownership, sweep ownership, grace bundling, or tracker presentation.
2. **The original ruling was prose.** Nothing executable recorded the July decision, so later derivations could overturn it silently. The August reversal improved this for one representation only.
3. **Seams make “the region” representation-specific.** Coarse ground tiles, arena maps, warp ids, and item lots do not share the same boundaries. Deliberate splits are sometimes necessary, but they must be explicit.
4. **A partial fix claimed a whole issue.** #803 addressed the mirror case without witnessing every case named by #202.
5. **The symptom needs asymmetric locks.** Everything-open testing hides it. One side locked at a time must be a standard seam witness.
6. **The runtime report lacked the bucket datum.** Without the kick-watch line, a faithful symptom still requires another investigation before it can adjudicate geometry.

## Corrective actions

- Record every boundary ruling in executable data or tests, with its issue, date, and operator decision.
- State which representations the ruling governs and witness each one. A kick-geometry test does not settle check or grace ownership.
- Pin deliberate splits explicitly, including both sides of the split.
- Test each seam with either side locked alone.
- Do not use “Closes #N” on a multi-case issue until every named case is witnessed, or split the issue first.
- Ask region-lock reporters for the kick-watch line: `play_region <raw> -> <folded>; range [a,b] flag F`.

## What went right

The generated artifacts and focused tests made the disagreement auditable. The #523 witness also preserves an important, non-obvious truth: Margit's arena and tunnel are Stormveil while the adjacent Stormhill cliff remains Limgrave. The process gap was not a lack of evidence; it was the absence of a rule requiring one adjudication to be carried across every representation it was intended to govern.
