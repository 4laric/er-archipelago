# v0.4.1 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**You can turn the curated item pool off.** `vanilla_pool: true` and your checks pay what they pay
in vanilla Elden Ring — no recipe rewriting the junk end of your pool, and no guaranteed set of
physick tears and bell bearings added on top. Off by default.

Half of this was already possible and that turned out to be the problem: emptying `curated_filler`
gave you a vanilla filler tail, but the tears and bell bearings came from a second feature that no
yaml could reach, so a seed built that way still handed you up to 18 tears vanilla never placed. It
looked like it had worked. The playtest report behind this was somebody counting 19 tears against a
catalog of 37 and concluding items were missing — 19 being the 18 guaranteed ones plus the one his
seed actually kept. One option now does both halves.

It is a real trade, so know what you are buying: no gear injection, no smithing-stone or rune
economy, and no promise that a physick tear exists at all in a seed that seals its home region.
That is what the curation was for. If you only wanted *less* gear, turn `juice` down instead.

**The new front page can actually be deployed now.** v0.4.0 shipped the deploy step for it
pointing at a path the site does not serve: `peliarch.ca/` is not a static directory, it is an
application route, so the file would have been written, reported as installed, and never appear.
Nobody would have found out until the front page failed to change after a deploy that said it
worked. It installs beside the options wizard and the check browser now, by the same atomic,
tag-pinned copy those two already use -- one directory, three pages, one deploy.

**Room hosting on peliarch.ca is retired.** The site is the yaml builder, the downloads, the
documentation, the check browser and the bug report form. It does not generate seeds and it does
not host rooms; archipelago.gg does that properly.

The reason is worth stating plainly. The rooms dashboard offered five different rooms **the same
connect address** and a Copy button beside it. Ports are genuinely handed out one per room, so
that address was a placeholder for rooms that were asleep -- and four of the five were wrong the
moment their room woke. Archipelago's connect handshake carries a slot name and a password and no
room identifier, so a client that reached whichever room actually held that port, with a slot name
that seed happened to contain, would have joined **the wrong multiworld and been told nothing**.
Rooms that already exist keep working; nobody loses a seed mid-run.

**Bug reports have a form.** It asks for the release tag you took both halves from, your whole
yaml, the client log from the last `SESSION START`, and what else was loaded -- the four things
every report has had to be asked for one at a time.
