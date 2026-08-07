# v0.3.8 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**The window opened on purpose.** v0.3.7 was tagged and published on 2026-08-07, and this window
was opened the same evening because somebody remembered — not because a gate went red. That is
worth one line in a changelog nobody else will ever read, because it had genuinely never happened
before: four windows in a row were opened by the release-notes gate failing, and the v0.3.7 notes
had just finished admitting as much.

**The client pin caught up with the client that shipped.** The world repo records which build of
the client it was tested against, and through all of v0.3.7 that record pointed at a commit five
merges old — it missed every Serpent-Hunter fix from the 7th, the ESD probe, and the weapon
swap-back. The `.dll` players actually received is built separately, so the release itself is
probably fine; what was wrong was the repo's own account of what pairs with what, and a cross-repo
gate that had been proving agreement against the wrong client. It proves the right one now.

_Nothing player-facing yet. This section grows as the window does._
