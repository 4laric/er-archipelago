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

### Red Wolf of Radagon is a major boss now, and so are nine others

Ask anyone which bosses in Elden Ring are the major ones and you get much the same list. Ours was
missing ten of them — Red Wolf, Godskin Noble, Godskin Duo, the Valiant Gargoyles, Mimic Tear, the
Dragonkin Soldier of Nokstella, Royal Knight Loretta, Elemer of the Briar, Commander Niall, Margit —
because the list was typed out by hand, and a hand list is only ever as complete as the afternoon
someone spent on it.

It is not a list any more. The game already knows which bosses are major: it hands you an achievement
for each one, and the achievement is wired directly to that boss's death. So we read the game's own
table instead of maintaining ours. All ten missing bosses came back, along with two more we had not
noticed were gone, and four entries dropped off that were only ever there to fill a gap that no
longer exists.

What you feel: your region Locks and Great Runes now sit on the bosses you would expect them to sit
on, in twelve more places than before.

Margit took one extra step and it is the best story here. He looked unfixable — no boss drop of his
anywhere in our data, we thought, only the Shackle you buy at the Roundtable. Wrong: he drops the
Stormveil Talisman Pouch, and the game had been saying so all along in an event file literally
labelled *Defeat Margit*. We had been throwing that line away, because killing Morgott also
retroactively ticks Margit off, and our reader could not tell "this boss pays this item" apart from
"this boss counts as having done it for you". Now it can, and one pouch that had never been marked as
anything is a major-boss check.

_(For the real one: the good line is that three of the seven hand entries we deleted turned out to be
the exact checks the achievement table derives. The list had been rediscovering the game's own answer
one region at a time. The other good line is that fixing Margit deleted the Agheel entry by itself —
Agheel and Godefroy were the two bosses matt's roster pointedly excludes, and neither was removed for
that reason.)_

### The Academy Glintstone Key is not a second lock any more

You get the Raya Lucaria Academy Lock, and until now the client told you *"walk in, the Academy
Glintstone Key opens it (no grace warp)"* — a Lock that unlocked nothing you could act on, and then
a key hunt on top of it. The key was buying a wall the Lock already is.

The Lock grants the Academy's graces now, same as every other region. The Glintstone Key is just an
item you might find. Rennala's Great Rune of the Unborn was sitting behind that key too, and isn't.

### The Unborn rune counts

Rennala's Great Rune of the Unborn is the one Great Rune whose name doesn't end in "Great Rune", and
our code checked for that ending in four different places. So the game called it a Great Rune and we
didn't: it couldn't count toward `great_runes_required`, couldn't open the capital, couldn't be
handed to you to repair a seed that was short. Seven runes now, everywhere.

### You can exclude the catacombs

96 of the 267 boss checks had no sub-class — every catacomb, cave, tunnel, gaol and Divine Tower
boss. If you wanted them on your progression surface you ticked `Boss`, and that dragged in every
field boss and every legacy boss with it. `MinorDungeonBoss` is its own thing now, so "the little
dungeons, not Margit" is a sentence you can say to the wizard.

The wizard also draws the classes as the tree they actually are. Remembrances and Great Runes sit
*inside* major bosses, which is why ticking them changed nothing — the page said so in small text
beside a checkbox and now it says it in the shape.

### Foreign exports have a dial

`filler_foreign` used to behave like an on/off switch. It spends a copy budget per category now, so
every category can still travel, and it ships at 70 — the measured even split in what your partner
actually receives.

## What carried over from v0.4.3

Nothing is owed. v0.4.3 shipped complete -- its changelog section and its blurb were both written
while the window was open, which is what rule 14 asks for and what the two versions before it did
not manage. The contract is unmoved at `5c2b9bf2`, the shape it has had since 0.3.9, so a v0.4.3
client still handshakes with a v0.4.4 seed and no client half was needed to open this.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel
before it says what was built, and that is the right order.
