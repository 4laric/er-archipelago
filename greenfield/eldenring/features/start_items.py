"""SPEC-PARITY Phase 7 -- starting items (COMPLETE).

Grants starting items the client hands the player at game start. TWO wire paths:

  startItems -- list of FullIDs the client's grant path adds once, settle-gated. For REPEATABLE /
      capacity grants where a duplicate is harmless (Torch, pot vessels: a second torch or cracked
      pot is just inventory).
  uniqueStartGrants -- list of [FullID, obtainedFlag] pairs for UNIQUE key items whose possession
      the game tracks via a vanilla obtained-flag. The client grants the goods ONLY if the flag is
      unset, then sets the flag with the grant -- so the flag is the single source of truth for
      "has it" and a re-run (reload / reconnect / reset) can never double-grant. It also stops the
      redundant double when the item is ALSO a randomized check whose pool copy the player finds
      (the pool receive path sets the same obtained-flag: client keyitems.rs / flag poll).

Matt-free (single vanilla item ids, no derivation):

  Torch -- WEAPON param id 24000000; FullID = 24000000 | WEAPON_NIBBLE(0x00000000) = 24000000. So dark
      caves/catacombs are navigable before you reach a grace. (repeatable path)
  Spectral Steed Whistle -- GOODS id 130; FullID = 130 | GOODS_NIBBLE(0x40000000) = 1073741954 (the
      client RE'd Torrent = 0x40000000 | 130). In the shattered/region-lock game Melina's mount
      hand-off is bypassed (rolled/num_regions starts), so grant the whistle directly so the player
      can summon Torrent and traverse. On by default. (UNIQUE path, obtained-flag 60100)
  Spirit Calling Bell -- GOODS id 8158; FullID = 0x40000000 | 8158 = 1073749982 (item_ids.py
      'Spirit Calling Bell'). Renna's hand-off is as bypassable as Melina's on a shattered start,
      and without the bell every found summoning ash is inert. On by default.
      (UNIQUE path, obtained-flag 60110 -- the enable/obtained flag the game gates spirit
      summoning on; same flag the Limgrave check 7770012 detects and client keyitems.rs sets when
      the pool copy is received. See memory er-spirit-bell-flag.)
  Flask of Wondrous Physick -- GOODS id 250; FullID = 0x40000000 | 250 = 1073742074 (item_ids.py).
      On by default. (UNIQUE path, obtained-flag 60020 -- the acquisition flag the Limgrave check
      7770011 detects. ⚠ UNVERIFIED IN-GAME: the client's flag-poll baseline work
      (er-logic flagpoll_baseline_replay.rs) lists 60020 among the flags that read SET on a FRESH
      save; if that is right, the unique grant SKIPS on a fresh save and this option is inert until
      confirmed/re-keyed. Alaric: in-game confirm which way 60020 reads at spawn.)
"""
from Options import DefaultOnToggle
from ..registry import Feature, register
from .. import contract

