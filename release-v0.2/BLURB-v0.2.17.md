# v0.2.17 — release blurb (draft)

> Drafted 2026-07-29. One new setting and one fix, both from **dafranky67**'s reports. Your existing
> client keeps working: the slot-data contract did not move.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.17 — choose how much of a region an unlock opens**

- **`region_grace_unlock`** decides how many Sites of Grace a region unlock lights.
  `all` (default) lights every warp point — Liurnia is 59 at once. `landmarks` lights one per
  sub-area, so Liurnia becomes Lake-Facing Cliffs / East Raya Lucaria Gate / Moonlight Altar /
  Ruin-Strewn Precipice. `entrance` lights only the way in.
  It cannot strand you: unlocks are still the only progression, every check stays where it was, and
  any grace you were not handed is still reachable on foot.
- **Fixed:** killing the tutorial Grafted Scion paid out 36 Stormveil Castle checks. All 36 were
  ordinary filler — sweeps never contain key items, Great Runes, Remembrances or boss rewards — so
  it was an early pile of junk, not a broken seed.
- ✅ **No client update required.**

---

## Long version (release notes)

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
logs a version-skew line. Updating both halves is tidier; nothing here forces it.
