"""Track D -- checkItemFlags (arms the client's vanilla-item suppressor).

Purpose (matt-free): for every greenfield CHECK location that vanilla-holds a known item, tell the
client "an AddItem of THIS raw item id belongs to a check location; suppress the vanilla bag-add so
the single copy is delivered by the AP grant instead of the world pickup." Without this table the
client logs `vanilla suppressor INERT: checkItemFlags empty/absent in slot_data` and every vanilla
ware leaks alongside the AP-placed item.

Client contract (detour.rs, LIVE 2026-07-01):
  static CHECK_ITEM_FLAGS: Mutex<Option<HashMap<u32, Vec<u32>>>>
  fn check_item_flags_lookup(raw_id: u32) -> Option<Vec<u32>>       # detour.rs:65
  configure_check_item_flags(map)                                   # detour.rs:47
  core.rs:369 parses slot_data["checkItemFlags"] as { str(u32): [u32, ...] }.
The detour reads `raw_id` from ITEMBUF_ENTRY_ID_OFF (detour.rs:237) -- the full AddItemFunc-space
item id, i.e. the ER FullID (category nibble | equipId; e.g. Traveler's Clothes 0x100f90c4). That is
EXACTLY the id space of ITEM_CATALOG values (gen_data.py ORs the category nibble in), so the key is
ITEM_CATALOG[LOCATION_ITEM[ap_id]] with no further transform. Shape: { str(FullID): [flag, ...] }.

Value = the acquisition/event flags of the check location(s) that vanilla-hold that raw id. Because
one vanilla raw id can back many checks (e.g. a Cracked Pot appears at 16 locations), flags are
MERGED into a list per FullID. The client's er_logic::vanilla_suppress::should_suppress(&flags,
collected) suppresses until EVERY mapped flag is collected, then passes (a genuine farm re-pickup) --
so merging (not first-wins) is required for correctness on shared-id wares.

matt-free derivation: keys come from greenfield's own generated ITEM_CATALOG / LOCATION_ITEM (FMG
name export) and the flags from data.py LOCATIONS -- never a matt name or matt-authored id map.

Only unambiguous entries are emitted: a location is included only if its vanilla item name resolves
in ITEM_CATALOG (LOCATION_ITEM[ap_id] in ITEM_CATALOG). Unresolved locations (name gaps / Rune
filler) are skipped -- they have no vanilla ware to suppress.
"""
from collections import defaultdict

from ..registry import Feature, register
from .. import contract
from ..data import HUB, LOCATIONS

try:
    from ..data import GESTURE_AWARD_FLAGS   # detect-only gesture pickups (EMEVD AwardGesture)
except ImportError:                           # pre-regen data
    GESTURE_AWARD_FLAGS = {}

try:
    from ..item_ids import ITEM_CATALOG, LOCATION_ITEM
except Exception:  # not yet generated
    ITEM_CATALOG, LOCATION_ITEM = {}, {}

try:
    from ..repeatable_goods import REPEATABLE_GOODS
except Exception:  # not yet generated -> old (over-broad) behaviour
    REPEATABLE_GOODS = frozenset()

_GOODS_CATEGORY = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF


@register
class CheckItemFlags(Feature):
    name = "check_item_flags"

    def slot_data(self, world):
        # Scope to the same locations the base contract exposes: hub + kept spokes. A check that isn't
        # in play this seed shouldn't arm suppression for its ware.
        scope = [HUB] + list(world._kept())
        by_full = defaultdict(set)
        for region in scope:
            for (_name, ap_id, flag) in LOCATIONS.get(region, []):
                # DETECT-ONLY gesture pickups: their ware is awarded by EMEVD AwardGesture, which
                # the AddItemFunc detour never sees, so arming an id here could only ever eat a
                # LEGITIMATE grant, never the vanilla award. gen_data already keeps their wares out
                # of LOCATION_ITEM (so vanilla_name is None today); this guard is the EXPLICIT
                # statement of that rule, so a future catalog change cannot silently re-arm them.
                if int(flag) in GESTURE_AWARD_FLAGS:
                    continue
                vanilla_name = LOCATION_ITEM.get(ap_id)
                if vanilla_name is None:
                    continue
                full_id = ITEM_CATALOG.get(vanilla_name)
                if full_id is None:
                    continue  # unresolved -> nothing unambiguous to suppress
                full_id = int(full_id)
                # DO NOT arm suppression for a ware you can ALSO farm / mine / buy / craft.
                # The client suppresses by ITEM ID -- detour.rs only ever sees `raw_id` off the
                # AddItemFunc buffer and cannot tell where the item came from. So arming a ware that
                # has a repeatable source eats it from EVERY source: Golden Rune [1] backs 46 checks,
                # so every Golden Rune [1] you pick up anywhere is eaten until all 46 are collected.
                # Mine an ore node -> get a Smithing Stone -> that stone is some check's ware -> eaten.
                # (Alaric, playtest 2026-07-11: "the stones in tunnels ... today they're just
                # suppressed". It was also silently eating 83% of the rerolled enemy drops.)
                #
                # Not arming it costs a DOUBLE-DIP at that one check: you get the vanilla ware as well
                # as the AP item -- on an item you could have farmed anyway. Strictly the lesser evil.
                # Suppression stays fully strong for the 446 wares obtainable ONLY as a check, which is
                # the case that actually matters (a unique ware cannot leak).
                if (full_id & ~_ROW_ID_MASK) == _GOODS_CATEGORY \
                        and (full_id & _ROW_ID_MASK) in REPEATABLE_GOODS:
                    continue
                by_full[full_id].add(int(flag))
        # str(FullID) -> sorted [flag, ...]; matches core.rs:369 (k.parse::<u32>, v.as_array of u32).
        check_item_flags = {str(full): sorted(flags) for full, flags in by_full.items()}
        return {contract.CHECK_ITEM_FLAGS: check_item_flags}
