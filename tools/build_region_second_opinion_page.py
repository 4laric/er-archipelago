#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_region_second_opinion_page.py -- the region second-opinion audit as ONE offline page.

Writes er-archipelago-region-second-opinion.html: a single self-contained file (no server, no
CDN, no network at view time) for working through the 305 "(region unconfirmed)" checks that
tools/audit_region_second_opinion.py got a second opinion on (issue #1025, PR #1027).

WHAT THIS IS. A WORKSHEET, not a verdict. The audit says what two public wikis appear to
claim about a check's region; it does NOT say who is right. The page exists so a human can
read the evidence and RULE, one check at a time, and carry those rulings out as a TSV that
feeds region_overrides.tsv. Nothing in gen reads this page or its export.

🛑 THE ADJUDICATION UNIT IS THE FLAG, NOT THE ROW. Eight flags in the audit carry more than
one ap id (the Scaled set is one flag with four). region_of decides per FLAG, so ruling on
one ap id and not its siblings would be incoherent: the page merges them into ONE row that
lists every ap id it speaks for, and the export carries the whole list. A per-row worksheet
would have invited exactly the split ruling the override table cannot express.

🛑 AMBIGUOUS-GENERIC IS NOT A BACKLOG. 209 of the 305 rows are items whose names are generic
(Smithing Stone [1], Rune Arc): the wiki has one page for the item, and that page lists every
place in the game it drops, so it can neither agree nor disagree about ONE pickup. Those rows
carry no source page at all -- their `source` column is empty in the tsv, which is the honest
record of "not consulted", not "consulted and found nothing". The group ships COLLAPSED and
its rows are not even rendered until it is opened, because a reader who scrolls into 209
sourceless rows starts adjudicating noise.

THE MSB VOTE COLUMN. Every row also carries the offline nearest-grace vote the audit computes
(`tools/msb_region_vote.py`): the region of the nearest region-attributed Site of Grace, once the
check is folded into the overworld frame. It is coloured by WHO IT BACKS -- us, the wiki, or
neither -- because that is the only thing about it a reader can act on, and it is the reason the
209 generic rows are no longer opinion-free. 🛑 IT IS 90% ACCURATE AND IT IS NOT INDEPENDENT OF
US: the same nearest-neighbour shape produced the regions it is checking, so a vote that agrees
corroborates nothing, and one row in ten is simply wrong. The header says so, in those words,
above every ruling anyone makes. Rows anchored on a grace whose OWN region came from a
tile-default row are badged SUSPECT-ANCHOR -- 17 of the 19 votes-against are one such grace
(73211, Yelough Anix Tunnel), which is a cluster to explain, not 17 defects to fix.

NO-DATA IS NOT AGREE. A page was found and it never named a region. That is a third thing,
and it is coloured as its own verdict for the same reason the audit's own suite pins it.

INPUTS (all committed; none are game files, none are fetched here):
  greenfield/check_region_second_opinion.tsv  the audit verdicts AND the msb_vote_* columns
                                              (produced offline, by hand run)
  greenfield/check_region_triage.tsv          how the region was decided (GUESSED / CONFLICT)
  greenfield/eldenring/data.py                _GEN_STAMP.inputs_hash, for the freshness stamp

LICENSES ARE IN THE PAGE, NOT JUST HERE. The footer names Eldenpedia (CC BY-SA 4.0) and the
Fandom Elden Ring Wiki (CC BY-SA 3.0), and states that Fextralife was deliberately not
consulted. No wiki PROSE is carried: the page holds page TITLES and LINKS, which is the same
license discipline the audit tool itself keeps.

DETERMINISM: a pure function of those inputs -- everything is emitted sorted, JSON is dumped
with sort_keys, and the page is stamped with data.py's inputs_hash, NOT a git commit. That is
what lets CI regenerate and fail on a non-empty diff (.github/workflows/tests.yaml
`generators`); a commit hash would make the committed file stale by construction.

Run:  python tools/build_region_second_opinion_page.py [--out PATH] [--repo ROOT] [--check]
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 🛑 The filename is a LITERAL inside the os.path.join, not a constant folded in from above:
# test_gf_regen_all's producer scan reads the basename straight out of this line, and a
# variable there makes the builder look like it declares no output at all -- which is how a
# generated artifact falls out of the regen entrypoint unnoticed (#699).
OUT_HTML = os.path.join(REPO, "er-archipelago-region-second-opinion.html")
DEFAULT_OUT = os.path.basename(OUT_HTML)

# DISAGREE first: it is the only verdict that asserts a defect. Then the two "look again"
# families, then AGREE (evidence FOR the status quo, still worth a skim), and the generic
# bucket last and collapsed. This order is the page's information architecture; the template
# renders groups in exactly this sequence.
VERDICT_ORDER = ["DISAGREE", "AMBIGUOUS", "NO-DATA", "AGREE", "AMBIGUOUS-GENERIC"]

VERDICT_WHY = {
    "DISAGREE": "a wiki page names a region that is not ours -- the only verdict that asserts "
                "a defect, and none of them is proven yet",
    "AMBIGUOUS": "the page named more than one region and ours was among them",
    "NO-DATA": "a page was found and it never named a region. NOT the same as agreeing",
    "AGREE": "the page named a region and it was ours. Evidence for the status quo, not proof",
    "AMBIGUOUS-GENERIC": "generic item name -- one wiki page covers every drop site in the "
                         "game, so it cannot speak about one pickup. No source was consulted",
}

# The four rulings, in the order a reader reaches for them. The VALUES are what the export
# writes; renaming one silently invalidates every note already exported, so treat them as a
# contract with the reader's own spreadsheet.
ADJUDICATIONS = [
    ("ours-right", "ours right"),
    ("wiki-right", "wiki right"),
    ("needs-msb", "needs MSB look"),
    ("generic-collision", "generic collision"),
]

def _vote_calibration():
    """The calibration sentence, taken from the tool that measured it -- never retyped here.

    🛑 If msb_region_vote is not importable (an installed world beside a partial checkout), we
    say the number is UNKNOWN rather than emitting a remembered one. A caveat that invents its
    own confidence is worse than no caveat.
    """
    try:
        sys.path.insert(0, os.path.join(REPO, "tools"))
        import msb_region_vote
        return msb_region_vote.CALIBRATION
    except Exception:  # noqa: BLE001 -- a missing sibling is data, not a crash
        return ("Its accuracy is UNKNOWN in this build (tools/msb_region_vote.py was not "
                "readable) -- treat every vote as unvalidated.")


EXPORT_HEADER = ["flag", "ap_ids", "audit_verdict", "adjudication", "note"]

# The four vote colourings, in the order a reader cares about them. "both" first: a vote that
# backs NEITHER of the two opinions on the row is the one worth a human's next hour.
VOTE_SIDES = [
    ("both", "vote disagrees with both"),
    ("wiki", "vote backs the wiki"),
    ("ours", "vote backs us"),
    ("none", "no vote"),
]

VOTE_CAVEAT = (
    "The MSB VOTE column is the region of the nearest region-attributed Site of Grace, folded "
    "into the overworld frame from our own committed coordinates. " + _vote_calibration() +
    " It is NOT independent of the nearest-neighbour hop that gave these checks their regions in "
    "the first place, so a vote that AGREES with us corroborates nothing. Read it as an ORDERING "
    "over what to adjudicate next, never as a ruling. THIS PARAGRAPH DOES NOT APPLY TO A ROW "
    "BADGED RULING -- see the next note."
)

# 🛑 The exemption, spelled out on the page itself. The caveat above exists because a
# nearest-neighbour vote cannot fail; a PLAYAREA-CONFIRMED row is not that kind of answer, and
# leaving one caveat covering both would either slander the ruling or launder the guess.
VOTE_RULING_NOTE = (
    "RULING (PLAYAREA-CONFIRMED): this row was NOT voted on. Its region is the point-in-volume "
    "answer from Region/PlayArea <PlayRegionID> -- the exact id the client's kick-watch reads at "
    "runtime -- read out of greenfield/item_play_regions.tsv and mapped through REGION_PLAY_IDS "
    "(docs/PLAYAREA-ITEM-SCAN.md). It REPLACED the nearest-grace heuristic rather than being "
    "averaged with it, the accuracy caveat above does not describe it, and only volume:/seam: "
    "sources qualify: a tile-default answer is the same tile-wide guess the vote already is, so "
    "it does NOT confirm anything and never becomes a ruling."
)

VOTE_SUSPECT_NOTE = (
    "SUSPECT-ANCHOR: the anchoring grace's OWN region came from a tile-default row, not from a "
    "PlayArea volume -- so the vote inherits a tile-wide guess. Badged, not dropped."
)

# Page titles are turned into links, never into prose. wiki.gg and Fandom are both MediaWiki,
# so /wiki/<Title with underscores> resolves on either.
SOURCE_BASE = {
    "eldenpedia": "https://eldenring.wiki.gg/wiki/",
    "fandom": "https://eldenring.fandom.com/wiki/",
}

TILE_RE = re.compile(r"^m(\d\d)_(\d\d)_(\d\d)")


def read_tsv(path):
    """Same reader shape as tools/build_check_browser.py: '#' lines are commentary, the first
    non-comment line is the header."""
    rows, comments, header = [], [], None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#"):
                comments.append(line.lstrip("#").strip())
                continue
            if not line:
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts)))
    return rows, comments


