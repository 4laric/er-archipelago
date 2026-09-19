# v0.6.1.1 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** `CONTRACT_HASH` is unmoved at `2aa64f43`, so the v0.6.1.1 client and the v0.6.1 client are interchangeable on each other's seeds, and both read every 0.4.13, 0.5.x and 0.6.0.x seed through the audited legacy-contract bridge. Swapping the `.dll` mid-run puts nothing at risk and needs no reroll or save migration. The standing version gates still apply and none are new.

## What you need to update

- **Client:** No -- nothing has changed since v0.6.1. Keep the v0.6.1 client.
- **APWorld:** No -- nothing has changed since v0.6.1.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

Nothing yet. This window was opened AT THE TAG of v0.6.1 with ZERO commits past it, so this file exists before its first entry does,
which is the point of it.

## What carried over from v0.6.1

Nothing is owed. v0.6.1's release workflows were green before the stable promotion, which was paid in this window's opening commit (stable and `latest.json` now read v0.6.1), and the one loose end from that cut -- a stale test-shard weights file -- was fixed before the tag.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
