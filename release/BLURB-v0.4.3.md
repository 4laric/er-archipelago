# v0.4.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

**You can get BK'ed now, and that is the point.** Until this release your Region Locks could not
leave Elden Ring for another game. Not rarely -- *not once*: four measured configurations against a
Hollow Knight slot returned zero Locks placed in it, including a seed where fifteen of twenty-eight
Locks travelled and every single one went to the *other* Elden Ring world. The valve existed and
structurally never opened, so Elden Ring sat in your multiworld as a game that could send things but
never actually needed anybody -- which is a strange way to play together.

`cross_game_progression` now offers a share of your released Locks to your partners FIRST, before
Elden Ring's own surfaces get their look. It defaults to `auto`: one over the number of games, so
half in a two-game seed, a quarter in a four-game one, and nothing at all when everyone is playing
Elden Ring however many slots there are.

What that means at the table is that a region you need can be sitting in somebody else's game, and
you may have to stop and wait for them. Being stuck is a complaint; the *risk* of being stuck is the
whole shape of a multiworld, and Elden Ring has not been carrying its share of it. **If you would
rather it did not, set `cross_game_progression: 0`** -- nothing else changes.

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

**Nineteen Roundtable Hold checks can no longer be the thing your seed is waiting on.** Sixteen of
them are Patches and Thiollier's stock and three are the Dragon Communion incantations. None of those
sellers actually stands in the Roundtable -- they are filed there because they turn up in more than
one region and the run could not pick one. The side effect was that the run treated all nineteen as
reachable the moment you spawned, so a key item could be placed on them for a player who had no route
to Patches at all. One tester watched it happen: his friend's spoiler put a region unlock on
Furlcalling Finger Remedy "from Patches or Thiollier" in a seed holding none of the three regions
either of them lives in.

Now they are filed where their seller actually stands. If your seed keeps one of the regions that
merchant lives in, the check is gated on reaching THAT region -- the earliest one your seed kept, so
Limgrave if you have it, otherwise Mt. Gelmir, otherwise the Cerulean Coast -- and it can hold
something the seed needs again, because now the run knows what you have to do first. If your seed
keeps none of them, the check goes back to holding filler only: there is no region to put it behind,
so it may not be the thing you are waiting on.

Being strict about it is the point. Patches is reachable from any of his regions, and the run can
only require one at a time, so it requires the earliest one you have -- which is never easier than
the truth, only sometimes harder. All nineteen still exist, still show up in your tracker and still
hand you something. They keep the `(region unconfirmed)` tail on their names, which is still honest:
the check is real, and which of the seller's regions your copy is sitting in is not something the run
can tell you. Everything else in the Hold is unaffected; Enia, the Twin Maiden Husks and the Table of
Lost Grace are genuinely there and are untouched.

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

**Your partners stop receiving four hundred Golden Runes and start receiving gear.** If you have
played Elden Ring beside a smaller game, you have probably sent them a great deal of nothing: our
exports to a non-Elden-Ring world were overwhelmingly runes and smithing stones, which that player
cannot use for anything at all. A Golden Rune in Hollow Knight is not a small prize, it is an inert
one.

Two changes move it. SweepSlot -- the option that lets a boss hand over a progression item -- now
scales with how many people you are playing with, opening more room for a partner's items to live in
your world, which in turn frees room in theirs. The export mix follows: measured on a two-game seed,
the useful share of what reaches your partner goes from **4%** to **35%**, while the amount of plain
filler you send them barely moves. They are not getting more from you. They are getting better things
from you.

**Traps that promised three of something now deliver three.** `Trap: Basilisk x3` had been arriving
as one basilisk, which is the failure the option's own description warns about -- one is a joke,
three is the overlapping Death Blight mist that actually threatens you. The count was never lost; the
game's debug spawner writes into a single shared slot, so three requests fired in the same instant
overwrote one another and only the last survived. They are spaced out now. The client also used to
log the number it *asked* for, which is why this survived so long -- the only way to catch it was to
stand in a room and count. It now counts what actually appeared.

**A trap could spend itself on a lie.** If Rune Thief reached you while you held no runes, it
announced that half your runes were gone, took nothing, and was consumed -- and because the server
had already marked it received, it never came back. It now waits until you have something to lose. If
you have been playing at zero runes for a while, which is more common than it sounds, that was a real
item quietly wasted.

**Items reported delivered but never received are now counted.** When a delivery hit the game's own
cap on how many of a consumable you may hold, it was announced as delivered and then not placed --
and further losses on the same item were silent, so there was no way to tell whether it had happened
once or twenty times. The client now tallies them per item and reports the total when you change
worlds. This does not get the items back; it makes the loss visible, which had to come first.

**The hint list counts what is still outstanding.** Hints for checks you had already collected stayed
in the tracker and kept counting toward the total, so `Hints (9)` could mean two things worth doing.
Collected hints now grey out and stop counting. They stay on the list, because a found hint is still
a record of where something was.

**A Great-Rune goal tells you which runes, in the game.** A `great_runes` seed requires a SPECIFIC
set, not any N of them -- and the only place that said so was the spoiler log. One player finished
holding four Great Runes, sent no victory, and worked out why by reading the spoiler himself. The
required names are now printed at connect, where you are actually looking.

**You get a warning before an ending that will not count.** If you reach the final arena while Region
Locks are still outstanding, the client tells you how many, once. Nothing stops you going in -- but
the ending is irreversible, and finding out afterwards from a spoiler log is the worst possible
moment.

**When connecting fails, the message is about your actual problem.** "Connection refused" and
"connection timed out" are opposite diagnoses -- nothing listening versus something eating the
packets -- and they used to share one line that told you to check your URL, which by that point had
already been proven fine. They are separate now, and the connection breadcrumbs are readable in a
normal log, so a failed connect can be diagnosed from the file you send rather than from a follow-up
conversation.

**Shop checks are filed where their seller stands.** Nineteen checks sold by Patches and at the
Dragon Communion altars were labelled as Roundtable Hold -- the hub, open from your first minute --
while the merchant who actually sells them is somewhere you may not have unlocked. The logic believed
they were reachable immediately; a player in one of our test seeds drew a Scadu Altus Lock onto one
of them and could not go and get it. They now say where their seller is.

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
