# Postmortem: key-item grant whack-a-mole

Date: 2026-09-01. Scope: Great Runes, whetblades, and the Leyndell seal incidents.

## Summary

The grant pipeline historically treated a key item as a goods id. Elden Ring key items can also
carry duplicate-named goods rows, randomized check flags, separate capability flags, a hold ceiling,
and consumers outside the decompiled event corpus. Fixing one symptom at a time left the next
consumer to be discovered by a player.

The durable model is now explicit: identity and grant semantics live in
`greenfield/key_item_contracts.tsv`; physical-door predicates live in
`greenfield/key_item_gates.tsv`.

## What happened

### Duplicate names selected the wrong Great Rune row

The six shardbearer runes each have a boss-awarded row (8148-8153) and a duplicate-named Divine
Tower row (191-196). The name-keyed catalog once selected the tower row. It rendered and could be
restored, but it was not the item the boss lot awards. Issue #682 established the only safe identity
rule for this family: the randomized check must resolve to the goods row awarded by that check's own
lot. `test_gf_catalog_matches_the_lot.py` now pins it.

### One whetblade flag appears to carry two meanings

Flags 65610, 65640, 65660, 65680, and 65720 are the five randomized pickup checks. Player reports
also show that goods-only start grants do not unlock the associated affinity behavior (#240).
Setting those flags as a repair would complete the checks (#239). Therefore the contract does not
call `goods+flags` a valid recipe. These rows are explicitly `BLOCKED_DUAL_USE_FLAG` until the
capability can be separated from check completion.

### The Leyndell predicate was misidentified

An early account claimed that the capital seal counted restored flags 190-199. That was not a traced
call site. The corrected derivation (clients#392) is:

- the seal event reads flags 182 and 105;
- common event 730 derives 182 from `CountEventFlags(170, 179) >= 2`;
- the six boss lots use acquisition flags 171-176;
- relief event 6905 maps Rennala's state into flag 177;
- the client reconciles 105 and 182 directly from AP-received Great Runes.

Flags 191-196 are still meaningful, but as Divine Tower restoration state, not the capital counter.
Keeping acquisition, restoration, and aggregate gate state separate prevents the old explanation
from returning through a new feature.

### Hold ceilings changed the failure mode

Every seeded row in this incident family has `maxNum=1`. Re-grants can be accepted without
materializing, produce a maximum-held popup, or surface as a floor drop depending on the path. The
bounded reconciliation guard correctly stops repeated attempts and logs the inert grant. It contains
the failure, but cannot invent a safe repair for a dual-use flag.

## Why the class persisted

The evidence existed in separate places: lot mappings, the gate table, client flag tables, issue
reports, and live probes. No artifact required a feature to state which row is canonical, which
flags are checks, which flags are capabilities, and which of those are safe to reconcile. As a
result, a locally reasonable fix could contradict another subsystem without a failing test.

## Corrective actions

1. Maintain `key_item_contracts.tsv` for every key-item family with grant-sensitive behavior.
2. Reject canonical ids that disagree with the item lot behind their check.
3. Require safe reconciliation flags to be disjoint from randomized check flags.
4. Mark dual-use conflicts as blocked rather than describing a check-leaking workaround as a recipe.
5. Keep untraced consumers `UNVERIFIED`; engine-side behavior is not proven by the absence of an
   EMEVD read.
6. Expand the table and make the inert-grant warning actionable only when the contract contains a
   verified, non-leaking rescue.

## Remaining work

Issue #240 remains the central whetblade design problem. The table makes the conflict testable but
does not pretend to solve it. Broader population coverage and client consumption of verified recipes
should land as separate, reviewable changes.
