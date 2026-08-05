# v0.2.16 — release blurb (draft)

> Drafted 2026-07-28. A **tuning** release: the dial that decides what fills your junk checks is now
> visible and editable in the template, and a knob that had quietly stopped working works again.
> Nothing about a default seed changes, and **your existing client keeps working** — the contract
> hash did not move.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.16 — the filler pool is yours to tune**

- **`curated_filler` is in the template now, with its real numbers.** It decides what your junk
  checks pay out — gear, upgrade stones, runes, throwables. Edit the weights, or delete the block to
  follow the default. It was hidden because a stale copy had once shipped an old economy; there is a
  test holding it to the code now, which is what makes showing it safe.
  📖 **Full documentation: [What fills your junk checks](https://github.com/4laric/er-archipelago/blob/main/Elden-Ring-Archipelago-Player-Guide.md#what-fills-your-junk-checks)** — every weight, what the upgrade
  economy reserves, and how to steer which gear you get.
- **`pool_builder_intensity` works again.** It sets how good a piece of gear has to be to count as
  "juice": `max` (default), `high`, `normal`.
  ⚠️ **A higher floor means LESS gear, not better gear** — it is a smaller catalog and the surplus
  becomes junk. `max` gives you the most.
- **Four dead options retired.** `pool_builder`, `pool_builder_scope`, `pool_builder_juice_cap`,
  `pool_builder_juice_pct` described a mechanism that no longer exists. If your yaml names one it
  will now **stop and tell you** instead of ignoring it. For no gear at all, set `juice: 0`.
- **Fixed:** foreign progression items could land on Ashen Capital checks that were meant to be off
  limits under `natural_progression`.
- ✅ **No client update required.** An installed v0.2.15 client still pairs; it will log a version
  skew and carry on.

---

## Long version (release notes)

### The dial you could not see

> 📖 Player documentation for all of this lives in the Player Guide, under
> **[What fills your junk checks](https://github.com/4laric/er-archipelago/blob/main/Elden-Ring-Archipelago-Player-Guide.md#what-fills-your-junk-checks)** — it covers the full recipe, the upgrade-economy
> reservation, `pool_builder_intensity`, and the `pool_builder_pct_*` category steering.
> The guide ships in the release zip as `Elden-Ring-Archipelago-Player-Guide.md`.

`curated_filler` is the single most useful thing in the yaml and it was not in the yaml. It sets the
weights for what fills every check that is not holding something important: `juice` (real gear),
`stones` and `somber_stones` (upgrade materials), `runes`, and the small consumable categories.

It was pulled from the template for a good reason. A literal recipe in the yaml **overrides** the
default, so the block had frozen at `stones: 27` — and 27 had since been measured below the
affordability floor on three seeds out of nine, and raised to 29. Every player generating from the
shipped template was getting the economy that had just been diagnosed as too tight, while the code,
the tests and the wizard all agreed on the fixed one. Deleting the block fixed that and cost you the
dial.

So it is back, written out in full, with a test that fails if the template's numbers ever drift from
the code's again. Showing it and pinning it are the same change; either alone is a bad idea.

### A higher floor gives you less gear

`pool_builder_intensity` decides how good an item has to be before the generator counts it as gear
worth injecting. It had been frozen during the v0.2 option slim and then, in a later refactor,
quietly decayed into a constant — the option was still in the code, still documented, and could not
move anything. It reads again.

| setting | counts as juice | how many items qualify |
|---|---|---|
| `normal` | legendary only | 149 |
| `high` | legendary + rare | 536 |
| `max` (default) | + the tier below | 1013 |

**The name points the wrong way, so read this bit.** Raising the floor does not upgrade your gear —
it *shortens the list*. The number of gear slots the recipe asks for does not change, so a shorter
list means the generator runs out and the leftover slots become ordinary junk. On one seed: `max`
put 1518 catalog-grade items in the pool, `high` 872, `normal` 230. `normal` is the connoisseur
setting and you pay for it in quantity everywhere else. If you want *more* gear, raise the `juice`
weight in `curated_filler`; that is the knob for volume.
(Written up in full in the guide: [What fills your junk checks](https://github.com/4laric/er-archipelago/blob/main/Elden-Ring-Archipelago-Player-Guide.md#what-fills-your-junk-checks).)

### Four options that described a machine that is gone

`pool_builder`, `pool_builder_scope`, `pool_builder_juice_cap` and `pool_builder_juice_pct` came from
an era when gear injection had its own private budget. It does not — there is one filler budget, and
gear competes in it by its `juice` weight like every other category. That weight *is* the cap, the
share, and the on/off switch.

They are retired rather than silently dropped: a yaml that names one now fails with a message saying
so. They were hidden options, never in any shipped template, so this should reach almost nobody — but
if you hand-wrote a yaml from an older release, that is the one thing in this release that can stop
your generation, and it will tell you exactly which key to remove.

### The Ashen Capital leak

Under `natural_progression`, ten of the finale's checks were being created through a path that
skipped the rule confining other players' progression items to safe locations. Seven foreign
progression items had been placed on them. Found by a new multiworld test — two Elden Rings and two
Hollow Knights — that asserts items flow both ways and that foreign progression only ever lands on
the progression surface. It found this on its first run, which is the argument for having it.

### Compatibility

The slot-data contract did not change, and that is what decides whether a client can talk to a seed.
An installed v0.2.15 client pairs with a v0.2.16 seed and logs a version-skew line. Updating both
halves is still the tidier thing to do, but nothing here forces it.
