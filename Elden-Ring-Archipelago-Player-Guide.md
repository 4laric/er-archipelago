# Elden Ring in Archipelago

*A randomizer that drops the Lands Between into a shared multiworld — your weapons, spells, flasks, and key items get scattered across everyone's games at once.*

---

## What is this?

[Archipelago](https://archipelago.gg) is a multiworld randomizer: a bunch of different games — Elden Ring, A Link to the Past, Hollow Knight, Factorio, whatever — get shuffled together into one shared seed. The item *you* need to progress might be sitting in someone's Hollow Knight game, and the chest in front of *you* might hold their progression item. Everyone plays their own game; the items fly between worlds.

This project makes **Elden Ring a first-class Archipelago game.** Every meaningful pickup in the Lands Between — chests, corpses, boss drops, merchant stock, the lot — becomes a *check*. Opening it sends an item out to the multiworld. In return, your weapons, spells, talismans, upgrade materials, flasks, and progression keys arrive from other players (or from your own checks elsewhere on the map).

It runs through a **custom runtime client** that talks to the live game, so received items actually appear in your inventory mid-session, and your pickups register as checks in real time. That full loop — pick something up, it counts as a check, items get granted back into the game — is **confirmed working end-to-end.**

---

## Why play it

Elden Ring is *enormous*, and that's exactly what makes it a great Archipelago game. The map is the puzzle. A few of the headline ways to play:

### Pick your scope — from a 2-hour sprint to the full Lands Between

You don't have to commit to a 60-hour seed. Choose a **goal** that fits your evening:

- **Godrick mini-campaign** — a short run that keeps Limgrave, the Weeping Peninsula, and Stormveil Castle open and seals everything else. Goal: defeat Godrick the Grafted. A tight, self-contained loop that's perfect for a first seed or a quick multiworld with friends.
- **Messmer DLC mini-campaign** — a compact Shadow of the Erdtree goal centered on reaching and beating Messmer.
- **Full-game goals** — final boss, the Elden Beast, all Great Runes into the capital, all remembrances, or all bosses, when you want the marathon.

### DLC-only mode

Restrict the entire randomized pool to **Shadow of the Erdtree.** The base game stays installed for transit, but the checks and items all live in the Land of Shadow — Scadutree Fragments, Revered Spirit Ashes, the DLC's weapons and bosses. A focused way to play the expansion as its own multiworld.

### Region locks — the open world becomes a progression graph

Normally Elden Ring lets you wander almost anywhere from the start. Turn on **region locks** and the world opens up *piece by piece* as you receive region keys — so the famously freeform map becomes a real item-gated progression puzzle. Where it makes sense, it reuses the game's own keys (Academy Glintstone Key → Raya Lucaria, Dectus Medallion → Altus, Rold Medallion → Mountaintops, Haligtree Medallion → the Haligtree), so the gating feels native rather than bolted on.

### Boss sweeps & dungeon sweeps

Don't want to comb every catacomb for the last three checks? **Dungeon sweep** auto-collects the remaining checks in a dungeon the moment you kill its boss, and **boss attribution** ties checks to the boss that guards them. Clear the fight, claim the loot — no backtracking pixel-hunt.

---

## Quality of life

A randomizer lives or dies on how it *feels* to play. A lot of work has gone into making this one feel smooth:

- **Native-style notifications.** Item sends and receives show up in Elden Ring's own bottom-center event banner / ticker — no intrusive modal popups interrupting a boss fight.
- **Auto-upgrade.** Optionally, every weapon you receive is automatically brought up to your highest upgrade level, so a late-game gift isn't dead weight.
- **Auto-equip.** Optionally auto-equip received armor and weapons.
- **Progressive consumables.** Golden Seeds, Sacred Tears, Scadutree Fragments and Revered Spirit Ashes can collapse into clean progressive upgrades instead of a pile of identical pickups — and extra copies past the cap convert into Lord's Runes so nothing's wasted.
- **Progressive bell bearings.** Smithing-stone and glovewort bell bearings can fold into ordered progressive ladders, so your shops scale up sensibly as you play.
- **In-game check indicators** (in progress) — glow and audio cues so you can spot a check without memorizing the whole map.
- **PopTracker pack** with auto-tracking, including a DLC-only map variant, so you always know what's reachable.

---

## Tune it to taste

There's a deep options menu. A few of the dials you can turn:

- **Footprint** — `all`, `trimmed`, or `lean` pools, to control how big a slice of the multiworld your Elden Ring world takes up. Great for keeping a seed brisk in a big async.
- **Start strong or start scrappy** — grant Level Up from the start (skip the wait for Melina), start with the Spirit Calling Bell and Physick, randomize your starting equipment, or remove all weapon stat requirements so anything you receive is usable.
- **Pool curation** — automatically drop the worst low-tier gear and seed in the good stuff, or *compose* a pool from a whole-game "best of" ladder (S-tier weapons, top spirit ashes, remembrances, crystal tears).
- **Enemy & material randomization** — shuffle enemies and the respawning material nodes.
- **DeathLink** — share your deaths with the rest of the multiworld, because of course.
- **Comedy junk** — yes, you can deliberately season a seed with a controlled amount of glorious garbage checks.

---

## Honest status

This is an **actively-developed project**, but a big chunk of it is already verified working in-game — here's the straight version:

- **Confirmed working in-game:** the full multiworld loop (pickup → check → item grant), the custom client and native-style notifications, **region locks** (the world really does open up region by region as you receive keys — warp-enforced, not honor-system), **DLC-only mode**, **auto-upgrade**, **quick-start**, the **pool builder** and gear curation, **progressive bell bearings**, and the footprint/curation options (`trimmed` pool, filler-to-runes, comedy junk).
- **Playtest in progress:** the **Godrick** and **Messmer** mini-campaign goals — being played end-to-end right now.
- **Still in testing / landing soon:** progressive consumables (flasks/seeds/tears/scadu), the leanest pool size, and the Liurnia Caves bundle lock.
- **Known rough edges:** a summoning-bell issue is being chased, and a couple of cosmetic touches (a custom AP item icon, per-item descriptions) aren't in yet.

In other words: the foundation is solid and genuinely playable today, with a broad, fast-growing feature set. If you hit a rough edge, that's expected — feedback is genuinely useful right now.

---

## Want in?

If any of this sounds like your kind of chaos, come say hi in the Discord — I can point you at a current build and a starter config, and help you get a first seed rolling. Whether you want a two-hour Godrick sprint or a full DLC-only odyssey shared across a multiworld of other games, there's a way to play it.

*Built on the Elden Ring Archipelago apworld and a custom runtime client. Elden Ring and Shadow of the Erdtree are property of FromSoftware / Bandai Namco; this is a fan-made randomizer and isn't affiliated with or endorsed by them.*
