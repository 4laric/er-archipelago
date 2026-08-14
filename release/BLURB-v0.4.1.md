# v0.4.1 — release blurb

Elden Ring's item pool got a lot more honest this window, multiplayer got a lot more generous, and
the site stopped lying about where your rooms are.

## Your neighbours' key items will actually reach you now

If you play multiworld, this is the change you will feel. `confine_foreign_progression` keeps
another player's progression on your interesting checks — bosses, remembrances, key items — rather
than on a random Smithing Stone pickup, and it is on by default. Nobody had measured what that
costs: the surface it confines to is about **30 checks out of 1500**, so a slot was receiving
**7 of the 60** foreign key items it would otherwise have got. The other 53 did not land somewhere
worse. They never arrived, and your checks were filled with your own items instead.

So the surface grew. `SweepSlot` is a new progression-surface class, **on by default**, that
nominates one member of every dungeon sweep your seed runs. Measured from the shipped template, one
Elden Ring slot beside a partner game:

| beside | key items received, before → after |
|---|---|
| DOOM 1993 | 7 → **18** |
| Hollow Knight | 15 → **44** |
| Bumper Stickers | 10 → **28** |

Nothing about the promise changed — foreign progression still lands only on the surface, never on
your filler.

**The cost, stated plainly:** a dungeon sweep can now hand you progression. Kill the boss, and one of
the checks that pays out may hold a key. If you would rather it never did, drop `SweepSlot` from
`progression_surface` in your yaml.

## Choose where the run starts

`start_region_pool: [Caelid]` and you open in Caelid. Name several and the opening region is drawn
from just those; `start_regions: 2` with two names opens both. Every region you name is kept, so
this can make a seed larger than `num_regions` asked for — that number has always been a draw size.
Naming a region the seed cannot open in fails generation and tells you which and why.

For anyone testing a build, `num_regions: 1` plus one name is "just play Caelid", the same seed
every time.

## Hundreds of items that were missing, and why

boblerrr spent a playtest counting vanilla items he could not find and posted the list. Almost none
of it was one bug — it was four, and they were all real:

- **+286 checks.** A "co-check" is the sibling item a single pickup grants. Five families were
  allowlisted by hand; the policy that finds them now selects them all. That is +5.7% locations, and
  it recovers twelve of the reported items on its own — Maternal Staff, Stargazer Heirloom, Crystal
  Burst, Scouring Black Flame among them.
- **+294 copies.** 926 locations grant more than one copy of their item and we paid one of each.
  The first slice mints 41 stacked names — 39 of them smithing and somber stones — so a lot that
  gives you three stones gives you three.
- **Four Scadutree Fragment checks** were paying half what the game gives you.
- **Five checks were paying Rune filler** because their item name resolved to nothing. They kept
  their location, silently paid a Rune, and dropped their item out of the catalog. Two of them are
  in bobler's list. The correct names were already in the repo, in a second table nothing had ever
  cross-checked against the first.

And **+135 items that no seed could ever have handed you**: an item whose only source is a random
enemy drop has no event to hang a check on, so it never entered the catalog at all. Celebrant's
Cleaver, Rib-Rake and Sickle are the reported case. 96 of the 135 are what the game itself marks as
trivia, so they get their own filler category — **`junk_gear`** — rather than being smuggled into
gear injection where they do not belong. Weight it if you want the low end of the armoury; it is off
unless you ask.

## Turn the curated pool off entirely

`vanilla_pool: true` and your checks pay what they pay in vanilla Elden Ring. No recipe rewriting
the junk end of your pool, no guaranteed set of physick tears and bell bearings added on top.

Half of this was already possible and that was the problem: emptying `curated_filler` gave you a
vanilla filler tail, but the tears and bell bearings came from a second feature no yaml could reach,
so a seed built that way still handed you up to 18 tears vanilla never placed. It looked like it had
worked. The report behind it was somebody counting 19 tears against a catalog of 37 and concluding
items were missing — 19 being the 18 guaranteed ones plus the one his seed kept.

It is a real trade: no gear injection, no smithing-stone or rune economy, no promise a physick tear
exists at all in a seed that seals its home region. If you only wanted *less* gear, turn `juice`
down instead.

## Options that were decisions again

- **`no_weapon_requirements` is a setting.** Weapon, shield, catalyst and spell requirements have
  been zeroed in every seed anyone has ever rolled — it was frozen on, so "any gear the multiworld
  hands you is usable" had stopped being a choice and become the game. It is a yaml option again.
- **`no_fall_damage` is off the yaml surface**, and **Spawn Traps is a text field** in the builder
  rather than a list you scroll.

## Room hosting is back, as one tab

v0.4.0's notes said hosting was retired. It is not — it returns as a single tab on peliarch.ca, with
the defect that killed it fixed.

That defect is worth stating, because it was live the whole time the retirement sat merged and
undeployed: the rooms dashboard offered five different rooms **the same connect address**, with a
Copy button beside it. Ports are handed out one per room, so that address was a placeholder for
sleeping rooms — and four of the five were wrong the moment their room woke. Archipelago's connect
handshake carries a slot name and a password and no room identifier, so a client that reached
whichever room actually held that port, with a slot name that seed happened to contain, would have
joined **the wrong multiworld and been told nothing**. Rooms that already exist keep working.

## Also

The front page can actually be deployed now — v0.4.0 shipped the deploy step pointing at a path the
site does not serve, so the file would have been written, reported as installed, and never appeared.
Bug reports have a form that asks for the four things every report has had to be asked for one at a
time: the release tag you took both halves from, your whole yaml, the client log from the last
`SESSION START`, and what else was loaded.

---

_Seeds from earlier versions are unaffected by anything here except the two defaults that changed on
purpose and are called out above: `SweepSlot` on the progression surface, and
`no_weapon_requirements` becoming a setting rather than a fixed behaviour._
