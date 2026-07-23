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
  * Capital   <- Altus (graph parent, REGION_PARENT) AND 2 Great Runes (count gate; leyndell_gate owns
                 the rune half). NB Altus IS a Leyndell prerequisite (Alaric 2026-07-23 -- this
                 SUPERSEDES the committed spec S2 "Altus prereq DROPPED" line; update the spec).

TWO NEW PRIMITIVES (spec S2): the COUNT-gate (open on N-of-a-set) and the COMPOUND-gate (items AND
world flags). v0.1 DRAFT scope: single-item + OR + compound-of-items gates are wired end-to-end
(logic entrance rule + client naturalKeyTriggers). The COUNT-gate is LOGIC-ONLY this pass -- a count
over a large set is not expressible as naturalKeyTriggers anyOf-subsets and wants a real client count
primitive (a genuine follow-up). Leyndell's 2-Great-Rune gate is the game's OWN native capital gate
(the vanilla main gate opens on 2 held runes; leyndell_gate carries the AP-logic mirror), so it needs
no client trigger from us.

OPEN QUESTIONS carried from spec S5 (need Alaric's datamine / an in-game oracle) -- marked below:
  * Pureblood Knight's Medallion is NOT a shuffled catalog item -> Mohgwyn uses the Secret-Medallion x2
    route only this pass (the DAG's other Mohgwyn route).
  * "Messmer's Kindling" is a vanilla CONCEPT with no catalog item -> Enir-Ilim gates on Shadow-Keep
    access only; the Kindling + K-Scadutree-Fragment count is DEFERRED (K undefined; needs the client
    count primitive too).
  * "Jori's remembrance" has no catalog item -> Abyssal Woods gates on DLC entry only.
  * Caelid's "2 remembrances" count collides with the festival-softlock flag 9410 (spec S5) -> the gate
    is LOGIC-ONLY here (no client trigger), so nothing touches 9410; reconcile before wiring the client.

Pure-ish module: imports Options/registry/data/region_spine/item_ids only (never core -> no cycle), so
its pure helpers unit-test without a live world.
"""
from itertools import combinations

from Options import Toggle
from ..registry import Feature, register

try:
    from ..data import REGIONS, LOCATIONS
except Exception:  # pragma: no cover -- pre-regen data
    REGIONS, LOCATIONS = [], {}
try:
    from ..item_ids import ITEM_CATALOG, LOCATION_ITEM
except Exception:
    ITEM_CATALOG, LOCATION_ITEM = {}, {}
try:
    from ..region_open_flags import REGION_OPEN_FLAGS
except Exception:
    REGION_OPEN_FLAGS = {}

# Great Runes + Remembrances read from the catalog (matt-free, same rule as core.GREAT_RUNES).
GREAT_RUNES = frozenset(n for n in ITEM_CATALOG if n.endswith("Great Rune"))
REMEMBRANCES = frozenset(n for n in ITEM_CATALOG
                         if n.startswith("Remembrance of") or n.startswith("Remembrance "))

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
    "Haligtree": [("Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)")],
    # Underworld / Eternal Cities bloc (spec S3 "Underworld (whole bloc)"): Rem. of the Starscourge.
    "Siofra River": [("Remembrance of the Starscourge",)],
    "Ainsel River": [("Remembrance of the Starscourge",)],
    "Deeproot Depths": [("Remembrance of the Starscourge",)],
    # Mohgwyn: Pureblood Knight's Medallion is NOT a catalog item (spec S5 open q) -> Secret-Medallion
    # x2 route only (also the Snowfield-portal route in the DAG). Re-add a Pureblood clause here once
    # that item is confirmed pooled.
    "Mohgwyn": [("Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)")],
    "Farum Azula": [("Remembrance of the Fire Giant",)],
    # --- DLC fold bloc: everything behind Mohg / Blood Lord remembrance (kept chokepoint) ---
    "Gravesite": [("Remembrance of the Blood Lord",)],
    "Ensis": [("Remembrance of the Blood Lord",)],
    "Cerulean": [("Remembrance of the Blood Lord",)],
    "Charo's": [("Remembrance of the Blood Lord",)],
    "Belurat": [("Remembrance of the Blood Lord",)],
    "Stone Coffin": [("Remembrance of the Blood Lord",)],
    # --- DLC gated-deeper regions (each = DLC entry AND its own token) ---
    "Scadu Altus": [("Remembrance of the Blood Lord", "Remembrance of the Twin Moon Knight")],
    "Shadow Keep": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
    # kept chokepoint: Rauh behind Shadow Keep -> Shadow Keep's clause. (Rauh Base + Ancient Ruins are
    # merged per spec S2; both carry the Shadow-Keep clause.)
    "Ancient Ruins": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
    "Rauh Base": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
    "Jagged Peak": [("Remembrance of the Blood Lord", "Dragon-Hunter's Great Katana")],
    # Abyssal Woods: "Jori's remembrance" has no catalog item (spec S5) -> DLC entry only this pass.
    "Abyssal": [("Remembrance of the Blood Lord",)],
    # Enir-Ilim finale: spec wants Messmer's Kindling + K Scadutree Fragments; Kindling is a vanilla
    # concept with no catalog item and K is undefined (spec S5) -> gate on Shadow-Keep access for now.
    "Enir Ilim": [("Remembrance of the Blood Lord", "Aspects of the Crucible: Thorns")],
}

# COUNT-gates (open on N of a named set). LOGIC-ONLY this pass (see docstring). region -> (set, N).
COUNT_GATES = {
    "Caelid": (REMEMBRANCES, 2),   # spec S3 "2 remembrances"; festival flag 9410 reconcile deferred (S5)
}

# Regions whose opening is the GAME's own native gate -> no clause of ours, no client trigger. Leyndell
# = 2 Great Runes (leyndell_gate owns the rune logic + the vanilla capital gate opens in-game on held
# runes); Sewer rides the capital as Leyndell's child.
GAME_NATIVE_GATE = frozenset({"Leyndell", "Sewer"})

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
    (start regions / spokes / degraded gates / the game-native capital, whose rune logic leyndell_gate
    ANDs onto the edge separately)."""
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


@register
class NaturalProgressionFeature(Feature):
    name = "natural_progression"
    OPTIONS = {"natural_progression": NaturalProgression}

    def generate_early(self, world) -> None:
        # Publish the progression key set for core._class_for (empty when the mode is off -> inert).
        world.gf_natural_keys = key_items(world) if is_on(world) else []
        if is_on(world):
            import logging
            degraded = sorted(r for r in GATE_CLAUSES
                              if r in set(world._kept()) and r not in active_clauses(world))
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] natural_progression: %d region gate(s) active, %d key item(s) "
                "marked progression%s",
                world.player, len(active_clauses(world)), len(world.gf_natural_keys),
                (" -- DEGRADED-to-open (unavailable keys): " + ", ".join(degraded)) if degraded else "")

    def set_rules(self, world) -> None:
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
        # Count-gates (logic-only) and the game-native capital emit nothing here (documented).
        if not is_on(world):
            return {}
        triggers = {}
        for region, clauses in active_clauses(world).items():
            if REGION_OPEN_FLAGS.get(region) is None:
                continue  # no apparatus to bloom (client tick_natural_key_triggers would skip it)
            triggers[f"{region} Lock"] = {
                "anyOf": [{"items": list(c), "flags": []} for c in clauses]
            }
        return {"naturalKeyTriggers": triggers} if triggers else {}
