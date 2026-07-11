"""SPEC-goal-send -- goalLocations slot_data (Track C).

The client (from-software-archipelago-clients goal.rs) ships a Goal-send handler that reads a
`goalLocations` list of AP location ids and sends ClientStatus::Goal once EVERY id is done. An id
that also appears in `locationFlags` is detected LOCAL-FIRST by its guarding vanilla event flag
(boss DefeatFlag) -- immune to another slot's `!collect` and reload-safe; any id missing from the
detection table falls back to the server-truth checked set. An EMPTY `goalLocations` can never be
met, which is the bug in the connect log ("goalLocations empty -- this slot can NEVER send Goal").

matt-free derivation (greenfield's own boss_data.py + region_spine.py, keyed by REGION/flag only):

  goal region (region_locks ending): the seed's win is reaching the goal region and clearing it.
  The goal region (Leyndell) is always kept whenever it is eligible (region_spine.compute_kept), so
  its boss locations are always in play. We emit Leyndell's boss-arena AP-ids -- the Omen King
  (Morgott), Hoarah Loux (Godfrey) and the Elden Remembrance (Elden Beast) -- i.e. beating the run.
  All three carry a vanilla DefeatFlag present in `locationFlags`, so they are flag-detected: Goal
  fires exactly when the final bosses are down in-game, never prematurely and never on a stray
  `!collect`.

  DLC-only (goal region sealed): under dlc_only Leyndell is not kept, so there is no capital to
  reach. We fall back to the boss locations of the DEEPEST kept region in the fixed spine order (the
  terminal region of the run). This is always a kept region, so the goal can never require a sealed
  location -> the seed stays winnable.

  great_runes ending: the AP victory rule additionally needs N Great Runes (core.set_rules). To keep
  the client Goal-send faithful to that rule -- not fire before the run is truly beaten -- we ALSO
  add the boss location that drops each REQUIRED Great Rune (matched by item name against the
  boss tuple in boss_data.py, scoped to kept regions). world._required_runes() is already clamped to
  the runes reachable this seed, so every added location is in a kept region and reachable.

Emits ONLY the `goalLocations` key (no other source emits it; merge_slot_data raises on a duplicate
top-level key). Never empty for a normal seed: there is always at least one kept region with a boss.
"""
from ..registry import Feature, register
from .. import contract
from ..region_spine import GOAL_REGION, SPINE

try:
    from ..boss_data import REGION_BOSSES
except Exception:  # not yet generated
    REGION_BOSSES = {}

# Spine rank for ordering kept regions; regions off the spine sort last (defensive, never expected).
_SPINE_RANK = {r: i for i, r in enumerate(SPINE)}


def _region_boss_ids(region):
    """AP location ids of the boss-arena checks in `region` (empty if the region has no boss)."""
    return [aid for (aid, _flag, _name) in REGION_BOSSES.get(region, [])]


def _terminal_region(kept):
    """The endpoint region of the run: the goal region when it is kept, else the deepest kept region
    (max spine rank) that actually has a boss. Always returns a KEPT region so the goal is never
    sealed out. None only if no kept region has any boss (degenerate; caller falls back)."""
    if GOAL_REGION in kept and _region_boss_ids(GOAL_REGION):
        return GOAL_REGION
    with_boss = [r for r in kept if _region_boss_ids(r)]
    if not with_boss:
        return None
    return max(with_boss, key=lambda r: _SPINE_RANK.get(r, len(SPINE)))


@register
class GoalLocations(Feature):
    name = "goal_locations"

    def slot_data(self, world):
        kept = list(world._kept())
        ids = set()
        # Endpoint: clear the goal region (or the deepest kept region under dlc_only).
        term = _terminal_region(set(kept))
        if term is not None:
            ids.update(_region_boss_ids(term))
        # great_runes ending: also require the boss dropping each REQUIRED Great Rune (name-matched,
        # kept-scoped). _required_runes() is empty for the region_locks ending and is already clamped
        # to the runes reachable this seed, so every id added here is in a kept region.
        required = set(world._required_runes())
        if required:
            for region in kept:
                for (aid, _flag, name) in REGION_BOSSES.get(region, []):
                    if name in required:
                        ids.add(aid)
        # Defensive last resort: never emit an empty set for a normal seed (would make Goal
        # unsendable). Leyndell is always kept for a base seed, so this only guards the degenerate
        # dlc_only+rolled draw that keeps exclusively a boss-less region.
        if not ids:
            for region in kept:
                ids.update(_region_boss_ids(region))
        return {contract.GOAL_LOCATIONS: sorted(ids)}
