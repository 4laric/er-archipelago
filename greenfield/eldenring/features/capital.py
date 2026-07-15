"""Capital-version reconciler (gen half) -- SPEC-capital-reconciler.md (repo root).

Leyndell ships as TWO mutually exclusive map versions selected by ONE save-persisted event flag,
9116 (sole vanilla setter: Maliketh's death, m13_00_00_00.emevd:409):

  * 9116 OFF -> Leyndell, Royal Capital (m11_00, measured play_region bucket 11000): Morgott +
    ~152 checks.
  * 9116 ON  -> Leyndell, Ashen Capital (m11_05, bucket 11050) + the Elden Throne (m19_00,
    bucket 19000): THE FINALE (Gideon 510060, Godfrey 510070, Elden Beast 510230, +7 map lots).

Vanilla only ever SETS the flag, so the swap is one-way: in region-lock play the Farum Azula Lock
lets the player kill Maliketh before clearing Royal, and the finale goal sits PAST the burn -- on
every finale seed the burn permanently strands the Royal checks. Pure-runtime means 9116 is ours
to write: the CLIENT keeps it matched to where the player actually is (or is warping to) --
warp-target intercept + per-tick latch, both pure er-logic (crates/er-logic/src/capital.rs,
host-tested by capital_replay.rs), both gated on burn-done flag 118 (common.emevd $Event(900)'s
completion latch) so the first burn stays 100% the game's own sequence.

THE FILL PAYOFF (why this feature also touches classification): because the reconciler restores
the Royal Capital, it is NEVER permanently lost -- so the ERDTREE_BURN_APS "may not carry
progression" bar (core._add_locations item_rule + the progression-surface exclusion) is LIFTED
while this option is on. No new constraint replaces it: Royal may carry progression, and Farum is
NOT gated on Morgott. Both mitigations exist only to protect a strand the reconciler ends. With
the option OFF the bar snaps back -- that is the one-flag disable.

ASSUMPTION (UNVERIFIED -- the reason the option exists): toggling 9116 at will has no bad side
effects (NPC/quest states keyed on it re-evaluate benignly; unsetting it after the finale does
not break the ending). Alaric is deferring the CE probe; until it runs, this ships default-ON
with the blast radius contained (client writes only post-burn, only to MATCH the player's
current/target capital) and `capital_reconciler: false` as the kill switch. SPEC-capital-
reconciler.md carries the probe checklist; IN-GAME-VALIDATION carries the debt line.

slot_data (all five contract-declared, emitted only while the option is ON; absent keys = the
client logs "capital reconciler INERT" and never touches 9116):
  capitalBurnFlag / capitalBurnDoneFlag -- 9116 / 118 (generated data.py values once gen_data
    re-runs; pinned fallbacks below until then, same values, provenance cited).
  capitalAshenPlayRegions / capitalRoyalPlayRegions -- the partition of Leyndell's MEASURED
    play_region buckets (generated region_play_ids.py -- the KICK id space) by the map each
    bucket encodes: 1100x -> m11_00 Royal, 1105x -> m11_05 Ashen, 19xxx -> m19 Throne. The
    partition HARD-FAILS generation on a bucket neither side claims (a future regen adding an
    m11 bucket must be classified consciously, not defaulted).
  capitalReleaseRows -- [row, from, to] ShopLineupParam release-flag re-keys: the rows whose
    eventFlag_forRelease is 9116 ITSELF (Enia's Maliketh armor set) re-key to 118, or the
    reconciler's OFF-default would keep those four checks off the shelf forever.
"""
from Options import DefaultOnToggle

from ..registry import Feature, register
from .. import contract

try:
    from ..region_play_ids import REGION_PLAY_IDS
except Exception:  # pragma: no cover -- pre-regen data
    REGION_PLAY_IDS = {}

# Generated values (gen_data.py emits these into data.py from the same $Event(900) scan that
# derives the finale; see gen_data "capital reconciler" block). Fallbacks below until the next
# Windows regen -- same numbers, provenance cited, and test_gf_capital_reconciler pins them equal
# once data.py carries them (a redundant fallback that DRIFTS must fail, not linger).
try:
    from ..data import CAPITAL_BURN_FLAG as _GEN_BURN_FLAG
    from ..data import CAPITAL_BURN_DONE_FLAG as _GEN_BURN_DONE_FLAG
    from ..data import CAPITAL_RELEASE_ROWS as _GEN_RELEASE_ROWS
except Exception:
    _GEN_BURN_FLAG = _GEN_BURN_DONE_FLAG = _GEN_RELEASE_ROWS = None

