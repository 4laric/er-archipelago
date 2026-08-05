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

## Known state

The contract handshake has not moved since v0.3.0, so an older client still connects. Seeds rolled
on this version are not the seeds v0.3.4 rolled — the data hash has moved.
