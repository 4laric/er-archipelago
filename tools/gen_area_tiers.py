#!/usr/bin/env python3
"""Generate the BAKED area-tier table for the client.

Emits `crates/er-logic/src/area_tiers.rs` from `greenfield/area_tiers.tsv`, which
`tools/datamine_area_tiers.py --emit` produces from the MSBs (tier-2, AGENTS.md 5a --
Alaric's box). This tool is the AP-env-free, artifact-free half: it reads the committed tsv
and nothing else, so CI can run it and assert the client's committed bytes are not stale.

WHY A CLIENT COPY EXISTS. `scale_action` places an UNRUNGED enemy -- every named boss, every
hand-tuned NPC -- by asking how hard vanilla thought the GROUND was. That answer used to come
from a live census over loaded enemies, which counts rung-AND-band carriers while our own
sweep strips the band, so it erases its own sample. The ground is a property of the MAP, so it
is knowable offline and correct on a region's FIRST sweep. See the module docs in the emitted
file, and client PR #126.

    python tools/gen_area_tiers.py            # regenerate
    python tools/gen_area_tiers.py --check    # CI drift gate (0 ok / 1 stale / 4 no client)

EXIT 4 = the client checkout is absent (submodule not initialised), NOT a pass. The caller
decides whether that is tolerable; `gen_region_locks.py` uses the same convention.
"""
import argparse
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
TSV = os.path.join(REPO, "greenfield", "area_tiers.tsv")
CLIENT = os.path.join(REPO, "from-software-archipelago-clients")
OUT = os.path.join(CLIENT, "crates", "er-logic", "src", "area_tiers.rs")

# er-logic::scaling -- keep in lockstep. A tier outside this range would index past SCALING_TIERS.
NUM_TIERS = 20


def read_rows(path=TSV):
    """-> [(bucket, tier, is_dlc)] for rows that make a claim, in file order.

    A row with an EMPTY tier is skipped, not defaulted: absence is the client's "no claim", and
    turning it into 0 would let an unrunged enemy at target 0 be judged against native 0 and
    touched. See `a_bucket_with_too_thin_a_sample_makes_no_claim` in er-logic.
    """
    rows, header = [], None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if header is None:
                header = fields
                for want in ("bucket", "tier", "ladder"):
                    if want not in header:
                        raise SystemExit(f"gen_area_tiers: {path} has no {want!r} column")
                continue
            row = dict(zip(header, fields))
            if not row["tier"]:
                continue
            bucket, tier = int(row["bucket"]), int(row["tier"])
            if not 0 <= tier < NUM_TIERS:
                raise SystemExit(f"gen_area_tiers: bucket {bucket} has tier {tier}, outside 0..{NUM_TIERS}")
            rows.append((bucket, tier, row["ladder"] == "dlc"))
    if not rows:
        raise SystemExit(f"gen_area_tiers: {path} produced no rows -- refusing to emit an empty table")
    buckets = [b for b, _, _ in rows]
    if buckets != sorted(set(buckets)):
        # The client binary-searches this. An unsorted table does not fail loudly, it MISSES --
        # and a miss reads as "no claim", i.e. silently the old behaviour.
        raise SystemExit("gen_area_tiers: buckets are not sorted/unique; the client binary-searches them")
    return rows


