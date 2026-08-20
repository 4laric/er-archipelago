"""Leyndell great-rune gate (opt-in-by-default) -- the capital sits behind >=N Great Runes.

Region-spine v2: Leyndell is a first-class GOAL region again (m11 Royal + Ashen fold + m19 Fractured
Marika). This gate adds a LOGIC access rule to its checks: >=N Great Runes (any of the game's Great
Runes) IN ADDITION to the Leyndell Lock, mirroring the vanilla "two great runes to enter the
capital". The m35 Shunning-Grounds rode this gate while it was folded into Altus; it is the SEWER
region now, gated by its own Lock and not by runes.

Winnability by construction: the N runes that satisfy the gate are marked PROGRESSION (core._class_for
reads world.gf_leyndell_runes), so AP fill guarantees N Great Runes are reachable and -- because the
Leyndell checks require them -- places them OUTSIDE Leyndell.

🛑 N IS FLOORED, NOT CLAMPED, AND THE FLOOR IS VANILLA'S (2026-08-01, issue from a player report).
The old code did `want = min(want, len(available))` on the theory that lowering the requirement is
always safe. It is not: OUR N is data-driven, but the game's capital gate is a FIXED
VANILLA_CAPITAL_GATE_RUNES=2 possession wall that does not clamp with us, and while the wall is
ARMED features/graces.py WITHHOLDS the capital grace bundle -- so the physical gate is the only way
in. At N=1 logic believes one rune opens Leyndell, the game still wants two, and fill may place a
region Lock behind a door the player cannot open. Two ways to land there: num_regions (default 6)
keeping exactly one Great-Rune region, or the player simply setting `leyndell_runes_required: 1`.

So an ARMED wall requires at least the vanilla constant. 🛑 AND WHEN THE POOL CANNOT SUPPLY THAT
MANY, WE TOP THE POOL UP -- we do not disarm (2026-08-12, #589). Disarming was the original answer
and it was wrong in the worst direction: disarming OUR wall does not disarm the GAME'S. The capital
gate is still a fixed two-rune possession wall and the fogwall is still the only way in, so a
one-rune seed sealed Leyndell, the Sewer and Ashen Capital behind a door nothing could open -- an
unwinnable run, with other players' items stranded inside it (LordChungle, seed
26505919849221796677: 42 of them). The pool is ours to write, so generate_early injects the missing
runes deterministically through create_items and arms at the floor.

Disarm survives only where it means something: `leyndell_runes_required: 0` (the player asked for no
gate), item_shuffle off, or a sealed goal region. Each of those now says so in the generation log --
silence about the wall's state is most of what made the defect expensive.

Option `leyndell_runes_required` (Range 0..6, default 2). 0 -> no gate (and world.gf_leyndell_runes is
empty, so nothing is marked progression and default fill is unchanged). Base-game only: under DLC Only
the goal region (Leyndell) is sealed, so the gate auto-skips. In-game the wall needs no client half at
all (gated-children fix, 2026-07-14): the capital's grace bundle is WITHHELD (features/graces.py), so
the only way in is the game's own main gate, which opens when the player holds N Great Runes -- the
runes arrive as AP items and the client's key-item grant makes the game count them. This gate's job
is the LOGIC mirror: mark N runes progression and require them on Leyndell's entrance + checks so
fill never strands progression past a wall it can't prove open.
"""
import logging

from Options import OptionError, Range

from ..registry import Feature, register

_log = logging.getLogger("Elden Ring")

try:
    from ..region_spine import GOAL_REGION
except Exception:  # pragma: no cover
    GOAL_REGION = "Altus Plateau"
try:
    from ..data import LOCATIONS
except Exception:
    LOCATIONS = {}
try:
    from ..item_ids import ITEM_CATALOG
    from .. import item_categories as _ic
except Exception:  # pre-regen / standalone import
    ITEM_CATALOG = {}

    class _ic:  # type: ignore[no-redef]  # no catalog -> no runes
        GREAT_RUNES: list = []

# Great Rune item names (matt-free: read from the greenfield catalog, same rule as core.GREAT_RUNES).
# SEVEN, from the one definition in item_categories -- see its GREAT_RUNE_GOODS_IDS block.
GREAT_RUNES = list(_ic.GREAT_RUNES)
# The VANILLA capital main gate is a fixed two-Great-Rune possession wall. It is not ours and it does
# not scale with our options, so it is the FLOOR on any armed rune wall (see the module docstring).
VANILLA_CAPITAL_GATE_RUNES = 2

