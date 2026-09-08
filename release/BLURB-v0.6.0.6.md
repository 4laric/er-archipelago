# v0.6.0.6 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes — and if Steam has updated your game, you have to.** Versions are V.R.M.F and this is the
0.6.0 line: a v0.6.0.6 client plays every seed rolled by any 0.6.0-line apworld, your run
included, and the contract hash has not moved since v0.6.0.3, so a v0.6.0.3, v0.6.0.4 or v0.6.0.5
client also plays every v0.6.0.6 seed. Your save is not at risk either way. But Elden Ring moved
to 2.7.1.0 on September 8th, and older clients switch themselves off on that executable — on the
new game binary this update is the only client that runs.

## What you need to update

- **Client:** **Required on Elden Ring 2.7.1.0** (the 2026-09-08 Steam update); optional
  otherwise — a v0.6.0.5 client keeps playing every 0.6.0-line seed on 2.6.2.x or 2.7.0.x, and
  the contract hash has not moved since v0.6.0.3.
- **APWorld:** Host-only — install v0.6.0.6 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** **Reinstall or replace** — use the MapForGoblins build and preset shipped
  with this release: it carries a crash fix and new map defaults.

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

## What carried over from v0.6.0.5

Two things, and both are ledger rather than promise.

First, everything above landed AFTER v0.6.0.5 was tagged. #1487 and #1489 wrote their notes
under the already-shipped `## v0.6.0.5` heading; this window moves them here, and the v0.6.0.5
blurb is back to its tagged text. So the 2.7.1.0 and MapForGoblins prose in this file has a
day of provenance behind it even though the window is minutes old — nothing was written twice,
and nothing is claimed for v0.6.0.5 that v0.6.0.5 did not ship.

Second, the debts. 🛑 **The 2.7.1.0 client has never been run against the game.** Its
addresses are mapper-generated and prologue-checked; the live smoke test (gate silent, connect,
one check, one item) is owed before `stable` moves to this version, and `VANILLA_MULTI_SLOT_ROWS`
is still unmeasured on a vanilla 2.7.1.0 run. Older still, and unchanged: `tools/matt_oracle.py`
leaves 107 item-identity disagreements and 45 missing slots allowlisted by cause, chiefly a DLC
upgrade-material tier disagreement spanning 99 event flags, and v0.6.0.5's `flag_lots.tsv`
refresh sharpened rather than answered that — on 37 of those checks the curated name no longer
names any item the flag's lot grants. Those are research debts against our tables, not risks to
a run.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
