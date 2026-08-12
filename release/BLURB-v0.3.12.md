# v0.3.12 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**Take this one if you are on v0.3.11.** v0.3.11's notes described a lot of client work -- your
received spells getting memorised, light roll finally doing something, a DeathLink telling you on
screen that somebody else's death just killed you, the bell hand-in showing up where you would look
for it -- and the release did not actually contain any of it. The apworld was current; the client
bundled with it was from the previous day. Nothing was lost or reverted, and none of it needs a new
seed: it is all here now.

**The wizard now shows what you are sending out, live, while you set the options.** It sits in the
right-hand column next to your yaml, on every step, and it finally answers the knob most people
reach for: `filler_foreign_pct`, which decides how much of your consumables, crafting materials and
upgrade stones stay in your own world. Turning it to 50 now reads "1,031 of your checks open to a
foreign item, 439 held at home" instead of standing still. It is an estimate and says so — the
option picks item names, and names carry different numbers of copies — but a labelled estimate beats
a figure that never moves.

**The wizard's Seed size step was blank.** Not slow, not wrong -- blank. You clicked to it and got
the settings and no numbers, and they only appeared once you changed something. A refactor three
days ago had it drawing its figures into a part of the page that had not been put on the page yet,
which fails silently in a browser. Fixed, and there is now a gate that actually renders every step
of the wizard and fails if one of them comes out empty.

**The Curated Filler recipe is usable in the options wizard.** It is the only setting whose value is
a table rather than a number, a switch or a list, and the wizard had no control for a table -- so it
handed the recipe to a plain text box, and the box showed you the words `[object Object]`. Typing in
that box was worse than looking at it: the yaml you downloaded afterwards carried a line of text
where the world expects a table of categories, which is not a recipe at all.

It is a weight per category now, with the share of the filler tail each weight buys shown beside it,
because the weights are relative -- proportions, not percentages, and they need not add up to
anything. Seven of the sixteen categories were not on the page at all before this, including
`firepots`, `rare` and `junk`; they are now. Nothing you have already written changes.
