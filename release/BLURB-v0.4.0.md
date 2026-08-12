# v0.4.0 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only
moment anyone remembers why it mattered._

## Why this one is 0.4 and not 0.3.13

Two things a default seed does differently, both of which landed under the v0.3.12 window:

**Your spells, spirit ashes and crystal tears are gear now, so your seeds will differ.** Elden Ring
files sorceries, incantations, spirit ashes and physick tears under the same internal category as
crafting materials and throwing pots, and this world took that at its word -- so 319 items you
equip, cast and drink were labelled junk everywhere it counts: in Archipelago's fill priority, in
your spoiler, and in the tracker of whoever receives one. They are `useful`. Useful items are placed
before filler, which means **the same yaml and the same seed number now produce a different layout**.
Nothing is unreachable -- 88 generations across 11 configurations, no failures -- but a seed you are
part-way through will not match a fresh generation of it.

**Rune shop prices are yours to choose again, and they start off.** Since late July, a shop check
whose reward was a rune had its price rolled to "somewhere between free and twice what the rune is
worth", for everyone, with no way to say no. It is `rune_shop_pricing` now, off unless you ask, in
the wizard under Shops & Merchants. 🛑 If you were enjoying the roll, you need that one line in your
yaml.

## 🛑 Everything below this line shipped in v0.3.12 and was never announced

v0.3.12's release body is three words -- "VA/RVA hotfix" -- and its actual contents are eleven
items. They are in the tag. They have never been put in front of a player. They are here.

**Take this one if you are on v0.3.11.** v0.3.11's notes described a lot of client work -- received
spells getting memorised, light roll finally doing something, a DeathLink telling you on screen that
somebody else's death just killed you, the bell hand-in showing up where you would look for it --
and the release did not contain any of it. The apworld was current; the bundled client was from the
previous day. Nothing was lost or reverted, and none of it needs a new seed.

**If you play through matt's randomizer, your shops were not empty of AP items -- they were full of
telescopes.** The AP flower is not an item. It is icon cell 92, the vanilla Telescope, repainted by
a texture shipped as a me3 *package*, and matt's "Add dll mod" launch path never reads our me3
profile. The client goes on marking every foreign shop slot with cell 92 regardless, so the marking
lands and the repaint does not. At least one player reasonably concluded his shops held no AP items.
They did, and the *names* were correct the whole time: an AP item reads `AP: <item>`. There is now a
section in `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` telling you which folder to copy `menu` into,
and the client says so itself -- in the log, with both paths, and once on screen -- instead of
leaving you to work out that a telescope means a missing file.

**Smithing bell bearings are gear; merchant bell bearings are convenience.** Elden Ring files all 48
bell bearings in one inventory tab with the gate keys, so this world called them all `key_items` and
classed them junk -- including the ones that hand you the entire smithing economy. A naturally-placed
Somberstone Miner's Bell Bearing [4] was filler. They are two categories now: **`upgrade_bells`**
(13, useful) and **`merchant_bells`** (35, filler). `key_items` still means the whole tab, so your
yaml does not change meaning.

**`cookbooks` is its own category.** `key_items` was 220 items and 96 of them are crafting cookbooks,
with no way to say "keep my cookbooks local but send the gate keys out". There is now.

**The wizard shows what you are sending out, live, while you set the options.** It sits in the
right-hand column next to your yaml, on every step, and it finally answers the knob most people
reach for: `filler_foreign_pct`. Turning it to 50 now reads "1,031 of your checks open to a foreign
item, 439 held at home" instead of standing still. It is a labelled estimate -- the option picks item
names, and names carry different numbers of copies -- which beats a figure that never moves.

**The wizard's Seed size step was blank.** Not slow, not wrong -- blank. You clicked to it and got
the settings and no numbers, and they appeared only once you changed something. Fixed, and there is
now a gate that renders every step and fails if one comes out empty.

**The Curated Filler recipe is usable.** It is the only setting whose value is a table, the wizard
had no control for a table, so it handed the recipe to a text box that displayed the words
`[object Object]` -- and typing in that box wrote a line of text where the world expects a table.
It is a weight per category now, with the share of the filler tail each weight buys shown beside it.
Seven of the sixteen categories were not on the page at all before this.

**Traps can be any enemy in the game.** There were three; there are now 390. `traps: [basilisk]`
drops **three basilisks where you are standing** -- one would be a joke, three is the Death Blight
mist, and it can kill you outright, so it sends a DeathLink. `spawn_traps` takes any spawnable enemy
by model id. All of it is off by default, all of it is filler, and no progression ever rides a trap.

**Traps no longer quietly eat your checks on an out-of-date client.** A spawn trap carries the enemy
it summons inside the item's name, and a client too old to read that name was throwing the item away
on arrival -- silently, with the check marked collected. One playtest seed had seven waiting. Seeds
that use traps now say so at connect. 🛑 Everyone on a trap seed needs a client from this release.

## Landed since the v0.3.12 tag

**The check browser will file a misregion report for you.** If a check is attributed to the wrong
region, the browser now turns that into a prefilled issue rather than asking you to describe it.

**A worksheet of every check whose tile holds more than one region**, which is the population the
region-attribution work has been arguing about without a list.

## Still open in this window

- #591 -- the Leyndell rune supply repair. Disarming the wall softlocks; the fix is to repair the
  supply instead.
