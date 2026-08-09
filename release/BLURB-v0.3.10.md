# v0.3.10 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

### Killing a boss grants more of what is around it

One player killed Commander Gaius in the Shadow Keep and got a single check. Bosses hand you the
loose items near them when they die, and Gaius stands on an open tile with almost nothing on it --
so he was supposed to be topped up with a share of whatever else in the region no boss had claimed.
He never was, because the Shadow Keep's West Rampart has no boss of its own, and a stretch of map
with no boss was being left out of the pot for exactly that reason.

Now it is in. The Shadow Keep's outdoor bosses hand over five to seven checks instead of one, the
Siofra River gains a handful, and 49 checks across the game stop falling through.

What this does not do is even out the big fights. Belurat still keeps 82 of its 93 checks behind the
Divine Beast Dancing Lion, because Belurat has one boss and there is nobody else to share them with.

### Your DLC-only run ends on Promised Consort Radahn now

If you play `dlc_only` and leave `goal` alone, the run used to end wherever your draw happened to
reach -- for one player this week, on Romina in the Ancient Ruins of Rauh, well before he expected an
ending. Nothing was broken. The base game's finale is guaranteed because the Ashen Capital is not a
region you can roll: it is there on every seed. Enir Ilim is an ordinary DLC region, so Radahn was
the ending only when the draw felt like it.

Enir Ilim is now handled the way the Ashen Capital is. It is taken out of the draw and always kept,
so `num_regions: 3` means three regions to play **plus** the ending. It stays a real region you
explore, with its own checks and its own Lock -- it is a place you play, where the Ashen Capital is
ten checks and a gauntlet.

### ...and it can no longer be where your run STARTS

The region you end in should not be the region you open in. It could be: on the previous build,
14.7% of `num_regions: 6` DLC-only seeds opened on Enir Ilim, and 59.6% at `num_regions: 1`. That is
fixed for `goal: promised_consort` as well as for the default -- whatever your goal keeps, your run
will not begin there.

### Your Region Locks can end up in other players' games

Until now they never did. Not because anything forbade it -- Elden Ring's own settings leave them
free to travel -- but because they were quietly placed at home before the multiworld fill ever got a
look at them. Measured on the last build: across eight two-player seeds, **not one of 105 Region
Locks reached the other player**, while half of everything else did.

There is a new setting, **Progression Bias**, and at its default your Locks are ordinary multiworld
items. In a two-slot game a little under half of them end up in the other player's world, so you may
well be waiting on somebody else to find your way into Liurnia. That is Archipelago working the way
it is supposed to, and getting stuck behind someone is part of the deal.

Turn it up if you would rather keep them: 100 pins every Lock at home, which is what every previous
version did, and 40 reserves about 40% of them for you.

**A Lock that travels is still on a check worth finding.** It is held to the same set of vetted
locations everyone's progression is held to, so it lands on somebody's boss or remembrance rather
than on a random crafting material -- just not necessarily yours. If you want progression scattered
across ordinary pickups, that is a different setting and it is still there.

One consequence worth knowing: the stars in your tracker now mean "a progression item can be here",
which may be yours or another player's. They used to mean your Locks specifically.

### A crash at the very end of generation

If you were unlucky with settings, generation could do all its work, fill the whole seed, and then
fail while writing the spoiler. That is fixed. It was found by fuzzing thousands of random settings
combinations rather than by anyone hitting it, and it predates this release.

## What just shipped, for context

v0.3.9 is the release this window follows, and it is worth knowing what a player already has before
adding to it: **Grace Attunement** (a region hands over one Site of Grace on unlock and the rest bloom
once you have touched a few), a progression-surface picker in the options wizard that finally says
what each class actually selects and what ticking it is worth, the `Boss` location class corrected
from 143 checks to 214, the `Shop` umbrella corrected to actually contain its own members, and 29
checks that shipped with no item name getting one.

## Compatibility

`CONTRACT_HASH` is unmoved at `5c2b9bf2`, so v0.3.10 opens version-lockstep with v0.3.9: the version
number moves in step with the client, the wire between them does not, and a v0.3.9 client still
handshakes -- including with a seed that has grace attunement turned on, which was the single
version-sensitive setting v0.3.9 introduced.

If that changes while this window is open, this section is where it gets said, and the ledger row in
`release/CONTRACT-VERSIONS.tsv` is what makes the claim checkable rather than remembered.
