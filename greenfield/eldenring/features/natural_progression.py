"""Natural / Vanilla Progression mode -- SPEC-vanilla-progression-20260722.md.

Faithful-vanilla progression: encode vanilla ER's region dependency graph using REAL vanilla key
items + boss remembrances as gate tokens, fully shuffled and decoupled from their vanilla givers --
"vanilla's SHAPE, AP's variety." The inverse of num_regions (The Shattering): instead of a rolled
random subset gated by synthetic locks, the whole eligible map is in play and every region opens on
its own REAL key. ZERO synthetic ``<Region> Lock`` items are minted in this mode.

Three-layer coherence (spec S1): topology = vanilla (which region gates which), order = the multiworld
(the gate items are shuffled, so *when* you reach a region is AP fill's call), difficulty =
sphere-scaling (features/scaling.py, unchanged -- this mode owns ORDER, never difficulty).

HOW IT RIDES THE REGION-LOCK ENGINE
-----------------------------------
The client already ports + host-tests ``naturalKeyTriggers`` (region.rs::tick_natural_key_triggers):
a region blooms its open flag WITHOUT an AP lock item when a disjunctive clause of real items (AND
optional world flags) is satisfied. Its map key is the same ``"<Region> Lock"`` identifier the
region-lock slot_data (regionOpenFlags / regionGraces / areaLockFlags) already speaks, so we emit
triggers keyed by that identifier WITHOUT minting the item and WITHOUT touching graces.py/area_locks.py
-- the ``"<Region> Lock"`` string survives only as an internal identifier, never as a received item.
core.py does the rest in this mode: skip minting locks + the start anchor, gate each region's entrance
on its key clause (below) instead of ``has("<Region> Lock")``, and make the goal REACH the goal region
(Leyndell, via its 2-Great-Rune gate) rather than ``has_all(locks)``.

FLATTEN + kept chokepoints (spec S2): warp-in flattens geography (a lock warps you in, so geography !=
dependency), so every region opens directly off START except the deliberately-KEPT chokepoints, which
are encoded as COMPOUND key clauses (you must hold the upstream key), not graph edges:
  * DLC bloc  <- Remembrance of the Blood Lord (Mohg)
  * Gelmir    <- Rya's Necklace  OR  (Rem. of the Grafted AND Academy Glintstone Key)   [Liurnia+Academy]
  * Rauh      <- Shadow Keep's clause (Blood Lord AND Aspects of the Crucible: Thorns)
  * Capital   <- Altus (graph parent, REGION_PARENT) AND 2 Great Runes (count gate; this
                 feature owns the rune half -- the AP-logic mirror of the vanilla wall -- since
                 features/leyndell_gate.py was retired on 2026-09-14). NB Altus IS a Leyndell
                 prerequisite (Alaric 2026-07-23 -- this SUPERSEDES the committed spec S2
                 "Altus prereq DROPPED" line; update the spec).

TWO NEW PRIMITIVES (spec S2): the COUNT-gate (open on N-of-a-set) and the COMPOUND-gate (items AND
world flags). v0.1 DRAFT wired single-item + OR + compound-of-items gates end-to-end; the COUNT-gate
was LOGIC-ONLY until the client count primitive landed (2026-07-24): a clause may now carry
``{"countItems": [names...], "count": N}`` (region.rs parse_natural_keys / er-logic
natural_key_fired) and fires when >= N distinct countItems have been received -- so COUNT_GATES
(Caelid) now emits a real client trigger instead of degrading to always-open. Leyndell's
2-Great-Rune gate ALSO rides the count primitive now: the vanilla main gate does open in-game on
held runes, but the client's areaLock seal (open flag 71102, set by nothing in this mode -- no
"Leyndell Lock" item exists) kept the capital kicked-sealed in the 2026-07-24 playtest, so slot_data
emits a count trigger on 2 Great Runes that blooms the capital's open flag exactly when the
vanilla wall would open. This feature keeps the AP-logic mirror (the "To Leyndell" edge rule in
set_rules below) -- since the 2026-09-14 retirement of features/leyndell_gate.py, which owned it
before. (The Sewer merged into Leyndell 2026-08-20: one region, one trigger.)

DLC key resolution (Alaric 2026-07-24 -- corrects spec S3/S4/S5):
  * Abyssal Woods -> Barbed Staff-Spear (Jori, Elder Inquisitor, is NOT a remembrance boss; the spec's
    "Jori's remembrance" was a slip). Barbed Staff-Spear is a real pooled catalog item -> RESOLVED.
  * Mohgwyn -> Pureblood Knight's Medal (Varre) OR Secret-Medallion x2. Pureblood was an unplaced
    common-event grant (not pooled); INJECTED via gen_data.GLOBAL_RECOVER[400032]="Liurnia" -> becomes a
    real pooled item after a `-Greenfield` regen. The clause is availability-guarded (rides Secret-
    Medallion until the regen bakes the medal).
  * Enir-Ilim -> Messmer's Kindling (a real vanilla KEY ITEM, goods 2008021). It shares Messmer's defeat
    flag 510460 with the Remembrance of the Impaler (lots 10460+10461); captured as its own CO-CHECK
    (SPEC-flag-lot-item-model: gen_data.CO_CHECK_FLAGS + co_check_ids.tsv -- the sibling lot is its own
    co-firing location, the remembrance stays the primary check, BOTH items are pooled, nothing deleted;
    supersedes the retired ROW_ITEM_NAME_FIX rename, which deleted the remembrance from the game) ->
    becomes a real pooled item after a `-Greenfield` regen. Enir-Ilim's clause is availability-guarded
    (opens ungated pre-regen; gates on Blood Lord + Kindling post-regen). The spec's additional
    K-Scadutree-Fragment count-gate half still needs the client count primitive.
  * Caelid's "2 remembrances" count vs the festival-softlock flag 9410 (spec S5): RECONCILED -- the
    Radahn Festival flag is force-set at spawn by start_grace (_RADAHN_FESTIVAL, playtest 2026-07-11),
    independent of Caelid's gate, and the client count trigger only sets Caelid's open flag / graces /
    reveal flags (tick_natural_key_triggers), never 9410. Nothing here touches 9410.

Pure-ish module: imports Options/registry/data/region_spine/item_ids only (never core -> no cycle), so
its pure helpers unit-test without a live world.
"""
from itertools import combinations

