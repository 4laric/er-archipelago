"""SPEC-goal-send -- goalLocations slot_data (Track C).

The client (from-software-archipelago-clients goal.rs) ships a Goal-send handler that reads a
`goalLocations` list of AP location ids and sends ClientStatus::Goal once EVERY id is done. An id
that also appears in `locationFlags` is detected LOCAL-FIRST by its guarding vanilla event flag
(boss DefeatFlag) -- immune to another slot's `!collect` and reload-safe; any id missing from the
detection table falls back to the server-truth checked set. An EMPTY `goalLocations` can never be
met, which is the bug in the connect log ("goalLocations empty -- this slot can NEVER send Goal").

THE GOAL IS THE GAME'S REAL TERMINUS WHEN IT EXISTS, ELSE THE TERMINAL REGION OF THE CHAIN --
never a hardcoded region.

Tier 0, THE FINALE (ruling 2026-07-14): when the conditional finale region exists this seed --
data.FINALE_REGION ('Ashen Capital'), created by features/finale.py iff every FINALE_REQUIRES
region (Farum Azula + Leyndell) is kept -- its major bosses ARE the goal: Godfrey/Hoarah Loux
(f510070) and the Elden Beast (f510230), the game's actual final bosses, now real locations in
data.py/boss_data.py (REGION_BOSSES['Ashen Capital']). The Ashen Capital is the game's real
terminus even though Farum Azula outranks Leyndell in SPINE, so tier 0 outranks the spine walk.
When the finale is not active, the ladder below decides, exactly as before.

(History, both bugs guarded by test_gf_goal_terminal: the predecessor preferred GOAL_REGION
whenever kept, and GOAL_REGION (Leyndell) is ALWAYS kept on a base seed, so every base seed's goal
collapsed to Morgott and the client sent Goal the moment he died -- the 2026-07-14 playtest bug.
An older docstring promised Hoarah Loux and the Elden Beast as goal locations while neither was a
location at all; as of the finale revival that promise is finally TRUE, and conditional.)

Resolution ladder (each tier total, deterministic, and derived -- no hand list):
  0. THE FINALE's major bosses, iff features/finale.py created the finale region this seed.
  1. MAJOR BOSSES OF THE DEEPEST KEPT REGION THAT HAS ANY, walking down from the deepest kept
     region by SPINE rank. MajorBoss membership is LOCATION_TAGS (= REGION_BOSSES arena majors
     UNION the curated MAJOR_BOSS_EXTRAS field majors -- so a Sewer-terminal seed ends on Mohg the
     Omen, not on a shallower region's arena). The spine is a total order, so "the terminal
     regions" collapse to the single deepest region that has majors; ALL of its majors are the
     goal ("clear the terminal region").
  2. Degenerate (NO kept region has any major -- only reachable under dlc_only+rolled draws over
     the majorless DLC regions): every check of the deepest kept region EXCEPT missable-tagged
     ones -- literally "clear the terminal region", and achievable by construction because
     missables are the only checks a player can permanently lose.
  3. Still empty -> ContractError. A seed whose goal cannot name one achievable location is
     unwinnable and must die at generation, not at the connect log.

great_runes ending: the rune requirement rides `great_rune_items` (core._base_slot_data), which the
client's goal.rs reads; this feature emits ONLY goalLocations (merge_slot_data raises on duplicate
top-level keys).

Invariants promised here and enforced by tests/test_gf_goal_terminal.py + test_gf_finale.py:
  * goalLocations is never empty;
  * when the finale is active, goalLocations is exactly the finale's MajorBoss set;
  * otherwise every goalLocations id lives in the DEEPEST kept region carrying them (never
    Leyndell-by-preference: a seed keeping a region deeper than Leyndell must not goal on Morgott);
  * every id belongs to a location set that exists this seed (a kept region's, or the active
    finale region's).
"""
from ..registry import Feature, register
from .. import contract
from ..region_spine import SPINE
from ..data import FINALE_REGION
from .finale import finale_active

try:
    from ..boss_data import REGION_BOSSES
except Exception:  # not yet generated
    REGION_BOSSES = {}
try:
    from ..data import LOCATIONS
except Exception:
    LOCATIONS = {}
try:
    from ..location_tags import LOCATION_TAGS
except Exception:
    LOCATION_TAGS = {}
try:
    from ..missable_locations import MISSABLE_LOCATIONS
except Exception:
    MISSABLE_LOCATIONS = {}

# Spine rank for ordering kept regions; regions off the spine sort last (defensive, never expected).
_SPINE_RANK = {r: i for i, r in enumerate(SPINE)}


def _major_boss_ids(region):
    """AP location ids of the MajorBoss-tagged checks in `region` (LOCATION_TAGS = REGION_BOSSES
    arena majors UNION MAJOR_BOSS_EXTRAS curated field majors). Falls back to the raw REGION_BOSSES
    arena entries if the tag table is unavailable (partial regen), so the goal never silently
    narrows to nothing on a data lag."""
    ids = [aid for (_name, aid, _flag) in LOCATIONS.get(region, ())
           if "MajorBoss" in LOCATION_TAGS.get(aid, ())]
    if ids:
        return sorted(ids)
    return sorted(aid for (aid, _flag, _name) in REGION_BOSSES.get(region, ()))


def _by_depth(kept):
    """Kept regions, deepest spine rank first (stable for equal/off-spine ranks by name)."""
    return sorted(kept, key=lambda r: (-_SPINE_RANK.get(r, len(SPINE)), r))


def terminal_goal_ids(kept):
    """(region, ids) for the goal: tier 0 = the finale's majors iff the finale exists for `kept`
    (see module docstring); tier 1 = majors of the deepest kept region that has any; tier 2 = the
    deepest kept region's non-missable checks. ids may be empty only if tier 2 is too (caller
    raises)."""
    if finale_active(kept):
        ids = _major_boss_ids(FINALE_REGION)
        if ids:                       # defensive: a finale with no majors falls to the spine walk
            return FINALE_REGION, ids
    ordered = _by_depth(kept)
    for region in ordered:
        ids = _major_boss_ids(region)
        if ids:
            return region, ids
    terminal = ordered[0] if ordered else None
    if terminal is None:
        return None, []
    ids = sorted(aid for (_name, aid, _flag) in LOCATIONS.get(terminal, ())
                 if aid not in MISSABLE_LOCATIONS)
    return terminal, ids


@register
class GoalLocations(Feature):
    name = "goal_locations"

    def slot_data(self, world):
        kept = list(world._kept())
        region, ids = terminal_goal_ids(kept)
        if not ids:
            raise contract.ContractError(
                "goal_locations: no achievable goal location exists in the kept set %r -- the seed "
                "would be unwinnable (goalLocations may never be empty)" % (sorted(kept),))
        return {contract.GOAL_LOCATIONS: sorted(ids)}