# ER Lantern: GOODS id 2070 (item_ids.py 1073743894 = 0x40000000 | 2070); FullID below. Replaces the
# old start Torch (WEAPON 24000000): the Lantern lights caves/catacombs HANDS-FREE (equipped in a
# pouch slot, no weapon slot burned), so it's the strictly better opening light source.
_LANTERN_FULL_ID = 0x40000000 | 2070
# Whetstone Knife: GOODS id 8590 (item_ids.py 1073750414 = 0x40000000 | 8590); obtained/acquisition
# flag 60130 (data.py check for the Gatefront Ruins pickup, AP 7000026, m60_42_37). Granted as a
# UNIQUE (flagged) start item -- same shape as the steed/bell/physick below -- so Ashes of War /
# weapon skills work from the opening (the Gatefront hand-off is bypassed on region-lock starts).
# Setting 60130 as the idempotency latch also collects that vanilla location, exactly like the other
# uniques collect theirs.
_WHETSTONE_KNIFE_FULL_ID = 0x40000000 | 8590
_WHETSTONE_KNIFE_FLAG = 60130
# Spectral Steed Whistle: GOODS id 130; FullID = id | GOODS_NIBBLE(0x40000000) = 1073741954.
_STEED_WHISTLE_FULL_ID = 0x40000000 | 130
# 60100 = the Spectral Steed Whistle OBTAINED-flag. In vanilla, MELINA's mount hand-off sets it, and
# the game gates Torrent summoning on it -- the whistle GOODS is INERT without it (verified in-game,
# er-torrent-regionlock-mountless). Set as part of the unique grant, NOT unconditionally: the flag
# doubles as the idempotency latch ("already has it -> skip").
_STEED_WHISTLE_FLAG = 60100
# Spirit Calling Bell: GOODS id 8158 (item_ids.py 1073749982 = 0x40000000 | 8158); obtained-flag
# 60110 (data.py check 7770012 'Limgrave :: Spirit Calling Bell [f60110]'; client keyitems.rs
# COMPANION_ACQUIRE_FLAGS).
_SPIRIT_BELL_FULL_ID = 0x40000000 | 8158
_SPIRIT_BELL_FLAG = 60110
# Flask of Wondrous Physick: GOODS id 250 (item_ids.py 1073742074 = 0x40000000 | 250); acquisition
# flag 60020 (data.py check 7770011). ⚠ fresh-save default-set per the client's flag-poll baseline
# pin -- see module docstring; in-game confirm pending.
_WONDROUS_PHYSICK_FULL_ID = 0x40000000 | 250
_WONDROUS_PHYSICK_FLAG = 60020
# Starting flasks (prior in-game-verified goods ids): Flask of Crimson Tears = GOODS 1001, Flask of
# Cerulean Tears = GOODS 1051; FullID = id | GOODS_NIBBLE.
# NOT folded into uniqueStartGrants (yet): Crimson's acquisition flag is 60000, but Cerulean's flag
# could not be confirmed from params/repo ground truth (60010 is the obvious pattern guess -- and an
# invented id silently no-ops, CONTRIBUTING "no invented IDs"), and 60000 itself is pinned as
# fresh-save default-set (client flagpoll_baseline_replay.rs). So the flasks stay on the plain
# repeated path until both flags are param/in-game verified.
_CRIMSON_FLASK_FULL_ID = 0x40000000 | 1001
_CERULEAN_FLASK_FULL_ID = 0x40000000 | 1051
# Pot vessels: Cracked Pot = GOODS 9500, Ritual Pot = GOODS 9501. Held throwing-pot capacity == your
# Cracked Pot count (Ritual Pots for ritual-type pots, e.g. Rancor Pot). Without vessels a granted pot
# (curated_filler stack OR an item_shuffle vanilla pot) overflows straight to STORAGE and can't be
# thrown. The client grants startItems one-per-list-entry (grant_full_id(id,1), index-tracked), so we
# just repeat the FullID N times. Additive -- shuffled vessels stay in the pool as bonus capacity.
_CRACKED_POT_FULL_ID = 0x40000000 | 9500
_RITUAL_POT_FULL_ID = 0x40000000 | 9501
_START_CRACKED_POTS = 10   # throwing-pot capacity at spawn (Alaric playtest)
_START_RITUAL_POTS = 4     # ritual-pot capacity (Rancor Pot etc.)
# Perfume Bottle = GOODS 9510: the vessel that holds the DLC perfume/spraymist/aromatic consumables the
# curated_filler 'perfumes' category hands out (same vessel role Cracked Pot plays for thrown pots).
_PERFUME_BOTTLE_FULL_ID = 0x40000000 | 9510
_START_PERFUME_BOTTLES = 10
# Hefty Cracked Pot = GOODS 2009500 (DLC): the larger vessel for the DLC 'Hefty ...' throwing pots.
_HEFTY_CRACKED_POT_FULL_ID = 0x40000000 | 2009500
_START_HEFTY_CRACKED_POTS = 10