from Options import Toggle
from ..registry import Feature, register

try:
    from ..tables.data import REGIONS, LOCATIONS
except Exception:  # pragma: no cover -- pre-regen data
    REGIONS, LOCATIONS = [], {}
try:
    from ..tables.item_ids import ITEM_CATALOG, LOCATION_ITEM
    from .. import item_categories as _ic
except Exception:  # pre-regen / standalone import
    ITEM_CATALOG, LOCATION_ITEM = {}, {}

    class _ic:  # type: ignore[no-redef]  # no catalog -> no runes
        GREAT_RUNES: list = []
try:
    from ..tables.region_open_flags import REGION_OPEN_FLAGS
except Exception:
    REGION_OPEN_FLAGS = {}

# Great Runes + Remembrances read from the catalog (matt-free, same rule as core.GREAT_RUNES).
# SEVEN, from the one definition in item_categories -- see its GREAT_RUNE_GOODS_IDS block.
GREAT_RUNES = frozenset(_ic.GREAT_RUNES)
REMEMBRANCES = frozenset(n for n in ITEM_CATALOG
                         if n.startswith("Remembrance of") or n.startswith("Remembrance "))

try:
    from ..region_spine import GOAL_REGION
except Exception:  # pragma: no cover -- pre-regen data
    GOAL_REGION = "Leyndell"

# The VANILLA capital main gate is a fixed two-Great-Rune possession wall. It is not ours and it
# does not scale with our options, so it is the count on any capital rune wall this mode arms.
# (Moved here 2026-09-14 with the retirement of features/leyndell_gate.py, which owned it before.)
VANILLA_CAPITAL_GATE_RUNES = 2

