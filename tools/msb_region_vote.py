#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""msb_region_vote.py -- an OFFLINE, in-repo second opinion on a check's region.

WHY. `tools/audit_region_second_opinion.py` asks two public wikis where a check's vanilla item
is found. That join key is the ITEM NAME, so it is silent on the 209 generic-name rows and thin
everywhere else. This module asks a completely different question of data we already own: the
check's own MSB coordinates. It folds the pickup into the single overworld frame and votes the
region of the NEAREST region-attributed Site of Grace.

WHAT IT IS AND IS NOT. This is a RANKING SIGNAL, not an adjudicator.

  * It measures 91.4% over 2607 CONTROL checks -- the ones whose region is NOT
    `(region unconfirmed)` and that carry MSB coords (`--calibrate` re-derives it). One row in ten
    is wrong, by construction: a grace is not a region boundary, and the nearest one across a
    cliff, a lake or a tunnel mouth belongs to somewhere you cannot walk to. The largest error
    families are the ones you would predict -- Scadu Altus/Shadow Keep (52), Leyndell/Ashen
    Capital (29), Liurnia/Mountaintops (23) -- regions that share a border or a coordinate frame.
  * It is the SAME KIND of derivation as the nearest-neighbour tile hop that produced the 305
    unconfirmed regions in the first place -- a hop that CANNOT FAIL (CONTRIBUTING rule 1).
    An agreement between two nearest-neighbour hops is therefore NOT independent corroboration.
    What it is good for is ORDERING the hand-adjudication: a vote that disagrees with us AND
    with the wiki is worth a human's next hour; a short-distance unanimous vote that backs us is
    worth the least.
  * The decisive instrument is the point-in-volume PlayArea test, which reads the exact runtime
    `PlayRegionID` instead of guessing from a neighbour. It needs the extracted MSB corpus, which
    CI does not have. `docs/PLAYAREA-ITEM-SCAN.md` is the runbook for running it; when it has
    run, its answers REPLACE these votes (`vote_note` becomes `PLAYAREA-CONFIRMED`).

INPUTS (all committed; nothing is fetched, nothing needs game files):
  greenfield/item_grace_coords.tsv        map-local XYZ for items and graces
  tools/overworld_fold.py                 THE tile fold (LOD-aware) -- never re-implement it
  greenfield/grace_region_map.tsv         grace -> warp-menu play_region
  greenfield/grace_ground.tsv             grace -> the play_region BUCKET of the ground it is on
  greenfield/eldenring/region_play_ids.py REGION_PLAY_IDS: play ids -> our region vocabulary

THE ANCHOR CLASS THAT LIES (`SUSPECT-ANCHOR`). A grace's region is read from the warp menu
first; where the warp menu names a play_region we do not own, we fall back to the BUCKET of the
ground it stands on. When that ground row's own source is `tile-default` -- i.e. no PlayArea
volume contained the grace and we took the tile's default bucket -- the grace's region is itself
a tile-wide guess, and every vote it anchors inherits that guess. 22 graces are in that class.
Grace 73211 "Yelough Anix Tunnel" is the one that matters here: it anchors 17 votes that flip
Mountaintops rows to Consecrated Snowfield, and its own region came from a tile-default row on
tile m60_47_55. Those rows are BADGED, not dropped -- a badge is a reader's warning; dropping
them would hide a cluster that may well be right.

`CROSS-TILE-MSB` is the other note that changes how a row reads: the audit's `map_tile` comes
from the check label, but the MSB row that actually holds the coordinates can live on a
DIFFERENT fine-grid tile (three Bestial Sanctum checks are labelled m60_51_41 and their coords
are authored in m60_51_43). Where those disagree the label's tile is the weaker of the two, and
the vote is the one computed from the MSB. `COARSE-LOD` marks a coords row authored on a LOD1/2
tile: the fold handles it (pitch = 256 << lod, plus the centring term), but the position is
coarser and a reader should know before trusting a 300 m margin.

Use as a library (the audit tool does) or run it for a standalone report:

    python tools/msb_region_vote.py --limit 20
