"""unobtainable_locations -- tell the tracker which checks THIS seed can never award (slot_data only).

THE REPORT (Ace, Discord, 2026-09-13). Haligtree read 116/123 after both Haligtree bosses were
dead. Two of the leftovers were Millicent's rewards -- `Prosthesis-Wearer Heirloom [f400320]` and
`Somber Ancient Dragon Smithing Stone [f400325]`. Millicent's questline starts with Gowry in
Caelid, and Caelid was not a kept region in that seed, so the checks could never fire; the tracker
listed them under Haligtree anyway, because `locationRegions` says only WHERE a check is, never
whether the seed can reach the quest state that awards it. Alaric's ruling: "we shouldn't be
displaying those checks in the tracker if they're not obtainable in seed."

WHAT THIS IS, AND IS NOT.
  * It is the consumer `tracker_tables.rs` said to wait for when it dropped the baked `missable`
    column ("when a consumer exists, add the key then"). It is NOT the missable set:
    features/missable_locations.py tags checks that CAN BE LOST (a killable NPC, a spent
    consumable) and bars progression from them at fill. This module names checks that CANNOT BE
    OBTAINED in a given seed, which is a per-seed fact about `num_regions`, not a corpus fact.
  * AP-side semantics are UNCHANGED on purpose. The locations stay in the multiworld exactly as
    before -- randomised, missable-tagged, filler-only under the default protection. This module
    emits ONE optional slot_data key (`unobtainableLocations`) and touches no rule. A client that
    predates the key shows the checks as it always did.
  * The route table is REVIEWED, not derived. `greenfield/questline_dag.tsv` is evidence, not
    executable logic (its header says so), and the two things it cannot tell us are exactly what
    this needs: which NPC STATIONS a quest passes through (Millicent must be met at Windmill
    Village and the Snow Valley before she reaches the Prayer Room, and neither talk is a check),
    and whether a `group_semantics=any` gate is a hard prerequisite at all. So the strong DAG rows
    (sense=set, single, cross_region=yes) are pinned by `test_gf_unobtainable_locations` as the
    population every entry below must either COVER or name in `REVIEW_PENDING` with a reason --
    the same keeper shape `test_gf_lot_gates_cross_region` uses for the missable set.

WHY REGIONS AND NOT ITEMS. Under item shuffle the quest ITEMS (Unalloyed Gold Needle, Valkyrie's
Prosthesis, Fingerslayer Blade) are in the pool and can come from any world, so "the check where the
needle vanilla-sits is in Caelid" is not a prerequisite. What IS a prerequisite is physical: the NPC
has to be TALKED TO in a region, and a region that is not kept is sealed. That is why the table
below is keyed by regions a quest must visit, and why `quest_prerequisite_rules.REVIEWED_PREREQUISITES`
(flag -> flag, about self-locking a placed item) is deliberately not folded in.
"""
from typing import Dict, FrozenSet, Iterable, List, Mapping, Sequence, Set, Tuple

from ..registry import Feature, register
from .. import contract


# Dependent check FLAG -> regions (other than the check's own) the awarding questline must be
# advanced in. A region is a `tables.regions` name. Every row cites what it rests on.
#
# ⚠️ FALSE POSITIVES HIDE REAL CHECKS. A row here makes the tracker HIDE the check on every seed
# that drops one of its regions, so a region that is not truly required is a check the player
# never gets told about. Only rows the author would defend at the table go here; the doubtful
# ones sit in REVIEW_PENDING (visible, inert) until somebody plays them.
REVIEWED_QUEST_ROUTES: Dict[int, Tuple[str, ...]] = {
    # ---- Millicent (Gowry's shack, Caelid -> Windmill Village, Altus -> Ancient Snow Valley
    #      Ruins, Mountaintops -> Prayer Room, Haligtree). The Ace report. The Haligtree rewards
    #      only exist once she has been walked through all three earlier stations; the Heirloom
    #      (f400320) is awarded AT Gowry's shack and moved to Caelid in #1555, so it needs no row.
    #      Evidence: questline_dag.tsv esd_gifts rows 1050389257 -> 400320 (Caelid, Millicent's
    #      NPC state) and lot_gates 4192 -> 400321 (her Haligtree state transition), plus the
    #      1.17 talk ESD t348 station order.
    400321: ("Caelid", "Altus", "Mountaintops of the Giants"),   # Unalloyed Gold Needle (Prayer Room)
    400323: ("Caelid", "Altus", "Mountaintops of the Giants"),   # Millicent's Prosthesis
    400324: ("Caelid", "Altus", "Mountaintops of the Giants"),   # Miquella's Needle (lot 103240)
    400325: ("Caelid", "Altus", "Mountaintops of the Giants"),   # Somber Ancient Dragon SS (lot 103241)
    # ---- Ranni (Ranni's Rise, Liurnia -> Ainsel River). Miniature Ranni is handed over at Ainsel
    #      River Main only after the Rise conversations. DAG lot_gates 1034509430 -> 400394
    #      (single, set, cross_region=yes: Ranni's Liurnia state).
    400394: ("Liurnia",),                                        # Miniature Ranni (Ainsel)
    #      The Dark Moon Greatsword sits in Liurnia (Manus Celes) but the doll talks, the Baleful
    #      Shadow and Astel are Ainsel River content. The DAG's rows for 400393 resolve their
    #      source to `Caelid` (group `unknown`), which is no station of the quest; the reviewed
    #      station is Ainsel River.
    400393: ("Ainsel River",),                                   # Dark Moon Greatsword
    # ---- Volcano Manor letters (Tanith, Mt. Gelmir). Each target only spawns after the letter
    #      is taken at the Manor. DAG lot_gates 7602/7605/7604 -> the three armour drops (single,
    #      set, cross_region=yes) -- the same rows gen_data.py lists at "ADDED 2026-07-26".
    1042397500: ("Mt. Gelmir",),                                 # Scaled set, Old Knight Istvan (Limgrave)
    11007985: ("Mt. Gelmir",),                                   # Raging Wolf set, Vargram (Leyndell)
    1050567700: ("Mt. Gelmir",),                                 # Hoslow's set, Juno Hoslow (Snowfield)
    # ---- Sellen (Waypoint Ruins, Limgrave -> Azur, Mt. Gelmir -> Lusat, Caelid -> Witchbane
    #      Ruins, Weeping -> Grand Library). The crown is her Grand Library ending. DAG lot_gates
    #      3469 -> 400107 (single, set: her Weeping state transition) is the evidenced leg; the
    #      other three are the station order of talk ESD t316.
    400107: ("Limgrave", "Mt. Gelmir", "Caelid", "Weeping"),    # Witch's Glintstone Crown
    # ---- Edgar (Castle Morne, Weeping -> Revenger's Shack, Liurnia). The Shabriri Grape is his
    #      invasion drop and he only relocates after the Morne leg. gen_data.py cross-region list;
    #      DAG group `any` because all three trigger flags are Weeping-side.
    400061: ("Weeping",),                                        # Shabriri Grape
}