def data_stamp(path):
    """data.py's _GEN_STAMP.inputs_hash -- a content id that is stable across commits."""
    try:
        with open(path, encoding="utf-8") as fh:
            m = re.search(r"^_GEN_STAMP = (\{.*\})\s*$", fh.read(), re.M)
    except OSError:
        return ""
    if not m:
        return ""
    import ast
    return ast.literal_eval(m.group(1)).get("inputs_hash", "")


def strip_label(label):
    """'Liurnia :: Dragonscale Blade - m60_33_45 (region unconfirmed) [f1033457100]' ->
    'Dragonscale Blade - m60_33_45'. The region, the marker and the flag all have their own
    columns; repeating them in the name only makes the row harder to read."""
    s = label
    if " :: " in s:
        s = s.split(" :: ", 1)[1]
    s = re.sub(r"\s*\[f\d+\]\s*$", "", s)
    s = re.sub(r"\s*\(region unconfirmed\)\s*(\(\d+\))?\s*", " ", s).strip()
    return re.sub(r"\s{2,}", " ", s)


def tile_xy(tile):
    m = TILE_RE.match(tile or "")
    if not m:
        return None
    return (m.group(1), int(m.group(2)), int(m.group(3)))


def cluster_tiles(tiles):
    """Union tiles that touch (Chebyshev distance <= 1) WITHIN one map prefix.

    🛑 A CLUSTER IS A HINT, NOT A FINDING. Adjacent overworld tiles are 256m apart, so a run
    of them usually means one contiguous piece of ground got the same nearest-neighbour hop --
    which is why the Consecrated Snowfield rows clump. It is not evidence that the hop was
    wrong, and the page says so beside the list. Clusters of one are dropped: a lone tile is
    not a pattern.
    """
    pts = {}
    for t in tiles:
        xy = tile_xy(t)
        if xy:
            pts[t] = xy
    parent = {t: t for t in pts}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    ordered = sorted(pts)
    for i, a in enumerate(ordered):
        pa, xa, za = pts[a]
        for b in ordered[i + 1:]:
            pb, xb, zb = pts[b]
            if pa == pb and abs(xa - xb) <= 1 and abs(za - zb) <= 1:
                union(a, b)
    groups = {}
    for t in ordered:
        groups.setdefault(find(t), []).append(t)
    out, meta, n = {}, [], 0
    for root in sorted(groups):
        members = groups[root]
        if len(members) < 2:
            continue
        n += 1
        cid = "C%d" % n
        for t in members:
            out[t] = cid
        meta.append({"id": cid, "n": len(members),
                     "label": members[0] + (" ... " + members[-1] if len(members) > 1 else "")})
    return out, meta


