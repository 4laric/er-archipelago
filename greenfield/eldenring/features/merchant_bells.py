"""merchant_bells -- talk to a merchant, and their Bell Bearing is already at the Twin Maidens.

Requested by **boblerrr** on the Nexus mod page, 2026-08-03 (er-archipelago#325): *"Add an option
to receive bell bearings directly from merchants on first interaction."* This is the bell half of
that issue; the equip-load cap half is still a ruling, not a patch.

WHAT IT DOES, AND WHY IT IS NOT WHAT THE REQUEST LITERALLY SAID
--------------------------------------------------------------
Taken literally, "receive the bell bearing" means putting a vanilla Bell Bearing in the bag. Every
one of those bells is ALSO an Archipelago item in this seed's pool (`Nomadic Merchant's Bell
Bearing [1]` is ap id 7001065), so granting one hands the player a second copy of an item the
multiworld is tracking -- a duplicate of a singleton, which is the invariant `shops.py` already
protects Enia's remembrance returns from. What the player actually wants from that item is the
SHOP, so the option delivers the shop and nothing else. The bell stays in the pool, stays worth
finding, and simply arrives already spent.

🛑 THE JOIN THIS FILE'S SIBLING SAID WAS NOT DERIVABLE
-------------------------------------------------------
`features/shops.py` has recorded since Phase 4 that the bell -> shop link "is NOT derivable
matt-free from disk", because the bell-item flags appear NOWHERE in `ShopLineupParam`. That is
true, and it is looking in the wrong file. `tools/datamine_bell_handins.py` found the join in the
Twin Maidens' own talk ESD (`t600001110`), and it is not a param relation at all:

    "Offer a bell bearing"  -> PlayerEquipmentQuantityChange(Goods, 8910 + n)  # consume the item
                            -> SetEventFlag(11109710 + n)                      # the HAND-IN flag
    "Bell Bearing Shop N"   -> AddTalkListDataIf(GetEventFlag(11109710 + n))   # entry appears
                            -> OpenRegularShop(begin, end)                     # the SAME rows

⭐⭐⭐ The range the Maidens open is the merchant's OWN block, not a copy of it -- Kale's talk opens
`100500..100524` and the Maidens' "Kale's Bell Bearing" entry opens `100500..100524`. So a hand-in
releases nothing and duplicates nothing; it adds a MENU ENTRY. That is why the client half is one
event-flag write, and why this feature cannot disturb a single AP location: a shop check is keyed
on its row's `eventFlag_forStock`, and buying at the hub buys the same row.

Cross-checked against `greenfield/esd_gates.tsv`: all 38 emitted ranges appear there as ranges a
MERCHANT's own talk opens (`tests/test_gf_bell_handins.py` recomputes it).

WHERE THE TABLE LIVES, AND WHY NOT HERE
---------------------------------------
`(shop range -> hand-in flag)` is STATIC GAME DATA -- seed-invariant, identical for every apworld,
unchanged by any option -- so it is baked into the client by `tools/gen_merchant_bells.py` rather
than sent. A slot_data key would move `CONTRACT_HASH` to ship a constant. Same argument and same
generator shape as `tools/gen_sweep_boss_names.py`.

THE HANDSHAKE TAG IS REQUIRED HERE (unlike body_tuning's two)
-------------------------------------------------------------
`_contract_hash()` folds CONTRACT and NOT OPTIONS_SUBKEYS, so an older client reports `VERSION: OK`
and then simply never reads this key. `body_tuning.py` argues correctly that a capability OLDER
than every released client must NOT emit a tag -- but this capability is NEW (`merchant_bells.rs`
and `merchant_bell_table.rs` ship in the same window), so the auto_equip precedent applies instead:
a seed with the option ON emits the tag and an unsupporting client REFUSES and says why. An OFF
seed emits nothing and connects to anything.

🛑 KNOWN LIMITS, stated here because a player will meet both
------------------------------------------------------------
1. Twelve bells work the other way round -- they release rows inside the Maidens' own block 1018
   via `eventFlag_forRelease` and have no menu entry and no shop range (the four peddlers, and the
   DLC Herbalist / Mushroom-Seller / Greasemonger / Moldmonger / Igon / Spellmachinist /
   String-Seller). They are absent from the table deliberately: the obvious "match the tranche's
   goods against every shop block" join resolves only 4 of 12 and two of those are coincidence, and
   a wrong merchant would hand the player someone else's shelf.
2. The trigger is the REGULAR BUY MENU (ESD command 22). Ash-of-War, tailoring, upgrading and
   change-of-purpose shops open through commands whose ids nobody has observed yet, so a vendor
   reached only that way does not fire -- the same limit `shop_hints` states.
"""
from Options import Toggle
from ..registry import Feature, register
from .. import contract

# The er-logic client_features.rs SUPPORTED tag. One string, named once: a handshake whose two
# halves disagree about spelling is worse than no handshake.
CLIENT_FEATURE_TAG = "merchant_bells_on_talk"


class MerchantBellsOnTalk(Toggle):
    """Opening a merchant's shop hands their Bell Bearing to the Twin Maiden Husks for you, so
    their wares are on sale at the Roundtable Hold from then on. You are not given the bell itself
    -- it stays in the multiworld as a real item to find -- only the shop it would have unlocked.
    Covers the roving merchants and the named NPC vendors; the peddlers whose bells add stock to
    the Maidens' own shelf are not covered, and neither are Ash-of-War, tailoring or upgrade
    counters. Off by default. A seed with this on requires a client that supports it and will say
    so rather than connect and quietly ignore the setting."""
    display_name = "Merchant Bells on Talk"


@register
class MerchantBellsFeature(Feature):
    name = "merchant_bells"
    OPTIONS = {"merchant_bells_on_talk": MerchantBellsOnTalk}

    def slot_data(self, world):
        # The VALUE is emitted centrally by core._options_echo (contract key
        # options.merchant_bells_on_talk). All this hook owns is the client-feature handshake, and
        # only when the seed actually uses the feature -- an OFF seed emits nothing and connects to
        # any client.
        if not world.options.merchant_bells_on_talk.value:
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
