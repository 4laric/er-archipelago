"""Legible-key mapping layer (SPEC-region-capstone-model, gap 4; er-legible-key-locks-spec).

Naming / messaging ONLY. This module does NOT change fill, item allocation, or the gating
mechanism -- it maps a capstone boss to the VANILLA key item whose name should be shown in
place of the synthetic ``Boss Key: <Boss>`` when a real vanilla key exists for that lock.

The join key is the boss label exactly as ``boss_locks._boss_label`` emits it (the same token
that mints ``Boss Key: <label>``), so a downstream consumer can look up by that label without
re-deriving anything. The labels below were verified against boss_data.REGION_BOSSES (see the
unit test, which re-derives them and asserts every mapping key joins).

Bosses with no real vanilla capstone key (Godrick/Grafted, Dancing Lion, Romina, Golden
Hippopotamus, Messmer/Impaler, Rellana, etc.) are simply ABSENT here -- the resolver falls
back to the synthetic ``Boss Key: <Boss>`` name for them. (Fire Giant IS mapped: Mountaintops'
capstone fog is gated by the Haligtree Secret Medallion (Right) via Castle Sol, spec section 4.)

Pure module: no Archipelago imports, so it runs in the data-invariant gate.
"""

# boss_label (as boss_locks._boss_label emits) -> vanilla capstone key display name.
# The trailing comment on each row is the common boss name the label denotes.
CAPSTONE_VANILLA_KEYS = {
    "Full Moon Queen":  "Academy Glintstone Key",       # Rennala (Raya Lucaria Academy)
    # Morgott / Omen King (Leyndell) intentionally has NO vanilla alias: its vanilla gate is a
    # COMPOUND possession check (2 Great Runes), so a single-item name ("Two Great Runes") read as a
    # concrete item and confused players. Falls back to the synthetic "Boss Key: Omen King".
    "Radahn":           "Dectus Medallion",              # Starscourge Radahn (Caelid; halves double as festival trigger)
    "Malenia":          "Haligtree Secret Medallion",    # Malenia (Snowfield/Haligtree; both halves at Rold)
    "Rykard":           "Drawing-Room Key",              # Rykard (Mt. Gelmir / Volcano Manor)
    "Mohg":             "Pureblood Knight's Medal",      # Mohg (Mohgwyn Palace)
    "Naturalborn":      "Fingerslayer Blade",            # Astel, Naturalborn of the Void (Ainsel River)
    "Black Blade":      "Deathroot",                     # Maliketh, the Black Blade (Farum Azula; Gurranq eats N deathroot)
    "a God and a Lord": "Messmer's Kindling",            # Promised Consort Radahn (DLC finale, Enir-Ilim)
    "Fire Giant":       "Haligtree Secret Medallion (Right)",  # Fire Giant (Mountaintops; Castle Sol holds the Right half -> gates Fire Giant's fog, spec section 4)
}


def display_key_name(boss_label):
    """Resolve a boss (by its ``_boss_label`` token) to the display name of its capstone lock.

    Returns the vanilla key name when one is mapped, else the synthetic ``Boss Key: <label>``
    (same string boss_locks mints), so a boss with no legible vanilla key keeps its synthetic
    name. Naming only -- callers still key fill / gating on the synthetic item.
    """
    name = CAPSTONE_VANILLA_KEYS.get(boss_label)
    if name is not None:
        return name
    return "Boss Key: " + boss_label


def synthetic_key_name(boss_label):
    """The synthetic ``Boss Key: <label>`` name for a boss (mechanism/join identity)."""
    return "Boss Key: " + boss_label


def display_for_synthetic(synthetic_name):
    """Resolve a synthetic ``Boss Key: <label>`` name straight to its display name.

    Inverse convenience for callers that already hold the minted item name. Any string that is
    not a ``Boss Key: <label>`` (or whose label is unmapped) passes through unchanged.
    """
    prefix = "Boss Key: "
    if not synthetic_name.startswith(prefix):
        return synthetic_name
    return display_key_name(synthetic_name[len(prefix):])


def has_vanilla_key(boss_label):
    """True when this boss has a legible vanilla capstone key (vs. keeping the synthetic name)."""
    return boss_label in CAPSTONE_VANILLA_KEYS
