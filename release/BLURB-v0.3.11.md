# v0.3.11 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

**The options wizard grew tabs.** All 54 settings used to sit in one collapsed section called
"Other Options", in the wizard's last step, under a line telling you everything there was safe to
skip. Enemy scaling was in there. So was the pool builder, and the progression surface, and every
shop setting. They are now seven steps you walk through -- Goal & Regions, DLC & Blessings,
Difficulty & Scaling, Checks & Item Pool, Multiworld & Placement, Shops & Merchants, Quality of Life
-- with the ones you have touched lit up in the rail. Your yaml comes out exactly as it did before;
this is only about being able to find the thing you were looking for. The same grouping now shows up
on Archipelago's own player-options page too, because both read it from the same place.

**Keep your gear out of the shops.** A new setting, off unless you ask for it:

    keep_out_of_shops: [weapons, armor]

and no merchant of yours will stock a weapon or a piece of armour again. They are still shuffled and
still yours to find -- they are just out in the world, where finding one is a matter of going
somewhere rather than of having enough runes. boblerrr asked for it looking at a shelf of weapons,
gauntlets and helms priced up to 25,000 with 11,144 runes in his pocket, and he had a point: a fifth
of every purchase-menu check in the game pays gear, and on a short seed the merchant more or less IS
the world.

It takes any category, not just gear -- `[consumables, crafting]`, `[spells]`, the same list Keep
Local uses -- and it covers the unlimited shelves as well as the checks.

On a very short seed there may simply be nowhere else to put it all, and rather than quietly doing
nothing the option takes what fits, skips what does not, and writes down which was which. Ask for
weapons and armour on a one-region seed and you will get weapons kept out and a line in the log
explaining that armour would not fit and by how much.

**Progressive Stone Bells actually paces you now.** The setting collapses the Miner's Bell
Bearings into two progressive items, so the Twin Maidens' smithing shop opens a tier at a time instead
of all at once when you happen to find the right bearing. Except that the ordinary bell bearings were
still in the pool alongside it -- and one of them is the top of the somber shop. boblerrr picked up
`Somberstone Miner's Bell Bearing [5]` in Enir-Ilim and the ladder was simply over. Turn the option on
now and there are no loose bell bearings to find; turn it off and everything is exactly where it was.

**The options template downloads and loads again.** If you pulled the default Elden Ring yaml
from Archipelago and it came back at you with `Duplicate key False found in YAML`, that was ours and
it is fixed. One setting listed both `off` and `false` among the words it accepts, and to a yaml file
those are the same word -- so the template Archipelago generated for this game held the same key
twice and Archipelago would not read its own file back. Writing `on` or `off` in your yaml still
works exactly as before; nothing you have already written needs touching.

## What is queued for it

A fix for something two players noticed independently -- items whose region label sends you to the
wrong part of the map. If an item said "Cerulean Coast" and you found it in Charo's Hidden Grave,
that was real, and on a seed that kept one of those regions and not the other it was worse than
cosmetic: the check either sat somewhere the game would not let you walk, or never existed at all.

That work is open as a pull request, not merged, so it is not promised here yet.

## For the technically minded

Nothing in the contract moved. A v0.3.10 client and a v0.3.11 seed still speak to each other, and
the reverse holds too -- the version bump exists so that a bug report can name exactly one build.
