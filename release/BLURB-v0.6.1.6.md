# v0.6.1.6 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** This is a fixpack on the 0.6.1 line: the contract is unchanged, so a v0.6.1 / v0.6.1.x client can be swapped for this one mid-run, and your save is not touched. Nothing in this release requires the swap.

## What you need to update

- **Client:** Optional. The client half of this window is a version stamp only (clients #722); any v0.6.1 / v0.6.1.x client still connects.
- **APWorld:** Host-only. The new `multiworld_scope` option is decided at generation, so only whoever generates the seed needs this apworld; players connect with what they have.
- **YAML:** **New YAML optional.** Existing YAMLs remain valid. `multiworld_scope` defaults to `all`, which is today's behaviour.
- **Existing seed/save:** Compatible. No regeneration or save migration.
- **Profile/assets:** No action.

## What is in it so far

Nothing yet. This window was opened AT THE TAG of v0.6.1.5 with ZERO commits past it, so this file exists before its first entry does,
which is the point of it.

## What carried over from v0.6.1.5

Nothing is owed. v0.6.1.5 shipped the three client fixes and the MapForGoblins 2.1.5 port it
promised, and its stable promotion is paid in this window's opening commit.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
