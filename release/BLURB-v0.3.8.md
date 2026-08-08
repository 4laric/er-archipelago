# v0.3.8 — release blurb

**This is the release where the wizard stops guessing and starts telling you things.**

## Before you generate: how big is this seed, and what is in it?

The options wizard has a **Seed size** tab. It computes, from the region tables and your actual
options, how many checks your seed will have, how many regions it will keep, and how many of those
checks can hold progression — exact, not an estimate, with the spread shown rather than a median
pretending to be a promise. Under it, measured over sampled builds: how much of your pool is filler,
how much is real gear, and how little of it is progression.

The controls that move those numbers sit directly underneath them, so you can watch a seed get
bigger or smaller as you change your mind.

## In a multiworld: what are you putting into everyone else's game?

Two players asked the same question on the same morning from opposite ends of it. One wanted the
number — *"if I'm playing with 5 other people who have 200 checks each, 2/3 of the checks sent to
others are from me; how many of those are filler?"* The other wanted the control — *"crafting
materials should be local, upgrade materials other than bell bearing, ghost gloveworts, every
consumable, small rune amounts should not be sent out."*

Neither was possible. Locality was all-or-nothing (`local_item_only`) or a coin toss
(`filler_foreign_pct`, which keeps a random selection of filler names and so means something
different in every seed). Now:

* **`keep_local`** takes a list of item categories — `consumables`, `crafting`,
  `upgrade_materials`, `runes`, `crystal_tears`, `spells`, `spirit_ashes`, `weapons`, `armor`,
  `talismans` and the rest. `keep_local: [consumables, crafting, upgrade_materials, runes]` keeps
  your crafting mats, smithing stones, ghost gloveworts, every consumable and every Golden Rune at
  home while your gear still travels. Bell bearings are key items, not upgrade materials, so they
  still go out.
* **`keep_local_rune_cap`** holds rune items worth N runes or fewer and lets the big ones travel.
  "Small" is a number the game itself publishes, so it isn't guessed.
* **The count.** Every seed's generation log and spoiler now say, per slot, how many of your items
  actually went into other worlds, split filler / useful / progression, how many came back, and how
  many your options held at home. The wizard shows the ceiling live as you move the knobs.

Underneath is a new taxonomy of the item pool derived from the game's own data — the item id called
933 different things "goods", so until now there was no way to separate a crafting material from a
smithing stone from a throwing pot.

## Beta and stable

The wizard is a web page and the apworld is a download, and they had drifted apart: the live page
offered options the newest release did not have. That is worse than it sounds, because Archipelago
does not refuse a yaml carrying an option your apworld has never heard of — it prints one line
among fifty and generates the seed **without** it.

So there are two channels now. **`/er/` is the wizard for the released build**; **`/er/beta/`
tracks what is being built right now** and says so in a banner. Every yaml the wizard writes records
which apworld version it was written for, and that line reaches the generation log and the seed
itself, so a host can always see which wizard made a file.

Hosts also finally get what the docs have promised since v0.2: a **bare `eldenring.apworld`**, 1.3 MB
instead of the 124 MB player bundle, for someone who is generating a multiworld and not playing
Elden Ring. The release process now proves it can actually roll a seed before publishing it.

## Also

The wizard can hand your seed straight to a host and give you back a connect address. Its Checks
panel no longer describes a randomizer this project stopped being. And every yaml it produced for
months named `EldenRing` — a game Archipelago does not have — which is fixed, and gated so it cannot
come back.

`CONTRACT_HASH` is unchanged at `d7d3a58e`: the version moves in lockstep with the client, but the
wire between them did not, so a v0.3.7 client still handshakes.
