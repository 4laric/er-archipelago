# v0.3.7 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**One of Elden Ring's Great Runes has been missing from every seed, and nothing noticed.**

Beat Rennala and the game hands you two things: the Remembrance of the Full Moon Queen, and the
Great Rune of the Unborn. Only the Remembrance was ever modelled as a check.

That would be harmless if the two were independent, but they are not — they hang off the same
acquisition flag, and the randomizer clears a check's vanilla items by flag. So it was clearing
both, and because only one of them had a check to hand something back, the Great Rune of the Unborn
was simply deleted. Not misplaced, not made rare: removed from the game and replaced by nothing, in
every seed, since the check model landed.

What kept it hidden is that the item had no name anywhere in our data. Not in the spoiler, not in
hints, not in the item catalog. A player who went looking for it found no trace of it existing —
which is exactly what a player did earlier this week, and it read like the rune had been excluded on
purpose.

It is now a check of its own, in the same place, beside the Remembrance. Both are shuffled
independently. Both are yours to find.

If you use Rennala to respec, this is worth a moment of your attention: vanilla wants that rune in
your inventory to offer rebirth. We have not yet confirmed whether the game asks for the item or
just the flag, so we do not know whether respec has been quietly unavailable this whole time. If you
have tried to respec in a recent seed, we would like to hear either way.

## The Hippopotamus problem

bobler's tracker said `Shadow Keep 124/270` and he said "all bosses dead except hippo which i can't
fight". He was right on both counts, and the two facts were the same fact.

Killing a boss hands you the loot from its area — that is what `dungeon_sweep` is. The Golden
Hippopotamus's sweep is 104 Shadow Keep checks, 38% of the whole region. But the arena you fight it
in is not Shadow Keep. Its reward is scripted in the Keep's map, so that is where we filed the
sweep, while the ground under the fight belongs to Scadu Altus. His seed kept the Keep and not
Scadu Altus, so the region lock ejected him every time he walked toward the fight.

We knew half of this in July. The Hippo's *reward* was re-homed to Scadu Altus back then, with a
note in our own data explaining the kick. The 104-check sweep was left in Shadow Keep and nobody
asked whether that was the same problem wearing different clothes. It was.

Six groups had this shape. They are no longer sent to seeds that cannot fire them, and the tracker
no longer promises a payout that depends on a fight you are not allowed to have. Every check
involved is still in your seed, still in its own region, still yours to walk to and pick up — the
sweep was a convenience, and you keep the checks either way.

The part worth saying plainly: **this had been true in roughly half of all six-region seeds since
sweeps shipped**, and no gate anywhere asked the question. There is one now, over all 225 sweep
groups rather than over the one that got reported.

## Known, and honest about it

**The capital gate counts a rune we do not.** Elden Ring opens Leyndell on a count of flags rather
than on which runes you hold, and Rennala's flag falls inside the range it counts. So the game has
always treated the Great Rune of the Unborn as one of the runes on that door. We do not, yet.

The good news is which direction that error runs: our logic is the stricter of the two. Nothing
becomes unreachable, no seed can soft-lock on it, and no fill is unsafe. What you may see is the
capital physically open a little earlier than the randomizer expects.

Fixing it properly changes what "how many Great Runes" means — the goal option, the gate, and the
item pool all have an opinion — so it is scoped and deliberately not rushed into this window.
