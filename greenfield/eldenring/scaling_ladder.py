"""The enemy-scaling tier ladder, and the ONE conversion that makes the difficulty floor mean what
it says. AP-free and dependency-free on purpose: `tests/test_gf_scaling_ladder_mirror.py` runs it
standalone from the source tree, against the client's Rust source, without an Archipelago install.

WHY THIS MODULE EXISTS -- the units bug (found 2026-07-27, latent since 2026-07-06)

`completion_scaling_floor` is the difficulty FLOOR: the minimum enemy-scaling tier, applied
everywhere from the start. The world and the client disagreed about its units, and nothing said so:

    world   a Range documented as "a percent of max"; core._options_echo emitted the raw int
    client  er-logic/scaling.rs:225 `floor_tier_from_multiplier` -- the FIRST tier whose
            `hp >= value`. An HP MULTIPLIER, over a ladder that tops out at 3.703.

Every value above 3 therefore selected the TOP tier: 46 of the old Range(0..50)'s 51 settings
collapsed to one outcome, and `completion_scaling_floor: 25` -- the obvious reading -- would have
pinned every enemy in the game to 3.70x HP from the moment the player left Roundtable. Not a crash;
an inversion of the knob's meaning. It never reached a player only because the option was frozen at
0 in `defaults.FROZEN_OPTIONS`, so the value never left gen.

`docs/history/RECON-tracker-scaling-20260706.md` line 171 diagnosed this exactly, and prescribed the
conversion below as item 3 of five. The other four shipped. Item 3 did not, and nothing was watching.

CONSTRAINT OWNERSHIP (CONTRIBUTING): the multiplier semantics are the CLIENT's -- a shipped, released
binary that validates this contract on connect. Gen converts because gen is the side that can. The
percent-facing option is OURS and could be redesigned; the multiplier on the wire cannot, not without
a client release and a compatibility story for every seed already rolled.
"""

# Mirror of `er-logic/src/scaling.rs::SCALING_TIERS` -- the vanilla `SpEffectParam` rows 7010..7100
# the client applies to an enemy, ascending. Only the HP rate is mirrored: it is the key the client's
# `floor_tier_from_multiplier` searches on, so it is the only column gen needs to speak.
#
# 🛑 CROSS-REPO DUPLICATED CONSTANT. Kept honest by `tests/test_gf_scaling_ladder_mirror.py`, which
# parses the Rust source and fails on divergence. Without that gate this tuple is folklore with
# syntax highlighting (CONTRIBUTING rule 10) and a drifted rung would move every player's difficulty
# floor by a tier with nothing to say so.
#
# PROVENANCE: DERIVED from `SpEffectParam.csv`, which joined `gen_inputs.db` on 2026-07-27
# (tools/gen_inputs.py PARAM_CSVS). Rungs `7010..7200`, 20 of them, strictly ascending.
#
# EXTENDED 2026-07-27, from the subset `7010..7100` (top rung 3.703x) to the full run (7.422x). The
# Rust comment had said for months that the ladder continued to ~7.4x and to "extend toward 7200 for
# a harsher curve"; it was right, and nothing could check it until the param was in the bundle. The
# first ten rungs came back byte-identical to the hand-transcribed values, so that transcription was
# correct -- but it was correct by luck, not by construction, which is what the drift gate fixes.
#
# ⚠️ This DOUBLED the deepest region's enemy HP and raised every mid-run tier with it. Deliberate
# (Alaric, 2026-07-27): the ceiling is fixed at 7.422x and `completion_scaling_ramp` chooses how fast
# a seed climbs to it.
SCALING_HP_LADDER = (1.141, 1.281, 1.656, 1.813, 1.953, 2.266, 2.406, 2.688, 3.25, 3.703,
                     4.125, 4.844, 5.484, 6.563, 6.688, 6.875, 7.047, 7.203, 7.328, 7.422)

# 🛑 THE CEILING IS NOT GEN-SIDE. The client normalizes every emitted target by the MAX EMITTED
# TARGET (`scaling.rs tier_for_target`), so scaling the wire up is a literal no-op -- the deepest
# region always lands on the last rung whatever numbers gen sends. The ceiling is this ladder, and it
# lives in the client. What gen CAN choose is how fast a seed climbs to it: see `ramped_target`.


