# v0.4.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

Nothing yet. This window was opened AT the v0.4.4 tag with zero commits past it, so this file exists
before its first entry does, which is the point of it.

## What carried over from v0.4.4

Nothing is owed. v0.4.4 shipped complete -- both its changelog section and its blurb were finished
while the window was open, and `release/CHANNELS.tsv` promoted `stable` to it in the same commit that
opened this window rather than the morning after. The contract is unmoved at `5c2b9bf2`, the shape it
has had since 0.3.9, so a v0.4.4 client still handshakes with a v0.4.5 seed and no client half was
needed to open this.

🛑 One thing IS owed, and it is not ours to write: **Elden Ring Tarnished Edition ships 2026-08-28**
and a paid content update moves the executable version. v0.4.4 shipped the gate that explains that
failure to a player instead of showing them a Rust backtrace, but the RVA table it reports against
lives in a third-party crate. When the update lands, the recovery is an upstream revision plus a
rebuild -- see #241, and the client's `Cargo.toml` now pins the revision it shipped so the move can be
a deliberate one.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel before
it says what was built, and that is the right order.