# ⭐ ALL SEVEN COUNT AT THE GATE -- and the claim that they do not was never sourced.
#
# `test_the_unborn_rune_is_never_injected` asserted, with no citation, that "Great Rune of the
# Unborn is not a capital-gate rune; the game does not count it toward its two", and this file
# briefly grew a `CAPITAL_COUNTABLE_RUNES` exclusion on the strength of it (2026-08-16). Alaric:
# *"what vanilla gate doesn't count Unborn? i believe they all do"* -- and the data agrees with him:
#
#     common.emevd $Event(6905) "救済対応_伍 / Relief response_5" maps every remembrance flag to a
#     CONTIGUOUS held-rune slot -- 510010->171, 510300->172, 510040->173, 510220->174, 510120->175,
#     510200->176, and 197->177. SEVEN slots, one per Great Rune, the Unborn rune among them.
#
# A game that did not count it would not give it a slot in that block. Nothing in the 589-file EMEVD
# corpus READS 171-177, so the gate's actual count is engine-side and not decidable from here -- but
# an uncited exclusion is the wrong way to resolve that, and shipping one would have removed a rune
# the player legitimately holds from the wall it legitimately opens.
#
# So: no exclusion. If the engine ever proves otherwise, the fix is a cited constant, not a docstring.

# Capital map prefixes: m11 = Leyndell Royal + Ashen Capital, m19 = Fractured Marika / final
# arena. The acquisition flag encodes the map (mAA -> AA......), so an m11/m19 flag in the goal
# region is a capital check. Restricting to GOAL_REGION keeps HUB-overridden m11_10 Roundtable
# checks out (they region to the hub). m35 left this list with the Sewer split (v2); 510250
# (Mohg the Omen) left with it.
_LEYNDELL_PREFIXES = ("11", "19")
_LEYNDELL_EXTRA_FLAGS = frozenset({173, 510040, 60520})  # Morgott GR + Rem. Omen King, Godfrey pouch
# Gating items forbidden on Leyndell-gated locs = Great Runes (the gate's own prerequisite) PLUS the
# folded-dungeon legacy keys (Academy Glintstone Key, Hole-Laden Necklace) -- keeping a key off a
# rune-gated capital check breaks the Metyr<->Leyndell cross-gate cycle (FillError 2026-07-10).
_LEGACY_KEY_NAMES = frozenset({"Academy Glintstone Key", "Hole-Laden Necklace"})
_GATING_ITEMS = frozenset(GREAT_RUNES) | _LEGACY_KEY_NAMES


def _gated_region_names(world):
    """Every region physically behind the 'To <GOAL_REGION>' edge, DERIVED from the live region
    graph: the goal region plus everything reachable through its exits, without this list needing
    to know future child names. Sewer left this subtree in #842 because its own Lock now grants an
    independent m35 warp entrance; the Ashen Capital left earlier when finale.py hung it off the
    hub. A location still in this subtree sits behind the rune wall, so a gating item placed there
    can deadlock the very gate it opens. Empty when the goal region is sealed this seed (dlc_only)."""
    try:
        start = world.multiworld.get_region(GOAL_REGION, world.player)
    except KeyError:
        return frozenset()
    seen = {GOAL_REGION}
    stack = [start]
    while stack:
        for exit_ in stack.pop().exits:
            dst = getattr(exit_, "connected_region", None)
            if dst is not None and dst.name not in seen:
                seen.add(dst.name)
                stack.append(dst)
    return frozenset(seen)


def _leyndell_location_ids():
    out = set()
    for reg, locs in LOCATIONS.items():
        if reg != GOAL_REGION:
            continue
        for (_name, ap_id, flag) in locs:
            if str(flag)[:2] in _LEYNDELL_PREFIXES or int(flag) in _LEYNDELL_EXTRA_FLAGS:
                out.add(ap_id)
    return out

def _vanilla_placement_on(world) -> bool:
    """Is every item pinned to its base-game location this seed?

    Read off the OPTION, not off `world.gf_vanilla_pins`: the pins are published later in the
    pipeline and this runs in `generate_early`, so keying on them silently reads empty and the wall
    arms anyway. (That is not hypothetical -- it is how the first attempt at #769 failed, and it
    failed QUIETLY, which is the whole reason this note is here.)
    """
    opt = getattr(getattr(world, "options", None), "vanilla_placement", None)
    return bool(opt is not None and opt.value)

