# SPEC — growing the spare-preview goods pool

**Status:** proposed, 2026-08-03. Blocked on client PR #32's insertion path being confirmed in game.
**Owner:** Alaric rules. This document is a proposal with its prerequisites stated, not a plan of record.

---

## 1. What the pool is, and why it binds today

`greenfield/spare_goods.tsv` is **65 rows** of `EquipParamGoods` that (a) exist, (b) are referenced by
no lot, shop or recipe, and (c) carry a placeholder or empty `GoodsName` FMG entry. They are borrowed
as stand-ins so a shop slot holding a *foreign* AP item, or a region lock, can show a meaningful name
and the AP flower instead of a vanilla ware.

The pool is **two-tier and ordered**:

| tier | rows | has |
|---|---|---|
| complete | **25** | GoodsName + GoodsInfo + GoodsCaption |
| name-only | **40** | GoodsName only |

`GoodsInfo` (FMG category 20) and `GoodsCaption` (24) cover far fewer ids than `GoodsName` (10), so a
row can be nameable but not describable. `datamine_spare_goods.py` orders complete rows first and
spends them first.

**This is why boblerrr saw 28 broken descriptions.** His seed needed 53 distinct previews: the 25
complete rows were spent, then 28 name-only rows. `53 - 25 = 28`, which is exactly the client's
`names=53 infos=25 captions=25` and its `28 of 53 id(s) are in NO vanilla group` warning. Working as
designed, not a defect.

**The pool already runs out.** `features/shops.py` records a measured solo seed (no foreign items)
where *"65 slots repointed to spares, the entire pool exhausted"*. On exhaustion the code does:

```python
preview[key] = _free[-1]   # pool exhausted -> share the last spare (still flowers)
```

⇒ **every overflow slot shows the same preview name.** Different AP items, one label. That ships today.

## 2. What changed to make growth possible

Client PR #32 taught `fmg_inject` to **create** an FMG entry by inserting a record into the group
array, not only to **redirect** the string slot of an id that already has one. If that holds up, two
world-side constraints stop being load-bearing:

1. **the `g in texts` filter** in `datamine_spare_goods.py` — only offer rows that already have a
   `GoodsName` entry. It exists because an id in no vanilla group had no slot to redirect;
2. **the complete-first ordering** — only 25 rows can carry a description.

Dropping (1) grows the pool past 65. Dropping (2) lets every row carry a full description.

## 3. 🛑 PREREQUISITE — the boundary-claim convention, and why this is not yet safe to build

**Do not implement section 4 until this is settled.** Evidence comes from Alaric's own
`4laric/nightreign-enemy-rando`, where exactly this problem was solved the expensive way
(`healthbar_inplace/fmg.py`).

Nightreign found that **vanilla FMGs routinely set `group[i].last_id == group[i+1].first_id`** — a
"wide claim" where each group claims up to and including its successor's first id. The runtime
resolves a lookup by **linear scan, first group whose `[first_id, last_id]` contains the id**, so the
*earlier* group wins the boundary and the later group's own `first_id` is unreachable. In vanilla NR
this shadowed **77 ids** in `NpcName.fmg`; `905_011_000` rendered "Golden Hippopotamus" instead of
"Demi-Human Swordmaster". Nightreign's note is blunt about the cost:

> *"this is why every prior splice attempt rendered as `?NpcName?` or as the previous group's text."*

Its fix, validated in game: **normalize every adjacent pair before inserting** — where
`group[i].last_id == group[i+1].first_id`, shrink `group[i].last_id` to `first_id - 1` — then insert
the new single-slot group at its sorted position, shrinking the previous group's claim again if needed.

**Elden Ring's lookup has the same shape.** `fmg_inject.rs::my_lookup` is:

```rust
let g = groups.iter().find(|g| id >= g.first_id && id <= g.last_id)?;
let si = (id - g.first_id + g.string_index_base) as usize;
```

First match in a linear scan — identical shadowing exposure.

⚠️ **And PR #32's safety gate rejects exactly that shape.** `er_logic::fmg_groups::is_ordered_disjoint`
fails when `spans[i-1].last_id >= s.first_id`. So **if ER's vanilla FMGs use the boundary-claim
convention, the insert path refuses to build every time** and logs a message blaming *"an injected id
that a vanilla group already covers"* — a misleading diagnosis of a vanilla-shape problem. The feature
would be inert, and the warning would send the next reader after the wrong thing.

### 3.1 The probe that settles it — do this FIRST, it is one log line

Add a one-shot startup diagnostic to `fmg_inject`, per category (10 / 20 / 24):

