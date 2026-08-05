# v0.2.18 — release blurb (draft)

> Drafted 2026-07-30. The shop half of the game gets honest: the shelves the randomiser was
> rerolling were menus no player can open, and money runes were priced by a name whitelist that
> missed every DLC rune. Both are fixed at the datum, not at the symptom. Plus a scaling default
> that stops short seeds throwing endgame enemies at mid-game gear, and three crash guards.
>
> ⚠️ **Client update required.** ⚠️ **`maximum_enemy_difficulty` behaves differently by default** —
> see Compatibility.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.18 — the shops were lying, and short seeds were too hard**

- **Money runes are priced correctly at last.** Rune pricing keyed off a list of *names*, which
  matched all 21 base-game runes and **none of the 11 DLC ones** — so every Shadow Realm Rune,
  Marika's, Leda's and Broken Rune kept selling at ten times its payout, through two previous
  "fixed" releases and three player reports. Price now comes from the game's own payout value, so
  the next DLC needs no edit.
- **The infinite shop shelves were pointed at the wrong rows for their entire life** — 455 of them,
  and they were the Alter-Garments menu, the Ash-of-War duplication menu and debug rows. Not shelves.
  No player could browse them. The randomiser now finds the **14 real shelves** by what a shelf
  actually is. This was one of two reasons runes never seemed to show up for sale below their worth
  — some were priced into rows nobody could reach; the rest hid themselves, see below.
- **Shop rows that were invisible now render.** A shop row whose price sat below the item's own
  sell value was silently dropped from the purchase menu — so a rune priced at a bargain became a
  rune you could not see, and the same thing could hide *any* discounted ware. Fixed by lowering the
  item's sell value rather than raising the price, so the bargain survives.
- **New: `no_runes_in_shops`** — keeps your own money runes out of merchant stock entirely, if you
  would rather not shop for them. Off by default.
- **Whetblades no longer collect their own location.** Receiving one from the multiworld was quietly
  marking its vanilla location as found and making that treasure disappear — so the item placed there
  went out to whoever owned it without anyone visiting, and the chest was gone. The location is now
  yours to actually go and open, and every affinity still unlocks on receipt.
- **`maximum_enemy_difficulty` now defaults to `auto`**, which lowers the top of the difficulty curve
  to match the LENGTH of your run. A 5-region seed tops out around 4.1x enemy HP instead of 7.4x.
  Long seeds are unchanged. Set a number to override.
- **New: `infinite_hub_wares`** — name up to four items the hub merchant always stocks, unlimited.
- **Gems, weapons and armour can be sold** at shops that should buy them.
- **Three crash guards**, two of them generalising fixes that previously covered only one caller.
- ⚠️ **Client update required.**

---

## Long version (release notes)

### The shelves were menus

`reroll_infinite_shop_stock` decides what the unlimited-stock shop rows contain. It had been aimed
at the wrong rows since it was written, and the reason is worth stating because it is the shape of
most bugs in this project: the row filter asked for `eventFlag_forStock == 0`, which is the exact
**inverse** of what marks a shop check. Read quickly, that looks like "rows that can never be
checks" — safe. What it actually collected was 455 rows belonging to the Alter-Garments menu, the
Ash-of-War duplication menu, and debug entries.

Those are menus, not shelves. Nobody can browse them. So rerolling them changed nothing a player
could buy, and corrupted the menus it did touch.

The filter now derives a browsable shelf from what one *is* — a real equip id, no material cost, no
release flag, unlimited quantity, and a stock flag **greater than** zero. **Fourteen rows qualify:**
Kalé's glass shards, Iji's somber smithing stones, the throwing-knife and poison-dart racks, and
their neighbours. Those are the shelves that reroll now.

### Money runes: a rune is not a name

A player reported three times that no rune in any shop was ever priced below its value. Twice this
was declared fixed. It was not.

Rune-ness was decided by an anchored name pattern — `Golden`, `Hero's`, `Lord's`, `Numen's`. That
matched all 21 base-game money runes and **missed all eleven DLC ones**: Shadow Realm Rune [1] to
[7], Rune of an Unsung Hero, Marika's Rune, Leda's Rune, Broken Rune. And a miss was not a skip: an
unmatched rune fell through to the generic price path, which for a rune is its sell value times ten
— *exactly* the bug the code existed to remove. So the whitelist was re-introducing the 10x error on
every DLC rune, in the same commit that claimed to fix it.

Pricing now reads the payout the game itself stores for each rune. No list of names, no anchor, no
DLC blind spot — and the retired pattern survives as a cross-check in the tests: everything it used
to match must still be priced. A future DLC needs no edit here.

### The bargain that hid itself

A rune priced below its worth would not appear in the merchant's menu at all. Rune rows were being
written correctly — proven by reading them back out of the game — so the fault lay downstream of the
write, in what the purchase menu was willing to display.

**It was the discount itself.** Elden Ring drops a shop row from the list when the row's price is
below the item's own sell value. Money runes hit that by construction: a rune's sell value equals its
payout exactly, and the randomiser rolls the price anywhere from zero up to that payout — so
*every* rune priced as a bargain, which is the whole point of the feature, made itself invisible.
This was never rune-specific either; the same rule could hide any ware discounted below its sell
value, which is what had happened to a stray Veteran's Helm.

The obvious repair — raise the price until the row renders — would have traded the feature away: a
rune could then never be a bargain again. So the fix goes the other way and **lowers the item's sell
value** instead. On a rune that is redundant data: the payout is read from somewhere else entirely,
verified across all 35 rune rows, so nothing that matters changes. The row renders, and the discount
survives.

