# v0.4.2 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

This window is mostly about things that looked right and were not. A Great Rune that the capital
gate would not count, a hint that named a perfume bottle and not the boss holding it, a quest that
opened its own door and then stood in it, and progression parked behind bosses that do not exist.

## Your Great Runes now count

If you have stood at Leyndell's gate holding two Great Runes while it refused to open, this is why.

Elden Ring has two items called "Godrick's Great Rune". One is what Godrick drops. The other is what
the Divine Tower hands back after you restore it. They are separate rows in the game's data, and
only one of them is the thing the capital gate counts — and since the item pool existed, the run has
been giving you the other one.

Everything about it looked correct. The rune appears in your Great Runes menu. You can equip it. Its
blessing works. The run even marks it restored for you so you can skip the Divine Tower. It simply
was not the item the door is looking for, and nothing anywhere said so.

Six runes were affected, and eight other items had the same problem for the same reason — two rows
sharing one name, and the run picking whichever came first. Crystal Tears, Golden Vow, the Unalloyed
Gold Needle, a couple of Scorpion Stews. The rule now is that a check gives you whatever its own
drop actually contains, which is what you would have assumed all along.

**If you are mid-run on a v0.4.1 seed and stuck at that gate**, this is your fix, but it arrives
with the apworld — the runes already in your inventory are the old row and will stay uncounted. A
fresh seed is the clean answer.

## Hints tell you which boss to kill

Under `SweepSlot` a region Lock can sit on a check that some boss hands over when it dies — which is
the point of the feature, and made for a baffling hint:

> bobler's Altus Lock is at Mt. Gelmir :: Perfume Bottle - near Craftsman's Shack

Perfectly true, and no help at all. Sweep members now say who sweeps them:

> Mt. Gelmir :: Perfume Bottle - near Volcano Manor, **also granted by Godskin Noble (m16_00)**

It says "also granted by" rather than "go kill", deliberately. The pickup is still sitting there and
walking to it still works; the boss is an additional route, not an instruction. The map tile comes
along because the names are not unique — there are eight different Night's Cavalry sweeps, and
naming one without the tile would be barely better than saying nothing.

## Progression stopped hiding behind bosses that do not exist

Someone cleared all nineteen Limgrave bosses in a boss-sweeps-only seed and still had two
progression checks sitting there unopened. One was swept by the Divine Tower of Limgrave, which has
no boss. The other was swept by Patches, who yields instead of dying.

Neither sweep can ever fire, so neither may hold progression any more. If a trigger cannot be
vouched for, the run does not put your key behind it.

## Metyr is reachable again

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

## Also in this window

- **Catacomb boss doors open on arrival.** Walk in and fight, rather than hunting the lever first.
  The ancestor altars light with them.
- **Three options retired**: `local_item_only`, `exclude_local_item_only`, `progression_surface_mode`.
  If your yaml still names them, generation ignores them rather than failing.
- **A Bonny Gaol pickup was a live Limgrave check** pointing at ground you could only reach with the
  DLC. Fixed, with a new gate that stops the whole class: no base-game region may hold a check whose
  nearest grace is in a DLC map.
- **Five documentation claims that were false** are corrected — the Academy and capital graces do
  *not* light when their key item arrives, there are three gated regions rather than two, and
  `ending_condition: great_runes` needs a specific set of runes rather than any N of them.

## Compatibility

`CONTRACT_HASH` is unmoved at `5c2b9bf2`, the same shape the contract has had since v0.3.9. The
client and the apworld handshake on that hash, not on the version number, so a v0.4.1 client
generates and plays a v0.4.2 seed and the other way round.

Two things did move, and neither breaks a room that is already running:

- **4000 location names gained a "also granted by" clause.** An Archipelago server serves the names
  from the seed it generated, so a room in progress keeps the names it started with. The PopTracker
  pack matches on location ids rather than names, so it is unaffected.
- **Six Great Runes and eight other items now resolve to a different underlying game item.** This
  only applies to seeds generated on v0.4.2. A rune already in your inventory from an older seed is
  the old row.

So: nothing you have rolled stops working, but a v0.4.1 seed blocked at the capital gate stays
blocked. That one wants a re-roll.

## If you are upgrading

Take the bundle from the release page as usual. The apworld and the client in it are built from the
same commit, so there is no pairing to check by hand.