def build(root):
    gf = os.path.join(root, "greenfield")
    er = os.path.join(gf, "eldenring")
    rows, comments = read_tsv(os.path.join(gf, "check_region_second_opinion.tsv"))
    triage_rows, triage_comments = read_tsv(os.path.join(gf, "check_region_triage.tsv"))

    # 🛑 Join on ap_id, never on the label. Labels carry disambiguating "(1)"/"(2)" suffixes
    # that the audit's own label does not always reproduce, and a name join over this corpus
    # is the exact mistake flag_lots.tsv has already cost this project once.
    triage = {r["ap_id"]: r for r in triage_rows if r.get("ap_id")}

    units = {}
    for r in rows:
        flag = r.get("flag", "")
        if not flag:
            continue
        u = units.get(flag)
        if u is None:
            u = units[flag] = {
                "key": "f" + flag,
                "flag": int(flag),
                "ap_ids": [],
                "verdict": r["verdict"],
                "our_region": r.get("our_region", ""),
                "external_regions": [],
                "item": r.get("item", ""),
                "source": r.get("source", ""),
                "page_title": r.get("page_title", ""),
                "scope": r.get("scope", ""),
                "tile": r.get("map_tile", ""),
                "how": r.get("how", ""),
                "name": strip_label(r.get("label", "")),
                # The vote is a property of the FLAG (it is computed from the flag's one MSB
                # position), so the first row of a multi-ap-id flag carries it for all of them.
                "vote_region": r.get("msb_vote_region", ""),
                "vote_distance": r.get("vote_distance_m", ""),
                "vote_unanimous": r.get("vote_unanimous", ""),
                "vote_anchor": r.get("vote_anchor_grace", ""),
                "vote_note": r.get("vote_note", ""),
                "rows": 0,
            }
        u["rows"] += 1
        if r.get("ap_id") and r["ap_id"] not in u["ap_ids"]:
            u["ap_ids"].append(r["ap_id"])
        for x in (r.get("external_regions") or "").split(","):
            x = x.strip()
            if x and x not in u["external_regions"]:
                u["external_regions"].append(x)
        # A flag's rows should not disagree about the verdict -- but if the audit ever emits
        # rows that do, take the MOST SEVERE rather than the last one read, because silently
        # keeping whichever row happened to be last would hide the disagreement entirely.
        if VERDICT_ORDER.index(r["verdict"]) < VERDICT_ORDER.index(u["verdict"]):
            u["verdict"] = r["verdict"]

    clusters, cluster_meta = cluster_tiles({u["tile"] for u in units.values()})

    out = []
    for flag in sorted(units, key=lambda f: int(f)):
        u = units[flag]
        u["ap_ids"] = sorted(u["ap_ids"], key=lambda a: (len(a), a))
        u["cluster"] = clusters.get(u["tile"], "")
        t = triage.get(u["ap_ids"][0]) if u["ap_ids"] else None
        if t:
            u["how"] = t.get("how") or u["how"]
            u["grace_says"] = "" if t.get("grace_says", "-") in ("", "-") else t["grace_says"]
            u["kick_row_says"] = ("" if t.get("kick_row_says", "-") in ("", "-")
                                  else t["kick_row_says"])
        else:
            u["grace_says"] = u["kick_row_says"] = ""
        # WHO the vote backs -- the only actionable thing about it. "both" means it backs
        # neither us nor the wiki, which is the rarest and most interesting row on the page.
        if not u["vote_region"]:
            u["vote_side"] = "none"
        elif u["vote_region"] == u["our_region"]:
            u["vote_side"] = "ours"
        elif u["vote_region"] in u["external_regions"]:
            u["vote_side"] = "wiki"
        else:
            u["vote_side"] = "both"
        u["vote_suspect"] = "SUSPECT-ANCHOR" in u["vote_note"]
        # A RULING is a separate KIND of answer, not a fifth opinion: it keeps its vote_side (who
        # it happens to back is still worth filtering on) and carries its own class and badge.
        u["vote_ruled"] = "PLAYAREA-CONFIRMED" in u["vote_note"]
        base = SOURCE_BASE.get(u["source"])
        u["url"] = (base + u["page_title"].replace(" ", "_")) if (base and u["page_title"]) else ""
        u["hay"] = " ".join([
            u["name"], u["item"], str(u["flag"]), " ".join(u["ap_ids"]), u["tile"],
            u["our_region"], " ".join(u["external_regions"]), u["page_title"], u["source"],
            u["verdict"], u["cluster"], u["vote_region"], u["vote_anchor"], u["vote_note"],
        ]).lower()
        out.append(u)

    # Sorted by verdict severity, then by tile so a cluster reads as a block, then by flag.
    out.sort(key=lambda u: (VERDICT_ORDER.index(u["verdict"]), u["tile"], u["flag"]))

    counts = {}
    for u in out:
        counts[u["verdict"]] = counts.get(u["verdict"], 0) + 1
    vote_counts = {}
    for u in out:
        vote_counts[u["vote_side"]] = vote_counts.get(u["vote_side"], 0) + 1

    footer = (
        "<b>Worksheet, not a verdict.</b> Rulings live only in this browser (localStorage) "
        "until you export them; nothing here is read by generation. "
        "Sources: <b>Eldenpedia</b> (eldenring.wiki.gg) content CC BY-SA 4.0; "
        "<b>Elden Ring Wiki on Fandom</b> (eldenring.fandom.com) content CC BY-SA 3.0, used as "
        "fallback. <b>Fextralife was deliberately not consulted.</b> ERDB (MIT) was probed and "
        "not used. Only page titles and links are carried -- no wiki prose is in this repo. "
        "Produced by <code>tools/audit_region_second_opinion.py</code>; rendered by "
        "<code>tools/build_region_second_opinion_page.py</code>."
    )

    meta = {
        "stamp": data_stamp(os.path.join(er, "data.py")),
        "vote_counts": vote_counts,
        "vote_sides": [list(p) for p in VOTE_SIDES],
        # Verbatim from the tool that computed the votes -- paraphrasing a calibration is how a
        # calibration becomes a claim of exactness.
        "vote_caveat": VOTE_CAVEAT,
        "vote_suspect_note": VOTE_SUSPECT_NOTE,
        "vote_ruling_note": VOTE_RULING_NOTE,
        "vote_ruled_count": sum(1 for u in out if u["vote_ruled"]),
        "rows": len(rows),
        "counts": counts,
        "verdict_order": VERDICT_ORDER,
        "verdict_why": VERDICT_WHY,
        "adjudications": [list(p) for p in ADJUDICATIONS],
        "export_header": EXPORT_HEADER,
        "clusters": cluster_meta,
        "cluster_note": ("adjacent m60 tiles that share the nearest-neighbour hop. A HINT, not "
                         "a finding -- contiguous ground legitimately looks like this."),
        # Carried VERBATIM, per the check-browser convention: a tsv header states its own
        # caveats and paraphrasing one is how a caveat becomes its own opposite.
        "caveats": {"second_opinion": comments, "triage": triage_comments},
        "footer": footer,
    }
    return {"meta": meta, "units": out}


