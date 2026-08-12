# v0.3.12 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**The wizard's Seed size step was blank.** Not slow, not wrong -- blank. You clicked to it and got
the settings and no numbers, and they only appeared once you changed something. A refactor three
days ago had it drawing its figures into a part of the page that had not been put on the page yet,
which fails silently in a browser. Fixed, and there is now a gate that actually renders every step
of the wizard and fails if one of them comes out empty. The card about what you send other players
also now appears on the Multiworld & Placement tab, next to the settings that move it.
