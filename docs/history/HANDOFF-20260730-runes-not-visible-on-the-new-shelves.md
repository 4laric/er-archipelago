# Handoff — 2026-07-30 — a rune was not visible on the new shelves, and why the param diff was the wrong question

Supersedes an uncommitted `HANDOFF-20260730-runes-dont-render-in-shop-rows.md` that sat at the repo
root, unreachable to anyone following AGENTS §1 (never read the mount). Its headline claim — "a
Golden Rune written into a shop row DOES NOT RENDER" — is **retracted**; §3 says what survived.

Everything here states its basis. Numbers marked MEASURED were computed this session from the
committed `gen_inputs.db` bundle and `greenfield/eldenring/data.py`; the commands are inline.

## 1. Repo state — VERIFIED against origin, not recited

| | |
|---|---|
| world `main` | `20ee265`, CI **green** (`Test` completed success 2026-07-30T02:54Z) |
| PR #223 `shop-stock-retarget` | **merged** 00:59:39Z — carries `62bd599`, `67422a3`, `0724e9f`, `8a69af8` |
| PR #224 `fix/shop-preview-repoint-tests` | **merged** 00:59:41Z — its single commit `7eb3521` went INTO #223's branch via `0af1411`, then both landed |
| client `main` | `fad5182`, CI green (build, 532 tests, fmt, clippy ×2). Two runs before it were RED (`58f0606`, `cf131cf`) |
| post-merge on `main` | `a321153`, `8610deb` (merchant labels) |

🛑 **`67422a3` re-armed the wizard drift gate, reversing Alaric's 2026-07-04 disable — and it is
already ON `main`.** The superseded handoff described this as "his to veto", which is no longer the
shape of the decision: a veto is now a revert. Flagging it, not deciding it.

## 2. The finding, stated at the size the evidence supports

On the 14 retargeted shelves, a rune ware was **not seen by Alaric in the merchant menu**, while the
non-rune row beside it rendered. Same merchant (Iji), same two adjacent rows, two seeds — the rows
traded which one was missing:

| seed | row 100225 (vanilla Somber [1] @2000) | row 100226 (vanilla Somber [2] @3000) |
|---|---|---|
| A | Golden Rune [1] @187 → **not seen** | Smithing Stone [3] @600 → visible |
| B | Gold-Pickled Fowl Foot @600 → visible | Golden Rune [7] @2343 → **not seen** |

**Price is controlled, and MEASURED so** — `GOODS_PRICE` is 600 for both visible wares against
vanilla row values of 2000/3000, so a changed ware at a changed price renders fine. Row identity and
merchant are controlled by the swap. Within these four observations only ware-ness tracks the miss.

**What it is NOT evidence for:** "runes do not render in shop rows." Four rows on one merchant on two
seeds cannot carry a game-wide render rule, and §3 shows it is false.

## 3. 🛑 Alaric, 2026-07-30: runes rendered fine before the retarget — the cost was just wrong

That is the live-game oracle and it **voids the entire `EquipParamGoods` diff**. `sortGroupId` is a
vanilla constant: it was 100 on every build where rendering worked, so it cannot be why rendering
stopped. Same for every column in that table. A param diff answers *"what is different about this
item"*, which is only the right question when the symptom is as old as the param — on a
**regression** it is a category error that returns a confident, well-evidenced, irrelevant answer.

Caveat, stated rather than glossed: under the old 455 rows the writes landed in Boc's alteration list
and the Roundtable duplication list, which are different UI screens from a merchant's purchase list.
A purchase-menu-specific behaviour is therefore not fully excluded — but the burden has moved, and
the search space is now **our own commits**, chiefly `62bd599` (455 → 14 rows) and the client flag
write added while chasing this (`cf131cf`).

### Two readings that fit everything, cheapest first

1. **`sortGroupId` SORTS, it does not filter.** Group 100 would place the rune elsewhere in the list
   — Iji's list is long, Boc's alteration list was short, which is also why it looked fine before.
   **Predicts the row is present.** Cost: scroll Iji's entire list, every category, and look for a
   blank-named row while you are there. Do this before building anything.
2. **The retarget changed the visibility regime.** MEASURED from vanilla `ShopLineupParam`: all 14
   new shelves carry a NONZERO `eventFlag_forStock` (110040 … 220720), where all 455 old rows had
   none by construction of the old predicate. These rows are flag-gated in a way the old ones never
   were, and the client now zeroes that flag on every rerolled row. Effect unmeasured.

## 4. MEASURED: three of the five candidate columns are already dead

```bash
python3 tools/gen_inputs.py --ensure /tmp/art     # 1452 files, no Windows box needed
# then join art/vanilla_er/vanilla_er/{EquipParamGoods,ShopLineupParam}.csv
```

| column | runes | goods sharing that value | shopped in vanilla (equipType 3) | verdict |
|---|---|---|---|---|
| `sortGroupId` | 100 | 43 | **0 of 306** | survives |
| `canMultiUse` | 1 | 33 | **0 of 306** | survives |
| `goodsUseAnim` | 9 | 63 | 25 of 306 | **ELIMINATED** |
| `maxNum` | 99 | 354 | 139 of 306 | **ELIMINATED** |
| `maxRepositoryNum` | 600 | 1398 | 162 of 306 | **ELIMINATED** |

