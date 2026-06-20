# PR A1 — apworld: reclassify build-relevant filler as `useful` (junk ammo excluded)

**Target:** `lBedrockl/Archipelago` (base `main`), path `worlds/eldenring/`
**File:** `worlds/eldenring/__init__.py` — `generate_early()`, the item-classification pass (~L373–407)
**Depends on:** nothing in our other PRs. Independent, apworld-only, no license risk.

## ⚠️ Scope correction vs. the plan
The plan listed A1 as a one-line ammo guard in `items.py`. On inspection it isn't standalone — the
guard is a `continue` **inside** a larger filler→`useful` promotion block, and that whole block is
*our* addition (commit `9018a109`, tagged "AP sync candidate" = not yet upstream). So A1 must ship
the promotion block *and* the ammo exclusion together; the guard alone is meaningless to an upstream
that doesn't promote.

**Decision gate before opening:** diff `worlds/eldenring/__init__.py` against `lBedrockl/Archipelago@main`.
- If upstream has **no** useful-reclassification → this PR ships the whole block (as below).
- If upstream **already** reclassifies gear as useful → narrow this PR to just the ammo-range `continue`
  and retitle it "exclude junk ammo from useful promotion."

---

## Suggested PR title
`Elden Ring: classify build-relevant gear as useful (exclude junk ammo)`

## Suggested PR description

> ### What
> In `generate_early`, after progression is assigned, promote build-relevant **filler** items to
> `useful`: all weapons, armor, talismans and ashes of war, plus the meaningful GOODS (upgrade
> stones, larval/crystal tears, spirit ashes, and large rune-drop consumables). `useful` items are
> kept out of missable/excluded locations under the default `forbid_useful` and may spread in
> multiworld. Progression items are never touched.
>
> ### Why
> Without this, real gear sits in the undifferentiated `filler` bucket — it can land in excluded
> locations and is indistinguishable from junk for fill/placement purposes. Marking it `useful`
> gives the generator the right signal without forcing anything to be progression.
>
> ### The ammo exclusion (the correctness detail)
> Arrows and bolts are `WEAPON`-category but are pure filler clutter, so they're explicitly excluded
> from the promotion. This is done by **er_code range (`50_000_000 … 53_599_999`), not by name** —
> deliberately, because name-matching "bolt"/"arrow" would wrongly catch real weapons like
> **Bolt of Gransax** (a spear, er_code `16090000`, well outside the ammo range). Range-gating keeps
> junk ammo as filler while leaving named weapons that happen to contain "bolt"/"arrow" promoted.
>
> ```python
> _useful_cats = {ERItemCategory.WEAPON, ERItemCategory.ARMOR,
>                 ERItemCategory.ACCESSORY, ERItemCategory.ASHOFWAR}
> for _tbl in (item_table, item_table_vanilla):
>     for _data in _tbl.values():
>         if _data.classification != ItemClassification.filler:
>             continue
>         _n = _data.name.lower()
>         # Junk ammo (arrows/bolts, er_code 50_000_000..53_599_999): WEAPON-category but pure
>         # filler. Excluded by ID RANGE, not name -- "Bolt of Gransax" is a SPEAR (16090000).
>         if (_data.category == ERItemCategory.WEAPON and _data.er_code is not None
>                 and 50_000_000 <= _data.er_code < 53_600_000):
>             continue
>         if (_data.category in _useful_cats
>                 or "smithing stone" in _n or "larval tear" in _n or "crystal tear" in _n
>                 or _n.endswith(" ashes") or "spirit ash" in _n
>                 or (_data.runes is not None and _data.runes >= 10000)):
>             _data.classification = ItemClassification.useful
>             _data.filler = False
> # Drop anything just demoted from the pad-filler pools.
> ```
>
> ### Safety
> - Only items currently classified `filler` are considered; progression and existing `useful` are untouched.
> - Items promoted to `useful` are removed from the pad-filler name lists so they aren't double-counted
>   as generated filler.
> - Range-based ammo exclusion has no false positives on named weapons (verified against Bolt of Gransax).
>
> ### Testing
> - Clean generation on a default ER yaml: real gear shows `useful`, arrows/bolts stay `filler`.
> - Bolt of Gransax remains promoted (spear, not ammo).
> - No change to progression placement; seeds still fill.

---

## Pre-submit checklist
- [ ] Run the decision gate above (does lBedrockl already reclassify?) and pick full-block vs. ammo-only scope.
- [ ] Strip any trimmed/lean-specific phrasing from comments — this PR is base-game classification only,
      not our curation modes. (The "dropped in Trimmed/Lean" aside in the current comment should go.)
- [ ] Clean Windows gen-test on a stock yaml (no trimmed, no dlc_only) on its own branch.
- [ ] Keep this PR to the classification pass only — do NOT pull in rune-skip demand-drops (that's A3)
      or region_lock (A4), which touch nearby code in the same file.

## Note
Mild design sensitivity: promoting all real gear to `useful` changes fill/placement behavior (keeps it
out of excluded/missable, lets it spread). It's a common and defensible AP-world choice, but since the
maintainer has been idle since Feb, consider a one-line heads-up in the PR body inviting them to push
back on the GOODS keep-list if they'd scope it differently.
