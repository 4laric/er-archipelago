"""SPEC-goal-send -- goalLocations slot_data (Track C).

The client (from-software-archipelago-clients goal.rs) ships a Goal-send handler that reads a
`goalLocations` list of AP location ids and sends ClientStatus::Goal once EVERY id is done. An id
that also appears in `locationFlags` is detected LOCAL-FIRST by its guarding vanilla event flag
(boss DefeatFlag) -- immune to another slot's `!collect` and reload-safe; any id missing from the
detection table falls back to the server-truth checked set. An EMPTY `goalLocations` can never be
met, which is the bug in the connect log ("goalLocations empty -- this slot can NEVER send Goal").

THE GOAL IS THE GAME'S REAL TERMINUS WHEN IT EXISTS, ELSE THE TERMINAL REGION OF THE CHAIN --
never a hardcoded region.

Tier 0, THE FINALE (ruling 2026-07-14): when the conditional finale region exists this seed --
data.FINALE_REGION ('Ashen Capital'), created by features/finale.py iff every FINALE_REQUIRES
region (Farum Azula + Leyndell) is kept -- its major bosses ARE the goal: Godfrey/Hoarah Loux
(f510070) and the Elden Beast (f510230), the game's actual final bosses, now real locations in
data.py/boss_data.py (REGION_BOSSES['Ashen Capital']). The Ashen Capital is the game's real
terminus even though Farum Azula outranks Leyndell in SPINE, so tier 0 outranks the spine walk.
When the finale is not active, the ladder below decides, exactly as before.

(History, both bugs guarded by test_gf_goal_terminal: the predecessor preferred GOAL_REGION
whenever kept, and GOAL_REGION (Leyndell) is ALWAYS kept on a base seed, so every base seed's goal
collapsed to Morgott and the client sent Goal the moment he died -- the 2026-07-14 playtest bug.
An older docstring promised Hoarah Loux and the Elden Beast as goal locations while neither was a
location at all; as of the finale revival that promise is finally TRUE, and conditional.)

EXPLICIT CHOICE (option `goal`, 2026-07-30). Everything below describes `goal: auto`, which is
the default and is unchanged. When the player NAMES a goal, GOAL_CHOICES pins the terminal region
outright and core force-keeps that region's prerequisites through compute_kept(forced=...), so the
chosen goal is reachable BY CONSTRUCTION rather than by fallback -- there is no silent degradation
to the ladder, which is the "I set my goal and the game ignored it" failure this project has been
burned by. Most choices clear all majors in that region; a boss-specific choice may pin an exact
check (`malenia` is only f510200, not Loretta). An explicit choice OUTRANKS tier 0: a named goal on
a seed that also keeps Farum Azula + Leyndell still goals on its named boss, and the Ashen Capital's
ten checks remain ordinary locations (features/finale.py creates the region on its own
prerequisites, never on the goal). The consequence, stated plainly because this docstring has lied
before: with an explicit choice the goal ids are NOT necessarily in the deepest kept region by
SPINE rank -- that invariant holds for `auto` only.

Resolution ladder (each tier total, deterministic, and derived -- no hand list):
  0. THE FINALE's major bosses, iff features/finale.py created the finale region this seed.
  0b. THE DLC'S TERMINUS -- Enir Ilim's majors (Promised Consort Radahn), iff the base game is NOT
     in play. Mutually exclusive with tier 0. Core force-keeps Enir Ilim on those seeds and bars it
     from the draw, so this tier is a guarantee rather than a preference: added 2026-08-09 after a
     dlc_only seed ended on Romina because the draw never took Enir Ilim. See DLC_TERMINUS_REGION.
  1. MAJOR BOSSES OF THE DEEPEST TERMINAL KEPT REGION -- terminal meaning one of its majors is
     tagged LegacyBoss, Remembrance or GreatRune (see _is_terminus), so an optional FieldBoss like
     Bayle can never end a run. Walks those deepest-first by SPINE rank, then the plain walk. MajorBoss membership is LOCATION_TAGS (= REGION_BOSSES arena majors
     UNION the curated MAJOR_BOSS_EXTRAS field majors -- so a Sewer-terminal seed ends on Mohg the
     Omen, not on a shallower region's arena). The spine is a total order, so "the terminal
     regions" collapse to the single deepest region that has majors; ALL of its majors are the
     goal ("clear the terminal region").
  2. Degenerate (NO kept region has any major -- only reachable under dlc_only+rolled draws over
     the majorless DLC regions): every check of the deepest kept region EXCEPT missable-tagged
     ones -- literally "clear the terminal region", and achievable by construction because
     missables are the only checks a player can permanently lose.
  3. Still empty -> ContractError. A seed whose goal cannot name one achievable location is
     unwinnable and must die at generation, not at the connect log.

great_runes ending: the rune requirement rides `great_rune_items` (core._base_slot_data), which the
client's goal.rs reads; this feature does NOT emit it (merge_slot_data raises on duplicate top-level
keys).

goalRequiredItems -- ALIGNING THE TWO TERMINAL CONDITIONS (2026-07-30). core.set_rules tells
Archipelago the slot completes on `has_all(kept Region Locks)`, but goal.rs `is_met()` checked the
goal BOSS FLAGS ALONE, and the client's Goal-send is what actually ends the run. Because
region_access is warp, every kept region sits at sphere ~1 and fill may legitimately place the
terminal region's Lock in sphere 0: MEASURED over generated seeds, 25% of rolled draws made the goal
region the SECOND region opened, ending the run while the world still claimed every lock was
required. So this feature also emits `goalRequiredItems` = core.goal_required_lock_names() (the kept
locks minus the precollected start anchor), which goal.rs folds into its existing `item_goals`. Both
sides now read ONE list, single-sourced at core.kept_lock_names().
  * Emitted ONLY when there are locks to require. natural_progression mints NO Lock items -- its
    regionOpenFlags keys are "<Region> Lock" NAMES with nothing behind them, so requiring them would
    deadlock the seed; core.kept_lock_names() returns [] there and the key is omitted.
  * This does NOT change WHICH boss is the goal, and it does not move fill: the lock is still
    placed wherever fill wants it. The client just waits until the player holds it.

Invariants promised here and enforced by tests/test_gf_goal_terminal.py + test_gf_finale.py:
  * goalLocations is never empty;
  * when the finale is active, goalLocations is exactly the finale's MajorBoss set;
  * when the base game is sealed, goalLocations is exactly Enir Ilim's MajorBoss set -- on EVERY
    such seed, not on the ones whose draw happened to keep it;
  * under `goal: auto` (and only then) every goalLocations id lives in the DEEPEST kept region
    carrying them (never Leyndell-by-preference: a seed keeping a region deeper than Leyndell must
    not goal on Morgott); under an explicit choice they live in the CHOSEN region, which
    compute_kept(forced=...) guarantees is kept;
  * every id belongs to a location set that exists this seed (a kept region's, or the active
    finale region's);
  * goalRequiredItems, when present, is EXACTLY core.goal_required_lock_names() +
    core._required_ability_unlocks() -- the same two lists set_rules closes its has_all over (the
    locks minus the precollected anchor, plus the pooled Unlock items when ability_unlocks_required).
"""
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from ..registry import Feature, register
from . import vanilla_placement as _vp
from .. import contract
from ..region_spine import SPINE
from ..data import FINALE_REGION
from .finale import finale_active, base_game_in_play

