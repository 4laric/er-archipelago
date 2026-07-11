"""SPEC-PARITY Phase 7 -- starting items (COMPLETE).

Grants starting items the client hands the player at game start (startItems = list of FullIDs the
client's grant path adds once, settle-gated). Matt-free (single vanilla item ids, no derivation):

  Torch -- WEAPON param id 24000000; FullID = 24000000 | WEAPON_NIBBLE(0x00000000) = 24000000. So dark
      caves/catacombs are navigable before you reach a grace.
  Spectral Steed Whistle -- GOODS id 130; FullID = 130 | GOODS_NIBBLE(0x40000000) = 1073741954 (the
      client RE'd Torrent = 0x40000000 | 130). In the shattered/region-lock game Melina's mount
      hand-off is bypassed (rolled/num_regions starts), so grant the whistle directly so the player
      can summon Torrent and traverse. On by default.
"""
from Options import DefaultOnToggle
from ..registry import Feature, register
from .. import contract

# ER Torch: WEAPON param id 24000000; FullID = id | WEAPON_NIBBLE(0x00000000) = 24000000.
_TORCH_FULL_ID = 24000000
# Spectral Steed Whistle: GOODS id 130; FullID = id | GOODS_NIBBLE(0x40000000) = 1073741954.
_STEED_WHISTLE_FULL_ID = 0x40000000 | 130
# Starting flasks (prior in-game-verified goods ids): Flask of Crimson Tears = GOODS 1001, Flask of
# Cerulean Tears = GOODS 1051; FullID = id | GOODS_NIBBLE.
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


class StartWithTorch(DefaultOnToggle):
    """Start with a Torch so dark caves and catacombs are navigable before you reach a grace.
    On by default; turn off for a stricter start."""
    display_name = "Start With Torch"


class StartWithSteed(DefaultOnToggle):
    """Start with the Spectral Steed Whistle so you can summon Torrent and traverse the shattered
    world (Melina's mount hand-off is bypassed on region-lock starts). On by default."""
    display_name = "Start With Spectral Steed Whistle"


class StartWithFlasks(DefaultOnToggle):
    """Start with the Flask of Crimson Tears (HP) and Flask of Cerulean Tears (FP) so you can heal
    and cast from the opening. On by default."""
    display_name = "Start With Flasks"


@register
class StartItems(Feature):
    name = "start_items"
    OPTIONS = {"start_with_torch": StartWithTorch, "start_with_steed": StartWithSteed,
               "start_with_flasks": StartWithFlasks}

    def slot_data(self, world):
        items = []
        if world.options.start_with_torch.value:
            items.append(_TORCH_FULL_ID)
        if world.options.start_with_steed.value:
            items.append(_STEED_WHISTLE_FULL_ID)
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
        return {contract.START_ITEMS: items}
