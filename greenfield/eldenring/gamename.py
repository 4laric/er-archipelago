"""THE AP GAME NAME -- the single source of truth for the string Archipelago keys everything on.

Archipelago keys the data package, every player yaml, the wizard's emitted yaml, the poptracker
pack and the client's handshake on ONE string. Before #1465 that string was typed out at ~20 Python
sites, three Rust sites and every shipped/preset/tester yaml, so a rename would have shipped
half-done -- which is not hypothetical: the v0.1 -> v0.2 rename (`EldenRing` -> `Elden Ring`) left
`er_yaml_lint.py` looking for the old key for months (every rule silently no-op) and left the
wizard emitting yamls naming a game Archipelago does not have.

WHY ITS OWN MODULE, not just `core.GAME`. `core.py` imports `BaseClasses` / `worlds.AutoWorld` /
`Options`, i.e. it only imports inside a running Archipelago. Half the readers of this name are
tools that run OUTSIDE the world -- `er_yaml_lint.py`, `dump_options_metadata.py`,
`gf_multiworld_smoke.py`, `gen_contract.py` -- and they cannot pay for an Archipelago import just
to learn a string. This module imports NOTHING, so it is importable from anywhere:

    from .gamename import GAME                 # inside the world package
    sys.path.insert(0, ".../greenfield/eldenring"); from gamename import GAME   # outside it

`core.GAME` is now an alias of this, and `contract.py` mirrors it into `contract_gen.rs` so the
client reads the same string. To rename the game, change it HERE, run
`python greenfield/gen_contract.py` and `python tools/dump_options_metadata.py`, and fix the yamls
the yaml gate names. `tests/test_gf_game_name_single_source.py` fails on any other site.
"""

GAME = "Elden Ring"

# Game keys a player yaml may legitimately carry. The v0.1 name is kept because a v0.1 yaml is
# exactly the one that most needs `er_yaml_lint`'s REMOVED-option migration messages -- it is
# accepted for LINTING only, never emitted, and the yaml gate rejects it in files we ship.
LEGACY_GAME_KEYS = ("EldenRing",)
YAML_GAME_KEYS = (GAME,) + LEGACY_GAME_KEYS
