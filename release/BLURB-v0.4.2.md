# v0.4.2 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

### Metyr is reachable again

Metyr, Mother of Fingers is at the end of Count Ymir's questline, and that questline runs through
two sets of Finger Ruins that are not in the same region — Rhia in Scadu Altus, Dheo in Jagged Peak.
Ring both bells and the throne in the Cathedral of Manus Metyr opens. Keep one region and seal the
other and, in vanilla terms, it never can.

The run has always known that and has always cheated it, by switching on the flag the game works out
from the two bells. It turns out that flag only opens the throne. Ymir himself is watching the
bells, so he stayed seated, his dialogue never ran out, and the quest stopped dead with the door
technically open behind him. So the run now rings the bells instead and lets the game work the rest
out for itself.

It rings as few as it can. Dheo always, because that is the one on the far side of a region
boundary. Rhia only when Scadu Altus is sealed — if you kept it, you ring that bell yourself with
the Hole-Laden Necklace, exactly as you would in a normal playthrough, and the check there is still
yours to earn.

One oddity to expect: if your seed keeps Jagged Peak, the Crimson Seed Talisman +1 at the Finger
Ruins of Dheo will collect itself the moment you walk in. The game hands out that reward for a bell
that has already been rung, and from its point of view yours has.

## What v0.4.2 does not change

`CONTRACT_HASH` is unmoved at `5c2b9bf2`, the same shape the contract has had since v0.3.9. The
client and the apworld handshake on that hash, not on the version number, so a v0.4.1 client
generates and plays a v0.4.2 seed and the other way round. Nothing in your yaml needs to change, no
seed you have already rolled is invalidated, and there is no reason to re-download the client unless
a later entry in this file gives you one.

## If you are upgrading

Take the bundle from the release page as usual. The apworld and the client in it are built from the
same commit, so there is no pairing to check by hand.
