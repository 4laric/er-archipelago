# SPEC: Pool-collapse / slimming (BACKLOG)

Status: TODO, drafted 2026-06-17. Not urgent — `patch_apworld_dlc_filler_trim.py`
(stop base filler leaking into the dlc_only backfill) already solved the practical
"too many base goods in the pool" problem. These are pool-tidying follow-ups that reduce
redundant bloat in the `relevance_uplift` injects so the base-game juice is fewer-but-better.

Apworld-only, regen to take effect (no client rebuild). Alaric applies all patches on Windows
(see memory `er-patches-run-on-windows`). Each should be a SEPARATE patch so it can be verified
and reverted independently. All edits via Python string-replace with an EOF-anchored verify
(never a sandbox read-modify-write).

Related: `SPEC-relevance-uplift.md`, memory `er-relevance-uplift-spec`, `er-dlc-gear-curation`.

## 1. Armor-set collapse  (highest payoff — ~40 pool slots)

Whole 4-piece armor sets are the single biggest distinctive uplift chunk (~54 base armor
placements measured in a dlc_only messmer seed). Collapse each set to ONE representative item.

- **Representative piece = HELMET. Fallback = CHESTPLATE** if the set has no helmet
  (Alaric-decided 2026-06-17). The other pieces are dropped from the pool; their locations
  stay checks and are backfilled like any other dropped item.
- Implementation sketch: a set→pieces grouping (likely from `curation.py`, cf. `ARMOR_SET_NONREP`
  which already enumerates non-representative set pieces). Keep the representative in the pool /
  uplift inject list; mark the rest non-injectable / drop from `_uplift_inject_names` armor.
- Verify: representative-per-set count ≈ number of sets; non-rep pieces gone from the pool;
  uplift still injects armor (just one piece per set).

## 2. Physick crystal-tear grouping  (moderate — ~10 slots)

Collapse the physick crystal tears injected by uplift (~16 measured) into a few groups instead
of every individual tear. **Groupings TBD by Alaric** — he named: damage-increase tears,
damage-reduction tears, the two Opaline tears, etc. Build to the confirmed group list; one
representative per group, rest dropped.

## 3. Progressive flask upgrade + progressive additional flask

Replace the Golden Seed / Sacred Tear stackable injects (flask-count and flask-charge upgrades)
with PROGRESSIVE items, mirroring the progressive stone bells pattern (`stone_bells.py` +
client receive handler). Saves space vs. piling N Golden Seeds + N Sacred Tears, and delivers
the upgrades in order. (Minor space win in the measured seed — only ~6 seeds/tears — but varies:
when uplift uniques run out, the budget fills with seeds/tears/runes and they pile up.)

## 4. quick_start → spawn with MAX flasks  (cheapest)

Have `quick_start` grant max flasks (count + charge) at load-in. Then Golden Seed / Sacred Tear
become pointless to inject and can be dropped from the uplift stackable buckets entirely.
Pairs naturally with quick_start (already front-loads the RL120 runes). Alternative to #3.

## Guardrail (do NOT collapse/filler these)

Region **Locks**, **Messmer's Kindling Shard**, **Remembrances**, **keys**, **Scadutree
Fragment** / **Revered Spirit Ash** (upgrade currency), quest items — must stay non-filler /
non-collapsed or uplift will swap them away and break gating/progression.
