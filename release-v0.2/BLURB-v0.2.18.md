# v0.2.18 — release blurb (draft)

> Drafted 2026-07-30. The shop half of the game gets honest: the shelves the randomiser was
> rerolling were menus no player can open, and money runes were priced by a name whitelist that
> missed every DLC rune. Both are fixed at the datum, not at the symptom. Plus a scaling default
> that stops short seeds throwing endgame enemies at mid-game gear, and three crash guards.
>
> ⚠️ **Client update required.** ⚠️ **`maximum_enemy_difficulty` behaves differently by default** —
> see Compatibility.
>
> 🔴 **DRAFT NOTE, DELETE BEFORE PUBLISHING:** the section *"Runes you can actually buy"* assumes the
> shop-rune visibility fix lands. It is still being traced at time of writing (client `e33a1b8`,
> `5e09828`). If it does not land, delete that section — the pricing fix below it stands on its own.

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
  actually is. This is also why runes never seemed to show up for sale below their worth: they were
  being priced into rows nobody could reach.
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

### Runes you can actually buy

<!-- 🔴 DRAFT: assumes the visibility fix lands. Delete this whole section if it does not. -->
Rune rows were being written correctly and then not appearing on the shelf. The rows held what we
wrote — that was proven by reading them back — so the fault was downstream of the write, in what the
purchase menu was willing to show. That is fixed, so a rune priced below its worth is now a rune you
can walk up to and buy.

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
