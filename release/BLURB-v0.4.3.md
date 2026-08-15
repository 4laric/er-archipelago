# v0.4.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

**A bad `start_region_pool` now fails like a yaml problem instead of a crash.** If you name fewer
regions in `start_region_pool` than you ask for in `start_regions` -- one region, two starting
regions -- generation used to stop on a Python traceback. Worse, the message buried in it told you
to raise `num_regions`, and that road is closed: `start_region_pool` cuts the pool down to the
regions you named before the starting regions are drawn, so a bigger seed just grows a set the
option shrinks again. A tester followed that advice at `num_regions: 9` and got the same crash back.

The refusal now names both options, both numbers and the regions you actually listed, and offers the
two fixes that work: list more regions, or start in fewer. Nothing about a yaml that already
generated changes -- if your pool is big enough for your count, this is invisible to you.

**Roundtable Hold, Fringefolk Hero's Grave, the Stranded Graveyard cliff and the Chapel of
Anticipation intro now scale.** They never did. Those places sit in three play_region buckets the
run deliberately never kicks you out of -- the Hold is home, and being ejected mid-intro used to
crash the game -- and difficulty scaling was reading that same exemption list, so it left them at
full vanilla strength. The result was quiet and easy to misread: everything else in a fresh seed sat
at the lowest difficulty tier, and the Grave was the untouched game. The same enemy measured 7,141
HP there against 3,386 HP one region over, and one boss in that bucket had 31,518 HP in a seed where
the biggest boss anywhere else had 6,564. The Hold was the same bug wearing a friendlier face: the
invader who turns up in the one room you always come back to was fighting at endgame strength in a
seed you had barely started.

All four now take the LOWEST difficulty in your seed, not the tier of the region they happen to sit
next to. That is deliberate: they are the ground you reach in the first five minutes and keep
walking back through, so they should never be the hardest thing you have met. You are still not
kicked out of the intro, and the Hold is still safe.

One honest caveat about the Hold. The scaling client can only bring an enemy down if it recognises
what it is looking at, and nothing vanilla placed in Roundtable Hold carries the marking it reads.
Being on the list is what gets the room looked at at all; whether the invader himself comes down is
the next thing to measure, and it will be measured in a game rather than argued in a file.

Every change that lands from here writes its own line while somebody still knows what it was for,
rather than being reconstructed from a commit log at release time.

**A Great-Rune goal wants SPECIFIC runes, and now every document says so.** `goal_great_runes: 4`
never meant "any four". The seed names four, only those count, and the yaml said "collect
`goal_great_runes` Great Runes" -- which reads as any four. Someone finished a run holding four
Great Runes, got no victory, and had to open his spoiler log to find out why. The yaml, the player
guide, the README, KNOWN-ISSUES and the wizard's own option text now all say "a specific set, not
any N", and all point at the same place for the answer: your client prints the required names the
moment you connect, on the line beginning `goal: N item(s) must be HELD`. That line is the
requirement, so the spoiler is no longer the only route to it. Do not guess the set from a pattern --
today it is the alphabetically first N of the runes your kept regions can reach, which looks like a
rule and is not one to bet a run on. The names are still not shown IN GAME; putting them in the
connect banner is client work and is not in this release.

## What v0.4.3 does not change

`CONTRACT_HASH` is unmoved at `5c2b9bf2`, the same shape the contract has had since v0.3.9. The
client and the apworld handshake on that hash, not on the version number, so a v0.4.2 client
generates and plays a v0.4.3 seed and the other way round. Nothing in your yaml needs to change, no
seed you have already rolled is invalidated, and there is no reason to re-download the client unless
a later entry in this file gives you one.

Three options were retired during the v0.4.2 window -- `local_item_only`,
`exclude_local_item_only` and `progression_surface_mode` -- and that happened in v0.4.2, not here.
If your yaml still names one of them, that is the release to read, not this one.

## If you are upgrading

Take the bundle from the release page as usual. The apworld and the client in it are built from the
same commit, so there is no pairing to check by hand.