"""
import argparse
import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from overworld_fold import world_xz  # noqa: E402  -- THE fold, single implementation (#338)

COORDS = os.path.join("greenfield", "item_grace_coords.tsv")
GRACE_REGION_MAP = os.path.join("greenfield", "grace_region_map.tsv")
GRACE_GROUND = os.path.join("greenfield", "grace_ground.tsv")
REGION_PLAY_IDS_PY = os.path.join("greenfield", "eldenring", "region_play_ids.py")

# The calibration sentence. It is repeated verbatim into the tsv header and the worksheet page
# because a number that travels without its caveat becomes an authority (CONTRIBUTING rule 10).
# MEASURED, not remembered: `python tools/msb_region_vote.py --calibrate` re-derives this number
# from the repo in seconds, and the sentence names the run so a reader can falsify it rather than
# inherit it (CONTRIBUTING rule 10 -- a comment that asserts a fact is a claim, and claims rot).
CALIBRATION = ("91.4% on a 2607-check control set (--calibrate, 2026-08-25) -- roughly one row in "
               "ten is WRONG, so this is a RANKING signal for hand-adjudication, never an "
               "adjudicator. The exact answer is the PlayArea point-in-volume test "
               "(docs/PLAYAREA-ITEM-SCAN.md).")

NOTE_NO_COORDS = "NO-COORDS"
NOTE_NO_ANCHOR = "NO-ANCHOR"
NOTE_SUSPECT = "SUSPECT-ANCHOR"
NOTE_CROSS_TILE = "CROSS-TILE-MSB"
NOTE_COARSE = "COARSE-LOD"
NOTE_MULTI = "MULTI-PLACEMENT"

FINE_TILE_RE = re.compile(r"^(m6[01])_(\d\d)_(\d\d)(?:_(\d)(\d))?$")


def _rows(path):
    """'#' comment lines, first non-comment line is the header. Same reader as the other tools."""
    with open(path, encoding="utf-8-sig") as fh:
        body = [ln for ln in fh if not ln.startswith("#") and ln.strip()]
    return list(csv.DictReader(body, delimiter="\t"))


def load_play_id_regions(repo=REPO):
    """play_region id (as str) -> our region name, out of REGION_PLAY_IDS.

    Read by exec of the module body, not by import: the tools/ scripts are run from a checkout
    with no package install and `greenfield.eldenring` is not importable there.
    """
    path = os.path.join(repo, REGION_PLAY_IDS_PY)
    ns = {}
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    exec(compile(src, path, "exec"), ns)  # noqa: S102 -- our own committed table
    table = ns.get("REGION_PLAY_IDS")
    if not table:
        raise SystemExit("REGION_PLAY_IDS empty in %s -- refusing to vote half-blind" % path)
    out = {}
    for region, ids in table.items():
        for i in ids:
            out[str(i)] = region
    return out


def load_grace_regions(repo=REPO):
    """(region_by_grace, suspect_graces).

    Warp-menu play_region first; where that names an id we do not own, the ground BUCKET of the
    grace, but only when the buckets agree on ONE region -- a two-region ground is not an answer.
    A grace whose region came only from a `tile-default` ground row is SUSPECT: its own region is
    a tile-wide guess and it must not silently anchor a vote (see the module docstring).
    """
    play = load_play_id_regions(repo)
    region, suspect = {}, set()
    for row in _rows(os.path.join(repo, GRACE_REGION_MAP)):
        got = play.get(row["play_region_id"])
        if got:
            region[row["grace_flag"]] = got
    for row in _rows(os.path.join(repo, GRACE_GROUND)):
        flag = row["grace_flag"]
        if flag in region:
            continue
        regions = {play[b] for b in row["ground_buckets"].split(";") if b in play}
        if len(regions) != 1:
            continue
        region[flag] = regions.pop()
        if row.get("source", "").startswith("tile-default"):
            suspect.add(flag)
    if not region:
        raise SystemExit("no grace got a region -- inputs are stale or empty (rule 2)")
    return region, suspect


def fold(map_id, x, y, z):
    """(frame, (x, y, z)) in the single folded overworld frame. Interiors keep their own map id
    as the frame, which is what confines a vote to the map it was measured in."""
    got = world_xz(map_id, x, z)
    if got is None:
        return map_id, (x, y, z)
    base, gx, gz = got
    return base, (gx, y, gz)


def tile_of(map_id):
    """(base, tx, tz, lod) for an overworld map id, else None."""
    m = FINE_TILE_RE.match(map_id or "")
    if not m:
        return None
    lod = int(m.group(5)) if m.group(5) is not None else (2 if int(m.group(2)) < 30 else 0)
    return m.group(1), int(m.group(2)), int(m.group(3)), lod


def load_coords(repo=REPO):
    """(items, graces): flag -> [ (map_id, x, y, z), ... ], and [(flag, map_id, x, y, z, name)].

    🛑 A FLAG CAN HAVE MORE THAN ONE PLACEMENT and the list is why. `item_grace_coords.tsv` holds
    5122 item rows over 3966 distinct flags: most of the surplus is the `_00`/`_10` MSB version
    pair carrying the SAME point (the fold ignores the version digit, so those collapse), but 442
    flags are genuinely placed twice -- the same lot authored in two maps. Keeping only the last
    row read would be a silent input loss (rule 4), and it would pick its winner by file order.
    Placements that fold to the same point are deduped; the rest are all kept and the vote SAYS
    when it had to choose (`MULTI-PLACEMENT`).
    """
    items, graces = {}, []
    for row in _rows(os.path.join(repo, COORDS)):
        try:
            x, y, z = float(row["x"]), float(row["y"]), float(row["z"])
        except (TypeError, ValueError):
            continue
        if row["kind"] == "item":
            items.setdefault(row["key"], []).append((row["map_id"], x, y, z))
        elif row["kind"] == "grace":
            graces.append((row["key"], row["map_id"], x, y, z, row.get("name", "")))
    return items, graces


class Vote(object):
    """One check's vote. `region` is None when there is nothing to vote with."""

    __slots__ = ("region", "distance_m", "unanimous", "anchor_grace", "anchor_name", "notes")

    def __init__(self, region=None, distance_m=None, unanimous=None,
                 anchor_grace="", anchor_name="", notes=None):
        self.region = region
        self.distance_m = distance_m
        self.unanimous = unanimous
        self.anchor_grace = anchor_grace
        self.anchor_name = anchor_name
        self.notes = list(notes or [])

    def as_columns(self):
        """The five tsv cells. Empty strings, never 'None' -- a stringified None in a data column
        is a value a reader cannot distinguish from a region called None."""
        return {
            "msb_vote_region": self.region or "",
            "vote_distance_m": ("%.1f" % self.distance_m) if self.distance_m is not None else "",
            "vote_unanimous": ("" if self.unanimous is None else ("yes" if self.unanimous else "no")),
            "vote_anchor_grace": ("%s %s" % (self.anchor_grace, self.anchor_name)).strip()
            if self.anchor_grace else "",
            "vote_note": ";".join(self.notes),
        }


