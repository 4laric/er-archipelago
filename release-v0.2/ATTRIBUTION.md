# Attribution, Licensing & Provenance

## License

This project adopts the **upstream Archipelago license -- MIT**. Archipelago core
is MIT-licensed, and both shipped components follow it:

- **Runtime client** (`eldenring_archipelago.dll`, the `eldenring-archipelago`
  Rust crate) -- MIT, original work.
- **apworld** (`eldenring.apworld`) -- MIT; a from-scratch, data-derived world
  (see Provenance below).

MIT grants the right to use, modify, and redistribute, including in derivative
works, provided the copyright notice and license text are retained. You supply
your own copy of Elden Ring; this release ships **no FromSoftware game assets**.

## Credits

- **nex3** -- for the Archipelago Rust ecosystem (`archipelago_rs`) that the
  runtime client builds on.
- **vswarte** -- for the FromSoftware reverse-engineering / tooling groundwork the
  client's live-game integration relies on.
- **The Archipelago project and community** -- for the multiworld framework, the
  MIT-licensed core, and the ecosystem conventions this release follows.

## Provenance -- why v0.2 is a clean rebuild

The whole point of the v0.2 rebuild is **provenance cleanliness**. Unlike the
v0.1 world -- whose location set traced upstream through another modder's
apworld -- the v0.2 apworld is built **from scratch against vanilla Elden Ring
game data**, and ships **none** of the following:

- **No non-free FromSoftware content.** The apworld carries no game assets, no
  regulation data, no map/message files -- only derived tables (event flags, item
  ids, region mappings) computed from data you already own by owning the game.
- **No third-party randomizer config or code.** No location-name set, no
  location->key or location->target maps, and no name-keyed rule modules are copied
  from any other randomizer or apworld. Every rule keys off the world's **own**
  data columns -- region / map-id / event-flag / item-name pulled from vanilla
  params (`ItemLotParam`, `ShopLineupParam`), MSB, and EMEVD.

This is a hard architectural constraint, not a claim after the fact. It is spelled
out in the repo as `SPEC-PARITY.md` non-negotiables **P1-P5** (P1: no third-party
data/code copied; P2: every feature re-derived from the world's own substrate;
P3: original feature logic re-keyed to region/map ids; P4: stable client contract;
P5: CI gates every phase) and cross-referenced in `PROVENANCE.md`.

The runtime client is original work that reads only public param data to map
checks to event flags. Because the shipped apworld is data-derived and the client
is original MIT code, the whole release is redistributable under MIT.

---

*Elden Ring and Shadow of the Erdtree are trademarks of FromSoftware / Bandai
Namco. This is an unofficial fan project and ships no game assets.*
