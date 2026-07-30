"""no_runes_in_shops -- keep this world's own money runes off its merchant checks entirely.

WHY THIS EXISTS (the escape hatch, 2026-07-30)
----------------------------------------------
A shop check whose reward is one of this world's own money runes has repeatedly reached players as
an INVISIBLE row: the generator writes the row correctly (read back 588/588 across a world edge),
yet the purchase menu does not render it, so the check cannot be bought and its reward is stranded.
The leading client-side account -- the menu drops any row whose `value` is at or below the ware's
`sellValue`, which a rune reward hits BY CONSTRUCTION because rune_pricing rolls randint(0, worth)
and a money rune's worth IS its sellValue -- predicted 16/16 on Alaric's seed but is NOT yet
verified in game, and the clamp that follows from it is a CLIENT change. This option is the
world-side escape hatch requested while that lands: if no own rune is ever a shop reward, no shop
check can be hidden by one, whatever the client bug turns out to be.

Deliberately placement (don't PUT runes there), not pricing (don't let the price hide them):
  * a world-side clamp could only touch the prices rune_pricing writes; a slot the roller does not
    price keeps its VANILLA value, and a cheap slot under a big rune (Lord's Rune, sellValue 50000)
    hides just the same. The world does not write those values, so it cannot clamp them;
  * a clamp bakes the unverified root cause into the design, and "always above sellValue" means
    every rune is a guaranteed loss to buy -- rune_pricing gutted to work around a client bug;
  * placement is bug-agnostic: the rune simply sits where no purchase menu mediates it.

WHAT IT DOES (Toggle, OFF by default -- a fresh yaml generates exactly as before):
  * every own-world money rune (the RUNE_PAYOUT-derived set: all 31 catalog runes, DLC included)
    is forbidden as the reward of every purchase-menu check -- scope is SHOP_ROW_FLAGS membership
    (561 rows), the same table shop_sell rewrites and rune_pricing prices. Tags are the wrong
    instrument here: `Shop` covers 527 of those rows and the mechanism covers 561;
  * the rerolled infinite shelves (features/shop_stock) draw from a rune-free pool, and an
    `infinite_hub_wares` pin naming a rune is rejected at options time with an OptionError.

WHAT IT LEAVES ALONE, on purpose:
  * FOREIGN rewards (any other slot's item, ER or not). A foreign reward is never sold natively --
    its slot shows an AP-placeholder spare good, whose sellValue is not a rune payout -- so the
    render trap cannot touch it, and forbidding it would shrink multiworld fill freedom for nothing;
  * the FILLER sentinel ("Rune" is not an ITEM_CATALOG name, so `_client_can_sell` answers False
    and it takes the same placeholder path as a foreign item);
  * runes anywhere else: ground pickups, drops, other worlds' shops. This is "no runes in OUR
    shops", not "no runes".

FILL-SAFETY (a feature owns its own). Money runes are pure filler here -- Great Runes are not money
runes, and `is_rune` anchors on RUNE_PAYOUT, so no progression item is ever forbidden and
fill_restrictive is untouched; only the remaining-fill of filler can feel this rule. The one way it
can hurt is capacity: more own rune items than non-shop slots to hold them. Measured on shipped
data: 744 vanilla money-rune checks (item_shuffle is frozen ON) + the filler-tail reservation,
against ~4300 non-shop locations full-world; the worst small seed (the hub is 185 shop rows out of
221 locations, plus one region) still clears it by hundreds. But the GATE is the model, not the
measurement (features/important_locations is the named precedent): count, and if the pool holds
more own runes than non-shop capacity, SKIP enforcement loudly rather than hand fill an
unsatisfiable constraint.
"""
import warnings

from Options import OptionError, Toggle

from ..registry import Feature, register
from .rune_pricing import is_rune_item

try:
    from ..shop_data import SHOP_ROW_FLAGS
except Exception:  # not yet generated -> no shop scope -> feature can only warn
    SHOP_ROW_FLAGS = {}


class NoRunesInShops(Toggle):
    """Keep your own money runes (Golden/Hero's/Lord's/Numen's and the DLC runes) out of your
    merchants' stock: no shop check's reward is ever one of your own runes, and the rerolled
    infinite shelves never stock one. Escape hatch for rune shop rows failing to show in the
    purchase menu; the runes still exist, just never behind a merchant. Off = no change. Other
    players' items at your shops are unaffected (they display as AP placeholders, which the
    rendering issue cannot hide)."""
    display_name = "No Runes In Shops"


def _skip_reason(rune_count, capacity):
    """The fill-safety gate, as a pure function so a test can call it DIRECTLY both ways (a guard
    the corpus never triggers is untested). None = enforce; a string = skip, saying why."""
    if rune_count > capacity:
        return ("the pool holds %d own money-rune items but only %d non-shop locations could hold "
                "them -- enforcing would make fill unsatisfiable" % (rune_count, capacity))
    return None


@register
class NoRunesInShopsFeature(Feature):
    name = "no_runes_in_shops"
    OPTIONS = {"no_runes_in_shops": NoRunesInShops}

    @staticmethod
    def _on(world):
        opt = getattr(world.options, "no_runes_in_shops", None)
        return bool(opt is not None and int(getattr(opt, "value", 0)))

    def generate_early(self, world):
        # infinite_hub_wares pins a ware onto a shelf BY NAME. A pinned rune would either override
        # this option (a knob that quietly loses to another knob) or be silently dropped (a player
        # asks and nothing says no). Reject at options time, actionably, per CONTRIBUTING.
        if not self._on(world):
            return
        pins = getattr(getattr(world.options, "infinite_hub_wares", None), "value", ()) or ()
        rune_pins = sorted(str(w) for w in pins if is_rune_item(str(w)))
        if rune_pins:
            raise OptionError(
                "no_runes_in_shops is on, but infinite_hub_wares pins %s onto a hub shelf. "
                "Remove the rune pin(s), or turn no_runes_in_shops off."
                % ", ".join(repr(p) for p in rune_pins))

    def set_rules(self, world):
        if not self._on(world):
            return
        if not SHOP_ROW_FLAGS:
            # TOLERANCE REQUIRES TELEMETRY (rune_pricing's rule): an option that is ON and can
            # scope nothing must say so, or "it did nothing" is indistinguishable from "it worked".
            warnings.warn(
                "no_runes_in_shops is ON but shop_data.SHOP_ROW_FLAGS is empty -- this tree needs "
                "a -Greenfield regen. The option scoped no shop checks and did nothing.",
                RuntimeWarning)
            return
        player = world.player
        shop_locs = []
        capacity = 0
        for loc in world.multiworld.get_locations(player):
            aid = getattr(loc, "address", None)
            if aid is None:
                continue                      # events are not checks
            if str(aid) in SHOP_ROW_FLAGS:
                shop_locs.append(loc)
            elif loc.item is None:
                capacity += 1                 # a non-shop slot a rune could still land on
        runes = sum(1 for i in world.multiworld.itempool
                    if i.player == player and is_rune_item(i.name))
        reason = _skip_reason(runes, capacity)
        if reason is not None:
            import logging
            logging.getLogger("Greenfield").warning(
                "[eldenring:%s] no_runes_in_shops: SKIPPING enforcement -- %s. The seed still "
                "generates; rune rewards may appear at merchants this seed.", player, reason)
            return
        for loc in shop_locs:
            prev = loc.item_rule
            loc.item_rule = (lambda item, pv=prev:
                             pv(item) and not (item.player == player and is_rune_item(item.name)))
