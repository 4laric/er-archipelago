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
from Options import Choice
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


@register
class BossLocks(Feature):
    name = "boss_locks"
    OPTIONS = {"dungeon_sweep": DungeonSweep, "boss_lock_placement": BossLockPlacement}

    def slot_data(self, world):
        kept = set(world._kept())
        boss_locs = {r: [aid for (aid, _f, _n) in REGION_BOSSES[r]]
                     for r in REGION_BOSSES if r in kept}
        sd = {"bossLocations": boss_locs}
        # Mode-A "Felled: <Boss>" trophy tracking (slot_data + client only; zero fill risk). Scoped
        # to KEPT regions AND base-game only (DLC bosses are OUT for v0.2 -- reuse the canonical
        # region_spine.DLC_REGIONS partition). The client mints a 'Felled: <Boss>' trophy when the
        # boss_flag fires; er-logic boss_felled / region.rs read this map keyed by boss-defeat flag.
        sd[contract.BOSS_LOCK_ITEMS] = {
            str(fl): {"name": "Felled: " + _boss_label(reward), "region": r, "boss_ap_id": aid}
            for r in REGION_BOSSES if r in kept and r not in DLC_REGIONS
            for (aid, fl, reward) in REGION_BOSSES[r]
        }
        if world.options.dungeon_sweep.value != 0:
            # FLAG-KEYED sweeps (boss-defeat flag -> member ap-ids), scoped to kept regions. Derived
            # from DarkScript EMEVD (boss_sweeps.py). A small client handler that watches the
            # boss-defeat flag and grants the members activates these in-game (P3b-client).
            sd[contract.DUNGEON_SWEEP_FLAGS] = {str(fl): DUNGEON_SWEEPS[fl]
                                       for fl in DUNGEON_SWEEPS if SWEEP_REGION.get(fl) in kept}
            sd[contract.DUNGEON_SWEEPS] = {}     # location-keyed variant (needs boss-reward-location join)
            sd["sweepLockGates"] = {}
        return sd
