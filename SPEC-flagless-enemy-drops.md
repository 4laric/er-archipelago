# SPEC — datamine the FLAGLESS enemy drops (the suppression blind spot)

**Status:** BUILT AND RUN, 2026-08-07. Measurement only — no gen wiring, no suppression policy.

> ## RESULT — the blind spot is real, and it does NOT explain the motivating case
>
> ```
> enemy lots                                   5134
>   FLAGLESS                                   4890
>     ...no NpcParam references it              3603   (orphan rows, ignored)
>   flagged (already a check candidate)          244
>
> named flagless award slots                   1185     across 1136 lots
>   base_point >= 100 (guaranteed)              268
>   upgrade materials (smithing/somber)          42
>   distinct NPCs referencing them             3896
> ```
>
> 🛑 **The acceptance test below FAILS, and per its own terms this section says so.** Exactly ONE
> `ItemLotParam_enemy` row awards an Ancient Dragon Smithing Stone — lot `50` — and **no `NpcParam`
> references it**. Nothing in the enemy table awards the Somber variant at all. So flagless enemy
> drops are NOT where boblerrr's stones came from.
>
> Eliminations, in order: the arena map lot `2054390000` was blanked and re-armed two minutes before
> the kill; no flagged enemy lot awards them; no live flagless enemy lot awards them. What remains is
> that **matt's enemy randomizer supplied the replacement boss's reward itself**, which is injected
> outside our params and is not datamineable from vanilla.
>
> **Read on the population: benign.** The most common flagless awards are Living Jar Shard, Sliver of
> Meat, Dagger, Pickaxe — ordinary farm loot nobody would want suppressed. The 42 upgrade rows are
> Somber Smithing Stone [2]/[4]/[7] at 150pts and Smithing Stone [3]/[5] at 100pts, i.e. exactly what
> those enemies are farmed for in vanilla. Recommendation: **no action**, but the number now exists
> instead of a worry.
>
> ⭐⭐⭐ It runs IN-SANDBOX. `python3 tools/gen_inputs.py --ensure elden_ring_artifacts` extracts all
> 1452 artifact files from the committed 9 MB `gen_inputs.db` — no Windows box needed for any of this.
**Motivating case (rule 11):** boblerrr, live 0.3.7, killed the enemy occupying Ancient Dragon
Senessax's arena and received **Ancient Dragon Smithing Stone + Somber Ancient Dragon Smithing Stone,
100%**, as real vanilla items.

---

## The defect, stated precisely

It is **not** "we failed to blank a lot we knew about". The arena reward lot was blanked correctly:
`f2053397000 -> lot 2054390000` is in `check_lots_table.map`, and `check-lots` re-armed at 16:16:25,
two minutes before the 16:18:37 kill, logging `485 MAP goods-blank … 0 missing from the named table`.
The stones came from somewhere the pipeline cannot see.

**The whole suppression chain is flag-keyed, and the corpus that feeds it drops unflagged rows by
construction.** `tools/datamine_flag_lots.py:98`:

```python
if lot <= 0 or flag <= 0:          # unflagged/farmable -> not a check
    continue
```

That line is *correct* for building the check list — an unflagged lot cannot be a check, because
there is no flag for the poll to observe. But `flag_lots.tsv` is also the input to
`check_lots_table.json`, which is the input to the client's blank pass. So an unflagged lot is
invisible three layers deep, and nothing downstream can even name it.

The proportions agree: `flag_lots.tsv` holds **4898 map rows and 244 enemy rows**, and the client
writes **485 MAP + 22 ENEMY goods-blanks**. Enemy-side suppression is thin because it inherits the
same blindness, not because enemies rarely drop things.

⚠️ **Enemy rando makes this strictly worse and un-fixable by enemy identity.** Swap an enemy in and
its unflagged drop comes with it, so any rule of the form "blank enemy X's lot" is void — the enemy
standing in a given arena is not ours to predict ([[er-matt-rando-compat]]).

---

## What the tool does

`tools/datamine_flagless_enemy_drops.py` — the INVERSE of every existing consumer: it looks for the
rows the others discard.

**Inputs (all already in `gen_inputs.db`, `REQUIRED_PARAM_CSVS`):**

