# v0.6.1.4 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** `CONTRACT_HASH` is unmoved at `2aa64f43`; any client from the 0.6.1 line (v0.6.1 through v0.6.1.3) keeps working on these seeds, and your save is not touched. The new client is worth taking mid-run if you share a slot with someone: it is what makes your two maps agree.

## What you need to update

- **Client:** Optional; recommended if two people play one slot (map pins sync). Otherwise keep the one you have.
- **APWorld:** Host-only, for newly generated rooms.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

**If two of you play one slot, your maps now match.** Report from a shared slot: different
MapForGoblins pins on two machines. The pin filter was reading two things off the local save
that should have come from the room: whether a check was already done (so your partner's
checks stayed pinned for you until you physically picked the item up), and whether a region
was open (a fresh character still catching up on its item ledger showed regions locked that
the room had opened). Both now come from the server first. The client also writes one
`map pins:` line to its log whenever the published set changes, so the next time two maps
disagree one log says why.

**Six checks that could never be taken are out of the pool.** A player asked what to do for
`Roundtable Hold :: Cracked Pot`. Nothing: the game has an item lot for it that nothing ever
awards, on a flag the game doesn't even allocate. It was in the pool because a datamine had
treated a map tile decoded from the flag number as evidence the pickup exists -- the flag vouching
for itself. That decode source no longer counts, which also retired a phantom Sacred Tear and
three more lots with the same signature. None of them could hold a required item, so no seed was
ever blocked by them; they were just dead checks. Their AP ids are burned rather than reused
(`greenfield/tombstones.tsv`), so nothing else renumbered -- the first use of the mechanism #1521
asked for. If someone in a running room still has one of these, the host clears it with
`/send_location`.

## What carried over from v0.6.1.3

Nothing is owed. v0.6.1.3 shipped complete (Grafted Blade sweep fix, `region_sweep`, the
matt's-randomizer guide fix) and `stable` was promoted to it on 2026-09-24. This window
opened two commits past that tag (the CHANNELS promotion and the region_sweep changelog
line), neither of which is player-facing.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
