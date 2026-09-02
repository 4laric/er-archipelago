# Postmortem: why Margit's boundary survived repeated fixes

This postmortem was prompted on 2026-09-01 by Lew's report: the Castleward Tunnel grace was granted with Stormveil, but warping to it or entering Margit's fight could trigger a region kick. The repository evidence below was rechecked against `09882a06` and current main. Player testimony is identified as testimony rather than treated as a measured bucket.

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
