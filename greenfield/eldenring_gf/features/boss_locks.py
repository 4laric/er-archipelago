"""SPEC-PARITY Phase 3 -- region bosses (+ future dungeon sweeps).

Region bosses: the 25 major bosses (method=boss_arena) joined to greenfield ap-ids by FLAG,
pre-generated into boss_data.py (matt-free). Emitted as bossLocations {region: [ap_ids]} for kept
regions -- the data a boss-based ending goal / region-boss tracker reads.

Dungeon SWEEPS (kill a dungeon boss -> auto-grant its other checks) need a per-dungeon boss-kill
flag the backbone does NOT carry: only 22/39 minidungeons have any emevd row, and those aren't
reliably boss rewards. That trigger set requires an EMEVD enrichment pass (SPEC-PARITY.md P3); the boss-defeat FLAG per dungeon is now derived from the DarkScript EMEVD (boss_sweeps.py) and
emitted as dungeonSweepFlags {boss_flag: [member_ap_ids]}; a small client flag-watch handler
(P3b-client) grants the members on boss kill. The location-keyed dungeonSweeps variant additionally
needs a boss-reward-location join (ItemLotParam) and stays empty for now.
"""
from Options import Choice, Toggle
from BaseClasses import ItemClassification
from ..registry import Feature, register
from .. import contract
from ..region_spine import DLC_REGIONS   # canonical base/DLC partition (also used by core.py)

try:
    from ..boss_data import REGION_BOSSES
except Exception:  # not yet generated
    REGION_BOSSES = {}
try:
    from ..boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION
except Exception:
    DUNGEON_SWEEPS, SWEEP_REGION = {}, {}


def _boss_label(reward: str) -> str:
    """Derive a clean boss name from a REGION_BOSSES reward string (no separate boss-name table --
    locked decision). Strips the 'Remembrance of the '/'Remembrance of ' prefix and a trailing
    "'s Great Rune"/' Great Rune' suffix. Examples: 'Remembrance of the Dancing Lion' -> 'Dancing
    Lion'; "Radahn's Great Rune" -> 'Radahn'. Names that fit neither shape (e.g. 'Elden
    Remembrance') pass through unchanged."""
    s = reward.strip()
    for pre in ("Remembrance of the ", "Remembrance of "):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    for suf in ("'s Great Rune", " Great Rune"):
        if s.endswith(suf):
            s = s[:-len(suf)]
            break
    return s.strip()


class DungeonSweep(Choice):
    """Which dungeons grant their loot in a sweep when their boss is killed. none disables sweeps;
    all covers minidungeons + legacy dungeons + castles; bosses adds field bosses. (Sweep triggers
    pending EMEVD enrichment -- see module docstring.)"""
    display_name = "Dungeon Sweep"
    option_none = 0
    option_minidungeons = 1
    option_all = 2
    option_bosses = 3
    default = 2


class BossLockPlacement(Choice):
    """Where boss-lock items are hosted once sweeps land. own_region keeps them legible and inside
    the sweep's region."""
    display_name = "Boss Lock Placement"
    option_scatter = 0
    option_own_region = 1
    option_any_boss = 2
    default = 1


class BossKeys(Toggle):
    """Mode B (deferred-release). off (default): bosses pay out as usual. on: each kept base-game
    boss mints a progression 'Boss Key: <Boss>' item; the boss's OWN AP check is logic-gated on it
    (so fill places the key reachably) and its dungeon sweep defers (sweepLockGates) until the key
    arrives. Never gates the FIGHT -- only the rewards -- so it cannot soft-lock. Base-game bosses
    only for v0.2 (DLC out), independent of the attunement gate."""
    display_name = "Boss Keys"


def _boss_keys_on(world):
    o = getattr(world.options, "boss_keys", None)
    return bool(o is not None and o.value)


def _base_boss_key_names():
    """Ordered, unique 'Boss Key: <Boss>' names for every BASE-game boss (DLC excluded), one per
    REGION_BOSSES entry -- the same set and labels as the mode-A 'Felled:' trophies. Static (read at
    import) so core can allocate ids + classify like the region-Lock items."""
    names = {}
    for r, lst in REGION_BOSSES.items():
        if r in DLC_REGIONS:
            continue
        for (_aid, _fl, reward) in lst:
            names["Boss Key: " + _boss_label(reward)] = None
    return list(names)