try:
    from ..boss_data import REGION_BOSSES
except Exception:  # not yet generated
    REGION_BOSSES = {}
try:
    from ..data import LOCATIONS
except Exception:
    LOCATIONS = {}
try:
    from ..location_tags import LOCATION_TAGS
except Exception:
    LOCATION_TAGS = {}
try:
    from ..missable_locations import MISSABLE_LOCATIONS
except Exception:
    MISSABLE_LOCATIONS = {}

# Spine rank for ordering kept regions; regions off the spine sort last (defensive, never expected).
_SPINE_RANK = {r: i for i, r in enumerate(SPINE)}

# THE EXPLICIT GOAL TABLE. Most choices select a REGION and therefore clear all of that region's
# majors. A choice may instead pin one or more exact terminal checks when the player-facing choice
# names one boss in a region with several majors -- Malenia is the motivating case. Keeping that
# distinction in the table prevents a new boss-shaped choice from silently inheriting the old
# "clear the region" rule.
@dataclass(frozen=True)
class GoalChoiceSpec:
    region: str
    forced: Tuple[str, ...]
    location_ids: Tuple[int, ...] = ()
    entry_grace: Optional[int] = None


# Generated-data pins for #861. 7770662 is "Remembrance of the Rot Goddess - Malenia [f510200]"
# (was 7770762 until #1013's Enia-vanilla exclusion removed 100 shop checks and shifted every
# later AP id down by 100); 71506 is "Haligtree Canopy" in grace_flags.tsv. The remembrance's
# defeat flag is the canonical Malenia kill check; her Great Rune uses a separate synthetic flag
# and is not the terminal event.
MALENIA_REGION = "Haligtree"
MALENIA_GOAL_LOCATION = 7770662
MALENIA_ENTRY_GRACE = 71506


