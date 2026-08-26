#!/usr/bin/env python3
"""Second opinion on the "(region unconfirmed)" checks, from permissively-licensed OUTSIDE data.

WHY. 305 rows in `greenfield/check_region_triage.tsv` carry `how=GUESSED`: their region came
from `tile_pr()`'s nearest-neighbour hop, not from first-hand evidence for their tile. That is a
derivation that CANNOT FAIL (CONTRIBUTING rule 1), so every one of them is a confident answer
that may be wrong, and nothing in this repo can tell us which. This tool asks a second, INDEPENDENT
corpus -- a community wiki -- where the vanilla item at that flag is found, and prints AGREE /
DISAGREE / AMBIGUOUS / NO-DATA per check. It is a CANDIDATE list for hand-adjudication, never an
authority: it does not edit `data.py`, it does not gate CI, and a DISAGREE is a question, not a fix.

SOURCES AND LICENSES
  * Eldenpedia -- https://eldenring.wiki.gg/ -- content CC BY-SA 4.0. Primary. Queried through
    the public MediaWiki `api.php` (action=parse&prop=wikitext).
  * Elden Ring Wiki (Fandom) -- https://eldenring.fandom.com/ -- content CC BY-SA 3.0. Fallback,
    same API shape, consulted only when Eldenpedia has no page for the item.
  * ERDB -- https://github.com/EldenRingDatabase/erdb -- MIT. Evaluated for this tool and NOT used
    as a location source: ERDB ships datamined PARAM json (stats, ids, shop lineups), which carries
    no world-placement/area field for a ground pickup. `--probe-sources` reports its reachability
    so the finding stays re-checkable rather than remembered.
  * Fextralife is DELIBERATELY NOT CONSULTED, at Alaric's instruction. Do not add it.

LICENSE DISCIPLINE -- the point of the exercise. No wiki PROSE ever reaches the repository. What
this tool takes off a wiki page is the set of `[[Wikilink]]` TARGETS inside the acquisition section
-- proper nouns, i.e. place names -- which it immediately normalizes into OUR region vocabulary and
throws the rest away. What it writes is our own verdict, our own region names, and the page TITLE as
a citation. Raw API responses are cached for re-runs, but the cache is off-repo by default
(`--cache`, defaults outside the tree) and must never be committed.

WHAT IT CANNOT DO -- read this before believing a number.
  * The join key to the outside world is the ITEM NAME, and an item is not a location. A
    `Golden Rune [1]` lies in a hundred places; no wiki page can say which of them this flag is.
    Those rows are answered `AMBIGUOUS-GENERIC` from a hand-written list (GENERIC_ITEMS) WITHOUT a
    network call -- an honest refusal, not a shrug, and it is the single largest bucket.
  * ABSENCE IS WEAK EVIDENCE. These wikis are thinner than the one we are not allowed to use.
    `NO-DATA` means "we could not read it here", never "the check is fine".
  * An AGREE is corroboration of the REGION, not of the tile. Two independent guesses can agree.

THE MSB VOTE (the `msb_vote_*` columns). Beside the wiki verdict every row now carries a SECOND,
offline second opinion computed from our own committed coordinates: `tools/msb_region_vote.py`
folds the check's MSB position into the overworld frame and votes the region of the nearest
region-attributed Site of Grace. It needs no network and runs in `--offline` mode too. It is a
RANKING signal (90.1% on a 2607-row control set of checks whose region is NOT unconfirmed), NOT
an adjudicator, and it is NOT independent of the hop that produced these regions -- both are
nearest-neighbour derivations, so an agreement between them corroborates nothing. Rows it cannot
vote on say so in `vote_note` (`NO-COORDS` / `NO-ANCHOR`); rows whose anchoring grace got its own
region from a tile-default row say `SUSPECT-ANCHOR`. The exact instrument is the PlayArea
point-in-volume test -- see `docs/PLAYAREA-ITEM-SCAN.md`.

Run:
  python3 tools/audit_region_second_opinion.py --probe-sources
  python3 tools/audit_region_second_opinion.py --limit 40 --out greenfield/check_region_second_opinion.tsv
  python3 tools/audit_region_second_opinion.py --offline      # cache-only; no network
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msb_region_vote  # noqa: E402  -- sibling module, same tools/ dir

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIAGE = os.path.join(REPO, "greenfield", "check_region_triage.tsv")
FLAG_LOTS = os.path.join(REPO, "greenfield", "flag_lots.tsv")

UNCONFIRMED = " (region unconfirmed)"
USER_AGENT = ("er-archipelago-region-audit/1.0 "
              "(https://github.com/4laric/er-archipelago; research, low rate)")

SOURCES = [
    ("eldenpedia", "https://eldenring.wiki.gg/api.php", "CC BY-SA 4.0"),
    ("fandom", "https://eldenring.fandom.com/api.php", "CC BY-SA 3.0"),
]
# Probed, reported, and deliberately not used as a location source -- see the module docstring.
ERDB_PROBE = "https://api.github.com/repos/EldenRingDatabase/erdb"

# ---------------------------------------------------------------------------
# OUR mapping table. This is our own work (not wiki content): it maps the area
# vocabulary an outside corpus uses onto `eldenring.data.REGIONS`. Keys are
# lowercased wikilink targets; the FIRST matching key by longest length wins, so
# "liurnia of the lakes" must not be shadowed by "liurnia".
# A value of None means "a real place we recognise that is NOT one of our region
# buckets" -- recorded as recognised-but-unmapped rather than silently dropped,
# because a silent drop is how an empty result becomes a clean run (rule 2).
# ---------------------------------------------------------------------------
AREA_ALIASES = {
    "limgrave": "Limgrave",
    "west limgrave": "Limgrave",
    "east limgrave": "Limgrave",
    "the mistwood": "Limgrave",
    "mistwood": "Limgrave",
    "stormhill": "Limgrave",
    "stormfoot catacombs": "Limgrave",
    "summonwater village": "Limgrave",
    "fringefolk hero's grave": "Limgrave",
    "the weeping peninsula": "Weeping",
    "weeping peninsula": "Weeping",
    "castle morne": "Weeping",
    "liurnia of the lakes": "Liurnia",
    "liurnia": "Liurnia",
    "lake of rot": "Ainsel River",
    "the four belfries": "Liurnia",
    "the four belfrys": "Liurnia",
    "caria manor": "Liurnia",
    "bellum highway": "Liurnia",
    "raya lucaria academy": "Raya Lucaria Academy",
    "academy of raya lucaria": "Raya Lucaria Academy",
    "stormveil castle": "Stormveil",
    "caelid": "Caelid",
    "swamp of aeonia": "Caelid",
    "dragonbarrow": "Caelid",
    "greyoll's dragonbarrow": "Caelid",
    "redmane castle": "Caelid",
    "altus plateau": "Altus",
    "the altus plateau": "Altus",
    "leyndell, royal capital": "Leyndell",
    "leyndell, ashen capital": "Leyndell",
    "leyndell": "Leyndell",
    "subterranean shunning-grounds": "Leyndell",
    "mt. gelmir": "Mt. Gelmir",
    "mount gelmir": "Mt. Gelmir",
    "volcano manor": "Mt. Gelmir",
    "mountaintops of the giants": "Mountaintops of the Giants",
    "the mountaintops of the giants": "Mountaintops of the Giants",
    "flame peak": "Mountaintops of the Giants",
    "giants' mountaintop catacombs": "Mountaintops of the Giants",
    "castle sol": "Consecrated Snowfield",
    "consecrated snowfield": "Consecrated Snowfield",
    "miquella's haligtree": "Haligtree",
    "elphael, brace of the haligtree": "Haligtree",
    "haligtree": "Haligtree",
    "crumbling farum azula": "Farum Azula",
    "farum azula": "Farum Azula",
    "siofra river": "Siofra River",
    "nokron, eternal city": "Siofra River",
    "ainsel river": "Ainsel River",
    "nokstella, eternal city": "Ainsel River",
    "lands between underground": None,
    "deeproot depths": "Deeproot Depths",
    "mohgwyn palace": "Mohgwyn",
    "mohgwyn dynasty mausoleum": "Mohgwyn",
    "roundtable hold": None,
    "the lands between": None,
    "gravesite plain": "Gravesite",
    "belurat, tower settlement": "Belurat",
    "belurat": "Belurat",
    "castle ensis": "Ensis",
    "scadu altus": "Scadu Altus",
    "shadow keep": "Shadow Keep",
    "specimen storehouse": "Shadow Keep",
    "abyssal woods": "Abyssal",
    "the abyssal woods": "Abyssal",
    "cerulean coast": "Cerulean",
    "jagged peak": "Jagged Peak",
    "rauh base": "Rauh Base",
    "ancient ruins of rauh": "Ancient Ruins",
    "enir-ilim": "Enir Ilim",
    "enir ilim": "Enir Ilim",
    "realm of shadow": None,
    "the shadow realm": None,
}

# ---------------------------------------------------------------------------
# Items whose vanilla copies are scattered across the world. An item name cannot
# identify a PLACEMENT for these, so no outside page can adjudicate the row and
# we refuse the question instead of asking it. Matched case-insensitively; a
# trailing "[n]" upgrade bracket is stripped before the test.
# ---------------------------------------------------------------------------
GENERIC_ITEMS = {
    "golden rune", "smithing stone", "somber smithing stone", "rune arc",
    "stonesword key", "grace mimic", "furlcalling finger remedy", "lands between rune",
    "arteria leaf", "beast blood", "beast liver", "bloodrose", "crystal dart",
    "exalted flesh", "fire blossom", "four-toed fowl foot", "gold-pickled fowl foot",
    "gold firefly", "smoldering butterfly", "starlight shards", "warming stone",
    "old fang", "strip of white flesh", "mushroom", "trina's lily", "herba",
    "root resin", "cracked pot", "ritual pot", "throwing dagger", "fan daggers",
    "kukri", "poisonbone dart", "explosive bolt", "explosive greatbolt", "burred bolt",
    "golden arrow", "golden bolt", "bone arrow", "bone bolt", "great arrow",
    "celestial dew", "rowa fruit", "dappled cured meat", "dappled white cured meat",
    "sacrificial twig", "festering bloody finger", "bewitching branch",
    "albinauric bloodclot", "dragonwound grease", "blood grease", "freezing grease",
    "drawstring holy grease", "holy grease", "fire grease", "magic grease",
    "lightning grease", "soap", "invigorating cured meat", "neutralizing boluses",
    "stanching boluses", "thawfrost boluses", "preserving boluses", "flame, grant me strength",
    "nascent butterfly", "silver firefly", "budding cave moss", "cave moss",
    "erdleaf flower", "melted mushroom", "poisonbloom", "sanctuary stone",
    "smithing-stone key", "hefty beast bone", "thin beast bone", "string",
    "human bone shard", "great dragonfly head", "slumbering egg", "livid glowstone",
    "glowstone", "cuckoo glintstone", "crystal bud", "somber ancient dragon smithing stone",
    "ancient dragon smithing stone", "golden centipede",
    # Dropped by every Great/Full-grown dragon in the game -- an item, not a place.
    "dragon heart", "somber smithing stone key",
}

VERDICTS = ("AGREE", "DISAGREE", "AMBIGUOUS", "AMBIGUOUS-GENERIC", "NO-DATA")

_UPGRADE = re.compile(r"\s*\[\d+\]\s*$")
_PREFIX = re.compile(r"^\[(?:Incantation|Sorcery|Spell|Ash of War)\]\s*")
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_SECTION = re.compile(
    r"^=+\s*(?:acquisition|location|locations|where to find|availability|obtained)\b[^=]*=+\s*$",
    re.I)


# --------------------------------------------------------------------------- names

def item_name_from_label(label):
    """The item name a check label carries. Our own format, parsed by us.

    'Liurnia :: Snow Witch Hat - near Royal Moongazing Grounds (region unconfirmed) [f...]'
    -> 'Snow Witch Hat'
    """
    if label is None:
        return ""
    body = label.split(" :: ", 1)[1] if " :: " in label else label
    body = body.split(" [f", 1)[0]
    body = body.replace(UNCONFIRMED, " ")
    body = re.sub(r"\s*\(\d+\)\s*$", "", body)
    # ' - near X' / ' - from X' / ' - m60_33_41' are OUR positional hints, not the item.
    body = re.split(r"\s+-\s+", body, 1)[0]
    body = _PREFIX.sub("", body)
    return body.strip()


def is_generic(item):
    """True when the item name cannot identify a placement (many vanilla copies)."""
    base = _UPGRADE.sub("", (item or "")).strip().lower()
    if not base:
        return True
    return base in GENERIC_ITEMS


def normalize_area(link):
    """One wikilink target -> (our region | None), plus whether we recognised it at all."""
    key = (link or "").strip().lower().rstrip(".,;:")
    key = re.sub(r"\s+", " ", key)
    if key in AREA_ALIASES:
        return AREA_ALIASES[key], True
    # Longest-suffix/containment pass, longest key first so "liurnia of the lakes"
    # is tried before "liurnia".
    for alias in sorted(AREA_ALIASES, key=len, reverse=True):
        if alias in key:
            return AREA_ALIASES[alias], True
    return None, False


def regions_from_wikitext(text):
    """Region names an item page implies, plus which slice of the page they came from.

    Returns (regions, unmapped, scope). Only wikilink TARGETS are read; no sentence
    of the page is retained, returned, or written anywhere.
    """
    if not text:
        return [], [], "none"
    lines = text.splitlines()
    section, taking = [], False
    for line in lines:
        if line.strip().startswith("="):
            taking = bool(_SECTION.match(line.strip()))
            continue
        if taking:
            section.append(line)
    scope = "acquisition"
    body = "\n".join(section)
    if not body.strip():
        # No acquisition heading (short pages often have none). Fall back to the whole
        # page and SAY SO -- a page-wide read is weaker evidence and the report shows it.
        body, scope = text, "page-wide"
    regions, unmapped = [], []
    for link in _WIKILINK.findall(body):
        mapped, known = normalize_area(link)
        if mapped and mapped not in regions:
            regions.append(mapped)
        elif known and mapped is None:
            if link not in unmapped:
                unmapped.append(link)
    return regions, unmapped, scope


def verdict_for(our_region, external_regions, generic=False, had_page=True):
    """Our verdict, in our words. Absence is weak evidence and says NO-DATA."""
    if generic:
        return "AMBIGUOUS-GENERIC"
    ext = list(dict.fromkeys(external_regions or []))
    if not ext:
        return "NO-DATA"
    if our_region in ext:
        return "AGREE"
    if len(ext) >= 3:
        # A page that name-drops three or more regions is describing a journey, not a
        # placement. Refuse rather than manufacture a DISAGREE.
        return "AMBIGUOUS"
    return "DISAGREE"


# --------------------------------------------------------------------------- inputs

def load_targets(triage_path=TRIAGE, lots_path=FLAG_LOTS):
    """Every `(region unconfirmed)` triage row, with its lot's item names.

    flag_lots is joined on the FLAG column -- never on `name` (one name, many lots).
    Rows are COUNTED, not silently dropped (rule 4).
    """
    with open(triage_path, encoding="utf-8") as fh:
        body = [ln for ln in fh if not ln.startswith("#")]
    rows = list(csv.DictReader(body, delimiter="\t"))
    lots = {}
    if os.path.isfile(lots_path):
        with open(lots_path, encoding="utf-8") as fh:
            for lot in csv.DictReader(fh, delimiter="\t"):
                lots.setdefault(lot["flag"], []).append(lot)
    else:
        raise SystemExit("flag_lots.tsv missing at %s -- refusing to run half-blind" % lots_path)
    targets, skipped = [], 0
    for row in rows:
        if UNCONFIRMED not in row.get("label", ""):
            skipped += 1
            continue
        flag = row["flag"]
        lot_names = [l["name"] for l in lots.get(flag, []) if l.get("name")]
        item = item_name_from_label(row["label"])
        if not item and lot_names:
            item = lot_names[0]
        targets.append({
            "flag": flag,
            "ap_id": row["ap_id"],
            "map_tile": row["map_tile"],
            "our_region": row["region"],
            "how": row["how"],
            "label": row["label"],
            "item": item,
            "lot_items": sorted(set(lot_names)),
        })
    return targets, skipped


# --------------------------------------------------------------------------- network

class Wiki:
    """A politely rate-limited MediaWiki reader with an off-repo response cache."""

    def __init__(self, cache_dir, delay=1.0, offline=False, timeout=25):
        self.cache_dir = cache_dir
        self.delay = delay
        self.offline = offline
        self.timeout = timeout
        self.hits = self.misses = self.errors = 0
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, source, title):
        safe = re.sub(r"[^A-Za-z0-9._+-]", "_", title)[:120]
        return os.path.join(self.cache_dir, "%s__%s.json" % (source, safe))

    def wikitext(self, source, api, title):
        path = self._cache_path(source, title)
        if os.path.isfile(path):
            self.hits += 1
            with open(path, encoding="utf-8") as fh:
                return json.load(fh).get("wikitext")
        if self.offline:
            return None
        self.misses += 1
        params = urllib.parse.urlencode({
            "action": "parse", "page": title, "prop": "wikitext",
            "redirects": "1", "format": "json", "formatversion": "1",
        })
        req = urllib.request.Request(api + "?" + params, headers={"User-Agent": USER_AGENT})
        text = None
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if "parse" in payload:
                text = payload["parse"]["wikitext"]["*"]
        except Exception as exc:  # noqa: BLE001 -- a fetch failure is data, not a crash
            self.errors += 1
            sys.stderr.write("  fetch failed %s %r: %s\n" % (source, title, exc))
        finally:
            time.sleep(self.delay)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"wikitext": text, "title": title, "source": source}, fh)
        return text


def probe_sources(timeout=20):
    """Reachability, reported per source. A blocked source is a FINDING, not a retry."""
    out = []
    for name, api, lic in SOURCES:
        url = api + "?action=query&meta=siteinfo&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ok = resp.status == 200
            out.append((name, lic, "REACHABLE" if ok else "HTTP %s" % resp.status))
        except Exception as exc:  # noqa: BLE001
            out.append((name, lic, "UNREACHABLE (%s)" % exc))
    try:
        req = urllib.request.Request(ERDB_PROBE, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.loads(resp.read().decode("utf-8"))
        out.append(("erdb", "MIT", "REACHABLE via GitHub; carries no location field -- not used"))
    except Exception as exc:  # noqa: BLE001
        out.append(("erdb", "MIT", "UNREACHABLE (%s)" % exc))
    return out


# --------------------------------------------------------------------------- report

REPORT_COLUMNS = [
    "verdict", "our_region", "external_regions", "flag", "ap_id", "map_tile",
    "item", "source", "page_title", "scope", "how", "label",
] + msb_region_vote.VOTE_COLUMNS

REPORT_HEADER = """\
# Second opinion on the "(region unconfirmed)" checks -- tools/audit_region_second_opinion.py
#
# Sources: Eldenpedia (eldenring.wiki.gg, CC BY-SA 4.0); Elden Ring Wiki on Fandom
# (eldenring.fandom.com, CC BY-SA 3.0) as fallback. ERDB (MIT) probed and not used: its
# datamined params carry no placement field. Fextralife is deliberately not consulted.
#
# No wiki prose is reproduced here. Every cell is a region name from OUR vocabulary, an id
# from OUR tables, a page TITLE used as a citation, or a verdict in OUR words.
#
# This is a CANDIDATE list for hand-adjudication, not a cull list and not a fix list.
# NO-DATA means "not readable there" -- absence on a thin wiki is WEAK evidence that
# says nothing about whether the check's region is right.
#
# The msb_vote_* columns are a SECOND and SEPARATE opinion, computed offline from our own
# committed MSB coordinates (tools/msb_region_vote.py): the region of the nearest
# region-attributed Site of Grace, once the check is folded into the overworld frame.
# %s
# It is NOT independent of the nearest-neighbour hop that produced these regions in the first
# place, so a vote that AGREES with us corroborates nothing. vote_note: NO-COORDS (no MSB row),
# NO-ANCHOR (no region-attributed grace in that frame), SUSPECT-ANCHOR (the anchoring grace's
# own region came from a tile-default row, so the vote inherits a tile-wide guess),
# CROSS-TILE-MSB (the coords are authored on a different fine-grid tile than the label names),
# COARSE-LOD (the coords row is on a LOD1/2 tile -- folded correctly, but coarser).
""" % msb_region_vote.CALIBRATION


def write_report(rows, path):
    """The tsv report. Deterministic order: DISAGREE first, then by flag."""
    order = {"DISAGREE": 0, "AMBIGUOUS": 1, "AGREE": 2, "NO-DATA": 3, "AMBIGUOUS-GENERIC": 4}
    rows = sorted(rows, key=lambda r: (order.get(r["verdict"], 9), int(r["flag"])))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(REPORT_HEADER)
        # restval="" so a --no-vote run writes EMPTY vote cells rather than dying on the
        # missing keys: an absent opinion is a blank, and a blank is honest.
        writer = csv.DictWriter(fh, fieldnames=REPORT_COLUMNS, delimiter="\t",
                                extrasaction="ignore", restval="", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            ext = out.get("external_regions") or []
            out["external_regions"] = ",".join(ext) if isinstance(ext, list) else ext
            writer.writerow(out)
    return path


def summarize(rows):
    counts = {v: 0 for v in VERDICTS}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return counts



def _vote_cell(row):
    """The vote as one markdown cell. Empty when there is none -- and the NOTE is carried, because
    a distance without SUSPECT-ANCHOR beside it reads as a measurement rather than a guess."""
    if not row.get("msb_vote_region"):
        return row.get("vote_note", "") or "--"
    bits = "%s @ %sm" % (row["msb_vote_region"], row.get("vote_distance_m", "?"))
    if row.get("vote_unanimous") == "no":
        bits += ", top-3 split"
    if row.get("vote_note"):
        bits += " (%s)" % row["vote_note"]
    return bits


def _vote_section(rows):
    """The MSB-vote roll-up. Numbers first, then the rows where the vote and our region differ --
    which is the whole point of the column: it ORDERS the reading, it does not settle anything."""
    cast = [r for r in rows if r.get("msb_vote_region")]
    against = [r for r in cast if r["msb_vote_region"] != r["our_region"]]
    suspect = [r for r in against if "SUSPECT-ANCHOR" in (r.get("vote_note") or "")]
    out = ["## MSB nearest-grace vote", ""]
    out.append("A second and SEPARATE opinion, computed offline from our own committed MSB")
    out.append("coordinates (`tools/msb_region_vote.py`): fold the check into the overworld frame,")
    out.append("vote the region of the nearest region-attributed Site of Grace.")
    out.append("")
    out.append("**%s**" % msb_region_vote.CALIBRATION)
    out.append("")
    out.append("It is NOT independent of the nearest-neighbour hop that produced these regions, so a")
    out.append("vote that AGREES with us corroborates nothing; a vote that disagrees is a QUESTION.")
    out.append("")
    out.append("| | rows |")
    out.append("| --- | ---: |")
    out.append("| vote cast | %d |" % len(cast))
    out.append("| vote backs our region | %d |" % (len(cast) - len(against)))
    out.append("| vote disagrees with our region | %d |" % len(against))
    out.append("| of those, on a SUSPECT-ANCHOR grace | %d |" % len(suspect))
    out.append("| no vote (no coords / no anchor) | %d |" % (len(rows) - len(cast)))
    out.append("")
    if against:
        out.append("### Votes against our region")
        out.append("")
        out.append("| flag | tile | our region | wiki | msb vote | anchor grace | verdict |")
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in sorted(against, key=lambda r: int(r["flag"])):
            ext = row["external_regions"]
            out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                row["flag"], row["map_tile"], row["our_region"],
                (",".join(ext) if isinstance(ext, list) else ext) or "--",
                _vote_cell(row), row.get("vote_anchor_grace", ""), row["verdict"]))
        out.append("")
    return out


def write_markdown(rows, counts, path, probes=None):
    lines = ["# Region second opinion -- run report", ""]
    lines.append("Sources: Eldenpedia (CC BY-SA 4.0), Fandom Elden Ring Wiki (CC BY-SA 3.0) as")
    lines.append("fallback, ERDB (MIT) probed and unused. Fextralife deliberately not consulted.")
    lines.append("No wiki prose is reproduced: only region names, ids, page titles and verdicts.")
    lines.append("")
    if probes:
        lines.append("## Reachability")
        lines.append("")
        for name, lic, status in probes:
            lines.append("- `%s` (%s): %s" % (name, lic, status))
        lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append("| verdict | rows |")
    lines.append("| --- | ---: |")
    for verdict in VERDICTS:
        lines.append("| %s | %d |" % (verdict, counts.get(verdict, 0)))
    lines.append("| **total** | **%d** |" % sum(counts.values()))
    lines.append("")
    lines.append("`AMBIGUOUS-GENERIC` is refused without a network call: the item has many vanilla")
    lines.append("copies, so no item page can name THIS placement. `NO-DATA` is weak evidence -- it")
    lines.append("means the page was missing or named no place we recognise, not that we are right.")
    lines.append("")
    lines.append("## DISAGREE")
    lines.append("")
    dis = [r for r in rows if r["verdict"] == "DISAGREE"]
    if not dis:
        lines.append("None.")
    else:
        lines.append("| flag | ap_id | tile | our region | external | item | source / page | msb vote |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in sorted(dis, key=lambda r: int(r["flag"])):
            lines.append("| %s | %s | %s | %s | %s | %s | %s / %s | %s |" % (
                row["flag"], row["ap_id"], row["map_tile"], row["our_region"],
                ",".join(row["external_regions"]), row["item"],
                row["source"], row["page_title"], _vote_cell(row)))
    lines.append("")
    lines.extend(_vote_section(rows))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


# --------------------------------------------------------------------------- driver

def audit(targets, wiki, verbose=False, voter=None):
    rows = []
    for i, tgt in enumerate(targets, 1):
        item = tgt["item"]
        row = dict(tgt)
        # The vote is attached to EVERY row, including the AMBIGUOUS-GENERIC ones the wiki
        # cannot speak about at all -- those 209 rows are precisely where a coordinate-based
        # opinion is the only opinion available.
        if voter is not None:
            row.update(voter.vote(tgt["flag"], tgt.get("map_tile", "")).as_columns())
        row["external_regions"] = []
        row["source"] = ""
        row["page_title"] = ""
        row["scope"] = ""
        if is_generic(item):
            row["verdict"] = "AMBIGUOUS-GENERIC"
            rows.append(row)
            continue
        for name, api, _lic in SOURCES:
            text = wiki.wikitext(name, api, item)
            if not text:
                continue
            regions, _unmapped, scope = regions_from_wikitext(text)
            row["source"], row["page_title"], row["scope"] = name, item, scope
            row["external_regions"] = regions
            if regions:
                break
        row["verdict"] = verdict_for(row["our_region"], row["external_regions"])
        rows.append(row)
        if verbose:
            sys.stderr.write("[%d/%d] %s -> %s %s\n" % (
                i, len(targets), item, row["verdict"], row["external_regions"]))
    return rows


def revote(out, markdown=None):
    """Recompute ONLY the msb_vote_* columns of an existing report, in place.

    Every other cell -- above all `verdict` and `external_regions`, which cost a rate-limited
    wiki crawl -- is carried through byte-for-byte from the file being rewritten.
    """
    if not os.path.exists(out):
        raise SystemExit("--revote needs an existing report at %s" % out)
    with open(out, encoding="utf-8-sig") as fh:
        lines = fh.readlines()
    body = [ln for ln in lines if not ln.startswith("#") and ln.strip()]
    rows = list(csv.DictReader(body, delimiter="\t"))
    # our_region/label/map_tile are RE-READ from the triage table, not carried: data.py moves
    # under this file (the Ancient Snow Valley cluster moved to Consecrated Snowfield after the
    # first crawl), and a worksheet that compares a fresh vote against a stale `our_region`
    # invents disagreements and hides real ones.
    fresh, _skipped = load_targets()
    fresh = {t["flag"]: t for t in fresh}
    refreshed = 0
    for row in rows:
        t = fresh.get(row["flag"])
        if not t:
            continue
        for col in ("our_region", "label", "map_tile", "how"):
            if row.get(col) != t[col]:
                refreshed += 1
            row[col] = t[col]
    print("refreshed %d stale cells from check_region_triage.tsv" % refreshed)
    voter = msb_region_vote.Voter.from_repo(REPO)
    print("msb vote: %d region-attributed graces, %d suspect tile-default anchors, %d rulings"
          % (len(voter.grace_region), len(voter.suspect), len(voter.play_area)))
    for row in rows:
        row.update(voter.vote(row["flag"], row.get("map_tile", "")).as_columns())
    counts = summarize(rows)
    write_report(rows, out)
    ruled = sum(1 for r in rows if msb_region_vote.NOTE_PLAYAREA in (r.get("vote_note") or ""))
    agree = sum(1 for r in rows if r.get("msb_vote_region") == r["our_region"])
    cast = sum(1 for r in rows if r.get("msb_vote_region"))
    print("revote: %d rows, %d cast, %d back our region, %d disagree, %d not votable, "
          "%d PLAYAREA-CONFIRMED rulings" % (len(rows), cast, agree, cast - agree,
                                             len(rows) - cast, ruled))
    if markdown:
        write_markdown(rows, counts, markdown)
    print("rewrote %s (vote columns only)" % out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(
        REPO, "greenfield", "check_region_second_opinion.tsv"))
    ap.add_argument("--markdown", default=None, help="also write a markdown run report here")
    ap.add_argument("--markdown-probe", action="store_true",
                    help="with --markdown, re-probe the sources so the report's reachability "
                         "section is a MEASUREMENT of this run, not a remembered one")
    ap.add_argument("--cache", default=os.environ.get(
        "ER_REGION_AUDIT_CACHE", os.path.join(os.path.expanduser("~"), ".cache",
                                              "er-region-audit")),
                    help="off-repo cache for raw API responses; NEVER commit it")
    ap.add_argument("--limit", type=int, default=0, help="first N targets only (batching)")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--offline", action="store_true", help="cache only; make no requests")
    ap.add_argument("--revote", action="store_true",
                    help="REFRESH THE VOTE COLUMNS OF THE COMMITTED TSV IN PLACE and exit. "
                         "The wiki verdict columns are read back from --out and carried "
                         "forward verbatim; nothing is fetched and nothing is re-derived from "
                         "the cache. 🛑 This exists because `--offline` on a box with no wiki "
                         "cache does not preserve `verdict`/`external_regions` -- it recomputes "
                         "them as NO-DATA and writes that, silently destroying the audit's "
                         "citations (rule 4: a rerun that loses an input must say so, not "
                         "quietly emit a smaller table). Use --revote whenever the only thing "
                         "that changed is tools/msb_region_vote.py.")
    ap.add_argument("--no-vote", action="store_true",
                    help="skip the offline MSB nearest-grace vote (leaves msb_vote_* empty)")
    ap.add_argument("--probe-sources", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.probe_sources:
        for name, lic, status in probe_sources():
            print("%-12s %-14s %s" % (name, lic, status))
        return 0

    if args.revote:
        return revote(args.out, args.markdown)

    targets, skipped = load_targets()
    print("triage rows skipped (not `(region unconfirmed)`): %d" % skipped)
    print("targets: %d" % len(targets))
    window = targets[args.offset:]
    if args.limit:
        window = window[:args.limit]
    print("this batch: %d (offset %d)" % (len(window), args.offset))

    wiki = Wiki(args.cache, delay=args.delay, offline=args.offline)
    voter = None if args.no_vote else msb_region_vote.Voter.from_repo(REPO)
    if voter is not None:
        print("msb vote: %d region-attributed graces, %d suspect tile-default anchors"
              % (len(voter.grace_region), len(voter.suspect)))
    rows = audit(window, wiki, verbose=args.verbose, voter=voter)
    counts = summarize(rows)
    write_report(rows, args.out)
    print("cache hits %d, fetches %d, fetch errors %d" % (wiki.hits, wiki.misses, wiki.errors))
    if voter is not None:
        agree = sum(1 for r in rows if r.get("msb_vote_region") == r["our_region"])
        cast = sum(1 for r in rows if r.get("msb_vote_region"))
        print("msb vote: %d cast, %d back our region, %d disagree, %d not votable"
              % (cast, agree, cast - agree, len(rows) - cast))
    for verdict in VERDICTS:
        print("%-18s %d" % (verdict, counts.get(verdict, 0)))
    if args.markdown:
        write_markdown(rows, counts, args.markdown,
                       probes=probe_sources() if args.markdown_probe else None)
    print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
