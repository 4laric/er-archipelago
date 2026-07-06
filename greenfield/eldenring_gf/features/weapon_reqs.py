"""no_weapon_requirements -- make any received gear usable on any build (matt-free).

The shared runtime client already implements this: no_weapon_reqs.rs reads the slot_data bool
'no_weapon_requirements' and zeroes the live-param stat requirements (weapon proper_str/dex/mag/fai/
arc + spell requirement_int/fai/luck), re-applied each launch, only ever lowering. Greenfield just
emits the bool -- no client change. Off by default (no-change); the flagship playtest yaml turns it on.
"""
from Options import Toggle
from ..registry import Feature, register
from .. import contract


class NoWeaponRequirements(Toggle):
    """Remove the stat requirements on weapons, shields, and catalysts (and spell requirements) so
    anything the multiworld hands you is usable regardless of your build. Off by default; the client
    zeroes the live params at runtime (only ever lowers requirements, so it is reconnect-safe)."""
    display_name = "No Weapon Requirements"


@register
class WeaponReqsFeature(Feature):
    name = "weapon_reqs"
    OPTIONS = {"no_weapon_requirements": NoWeaponRequirements}

    def slot_data(self, world):
        return {contract.NO_WEAPON_REQUIREMENTS: bool(world.options.no_weapon_requirements.value)}