# One line per value. The values are NAMED for bosses because that is how players ask for them;
# 'elden_beast' resolves to the Ashen Capital's pair (Hoarah Loux is physically on the way -- the
# Elden Throne is behind his arena -- so the pair adds no detour).
# 🛑 `elden_beast` FORCES NOTHING as of 2026-08-06 (SPEC-ashen-capital-lock). It used to force-keep
# ('Farum Azula', 'Leyndell') because the burn was game data and only those two regions could reach
# it -- which is why `num_regions: 1` produced four regions. The Ashen Capital Lock made the finale
# reachable from the HUB on any base-game seed, so the forced set is empty and stays empty.
#
# ⚠️ An EMPTY forced set makes `core._resolve_goal_choice`'s `all(r in eligible for r in need)`
# check pass VACUOUSLY -- including under `dlc_only`, where the region it names cannot be built at
# all. core carries an explicit base-game test for exactly that; do not re-derive the guard from
# this tuple.
GOAL_CHOICES = {
    "elden_beast":      GoalChoiceSpec(FINALE_REGION, ()),
    "promised_consort": GoalChoiceSpec("Enir Ilim", ("Enir Ilim",)),
    "malenia":          GoalChoiceSpec(MALENIA_REGION, (MALENIA_REGION,),
                                        (MALENIA_GOAL_LOCATION,), MALENIA_ENTRY_GRACE),
}


# ⭐⭐⭐ THE DLC'S TERMINUS, and the asymmetry it closes (2026-08-09).
#
# The Ashen Capital is NOT in `data.REGIONS`. It is never drawn, never counted by num_regions, and
# features/finale.py builds it on every seed with the base game in play -- so `goal: auto` ends on
# the Elden Beast whatever the draw did. Enir Ilim had NO equivalent: it is one of the thirteen
# ordinary rollable DLC regions, so on a `dlc_only` seed Promised Consort Radahn was the ending BY
# LOTTERY. bobler finished one on Romina in the Ancient Ruins of Rauh on 2026-08-07 and reasonably
# read the early goal as a broken ending. Nothing had malfunctioned -- Romina carries a Remembrance
# and his draw never kept Enir Ilim -- the DLC simply never got the guarantee the base game has.
#
# So under dlc_only Enir Ilim now behaves like the Ashen Capital in the two ways that matter: it is
# NOT DRAWN (core bars it from the draw pool, so it never spends one of the player's N) and it is
# ALWAYS KEPT (force-appended). It stays UNLIKE the Ashen Capital in the one way that matters too --
# it remains a real region with its own checks and its own Lock, because it is a place you play,
# where the Ashen Capital is ten checks and a gauntlet (Alaric, 2026-08-06).
DLC_TERMINUS_REGION = "Enir Ilim"


def dlc_terminus_active(regions) -> bool:
    """Does this region pool end on the DLC's terminus?

    True exactly when Enir Ilim is in play and the base game is not -- the MIRROR of
    `finale.finale_active`, and mutually exclusive with it by construction, so tier 0 and tier 0b
    below can never both claim the goal. Reads the resolved pool rather than the `dlc_only` yaml for
    the same reason `base_game_in_play` does: a future scope option that empties the base game gets
    the right answer without anyone remembering to teach this predicate about it."""
    regions = list(regions)
    return DLC_TERMINUS_REGION in regions and not base_game_in_play(regions)


def auto_forced_regions(eligible) -> tuple:
    """What `goal: auto` force-keeps, given this seed's ELIGIBLE pool. Single-sourced here so core,
    the yaml validator and the tests cannot drift from it -- the same contract `forced_regions`
    holds for a NAMED goal.

    Base game in play -> NOTHING, and that emptiness is load-bearing: SPEC-ashen-capital-lock
    deleted the old GOAL_REGION force-keep precisely so `num_regions: 1` really keeps one region.
    dlc_only -> the DLC terminus, which is the guarantee the finale hands the base game for free by
    not being a rollable region at all."""
    return (DLC_TERMINUS_REGION,) if dlc_terminus_active(eligible) else ()


def forced_regions(chosen):
    """Regions core must force-keep for `chosen` (empty for auto / unknown). Single-sourced here so
    core, the yaml validator and the tests cannot drift from the table."""
    if not chosen or chosen == "auto":
        return ()
    spec = GOAL_CHOICES.get(chosen)
    return spec.forced if spec is not None else ()


def goal_region(chosen):
    """The explicitly selected terminal region, or None for auto / an unknown value."""
    spec = GOAL_CHOICES.get(chosen)
    return spec.region if spec is not None else None