The "0 of 484" figure reconciles: 498 equipType-3 rows − the 14 shelves = 484.

⭐⭐ **The two survivors are COLLINEAR. 32 of the 33 `canMultiUse == 1` goods are also `sortGroupId
100`** — the only exception is unnamed good 98. So the 0-of-484 statistic never privileged
`sortGroupId` over `canMultiUse`, and it is equally consistent with FromSoft simply never shelving
these items (31 of the 43 group-100 goods are runes; the rest are prayerbooks and scrolls — quest
items nobody would merchandise). A correlation of zero over a column that tracks item CLASS cannot
separate "the menu filters on it" from "the designers never did it".

## 5. If §3.1 fails and a test build is needed: use a PRAYERBOOK, not any group-100 good

MEASURED. Prayerbooks/scrolls `8850`–`8866` are `sortGroupId 100`, `canMultiUse 0`,
`goodsUseAnim 0`, `maxNum 1` — and every one of those non-`sortGroupId` properties is demonstrably
shoppable in vanilla (`maxNum 1`: 56 of 306 shopped goods; `goodsUseAnim 0`: 230 of 306). So the arms
are clean:

- prayerbook **hides** ⇒ `sortGroupId` is the filter;
- prayerbook **shows** ⇒ `sortGroupId` exonerated, and `canMultiUse` is next (and the rune-specific
  possibilities re-open).

🛑 **Do NOT pick group-100 good `2990` for this.** It is `canMultiUse 1`, so it cannot separate the
two survivors, and it has no catalog name. The superseded handoff said "a group-100 non-rune" with no
selection criterion — 12 of the 43 qualify and the choice decides whether the experiment means
anything.

## 6. MEASURED: the merchant labels rest on a weaker basis than `8610deb` claims

`8610deb` replaced a row-prefix guess with "within a merchant block the stock flag runs sequentially,
so bracket the shelf's flag with its named neighbours in `data.py`". That is a real derivation and a
large improvement. Two things it should say and does not:

- **The base rate. MEASURED: 100 of 518 adjacent named-flag pairs change seller — 19%.** So a bracket
  drawn between two named flags straddles a merchant boundary about one time in five. This is a
  nearest-neighbour inference, the `tile_pr()` shape CONTRIBUTING's Provenance section is about; it
  never fails, it just sometimes answers wrong.
- **For 100225/100226 it is not a bracket at all.** The nearest named flag ABOVE is `f120270`
  (Smithing Master Iji, correct); the nearest named flag BELOW is `f120020` — **Sorcerer Rogier**,
  230 flags away. One-sided. The label happens to be right, and the warrant for that is **Alaric's
  screenshot**, not the derivation. `f110040` (Patches) does bracket cleanly: `f110030` and `f110050`
  both name Patches/Thiollier. `f190840`, `f220670` straddle.
- The premise itself is US-owned and unverified (CONTRIBUTING, *Constraint ownership*): `ShopLineupParam`
  has no seller column, so "flags run sequentially within a merchant" is our inference about the game's
  numbering, not a cited datum.

## 7. What the superseded handoff got wrong

- Presented **#224 as "ready to merge, fixes main's red"** two hours after it merged, and inverted the
  merge direction.
- Universalised four observations into **"a Golden Rune written into a shop row DOES NOT RENDER"**, and
  that headline propagated into memory as a 🔥🔥 fact with a "~30% of shelves are a silent no-op"
  figure that is an ESTIMATE from a pool share, never counted in a seed.
- Promoted one of **two collinear** candidates to the lead and parked the other as an "untested
  alternate", when three of the five could have been eliminated from committed data in ten minutes.
- Opened with "everything below is verified unless marked" and then listed four confident-wrong claims
  in the next section. The blanket claim is the thing CONTRIBUTING rule 10 is about.
- Lived at the repo root, **untracked**, so the workflow that is supposed to consume it could not.

Its good parts, kept: the swap design, the retraction of the stock-flag root cause, and `8a69af8` —
which found a false "the CSV is committed" claim, went and got the input from `gen_inputs.db` instead
of skipping, and verified the recovered file was byte-identical. That is the pattern.

## 8. Open

- **`test_gf_client_can_sell_mirror` does not cover the nibble set** (mutation-found: removing
  `_GEM_NIBBLE` left it green). Nothing compares `_SELLABLE_NIBBLES` to the Rust `er_sell_id`
  category list.
- Fable's spec items: `SELLERS` map + spoiler-log table for `shopInfiniteStock`, the CONTRACT/docstring
  wording fix ("browsable" overclaims), `shops.py` comment naming gems.
- The wizard `--check` step has run green once. Once is not a gate — it has never been seen red
  (CONTRIBUTING rule 7).
- Count the affected shelves in a real seed before repeating "~4 of 14".