| file | role |
|---|---|
| `ItemLotParam_enemy.csv` | the drop rows |
| `NpcParam.csv` | `itemLotId_enemy` → which enemies own which lot |
| `EquipParamGoods.csv` | `goodsType`, to classify the ware |
| `*Name*.fmg.xml` (base + both DLC) | display names, so the output is reviewable |

**The join** (already documented in `tools/datamine_msb_item_regions.py:19`):

```
NpcParam.itemLotId_enemy -> ItemLotParam_enemy.ID (+ consecutive rows) -> slots 01..08
```

**The filter — this is the whole tool:**

1. Keep rows where **every** `getItemFlagId*` column is 0/absent. 🛑 Read `getItemFlagId` **and**
   `getItemFlagId01..08`, not just the singular — see the second-order finding below.
2. Keep slots whose `lotItemId%02d > 0` and that resolve to a **named** item (an unnamed id is the
   cut-content class the item-existence guard already refuses).
3. Record `lotItemBasePoint%02d` — the drop weight. A 100%-weight slot is a guaranteed free item and
   is the population that matters; a 1% junk drop is noise.

**Output** — `greenfield/flagless_enemy_drops.tsv`, one row per (lot, slot):

```
lot  slot  item_id  category  base_point  goods_type  name  npc_param_ids
```

`npc_param_ids` is a `;`-joined list, because one lot is shared by many NPCs and the count is part
of the finding.

**Run modes**, mirroring `datamine_unplaced_globals.py`:

```
python tools/datamine_flagless_enemy_drops.py           # report: tallies only, writes nothing
python tools/datamine_flagless_enemy_drops.py --emit    # write the tsv
```

---

## The questions it must answer

The report is the deliverable, not the tsv. It should print:

- how many flagless enemy lots award a **named** item at all;
- of those, how many are **goods** (`EquipParamGoods` row exists) versus weapons/armour;
- how many are **upgrade materials** specifically — smithing stones, somber stones, Ancient Dragon
  stones — since those are the ones that distort the run;
- how many sit at **`lotItemBasePoint` = 100%**;
- how many distinct NPCs reference them, and whether they cluster (all dragons? all field bosses?)
  or are spread across ordinary trash.

**A handful of dragon bosses is a footnote. A broad population is a real integrity problem.** Nobody
knows which it is right now, and that is the only reason to build this.

---

## 🛑 Out of scope, deliberately

**Suppression policy is a separate ruling and must not be pre-empted by this tool.** An unflagged lot
is unflagged *because it is repeatable* — that is what the flag is for. Blanking one is the
`REPEATABLE_GOODS` problem again: it eats every legitimate copy the player would ever farm, which is
exactly why `features/check_item_flags.py` already declines id-keyed suppression for farmables. Sizing
the population first is what makes that ruling possible; guessing at it now is what makes it wrong.

---

## ⭐⭐ Second-order finding, worth checking while in there

`datamine_flag_lots.py` reads **only** the singular `getItemFlagId`:

```python
flag = int(r.get("getItemFlagId", 0) or 0)
```

`datamine_msb_item_regions.py:111` reads **every** column starting `getItemFlagId` — i.e. it knows
about `getItemFlagId01..08`. If any lot carries per-slot flags with the singular column at 0, then
`flag_lots.tsv` is discarding a **flagged** lot as unflagged, and that lot is a check we never made.
Same shape as the class in #249, one table over. Cheap to test: count rows where
`getItemFlagId == 0` but some `getItemFlagId%02d > 0`. If that count is non-zero it is its own issue
and probably outranks this spec.

---

## Acceptance

1. The report runs AP-free from the repo root with the artifacts present, and prints the tallies
   above.
2. `--emit` is idempotent: running it twice against an unchanged corpus produces a byte-identical
   file. (`datamine_unplaced_globals` nearly shipped a self-erasing generator; this one reads no
   table it writes, so idempotency should be free — assert it anyway.)
3. The motivating case is **located**: the Ancient Dragon Smithing Stone / Somber Ancient Dragon
   Smithing Stone drop appears in the output, attached to an ancient-dragon `NpcParam`. If it does
   **not**, the flagless-enemy-lot theory is wrong and the report says so rather than shipping a
   table that quietly fails to explain the case that motivated it.