def goal_entry_grace(chosen):
    """A named goal's required physical entry grace, if it overrides the normal region bundle."""
    spec = GOAL_CHOICES.get(chosen)
    return spec.entry_grace if spec is not None else None


def _major_boss_ids(region):
    """AP location ids of the MajorBoss-tagged checks in `region` (LOCATION_TAGS = REGION_BOSSES
    arena majors UNION MAJOR_BOSS_EXTRAS curated field majors). Falls back to the raw REGION_BOSSES
    arena entries if the tag table is unavailable (partial regen), so the goal never silently
    narrows to nothing on a data lag."""
    ids = [aid for (_name, aid, _flag) in LOCATIONS.get(region, ())
           if "MajorBoss" in LOCATION_TAGS.get(aid, ())]
    if ids:
        return sorted(ids)
    return sorted(aid for (aid, _flag, _name) in REGION_BOSSES.get(region, ()))


# A major that ENDS a run: a legacy-dungeon boss, or a demigod the game itself marks with a
# Remembrance or a Great Rune. Deliberately a UNION -- see _is_terminus.
_TERMINAL_TAGS = ("LegacyBoss", "Remembrance", "GreatRune")


def _by_depth(kept):
    """Kept regions, deepest spine rank first (stable for equal/off-spine ranks by name)."""
    return sorted(kept, key=lambda r: (-_SPINE_RANK.get(r, len(SPINE)), r))


def _is_terminus(region):
    """Does this region END a run? True when one of its MajorBoss checks also carries a terminal tag
    (LegacyBoss, Remembrance or GreatRune) -- i.e. it is NOT merely a FieldBoss standing outdoors.

    MOTIVATING CASE (rule 11, 2026-08-05). A player's DLC seed ended on BAYLE. Tier 1 read "deepest
    kept region by SPINE rank" as a proxy for "terminal", and the DLC breaks that proxy: Jagged Peak
    sits near the end of SPINE but Bayle is an optional dragon on a mountainside, and Rauh Base --
    deeper still -- ends the run on Rugalea, a bear. MEASURED over 3000 DLC seeds at num_regions=6,
    only 38% ended on an actual final boss; Bayle took 10.9% and Rugalea 9.3%.

    WHY A UNION, stated because I tried both halves alone and each is wrong:

      * Remembrance/GreatRune ALONE demotes the Sewer, whose major is Mohg the Omen and whose drop is
        an incantation -- but the Shunning-Grounds are a legacy dungeon that should be able to end a
        run, and test_deeper_kept_region_beats_leyndell says exactly that. It also promoted the
        capital over a deeper Sewer (Morgott carries a Great Rune), walking back into the 2026-07-14
        playtest bug where the goal is a boss who may already be dead when the lock arrives.
      * LegacyBoss ALONE demotes Astel, Fortissax and the Fire Giant -- Remembrance demigods who do
        not stand at the end of a legacy dungeon.

    Their union is exactly the set of bosses a run can credibly end on, and it needs no exception for
    GOAL_REGION: Morgott qualifies, so the capital wins when it is genuinely the deepest thing kept
    and loses to a deeper Sewer. Both goal_terminal tests state those two halves independently.

    It also excludes the curated MAJOR_BOSS_EXTRAS, which exist to give a region a PROGRESSION
    SURFACE rather than an ending -- Agheel, Makar, Leonine, Godefroy, Blackgaol are FieldBoss or
    plain Boss. A future region earns terminus status the moment its major gains one of these tags.

    MEASURED after this change: ZERO seeds end on a FieldBoss-only region, base-only or DLC."""
    return any(any(t in LOCATION_TAGS.get(aid, ()) for t in _TERMINAL_TAGS)
               for (_name, aid, _flag) in LOCATIONS.get(region, ())
               if "MajorBoss" in LOCATION_TAGS.get(aid, ()))