* the group count;
* whether the **vanilla** array is strictly ascending and disjoint;
* if not, **how many adjacent pairs satisfy `last_id == next.first_id`** (the wide-claim count) and how
  many are strict overlaps (`last_id > next.first_id`).

That is the number that decides everything below, and it is unknown today. Two outcomes:

| finding | consequence |
|---|---|
| vanilla is strictly disjoint | #32's insert works as written; section 4 is unblocked |
| vanilla uses wide claims | #32's insert is **inert**; port Nightreign's normalization first |

🛑 Do not infer the answer from ER's FMGs "probably" matching NR's. NR is a Sekiro+ variant and its
group record layout is explicitly *"unusual"* versus standard SoulsFormats (`_zero` at +0x04,
`last_id` at +0x0C). **The convention question and the layout question are separate**; only the first
one matters here, and only a measurement answers it.

### 3.2 One difference that works in our favour

NR's slot math clamps: `first_string_idx + min(nameid - first_id, count - 1)`. **ER's does not clamp
at all.** So in ER, shrinking a `last_id` changes only which ids a group *claims*; it cannot clip the
slot arithmetic of any id the group still claims. The normalization is therefore *safer* in ER than in
NR, where the safety argument had to route through count-derived-from-`first_string_idx`.

(The flip side: an unclamped lookup means a wide-claiming group indexes **past its own strings** into
the next group's, which is precisely how NR's boundary ids rendered the neighbour's text rather than
a tag. If our probe finds wide claims, expect the same symptom class in ER — and note that it would be
a **pre-existing vanilla-shape bug**, affecting any id we redirect on a boundary, not something #32
introduced.)

## 4. The change, once section 3 clears

1. **`tools/datamine_spare_goods.py`** — drop the `g in texts` requirement, and emit a third column
   distinguishing *redirectable* (has a vanilla group) from *insertable* (needs a created record).
   Keep the emitter's existing refusal-to-emit-on-empty guards.
2. **Ordering survives, with a new key.** Redirectable-and-complete first, then redirectable, then
   insertable. Old clients then consume exactly the rows they can handle, in the order they can
   handle them, and only run past the end on seeds that already exhaust today's pool.
3. **`features/shops.py`** — the `_free[-1]` share-the-last-spare fallback stays as the final
   backstop, but should now be a **loud** one: it is a silent quality loss today (rule: an empty or
   degraded result is a failure, not a clean run). Log the overflow count and the seed's demand.
4. **Declare the dependency.** `contract.py` already ships `requiresClientFeatures` (a seed with
   `auto_equip` on emits `["auto_equip"]`). A seed that hands out **insertable** rows must declare the
   FMG-insertion feature, so an older client refuses or warns instead of silently rendering
   `?GoodsName?` on every such slot.

## 5. Version skew — the reason this needs a decision rather than a merge

An older client can only **redirect**. Today's ordering degrades gracefully for it: complete rows go
first, and a short pool means duplicates rather than tags. If the world starts choosing rows on the
assumption that the client can create entries, an old client on a new seed shows **more**
`?GoodsName?` / `?GoodsInfo?`, not fewer.

So the honest sequencing is:

1. run the §3.1 probe and publish the number;
2. if needed, port the Nightreign normalization to `fmg_inject`, with its in-game confirmation;
3. only then grow the pool, gated on `requiresClientFeatures`.

## 6. Acceptance

- [ ] §3.1 probe shipped and its number recorded here, per category.
- [ ] A merchant screen with **more distinct AP previews than 65** shows a distinct name AND a
      description on every slot — the case the current pool cannot serve.
- [ ] An **old** client on such a seed either refuses at connect or names the shortfall in its log.
      It must not silently render tags.
- [ ] The exhaustion path logs its overflow count instead of quietly sharing `_free[-1]`.
- [ ] A seed at today's ceiling (≈53 previews) is byte-identical to today, so the change is provably
      additive for existing seeds.

## 7. Provenance

- Pool shape, tiers and the 53/25/28 arithmetic: `greenfield/spare_goods.tsv`,
  `tools/datamine_spare_goods.py`, boblerrr's 2026-08-03 log.
- Exhaustion behaviour: `greenfield/eldenring/features/shops.py`.
- Insertion path and its ordering gate: client PR #32, `crates/er-logic/src/fmg_groups.rs`.
- **Boundary-claim convention, the 77 shadowed ids, and the validated normalization:**
  `4laric/nightreign-enemy-rando`, `healthbar_inplace/fmg.py` — read `splice_fmg_entries`'s docstring
  before touching ER's insert path. It records what was tried, what rendered `?NpcName?`, and why.
