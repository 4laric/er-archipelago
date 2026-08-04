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

## What is NOT fixed

There are still 134 checks whose description is a raw map id like `m60_42_50` rather than a place.
Those are not a matching problem — the game data has no recorded position for them at all, so
nothing spatial can reach them. They need a different source, and that work has not started.

## Upgrading

**No new DLL needed for the data half.** The client's version string moves in lockstep so it reports
the build you are actually running, but nothing in its behaviour changed in this window. If you are
already on the v0.3.3 DLL you can keep it — you will just see it announce the older version number.

Seeds already in progress are unaffected: every change here is to the names and descriptions attached
to checks, not to what is placed where. A NEW seed rolled on v0.3.4 differs from one rolled on v0.3.3
because the data hash moved.
