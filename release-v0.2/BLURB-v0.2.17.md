# v0.2.17 — release blurb (draft)

> Drafted 2026-07-29, rewritten 2026-07-30 around a save-destroying softlock reported overnight by
> **dalekin31** and **dafranky67**. That fix is now the reason to ship this build, so it leads.
> **This one needs the new client** — the fix is client-side. The slot-data contract itself did not
> move, so a v0.2.16 client still connects; it just will not have the fix.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.17 — the infinite-item softlock is fixed, and you can choose how much of a region an unlock opens**

- **Fixed: an item the game refused could be re-sent forever.** If Elden Ring would not accept an
  item — inventory at its cap — the client had no way to tell, so it kept re-sending, several times a
  second, for the rest of the session. You got an endless stream of dropped items and
  "exceeds the maximum storage", could not move, warp or open a menu, and restarting did not help.
  **Update the client to get this.**
- **Already stuck in one?** You do not need to wait for a build: start the client with the
  environment variable `RECONCILE_APPLY=none`. That falls back to the older delivery path, which has
  no re-send loop, and your save becomes playable again.
- **`region_grace_unlock`** decides how many Sites of Grace a region unlock lights.
  `all` (default) lights every warp point — Liurnia is 59 at once. `landmarks` lights one per
  sub-area, so Liurnia becomes Lake-Facing Cliffs / East Raya Lucaria Gate / Moonlight Altar /
  Ruin-Strewn Precipice. `entrance` lights only the way in.
  It cannot strand you: unlocks are still the only progression, every check stays where it was, and
  any grace you were not handed is still reachable on foot.
- **Fixed:** killing the tutorial Grafted Scion paid out 36 Stormveil Castle checks. All 36 were
  ordinary filler — legacy-dungeon sweep pools exclude key items, Great Runes, Remembrances and boss
  rewards by construction — so it was an early pile of junk, not a broken seed.
- **`dungeon_sweep`'s middle settings work now.** `minidungeons`, `all` and `bosses` were doing the
  same thing; they are a real ladder — 515 / 1971 / 3184 checks. Your seeds are unaffected: the
  default is renamed to `bosses`, which is what every non-`none` value already gave you.
- ⚠️ **Client update required** for the softlock fix. The seed format is unchanged, so an old client
  still connects to a new seed — it simply keeps the bug.

---

## Long version (release notes)

### The item that would not stop arriving

Two players hit this on the same night. An item — Mohg's Great Rune in both reports — began arriving
over and over, dropping on the ground because there was nowhere to put it, with the "exceeds the
maximum storage" box reappearing faster than it could be dismissed. The camera locked up, warping and
menus stopped responding, and reconnecting or restarting the game resumed the flood immediately. One
of them lost two saves to it.

**What was actually wrong.** Item delivery is built to be self-correcting: the client checks whether
you are holding what the server says you own, and re-sends anything missing. That is a good design —
it is why an item lost to a crash comes back on its own. But it rested on an assumption nobody had
tested: that a delivery the game *accepts* is a delivery that *arrives*.

It is not. When your inventory cannot take another copy, Elden Ring refuses the add and drops the
item at your feet — and the function we call to hand you an item reports nothing at all about whether
it worked. So the client saw "delivered", looked in your bag, did not find it, and concluded the
delivery had been lost. Which it re-sent. Which was refused again. Several times a second, forever,
while the log cheerfully reported success.

**What changed.** Delivery is now verified rather than assumed: the client reads your inventory back
immediately after handing you an item. If an item is accepted but still cannot be found three times
running, it stops re-sending, and writes one line to the log naming the item and everything the game
knows about why — how full each part of your inventory is, and whether the item ended up somewhere it
was not looking. It tries again on your next load, so a temporary problem still resolves itself.

**Nothing is lost when this triggers.** The server still knows the item is yours, and every reload is
a fresh attempt. The worst case is now a few refused-item popups per load, with a note in the log
that says which item and why — instead of a run you cannot play.

**Being straight about the scope of this fix.** This bounds the damage; it does not yet explain what
made your inventory refuse a Great Rune in the first place. That is still open, and it is why the new
log line records so much — the next person it happens to will hand us the answer in a single report,
instead of another round of guesswork. If you see a line beginning `[reconcile] INERT:`, that is this
guard doing its job, and it is worth sending our way.