def render(payload):
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "region_second_opinion_template.html")
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return tpl.replace("/*__DATA__*/null", blob)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO, help="repo root (default: parent of tools/)")
    ap.add_argument("--out", default=None, help="output html (default: <repo>/%s)" % DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed page differs from a fresh build")
    args = ap.parse_args()
    out_path = args.out or os.path.join(args.repo, DEFAULT_OUT)
    payload = build(args.repo)
    html = render(payload)

    if args.check:
        if not os.path.exists(out_path):
            print("MISSING %s -- run: python tools/build_region_second_opinion_page.py" % out_path)
            return 1
        with open(out_path, encoding="utf-8", newline="") as fh:
            have = fh.read().replace("\r\n", "\n")
        if have != html:
            print("STALE %s -- run: python tools/build_region_second_opinion_page.py" % out_path)
            return 1
        print("fresh: %s" % out_path)
        return 0

    # newline='\n' so a Windows regen and a Linux regen produce the SAME bytes; the CI
    # staleness gate is a git diff and CRLF here would make it red on a platform swap.
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print(json.dumps({"rows": payload["meta"]["rows"],
                      "units": len(payload["units"]),
                      "counts": payload["meta"]["counts"],
                      "clusters": len(payload["meta"]["clusters"]),
                      "stamp": payload["meta"]["stamp"]}, indent=2, sort_keys=True))
    print("wrote %s (%.2f MB)" % (out_path, os.path.getsize(out_path) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
