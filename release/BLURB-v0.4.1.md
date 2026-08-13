# v0.4.1 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

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
