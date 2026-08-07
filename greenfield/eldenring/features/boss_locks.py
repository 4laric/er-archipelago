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
from Options import Choice, Toggle, Visibility
from BaseClasses import ItemClassification
from ..registry import Feature, register
from .. import contract
from ..region_spine import DLC_REGIONS   # canonical base/DLC partition (also used by core.py)
from . import legible_keys   # synthetic Boss Key -> vanilla key display-name layer (naming only)

try:
    from ..boss_data import REGION_BOSSES
except Exception:  # not yet generated
    REGION_BOSSES = {}
try:
    from ..boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION
except Exception:
    DUNGEON_SWEEPS, SWEEP_REGION = {}, {}
try:
    from ..boss_sweeps import SWEEP_ARENA_REGION   # trigger -> region the BOSS is fought in (#445)
except Exception:
    SWEEP_ARENA_REGION = {}
try:
    from ..boss_healthbars import BOSS_HEALTHBARS   # flag -> (map, tile, CLASS, name)
except Exception:
    BOSS_HEALTHBARS = {}
try:
    from ..boss_healthbars import BOSS_HEALTHBARS
except Exception:
    BOSS_HEALTHBARS = {}


def _hb_class(fl):
    """Boss class for a sweep trigger flag (the boss's defeat event flag; for interior classes this
    is the entity id, for field bosses the EMEVD-derived flag) from the DisplayBossHealthBar datamine;
    default 'legacy' (region major -> stays key-gated) when unknown, so the exemption is conservative."""
    info = BOSS_HEALTHBARS.get(int(fl))
    return info[2] if info else "legacy"


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


# Which boss CLASSES each rung sweeps. boss_healthbars classifies every boss as one of
# catacomb/cave/tunnel/dungeon (the minidungeons), legacy (legacy dungeons + castles) or field.
_SWEEP_MINI = frozenset({"catacomb", "cave", "tunnel", "dungeon"})
_SWEEP_RUNGS = {
    "none": frozenset(),
    "minidungeons": _SWEEP_MINI,
    "all": _SWEEP_MINI | {"legacy"},
    "bosses": _SWEEP_MINI | {"legacy", "field"},
}


class DungeonSweep(Choice):
    """Which bosses hand you their area's loot in a sweep when you kill them.

    none -- no sweeps; every check is picked up where it lies.
    minidungeons -- catacombs, caves, tunnels and minor dungeons only (~515 checks).
    all -- those plus legacy dungeons and castles (~1984).
    bosses (default) -- those plus FIELD bosses, i.e. everything (~3197).

    🛑 UNTIL 2026-07-29 THESE THREE WERE THE SAME THING. The emit gated on `value != 0` and never
    filtered by class, so minidungeons/all/bosses each granted the full 3197 -- the ladder in this
    docstring described behaviour that had never been implemented, and the player guide and the
    v0.2.15 release notes repeated it. The rungs are real now.

    The DEFAULT moved 'all' -> 'bosses' at the same time, and that is not a behaviour change: the
    full set is what every non-none value already granted, so 'bosses' IS what shipped. Leaving the
    default at 'all' would have quietly dropped field sweeps (1213 checks, 38%) from every seed
    under the banner of a bug fix.

    Sweeps are FILLER-ONLY by construction -- Remembrances, key items, Great Runes, boss rewards,
    legendaries and shop slots are cut before a sweep is built -- so no rung can gate progression.

    A group is only sent to a seed that can actually FIRE it (issue #445): the trigger boss's ARENA
    region has to be kept too, not just the region its members live in. Six groups are fought
    somewhere other than where their loot lies -- the Golden Hippopotamus hands over 104 Shadow Keep
    checks from Scadu Altus ground -- and a seed that keeps one region without the other used to
    ship a sweep whose boss the region lock would not let the player reach. Those groups are dropped
    instead. The checks are unaffected: every member is an ordinary pickup in its own region, so what
    is lost is the convenience, not the loot.
    """
    display_name = "Dungeon Sweep"
    option_none = 0
    option_minidungeons = 1
    option_all = 2
    option_bosses = 3
    default = 3


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
    arrives. Never gates the FIGHT -- only the rewards -- so it cannot soft-lock. Covers base AND
    DLC bosses (keys freely placeable in any world; local BK waiting on a remote key is intended,
    Rule B)."""
    display_name = "Boss Keys"
    # v0.2: OFF by default and fully INERT when off (no keys minted, no gates, no slot_data) -- so it
    # only ever raises "what's a boss key?" in the template. HIDDEN from the yaml template + web UI for
    # v0.2 (still settable by name; the D+F cycle-break infra sits ready underneath). Un-hide when boss
    # keys graduate to a recommended feature with its own non-boss premium surfaces. (Alaric 2026-07-10)
    visibility = Visibility.spoiler


def _boss_keys_on(world):
    o = getattr(world.options, "boss_keys", None)
    return bool(o is not None and o.value)


def _boss_key_names():
    """Ordered, unique 'Boss Key: <Boss>' names for every boss (BASE + DLC), one per REGION_BOSSES
    entry. Static (read at import) so core can allocate ids + classify like the region-Lock items.
    DLC keys are declared/allocated UNCONDITIONALLY (mirroring how DLC region Locks always get ids)
    but only ENTER the pool when boss_keys is ON and the DLC region is kept (create_items) -- so an
    OFF seed's pool is count-identical to HEAD; only the id catalog gains the unused DLC key names."""
    names = {}
    for r, lst in REGION_BOSSES.items():
        for (_aid, _fl, reward) in lst:
            names["Boss Key: " + _boss_label(reward)] = None
    return list(names)


