# v0.3.11 -- release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

**Traps, if you want them.** Off unless you ask:

    traps: [rune_thief, no_flask, runebear]
    trap_count: 8

Rune Thief takes half your runes. No Flask leaves your flask healing nothing for twenty seconds --
you can still drink it, it just does nothing, and the charge is spent. Runebear puts a Runebear
exactly where you are standing, and if you kill it you keep the runes. They are ordinary items in
your pool, so in a multiworld somebody else may be the one who finds them, and each one replaces a
junk item rather than adding a check -- your seed does not get any longer, only meaner. boblerrr
asked for it as "enemy horde on your head".

**Your spells get memorised now.** Receiving a sorcery or an incantation used to leave it sitting in
your bag with memory slots free. It is placed for you, in the right kind of slot for what you are
holding -- a seal takes the incantation, a staff takes the sorcery -- and spells that arrived under
an earlier build, before anything could equip them, get picked up rather than stranded there
forever. Long spells that used to cost two or three slots now cost one, so nothing is unplaceable
until you have earned enough of them.

**The last fight was the one fight that was never scaled.** Enemy scaling skipped the entire
endgame -- the Ashen Capital and the Elden Throne, where your goal fight happens -- because that
part of the map is minted rather than rolled and every path in the code was looking at the rolled
list. Across seven of boblerrr's seeds it appears exactly zero times. It is on the wire now, at the
top of the band.

**Light roll actually works, and it is a real option again.** `no_equip_load` was writing to a field
the game has never once read as a multiplier. The plumbing was fine, the logs were honest, the field
was wrong. It now does what it says -- and a medium-roll setting is built on the client side, waiting
on its yaml half, because a fast roll in full plate with no trade-off makes the equip-load budget
stop being a decision.

**Charo's Hidden Grave and the Stone Coffin Fissure are part of the Cerulean Coast.** They are one
contiguous stretch of the south-west coast and each was far too small to stand alone -- 43, 26 and 21
locations against a median of 100 -- which is how a seed keeps one of them and strands your checks in
the other two. They are one region of 90 now. Your seed is the same size it was; only the labels
moved.

**And an item that told you the wrong part of the map now tells you the right one.** Two players
reported it independently. Half the overworld tiles carrying checks have no site of grace on them, so
those checks were being filed under whichever neighbour did -- Ghostflame Call was on the Cerulean
Coast when it is in Charo's Hidden Grave. The table that gives each tile its own answer had been
sitting in the repo the whole time; generation reads it now.

**Stormveil's merchants are in Stormveil.** Gostoc's and Rogier's shop checks were being filed in
Limgrave and Liurnia, and 53 shop flags in total were labelled with the wrong region, because a
merchant who could not possibly be standing where the table claimed did not add a wrong answer -- it
quietly removed the right one.

**Five sites of grace came back.** Three merchant shacks, Azur's ledge and one behind a fort were
being withheld as boss-arena graces because a boss stands somewhere near them -- in three cases a
Bell Bearing Hunter who only spawns at night.

**And the card that tells you what you are sending other players now works at all.** It shipped
telling everyone "Shuffle Vanilla Items is off, so there are no real items to send", which was never
true -- it was reading a setting that had been frozen out of the yaml weeks before, getting nothing
back, and treating nothing as off. It now shows how many of your checks another player's item can
land on, how many of your items are free to travel (the same number, read from either end -- the fill
is count-neutral), and how many of your checks another world's key items may sit in. That last one is
where `confine_foreign_progression` bites, and the card now says what we measured: leave it at 100
and a non-Elden-Ring partner gets filler from you and nothing else.

**The options wizard grew tabs.** All 54 settings used to sit in one collapsed section called
"Other Options", in the wizard's last step, under a line telling you everything there was safe to
skip. Enemy scaling was in there. So was the pool builder, and the progression surface, and every
shop setting. They are now seven steps you walk through -- Goal & Regions, DLC & Blessings,
Difficulty & Scaling, Checks & Item Pool, Multiworld & Placement, Shops & Merchants, Quality of Life
-- with the ones you have touched lit up in the rail. Your yaml comes out exactly as it did before;
this is only about being able to find the thing you were looking for. The same grouping now shows up
on Archipelago's own player-options page too, because both read it from the same place.