class Voter(object):
    """Nearest-region-attributed-grace vote, over one folded frame per overworld base map.

    Constructed from tables (`from_repo`) or from plain dicts, which is what lets the suite test
    the geometry on synthetic fixtures with no repo data at all.
    """

    def __init__(self, items, graces, grace_region, suspect=(), top_n=3):
        # A single (map_id, x, y, z) tuple is accepted for one-placement flags -- the suite's
        # synthetic fixtures are written that way and a list of one means the same thing.
        self.items = {}
        for flag, placements in items.items():
            if placements and not isinstance(placements[0], (list, tuple)):
                placements = [placements]
            seen, keep = set(), []
            for p in placements:
                folded = fold(*p)
                key = (folded[0], round(folded[1][0], 2), round(folded[1][1], 2),
                       round(folded[1][2], 2))
                if key in seen:
                    continue
                seen.add(key)
                keep.append(tuple(p))
            self.items[flag] = keep
        self.grace_region = grace_region
        self.suspect = set(suspect)
        self.top_n = top_n
        self.grace_name = {}
        self.frames = {}
        for flag, map_id, x, y, z, name in graces:
            self.grace_name[flag] = name
            if flag not in grace_region:
                continue          # not region-attributed: it cannot vote
            frame, point = fold(map_id, x, y, z)
            self.frames.setdefault(frame, []).append((flag, point))

    @classmethod
    def from_repo(cls, repo=REPO, top_n=3):
        items, graces = load_coords(repo)
        region, suspect = load_grace_regions(repo)
        return cls(items, graces, region, suspect, top_n=top_n)

    def _vote_one(self, map_id, x, y, z, label_tile):
        frame, point = fold(map_id, x, y, z)
        candidates = sorted((math.dist(point, q), g) for g, q in self.frames.get(frame, []))
        notes = []
        label = tile_of(label_tile)
        here = tile_of(map_id)
        if here and here[3] > 0:
            notes.append(NOTE_COARSE)
        elif label and here and label[3] == 0 and (label[0], label[1], label[2]) != \
                (here[0], here[1], here[2]):
            notes.append(NOTE_CROSS_TILE)
        if not candidates:
            notes.append(NOTE_NO_ANCHOR)
            return Vote(notes=notes)
        distance, anchor = candidates[0]
        top = [self.grace_region[g] for _d, g in candidates[:self.top_n]]
        if anchor in self.suspect:
            notes.append(NOTE_SUSPECT)
        return Vote(region=self.grace_region[anchor], distance_m=distance,
                    unanimous=len(set(top)) == 1, anchor_grace=anchor,
                    anchor_name=self.grace_name.get(anchor, ""), notes=notes)

    def vote(self, flag, label_tile=""):
        """The vote for one check flag. Always returns a Vote; `region is None` says why.

        With several placements the CLOSEST-anchored one wins and the row is noted
        MULTI-PLACEMENT -- an arbitrary pick that does not announce itself is the same silent
        wrong answer as no pick at all.
        """
        placements = self.items.get(flag)
        if not placements:
            return Vote(notes=[NOTE_NO_COORDS])
        votes = [self._vote_one(m, x, y, z, label_tile) for m, x, y, z in placements]
        cast = [v for v in votes if v.region is not None]
        best = min(cast, key=lambda v: v.distance_m) if cast else votes[0]
        if len(placements) > 1:
            best.notes.append(NOTE_MULTI)
            if len({v.region for v in cast}) > 1:
                best.notes.append("MULTI-PLACEMENT-SPLIT")
        return best


