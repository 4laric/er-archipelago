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
    from ..location_tags import LOCATION_TAGS       # ap id -> [surface class, ...]
except Exception:  # not yet generated -> the per-seed surface cut is a no-op
    LOCATION_TAGS = {}


# The half of contract.SURFACE_CLASSES that gen_data ADMITS into a sweep and this side cuts PER
# SEED. Its complement (gen_data._SWEEP_NEVER_TAGS) is the permanent floor -- boss drops,
# remembrances, great runes, key items and merchant stock are never sweep members in any seed and no
# option restores them. See gen_data's comment for why the split falls where it does; the two halves
# PARTITION the vocabulary and test_gf_boss_sweeps asserts exactly that, so a new premium class has
# to be filed on one side deliberately.
_SWEEP_SURFACE_CUTTABLE = frozenset({"Seedtree", "Church", "Fragment", "Revered", "Basin",
                                     "Legendary"})


def seed_surface_classes(world):
    """The surface classes THIS seed says may hold progression, as a plain set.

    Not `progression_surface.selected_surface()`: that returns a canonically ORDERED list because
    the feasibility ladder's determinism depends on the order, and nothing here iterates -- this is
    a membership test only, so importing the feature (and its Options dependency) buys nothing and
    costs a cycle. Falls back to contract.SURFACE_DEFAULT_CLASSES when the option is absent, which
    is the conservative direction: the default surface is the widest cut of the six.

    Unfiltered by the valid vocabulary on purpose -- an unknown key cannot be in
    _SWEEP_SURFACE_CUTTABLE, so it can only ever fail to cut, and AP's VerifyKeys has already
    rejected it upstream anyway."""
    opt = getattr(getattr(world, "options", None), "progression_surface", None)
    if opt is None:
        return frozenset(contract.SURFACE_DEFAULT_CLASSES)
    return frozenset(getattr(opt, "value", None) or ())


def _full_area_sweeps_on(world):
    """Is this seed's `full_area_sweeps` on? Absent option (or no world) reads OFF, which is the
    default and the HEAD behaviour -- every synthetic-world unit test that predates the option
    therefore keeps measuring the surface cut it was written for."""
    opt = getattr(getattr(world, "options", None), "full_area_sweeps", None)
    return bool(opt is not None and getattr(opt, "value", 0))


def sweep_surface_cut(world, location_tags=None):
    """The member ap ids this seed must NOT sweep: the ones whose class its Progression Surface has
    claimed for progression.

    WHY THIS IS PER SEED AND NOT BAKED. Until 2026-08-13 gen_data cut the whole 16-class vocabulary,
    so a sweep was "filler-only" in the narrow sense of "holds nothing the surface could ever name".
    That is a corpus-wide answer to a per-seed question: `Legendary` and `Basin` are not in
    SURFACE_DEFAULT_CLASSES at all, so in a default seed those 51 checks were barred from a sweep to
    protect a placement that could not happen. The rule now matches what the seed actually decided --
    a class that cannot host progression here is ordinary area loot, and killing the boss pays it out.

    🛑 THE HONEST EDGE, stated rather than special-cased. An EMPTY surface turns confinement off
    entirely (progression scatters as vanilla AP fill decides) and this cut correctly returns
    nothing -- but that is not a hole this change opens. With no confinement, our own Locks and, at
    `confine_foreign_progression` 0, foreign advancement can already land on any of the 3731
    UNTAGGED filler members a sweep has always granted. The surface is the only statement a seed
    makes about where progression may go; when it says "nowhere in particular" there is nothing for
    a tag cut to act on, and DungeonSweep's docstring says so.

    ⚠️ progression_surface's feasibility LADDER can widen past the player's selection when the
    surface is too small to host every Lock (a few-region seed). If it reaches its +Legendary or
    +Seedtree,Church rung it can place a Lock on a check this cut has already released, and the
    sweep will hand it over. Not a soft-lock -- a sweep member's access rule is its region, so the
    Lock was reachable there anyway and the sweep only makes it earlier -- but it is the one way a
    sweep can pay out progression under a non-empty surface, and it is why this returns the BASE
    selection rather than pretending to predict the ladder.

    🛑 `full_area_sweeps` TURNS THIS OFF ENTIRELY (#1033, siffrin + bobler). It is checked HERE
    rather than in `enabled_sweeps` so that every reader of the cut agrees about what this seed
    grants -- a cut that two callers disagree about is the defect `enabled_sweeps` was written to
    prevent. When the option is on the cut is empty, the six cuttable classes stay in the payload
    whatever the surface says, and the honest edge above stops being an edge and becomes the
    behaviour: a boss kill CAN hand over this seed's own Locks, and at the default
    `confine_foreign_progression` another player's. That is not a soft-lock for the same reason the
    ladder case is not -- a sweep member's access rule is its own region and the trigger boss stands
    in a region this seed kept (#445) -- so the sweep only makes a reachable check arrive earlier.

    Pure over its inputs (module globals by default) so it unit-tests with synthetic data."""
    if _full_area_sweeps_on(world):
        return frozenset()
    tags = LOCATION_TAGS if location_tags is None else location_tags
    claimed = _SWEEP_SURFACE_CUTTABLE & seed_surface_classes(world)
    if not claimed:
        return frozenset()
    return frozenset(ap for ap, t in tags.items() if claimed.intersection(t))


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


