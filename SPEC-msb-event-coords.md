# SPEC — position the `source=event` checks from the MSBs

**Status:** specified, not built. Needs a Windows run (MSBs).
**Expected yield:** up to **505 live checks** gain a coordinate (3912 → ~4417 of 4875).
**Cost:** an extension to an existing datamine, ~200 KB more committed tsv. No new inputs.

---

## The question this answers

"We can't upload the MSBs, they're gigabytes — but is there a datamine where we scan for the
relevant info and put *that* in the db?"

Yes, and that pattern is already the established one here. Five tools read the MSBs on the Windows
box and commit only their distilled output:

| tool | output | size |
|---|---|---|
| `datamine_item_grace_coords.py` | `item_grace_coords.tsv` | 294 KB |
| `datamine_msb_item_regions.py` | `msb_flag_region.tsv` | 159 KB |
| `datamine_msb_gated_treasures.py` | `msb_gated_treasures.tsv` | 18 KB |
| `datamine_grace_ground.py` | `grace_ground.tsv` | 17 KB |
| `datamine_arena_graces.py` | `arena_graces.tsv` | 3 KB |

~490 KB, distilled from gigabytes. So the question is not whether to distil — it is **what we are
not distilling yet.**

> ⚠️ This is the one place the `gen_inputs.py` DESIGN note ("A MIRROR, NOT A DISTILLATION") does
> **not** apply, and the distinction matters. That rule exists because a distillation silently
> drops a column and the artifact dependency comes back at the worst moment — and it is right,
> *when mirroring is possible*. The MSBs cannot be mirrored at any price, so the real choice is
> distil-or-nothing. The mitigation is that the extract must be **wide and dumb** (emit the record,
> not a conclusion) and must record what it scanned, so a missing column is a re-run and not a
> re-derivation.

---

## The gap, measured

Of 4875 live checks:

```
with a coordinate (item_grace_coords)   3912
seen by msb_flag_region                 2672
   ...of which ALSO have coords         2167
   ...MAP known, POSITION missing        505   <- this spec
```

And the 505 are not scattered noise — they are one population. Breaking the missing rows down by
`msb_flag_region.source`:

```
MISSED by the coords tool : event 537,  treasure 9
HAVE  a coordinate        : treasure 2129, enemy 83, event 26
```

**537 of the 546 missing rows are `source=event`**, and every one of them carries
`treasure_name = common90005300` — a shared common-event asset marker, not a real treasure name:

```
flag        map_id      item_lot_id  treasure_name    source
10007085    m10_00      10001085     common90005300   event
1033417400  m60_33_41   1033410400   common90005300   event
```

## Why they have no position today

The two datamines read **different MSB record types**:

- `datamine_msb_item_regions` reads MSB **Event** records, so it can attribute a flag to a MAP.
- `datamine_item_grace_coords` reads MSB **Treasure / Part** records, which is where XYZ lives.

An `event`-sourced check has no Treasure part of its own — it is awarded by a shared common event
(`common90005300`, the corpse/world-drop pattern) — so the coords tool finds nothing to emit. Both
tools are behaving correctly; the corpus is simply split across two record types and only one of
them is being read for geometry.

## What to build

Extend `tools/datamine_item_grace_coords.py` (or add a sibling) to, for each MSB **Event** record
that references an item lot:

1. resolve the Event's referenced **entity / part** (the corpse, asset, or region it fires on);
2. emit that part's `position` as the check's coordinate, with `kind=item` and `key=<flag>` so it
   lands in the existing `item_grace_coords.tsv` schema with no consumer change;
3. add a `via` column (`treasure` | `event_part` | `enemy`) so a consumer can tell a direct
   treasure position from an inferred one — **do not** silently mix provenance into one column.

Everything downstream then improves for free: `build_nearest_grace`, `check_maps`, the check
browser's map tab, and the desc-triage map all read `item_grace_coords.tsv`.

## 🛑 The honest uncertainty

**I cannot verify from the bundle that these Event records resolve to a position** — the MSBs are
not here, which is the whole point. What is established:

- `msb_flag_region` already reads these records and resolves them to a map, so the record IS being
  parsed and DOES carry enough to identify a map;
- whether it also carries (or points at) a usable XYZ is **unconfirmed**.

So the first step is a **probe, not an implementation**: dump one `source=event` record in full
(say `flag 10007085` in `m10_00`) and look at what fields it actually has. If there is no position
and no resolvable part reference, this spec is dead and should be deleted with that finding
recorded — the same way the place-name route was measured and killed in AGENTS.md.

## What this does NOT fix

Of the 901 unplaced weak-descriptor checks, this route can reach at most ~458. The remainder are
unplaceable **by nature**, and no MSB scan will change that:

```
 91  ENEMY drop   position belongs to the enemy, not a treasure
 40  SHOP row     a merchant's stock has no world position
 32  no itemlot   event / gesture award
183  flag_tile    mapped by flag-id convention only, never seen in an MSB
 97  map lot, no msb row
```

Those need a **non-spatial** descriptor (who drops it, which quest, which merchant) — and with
`TalkMsg` and the 365-file talk ESD now both bundled, that is a separate and newly-viable route.
