# v0.3.4 — release blurb (draft, window OPEN)

> Opened 2026-08-04 on the first change of the window (rule 14) — and opened late. v0.3.3 was tagged
> the day before while `APWORLD_VERSION` still read `0.3.3`, so the first entry below spent a day
> filed under a version that had already shipped. `CONTRACT_HASH` is unmoved from v0.3.0, so the
> handshake is unchanged and older clients still connect. The `data/` hash moves, so this rolls
> different seeds than v0.3.3 did.

**This one is about knowing where things are.** Two changes, and both of them are about the same
complaint: you get a hint, or you look at your tracker, and the place it names is not where the item
is. One was fixed by hand and one by finding the bug underneath it.

- **Every Golden Seed and Sacred Tear now tells you where it actually is.** All 56 were walked and
  described by hand. "Golden Seed - around War-Dead Catacombs" is now "Putrid Tree-Spirit drop in
  War-Dead Catacombs"; the Stormhill Shack seed says it is what Roderika leaves behind when she moves
  to the Roundtable; the churches are named as churches. Nine of them stopped saying "(region
  unconfirmed)" and can now hold progression.

- **Checks that were pointing at the wrong Site of Grace now point at the right one.** The tool that
  works out which grace a check is nearest could not read one of the two coordinate formats the game
  uses, so 421 checks silently failed to match anything at all, and a handful matched a grace on the
  far side of the map — a "Golden Seed near Altar South" that was nine kilometres from Altar South.
  Seventeen location names improve directly, mostly from naming a whole region ("around the Altus
  Plateau") to naming somewhere you can actually walk to.

- **36 items that were quietly never randomized now are.** Some pickups were never registered as
  checks at all, so you would walk up, grab them, and get the vanilla item while the tracker showed
  nothing — Kalé's and Gostoc's Bell Bearings, most of the merchant Bell Bearings, the Glintstone
  Kris, the Royal Greatsword, a handful of Ashes of War. Three field bosses that dropped nothing of
  interest now have a check on them.

## What is NOT fixed

Thops still drops his vanilla Academy Glintstone Staff, and 63 other items like it are still not
checks: nothing in the game data we can read says where they are, so placing them would be a guess.

There are still 134 checks whose description is a raw map id like `m60_42_50` rather than a place.
Those are not a matching problem — the game data has no recorded position for them at all, so
nothing spatial can reach them. They need a different source, and that work has not started.

## Items that were being thrown away

If you have ever wondered why a pot you were clearly sent never showed up, this is why. Elden Ring
caps how many of an item you can hold, and once you are at the cap the game quietly refuses the next
one -- but the multiworld has already marked it delivered. Nobody sees an error. The item is just
gone.

A default seed was placing 21 of them: Cracked Pots, Ritual Pots, Perfume Bottles and Hefty Cracked
Pots, counted together with the ones you start with. Thirteen other items had the same problem more
quietly -- a duplicate Whetstone Knife, a second Cursemark of Death, a ninth Memory Stone.

The generator now knows the game's own limits and does not place items you could not receive. Those
slots become curated filler instead, so seeds hold exactly as many items as before and you get
something you can use.

Consumables are untouched on purpose. You will still be sent far more Golden Runes than you can hold
at once, because you spend them and the stack drains -- those arrive late, not never.

## Upgrading

**No new DLL needed for the data half.** The client's version string moves in lockstep so it reports
the build you are actually running, but nothing in its behaviour changed in this window. If you are
already on the v0.3.3 DLL you can keep it — you will just see it announce the older version number.

Seeds already in progress are unaffected: every change here is to the names and descriptions attached
to checks, not to what is placed where. A NEW seed rolled on v0.3.4 differs from one rolled on v0.3.3
because the data hash moved.
