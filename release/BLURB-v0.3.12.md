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

**The Curated Filler recipe is usable in the options wizard.** It is the only setting whose value is
a table rather than a number, a switch or a list, and the wizard had no control for a table -- so it
handed the recipe to a plain text box, and the box showed you the words `[object Object]`. Typing in
that box was worse than looking at it: the yaml you downloaded afterwards carried a line of text
where the world expects a table of categories, which is not a recipe at all.

It is a weight per category now, with the share of the filler tail each weight buys shown beside it,
because the weights are relative -- proportions, not percentages, and they need not add up to
anything. Seven of the sixteen categories were not on the page at all before this, including
`firepots`, `rare` and `junk`; they are now. Nothing you have already written changes.