Selling a ware back is capped at just under what you paid for it for the rest of the session, so
there is no money pump. Other merchants selling the same item keep their own prices. And the Veteran's
Helm keeps its 600-rune price instead of being inflated to 1001 to make it visible.

### Keeping runes out of shops entirely

If you would simply rather not buy runes from merchants, `no_runes_in_shops` keeps your own money
runes off every shop check and out of the rerolled shelves. Off by default, so nothing changes unless
you ask for it.

It began life as an escape hatch while the bug above was resisting diagnosis. That is fixed, so this
is now a preference rather than a workaround — but it costs nothing to keep, and some people would
rather spend their merchant slots on anything else.

### The whetblade that opened its own chest

Receiving any of the five whetblades from the multiworld silently collected the location where that
whetblade sits in the world. The item the seed had placed there was sent out as though you had found
it, and the treasure itself stopped spawning — so a location you had never visited was simply gone,
with nothing announcing it.

**Why, and it is a nice piece of Elden Ring trivia.** Each whetblade unlocks several Ash-of-War
affinities, and the game tracks them one flag apiece — Iron carries Heavy, Keen and Quality; Black
carries Poison, Blood and Occult. The catch is that the *first* affinity's flag is the same flag the
game uses to record "this whetblade has been picked up". One flag, two jobs. The randomiser reads
that flag to know a location was found, and the client was setting it to unlock the affinity — so
unlocking Heavy and collecting the Stormveil chest were, to the game, the same act.

Skipping the flag would have cost an affinity instead, which is a worse trade and just as invisible.
So the two jobs are now separated: the affinity keeps the flag it has always used, and the
randomiser watches a different one for the pickup. Both work, and neither can trigger the other.

Nothing about your seed changes and no item moves. If you already received a whetblade on an earlier
build, its location was collected then and stays collected — the server has that recorded and it
cannot be undone from here.

### Short seeds were being scaled like long ones

Enemy scaling targets a region's **position in your unlock order**, normalised so the deepest region
you kept tops out. That is right for a long seed and wrong for a short one: with five regions, the
deepest is reached quickly but still counts as "the end of the run", so it is scaled as the end of a
run — while your weapon is still on a fixed upgrade ladder that a short seed does not accelerate. The
result was endgame-strength enemies on mid-game gear.

`maximum_enemy_difficulty` gains an `auto` setting, and **`auto` is the new default.** It lowers the
top of the curve with the length of the run:

| regions | ceiling |
|---|---|
| 5 | ~4.1x enemy HP |
| 8 | ~5.5x |
| 12 | ~6.7x |
| 30 (all) | ~7.4x — unchanged |

The curve keeps its shape; only its top moves. A full-length seed is scaled exactly as before.

**On the calibration, honestly:** the 5-region figure is anchored to one playtest of an earlier,
shorter ladder that topped out at 3.7x, described then as "felt pretty close, if it was a bit harder
we get there" — so five regions lands one rung above that. Everything above that point is
extrapolation across rungs nobody has fought yet. Set a number instead of `auto` if you disagree
with it; that is what the number is for.

### New: choose what the hub always sells

`infinite_hub_wares` takes item names and stocks them, unlimited, at the hub merchant:

    infinite_hub_wares: ["Rune Arc", "Larval Tear"]

Up to **four** — that is how many browsable unlimited shelves the hub has, and asking for a fifth is
rejected at generation with a message rather than silently dropped. Each ware sells at its own
derived price, so a shelf is never a free dispenser.

Empty by default; a yaml that does not mention it generates exactly as before. Worth a thought
before filling it, though: unlimited Larval Tears is unlimited respec, and unlimited Rune Arcs is a
permanent great-rune buff. Both genuinely change how a run plays.

### Things you can now sell

Gems sell natively at shops that take them (135 vanilla rows support it). Weapons and armour sell
too — the floor that decided what was sellable had been goods-only, so everything else read as
worthless.

### Stability

Three guards, and the honest framing is that two of them are **generalisations of fixes that already
existed but only covered one caller each**. That pattern — patch the instance, leave the mechanism —
is what put the same crash in front of players more than once.

- **The inventory pointer is retired when a warp is requested**, not only when one completes. A warp
  tears the old map down first, and the game still reports "in world" while it does, so item
  delivery could run against memory the engine was already freeing.
- **Enemy scaling stops during the death-cam.** Three other features already skipped their work while
  the player is dying, each because touching those structures mid-teardown crashes. The scaling
  sweep touches the same structures on every enemy in the area and had no such check.
- **Event-flag writes are now bounded the way item grants are.** A flag the game silently discards
  was re-written every frame forever; it now stops after three attempts and says so in the log. A
  flag the game merely *contests* — sets back a moment later — is deliberately **not** bounded, so
  nothing legitimate stops being re-asserted.

Also: start-of-run pot vessels no longer ask for more than the game will accept — two of them
requested ten where nine is the limit, and the tenth silently vanished.

### Compatibility

⚠️ **Client update required.** Some of the above is client-side, and an older client will connect to
a v0.2.18 seed and simply not have it.

⚠️ **`maximum_enemy_difficulty` changes behaviour by default.** If you were relying on the previous
uncapped curve on a short seed, set `maximum_enemy_difficulty: 100` to get it back. Full-length seeds
are unaffected either way. A seed that caps below 100 tells the client at connect, and an older
client refuses with a message rather than ignoring the cap.

Existing seeds in progress are unaffected — nothing here moves an item or a check.
