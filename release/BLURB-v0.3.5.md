# v0.3.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

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
on this version are not the seeds v0.3.4 rolled — the data hash has moved.

The scaling changes above are client-side, so they need the matching client build; the apworld
alone will not deliver them. The enemies left out of step were never made *harder* than the base
game by us — the complaint was always about the gap between neighbours, not about a wall — so an
older client is playable, just less even.