def tier_for_floor_multiplier(mult):
    """MIRROR of er-logic `floor_tier_from_multiplier`: the FIRST rung at least this strong.

    Gen has no business re-deriving what the client computes -- but for TELEMETRY it must, because a
    log line that reports the option value instead of the resolved tier reports the one number a bug
    would leave looking correct. Both mirrors are pinned against the Rust source by
    tests/test_gf_scaling_ladder_mirror.py, which is what keeps this from becoming folklore."""
    for i, hp in enumerate(SCALING_HP_LADDER):
        if hp >= mult:
            return i
    return len(SCALING_HP_LADDER) - 1


def tier_for_ceiling_multiplier(mult):
    """MIRROR of er-logic `ceiling_tier_from_multiplier`: the LAST rung no stronger than this.
    Deliberately the opposite search from `tier_for_floor_multiplier` -- see ceiling_multiplier."""
    hits = [i for i, hp in enumerate(SCALING_HP_LADDER) if hp <= mult]
    return hits[-1] if hits else 0


def ceiling_multiplier(pct):
    """`maximum_enemy_difficulty` PERCENT (0..100) -> the HP MULTIPLIER capping the scaling tier.

    The MIRROR of `floor_multiplier`, and deliberately not a reuse of it. A floor asks "the first
    rung at least this strong"; a ceiling asks "the last rung no stronger than this". Same ladder,
    opposite search, and conflating them would cap one rung high.

    100 (the default) returns the top rung, i.e. no cap -- the client's `ceiling_tier_from_multiplier`
    maps it to the last tier, which is what `tier_for_target` already clamps to. So a default seed's
    behaviour is unchanged, and the key is emitted regardless (a constant, like the rest of the
    options echo) rather than appearing and disappearing.
    """
    pct = max(0, min(100, int(pct)))
    return SCALING_HP_LADDER[round(pct / 100 * (len(SCALING_HP_LADDER) - 1))]


# `maximum_enemy_difficulty: auto` -- the DEFAULT. Not a percent, and deliberately outside 0..100 so
# it can never be mistaken for one.
AUTO_CEILING = -1


def auto_ceiling_pct(num_regions, total_regions):
    """`auto` -> the `maximum_enemy_difficulty` PERCENT for a seed of this size.

    WHY AT ALL. The scaling target is a region's POSITION in the seed's unlock order, normalized so
    the deepest kept region reaches the top. That is RELATIVE; player power is ABSOLUTE (Somber +10
    needs a Somber [9], a fixed rung). So a 5-region seed reaches "the end of the run" in 2-3 hours
    against endgame-strength enemies with mid-game gear, and fewer regions makes the ramp STEEPER --
    backwards for a short seed. This lowers the top of the curve with the length of the run.

    THE CURVE, and where its single calibration point comes from. Alaric playtested the pre-2026-07-27
    ladder, which topped out at 3.703x, and at num_regions 5 that "felt pretty close, if it was a bit
    harder we get there". The DLC rungs were then found and the ladder grew from 10 rungs to 20
    (top 7.422x). So, a cube root in LADDER-INDEX space:

        pct = round(100 * (n / total) ** (1/3))

    n=5 of 30 -> 55% -> rung 10 -> 4.125x: his datum plus exactly one rung, which is what "a bit
    harder" asked for. n=total -> 100% -> the top rung, so a FULL map is unchanged from before.

    🛑 INDEX SPACE, NOT MULTIPLIER SPACE, and that is not a preference. `ceiling_multiplier` is
    `LADDER[round(pct/100 * (N-1))]`, and the client's search takes the last rung NO STRONGER than
    the value. Target 4.084x -- the multiplier-space answer for n=5 -- therefore resolves DOWN to rung
    9, which is 3.703x, the old cap. That version of this function would have shipped a change that
    did nothing whatsoever and looked correct in review.

    ⚠️ ONE PLAYTESTED POINT. Only ~3.7x at 5 regions has actually been played; everything above is
    extrapolation over rungs nobody has fought. Note also that the ladder's top 7 rungs
    (6.563..7.422) sit within 13% of each other, so up there the curve moves the NUMBER more than it
    moves the fight.

    num_regions 0 means ALL regions (core.NumRegions: "0 = all regions (full Shattering)"), NOT zero
    -- read as zero this would return pct 0 and cap every enemy at the bottom rung, making the
    DEFAULT seed trivial. Hence an explicit branch instead of arithmetic on the raw value.
    """
    total = int(total_regions)
    if total <= 0:
        raise ValueError("total_regions must be positive; got %r" % (total_regions,))
    n = int(num_regions)
    n = total if n <= 0 else min(n, total)          # 0 == all regions
    return int(round(100.0 * (float(n) / total) ** (1.0 / 3.0)))


