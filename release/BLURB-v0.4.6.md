# v0.4.6 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

The change is behind the scenes: the full world test suite now uses both cores on the GitHub runner.
The measured CI-equivalent run fell from 224.7 seconds to 130.4 without dropping a test or either of
the suite's guards against silently inert tests. That makes the green-or-red answer arrive
substantially sooner on every future change.

## What carried over from v0.4.5

Nothing is owed. v0.4.5 shipped complete: its changelog section and its blurb were both finished
while the window was open, and `release/CHANNELS.tsv` promoted `stable` to it in the same commit that
opened this window rather than the morning after -- the second window running that row has not
lagged its tag.

⚠️ One thing v0.4.5 shipped is worth repeating to anyone reading this before they generate: a
**one-region seed on the plain region-locks goal is refused now**. The goal region's Lock is
withheld, so a seed whose only Lock is the region you start in has nothing left to find. Generation
says so and names the ways out.

🛑 And one thing IS owed, unchanged from the last two windows because it is not ours to write:
**Elden Ring Tarnished Edition ships 2026-08-28** and a paid content update moves the executable
version. v0.4.4 shipped the gate that explains that failure to a player instead of showing them a
Rust backtrace, but the RVA table it reports against lives in a third-party crate. When the update
lands, the recovery is an upstream revision plus a rebuild -- see #241. That date is now eleven days
out, so it is likely to land IN this window rather than after it.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel before
it says what was built, and that is the right order. v0.4.5's opening section is the same move.