def sweep_trigger_reachable(fl, kept, sweep_region=None, arena_region=None):
    """True iff this seed can ever FIRE sweep group `fl` -- issue #445.

    A group has two regions, and until 2026-08-07 only one of them was checked:

    * the MEMBERS' region (`SWEEP_REGION`) -- where the checks it grants live;
    * the ARENA region (`SWEEP_ARENA_REGION`) -- where the player must STAND to kill the trigger
      boss, read from PlayRegionParam's boss-area row.

    They are the same region for 106 of the 112 audited triggers and this predicate changes nothing
    there. For the other 6 they differ, and a seed that keeps the members' region WITHOUT the arena's
    ships a group whose trigger can never fire: `er_logic::region_lock::kick_decision` ejects the
    player from the arena's play_region bucket before the fight. The Golden Hippopotamus is the case
    that found it (issue #445) -- arena bucket 69000 = m61_48_45 = Scadu Altus, 104 members in Shadow
    Keep -- and boblerrr's 6-region seed kept Shadow Keep and not Scadu Altus.

    🛑 AN UNKNOWN ARENA IS TREATED AS REACHABLE, and that is a documented LOWER BOUND, not a clean
    bill. 113 of the 225 triggers have no `boss_area_regions.tsv` row, so this predicate cannot speak
    for them; refusing them instead would silently delete 1686 member links on missing evidence.
    `slot_data` logs the unaudited count on every seed and
    test_gf_boss_sweeps.test_sweep_arena_coverage_floor ratchets it, because a self-reported coverage
    number is not a safeguard unless something acts on it (CONTRIBUTING rule 11).

    Pure over its inputs (module globals by default) so it unit-tests with synthetic data injected."""
    sweep_region = SWEEP_REGION if sweep_region is None else sweep_region
    arena_region = SWEEP_ARENA_REGION if arena_region is None else arena_region
    kept = set(kept)
    if sweep_region.get(fl) not in kept:
        return False
    arena = arena_region.get(fl)
    return arena is None or arena in kept


def unreachable_sweeps(live, kept, sweep_region=None, arena_region=None):
    """The subset of `live` this seed keeps the members' region for but can never TRIGGER, as
    {flag: (members_region, arena_region)}. Split out from the filter so the drop can be COUNTED and
    named in the log rather than silently vanishing -- a filter with no tally is a lie
    (CONTRIBUTING rule 4). Groups whose members' region is simply not kept are not in here: those
    are ordinary out-of-scope groups, not a defect."""
    sweep_region = SWEEP_REGION if sweep_region is None else sweep_region
    arena_region = SWEEP_ARENA_REGION if arena_region is None else arena_region
    kept = set(kept)
    return {fl: (sweep_region.get(fl), arena_region.get(fl))
            for fl in live
            if sweep_region.get(fl) in kept
            and not sweep_trigger_reachable(fl, kept, sweep_region, arena_region)}


