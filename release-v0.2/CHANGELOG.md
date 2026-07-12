# Changelog

## v0.2 -- 2026-07-12

v0.2 is a from-scratch, provenance-clean rebuild of the Elden Ring world. No
data or code from the earlier community lineage remains. It requires
**Archipelago 0.6.7**, and it never modifies your game files: you run vanilla
Elden Ring, the apworld generates the seed, and the client .dll does everything
at runtime.

### Breaking: the game id is now `Elden Ring` (with a space)

v0.1 called the game `EldenRing`. v0.2 calls it `Elden Ring`. A v0.1 yaml is
rejected at generation with:

    No world found to handle game EldenRing. Did you mean 'Elden Ring'?

The upside of the new id: v0.1 and v0.2 install side by side without conflict.
If you have a v0.1 seed in flight, you can finish it on v0.1 and start your
next seed on v0.2.

### Breaking: the option surface shrank to 19 tunable options

The yaml now exposes only the options a player actually tunes. The rest are
frozen to sensible defaults and no longer appear in the yaml at all.

**Do not retrofit a v0.1 yaml.** Archipelago silently ignores yaml options it
does not recognize -- there is no error and no warning. An old yaml full of
renamed or removed options can generate a seed that is *not* the one you think
you configured, and nothing will tell you. Start from the shipped
`EldenRing.yaml` template and edit from there.

### What's new

The world itself was rebuilt from the ground up against public game data
(params, MSBs, grace anchors), with every rule keyed off region, map id, event
flag, and item name -- never off an imported location name. It ships no
FromSoftware content and no third-party randomizer config or code: just the
MIT client and the data-derived apworld. See `ATTRIBUTION.md` and the repo's
`PROVENANCE.md`.

- **The Shattering, on the clean base.** `num_regions` -- the marquee mode
  that turns Elden Ring's open map into an Archipelago progression graph --
  is rebuilt on the data-derived world. You spawn at Roundtable Hold with one
  region open; every other region's Lock is a multiworld item; the goal
  region is always kept, so the seed is always winnable. `num_regions_order`
  picks a fixed (`spine`) or random (`rolled`) set of kept regions.
- **Real item shuffle.** item shuffle pays out each check's own vanilla ER
  item, shuffled across the checks (~98.9% carry a real item; the rest give a
  Rune).
- **Great-Rune goal.** `ending_condition: great_runes` requires collecting
  Great Runes, auto-clamped to what is reachable this seed.
- **Dungeon sweeps.** Kill a dungeon's boss and its other checks
  auto-register (dungeon sweep).
- **Pool building and varied filler.** pool builder scrubs the Rune tail
  and injects rare and legendary items; varied filler spreads the rest
  across item types.
- **Grace bundling.** A Region Lock lights all of its region's graces at
  once, so an arriving Lock means you can warp straight in.
- **Scaling and quality of life.** Completion scaling, Scadutree blessing
  scope, start-with torch / steed / flasks, all maps revealed, early
  leveling, no weapon requirements, buyable Stonesword Keys, a flattened
  smithing-stone ladder, and DeathLink.

### Under the hood

- A single contract file defines every slot_data key's shape, producer, and
  consumer, validated at generation time -- the world and client stay in
  lockstep with no client fork.
- Replay suites and region-correctness gates run in CI and catch
  wrong-behavior bugs (for example, region or grace mis-bundling), not just
  missing-feature bugs.
- The MIT runtime client carries over from v0.1 -- still no fork of anyone
  else's client -- rebuilt in lockstep with the world: the shipped `.dll`
  and the apworld are a matched pair from the same release.

### Fixed

Confirmed fixed in playtesting on 2026-07-12:

- Spirit Calling Bell was unusable; Spirit Ashes are now callable from the
  received item.
- Map-piece items were granted on connect; the map reveal now fires without
  minting item grants.
- Flasks were double-granted after a tutorial-death reload.
- A rolled start could leave you without Torrent; it no longer can.

### Known issues

Current issues are tracked in `KNOWN-ISSUES.md`. The headline: a few checks
can still pay out the vanilla item instead of the Archipelago one (contained
-- it cannot strand a run; worst case you miss a filler item), and DLC seeds
are experimental. Base game is the recommended, supported way to play.

### Licensing

The project adopts the upstream Archipelago license (MIT). The runtime client
is MIT; the data-derived apworld ships no non-free FromSoftware content and no
third-party randomizer config or code. You bring your own copy of Elden Ring.
See `ATTRIBUTION.md`.

---

*Elden Ring and Shadow of the Erdtree are trademarks of FromSoftware / Bandai
Namco. This is an unofficial fan project and ships no game assets.*
