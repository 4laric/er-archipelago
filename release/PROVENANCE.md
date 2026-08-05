# Provenance — why this release is a clean rebuild

This is the single, external-facing statement of where the Elden Ring Archipelago
world comes from. The short version: **the shipped `eldenring.apworld` is built from
scratch against vanilla Elden Ring game data, and the runtime client is original MIT
code.** The release carries no FromSoftware game assets and no code or data from any
other randomizer project. This is a hard architectural constraint, enforced in CI —
not a claim made after the fact.

## The five non-negotiables

These are the rules the build holds itself to (formerly tracked internally as the
`SPEC-PARITY` "P1–P5"):

1. **No third-party data or code copied.** No location-name set, no
   location→key or location→target maps, and no name-keyed rule modules are taken
   from any other randomizer or apworld.
2. **Every feature is re-derived from the world's own substrate.** Location and item
   data are computed from vanilla params (`ItemLotParam`, `ShopLineupParam`), MSB
   geometry, and decompiled EMEVD — data you already own by owning the game.
3. **Rules key off the world's own columns.** Progression logic keys on
   region / map-id / event-flag / item-name derived from that substrate, never on a
   borrowed naming scheme.
4. **A stable, versioned client contract.** The apworld and client agree on a
   contract whose hash is checked on connect (`greenfield/CONTRACT.md`).
5. **CI gates it.** The generated data carries a freshness stamp, and the test suite
   plus a clean-room region-correctness oracle run on every push and PR, so a
   provenance regression cannot land silently.

## What the apworld does **not** ship

- **No non-free FromSoftware content** — no game assets, no regulation data, no
  map/message files. Only derived tables (event flags, item ids, region mappings)
  computed from your own game install.
- **No third-party randomizer config or code** — nothing from thefifthmatt's
  randomizer or any other apworld (see `ATTRIBUTION.md`).

## Why v0.2, specifically

The v0.1 world's location set traced upstream through another modder's apworld. The
v0.2 rebuild exists to cut that lineage entirely: the world is re-derived from vanilla
game data, so the whole release — data-derived apworld plus original MIT client — is
cleanly redistributable under MIT.

See `ATTRIBUTION.md` for credits and license, and
`ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` for how this composes with thefifthmatt's
randomizer (with item randomization OFF, because that part is ours).