def enabled_sweeps(world):
    """The sweeps this seed actually grants: {boss flag: [member ap ids]} at the chosen rung.

    ONE definition, used by the slot_data emit AND by the boss-key gating below. They used to be
    written separately and would have silently disagreed the moment the rungs became real -- gating
    a member behind a boss key whose sweep is not emitted strands it behind a trigger that never
    fires."""
    opt = getattr(getattr(world, "options", None), "dungeon_sweep", None)
    key = getattr(opt, "current_key", None) or "bosses"
    allowed = _SWEEP_RUNGS.get(key, _SWEEP_RUNGS["bosses"])
    if not allowed:
        return {}
    out, unjoined = {}, []
    for fl, members in DUNGEON_SWEEPS.items():
        info = BOSS_HEALTHBARS.get(fl)
        if info is None:
            # A sweep whose boss is not in boss_healthbars cannot be classified. Count it, say so,
            # and keep it only at the widest rung -- a filter with no tally is a lie.
            unjoined.append(fl)
            if key == "bosses":
                out[fl] = members
            continue
        if info[2] in allowed:
            out[fl] = members
    if unjoined:
        import warnings
        warnings.warn("dungeon_sweep: %d sweep(s) have no boss_healthbars class and were %s: %s"
                      % (len(unjoined), "kept (rung=bosses)" if key == "bosses" else "dropped",
                         sorted(unjoined)[:5]))
    return out


def _sweep_lock_gates(kept, region_bosses=None, dungeon_sweeps=None, sweep_region=None):
    """sweepLockGates {str(sweep_trigger_flag): 'Boss Key: <Boss>'} for kept regions (base + DLC).

    Two-tier routing, per SPEC-region-capstone-model section 7 gap #3:

    * PRECISE per-boss join -- if a dungeon-sweep TRIGGER flag is itself a boss-defeat flag in
      REGION_BOSSES, route that sweep to the Boss Key of the boss it actually belongs to. This is
      the derivable per-boss precision: the sweep flag and the boss-defeat flag are the same event
      flag, so the join needs no extra data. Today only Rennala's m14 flag (14000800) aligns; the
      set grows automatically as the EMEVD-enrichment regen makes more boss_data defeat flags equal
      their dungeon's sweep trigger.

    * REPRESENTATIVE fallback (the documented coarsening GAP) -- when the sweep trigger flag is NOT
      a known boss-defeat flag (no per-boss join derivable), route to the region's FIRST Boss Key.
      Multi-boss regions therefore coarsen to one key. This is sound for the CLIENT deferral hint:
      an over-broad representative key just delays a client grant. (Note: sweep members ARE now
      logic-gated behind their key -- key_gate_map/set_rules, 2026-07-08 -- so the representative
      coarsening also decides WHICH key a member logic-defers on; that only ever gates on a key
      reachable no later than the precise one, and progression_surface precollects lock-hosting keys,
      so it cannot soft-lock or overload fill.) The precise branch drops in once the flags align.

    Pure over its inputs (module globals by default) so it unit-tests with synthetic data injected."""
    region_bosses = REGION_BOSSES if region_bosses is None else region_bosses
    dungeon_sweeps = DUNGEON_SWEEPS if dungeon_sweeps is None else dungeon_sweeps
    sweep_region = SWEEP_REGION if sweep_region is None else sweep_region
    kept = set(kept)
    flag_to_key, rep = {}, {}
    for r, lst in region_bosses.items():
        if r not in kept or not lst:
            continue
        rep[r] = "Boss Key: " + _boss_label(lst[0][2])          # region representative (first boss)
        for (_aid, fl, reward) in lst:
            flag_to_key[fl] = "Boss Key: " + _boss_label(reward)  # per-boss defeat flag -> its key
    gates = {}
    for fl in dungeon_sweeps:
        reg = sweep_region.get(fl)
        if reg not in kept:
            continue
        # ...and the group must be FIREABLE at all (#445): a gate on a trigger whose arena region is
        # not kept holds a sweep that was never going to fire, so the client would render "waiting on
        # <lock>" for a boss the seed cannot let the player reach. Same predicate as the emit, so the
        # two can never disagree about which groups exist.
        if not sweep_trigger_reachable(fl, kept, sweep_region):
            continue
        # Exempt minor-dungeon + field sweeps from boss-key deferral: killing a catacomb/cave/tunnel/
        # divine-tower/field boss releases its (map-local / own-tile) sweep IMMEDIATELY. Only region
        # MAJORS (legacy class) defer behind a Boss Key. (2026-07-08: a Divine Tower boss -- Onyx Lord,
        # m34 -- was stranding its sweep behind Altus's representative key: "killed onyx lord, no sweep".)
        if _hb_class(fl) != "legacy":
            continue
        key = flag_to_key.get(fl)          # PRECISE: sweep trigger flag == a boss-defeat flag
        if key is None:
            key = rep.get(reg)             # FALLBACK: region representative (coarsening gap)
        if key is not None:
            gates[str(fl)] = key
    return gates