Two earlier bugs in this same family were fixed in July, each by removing one specific cause. This
one bounds the loop itself, so the next cause we have not thought of costs you a few popups rather
than a save.

### How much of the map an unlock hands you

Region unlocks light that region's Sites of Grace so you can warp in. Until now they lit **all** of
them, which for Liurnia is 59 warp points at once, Caelid 38, Limgrave 28. Convenient — and it makes
a region you have never walked read as already explored.

| value | lights | total |
|---|---|---|
| `all` (default) | every warp point in the region | 338 |
| `landmarks` | one per sub-area | 47 |
| `entrance` | the region's front door only | 27 |

**`landmarks` uses the game's own grouping**, not a list we invented — the same partition the warp
menu uses for its sub-areas. Liurnia comes out as its four real chunks; Caelid as Smoldering Church,
Aeonia Swamp Shore and Dragonbarrow West. Because it follows the menu rather than region size it is
uneven on purpose: Gravesite, Scadu Altus and Weeping each have one sub-area and behave the same as
`entrance` there.

Whichever you pick, this is a pacing setting and nothing more. Region unlocks remain the only
progression, no item moves, no check moves, and a grace you were not handed is still yours the moment
you touch it. Regions behind a wall the game itself enforces — the Academy seal, the capital's Great
Rune gate, the sewer — hand out nothing under any setting; you walk in the way the game intends.

### The tutorial boss was paying out Stormveil

The game files bucket the ruined Chapel of Anticipation — the intro area, where you fight or flee the
Grafted Scion — under Stormveil. So the generator counted that Scion as one of Stormveil's bosses and
gave it a share of the region's sweep pool. Kill the optional tutorial boss in your first few minutes
and three dozen Stormveil Castle checks arrived with it.

**How bad it actually was: not very, by design.** Sweep pools are built from filler only —
Remembrances, key items, Great Runes, boss rewards, legendaries and shop slots are all cut out before
a sweep exists — and every one of these 36 was ordinary filler. So the seed was never in danger; you
just got an early heap of junk and consumables, and Stormveil's own bosses had less to give you
later. That containment was a deliberate design decision and it is the reason this shipped as an
annoyance rather than a broken run.

Stormveil's total is unchanged. Its pool now divides between its two real bosses, Godrick and Margit,
instead of three. The Scion's own drop, the Ornamental Straight Sword, was always a normal check and
is untouched.

There is a second Grafted Scion inside Stormveil Castle proper. It is a different fight, it was never
involved, and it is unaffected.

### The sweep settings in the middle were doing nothing

`dungeon_sweep` offers `none`, `minidungeons`, `all` and `bosses`. Only `none` ever behaved
differently — the other three granted the identical, complete sweep set, because the generator asked
"are sweeps on?" and never looked at what kind of boss it was. The values mean what they say now:

| value | sweeps | checks |
|---|---|---|
| `none` | nothing | 0 |
| `minidungeons` | catacombs, caves, tunnels, minor dungeons | 515 |
| `all` | + legacy dungeons and castles | 1971 |
| `bosses` (default) | + field bosses | 3184 |

**Your seeds do not change.** The full set is what every non-`none` value already produced, so the
default is renamed from `all` to `bosses` to describe what has actually been shipping. Had the
default stayed on `all`, this "fix" would have silently deleted field-boss sweeps from everyone's
games.

If you want dungeons swept but field bosses left alone, `all` is now that setting.

### Behind the scenes

The AP flower icon can be built again. The generator that composites it into the game's icon sheet
was lost in July, which is why AP items have worn a vanilla Telescope ever since. It is rewritten,
the artwork is in the repository, the build produces the override instead of printing instructions,
and packaging now refuses to ship a bundle without it. You will not see a change until a build stages
the texture — but it can no longer go missing quietly.

The client also re-applies the AP icon after a load. It writes an icon setting that loading a save
reverts, and it was the only such writer that never re-armed, so flowered shop slots fell back to a
telescope after the first load of a session.

### Compatibility

The slot-data contract is unchanged, so an installed v0.2.16 client pairs with a v0.2.17 seed and
logs a version-skew line — nothing in the seed format forces an update.

**The softlock fix is a different matter: it lives entirely in the client.** A v0.2.16 client on a
v0.2.17 seed will generate and play, and will still be able to lock up the way described above. If
you take one thing from this release, take the client.

You can confirm you have it: the log prints `grant-stall guard ARMED` shortly after you load in.