# Which boss CLASSES each rung sweeps -- MOVED TO contract.py 2026-08-13 so the AP-free wizard census
# tool can read it (it prices the SweepSlot box). Re-exported under the old private names so every
# reader in this module and its tests keeps working and there is still exactly one table.
_SWEEP_MINI = contract.SWEEP_MINI_CLASSES
_SWEEP_RUNGS = contract.SWEEP_RUNGS


class DungeonSweep(Choice):
    """Which bosses hand you their area's loot in a sweep when you kill them.

    none -- no sweeps; every check is picked up where it lies.
    minidungeons -- catacombs, caves, tunnels and minor dungeons only (~510 checks).
    all -- those plus legacy dungeons and castles (~2614).
    bosses (default) -- those plus FIELD bosses, i.e. everything (~3876).

    Those are the BAKED pools. What a seed grants is that minus its Progression Surface cut below;
    at the default surface, ~3782 at the widest rung.

    🛑 UNTIL 2026-07-29 THESE THREE WERE THE SAME THING. The emit gated on `value != 0` and never
    filtered by class, so minidungeons/all/bosses each granted the full 3197 -- the ladder in this
    docstring described behaviour that had never been implemented, and the player guide and the
    v0.2.15 release notes repeated it. The rungs are real now.

    The DEFAULT moved 'all' -> 'bosses' at the same time, and that is not a behaviour change: the
    full set is what every non-none value already granted, so 'bosses' IS what shipped. Leaving the
    default at 'all' would have quietly dropped field sweeps (1213 checks, 38%) from every seed
    under the banner of a bug fix.

    A sweep never hands you another boss's reward, a Remembrance, a Great Rune, a key item or a
    merchant's stock: those are cut when the sweep is built and no option restores them.

    Everything else in the area is yours, INCLUDING the good stuff -- Golden Seeds, Sacred Tears,
    Scadutree Fragments, Revered Spirit Ashes, Crystal Tears and the legendaries (2026-08-13; it was
    filler-only before, +145 checks corpus-wide). The exception is the classes YOU put on the
    Progression Surface: those are where this seed places its Locks, so they are taken back out of
    the sweep, per seed. At the default surface that means Golden Seeds, Sacred Tears, Scadutree
    Fragments and Revered Ashes stay where they lie and the legendaries and Crystal Tears sweep;
    untick a collectathon line on the surface and the sweep picks it up instead.

    🛑 ONE SWEEP MEMBER PER TRIGGER CAN NOW HOLD PROGRESSION, in a default seed (2026-08-13). The
    default Progression Surface includes `SweepSlot`, which nominates a single member of every sweep
    you run as somewhere a key item may be placed -- so killing a boss can hand you one. That is the
    only class the surface does NOT take back out of the sweep, and deliberately: taking it back
    would delete the check it just nominated. Drop `SweepSlot` from progression_surface if you would
    rather a sweep never pay out progression -- or see `full_area_sweeps` for the opposite ask,
    every check in the area including the progression; the cost of dropping it is that at the default
    `confine_foreign_progression` another player's key items have only ~30 checks of yours to land
    on, and most of them stop arriving (er-archipelago#631).

    🛑 With an EMPTY Progression Surface there is no confinement at all, so progression scatters
    wherever AP's fill puts it -- including onto ordinary sweep members, as it always could. The cut
    can only act on a surface that says something.

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


class FullAreaSweeps(Toggle):
    """Should a boss kill hand you EVERYTHING in its area, including the good stuff this seed is
    using for progression?

    off (default) -- a sweep pays out the area's ordinary loot. The classes you put on the
    Progression Surface are taken back out of it, because those are exactly where this seed places
    its key items: at the default surface that is Golden Seeds, Sacred Tears, Scadutree Fragments
    and Revered Spirit Ashes, and you still walk to those yourself.

    on -- nothing is taken back out. Every check the sweep holds is granted the moment the boss
    dies, progression included, so killing a boss can hand you a region Lock (or, at the default
    `confine_foreign_progression`, another player's item). That is the point of the option, not a
    side effect: it is what "killing the boss gives me the area" actually means. It cannot strand
    you -- a sweep only ever grants checks in a region you kept and behind a boss you could reach,
    so it makes a reachable check arrive earlier and never makes an unreachable one required.

    WHAT IT DOES NOT DO, in any seed. This widens WHICH checks a sweep pays; it does not widen
    which bosses sweep (that is `dungeon_sweep`) and it does not lift the permanent floor:

    * another boss's reward, remembrance or Great Rune -- handing those over would delete the fight;
    * gate and quest KEY ITEMS;
    * merchant stock, which is bought at a counter rather than picked up off the ground.

    Nor can it reach a check whose position was never recovered from the game data: those belong to
    no boss's area, so no boss kill can grant them. Requested by siffrin and bobler (#1033).

    Missable checks are unaffected by this option in either direction -- they have always been
    ordinary sweep members (170 of the 289 are swept today), so a sweep already rescues most of
    them and this changes nothing about which. `protect_missable_locations` is the option for that.

    Corpus size of the change: +113 member links at the default Progression Surface (4101 -> 4214),
    up to +215 for a seed that puts all six of the collectathon/rarity classes on its surface, and
    exactly zero for a seed with an empty surface -- an empty surface makes no claim, so there was
    nothing being taken back out to restore."""
    display_name = "Full Area Sweeps"


class RevealSweepBossNames(Toggle):
    """Show boss names for tracker sweep rows before their region has been opened.

    Off by default so the tracker does not turn the sweep convenience into a boss spoiler.  This
    is presentation-only: the emitted sweep groups, their members, and every logic rule are
    identical either way; the client alone decides whether a locked row may reveal its label.
    """
    display_name = "Reveal Hidden Sweep Boss Names"
    default = 0


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


def rung_sweeps(world, _want_unjoined=False):
    """{boss flag: [member ap ids]} at this seed's RUNG, BEFORE the per-seed surface cut.

    Split out of `enabled_sweeps` so `progression_surface.sweep_slot_aps` can ask "which sweeps does
    this seed run?" without asking "which members did the surface claim?" -- because it is the thing
    that decides the surface. 🛑 Calling `enabled_sweeps` from the surface would be a cycle:
    enabled_sweeps -> sweep_surface_cut -> seed_surface_classes -> the surface -> sweep_slot_aps ->
    enabled_sweeps. The rung filter reads only `dungeon_sweep`, so it is safe from either side.
    """
    opt = getattr(getattr(world, "options", None), "dungeon_sweep", None)
    key = getattr(opt, "current_key", None) or "bosses"
    allowed = _SWEEP_RUNGS.get(key, _SWEEP_RUNGS["bosses"])
    out, unjoined = {}, []
    runtime_skips = contract.runtime_sweep_skips()
    if allowed:
        for fl, members in DUNGEON_SWEEPS.items():
            # #878: a trigger positively known not to fire is not a runtime sweep. Keep the baked
            # table as evidence, but never send this group to the client/tracker. Do NOT use the
            # wider sweep_slot_skips() set here: unnamed/unaudited groups are unsafe for required
            # progression, not proven dead at runtime.
            if fl in runtime_skips:
                continue
            info = BOSS_HEALTHBARS.get(fl)
            if info is None:
                # A sweep whose boss is not in boss_healthbars cannot be classified. Count it, say
                # so, and keep it only at the widest rung -- a filter with no tally is a lie.
                unjoined.append(fl)
                if key != "bosses":
                    continue
            elif info[2] not in allowed:
                continue
            out[fl] = members
    return (out, unjoined, key) if _want_unjoined else out


def enabled_sweeps(world):
    """The sweeps this seed actually grants: {boss flag: [member ap ids]} at the chosen rung.

    ONE definition, used by the slot_data emit AND by the boss-key gating below. They used to be
    written separately and would have silently disagreed the moment the rungs became real -- gating
    a member behind a boss key whose sweep is not emitted strands it behind a trigger that never
    fires."""
    rung, unjoined, key = rung_sweeps(world, _want_unjoined=True)
    if not rung:
        return {}
    # ...and the PER-SEED surface cut on top of the rung. gen_data admits the six cuttable classes
    # into the baked member lists; this seed takes back the ones its own Progression Surface claims.
    #
    # 🛑 SweepSlot (contract.SURFACE_DERIVED_CLASSES) is deliberately NOT consulted here. It is not
    # one of _SWEEP_SURFACE_CUTTABLE, so a seed that puts SweepSlot on its surface does NOT lose the
    # member it just nominated -- that is the whole point of the class, and it is why the cut reads
    # `_SWEEP_SURFACE_CUTTABLE & seed_surface_classes` rather than the raw selection. Were it
    # otherwise this would be self-referential: the surface would name the sweep, the cut would
    # remove it, and the surface would then be naming a member that no longer exists.
    surface_cut = sweep_surface_cut(world)
    out, cut_links, emptied = {}, 0, []
    for fl, members in rung.items():
        if surface_cut:
            kept_members = [ap for ap in members if ap not in surface_cut]
            cut_links += len(members) - len(kept_members)
            if not kept_members:
                # Possible only now that a group's whole membership can be surface-claimed. An empty
                # group is not a sweep: the client would draw a group that can never grant anything.
                emptied.append(fl)
                continue
            out[fl] = kept_members
        else:
            out[fl] = members
    if unjoined:
        import warnings
        warnings.warn("dungeon_sweep: %d sweep(s) have no boss_healthbars class and were %s: %s"
                      % (len(unjoined), "kept (rung=bosses)" if key == "bosses" else "dropped",
                         sorted(unjoined)[:5]))
    if cut_links or emptied:
        # Rule 4: say the size of the cut out loud. A seed's sweep total moving because the player
        # ticked a surface class is intended; it moving for any other reason is not, and this is the
        # only number that can tell those apart after the fact.
        print("dungeon_sweep: progression-surface cut removed %d member link(s)%s"
              % (cut_links, ", emptying %d group(s)" % len(emptied) if emptied else ""))
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
    runtime_skips = contract.runtime_sweep_skips()
    for fl in dungeon_sweeps:
        if fl in runtime_skips:
            continue
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
        for _fl_str, _key in _sweep_lock_gates(kept, dungeon_sweeps=_live).items():
            for _member in _live.get(int(_fl_str), ()):
                gate.setdefault(_member, _key)
    return gate


@register
class BossLocks(Feature):
    name = "boss_locks"
    OPTIONS = {"dungeon_sweep": DungeonSweep, "full_area_sweeps": FullAreaSweeps,
               "reveal_sweep_boss_names": RevealSweepBossNames,
               "boss_lock_placement": BossLockPlacement, "boss_keys": BossKeys}
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
        # Presentation-only tracker preference (#1184).  Emit it even when sweeps are off so the
        # wire shape is stable and the setting remains inspectable in a generated seed.
        sd[contract.REVEAL_SWEEP_BOSS_NAMES] = bool(world.options.reveal_sweep_boss_names.value)
        if world.options.reveal_sweep_boss_names.value:
            # A client predating #1184 would silently ignore the chosen spoiler policy. Refuse that
            # pairing loudly only for opted-in seeds; the default remains compatible with old DLLs.
            sd[contract.REQUIRES_CLIENT_FEATURES] = ["reveal_sweep_boss_names"]
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
            sd["sweepLockGates"] = _sweep_lock_gates(kept, dungeon_sweeps=_live) if _bk else {}
        return sd