**Keep your gear out of the shops.** A new setting, off unless you ask for it:

    keep_out_of_shops: [weapons, armor]

and no merchant of yours will stock a weapon or a piece of armour again. They are still shuffled and
still yours to find -- they are just out in the world, where finding one is a matter of going
somewhere rather than of having enough runes. boblerrr asked for it looking at a shelf of weapons,
gauntlets and helms priced up to 25,000 with 11,144 runes in his pocket, and he had a point: a fifth
of every purchase-menu check in the game pays gear, and on a short seed the merchant more or less IS
the world.

It takes any category, not just gear -- `[consumables, crafting]`, `[spells]`, the same list Keep
Local uses -- and it covers the unlimited shelves as well as the checks.

On a very short seed there may simply be nowhere else to put it all, and rather than quietly doing
nothing the option takes what fits, skips what does not, and writes down which was which. Ask for
weapons and armour on a one-region seed and you will get weapons kept out and a line in the log
explaining that armour would not fit and by how much.

**Progressive Stone Bells actually paces you now.** The setting collapses the Miner's Bell
Bearings into two progressive items, so the Twin Maidens' smithing shop opens a tier at a time instead
of all at once when you happen to find the right bearing. Except that the ordinary bell bearings were
still in the pool alongside it -- and one of them is the top of the somber shop. boblerrr picked up
`Somberstone Miner's Bell Bearing [5]` in Enir-Ilim and the ladder was simply over. Turn the option on
now and there are no loose bell bearings to find; turn it off and everything is exactly where it was.

**The options template downloads and loads again.** If you pulled the default Elden Ring yaml
from Archipelago and it came back at you with `Duplicate key False found in YAML`, that was ours and
it is fixed. One setting listed both `off` and `false` among the words it accepts, and to a yaml file
those are the same word -- so the template Archipelago generated for this game held the same key
twice and Archipelago would not read its own file back. Writing `on` or `off` in your yaml still
works exactly as before; nothing you have already written needs touching.

**One fewer free skip in the burnt capital.** Unlocking the Ashen Capital used to light its Queen's
Bedchamber, which is on the far side of the Erdtree Sanctuary -- so the region lock handed you a warp
straight past Sir Gideon. It does not any more. The base game's version of that grace was fixed a week
earlier for the identical reason; the burnt one had simply not existed as a bundle yet when that call
was made.

**Smaller things you will still notice.** A DeathLink that kills you now says so on screen instead of
only in a log file. Handing a merchant's bell to the Twin Maidens shows up in the client feed, not
just as a toast that expires. The connection template points at `archipelago.gg:PORT` rather than a
port number that could never have been right, and a port that is not a number now opens the connect
form instead of a retry loop of parser errors. And if you want the old Limgrave-first region order
back, it is an option again -- `num_regions_order: vanilla_order`, opt-in, with random still the
default and every existing seed unchanged. A Region Lock now tells you whether it warps you in or only
lets you walk in. And the F6 tracker fits its own window, stops leaving a swept group looking stuck
when its region is unreachable, and clears groups that have already paid out.

## For the technically minded

Nothing in the contract moved. A v0.3.10 client and a v0.3.11 seed still speak to each other, and
the reverse holds too -- the version bump exists so that a bug report can name exactly one build.

The client can now sample player and boss HP through a boss fight, roughly twice a second, and it is
on by default. Every scaling complaint so far has ended in a log dig and an argument because nothing
recorded what the fight actually was; two HP curves settle it. It also reconciles, once per connect,
what the seed DECLARED against what actually ARMED -- which is the check that would have caught the
merchant-bell option shipping wired to nothing.
