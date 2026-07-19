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

Multi-key gates (features/legacy_key_gates._MULTI_KEY_GATES) handle a sub-dungeon whose checks need
MORE THAN ONE key ANDed -- DLC Lamenter's Gaol needs BOTH the Gaol Upper and Lower Level Keys.

Currently gated:
  Academy Glintstone Key  ->  Raya Lucaria Academy (its own region since region-spine v2; the key
                              is required IN ADDITION to the region's Lock, like the vanilla fog);
  Gaol U+L Level Keys      ->  Lamenter's Gaol (m41_02, Charo's) -- BOTH keys, check-level, incl.
                              the Lamenter boss reward (f520770). See _MULTI_KEY_GATES;
  Hole-Laden Necklace     ->  Metyr's remembrance check. NB: the Cathedral surface bucket 6920 (the
                              old Scaduview, folded into Shadow Keep 2026-07-19), but Metyr's ARENA is
                              m25_00, whose own grace the game buckets 6900 = Scadu Altus (MSB truth,
                              measured 2026-07-12) -- so the gated check lives in Scadu Altus.

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

# MULTI-KEY gates: a dungeon whose checks need MORE THAN ONE key ANDed (nested cells). DLC Lamenter's
# Gaol (m41_02, in Charo's): the Gaol Upper + Lower Level Keys open its nested cells, the Lamenter
# boss sits behind them, and BOTH vanilla key locations sit INSIDE the gaol (flags 41027000 /
# 41027320) -- so there is no "spare key outside" and the coarse region-lock model would treat the
# whole gaol (incl. the Lamenter) as reachable on the Charo's Lock alone: softlock (Alaric, playtest
# 2026-07-16). Require BOTH keys for EVERY gaol check + the boss reward. Conservative on purpose:
# over-requiring a key (the outer cell may strictly need only the Upper key) never softlocks, and the
# keys -- forbidden from the gaol via _GATING_ITEMS -- place freely into the rest of the pool.
# `ranges` are map-lot flag windows [lo, hi); `extra` pins non-map-lot flags (the boss reward).
_MULTI_KEY_GATES = (
    {"id": "lamenters_gaol", "region": "Charo's",
     "keys": ("Gaol Upper Level Key", "Gaol Lower Level Key"),
     "ranges": ((41020000, 41030000),),
     "extra": frozenset({520770})},   # Lamenter's Mask f520770 = the Lamenter boss reward
)
_MULTI_KEYS = frozenset(k for g in _MULTI_KEY_GATES for k in g["keys"])

# Gating items (region keys + Great Runes) must NEVER be placed BEHIND another gate: two gates can
# otherwise form an unsolvable cycle (the necklace lands on a Leyndell rune-gated check while a Great
# Rune lands on the necklace-gated Metyr check -> deadlock; FillError seen 2026-07-10). Forbid ALL of
# them on every gated location (supersedes the old "!= own key" self-gate rule).
_GREAT_RUNES = frozenset(nm for nm in ITEM_CATALOG if nm.endswith("Great Rune"))
_GATING_ITEMS = _GREAT_RUNES | frozenset(_LEGACY_KEYS) | _MULTI_KEYS


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


def _multi_gated_location_ids(gates):
    """ap_ids gated by a MULTI-key gate -> the tuple of keys that must ALL be held. {ap_id: (k1, k2)}.
    A location matches if its flag falls in any of the gate's map-lot ranges or its `extra` set."""
    out = {}
    for g in gates:
        for (_name, ap_id, flag) in LOCATIONS.get(g["region"], ()):
            try:
                fl = int(flag)
            except (TypeError, ValueError):
                continue
            if fl in g["extra"] or any(lo <= fl < hi for (lo, hi) in g["ranges"]):
                out[ap_id] = g["keys"]
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
        """SINGLE-key gate names live this seed: toggle on, vanilla items shuffled (so the key is
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

    def _active_multi(self, world):
        """MULTI-key gates live this seed: toggle on, vanilla items shuffled, region kept, and every
        one of the gate's keys is a real catalog item (all keys must be placeable/holdable)."""
        opt = getattr(world.options, "legacy_dungeon_keys", None)
        if opt is None or not opt.value:
            return []
        shuf = getattr(world.options, "item_shuffle", None)
        if not (shuf and shuf.value):
            return []
        kept = set(world._kept())
        return [g for g in _MULTI_KEY_GATES
                if g["region"] in kept and all(k in ITEM_CATALOG for k in g["keys"])]

    def generate_early(self, world) -> None:
        # Publish EVERY active gate key (single + multi) so core._class_for upgrades them to PROGRESSION
        # (they are GOODS => filler by default). Empty -> nothing marked progression, default fill
        # unchanged. set_rules re-derives single vs multi (multi keys are not in _LEGACY_KEYS).
        keys = list(self._active_keys(world))
        for g in self._active_multi(world):
            keys += list(g["keys"])
        world.gf_legacy_keys = keys

    def set_rules(self, world) -> None:
        active = getattr(world, "gf_legacy_keys", [])
        single = [k for k in active if k in _LEGACY_KEYS]
        multi = self._active_multi(world)
        if not single and not multi:
            return
        player = world.player
        gate = _gated_location_ids(single)          # {ap_id: key_name}
        mgate = _multi_gated_location_ids(multi)     # {ap_id: (k1, k2, ...)}
        # ENTRANCE rule (2026-07-14, gated-children fix): a key that gates a whole MAP RANGE gates
        # region ENTRY, and core.create_regions parents such regions under region_spine.REGION_PARENT
        # (test_gf_gated_children enforces the pairing). Requiring the key on the "To <region>" edge
        # itself makes the wall transitive to any future child hung under it, exactly like the
        # physical seal. Check-level keys (empty range, e.g. the Hole-Laden Necklace) gate no entry.
        # Multi-key gates are check-level (a sub-dungeon inside a kept region) -> no entrance rule.
        for key in single:
            region, (lo, hi) = _LEGACY_KEYS[key]
            if hi <= lo:
                continue
            try:
                entrance = world.multiworld.get_entrance(f"To {region}", player)
            except KeyError:
                continue  # region sealed this seed -- nothing to gate
            prev_ent = entrance.access_rule
            entrance.access_rule = (lambda state, p=prev_ent, k=key:
                                    p(state) and state.has(k, player))
        for loc in world.multiworld.get_locations(player):
            ap = getattr(loc, "address", None)
            keys = ()
            sk = gate.get(ap)
            if sk is not None:
                keys = (sk,)
            mk = mgate.get(ap)
            if mk is not None:
                keys = keys + tuple(mk)
            if not keys:
                continue
            prev = loc.access_rule
            loc.access_rule = (lambda state, p=prev, ks=keys:
                               p(state) and all(state.has(k, player) for k in ks))
            prev_item = loc.item_rule
            loc.item_rule = lambda item, pv=prev_item: pv(item) and item.name not in _GATING_ITEMS

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key yet (in-game hard gate = follow-up)