# Strong DAG rows (sense=set, single, cross_region=yes) that are NOT promoted to a route yet, each
# with the reason. The keeper test requires every such row to be here or above, so a new datamine
# result cannot ship silently -- and a row here cannot silently become a route either.
REVIEW_PENDING: Dict[int, str] = {
    9500: "Ashen Capital target; the Capital exists only when Leyndell is kept, so the Leyndell "
          "prerequisite is satisfied by construction (finale.py). Nothing to hide.",
    400500: "Ashen Capital target, same as 9500.",
    400281: "source is Roundtable Hold (the hub), which every seed keeps. Nothing to hide.",
    400349: "Twinned set at the Roundtable: DAG names Siofra River (D's brother, flag 4048), but "
            "the award also runs through Deeproot (Fia) and the exact station set is unconfirmed.",
    400614: "Soiled Loincloth (Enir Ilim): DAG source 7623 decodes to Scadu Altus while gen_data's "
            "list says Ancient Ruins (Ansbach/Thiollier). Two derivations disagree on the region.",
    400622: "Ansbach's Boots (Shadow Keep): DAG source 7621 decodes to Scadu Altus; gen_data lists "
            "the Wise Man's Mask on the same gate from Scadu Altus. Station unconfirmed in play.",
    580120: "Scadu Altus checks whose cone root is MAP_ACCESS(m21_00), i.e. the Shadow Keep map "
            "tile. That is a region-ASSIGNMENT question (are they Shadow Keep checks?), not a "
            "quest route; hiding them would paper over a possible misregion instead of fixing it.",
    21007991: "same as 580120 (m21_00 map access).",
    21007993: "same as 580120 (m21_00 map access).",
    21007995: "same as 580120 (m21_00 map access).",
    34147720: "Divine Tower of East Altus stone regioned Leyndell with cone root MAP_ACCESS(m34_14) "
              "from Altus: region assignment, not a quest route (see 580120).",
    1044357100: "Larval Tear at Agheel Lake South: lot_gates 1035432270 (a Liurnia m60_35_43 flag) "
                "is the only evidence and no NPC station is known for a world pickup; suspected "
                "sweep-grant co-occurrence rather than a prerequisite.",
}


def prerequisite_regions_by_flag() -> Dict[int, FrozenSet[str]]:
    """The reviewed table as flag -> frozenset(regions). One place the tests and the emitter read."""
    return {int(flag): frozenset(regions) for flag, regions in REVIEWED_QUEST_ROUTES.items()}


def unobtainable_ids(kept: Iterable[str], hub: str,
                     rows_by_region: Mapping[str, Sequence[Tuple[str, int, int]]],
                     routes: Mapping[int, FrozenSet[str]] = None) -> List[int]:
    """AP ids among `rows_by_region` (region -> (name, ap_id, flag) rows, ALREADY scoped to this
    seed) whose flag has a reviewed route through a region that is neither kept nor the hub.
    Pure, so it can be tested against explicit kept sets without a built world."""
    if routes is None:
        routes = prerequisite_regions_by_flag()
    open_regions: Set[str] = set(kept) | {hub}
    out: Set[int] = set()
    for rows in rows_by_region.values():
        for (_name, ap_id, flag) in rows:
            need = routes.get(int(flag))
            if need and (need - open_regions):
                out.add(int(ap_id))
    return sorted(out)


@register
class UnobtainableLocations(Feature):
    name = "unobtainable_locations"

    def slot_data(self, world) -> Dict[str, List[int]]:
        kept = list(world._kept())
        hub = world.tables.hub
        # `_seed_locations` is the count-neutral chokepoint locationRegions is built from, so the
        # emitted ids are a subset of that table by construction (the test pins it anyway).
        rows = {rn: world._seed_locations(rn) for rn in [hub] + kept}
        ids = unobtainable_ids(kept, hub, rows)
        # Always emitted, even empty: an ABSENT key means "old apworld, nothing known", and the
        # client logs exactly that; an EMPTY list means "checked, nothing to hide".
        return {contract.UNOBTAINABLE_LOCATIONS: ids}
