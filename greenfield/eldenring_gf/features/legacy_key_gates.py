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
  Academy Glintstone Key  ->  Raya Lucaria Academy (m14, folded into Liurnia of the Lakes).

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

# {key item name: (parent region name, (flag_lo, flag_hi))}. flag_hi exclusive. m14 map-lot flags are
# 14000000..14999999 (Raya Lucaria Academy); 1034457100 (the Liurnia-overworld spare key) is OUTSIDE
# that range, so it is never gated -- fill can always place a key there or anywhere else reachable.
_LEGACY_KEYS = {
    "Academy Glintstone Key": ("Liurnia of the Lakes", (14000000, 15000000)),
}


def _gated_location_ids(active):
    """ap_ids of the checks gated by each active key: parent-region locations whose flag is in the
    key's map range. {ap_id: key_name}."""
    out = {}
    for key in active:
        parent, (lo, hi) = _LEGACY_KEYS[key]
        for (_name, ap_id, flag) in LOCATIONS.get(parent, ()):
            try:
                fl = int(flag)
            except (TypeError, ValueError):
                continue
            if lo <= fl < hi:
                out[ap_id] = key
    return out


class LegacyDungeonKeys(DefaultOnToggle):
    """Gate folded-in legacy dungeons behind their key item in logic (e.g. Raya Lucaria Academy needs
    the Academy Glintstone Key on top of the Liurnia Lock). Keeps fill from placing required
    progression behind a key it hasn't proven reachable. On by default; off restores the coarse
    region-only model."""
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

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key yet (in-game hard gate = follow-up)