def key_gate_map(world):
    """{ap_id: 'Boss Key: <Boss>'} for every AP check gated on a boss key this seed: each kept boss's
    OWN check (REGION_BOSSES) plus, when dungeon_sweep is on, its gated sweep MEMBERS. Empty when
    boss_keys is off. Pure over world options + the generated boss tables. Shared by `set_rules` (which
    installs the has(key) logic gates) and `progression_surface.apply` (which precollects the key of any
    boss a region Lock landed on -- the boss-key <-> region-lock cycle break, D)."""
    if not _boss_keys_on(world):
        return {}
    kept = set(world._kept())
    gate = {}
    for r in REGION_BOSSES:
        if r in kept:
            for (aid, _fl, reward) in REGION_BOSSES[r]:
                gate[aid] = "Boss Key: " + _boss_label(reward)
    _ds = getattr(world.options, "dungeon_sweep", None)
    if _ds is not None and _ds.value != 0:
        # Sweep MEMBERS defer behind their boss key too (their real trigger is the key-gated sweep, not
        # their own pickup flag). setdefault so the boss's own-check gate wins on overlap.
        _live = enabled_sweeps(world)
        for _fl_str, _key in _sweep_lock_gates(kept).items():
            for _member in _live.get(int(_fl_str), ()):
                gate.setdefault(_member, _key)
    return gate