class StartWithLantern(DefaultOnToggle):
    """Start with a Lantern so dark caves and catacombs are navigable before you reach a grace --
    hands-free (pouch slot), unlike the Torch it replaces. On by default; turn off for a stricter
    start."""
    display_name = "Start With Lantern"


class StartWithWhetstone(DefaultOnToggle):
    """Start with the Whetstone Knife so Ashes of War / weapon skills work from the opening (the
    Gatefront Ruins hand-off is bypassed on region-lock starts). On by default. Granted only if you
    don't already have it (obtained-flag 60130)."""
    display_name = "Start With Whetstone Knife"


class StartWithSteed(DefaultOnToggle):
    """Start with the Spectral Steed Whistle so you can summon Torrent and traverse the shattered
    world (Melina's mount hand-off is bypassed on region-lock starts). On by default. Granted
    only if you don't already have it (obtained-flag 60100)."""
    display_name = "Start With Spectral Steed Whistle"


class StartWithBell(DefaultOnToggle):
    """Start with the Spirit Calling Bell so spirit-ash summons work from the opening (Renna's
    hand-off is bypassed on region-lock starts). On by default. Granted only if you don't
    already have it (obtained-flag 60110)."""
    display_name = "Start With Spirit Calling Bell"


class StartWithPhysick(DefaultOnToggle):
    """Start with the Flask of Wondrous Physick so mixed-tear physicks work from the opening.
    On by default. Granted only if you don't already have it (obtained-flag 60020)."""
    display_name = "Start With Flask of Wondrous Physick"


class StartWithFlasks(DefaultOnToggle):
    """Start with the Flask of Crimson Tears (HP) and Flask of Cerulean Tears (FP) so you can heal
    and cast from the opening. On by default."""
    display_name = "Start With Flasks"


@register
class StartItems(Feature):
    name = "start_items"
    OPTIONS = {"start_with_lantern": StartWithLantern, "start_with_steed": StartWithSteed,
               "start_with_bell": StartWithBell, "start_with_physick": StartWithPhysick,
               "start_with_flasks": StartWithFlasks, "start_with_whetstone": StartWithWhetstone}

    def slot_data(self, world):
        items = []
        if world.options.start_with_lantern.value:
            items.append(_LANTERN_FULL_ID)
        if world.options.start_with_flasks.value:
            items.append(_CRIMSON_FLASK_FULL_ID)
            items.append(_CERULEAN_FLASK_FULL_ID)
        _shuf = getattr(world.options, "item_shuffle", None)
        if _shuf is not None and _shuf.value:
            items += [_CRACKED_POT_FULL_ID] * _START_CRACKED_POTS
            items += [_RITUAL_POT_FULL_ID] * _START_RITUAL_POTS
            items += [_PERFUME_BOTTLE_FULL_ID] * _START_PERFUME_BOTTLES
            if getattr(world, "gf_dlc_on", False):
                items += [_HEFTY_CRACKED_POT_FULL_ID] * _START_HEFTY_CRACKED_POTS
        # UNIQUE start grants: [FullID, obtainedFlag] pairs. The client grants the goods ONLY if
        # the flag is unset, then sets the flag with the grant (er-logic unique_grant_action) --
        # idempotent across reload/reconnect/pool-pickup by construction. These FullIDs must NOT
        # also appear in the plain startItems list (that path is unconditional and would double).
        uniques = []
        if world.options.start_with_steed.value:
            uniques.append([_STEED_WHISTLE_FULL_ID, _STEED_WHISTLE_FLAG])
        if world.options.start_with_bell.value:
            uniques.append([_SPIRIT_BELL_FULL_ID, _SPIRIT_BELL_FLAG])
        if world.options.start_with_physick.value:
            uniques.append([_WONDROUS_PHYSICK_FULL_ID, _WONDROUS_PHYSICK_FLAG])
        if world.options.start_with_whetstone.value:
            uniques.append([_WHETSTONE_KNIFE_FULL_ID, _WHETSTONE_KNIFE_FLAG])
        return {contract.START_ITEMS: items, contract.UNIQUE_START_GRANTS: uniques}