def render(rows):
    n_dlc = sum(1 for _, _, d in rows if d)
    body = "\n".join("    (%d, %d)," % (b, t) for b, t, _ in rows)
    dlc = ", ".join(str(b) for b, _, d in rows if d)
    # trailing comma on the last element: rustfmt's own style for a wrapped slice literal, and
    # what the committed file carries -- without it --check reports STALE on a byte nobody sees.
    dlc_wrapped = "\n".join("    " + l for l in textwrap.wrap(dlc, 92)) + ","
    return TEMPLATE % {"n": len(rows), "dlc": n_dlc, "body": body, "dlc_wrapped": dlc_wrapped}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the committed output is stale")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    if not os.path.isdir(CLIENT) or not os.path.isdir(os.path.join(CLIENT, "crates")):
        print("gen_area_tiers: no client checkout at %s (submodule not initialised)" % CLIENT,
              file=sys.stderr)
        return 4

    text = render(read_rows())
    if args.check:
        have = open(args.out, encoding="utf-8").read() if os.path.exists(args.out) else ""
        if have == text:
            print("gen_area_tiers: OK -- %s is current" % os.path.relpath(args.out, REPO))
            return 0
        print("gen_area_tiers: STALE -- %s does not match a regeneration from "
              "greenfield/area_tiers.tsv. Re-run without --check and commit."
              % os.path.relpath(args.out, REPO), file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("gen_area_tiers: wrote %s (%d buckets)" % (os.path.relpath(args.out, REPO),
                                                     len(read_rows())))
    return 0


TEMPLATE = r"""// @generated by tools/gen_area_tiers.py -- DO NOT EDIT BY HAND.
// Source: greenfield/area_tiers.tsv (tools/datamine_area_tiers.py --emit, which needs the MSBs
//         and therefore the Windows box -- AGENTS.md section 5a, tier-2).
// Regenerate: python tools/gen_area_tiers.py
//
// STATIC GAME DATA: what difficulty VANILLA declared for the ground in each play_region bucket,
// measured offline instead of at runtime. 128 buckets emitted, %(n)d of them with a defensible
// tier; a bucket ABSENT here has no claim and the caller MUST fall back rather than default.

//! Vanilla's own declared difficulty per play_region bucket (issue #346).
//!
//! ## Why this is baked and not measured
//!
//! `scaling::area_tier_from_histogram` counts the enemies that carry a vanilla ladder rung AND a
//! band -- and our own sweep STRIPS the band. So the live census erases its own sample: a region
//! answers `Some(n)` on its first sweep and `None` on every sweep after. That is harmless for the
//! enemies standing there at the time (they come out carrying a rung or a down state, and
//! `Replace`/`KeepDown` re-derive them forever) and fatal for anything that arrives LATER, which
//! has neither. bobler, 2026-08-09: bucket 69300 answered `from 0 vanilla-shaped` on 33 of 48
//! sweeps and its `left vanilla` count never converged -- it plateaued at 122..214.
//!
//! `AreaAnchor` latches the first good live reading and covers most of that. It cannot help a
//! region that never samples well ONCE (bucket 21020: two sweeps, both `from 0`, zero down-states),
//! and it does not survive `configure`, so loading a save into already-converged ground starts the
//! hunt over with no vanilla sample left anywhere in it.
//!
//! This table has neither problem: the ground is a property of the MAP, so it is knowable without
//! a live sample and correct on a region's FIRST sweep.
//!
//! ## How it was derived
//!
//! `mapstudio/<map>-msb-dcx/Part/Enemy/*.xml` -> `NPCParamID` -> `NpcParam.spEffectID3` (the only
//! column in the whole param set that carries a ladder rung: 2952 base rows, 1282 DLC, and
//! `spEffectID0/1/2` carry zero) -> bucket via `play_region_buckets.tsv` -> **the weighted median,
//! using the same reducer as `area_tier_from_histogram`**. A different reducer would make this a
//! second opinion rather than a replacement.
//!
//! ## Validation
//!
//! Reproduced two independent live census readings from static data:
//! **Liurnia (62000) = 5** against a recorded `area-index 5`, and **Altus (63000) = 7** against a
//! recorded `area-index 7` off a 302-enemy sample. Altus was not in the acceptance set.
//!
//! ## Two things to know before using a number from here
//!
//! 1. **A DLC tier and a base tier are NOT comparable to each other.** The two ladders are disjoint
//!    bands -- base spans 1.141x..7.422x HP, the DLC ladder 7.047x..16.641x -- so no multiplier
//!    mapping between them exists. DLC buckets (%(dlc)d of them, listed in `DLC_RANKED`) are ranked
//!    WITHIN the 16-rung DLC ladder and projected onto 0..19 by RANK. Each is only ever compared
//!    against its own region's sphere target, which is likewise a position and not a multiplier.
//!    Anything that pools the two scales is wrong.
//! 2. **It is a SAMPLE, not a census.** `play_region_buckets.tsv` names a subset of each overworld
//!    bucket's tiles (`PlayRegionParam` does not name the rest; the game resolves play_region by
//!    position at runtime), so 61%% of enemy parts land in no bucket at all. The median is robust
//!    to that and two regions matched their live readings, but the skipped set is larger than the
//!    sample.

/// `(play_region bucket, ladder index 0..19)`, sorted so lookup can binary-search.
///
/// ABSENT = NO CLAIM, deliberately, and it is the same convention as `native_tiers::NATIVE_TIERS`:
/// 13 buckets had fewer than `MIN_AREA_SAMPLE` runged enemies and are simply not here.
pub const AREA_TIERS: &[(i32, u8)] = &[
%(body)s
];

/// The buckets above whose tier came from the DLC ladder and was rank-projected. Diagnostic only --
/// nothing should branch on it -- but a future change that wants to compare two tiers needs to be
/// able to see that they may not live on the same scale.
pub const DLC_RANKED: &[i32] = &[
%(dlc_wrapped)s
];
"""


if __name__ == "__main__":
    raise SystemExit(main())