# ⭐ ALL SEVEN COUNT AT THE GATE -- and the claim that they do not was never sourced.
#
# (Moved here 2026-09-14 from features/leyndell_gate.py, which carried this block until its
# retirement. In default modes the capital opens on its Lock now and no logic counts runes
# there; in THIS mode the game's own wall is still the wall, so this is where the reading lives.)
#
# `common.emevd $Event(6905)` "救済対応_伍 / Relief response_5" maps every remembrance flag to a
# CONTIGUOUS held-rune slot -- 510010->171, 510300->172, 510040->173, 510220->174, 510120->175,
# 510200->176, and 197->177. SEVEN slots, one per Great Rune, the Unborn rune among them.
#
# A game that did not count it would not give it a slot in that block. And the count IS decidable
# from the corpus (2026-08-22, clients#392): common $Event(730) 大ルーン所持数チェック is
# `CountEventFlags(EventFlag, 170, 179) >= threshold` -- the possession band 6905 writes into --
# and its threshold-2 slot outputs flag 182, which the 王都の封印 (m60_45_52_00/.10
# $Event(1045522500)) reads as `EventFlag(182) && EventFlag(105)`. The sibling counter $Event(720)
# over the RESTORED band 190-199 feeds outputs 160-167 that nothing in the corpus reads. So all
# seven count, in vanilla, through 171-177 -- and an AP goods grant sets none of them, which is why
# the client writes 105+182 directly (keyitems.rs LEYNDELL_TWO_RUNES_FLAGS; on Lock receipt since
# the 2026-09-14 Leyndell ruling, on rune receipt before).
#
# So: no exclusion. If the engine ever proves otherwise, the fix is a cited constant, not a docstring.

