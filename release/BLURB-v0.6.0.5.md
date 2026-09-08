# v0.6.0.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is the 0.6.0 line: a v0.6.0.5 client plays every seed
rolled by any 0.6.0-line apworld, your run included, and the contract hash has not moved since
v0.6.0.3, so a v0.6.0.3 or v0.6.0.4 client also plays every v0.6.0.5 seed. Your save is not at
risk either way. If Steam has updated your game to 2.7.1.0, you HAVE to update: older clients
switch themselves off on that executable.

## What you need to update

- **Client:** **Required on Elden Ring 2.7.1.0** (the 2026-09-08 Steam update); optional
  otherwise — a v0.6.0.4 client keeps playing every 0.6.0-line seed on 2.6.2.x or 2.7.0.x, and
  the contract hash has not moved since v0.6.0.3.
- **APWorld:** Host-only — install v0.6.0.5 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** **Reinstall the MapForGoblins build and preset** from this release: it
  carries a crash fix and new map defaults.

## What is in it so far

**Elden Ring updated to 2.7.1.0 on September 8th, and this client follows it.** Older clients
show the "unsupported game version" box and switch themselves off; your save is untouched
either way. The new addresses come from the same generator upstream uses, run against the real
executable, and the patch itself changed nothing in the game's item tables -- so nothing about
your seed moves. Players still on 2.6.2.x or 2.7.0.x keep working. What has NOT happened yet is
a live run on 2.7.1.0; until one is logged, treat this as a build that should work rather than
one that has.

**The in-game map stops crashing and stops lagging.** A use-after-free on the map overlay
thread, caught in a v0.6.0 player log, is fixed. Late-game map opens are faster because pins
hidden by a setting or by collection are no longer built at all; the trade is that unhiding a
marker takes effect on the next map open. Two defaults changed with it: **"In logic only" is
now on**, so the map pins only checks your tracker says you can reach right now (turn it off
under F10 for everything), and **the orange progression rings are gone** along with their size
slider -- they buried the pins they were meant to lift.

**Bookkeeping you will not feel:** the flag-to-lot table behind multi-copy checks was
re-derived against the current param corpus and its datamine is now gated in CI, and the
patch-day runbook grew a name-stripping tool so the next Elden Ring update is diffed in
minutes instead of a morning.

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