class LeyndellRunesRequired(Range):
    """Great Runes needed to access Leyndell (m11 Royal/Ashen + Fractured Marika), on top of the
    Leyndell Lock. 0 disables the gate.

    Values 1..2 all mean 2: the vanilla capital gate is a fixed two-rune wall, so a gate weaker than
    vanilla cannot be expressed -- asking for one arms at 2. If this seed's regions hold fewer than
    two Great Runes, the missing ones are added to the item pool rather than the gate being dropped:
    the game's own two-rune wall does not go away when ours does, so dropping it would seal the
    capital instead of opening it. Never clamped DOWN to an armed value below 2."""
    display_name = "Leyndell Great Runes Required"
    range_start = 0
    range_end = 6
    default = 2


@register
class LeyndellGate(Feature):
    name = "leyndell_gate"
    OPTIONS = {"leyndell_runes_required": LeyndellRunesRequired}

    def generate_early(self, world) -> None:
        # Pick the concrete runes that satisfy the gate (floored at vanilla's 2; the pool is topped
        # up when it cannot supply that many -- see #589); core marks these progression so fill
        # guarantees them reachable OUTSIDE Leyndell. Empty -> gate off, bundle rides the Lock.
        world.gf_leyndell_runes = []
        opt = getattr(world.options, "leyndell_runes_required", None)
        want = int(opt.value) if opt is not None else 0
        # Every exit from here says which state the wall is in. #589's defect was silent in the
        # generation log AND in game, and the silence is most of what made it expensive -- a host
        # reading the output had no way to know the capital had no wall on it.
        if want <= 0 or not GREAT_RUNES:
            if GREAT_RUNES:
                _log.info("leyndell_gate: leyndell_runes_required is 0 -- no rune wall; the capital "
                          "grace bundle rides the Leyndell Lock.")
            return
        if not (getattr(world.options, "item_shuffle", None) and world.options.item_shuffle.value):
            # runes only enter the pool when vanilla items are shuffled
            _log.info("leyndell_gate: item_shuffle is off, so no Great Runes enter the pool -- no "
                      "rune wall; the capital grace bundle rides the Leyndell Lock.")
            return
        # 🛑 VANILLA PLACEMENT DISARMS THIS WALL, and it is the mode's own promise (#769).
        # `VanillaPlacement`'s docstring: "Progression is gated the way the base game gates it, so
        # the region locks are not used at all ... and the Leyndell wall, the Rold Medallion and
        # every other door work as they always did." Our synthetic wall is not "the Leyndell wall" --
        # the GAME's fixed two-rune gate is, and it is still there. Arming ours on top asks for runes
        # we chose on a map where we did not choose where anything is.
        #
        # ⭐ WHAT IT ACTUALLY COST, measured: seed 60255596019398880819 armed on
        # ["Godrick's Great Rune", "Morgott's Great Rune"] -- and Morgott drops HIS rune INSIDE
        # Leyndell, so the capital gated on a key kept behind it. `can_beat_game()` False, and
        # test_gf_vanilla_placement red with the whole of Leyndell and the Ashen Capital unreachable.
        #
        # ⭐ THE SELF-GATE IS OLD; ONLY ITS VISIBILITY IS NEW. Selection used to be
        # `sorted(avail)[:want]` and Morgott's is FIFTH of seven alphabetically -- a two-rune wall
        # could never reach him. #640 replaced the prefix with a seeded sample, correctly, and the
        # sample can draw him. Fixing a real defect exposed a latent one; #640 is not the mistake.
        #
        # 🛑 DISARMING THIS WALL IS NORMALLY A SOFTLOCK (#589) -- our wall is what stops fill putting
        # something needed behind the game's fixed 2-rune gate. That argument does not reach here:
        # under vanilla_placement fill puts every item exactly where the base game puts it, and the
        # base game is winnable. The hazard is about FILL's freedom, and this mode has none.
        if _vanilla_placement_on(world):
            _log.info("leyndell_gate: vanilla_placement is on, so the base game's own two-rune "
                      "capital gate is the wall -- ours would arm on runes we did not place "
                      "(#769). No synthetic rune wall; the capital grace bundle rides the "
                      "Leyndell Lock.")
            return
        if GOAL_REGION not in world._kept():
            _log.info("leyndell_gate: %s is not kept this seed (DLC Only or a sealed goal region) "
                      "-- no capital to gate.", GOAL_REGION)
            return  # DLC Only / sealed goal region -> no Leyndell to gate
        # FLOOR, not clamp. The vanilla wall is fixed at 2 and the capital bundle is withheld while
        # ours is armed, so an armed wall must be at least as strict as the game's.
        want = max(want, VANILLA_CAPITAL_GATE_RUNES)
        avail = world._available_runes()   # all seven now (#764) -- every one counts at the gate
        # 🛑 REPAIR THE SUPPLY. DO NOT DISARM. (2026-08-12, issue #589.)
        #
        # This used to `return` on a shortfall, leaving gf_leyndell_runes empty so WALL_ARMED reads
        # False and the capital bundle is granted on the Lock. The reasoning was that disarming is
        # always the safe direction. IT IS NOT, AND THE COST IS AN UNWINNABLE SEED: disarming OUR
        # wall does not disarm the GAME'S. The vanilla capital gate still demands two Great Runes,
        # and per the fogwall note below it is the only way in -- so a seed whose kept regions hold
        # one rune sealed Leyndell, the Sewer and Ashen Capital behind a door nothing could open.
        # LordChungle's 7-player seed 26505919849221796677 is the case: one countable rune in the
        # whole multiworld, the run unfinishable, and FORTY-TWO other players' items stranded in a
        # region nobody could reach. Generation said nothing.
        #
        # The pool is ours to write, so top it up: mint the shortfall as real items and arm at the
        # floor. Selection is `sorted`, never world.random -- no rng-stream motion, so every
        # existing seed that did NOT need repair rolls byte-identically. Injected runes go into
        # gf_leyndell_runes so core._class_for marks them PROGRESSION and fill places them outside
        # the capital, exactly like the runes that were already there.
        # ⭐ THE TOP-UP MOVED OUT, 2026-08-16 (#764). This block used to compute
        #     shortfall = max(0, want - len(avail)); inject = sorted(GREAT_RUNES - avail)[:shortfall]
        # and mint the difference itself. The repair was right -- it is #589's fix and it stays --
        # but it was conditioned on THIS FEATURE running, i.e. on the capital being in the draw. A
        # seed without Leyndell got no top-up at all (bobler, seed 75791261719639771134: three
        # regions, one rune in the whole multiworld, nothing injected because there was no wall to
        # inject for). A supply floor that exists only when one particular consumer is present is
        # not a floor.
        #
        # `features/great_runes` now mints every rune the draw did not supply, on every seed, so
        # `_available_runes()` is all seven by the time this runs. The wall READS the supply and no
        # longer CREATES it, which is the separation the move was for.
        inject: list = []
        if len(avail) + len(inject) < want:
            # The CATALOG itself cannot supply the wall. Unreachable while the game has six Great
            # Runes and the floor is two; here so that a future catalog change fails loudly at
            # generation instead of quietly reintroducing the strand.
            raise OptionError(
                f"leyndell_runes_required needs {want} Great Runes (floored at the vanilla "
                f"capital gate's {VANILLA_CAPITAL_GATE_RUNES}), but this seed can only supply "
                f"{len(avail) + len(inject)}. The capital's own gate cannot be lowered, so the "
                f"goal would be unreachable. Set leyndell_runes_required: 0 to hand the capital "
                f"bundle to the Leyndell Lock instead.")
        world.gf_leyndell_injected = inject
        # 🛑 SEEDED SAMPLE, NOT AN ALPHABETICAL PREFIX (#640, same seam as core._resolve_required_runes).
        # This was `sorted(avail)[:want]`. `GREAT_RUNES` is sorted and `avail` is now ALL SEVEN on
        # every seed (#764), so the prefix became totally fixed -- every capital in every seed would
        # arm on Godrick's + the Unborn rune, and Rykard's (last alphabetically) could only ever arm
        # a wall asking for all seven. `world.random` is the seeded multiworld stream, so this stays
        # reproducible from the seed while being a real choice; sorted on the way out so the armed
        # set reads stably in logs and slot_data.
        world.gf_leyndell_runes = sorted(world.random.sample(sorted(avail), want))
        _log.info("leyndell_gate: wall ARMED at %d of %d pooled Great Rune(s) -- %s",
                  len(world.gf_leyndell_runes), len(avail),
                  ", ".join(world.gf_leyndell_runes))

    def create_items(self, world):
        """Mint the runes generate_early had to inject.

        This rides the existing count-exact seam (core.create_items: `pool += f.create_items(self)`
        before the filler tail is sized), the same way features/finale.py contributes the Ashen
        lock's replacement -- items minted here eat filler-tail slots, so items == locations by
        construction. Never touch multiworld.itempool directly.
        """
        return [world.create_item(nm) for nm in getattr(world, "gf_leyndell_injected", ())]

    def set_rules(self, world) -> None:
        runes = getattr(world, "gf_leyndell_runes", [])
        if not runes:
            return
        need = len(runes)
        player = world.player
        # ENTRANCE rule (2026-07-14, gated-children fix): the rune requirement also guards the
        # "To Leyndell" edge itself. core.create_regions parents gated children (REGION_PARENT), so
        # Leyndell hangs off Altus and the SEWER hangs off Leyndell -- gating the entrance makes the
        # rune wall transitive exactly like the physical one (the m35 well is inside the capital;
        # you cannot reach it runeless).
        #
        # THAT PARENTHESIS IS LOAD-BEARING AND WAS UNCITED. With #278 fixed, the Lock disarms our
        # kick (synthetic flag 76980) and the withheld bundle denies the warp -- so the vanilla
        # fogwall is the ONLY thing left denying physical entry to the capital. A backdoor would
        # mean Leyndell is unenforceable without a client-side wall we deliberately never built.
        # CONFIRMED by Alaric in game, 2026-08-01: "there's one way into the capital and it's the
        # fogwall, the sewer is not a backdoor."
        #
        # 🛑 AND IT DOES NOT GENERALISE. Same source, same day: the capital fogwall "is the exception
        # and not the rule -- it's like the only boundary of sphere 0 in vanilla logic." Almost every
        # other vanilla "gate" in this game is soft: skippable on a horse, walkable around, or
        # reachable by a route the designers did not mean as an entrance. Leyndell is the one place
        # where letting the GAME hold the wall is sound. So features/natural_progression.GAME_NATIVE_GATE
        # is not a pattern to extend -- a second region added to it would be a region with no wall at
        # all, and the failure is silent (logic believes a door is shut that the player walks past).
        #
        # The per-location rules below stay: they carry the
        # item_rule cycle-breaker and cover the capital checks directly.
        try:
            entrance = world.multiworld.get_entrance(f"To {GOAL_REGION}", player)
        except KeyError:
            entrance = None  # goal region sealed (dlc_only) -- generate_early already bailed then
        if entrance is not None:
            prev_ent = entrance.access_rule
            entrance.access_rule = (lambda state, p=prev_ent, gr=GREAT_RUNES, k=need:
                                    p(state) and sum(1 for g in gr if state.has(g, player)) >= k)
        # ITEM rule (2026-07-15, sewer-rune FillError): the _GATING_ITEMS bar must cover the WHOLE
        # walled subtree, not just the capital's own m11/m19 checks. Under accessibility:minimal,
        # AP's fill_restrictive SKIPS the reachability check whenever the exploration state can
        # already beat the game (Fill.py perform_access_check) -- and with the region_locks ending
        # the completion condition never mentions the gate runes, so a rune's OWN placement is
        # exactly when the check is skipped (a Lock's never is: completion needs every Lock, so
        # "beaten" is false while that Lock is in hand). The strict progression_surface pre-fill
        # then LOCKS the rune wherever item_rule allows: seed 36 locked Godrick's Great Rune onto
        # Mohg the Omen (Sewer :: [Incantation] Bloodflame Talons, f510250) -- behind the very
        # wall it opens -- and post_fill's audit_reachable correctly FillErrored. item_rule is the
        # one rule can_fill honors UNCONDITIONALLY, so it, not the (transitive) entrance rule, is
        # the load-bearing guard; it must span every region the wall spans. The Sewer had this bar
        # while m35 rode the prefix list; the v2 region split silently dropped it.
        gated_regions = _gated_region_names(world)
        leyndell = _leyndell_location_ids()
        for loc in world.multiworld.get_locations(player):
            region = getattr(getattr(loc, "parent_region", None), "name", None)
            if region not in gated_regions:
                continue
            if getattr(loc, "address", None) in leyndell:
                prev = loc.access_rule
                loc.access_rule = (lambda state, p=prev, gr=GREAT_RUNES, k=need:
                                   p(state) and sum(1 for g in gr if state.has(g, player)) >= k)
            prev_item = loc.item_rule
            loc.item_rule = (lambda item, pv=prev_item:
                             pv(item) and item.name not in _GATING_ITEMS)

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key yet (hard in-game gate = follow-up)