# ---- the gate table (spec S3 base + S4 DLC) -----------------------------------------------------
# region -> list of CLAUSES; each clause = a tuple of catalog key names ALL required (AND); the
# clauses are OR'd (any satisfied clause opens the region). A region absent here (Limgrave, Weeping,
# the DLC/base spokes with no vanilla key) opens directly off START. Kept chokepoints are encoded by
# folding the upstream key(s) into the clause (see the module docstring). Every name is a REAL catalog
# item; unavailable names are filtered at runtime (unavailable-only clauses degrade the region to open,
# logged) so a name that is not in this seed's pool never strands the region.
GATE_CLAUSES = {
    # --- base, off START ---
    "Stormveil": [("Rusty Key",)],
    "Liurnia": [("Remembrance of the Grafted",)],
    "Raya Lucaria Academy": [("Academy Glintstone Key",)],
    "Altus": [("Dectus Medallion (Left)", "Dectus Medallion (Right)"),
              ("Magma Wyrm's Scalesword",),
              ("Inquisitor's Girandole",)],
    # kept chokepoint: Gelmir behind Liurnia+Academy, or its own Rya's Necklace off START.
    "Mt. Gelmir": [("Rya's Necklace",),
                   ("Remembrance of the Grafted", "Academy Glintstone Key")],
    "Mountaintops of the Giants": [("Rold Medallion",)],
    "Consecrated Snowfield": [("Haligtree Secret Medallion (Left)",
                                "Haligtree Secret Medallion (Right)")],
    "Haligtree": [("Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)")],
    # Underworld / Eternal Cities bloc (spec S3 "Underworld (whole bloc)"): Rem. of the Starscourge.
    "Siofra River": [("Remembrance of the Starscourge",)],
    "Ainsel River": [("Remembrance of the Starscourge",)],
    "Deeproot Depths": [("Remembrance of the Starscourge",)],
    # Mohgwyn: two routes (spec S3) -- Varre's Pureblood Knight's Medal, OR the Snowfield Secret-Medallion
    # x2 portal. The Pureblood clause is availability-guarded: the medal is INJECTED into the pool via
    # gen_data.GLOBAL_RECOVER[400032] (Alaric 2026-07-24) but only exists after a `-Greenfield` regen, so
    # until then active_clauses drops that clause and Mohgwyn rides the Secret-Medallion route alone.
    "Mohgwyn": [("Pureblood Knight's Medal",),
                ("Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)")],
    "Farum Azula": [("Remembrance of the Fire Giant",)],
    # --- DLC fold bloc: everything behind Mohg / Blood Lord remembrance (kept chokepoint) ---
    "Gravesite": [("Remembrance of the Blood Lord",)],
    "Ensis": [("Remembrance of the Blood Lord",)],
    "Cerulean": [("Remembrance of the Blood Lord",)],
    "Belurat": [("Remembrance of the Blood Lord",)],
    # --- DLC gated-deeper regions (each = DLC entry AND its own token) ---
    "Scadu Altus": [("Remembrance of the Blood Lord", "Remembrance of the Twin Moon Knight")],
    "Shadow Keep": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
    # kept chokepoint: Rauh behind Shadow Keep -> Shadow Keep's clause. (Rauh Base + Ancient Ruins are
    # merged per spec S2; both carry the Shadow-Keep clause.)
    "Ancient Ruins": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
    "Rauh Base": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
    "Jagged Peak": [("Remembrance of the Blood Lord", "Dragon-Hunter's Great Katana")],
    # Abyssal Woods: the spec's "Jori's remembrance" is a naming slip -- Jori (Elder Inquisitor) is not
    # a remembrance boss. His signature drop is the Barbed Staff-Spear (a real, pooled catalog item;
    # vanilla location is a Scadu Altus check f510610, but keys are location-independent so it gates
    # Abyssal fine). DLC entry (Blood Lord) is folded in to keep Abyssal behind Mohg. (Alaric 2026-07-24.)
    "Abyssal": [("Remembrance of the Blood Lord", "Barbed Staff-Spear")],
    # Enir-Ilim finale: gate on Messmer's Kindling (spec S4), the vanilla finale key. Kindling is a
    # CO-CHECK (gen_data.CO_CHECK_FLAGS[510460] + co_check_ids.tsv: its sibling lot 10461 is its own
    # co-firing location beside the Remembrance primary, both pooled -- SPEC-flag-lot-item-model) ->
    # it becomes a real pooled item after a `-Greenfield` regen. Availability-guarded: PRE-regen
    # (Kindling absent) this clause drops and Enir-Ilim opens ungated -- harmless, as the goal is the
    # base capital, not Enir-Ilim; POST-regen the finale gates on Blood Lord + Kindling.
    # (The spec's additional K-Scadutree-Fragment count is deferred -- it needs the client count primitive.)
    "Enir Ilim": [("Remembrance of the Blood Lord", "Messmer's Kindling")],
}

# COUNT-gates (open on N of a named set). Wired end-to-end since 2026-07-24: entrance_rule counts in
# AP logic AND slot_data emits a client count trigger ({"countItems": [...], "count": N} clause --
# region.rs / er-logic natural_key_fired). region -> (set, N).
COUNT_GATES = {
    "Caelid": (REMEMBRANCES, 2),   # spec S3 "2 remembrances"; 9410 reconciled (see docstring)
}

# Regions whose opening is the GAME's own native gate -> no ENTRANCE clause of ours. Leyndell
# reads N Great Runes on its "To Leyndell" edge (this feature's set_rules, the AP-logic mirror of
# the vanilla wall) and gets a client count trigger from slot_data below -- the vanilla main gate
# opens in-game on held runes, but the client's areaLock seal needs the open flag bloomed or the
# kick keeps the capital shut (2026-07-24 playtest).
# 🛑 THIS MODE ONLY, since 2026-09-14. Everywhere else Leyndell opens on its Lock like any region
# (features/leyndell_gate.py retired): the seal is opened by the client on Lock receipt, and no
# logic counts runes at the capital. Here there IS no Lock item, so the game's own two-rune wall
# is still the wall -- leave this set, and this mode's rune half, exactly as they are.
GAME_NATIVE_GATE = frozenset({"Leyndell"})

