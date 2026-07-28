# v0.2.14 — release blurb (draft)

> Drafted 2026-07-28, off the Fortissax softlock report. Two player-visible things happened here: a
> seed-killing bug got fixed, and **the item pool changed shape** — key items that were being deleted
> from every seed now survive. The second one is the bigger deal for how a run feels, and it is the
> one nobody has playtested.
>
> ⚠️ **NOT SHIPPABLE UNTIL THE REGEN IS IN.** `key_item_goods` dropped the crafting cookbooks after
> the first regen, so `item_ids.py` on main is stale and CI's regen-drift gate says so. Run
> `build.ps1 -Greenfield`, commit, and check the line reads `key_item_goods: 108 key items … 96
> dropped by name ('Cookbook',)`. Every number below assumes that regen.

---

## ⚠️ If a region lock landed behind Fortissax, your seed was unwinnable

Lichdragon Fortissax is fought inside Fia's Deathbed Dream, and that dream does not exist until you
hand her the **Cursemark of Death**. The randomizer did not know that. It treated his Remembrance as
an ordinary boss reward — and because it is tagged as a major boss, it was one of the *preferred*
places to put a region lock.

Then the second half: **the Cursemark was being deleted from the item pool.** Not misplaced —
removed. So the fight could not be opened by any route, and anything the seed hid behind it was gone.

Thanks to **Nova71288** for the report, which arrived with the spoiler log already read: three
players' worth of logs, no Cursemark of Death in any of them. That is exactly the detail that turned
a "bad luck" story into a two-line fix.

Fixed on both halves in v0.2.14. Fortissax's reward can no longer hold anything a seed requires, and
the Cursemark stays in the pool.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.14 — key items stop disappearing**

- **Fixed a softlock:** a region lock could land behind Lichdragon Fortissax, whose fight only exists
  after an NPC questline. It can no longer hold required progression.
- **Key items were being deleted from seeds.** Bell bearings, whetblades, maps, the Dectus and
  Haligtree medallion halves, the Cursemark of Death — the pool builder classed every Goods item as
  junk and overwrote them. **270 check slots** now keep their real item.
- **35 more checks can no longer be required**, all of them NPC handovers: the Rold Medallion from
  Melina, the Drawing-Room Key from Tanith, the Haligtree Secret Medallion (Right), and friends. They
  are still randomised and still yours — they just cannot hold anything the seed needs.
- **Slightly more smithing stones early**, to pay for the above.

Update both halves; the apworld and the client `.dll` ship as a matched pair.

---

## Long version (release notes)

### The Fortissax softlock

Two independent faults lined up, and either one alone still strands you.

**The check was not marked.** Everything else in Fia's questline already refused to hold required
items — her hood, the Inseparable Sword, the Mending Rune, the Cursemark pickup itself. The boss
reward at the end of that chain was the one thing that did not, because every screen we have for
finding quest-gated checks looks at how an *item* is awarded, and what a questline gates here is
whether the *fight exists at all*. Nothing that inspects award sites can see that.

It matters more for Fortissax than for other quest-adjacent bosses because unlocking a region lights
that region's graces — so you warp past Ranni's chain into the Lake of Rot, past the medallion lifts,
past the Pureblood Medal. A warp cannot get you into a fight that has not been created yet, and his
arena is a dream you enter through Fia.

**And the key item was being deleted.** See below — that is a much wider bug than one questline.

### Key items were being classed as junk

The pool builder decides which vanilla items it may overwrite with curated filler. It was deciding
that by asking whether an item was a *Goods* item — and in Elden Ring, every key item is a Goods
item. So it could overwrite them, and with the default recipe it essentially always did.

Items this was quietly removing from your seeds: **bell bearings, whetblades, the crafting kit,
maps, prayerbooks and scrolls, the Dectus Medallion halves, the Haligtree Secret Medallion halves,
the Rold Medallion, Pureblood Knight's Medal, the Cursemark of Death**, and more.

They are now read from the game's own key-item flag instead of guessed from an ID range — **108 item
names, covering 270 checks**, that keep their real item.

Two notes on scope. **Crafting cookbooks are deliberately excluded** — they are key items by the
game's reckoning, all 96 of them, and holding 96 vanilla cookbooks instead of curated filler is a
change to what your seed feels like that nobody asked for. And the Pureblood Knight's Medal is *not*
flagged as a key item by the game at all — it is filed as a single-use travel consumable — so it is
protected because our own model calls it a travel key.

### 35 more checks cannot be required

Everything an NPC hands you in dialogue only exists while that NPC is alive and at that point in
their story. The logic sees the region open and calls the check available.

Those are now derived from the game's own dialogue scripts rather than found one at a time: 48 such
checks, 14 of which earlier hand audits had already caught — that overlap is the reason to trust the
screen about the other 34. The named ones you are most likely to notice: **Rold Medallion**
(Melina, after Morgott), **Drawing-Room Key** (Tanith), **Haligtree Secret Medallion (Right)**.

As always: randomised, obtainable, yours — they simply cannot hold something the seed requires.

### More stones early

Every check that stops being allowed to hold progression pushes the progression that remains into
earlier slots, and protecting key items made the filler pool smaller. Both squeeze the early upgrade
economy, which is measured against a stated bar: a player who has cleared a realistic fraction of
what is open to them should be able to afford a **+3 weapon**. At the old setting three of nine test
seeds fell under it. The smithing-stone share of the filler pool goes up to compensate, paid for out
of the rare-gear injection.

### Under the hood

The progression surface now counts only checks that can actually *hold* progression. It had been
counting checks the fill rules already refused — harmless until Fortissax was marked, at which point
Deeproot Depths claimed a place to put a lock while having none, since that reward was its only
surface member.

---

## Before you post

1. **The pool texture changed and has not been played.** 270 slots that used to pay curated filler
   now pay their vanilla key item. That is the intended fix, but it means a run has meaningfully more
   bell bearings and medallions and fewer stones/greases/gear injections than v0.2.13 did — on top of
   the stone-share bump pulling the other way. One short seed at defaults before shipping.

2. ⚠️ **Do not tell players "Fia's questline is completable now."** Protecting the Cursemark keeps it
   in the pool *when its check is in the seed* — and under `num_regions` the region that pays it may
   not be in your seed at all. The protection improves the odds; it is not a guarantee, which is
   exactly why the reward behind that fight stays unrequirable rather than becoming a logic rule.

3. ⚠️ **One known member is not a closed class.** Fortissax is the only boss we know of whose arena
   is created by a questline. Nothing has swept for others — the tool that would do it is described
   in the code and not written. Absence from the list is not evidence of safety, and the blurb should
   not imply the class is solved.

4. **Client `.dll` and apworld are a matched pair again.** The tracker's location table was
   regenerated for the 35 newly-unrequirable checks; refresh both.

5. **Nothing else from this window belongs in a player blurb.** The check-browser rebuild, the
   surface accounting, the derivation notes — developer-facing. Left out on purpose.
