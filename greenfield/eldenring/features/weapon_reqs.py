"""no_weapon_requirements -- make any received gear usable on any build (matt-free).

The shared runtime client already implements this: no_weapon_reqs.rs reads the slot_data bool
'no_weapon_requirements' and zeroes the live-param stat requirements (weapon proper_str/dex/mag/fai/
arc + spell requirement_int/fai/luck), re-applied each launch, only ever lowering. Greenfield just
emits the bool -- no client change.

ON by default, and that default is LOAD-BEARING. This option was frozen at 1 in defaults.FROZEN_OPTIONS
from the v0.2 slim until 2026-08-13, so "requirements removed" is what every seed ever rolled has
done. Unfreezing it at the bare `Toggle` default of 0 would have reversed that for everyone who does
not name the option -- see the comment on `default` below.
"""
from Options import Toggle
from ..registry import Feature, register
from .. import contract


class NoWeaponRequirements(Toggle):
    """Lets you use any weapon, shield, catalyst or spell whatever your stats are.

    It removes the stat requirements, so gear the multiworld sends you works on any build.
    On by default, since a randomizer hands you gear no build was made for. Turn it off to
    bring requirements back and let your stats decide what you can hold; the seed is
    generated the same either way, so nothing becomes unwinnable.
    """
    display_name = "No Weapon Requirements"
    # 🛑 1, NOT the bare Toggle 0. This option was FROZEN AT 1 until 2026-08-13; the freeze value IS
    # the default, and a class default that disagrees with it silently reverts every seed that does
    # not name the option the moment the freeze lifts. That is not hypothetical -- it is what the
    # PoolBuilderIntensity unfreeze did inside a release whose changelog said nothing had changed.
    # Pinned by test_gf_weapon_reqs.test_the_unfrozen_default_matches_the_freeze_value.
    default = 1


@register
class WeaponReqsFeature(Feature):
    name = "weapon_reqs"
    OPTIONS = {"no_weapon_requirements": NoWeaponRequirements}

    def slot_data(self, world):
        return {contract.NO_WEAPON_REQUIREMENTS: bool(world.options.no_weapon_requirements.value)}