# Graph parents kept in THIS mode (everything else flattens off the hub). Leyndell stays behind Altus
# (Alaric 2026-07-23: Altus IS a Leyndell prerequisite -- supersedes spec S2); Sewer stays inside the
# capital. Raya Lucaria's vanilla REGION_PARENT (-> Liurnia) is DROPPED here: it flattens off START on
# its own Academy Glintstone Key (spec S2 flatten).
NATURAL_PARENT = {
    "Leyndell": "Altus",
    "Sewer": "Leyndell",
}


class NaturalProgression(Toggle):
    """Faithful-vanilla progression: play the whole map with regions gated by REAL vanilla keys +
    boss remembrances (shuffled), in vanilla's dependency SHAPE -- the inverse of The Shattering
    (num_regions). No synthetic region locks. Off (default): normal num_regions behaviour. On: every
    region opens on its own real key off the start, minus the kept chokepoints (DLC behind Mohg, Gelmir
    behind Liurnia+Academy, Rauh behind Shadow Keep, the capital behind Altus + 2 Great Runes); the
    whole eligible map is in play (num_regions is ignored). SPEC-vanilla-progression-20260722.md."""
    display_name = "Natural Progression"


# ---- pure helpers (world may be None-ish in unit tests; all reads are getattr-guarded) ----------
def is_on(world) -> bool:
    opt = getattr(world.options, "natural_progression", None)
    return bool(opt is not None and opt.value)


def _pooled_names(world) -> set:
    """Catalog names that actually appear on a KEPT region's location this seed (so they are in the
    pool and can gate). item_shuffle is frozen ON, so every kept location contributes its vanilla item.
    Falls back to plain ITEM_CATALOG membership if LOCATION_ITEM is unavailable (pre-regen)."""
    kept = set(world._kept())
    if not LOCATION_ITEM:
        return set(ITEM_CATALOG)
    names = set()
    for rn in kept:
        for (_n, ap_id, _flag) in LOCATIONS.get(rn, ()):
            nm = LOCATION_ITEM.get(ap_id)
            if nm:
                names.add(nm)
    return names


def active_clauses(world):
    """{region: [clause, ...]} for KEPT regions in GATE_CLAUSES, with any clause dropped that names an
    unavailable key. A region whose clauses ALL drop is omitted (it degrades to open, logged by the
    feature). Cached on the world."""
    cached = getattr(world, "_gf_natural_clauses", None)
    if cached is not None:
        return cached
    kept = set(world._kept())
    avail = _pooled_names(world)
    out = {}
    for region, clauses in GATE_CLAUSES.items():
        if region not in kept:
            continue
        live = [c for c in clauses if all(k in avail for k in c)]
        if live:
            out[region] = live
    world._gf_natural_clauses = out
    return out


def _count_set(world, names, n):
    """The pooled subset of `names`, or None if fewer than `n` are available (gate can't bind -> open)."""
    avail = _pooled_names(world)
    live = [x for x in names if x in avail]
    return live if len(live) >= n else None


def key_items(world) -> list:
    """Every catalog key named by an active clause (single/OR/compound) -> core marks these PROGRESSION
    so AP fill guarantees them reachable. Count-gate sets are LOGIC-only and NOT force-marked here (they
    would over-constrain fill); their members stay whatever class they already are."""
    names = set()
    for clauses in active_clauses(world).values():
        for c in clauses:
            names.update(c)
    return sorted(names)


def natural_parent(region):
    """Graph parent for `region` in this mode (None = hangs off the hub)."""
    return NATURAL_PARENT.get(region)


