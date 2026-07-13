"""Legacy-dungeon key gates -- a separate-map legacy dungeon folded into a parent region is entered
with a KEY ITEM, but the coarse region-lock model treats its checks as reachable the moment the
parent region's Lock is held. Each entry here adds a LOGIC access rule: the dungeon's checks need
the key item IN ADDITION to the parent Lock, mirroring the vanilla "you can't get in without the
key" gate, so AP fill can never strand required progression (a region Lock, a required Great Rune)
behind a key it never proved reachable.

Data-driven table _LEGACY_KEYS: {key item name: (parent region, (flag_lo, flag_hi))}. A map-lot
acquisition flag encodes its map (mAA -> AA......), so a flag in [flag_lo, flag_hi) that lives in the
parent region is a check inside that dungeon. Winnability by construction: the key is marked
PROGRESSION (core._class_for reads world.gf_legacy_keys) and at least one vanilla source of every
listed key sits OUTSIDE its dungeon (e.g. the Academy Glintstone Key on the Liurnia overworld at
flag 1034457100, which is not in the m14 range), so fill always has a reachable slot to place it.

Currently gated:
  Academy Glintstone Key  ->  Raya Lucaria Academy (its own region since region-spine v2; the key
                              is required IN ADDITION to the region's Lock, like the vanilla fog);
  Hole-Laden Necklace     ->  Metyr's remembrance check. NB: the Cathedral surface is Scaduview
                              (bucket 6920), but Metyr's ARENA is m25_00, whose own grace the game
                              buckets 6900 = Scadu Altus (MSB truth, measured 2026-07-12) -- so the
                              gated check lives in Scadu Altus.

Toggle `legacy_dungeon_keys` (DefaultOnToggle). Off -> no gate; the key stays filler and default fill
is unchanged. LOGIC-only for now (no client hard-gate / kick), same status as features/leyndell_gate.
"""
from Options import DefaultOnToggle
from ..registry import Feature, register

try:
    from ..data import LOCATIONS
except Exception:  # pragma: no cover
    LOCATIONS = {}
try:
    from ..item_ids import ITEM_CATALOG
except Exception:
    ITEM_CATALOG = {}

# {key item name: (region whose checks are gated, (flag_lo, flag_hi))}. flag_hi exclusive. m14
# map-lot flags are 14000000..14999999 (Raya Lucaria Academy); the spare key on the LIURNIA
# overworld (flag 1034457100) is outside both the range and the region, so fill can always place a
# key there or anywhere else reachable.
_LEGACY_KEYS = {
    "Academy Glintstone Key": ("Raya Lucaria Academy", (14000000, 15000000)),
    "Hole-Laden Necklace": ("Scadu Altus", (0, 0)),   # Metyr arena m25_00 -> bucket 6900 (see above)
}
_LEGACY_EXTRA = {"Academy Glintstone Key": frozenset({197, 60440}), "Hole-Laden Necklace": frozenset({510550})}

# Gating items (region keys + Great Runes) must NEVER be placed BEHIND another gate: two gates can
# otherwise form an unsolvable cycle (the necklace lands on a Leyndell rune-gated check while a Great
# Rune lands on the necklace-gated Metyr check -> deadlock; FillError seen 2026-07-10). Forbid ALL of
# them on every gated location (supersedes the old "!= own key" self-gate rule).
_GREAT_RUNES = frozenset(nm for nm in ITEM_CATALOG if nm.endswith("Great Rune"))
_GATING_ITEMS = _GREAT_RUNES | frozenset(_LEGACY_KEYS)


def _gated_location_ids(active):
    """ap_ids of the checks gated by each active key: parent-region locations whose flag is in the
    key's map range. {ap_id: key_name}."""
    out = {}
    for key in active:
        parent, (lo, hi) = _LEGACY_KEYS[key]
        extra = _LEGACY_EXTRA.get(key, frozenset())
        for (_name, ap_id, flag) in LOCATIONS.get(parent, ()):
            try:
                fl = int(flag)
            except (TypeError, ValueError):
                continue
            if lo <= fl < hi or fl in extra:
                out[ap_id] = key
    return out


class LegacyDungeonKeys(DefaultOnToggle):
    """Gate legacy dungeons behind their vanilla key item in logic (e.g. Raya Lucaria Academy needs
    the Academy Glintstone Key on top of its region Lock). Keeps fill from placing required
    progression behind a key it hasn't proven reachable. On by default; off restores the
    region-Lock-only model."""
    display_name = "Legacy Dungeon Key Gates"


@register
class LegacyKeyGates(Feature):
    name = "legacy_key_gates"
    OPTIONS = {"legacy_dungeon_keys": LegacyDungeonKeys}

    def _active_keys(self, world):
        """Key names whose gate is live this seed: toggle on, vanilla items shuffled (so the key is
        in the pool), the key name is a real catalog item, and its parent region is kept."""
        opt = getattr(world.options, "legacy_dungeon_keys", None)
        if opt is None or not opt.value:
            return []
        shuf = getattr(world.options, "item_shuffle", None)
        if not (shuf and shuf.value):
            return []  # key only enters the pool when vanilla items are shuffled
        kept = set(world._kept())
        return [k for k, (parent, _rng) in _LEGACY_KEYS.items()
                if k in ITEM_CATALOG and parent in kept]

    def generate_early(self, world) -> None:
        # Publish the active keys so core._class_for upgrades them to PROGRESSION (they are GOODS =>
        # filler by default). Empty -> nothing marked progression, default fill unchanged.
        world.gf_legacy_keys = self._active_keys(world)

    def set_rules(self, world) -> None:
        active = getattr(world, "gf_legacy_keys", [])
        if not active:
            return
        gate = _gated_location_ids(active)
        if not gate:
            return
        player = world.player
        for loc in world.multiworld.get_locations(player):
            key = gate.get(getattr(loc, "address", None))
            if key is None:
                continue
            prev = loc.access_rule
            loc.access_rule = lambda state, p=prev, k=key: p(state) and state.has(k, player)
            prev_item = loc.item_rule
            loc.item_rule = lambda item, pv=prev_item: pv(item) and item.name not in _GATING_ITEMS

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key yet (in-game hard gate = follow-up)
