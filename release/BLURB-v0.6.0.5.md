# v0.6.0.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is the 0.6.0 line: a v0.6.0.5 client plays every seed
rolled by any 0.6.0-line apworld, your run included, and the contract hash has not moved since
v0.6.0.3, so a v0.6.0.3 or v0.6.0.4 client also plays every v0.6.0.5 seed. Your save is not at
risk either way. Nothing in this window yet asks you to update.

## What you need to update

- **Client:** Optional — nothing in this window yet changes the client; a v0.6.0.4 client keeps
  playing every 0.6.0-line seed, and the contract hash has not moved since v0.6.0.3.
- **APWorld:** Host-only — install v0.6.0.5 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** No action — the MapForGoblins build and preset are unchanged from v0.6.0.4.

## What is in it so far

Nothing yet. This window was opened AT THE TAG of v0.6.0.4 with ZERO commits past it, so this file exists before its first entry does,
which is the point of it.

The Divine Tower of East Altus is Leyndell now. Two players, a month apart, said the same thing
about it -- boblerrr on the Nexus page in August, Sinon this morning: the tower's loot was counted
as Altus, and the tower is not Altus. You reach its gate one way, over the greatbridge out of
Leyndell's eastern ward that opens after Morgott, so an Altus-only seed was steering people at
seven checks they could not walk to while a Leyndell seed walked them past all seven. The checks,
the Fell Twins' sweep and the tower's own kick geometry all moved together, which is the part that
matters: the region lock now ejects the player who has no business up there and lets in the one who
does. Its two graces stay out of every warp bundle -- owning Leyndell buys you the walk, not a
shortcut past Morgott.

Altus loses seven checks and Leyndell gains them, so seeds roll differently. Nothing about the
client, the contract or a save in progress changes.

## What carried over from v0.6.0.4

One thing is owed, and it is a research debt rather than a promise to players. v0.6.0.4 shipped
the generated `!give` item ID reference and `tools/matt_oracle.py`, the read-only cross-check
against thefifthmatt's slot table — and that tool deliberately left 103 item rows and 45 missing
slots on the record as OPEN findings to adjudicate, chiefly a DLC upgrade-material tier
disagreement spanning 99 event flags. They are allowlisted by cause, so they do not fail the
weekly run; they are still unanswered questions about our tables. Nothing else carries: the
item-ID page is generated with a `--check` gate, and neither v0.6.0.4 change touched the contract,
the client, generation or any seed, so no marker, waiver or version-compatibility promise from
that window is outstanding here.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