def entrance_rule(world, region):
    """The access predicate for `region`'s 'To <region>' edge in this mode, or None = always open
    (start regions / spokes / degraded gates / the game-native capital, whose 2-rune rule this
    feature's set_rules ANDs onto the edge separately)."""
    player = world.player
    if region in GAME_NATIVE_GATE:
        return None
    if region in COUNT_GATES:
        names, n = COUNT_GATES[region]
        live = _count_set(world, names, n)
        if live is None:
            return None
        return lambda state, nm=tuple(live), k=n, p=player: (
            sum(1 for x in nm if state.has(x, p)) >= k)
    clauses = active_clauses(world).get(region)
    if not clauses:
        return None
    return lambda state, cl=tuple(clauses), p=player: any(
        all(state.has(k, p) for k in c) for c in cl)


# ---- the capital rune wall (THIS MODE ONLY) ---------------------------------------------------
# Moved here 2026-09-14 from features/leyndell_gate.py, which is retired. Everywhere else Leyndell
# opens on its Lock and no logic counts runes; here there is no Lock item, so the game's own
# fixed two-rune wall is still the wall and logic must mirror it, or fill strands progression
# behind a door it cannot prove open.
#
# Capital map prefixes: m11 = Leyndell Royal + Ashen Capital, m19 = Fractured Marika / final
# arena. The acquisition flag encodes the map (mAA -> AA......), so an m11/m19 flag in the goal
# region is a capital check. Restricting to GOAL_REGION keeps HUB-overridden m11_10 Roundtable
# checks out (they region to the hub).
_LEYNDELL_PREFIXES = ("11", "19")
_LEYNDELL_EXTRA_FLAGS = frozenset({173, 510040, 60520})  # Morgott GR + Rem. Omen King, Godfrey pouch
# Gating items forbidden on capital-walled locs = Great Runes (the wall's own prerequisite) PLUS
# the folded-dungeon legacy keys (Academy Glintstone Key, Hole-Laden Necklace) -- keeping a key
# off a rune-walled capital check breaks the Metyr<->Leyndell cross-gate cycle (FillError
# 2026-07-10). Same membership the retired wall carried; the cycle it breaks is still real here.
_CAPITAL_GATING_ITEMS = frozenset(GREAT_RUNES) | frozenset(
    {"Academy Glintstone Key", "Hole-Laden Necklace"})


def _gated_region_names(world):
    """Every region physically behind the 'To <GOAL_REGION>' edge, DERIVED from the live region
    graph: the goal region plus everything reachable through its exits. A location in this subtree
    sits behind the rune wall, so a gating item placed there can deadlock the very gate it opens.
    Empty when the goal region is sealed this seed (dlc_only)."""
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


def _apply_capital_wall(world) -> None:
    """AND the vanilla 2-rune wall onto the capital in AP logic: the "To Leyndell" entrance, the
    capital's own checks, and the item_rule cycle-breaker over the whole walled subtree.

    ENTRANCE rule: the rune requirement guards the edge itself, so it is transitive to everything
    hung under the capital exactly like the physical fogwall (which Alaric confirmed in game,
    2026-08-01, is the one way in -- the sewer well inside it is not a backdoor).
    ITEM rule: the _CAPITAL_GATING_ITEMS bar must cover the WHOLE walled subtree, not just the
    capital's own checks. Under accessibility:minimal AP's fill_restrictive SKIPS the reachability
    check whenever the exploration state can already beat the game -- and item_rule is the one
    rule can_fill honors UNCONDITIONALLY, so it, not the (transitive) entrance rule, is the
    load-bearing guard (seed 36, 2026-07-15: Godrick's Great Rune locked onto Mohg the Omen
    behind the very wall it opens)."""
    runes = getattr(world, "gf_capital_runes", [])
    if not runes:
        return
    need = len(runes)
    player = world.player
    try:
        entrance = world.multiworld.get_entrance(f"To {GOAL_REGION}", player)
    except KeyError:
        entrance = None  # goal region sealed (dlc_only) -- generate_early already bailed then
    if entrance is not None:
        prev_ent = entrance.access_rule
        entrance.access_rule = (lambda state, p=prev_ent, gr=GREAT_RUNES, k=need:
                                p(state) and sum(1 for g in gr if state.has(g, player)) >= k)
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
                         pv(item) and item.name not in _CAPITAL_GATING_ITEMS)


