# v0.3.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**Which regions you get is now actually random.** This is the one most people will notice. The
default order kept the first N regions of a fixed path, which meant every default seed kept the
*same eight*: Limgrave, Weeping, Stormveil, Liurnia, Raya Lucaria, Caelid, and Leyndell with Altus
riding along behind it. Nine base regions could never appear at all at the default region count, no
matter what seed you rolled. They can now: over 3000 seeds every base region turns up in 34-37% of
them, and none is excluded.

If your yaml sets `num_regions_order`, delete the line. There is only one behaviour now; the old
value still rolls for this release and warns, and the key goes away after it. Two things the guide
used to say about it were wrong and are now fixed: it was never the default, and it never set which
region you start in — your opening region has always been a separate draw of its own.

**Naming a goal no longer drags the capital in with it.** If you set `goal: promised_consort`, the
seed kept Enir Ilim *and* Leyndell *and* Altus, every single time, whether or not you had any use
for a capital. That also quietly handed Altus a quarter of all opening-region draws. The goal region
is force-kept only when you have not named a goal — which is the case where it has to be there, so
the run has an ending to find. Seeds on the default goal are unchanged, down to the roll.

**Key items behave the way you expect them to.** If you have played matt's randomizer, the mental
model is "the important keys live on the important checks". This release moves us toward that. The
missable bar used to cover every item an NPC hands you, on the reasoning that an NPC can die — but
more than half of those are handed over the first time you talk, with no questline state behind
them at all. Those now count as places progression can live. In practice that means the Rold
Medallion, the Drawing-Room Key and the right Haligtree Secret Medallion stop being dead ends for
the fill, and four more key items get recognised as key items at all.

The distinction we kept is the one that actually bites: an item you can lose by advancing a
questline still cannot hold anything required. Rya's Necklace is barred for that reason and the
Fingerslayer Blade for a related one — you hand it to Ranni.

**Shop stock behind a questline cannot hold your progression any more.** A player found a Limgrave
Lock — this world's own progression — on a Night Shard sold by Sage Gowry, whose entire stock is
locked behind his questline. Two separate things were wrong. Gowry sells nothing but spells, so he
should never have been eligible in the first place, but "dedicated spell vendor" was measured over a
block of shop rows rather than over the merchant, and his rows sit in the Twin Maiden Husks' block —
so a seller with 100% spells inherited a general store's ratio. Any spell in a merchant's stock now
disqualifies it, judged per merchant: five excluded blocks became seventeen excluded merchants.

The second is stricter and worth stating plainly: a merchant can hold required items only if there
is at least one *unconditional* way to reach their stock. Of the 44 non-spell merchants, 22 qualify.
Gostoc, Patches, Bernahl, Thiollier, Blackguard, Rogier, Moore, Pidia and Iji do not, because each
is an NPC you must first advance. That took the shop slots able to carry progression from 15 to 12 —
Moore, Pidia and Iji dropped out.

**A run now ends on something that actually ends the game.** From a report: *"My run ended with
leyndell not ashen capital but morgott was already dead so it ended on bayle."* The goal used the
deepest kept region by progression order as a stand-in for "the end", and the DLC breaks that
stand-in — Jagged Peak sits near the end of that order, but Bayle is an optional dragon on a
mountainside, and deeper still is Rauh Base, where the run would end on a bear. Across 3000 DLC
seeds, Bayle ended 10.9% of them and Rugalea 9.3%; only 38% ended on a boss that finishes anything.

The goal now walks the genuinely terminal bosses first — a legacy-dungeon boss, a Remembrance, or a
Great Rune holder. Non-terminal endings are 0.0% in both pools. The three-way test is load-bearing
and each part alone gets it wrong: Remembrance alone demotes the Shunning-Grounds, whose Mohg drops
an incantation, and legacy-dungeon alone demotes Astel, Fortissax and the Fire Giant.

**A region fix you may notice.** Rya's Necklace was filed under Altus because of a bad map join.
It is handed to you at Boilprawn Shack, in Liurnia, which is where it now lives.

**Enemy scaling: the mismatch you have been reporting.** If you have hit a fight where one enemy
folds instantly and the one standing next to it takes four times as long and one-shots you, this is
the release that addresses it. The cause was that we could only re-tier enemies the base game had
already tagged with an area-scaling effect. Everything else — hand-tuned NPCs, and a good deal of
ordinary trash — kept its vanilla strength while its neighbours were moved to the region's level, so
the gap between them was widest exactly where the region's level was furthest from what the base
game intended for that ground.

Those enemies are now placed too. Where an enemy carries nothing we can read a strength from, we
read the ground instead: what the base game says about the *other* enemies standing in the same
region. In one Weeping Peninsula sweep that took the number of enemies left out of step from 69 down
to zero.

**Named characters are deliberately left alone.** Bosses and the named NPC invaders are tuned by
hand, and their stats already assume you meet them late — so applying a region's multiplier on top
of that produces exactly the boss that one-shots you through a full flask. They keep their vanilla
strength unless the base game gave us something to read on the enemy itself. The trade is honest and
worth stating: in a deep region a named invader will now be softer than the enemies around it. We
would rather that than the reverse.

**The difficulty floor is back to 0.** v0.3.4 shipped a floor that raised every enemy in the
shallowest regions to roughly 2.3x, on the strength of arithmetic that turned out to be wrong — the
base game's own floor is lower than we had calculated. Raising it again is not off the table, but it
will take a measurement rather than a calculation.

**The spoiler's scaling table now describes the seed you are playing.** If you set
`difficulty_ramp_speed`, the table printed the *unramped* curve — so a region could read as third
easiest in the spoiler while the game scaled it to the top tier. The wire was always right; the
report was not. The table now names the ramp speed it was computed with.

## Known state

The contract handshake has not moved since v0.3.0, so an older client still connects. Seeds rolled
on this version are not the seeds v0.3.4 rolled — the data hash has moved, and the region draw
changed on top of that, so a yaml you rolled last week will not give you the same regions.

`num_regions_order` is deprecated rather than removed: a yaml that still sets it generates fine and
warns. It is removed after this release, so this is the window to take it out of yours.

The scaling changes above are client-side, so they need the matching client build; the apworld
alone will not deliver them. The enemies left out of step were never made *harder* than the base
game by us — the complaint was always about the gap between neighbours, not about a wall — so an
older client is playable, just less even.