VOTE_COLUMNS = ["msb_vote_region", "vote_distance_m", "vote_unanimous",
                "vote_anchor_grace", "vote_note"]


LABEL_RE = re.compile(r"'([A-Za-z.' ]+?) :: (.*?)\[f(\d+)\]'")


def calibrate(repo=REPO, voter=None):
    """Accuracy on the CONTROL set: every check whose region is NOT `(region unconfirmed)`, that
    carries MSB coords, and whose flag is labelled with exactly one region.

    This is the mirror of rule 7 -- the number that justifies the column is re-derivable, so
    nobody has to take the docstring's word for it. It reads `data.py`'s labels, which is the
    same corpus the audit's own targets come out of.
    """
    voter = voter or Voter.from_repo(repo)
    regions, unconfirmed = {}, set()
    with open(os.path.join(repo, "greenfield", "eldenring", "data.py"), encoding="utf-8") as fh:
        text = fh.read()
    for region, body, flag in LABEL_RE.findall(text):
        regions.setdefault(flag, set()).add(region)
        if "(region unconfirmed)" in body:
            unconfirmed.add(flag)
    hits = misses = 0
    families = {}
    for flag, names in regions.items():
        if flag in unconfirmed or len(names) != 1 or flag not in voter.items:
            continue
        v = voter.vote(flag)
        if v.region is None:
            continue
        ours = next(iter(names))
        if v.region == ours:
            hits += 1
        else:
            misses += 1
            families[(ours, v.region)] = families.get((ours, v.region), 0) + 1
    return hits, misses, families


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--calibrate", action="store_true",
                    help="re-derive the accuracy figure in CALIBRATION and exit")
    args = ap.parse_args(argv)
    voter = Voter.from_repo(args.repo)
    if args.calibrate:
        hits, misses, families = calibrate(args.repo, voter)
        total = hits + misses
        print("CONTROL n=%d  agree=%d  accuracy=%.1f%%" % (total, hits, 100.0 * hits / total))
        for (ours, vote_), n in sorted(families.items(), key=lambda kv: -kv[1])[:8]:
            print("  %-28s voted %-28s %d" % (ours, vote_, n))
        print("CALIBRATION says: %s" % CALIBRATION)
        return 0
    print("region-attributed graces: %d (%d suspect tile-default anchors)"
          % (len(voter.grace_region), len(voter.suspect)))
    audit = _rows(os.path.join(args.repo, "greenfield", "check_region_second_opinion.tsv"))
    agree = disagree = novote = 0
    shown = 0
    for row in audit:
        v = voter.vote(row["flag"], row.get("map_tile", ""))
        if v.region is None:
            novote += 1
            continue
        if v.region == row["our_region"]:
            agree += 1
        else:
            disagree += 1
            if not args.limit or shown < args.limit:
                shown += 1
                print("  %-10s %-28s ours=%-26s vote=%-26s %6.1fm %s %s"
                      % (row["flag"], row["item"][:28], row["our_region"], v.region,
                         v.distance_m, v.anchor_grace, ";".join(v.notes)))
    print("audit rows %d: votable %d (agree %d, disagree %d), no vote %d"
          % (len(audit), agree + disagree, agree, disagree, novote))
    return 0


if __name__ == "__main__":
    sys.exit(main())