@register
class BossLocks(Feature):
    name = "boss_locks"
    OPTIONS = {"dungeon_sweep": DungeonSweep, "boss_lock_placement": BossLockPlacement,
               "boss_keys": BossKeys}
    ITEMS = {n: ItemClassification.progression for n in _boss_key_names()}

    def create_items(self, world):
        # Boss Keys (mode B): one progression 'Boss Key: <Boss>' per KEPT boss (base + DLC now),
        # mirroring the region-Lock item pattern. Count-neutral -- core.create_items sizes filler
        # off len(pool), so each key displaces one filler. OFF (default) -> [] -> pool byte-identical
        # to HEAD (the extra DLC key NAMES sit unused in the id catalog, never in the pool).
        if not _boss_keys_on(world):
            return []
        kept = set(world._kept())
        return [world.create_item("Boss Key: " + _boss_label(reward))
                for r in REGION_BOSSES if r in kept
                for (_aid, _fl, reward) in REGION_BOSSES[r]]

    def set_rules(self, world):
        # Gate each key-gated boss check in LOGIC on has(key). The set is built by key_gate_map(): each
        # boss's OWN reward/remembrance/great-rune check, PLUS (2026-07-08) its dungeon-SWEEP MEMBERS --
        # a member's real trigger is the key-gated sweep, and leaving members "manually reachable" once
        # let fill strand a region Lock on one while its Boss Key sat behind that very Lock (in-game
        # soft-lock: Altus Lock on the Full Moon Queen sweep member, Boss Key: Grafted in Altus). So
        # members ARE logic-gated now (an older comment claiming they never are is wrong). This alone
        # does NOT prevent the region-Lock/boss-key cycle when a Lock lands on the key-gated check
        # itself -- progression_surface.apply() closes that by precollecting lock-hosting keys (D).
        # Forced key demand == #kept bosses, far below the early-reachable slot count. DLC parity: DLC
        # keys are freely placeable in ANY world (Rule B); a DLC start BK'ed on a remote key is INTENDED.
        gate = key_gate_map(world)
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
        # Mode-A "Felled: <Boss>" trophy tracking (slot_data + client only; zero fill risk). The
        # client mints a 'Felled: <Boss>' trophy when the boss_flag fires; er-logic boss_felled /
        # region.rs read this map keyed by boss-defeat flag. Mode-B 'Boss Key' gate rides on the SAME
        # entries: when boss_keys is ON each entry ALSO carries "gate" = its 'Boss Key: <Boss>' so
        # the client holds the boss's own check until the key. gate ABSENT when boss_keys OFF.
        #
        # DLC scoping: base-only for v0.2 while boss_keys is OFF (mode-A trophy default is base-only,
        # so an OFF seed is HEAD-identical and no DLC boss flag leaks). When boss_keys is ON, DLC
        # entries ARE emitted -- their mode-B 'gate' hint is the ONLY channel that tells the client
        # to defer a DLC boss's own check until its key, giving DLC full parity with base (the gate
        # rides on this entry, so the entry must exist to carry it).
        _bk = _boss_keys_on(world)
        _items = {}
        for r in REGION_BOSSES:
            if r not in kept:
                continue
            if r in DLC_REGIONS and not _bk:
                continue
            for (aid, fl, reward) in REGION_BOSSES[r]:
                _label = _boss_label(reward)
                _entry = {"name": "Felled: " + _label, "region": r, "boss_ap_id": aid}
                if _bk:
                    _entry["gate"] = "Boss Key: " + _label
                    # Legible-lock display name (naming only; fill/gating still key the synthetic
                    # 'Boss Key: <Boss>'). Present only when a real vanilla key exists for this lock.
                    if legible_keys.has_vanilla_key(_label):
                        _entry["display_key"] = legible_keys.display_key_name(_label)
                _items[str(fl)] = _entry
        sd[contract.BOSS_LOCK_ITEMS] = _items
        if world.options.dungeon_sweep.value != 0:
            # FLAG-KEYED sweeps (boss-defeat flag -> member ap-ids), scoped to kept regions. Derived
            # from DarkScript EMEVD (boss_sweeps.py). A small client handler that watches the
            # boss-defeat flag and grants the members activates these in-game (P3b-client).
            _live = enabled_sweeps(world)
            # #445: a group is emitted only when BOTH its members' region and its trigger's ARENA
            # region are kept. Dropping it here is what stops the F6 tracker promising "0/104 checks
            # -- waiting on the boss" for a boss this seed can never let the player fight. The
            # members are unaffected: each is an ordinary location in `locationFlags` and is still
            # collected by walking to it. What is lost is the convenience the sweep was, and saying
            # so beats rendering a row that will never move.
            _dropped = unreachable_sweeps(_live, kept)
            sd[contract.DUNGEON_SWEEP_FLAGS] = {str(fl): _live[fl] for fl in _live
                                                if sweep_trigger_reachable(fl, kept)}
            _unaudited = [fl for fl in _live if fl not in SWEEP_ARENA_REGION]
            print("[greenfield] dungeon sweeps: %d group(s) armed; %d dropped as UNFIREABLE "
                  "(trigger's arena region not kept, #445)%s; %d group(s) UNAUDITED (no arena row -- "
                  "not verified clean)"
                  % (len(sd[contract.DUNGEON_SWEEP_FLAGS]), len(_dropped),
                     (" -- " + ", ".join("%d %s members, arena %s (%d checks)"
                                         % (fl, _dropped[fl][0], _dropped[fl][1], len(_live[fl]))
                                         for fl in sorted(_dropped, key=lambda x: -len(_live[x]))))
                     if _dropped else "",
                     len(_unaudited)))
            sd[contract.DUNGEON_SWEEPS] = {}     # location-keyed variant (needs boss-reward-location join)
            # sweepLockGates: non-empty under boss_keys, base + DLC. Per-boss PRECISE where the sweep
            # trigger flag is itself a boss-defeat flag, else the region-representative fallback (the
            # documented coarsening gap). See _sweep_lock_gates. Sound either way -- client-side
            # deferral hint only; sweep members are NEVER logic-gated. Empty when boss_keys OFF
            # (HEAD-identical).
            sd["sweepLockGates"] = _sweep_lock_gates(kept) if _bk else {}
        return sd
