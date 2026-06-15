# SPEC: Bad-and-Remote Check Trim

Status: draft (2026-06-14). Owner: Alaric.
Related: `SPEC-dungeon-sweep.md`, `SPEC-region-chain.md`, memory `er-start-items-randomize-request` (lean-check curation wishlist).

## Goal

Trim the multiworld pool of checks that are **both low-value AND out of the way** — a bad
weapon at the end of a dead-end cave, C-tier armor in a corner of a far region. Removing
such a check removes both the chore (walking there) and the junk item (it no longer
clutters anyone's pool), with no cost to anyone's experience.

Two conditions must hold for a check to be dropped. Removing the AND — trimming on
quality alone, or remoteness alone — is explicitly out of scope: a good weapon stays
wherever it is, and any item near a grace stays. We only cut the intersection.

## Where this lives

Fold into the existing `LocationPool` **Trimmed** mode rather than adding an option, per
decision 2026-06-14.

- Option: `LocationPool` (`options.py:408`), values `all`=0 / `trimmed`=1 / `lean`=2.
- Gate: `EldenRingWorld._in_location_pool(self, data)` in
  `Archipelago/worlds/eldenring/__init__.py:2755`. The `pool == 1` branch (lines
  2762–2785) is what we extend.

Today the Trimmed branch only ever drops checks whose vanilla item is `filler`
(runes, consumables, materials). The first thing it does is:

```python
if cls != ItemClassification.filler:
    return True          # <-- all gear/weapons/armor are kept here, unconditionally
```

So weapons and armor (category `WEAPON`/`ARMOR`, classification `useful`/`progression`,
never `filler`) currently **always survive** Trimmed. The whole point of this pass is to
insert a bad-and-remote test **before** that short-circuit so it can reach gear. The new
test only ever returns `False` (drop); anything it doesn't drop falls through to today's
logic unchanged, so existing behavior for filler and for good gear is preserved.

## The two signals

### Signal A — quality ("bad")

There is no tier/quality field on items today (`ERItemData`, `items.py:17`). Items only
carry `category`, `classification` (`filler`/`useful`/`progression`), and flags. So we
must add a quality source. Per decision 2026-06-14: **import a community tier list.**

Deliverable: a generated data file `eldenring/item_tiers.py` (mirrors the
`grace_data.py` pattern — auto-generated, header notes the source and regen command),
mapping item `base_name` → tier letter:

```python
# AUTO-GENERATED. Source: <tier-list URL>, fetched <date>. Regen: tools/build_item_tiers.py
WEAPON_TIERS = { "Longsword": "B", "Reduvia": "A", "Varre's Bouquet": "D", ... }
ARMOR_TIERS  = { "Lordsworn Set": "C", ... }   # keyed by SET; applied to every piece
```

**Source.** Pick one maintained PvE-oriented list and pin it (lists are opinionated and
drift). Candidates, in rough order of mapping-friendliness:
- A structured/community dataset (e.g. a GitHub-hosted ranked CSV/JSON) — best, parseable.
- Fextralife / a wiki tier-list page — readable but needs HTML scraping + cleanup.
- A well-known ranked spreadsheet — needs export.

Recommendation: prefer a structured dataset; fall back to scraping one wiki page. The
choice matters less than pinning it and committing the *generated* `item_tiers.py` so
gen is reproducible offline (the apworld must gen without network).

**The mapping problem (the real work).** Tier-list display names ≠ `item_table` keys:
- Weapons: tier lists name the base weapon ("Rivers of Blood"); `item_table` keys
  usually match, but watch infusions/affinities and `base_name` grouping (`items.py`).
- Armor: tier lists rank by **set**; `item_table` has individual pieces. Map set→tier,
  then apply the set's tier to all four pieces by name prefix.
- Misc: some list entries have no item (covered elsewhere) and vice-versa.

Build `tools/build_item_tiers.py` to: fetch source → normalize names (strip "+N",
affinity prefixes, punctuation; case-fold) → fuzzy-match against `item_table` keys →
emit matched pairs **plus an `unmatched.txt` report**. Maintain a small hand-written
`tools/tier_overrides.tsv` for entries the matcher misses or gets wrong; overrides win.
This is the same fetch→map→override→generate shape as the grace pipeline.

**"Bad" threshold.** A tunable module constant, default **C and below** (C/D/F) counts
as bad for the AND test. Tune after seeing the trim report (below). Items **not on the
tier list are treated as not-bad (kept)** — fail safe, never trim something we can't rate.

**Scope of categories.** Phase 1: `WEAPON` and `ARMOR` only (the user's stated cases).
`ACCESSORY` (talismans) and `ASHOFWAR` are deliberately excluded — talismans are
build-defining and ashes are cheap to want; revisit only with their own lists if asked.

### Signal B — remoteness ("out of the way")

Per decision 2026-06-14, remoteness is a **scored heuristic combining several metrics**,
including proximity to a site of grace — not a single tag. Compute a `remoteness(data)`
score; a check is "remote" when the score ≥ a tunable threshold.

Available metrics, by data we have **today**:

1. **Hand tags (per location, free).** `ERLocationData` already carries `outoftheway`,
   `hidden`, and `deadend` (`locations.py`). These are curated truth and should dominate
   the score. `outoftheway` is the strongest single signal.
2. **Dungeon depth (per location, free).** Location-type tags `catacombboss`,
   `caveboss`, `tunnelboss`, `graveboss`, `minidungeonboss`, and the `crawl` tag mean
   "you must clear an interior to reach this." Interior checks behind a boss are remote
   by construction.
3. **Region remoteness (per region, derivable today).** `grace_data.REGION_GRACE_POINTS`
   gives grace coordinates per region on a shared 256 m grid (overworld) and
   `region_order` gives progression order. A region whose grace centroid is far from the
   start cluster, or late in `region_order`, is a coarse "this whole area is far" signal.

The metric the user named explicitly — **per-check proximity to the nearest grace** —
is **not computable from current apworld data**: locations have no world coordinates.
`ERLocationData.key` is a map/entity id (e.g. `"100000,0:0010007960::"`), not a position,
and only *graces* carry coordinates (`grace_data.py`), keyed by region, not per check.

So per-check grace distance is a **prerequisite data-extraction job**, specced as its own
phase rather than hand-waved:

- **Phase 2 (coordinate extraction).** Add per-location world coords to the artifact
  pipeline that already produces `grace_flags.tsv` (referenced in `grace_data.py` header).
  Source the entity/MSB positions from the randomizer repo's map data, emit
  `elden_ring_artifacts/location_coords.tsv` (`location_key → map, x, z`), bake into a
  generated `location_coords.py`. Then `remoteness()` can add a true term:
  distance from the check to the nearest grace **in its region** (reuse
  `REGION_GRACE_POINTS`), bucketed (near / medium / far).

**Scoring.** Weighted sum, normalized, threshold tunable. Suggested starting weights:

| Metric | Source | Phase | Weight |
|---|---|---|---|
| `outoftheway` | tag | 1 | 3 |
| `hidden` | tag | 1 | 1 |
| `deadend` | tag | 1 | 1 |
| dungeon-interior (cave/tunnel/catacomb/grave/minidungeon/crawl) | tag | 1 | 2 |
| region far / late in `region_order` | grace centroid + order | 1 | 1 |
| nearest-grace distance bucket (near=0 / med=1 / far=2) | per-check coords | 2 | 2 |

Default "remote" threshold ≥ 3 (so a single `outoftheway`, or a dungeon-interior check in
a far region, qualifies). Phase 1 ships on metrics 1–5; Phase 2 adds the grace-distance
term and lets us lower reliance on the coarse region term. Tune both threshold and weights
against the trim report before committing defaults.

## The trim rule

Inserted at the top of the `pool == 1` branch in `_in_location_pool`
(`__init__.py:2762`), before the `cls != filler` short-circuit:

```python
if pool == 1:
    item = item_table.get(data.default_item_name)
    # NEW: bad-and-remote gear trim (runs before the filler short-circuit so it can
    # reach weapons/armor, which are never filler).
    if self._is_bad_and_remote(data, item):
        return False
    # ... existing Trimmed logic unchanged from here ...
    if item.classification != ItemClassification.filler:
        return True
    ...
```

`_is_bad_and_remote(data, item)` returns True only when **all** hold:

1. `item` exists and `item.category in (WEAPON, ARMOR)`.
2. `item.classification != progression` (never trim a progression item, regardless of
   tier — keeps the world beatable; defensive, gear is rarely progression).
3. Quality is bad: tier from `item_tiers` for the item's `base_name` ≤ threshold. Items
   with no tier entry are **not bad** → not trimmed.
4. Remote: `remoteness(data) >= threshold`.
5. Not force-kept (next section).

### Force-keep exemptions (override the trim)

These win even if bad-and-remote, reusing existing curation intent
(memory `er-start-items-randomize-request`):

- **`chest` checks holding a weapon** — keep. Chest weapons (e.g. Lordsworn's Greatsword)
  are wishlisted as fun early gear; `data.chest` is the lever.
- **The named on-path curation set** already in the Trimmed branch (the
  `"LG/GC: Kukri x4 - E of GC"`-style list) — extend with any gear spots we want
  protected by name.
- **Smithing-stone-bearing and early-finger checks** — already kept by the existing
  Trimmed logic; the new test must not pre-empt them (it won't: those items aren't
  WEAPON/ARMOR, so condition 1 already excludes them).
- A small **module allow-list** `TRIM_KEEP_NAMES` for one-off "actually keep this"
  decisions surfaced by the report.

## Side effects (intended)

Dropping a check via `_is_location_available` removing it from the pool also removes its
vanilla item from circulation: `create_items` (`__init__.py:657`) builds the item pool
from *unfilled locations'* `default_item_name`, so a trimmed bad weapon's item is never
added to anyone's multiworld. That is the desired outcome — fewer junk items, not just
fewer chores. The existing Golden-Rune demand-drop and filler balancing
(`create_items`) already absorb pool/location count changes, so no rebalancing is needed;
trimming only *reduces* locations and their items symmetrically.

## Phasing

- **Phase 0 — quality data.** `tools/build_item_tiers.py` + `tier_overrides.tsv` →
  committed `item_tiers.py`. Review `unmatched.txt`; get weapon coverage near-complete and
  armor by-set. No behavior change yet.
- **Phase 1 — tag/region trim.** `remoteness()` on metrics 1–5, `_is_bad_and_remote`,
  force-keeps, wire into Trimmed. Ship behind the existing Trimmed mode.
- **Phase 2 — grace-distance term.** Extract per-location coords into the artifact
  pipeline → `location_coords.py`; add the nearest-grace distance term to `remoteness()`;
  retune weights.

## Verification / eval

1. **Trim report tool** (dev-loop, do this first and iterate on it before trusting the
   defaults): dump every check `_is_bad_and_remote` would drop, with columns
   region / location name / item / category / tier / remoteness score / which metrics
   fired. Eyeball for false positives (good gear, on-path spots) and false negatives.
   Tune threshold/weights against this, not in the abstract.
2. **Counts:** report trimmed count overall and per region; confirm it lands in a sane
   band (Trimmed is ~2150 today — expect this to shave a few hundred gear checks, not
   gut it). Flag any region that loses an outsized share.
3. **No-progression assertion:** assert zero trimmed checks held a `progression` item.
4. **Beatability:** run the apworld's fill/completion test with `location_pool=trimmed`
   across several seeds (base, DLC-on, DLC-only) on Windows (sandbox can't run AP — see
   memory `er-dev-environment`); confirm generation succeeds and is beatable.
5. **Regression:** confirm `all` and `lean` modes are byte-for-byte unchanged (the new
   code is gated entirely inside `pool == 1`).

## Open questions

- Tier-list source to pin (structured dataset vs one wiki page) — affects the matcher.
- Default bad threshold: C-and-below vs D-and-below. Decide from the report.
- Whether Phase 2 coord extraction is worth it, or tags+region prove "good enough" in
  the Phase 1 report (the user asked for grace proximity, so assume yes unless the
  Phase 1 report already looks right).
- Armor: trim individual underranked pieces, or only when the whole set is C-and-below?
  (Spec assumes set-level tier applied per piece; per-piece needs a richer source.)