def terminal_goal_ids(kept, chosen=None, finale_built=None, dlc_terminus=None):
    """(region, ids) for the goal: tier 0 = the finale's majors iff the finale exists for `kept`
    (see module docstring); tier 1 = majors of the deepest kept region that has any; tier 2 = the
    deepest kept region's non-missable checks. ids may be empty only if tier 2 is too (caller
    raises).

    `chosen` is the explicit `goal` option value; when it names a GOAL_CHOICES entry it PINS the
    region and returns before the ladder runs -- outranking tier 0. A boss-specific choice returns
    only its pinned checks and NEVER falls through to a different ending if one goes stale. A
    region-wide choice with empty majors falls through to the ladder (defensive against a partial
    regen), and a wholly empty result still reaches the caller's ContractError."""
    if chosen and chosen != "auto" and chosen in GOAL_CHOICES:
        spec = GOAL_CHOICES[chosen]
        region = spec.region
        if spec.location_ids:
            available = {aid for (_name, aid, _flag) in LOCATIONS.get(region, ())}
            if all(aid in available for aid in spec.location_ids):
                return region, sorted(spec.location_ids)
            return region, []
        ids = _major_boss_ids(region)
        if ids:
            return region, ids
    # `finale_built` is the world's own answer (`world.gf_finale_active`) and OUTRANKS the static
    # re-derivation: features/finale.py decides existence from the seed's ELIGIBLE pool, not from
    # the draw, so re-asking here with `kept` could disagree on a base-game seed whose draw happened
    # to take only DLC regions -- two answers to one question, which is how tier 0 and the emitted
    # region drift apart. The static path stays for the callers that have no world (tests, the yaml
    # validator).
    if finale_built if finale_built is not None else finale_active(kept):
        ids = _major_boss_ids(FINALE_REGION)
        if ids:                       # defensive: a finale with no majors falls to the spine walk
            return FINALE_REGION, ids
    # TIER 0b, THE DLC'S TERMINUS -- the mirror of tier 0, and MUTUALLY EXCLUSIVE with it:
    # `dlc_terminus_active` is false the moment any base region is in play, so the two can never
    # contend for the same seed. Core force-keeps Enir Ilim on every dlc_only seed and the goal
    # NAMES it here rather than trusting it to win the spine walk below. It would win that walk
    # today -- it is SPINE-last -- and it would silently stop winning the day a deeper DLC region is
    # added. An ending that depends on a sort order is the same bug class as an ending that depends
    # on a draw, which is what this whole tier exists to retire.
    #
    # `dlc_terminus` is the world's own answer (`world.gf_dlc_terminus`) and OUTRANKS the static
    # re-derivation for exactly the reason spelled out above tier 0: core decides from the ELIGIBLE
    # pool, not from the draw, and re-asking here with `kept` can disagree. The static path stays
    # for the callers that have no world (tests, the yaml validator).
    if dlc_terminus if dlc_terminus is not None else dlc_terminus_active(kept):
        ids = _major_boss_ids(DLC_TERMINUS_REGION)
        if ids:                       # defensive: fall through to the spine walk, never to nothing
            return DLC_TERMINUS_REGION, ids
    # Tier 1, TERMINUS-FIRST: walk the terminus-bearing regions deepest-first, then everything else
    # deepest-first. The second pass is the pre-2026-08-05 behaviour and still guards draws where
    # nothing kept has a terminal major, so this narrows WHICH region ends the run without ever
    # narrowing the result to nothing.
    ordered = _by_depth(kept)
    for region in [r for r in ordered if _is_terminus(r)] + ordered:
        ids = _major_boss_ids(region)
        if ids:
            return region, ids
    terminal = ordered[0] if ordered else None
    if terminal is None:
        return None, []
    ids = sorted(aid for (_name, aid, _flag) in LOCATIONS.get(terminal, ())
                 if aid not in MISSABLE_LOCATIONS)
    return terminal, ids


@register
class GoalLocations(Feature):
    name = "goal_locations"

    def slot_data(self, world):
        kept = list(world._kept())
        region, ids = terminal_goal_ids(
            kept, getattr(world, "gf_goal_choice", None),
            finale_built=getattr(world, "gf_finale_active", None),
            dlc_terminus=getattr(world, "gf_dlc_terminus", None))
        if not ids:
            raise contract.ContractError(
                "goal_locations: no achievable goal location exists in the kept set %r -- the seed "
                "would be unwinnable (goalLocations may never be empty)" % (sorted(kept),))
        out = {contract.GOAL_LOCATIONS: sorted(ids)}
        # goalRequiredItems = held Region Locks PLUS required ability unlocks (#980 follow-up). Both
        # halves are single-sourced -- locks at core.kept_lock_names, unlocks at
        # core._required_ability_unlocks -- and core.set_rules closes the same two lists into the
        # completion_condition, so the client Goal gate and AP's terminal condition stay identical.
        required = list(world.goal_required_lock_names()) + list(world._required_ability_unlocks())
        if required:
            out[contract.GOAL_REQUIRED_ITEMS] = sorted(required)
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] goal = %s (%d location(s)) AND %d held Region Lock(s)",
                world.player, region, len(ids), len(required))
        else:
            policy = getattr(world.options, "goal_region_unlock_policy", None)
            policy_name = getattr(policy, "current_key", "items_held")
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] goal = %s (%d location(s)); no held-item requirement "
                "(goal-region policy: %s)", world.player, region, len(ids), policy_name)
        return out
