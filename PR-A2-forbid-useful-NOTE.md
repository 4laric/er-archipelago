# A2 — forbid_useful filler shortage → NOT a PR

**Verdict: do not upstream.** This is configuration, not a code defect. Recorded here so we don't
re-litigate it later.

## What we observed
Generation fails with **"not enough filler"** when running our **trimmed/lean** pools together with
the default location behaviors:

- `ExcludedLocationBehaviorOption.default = 2` (`forbid_useful`)
- `MissableLocationBehaviorOption.default = 2` (`forbid_useful`)

(`worlds/eldenring/options.py` L326–358.) Under `forbid_useful`, neither progression nor useful items
may land in excluded/missable locations, so those slots must be filled from the **filler** pool. Our
trimmed/lean modes deliberately shrink the filler pool — so on tight seeds there isn't enough filler
left to satisfy every forbid-useful slot, and the fill aborts.

## Why it isn't upstreamable
- The shortage is a property of **our pool-shrinking modes** (trimmed/lean), which we're explicitly
  keeping OUT of upstream. With stock pools, the `forbid_useful` default has plenty of filler and
  never trips.
- The fix we used was a **YAML change**, not code: set both behaviors to `allow_useful`.
  Our own note records it as "not a curation-code bug." There is no diff to send.
- The consumption logic (`__init__.py` L777–788, marking missable+forbid_useful locations
  `EXCLUDED`) is stock AP behavior and correct as written.

**Action:** drop A2 from the upstream PR set. Fold the guidance ("trimmed/lean ⇒ run both behaviors
`allow_useful`") into our *own* trimmed-mode docs/yaml templates, not a PR.

---

## Optional future item (only if we want it) — NOT this PR, must be built+tested first

There *is* one genuinely upstream-shaped improvement hiding here, but **we haven't built it**, so it
must not go out under the don't-PR-unbuilt-work gate:

> **Graceful filler fallback instead of a hard abort.** When the forbid_useful slot demand exceeds
> available filler, the world could (a) emit a clear, actionable error naming the option combination
> at fault, or (b) auto-relax to `allow_useful` for the overflow with a warning, rather than failing
> with the generic core "not enough filler." This would be a real, stock-relevant robustness fix any
> AP world could benefit from.

If we ever pursue it: build it against stock pools, add a regression test that forces the shortage,
gen-test on Windows, *then* consider a separate PR. Until then it stays a backlog idea, not a draft.