@register
class BossLocks(Feature):
    name = "boss_locks"
    OPTIONS = {"dungeon_sweep": DungeonSweep, "boss_lock_placement": BossLockPlacement,
               "boss_keys": BossKeys}
    ITEMS = {n: ItemClassification.progression for n in _base_boss_key_names()}

    def create_items(self, world):
        # Boss Keys (mode B): one progression 'Boss Key: <Boss>' per KEPT base boss, mirroring the
        # region-Lock item pattern. Count-neutral -- core.create_items sizes filler off len(pool),
        # so each key displaces one filler. OFF (default) -> [] -> pool byte-identical to HEAD.
        if not _boss_keys_on(world):
            return []
        kept = set(world._kept())
        return [world.create_item("Boss Key: " + _boss_label(reward))
                for r in REGION_BOSSES if r in kept and r not in DLC_REGIONS
                for (_aid, _fl, reward) in REGION_BOSSES[r]]

    def set_rules(self, world):
        # Fill soundness: gate ONLY the boss's OWN AP check in LOGIC with has(key). Fill then places
        # the key reachably and never behind the boss's own check -- without this, curated_fill
        # (region Locks -> big-ticket/Boss checks) could load a boss check with its region Lock while
        # the only path to that Lock ran through the boss check itself (a deadlock). Gate just the
        # boss's own location(s) (its reward/remembrance/great-rune check == boss_ap_id), NOT the
        # dungeon sweep -- sweep members stay manually reachable so fill is not overloaded. Forced
        # boss-key demand == #kept base bosses, far below the early-reachable slot count -> feasible.
        if not _boss_keys_on(world):
            return
        kept = set(world._kept())
        gate = {}
        for r in REGION_BOSSES:
            if r in kept and r not in DLC_REGIONS:
                for (aid, _fl, reward) in REGION_BOSSES[r]:
                    gate[aid] = "Boss Key: " + _boss_label(reward)
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
        kept = set(world._kept())
        boss_locs = {r: [aid for (aid, _f, _n) in REGION_BOSSES[r]]
                     for r in REGION_BOSSES if r in kept}
        sd = {"bossLocations": boss_locs}
        # Mode-A "Felled: <Boss>" trophy tracking (slot_data + client only; zero fill risk). Scoped
        # to KEPT regions AND base-game only (DLC bosses are OUT for v0.2 -- reuse the canonical
        # region_spine.DLC_REGIONS partition). The client mints a 'Felled: <Boss>' trophy when the
        # boss_flag fires; er-logic boss_felled / region.rs read this map keyed by boss-defeat flag.
        # Mode-B 'Boss Key' gate rides on the SAME entries: when boss_keys is ON each entry
        # ALSO carries "gate" = its 'Boss Key: <Boss>' so the client holds the boss's own check
        # until the key. gate ABSENT when boss_keys OFF (bossLockItems then HEAD-identical).
        _bk = _boss_keys_on(world)
        _items = {}
        for r in REGION_BOSSES:
            if r not in kept or r in DLC_REGIONS:
                continue
            for (aid, fl, reward) in REGION_BOSSES[r]:
                _label = _boss_label(reward)
                _entry = {"name": "Felled: " + _label, "region": r, "boss_ap_id": aid}
                if _bk:
                    _entry["gate"] = "Boss Key: " + _label
                _items[str(fl)] = _entry
        sd[contract.BOSS_LOCK_ITEMS] = _items
        if world.options.dungeon_sweep.value != 0:
            # FLAG-KEYED sweeps (boss-defeat flag -> member ap-ids), scoped to kept regions. Derived
            # from DarkScript EMEVD (boss_sweeps.py). A small client handler that watches the
            # boss-defeat flag and grants the members activates these in-game (P3b-client).
            sd[contract.DUNGEON_SWEEP_FLAGS] = {str(fl): DUNGEON_SWEEPS[fl]
                                       for fl in DUNGEON_SWEEPS if SWEEP_REGION.get(fl) in kept}
            sd[contract.DUNGEON_SWEEPS] = {}     # location-keyed variant (needs boss-reward-location join)
            # sweepLockGates: non-empty under boss_keys. Route each kept-region dungeon-sweep
            # trigger flag to its region's REPRESENTATIVE base Boss Key (first base entry). No
            # per-boss defeat-flag join exists in the data, so multi-boss regions coarsen to the
            # first key -- sound (client-side deferral hint only; sweep members are NOT logic-
            # gated). Empty when boss_keys OFF (HEAD-identical).
            _gates = {}
            if _bk:
                _rep = {}
                for r in REGION_BOSSES:
                    if r in kept and r not in DLC_REGIONS and REGION_BOSSES[r]:
                        _rep[r] = "Boss Key: " + _boss_label(REGION_BOSSES[r][0][2])
                for _fl in DUNGEON_SWEEPS:
                    _reg = SWEEP_REGION.get(_fl)
                    if _reg in kept and _reg in _rep:
                        _gates[str(_fl)] = _rep[_reg]
            sd["sweepLockGates"] = _gates
        return sd