# Pinned ground truth (2026-07-14, elden_ring_artifacts):
#   9116 -- m13_00_00_00.emevd:409 `SetEventFlagID(9116, ON)` (Maliketh dead; the only setter in
#          all 589 EMEVD) and the one flag common.emevd $Event(900) waits on before the burn.
#   118  -- $Event(900)'s own completion latch: entry `GotoIf(L1, !EventFlag(118))` + final step
#          `SetEventFlagID(118, ON)`. Monotonic -- nothing in any EMEVD clears it.
#   Release rows -- every ShopLineupParam row with eventFlag_forRelease == 9116 whose stock flag
#          is a live shop check: 101516/101517/101518/101519 (stock 250160/250170/250180/250190 =
#          "Roundtable Hold :: Maliketh's Helm/Armor/Gauntlets/Greaves", checks 7770500-7770503).
#          Row 101785 also releases on 9116 but its stock flag 270850 is the quarantined
#          mausoleum-remembrance-dupe non-check -> excluded.
_FALLBACK_BURN_FLAG = 9116
_FALLBACK_BURN_DONE_FLAG = 118
_FALLBACK_RELEASE_ROWS = ((101516, 9116, 118), (101517, 9116, 118),
                          (101518, 9116, 118), (101519, 9116, 118))

BURN_FLAG = _GEN_BURN_FLAG or _FALLBACK_BURN_FLAG
BURN_DONE_FLAG = _GEN_BURN_DONE_FLAG or _FALLBACK_BURN_DONE_FLAG
RELEASE_ROWS = tuple(tuple(r) for r in (_GEN_RELEASE_ROWS or _FALLBACK_RELEASE_ROWS))

# The region that owns ALL capital play buckets (region_play_ids.py; the finale maps' kick
# geometry rides Leyndell -- see features/finale.py).
_CAPITAL_REGION = "Leyndell"


def capital_partition(play_ids=None):
    """(royal, ashen) partition of Leyndell's measured play_region buckets, by the map each
    bucket encodes (bucket = area*1000 + block*10, verified: 11000=m11_00, 11050=m11_05,
    19000=m19_00 match both region_groups.py and every capital BonfireWarpParam row).

    HARD-FAILS (ContractError -> gen dies) on an unclaimed bucket or an empty side: a partition
    that silently dropped a bucket would leave the client's latch permissive exactly there --
    the play-region bucket-table lesson (CONTRIBUTING: a derivation that cannot answer must
    FAIL, not answer)."""
    ids = REGION_PLAY_IDS.get(_CAPITAL_REGION, ()) if play_ids is None else play_ids
    royal = sorted(b for b in ids if b // 10 == 1100)
    ashen = sorted(b for b in ids if b // 10 == 1105 or b // 1000 == 19)
    leftover = sorted(set(ids) - set(royal) - set(ashen))
    if leftover or not royal or not ashen:
        raise contract.ContractError(
            f"capital: cannot partition {_CAPITAL_REGION} play buckets {sorted(ids)} into "
            f"Royal/Ashen (royal={royal}, ashen={ashen}, unclaimed={leftover}) -- classify the "
            f"new bucket in features/capital.py before shipping the reconciler")
    return royal, ashen


class CapitalReconciler(DefaultOnToggle):
    """Keep the Leyndell map-version flag (9116) matched to where you actually are, so burning
    the Erdtree never permanently strands the Royal Capital's checks: warp to a Royal grace (or
    walk in from Altus) and the Royal Capital is back; warp to an Ashen grace and the finale is
    where you left it. Also lets Royal Capital checks carry progression. Default on.

    Turn OFF if the capital flag toggle misbehaves in-game (the toggle is assumed side-effect
    free but not yet probe-verified): off restores vanilla one-way behavior AND re-bars the
    Royal Capital from progression, so seeds stay winnable either way."""
    display_name = "Capital Version Reconciler"


@register
class Capital(Feature):
    name = "capital"
    OPTIONS = {"capital_reconciler": CapitalReconciler}

    def generate_early(self, world) -> None:
        opt = getattr(world.options, "capital_reconciler", None)
        world.gf_capital_reconciler = bool(opt.value) if opt is not None else False
        if world.gf_capital_reconciler and not REGION_PLAY_IDS.get(_CAPITAL_REGION):
            # No measured capital geometry (pre-regen data): the client latch would have nothing
            # to hold. Fail closed to vanilla behavior -- and SAY so (armed or why not).
            world.gf_capital_reconciler = False
            import logging
            logging.getLogger("Greenfield").warning(
                "[eldenring:%s] capital reconciler INERT: no %s entry in region_play_ids.py",
                world.player, _CAPITAL_REGION)

    def slot_data(self, world):
        if not getattr(world, "gf_capital_reconciler", False):
            return {}  # absent keys ARE the off-wire: the client logs INERT and never writes 9116
        royal, ashen = capital_partition()
        return {
            contract.CAPITAL_BURN_FLAG: int(BURN_FLAG),
            contract.CAPITAL_BURN_DONE_FLAG: int(BURN_DONE_FLAG),
            contract.CAPITAL_ASHEN_PLAY_REGIONS: [int(b) for b in ashen],
            contract.CAPITAL_ROYAL_PLAY_REGIONS: [int(b) for b in royal],
            contract.CAPITAL_RELEASE_ROWS: [[int(a), int(b), int(c)] for (a, b, c) in RELEASE_ROWS],
        }