def resolve_max_difficulty_pct(raw, num_regions, total_regions, floor_pct=0):
    """The ONE place `auto` becomes a number. Both callers -- features/scaling.generate_early and
    core._options_echo -- come through here, so what is validated is what the client is told.

    A derived ceiling is never placed below an EXPLICIT floor: the player typed the floor and did not
    type the ceiling, so the floor wins and generation proceeds. Raising here would fail a seed over a
    value nobody chose.
    """
    if int(raw) != AUTO_CEILING:
        return int(raw)
    return max(int(floor_pct), auto_ceiling_pct(num_regions, total_regions))


def ramped_target(position, span, target_max, ramp_pct=100):
    """Order POSITION (0..span) -> scaling target (0..target_max), given a ramp speed.

    `ramp_pct` is the share of the progression order by which a seed reaches the TOP tier:

        100  linear -- the last region is the first to hit the top rung  (default, unchanged)
         50  top tier from halfway through the lock chain, flat thereafter
         25  top tier a quarter of the way in

    Why a percent-of-the-run and not an exponent: this is the one formulation a player can predict
    from the number, and it is the one the CLIENT cannot undo. Emitting a lower CEILING is impossible
    (the client re-normalizes, above), but SATURATING EARLY is not -- the max emitted target is still
    `target_max`, so normalization is unchanged and the tail simply sits at the top rung.

    `ramp_pct > 100` would mean "never quite reach the top", which IS the un-expressible case: the
    max emitted target would fall and the client would renormalize it straight back. So the option
    range stops at 100 rather than offering a setting that silently does nothing.

    Monotonic non-decreasing in `position`; clamped to `target_max`. Pure.
    """
    if span <= 0:
        return 0
    ramp_pct = max(1, min(100, int(ramp_pct)))
    frac = position / span
    if ramp_pct < 100:
        frac = frac * 100.0 / ramp_pct
    return round(min(1.0, frac) * target_max)


def floor_multiplier(pct):
    """`completion_scaling_floor` PERCENT (0..100, the player-facing option) -> the HP MULTIPLIER
    the client reads at `sd["options"]["completion_scaling_floor"]`.

    Returns the exact ladder rung, so the client's search inverts this precisely:
    `floor_tier_from_multiplier(floor_multiplier(pct)) == round(pct/100 * (len(LADDER) - 1))`, i.e.
    `* 19` for today's 20-rung ladder. (This said `* 9` until 2026-08-05 -- correct for the 10-rung
    subset, stale from the moment the ladder was extended to `7200`. Written as the expression rather
    than a literal so it cannot rot again.) That exactness rests
    on the ladder being STRICTLY ASCENDING (a `hp >= rung` search only recovers that rung's index if
    no earlier rung is also >= it) -- asserted, along with the round-trip in both directions, in
    tests/test_gf_scaling_ladder_mirror.py.

    `pct == 0` returns int `0`, not `0.0`: "no floor" is the DEFAULT, and a yaml that never mentions
    this option must generate byte-identically to one from before the option was reachable
    (CONTRIBUTING options hygiene). Both values resolve to tier 0 client-side, so pinning the int
    costs nothing and keeps default seeds stable.
    """
    pct = max(0, min(100, int(pct)))
    if pct == 0:
        return 0
    return SCALING_HP_LADDER[round(pct / 100 * (len(SCALING_HP_LADDER) - 1))]
