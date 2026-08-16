# v0.4.4 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

### Your region Locks stop hiding in a boss's trousers

The default progression surface puts this world's own key items — region Locks, required runes,
legacy keys — on major-boss checks, on the reasoning that a major boss is a thing you will find.
Four of the checks it counted as major bosses were Dancer of Ranah's Hood, Dress, Bracer and
Trousers, and four more were Blackgaol Knight's armour set.

The tag is keyed on a boss's death flag, which is right; the trouble is that a death flag pays out a
whole loot table, and every piece of it was being counted as another major boss. Nine checks, three
bosses. Now it is one check per boss — the one the death actually grants.

If you have been wondering why a Lock occasionally turned up on a piece of DLC armour rather than on
the boss who dropped it: that.

_(For whoever writes the real one: the interesting part is not the fix, it is the line it draws.
`Boss` and `Legendary` describe how a check was acquired, so a sibling lot inherits them and that
reading stands untouched. `MajorBoss` describes an entity, and ten lots are not ten bosses. The
changelog has it, with the two gates.)_
### Your yaml is no longer a shrug

If you used the wizard and trusted its defaults, the file it handed you said `Elden Ring: {}`. Every
option you had just been walked through — all 58 of them — went unmentioned, because the emitter
only ever wrote down what you had *changed*. The better the defaults got, the less the file said.

Now it writes all of them, in order, each with its name beside it. What you changed is still obvious
at a glance: those lines, and only those, carry a `(default: …)` note.

This matters twice over. A default is not a promise — `minimum_enemy_difficulty` moved 0 → 25 → 0
inside one day this month, and anyone holding an empty yaml across that would have rolled a seed
they never asked for. And "post your yaml" is the first thing anyone says in a support thread, which
is not a useful thing to say when the yaml is two braces.

_(The unglamorous half, for whoever writes the real notes: two options default to a value that is
illegal to write down — `-1`, which only exists as the name `auto` — so filling the file in nearly
made it un-generatable. That is in the changelog, with the tests.)_

## What carried over from v0.4.3

Nothing is owed. v0.4.3 shipped complete -- its changelog section and its blurb were both written
while the window was open, which is what rule 14 asks for and what the two versions before it did
not manage. The contract is unmoved at `5c2b9bf2`, the shape it has had since 0.3.9, so a v0.4.3
client still handshakes with a v0.4.4 seed and no client half was needed to open this.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel
before it says what was built, and that is the right order.