@register
class NaturalProgressionFeature(Feature):
    name = "natural_progression"
    OPTIONS = {"natural_progression": NaturalProgression}

    def generate_early(self, world) -> None:
        # Publish the progression key set for core._class_for (empty when the mode is off -> inert).
        world.gf_natural_keys = key_items(world) if is_on(world) else []
        # THE CAPITAL'S TWO RUNES (this mode only). Everywhere else the capital opens on its Lock;
        # here there is no Lock, so the game's fixed two-rune wall is still the wall: pick the two
        # runes core._class_for marks PROGRESSION so fill guarantees them reachable, and record
        # them for set_rules (the edge mirror) and slot_data (the client count trigger) below.
        # 🛑 SEEDED SAMPLE, NOT AN ALPHABETICAL PREFIX (#640). `GREAT_RUNES` is unordered and any
        # fixed pick would arm every capital on the same pair; `world.random` is the seeded
        # multiworld stream, so this stays reproducible from the seed while being a real choice.
        # The wall READS the supply it does not CREATE: `features/great_runes` mints every rune
        # the draw did not supply on every seed, so `_available_runes()` is all seven here.
        world.gf_capital_runes = []
        if is_on(world):
            import logging
            degraded = sorted(r for r in GATE_CLAUSES
                              if r in set(world._kept()) and r not in active_clauses(world))
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] natural_progression: %d region gate(s) active, %d key item(s) "
                "marked progression%s",
                world.player, len(active_clauses(world)), len(world.gf_natural_keys),
                (" -- DEGRADED-to-open (unavailable keys): " + ", ".join(degraded)) if degraded else "")
            avail = sorted(world._available_runes())
            if GOAL_REGION in world._kept() and len(avail) >= VANILLA_CAPITAL_GATE_RUNES:
                world.gf_capital_runes = sorted(
                    world.random.sample(avail, VANILLA_CAPITAL_GATE_RUNES))
                logging.getLogger("Greenfield").info(
                    "[eldenring:%s] natural_progression: capital wall ARMED at %d Great Rune(s) "
                    "-- %s", world.player, len(world.gf_capital_runes),
                    ", ".join(world.gf_capital_runes))

    def set_rules(self, world) -> None:
        if not is_on(world):
            return
        # THE CAPITAL WALL FIRST: it must not be skippable by the clause-breaker's early return
        # below (a seed with no live key clauses still has a capital behind two runes).
        _apply_capital_wall(world)
        # CYCLE-BREAKER (mirrors legacy_key_gates._GATING_ITEMS): a region's gate key must never land
        # inside a region that key gates, or fill can strand it behind its own gate -> the whole
        # region goes unreachable (dead checks; under accessibility:minimal AP allows it, so the guard
        # is on us). Forbid each key on the checks of EVERY region it gates -> the key lands outside,
        # keeping the region reachable. Count-gate SETS are intentionally not forbidden (too broad --
        # they name a large remembrance set, and their region has an OR of many members).
        if not is_on(world):
            return
        player = world.player
        clauses = active_clauses(world)
        key_regions = {}  # key name -> set of region names it gates
        for region, cls in clauses.items():
            for c in cls:
                for k in c:
                    key_regions.setdefault(k, set()).add(region)
        if not key_regions:
            return
        for loc in world.multiworld.get_locations(player):
            reg = getattr(getattr(loc, "parent_region", None), "name", None)
            if reg is None:
                continue
            bad = frozenset(k for k, regs in key_regions.items() if reg in regs)
            if not bad:
                continue
            prev = loc.item_rule
            loc.item_rule = lambda item, pv=prev, b=bad: pv(item) and item.name not in b

    def slot_data(self, world):
        # Emit naturalKeyTriggers keyed by the "<Region> Lock" identifier the region-lock slot_data
        # already uses, so the client blooms each region's open flag on receipt of the real keys.
        # Only regions with a live clause AND a real open flag (the client needs a flag to bloom).
        if not is_on(world):
            return {}
        kept = set(world._kept())
        triggers = {}
        for region, clauses in active_clauses(world).items():
            if REGION_OPEN_FLAGS.get(region) is None:
                continue  # no apparatus to bloom (client tick_natural_key_triggers would skip it)
            triggers[f"{region} Lock"] = {
                "anyOf": [{"items": list(c), "flags": []} for c in clauses]
            }
        # COUNT triggers (client count primitive, 2026-07-24): a clause {"countItems": [...],
        # "count": N} fires when >= N distinct countItems have been received (region.rs
        # parse_natural_keys / er-logic natural_key_fired; absent count fields parse to []/0 =
        # vacuous, so plain clauses above are untouched).
        #   * COUNT_GATES (Caelid: 2 remembrances) -- same availability rule as entrance_rule/
        #     _count_set: emitted only when >= N of the set are pooled, else the region degrades to
        #     open via the always-open fallback below (matching the degraded AP-logic rule).
        #   * Leyndell (the game-native capital): the vanilla main gate opens in-game on 2
        #     held Great Runes (this feature's generate_early arms world.gf_capital_runes and
        #     set_rules carries the AP-logic mirror), but the client's areaLock seal on open flag
        #     71102 has no "<Region> Lock" item to open it in this mode -- the 2026-07-24 playtest
        #     capital never opened. Bloom it on the 2nd received rune: exactly when the vanilla
        #     wall would open, so this cannot hand the player anything early, and it cannot strand
        #     the in-game wall (the runes the client counts are the very key-item grants the
        #     game's own gate counts). There is no Lock item here, so no grace bundle rides this
        #     trigger either way -- the player walks in past the game's own wall and touches the
        #     graces, the same as before the 2026-09-14 retirement. When the capital is not kept
        #     (dlc_only) gf_capital_runes is empty -> no count trigger -> the always-open fallback
        #     covers it.
        for region, (names, n) in COUNT_GATES.items():
            if region not in kept or REGION_OPEN_FLAGS.get(region) is None:
                continue
            live = _count_set(world, names, n)
            if live is None:
                continue  # gate can't bind this seed -> degrade to open (fallback below)
            triggers[f"{region} Lock"] = {"anyOf": [{"countItems": sorted(live), "count": n}]}
        runes = list(getattr(world, "gf_capital_runes", []) or [])
        if runes:
            for region in GAME_NATIVE_GATE:  # Leyndell, behind the game-native rune wall
                if region in kept and REGION_OPEN_FLAGS.get(region) is not None:
                    triggers[f"{region} Lock"] = {
                        "anyOf": [{"countItems": sorted(GREAT_RUNES), "count": len(runes)}]
                    }
        # BORN-SOFTLOCK FIX (2026-07-24): core.py seals EVERY in-play region with an areaLock + open
        # flag, but a region with no live clause gets no bloom trigger above -- so the client seals it
        # and nothing ever opens it. The start spoke (Limgrave) sealed = the seed is unplayable from
        # turn one. Emit an ALWAYS-OPEN trigger -- one empty clause, which natural_key_fired
        # satisfies vacuously (all() over [] is true) and blooms on the first client tick -- for every
        # KEPT region that HAS an open flag but NO trigger yet. This covers the flattened off-START
        # spokes (Limgrave, Weeping), any degraded gate (all clauses dropped / a count set with
        # fewer than N pooled members), and the capital when it is not kept (dlc_only -- no wall
        # to bloom). Regions with a real clause or count trigger above are skipped by the
        # `name not in triggers` guard -- Caelid and the armed capital no longer fall through
        # to always-open.
        for region in world._kept():
            if REGION_OPEN_FLAGS.get(region) is None:
                continue
            name = f"{region} Lock"
            if name not in triggers:
                triggers[name] = {"anyOf": [{"items": [], "flags": []}]}
        return {"naturalKeyTriggers": triggers} if triggers else {}
