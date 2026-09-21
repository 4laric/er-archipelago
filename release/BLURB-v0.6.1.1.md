# v0.6.1.1 — release blurb (draft)

_Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** `CONTRACT_HASH` is unmoved at `2aa64f43`, so the v0.6.1.1 client and the v0.6.1 client are interchangeable on each other's seeds, and both read every 0.4.13, 0.5.x and 0.6.0.x seed through the audited legacy-contract bridge. Swapping the `.dll` mid-run puts nothing at risk and needs no reroll or save migration. The standing version gates still apply and none are new.

## What you need to update

- **Client:** Optional, recommended -- three client-only fixes (repeating grace banner, false boss-defeat announcements, Leyndell tracker on older seeds). A v0.6.1 client still plays every v0.6.1.1 seed.
- **APWorld:** Host-only, for newly generated rooms.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** The new `flask_upgrade_minimum` is optional.
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

**The options screen is shorter and plainer.** If you build your yaml in the Archipelago Launcher or
on the web options page, it now opens on a "Start Here" section with six decisions -- do you own the
DLC, how many regions, which boss ends the run, how many Great Runes, enemy scaling, Death Link --
and the expert dials are out of the way (still in the template yaml and the wizard; nothing you
already wrote stops working). Every tooltip was cut to fit on screen, and the rewrite fixed several
that said the wrong thing. New: ready-made presets (Base Game, Short Run, Whole Map, DLC Only) and an
`EldenRing-Quickstart.yaml` with just the six decisions.

**Flasks stop coming up short.** A six-region seed could hand you as few as four flask upgrades. There is now a floor of two per region (`flask_upgrade_minimum`, `off` to opt out).

**`start_region_pool` is a list of places you might start, not a list of places you will visit.** A 25-name pool used to drag 27 regions into a six-region seed. Now it narrows where you open and `num_regions` still sets the size.

**Cross-game Locks reach your partners again** when your yaml says "I do not care where" -- they had all stayed home.

**Client fixes:** graces stop re-announcing "unlocked" every few seconds, a flask heal lock re-arms after loading in, Malenia and the other shardbearers are no longer announced as beaten when you only received the rune, and the tracker reads Leyndell correctly on older seeds. Also: Talisman Pouch counts as useful, and a corrupted item pool from another game's plugin now says whose it is.

## What carried over from v0.6.1

Nothing is owed. v0.6.1's release workflows were green before the stable promotion, which was paid in this window's opening commit (stable and `latest.json` now read v0.6.1), and the one loose end from that cut -- a stale test-shard weights file -- was fixed before the tag.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
