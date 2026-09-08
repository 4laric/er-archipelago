#!/usr/bin/env python3
r"""datamine_enemy_drops.py -- the enemy DEATH-DROP table, derived from OUR params.

WHY THIS EXISTS. `docs/MATT-ORACLE-ROADMAP.md` item 7 asks for an `enemy_drops` table derived from
`NpcParam` / `ItemLotParam_enemy` and count-checked against thefifthmatt's `enemy`-tagged slots.
Until now the only enemy-drop data in the tree was `tables/enemy_drops_data.py`
(`REROLLABLE_ENEMY_SLOTS`), which is the *inverse* population: the UNFLAGGED, farmable lots the
rerolling feature may touch. It says nothing about WHICH enemy drops WHAT, and nothing at all about
the flagged one-time drops -- the ones that are candidate CHECKS. `tools/matt_oracle.py` carried the
line "our enemy_drops table is a stub" as the reason his whole `enemy*` tag family is excluded from
class B. This is that table.

THE DERIVATION (one hop, no invention):

    NpcParam.itemLotId_enemy  ->  BASE lot in ItemLotParam_enemy
    base lot                  ->  the lot GROUP: base+0, base+1, ... while the row exists
    each lot row              ->  slots 1..8 (lotItemId0N / lotItemCategory0N / lotItemNum0N)
    slot weight               ->  lotItemBasePoint0N / SUM(all eight base points on that row)

  * THE GROUP RUNS FORWARD FROM THE BASE and STOPS at the first missing id **or at the next id that
    is itself another NpcParam's base**. ItemLotParam_enemy groups are banded in tens and the
    forward run is how `tools/gen_enemy_drop_entities.py` already walks them (`lot - lot%10`), but
    6 bands are not 10 wide and butt straight up against the next enemy's band. Without the
    next-base stop those 6 groups would steal the following enemy's drops and this table would
    assert, in a committed file, that an enemy drops something it does not.

  * A slot is one INDEPENDENT roll of its row: `chance_pct` is that slot's share of its own row's
    total weight, NOT of the enemy's whole drop table. The row's leftover weight is the "nothing"
    slot (`lotItemId0N == 0`), which is why the emitted chances for one lot usually sum to < 100.

POLARITY -- read `flag` first. `flag` is `getItemFlagId`:

    flag > 0   ONE-TIME drop. The game sets that acquisition flag on award and never rolls the lot
               again. These are the CHECK candidates: 243 rows reachable from an NpcParam.
    flag = ""  FARMABLE. Rolls every kill, forever. Not a check anywhere, and the population
               `REROLLABLE_ENEMY_SLOTS` is drawn from.

  The same polarity `datamine_flag_lots.py` uses (it keeps flag>0 and drops the rest). This tool
  keeps BOTH, because "which enemy drops this" is the question the table exists to answer and the
  farmable majority is most of the answer.

🛑 THIS TOOL ADDS NO AP LOCATIONS. Whether a flagged enemy drop becomes a check is a product
decision (an enemy-rando seed can delete the carrier -- see gen_enemy_drop_entities.py's docstring
on why the anchor has to be the placement EntityID, not the NpcParam). The table is evidence for
that decision, not the decision.

Emits `greenfield/enemy_drops.tsv` (tab-separated, utf-8, \n, sorted by npc_id,lot,slot):

    npc_id  npc_name  chr_id  lot  slot  category  item_id  full_id  item_name  num  chance_pct
            flag  map_id  part

  * npc_id     = NpcParam row id (the drop table's owner; NOT a placement -- one NpcParam is
                 usually many placed enemies)
  * npc_name   = tables/enemy_names.ENEMY_NAMES[chr_id], the game's own NpcName FMG string where it
                 ships one. BLANK for most rows and deliberately so: "Godrick Soldier" is a wiki
                 name, not a game string (see datamine_enemy_names.py). Nothing is invented here.
  * chr_id     = npc_id // 10000, the character MODEL (c<chr_id>)
  * lot        = the ItemLotParam_enemy row id
  * slot       = 1..8 (lotItemId0N)
  * category   = lotItemCategory0N (1 goods / 2 weapon / 3 protector / 4 accessory / 5 gem)
  * item_id    = lotItemId0N, the RAW id
  * full_id    = category nibble | item_id -- the AddItemFunc / ITEM_CATALOG space. The nibble is
                 DERIVED by gen_check_lots_table.derive_category_nibble, never declared here; that
                 function refuses to guess a category it cannot see, and hardcoding this mapping is
                 exactly how the vanilla-ware suppression bug shipped once already.
  * item_name  = ITEM_CATALOG reverse for full_id, else "" (only pooled items are in the catalog).
                 🛑 This column is a join against a COMMITTED table (tables/item_ids.py), not
                 against the params, so a catalog change alone makes this tsv stale. That is how
                 #1495 and #1497 turned main red the day both merged: each was green on its own
                 branch, and #1497 renamed the catalog entries #1495 had already baked in here.
                 `--check` prints the differing lines and the columns that moved so the log alone
                 tells you which of the two inputs shifted.
  * num        = lotItemNum0N (quantity awarded)
  * chance_pct = 100 * lotItemBasePoint0N / sum(lotItemBasePoint01..08), 4 dp
  * flag       = getItemFlagId when > 0 (one-time), else "" (farmable) -- see POLARITY above
  * map_id     = the map tile, ONLY where the flag has exactly ONE `source=enemy` placement in
                 greenfield/msb_flag_region.tsv. Blank where the flag has none or several: a
                 many-placement flag has no single map and this refuses to pick one.
  * part       = that single placement's MSB part name (`c<chr>_<instance>`), same condition

The AP placeholder goods id (8852) is skipped, as everywhere else.

    python tools/datamine_enemy_drops.py            # regenerate greenfield/enemy_drops.tsv
    python tools/datamine_enemy_drops.py --check    # CI drift gate (exit 1 if stale)
    python tools/datamine_enemy_drops.py --report   # flagged-drop summary from the COMMITTED tsv
                                                    #   (no artifacts needed, runs anywhere)

Artifacts: reads `elden_ring_artifacts/vanilla_er/vanilla_er/` under the repo, like
datamine_flag_lots.py. Override with env ER_ARTIFACTS_VV. `--check` re-derives, so it needs them
too -- and CI HAS them: the generators job runs `gen_inputs.py --ensure elden_ring_artifacts`
first, and gen_inputs.db carries every param CSV by glob. This is a real ubuntu gate, exactly like
`datamine_flag_lots.py --check` next to it, not a dev-box-only one.
"""
import argparse
import csv
import importlib.util
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
VV = os.environ.get("ER_ARTIFACTS_VV") or os.path.join(
    REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
OUT = os.path.join(REPO, "greenfield", "enemy_drops.tsv")

AP_PLACEHOLDER_GOODS = 8852   # must match gen_data.AP_PLACEHOLDER_GOODS
MSB_FLAG_REGION = os.path.join(REPO, "greenfield", "msb_flag_region.tsv")

COLUMNS = ("npc_id", "npc_name", "chr_id", "lot", "slot", "category", "item_id", "full_id",
           "item_name", "num", "chance_pct", "flag", "map_id", "part")

# The `#` preamble is the polarity note IN THE FILE, so a reader who opens the tsv without the tool
# still learns which rows are checks. check_maps.tsv does the same; readers below skip `#` lines.
PREAMBLE = """\
# AUTO-GENERATED by tools/datamine_enemy_drops.py -- DO NOT EDIT, re-emit.
# NpcParam.itemLotId_enemy -> the ItemLotParam_enemy lot GROUP (base+0.. while the row exists and is
# not another NpcParam's base) -> its 1..8 item slots. One row per (npc_id, lot, slot).
# POLARITY: flag>0 = ONE-TIME drop (getItemFlagId; the game never rolls it again -- a CHECK
# candidate). flag blank = FARMABLE, rolls on every kill, never a check.
# chance_pct is the slot's share of ITS OWN ROW's weight (the row's missing weight is the
# "nothing" slot), not of the enemy's whole drop table.
# npc_name is blank unless the game itself ships a name (tables/enemy_names.py); wiki names are
# not invented here. map_id/part are filled only where the flag has exactly ONE source=enemy
# placement in msb_flag_region.tsv.
# 🛑 No row here is an AP location. Whether flagged enemy drops become checks is a product ruling.
"""
HEADER = "\t".join(COLUMNS)


def _read_rows(path):
    """Rows of a `#`-prefaced tsv as dicts."""
    with open(path, encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().split("\n") if ln and not ln.startswith("#")]
    if not lines:
        return []
    cols = lines[0].split("\t")
    return [dict(zip(cols, ln.split("\t"))) for ln in lines[1:]]


def _enemy_names():
    """chr_id -> display name, from the committed tables/enemy_names.py (no FMG read needed)."""
    src = os.path.join(REPO, "greenfield", "eldenring", "tables", "enemy_names.py")
    if not os.path.isfile(src):
        return {}
    spec = importlib.util.spec_from_file_location("_ed_enemy_names", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.ENEMY_NAMES)


def _catalog_by_full():
    """FullID -> display name, from the committed catalog (item_ids.ITEM_CATALOG)."""
    src = os.path.join(REPO, "greenfield", "eldenring", "tables", "item_ids.py")
    if not os.path.isfile(src):
        return {}
    text = open(src, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"'([^']+)'\s*:\s*(\d+),", text):
        out.setdefault(int(m.group(2)), m.group(1))
    return out


def _single_placements():
    """flag -> (map_id, part) for flags with EXACTLY ONE source=enemy row in msb_flag_region.tsv."""
    if not os.path.isfile(MSB_FLAG_REGION):
        return {}
    seen = defaultdict(set)
    for r in _read_rows(MSB_FLAG_REGION):
        if r.get("source") != "enemy":
            continue
        try:
            seen[int(r["flag"])].add((r["map_id"], r["treasure_name"]))
        except (KeyError, ValueError):
            continue
    return {f: next(iter(v)) for f, v in seen.items() if len(v) == 1}


def _load_lots():
    p = os.path.join(VV, "ItemLotParam_enemy.csv")
    if not os.path.isfile(p):
        raise SystemExit("FATAL: %s missing -- elden_ring_artifacts required" % p)
    out = {}
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                out[int(r["ID"])] = r
            except (KeyError, ValueError):
                continue
    if not out:
        raise SystemExit("FATAL: %s has no rows" % p)
    return out


def _load_npcs():
    p = os.path.join(VV, "NpcParam.csv")
    if not os.path.isfile(p):
        raise SystemExit("FATAL: %s missing -- elden_ring_artifacts required" % p)
    out = []
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                npc_id = int(r["ID"])
                base = int(r.get("itemLotId_enemy", 0) or 0)
            except (KeyError, ValueError, TypeError):
                continue
            if npc_id < 0 or base <= 0:
                continue
            out.append((npc_id, base))
    if not out:
        raise SystemExit("FATAL: %s yielded no itemLotId_enemy rows" % p)
    return sorted(out)


def _int(row, key):
    try:
        return int(row.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0


def lot_group(base, lots, bases):
    """base -> [base, base+1, ...] while the row exists and is not another NpcParam's base."""
    out = []
    k = 0
    while base + k in lots and (k == 0 or base + k not in bases):
        out.append(base + k)
        k += 1
    return out


def _nibbles(rows_by_cat):
    """lotItemCategory -> FullID nibble, DERIVED by the existing gen_check_lots_table logic."""
    src = os.path.join(HERE, "gen_check_lots_table.py")
    spec = importlib.util.spec_from_file_location("_ed_check_lots", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    known = mod._catalog_raw_to_nibbles()
    named = {}
    witness = mod.name_witnesses()
    # name_witnesses() is flag -> (raw, nibble); fold it into the per-category vote shape the
    # deriver wants, using the categories our own lot rows carry for that raw.
    raw_cats = defaultdict(set)
    for cat, raws in rows_by_cat.items():
        for raw in raws:
            raw_cats[raw].add(cat)
    for raw, nib in witness.values():
        for cat in raw_cats.get(raw, ()):
            named.setdefault(cat, {})
            named[cat][nib] = named[cat].get(nib, 0) + 1
    return mod.derive_category_nibble(rows_by_cat, known, named)


def build_rows():
    lots = _load_lots()
    npcs = _load_npcs()
    bases = {b for _npc, b in npcs}
    names = _enemy_names()
    catalog = _catalog_by_full()
    placements = _single_placements()

    # PASS 1 -- every (category, raw) the reachable enemy lots reference, so the nibble map is voted
    # from the data rather than declared.
    rows_by_cat = defaultdict(set)
    reachable = {}
    for npc_id, base in npcs:
        group = lot_group(base, lots, bases)
        reachable[npc_id] = group
        for lot in group:
            row = lots[lot]
            for i in range(1, 9):
                iid = _int(row, "lotItemId%02d" % i)
                if iid <= 0 or iid == AP_PLACEHOLDER_GOODS:
                    continue
                rows_by_cat[_int(row, "lotItemCategory%02d" % i)].add(iid)
    nibble = _nibbles(dict(rows_by_cat))

    out = []
    for npc_id, base in npcs:
        chr_id = npc_id // 10000
        npc_name = names.get(chr_id, "")
        for lot in reachable[npc_id]:
            row = lots[lot]
            total = sum(_int(row, "lotItemBasePoint%02d" % i) for i in range(1, 9))
            flag = _int(row, "getItemFlagId")
            place = placements.get(flag) if flag > 0 else None
            for i in range(1, 9):
                iid = _int(row, "lotItemId%02d" % i)
                if iid <= 0 or iid == AP_PLACEHOLDER_GOODS:
                    continue
                cat = _int(row, "lotItemCategory%02d" % i)
                full = nibble[cat] | iid
                pct = (100.0 * _int(row, "lotItemBasePoint%02d" % i) / total) if total else 0.0
                out.append((
                    npc_id, npc_name, chr_id, lot, i, cat, iid, full,
                    catalog.get(full, ""), _int(row, "lotItemNum%02d" % i), "%.4f" % pct,
                    str(flag) if flag > 0 else "",
                    place[0] if place else "", place[1] if place else "",
                ))
    out.sort(key=lambda t: (t[0], t[3], t[4]))
    return out


def render(rows):
    body = [PREAMBLE + HEADER]
    for r in rows:
        body.append("\t".join(str(x) for x in r))
    return "\n".join(body) + "\n"


def stale_diff(committed, fresh, limit=20):
    """The first `limit` differing lines of two rendered tables, with line numbers and counts.

    WHY A REAL DIFF. `--check` used to print only "STALE ... re-run the tool", which on a machine
    that HAS the artifacts is fine (re-run it, read `git diff`) and on CI is a dead end: the runner
    throws the tree away and the only evidence of WHAT moved dies with it. The first failure
    (2026-09-08, run 34240106714) cost a full local repro to learn the answer was one column. This
    prints enough to name the column from the log alone: line counts on both sides, the differing
    lines paired up, then the set of COLUMNS that actually moved -- which separates "the params
    changed" from "a committed lookup table changed under us".
    """
    a = committed.split("\n")
    b = fresh.split("\n")
    out = ["  committed: %d lines / fresh: %d lines" % (len(a), len(b))]
    cols = set()
    shown = 0
    ndiff = 0
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else None
        y = b[i] if i < len(b) else None
        if x == y:
            continue
        ndiff += 1
        if x is not None and y is not None:
            for j, (p, q) in enumerate(zip(x.split("\t"), y.split("\t"))):
                if p != q:
                    cols.add(COLUMNS[j] if j < len(COLUMNS) else "col%d" % j)
        if shown < limit:
            shown += 1
            out.append("  line %d:" % (i + 1))
            out.append("    committed: %s" % ("<missing>" if x is None else x))
            out.append("    fresh    : %s" % ("<missing>" if y is None else y))
    out.append("  %d differing line(s)%s"
               % (ndiff, "" if shown >= ndiff else " (first %d shown)" % shown))
    if cols:
        out.append("  columns that moved: %s"
                   % ", ".join(sorted(cols, key=lambda c: COLUMNS.index(c) if c in COLUMNS else 99)))
    return "\n".join(out)


def _summary(rows):
    """(rows, npcs, lots, flagged rows, distinct flags, flags with a single placement)."""
    flagged = [r for r in rows if r[11]]
    return (len(rows), len({r[0] for r in rows}), len({r[3] for r in rows}), len(flagged),
            len({r[11] for r in flagged}), len({r[11] for r in flagged if r[12]}))


def flagged_flags(path=OUT):
    """Our ONE-TIME (flagged) enemy-drop flag ids, from the COMMITTED tsv. Used by matt_oracle."""
    if not os.path.isfile(path):
        return set()
    return {int(r["flag"]) for r in _read_rows(path) if r.get("flag")}


def report():
    """Flagged-drop summary from the COMMITTED tsv -- the sheet behind the product ruling."""
    if not os.path.isfile(OUT):
        raise SystemExit("FATAL: %s missing -- run the datamine first" % OUT)
    rows = _read_rows(OUT)
    flagged = [r for r in rows if r["flag"]]
    by_flag = defaultdict(list)
    for r in flagged:
        by_flag[int(r["flag"])].append(r)
    print("%d rows, %d NpcParam owners, %d lots" % (len(rows), len({r["npc_id"] for r in rows}),
                                                    len({r["lot"] for r in rows})))
    print("ONE-TIME (flagged) drops: %d rows over %d distinct flags; %d of those flags have a single"
          " known placement" % (len(flagged), len(by_flag),
                                len({int(r["flag"]) for r in flagged if r["map_id"]})))
    cats = Counter(r["category"] for r in flagged)
    print("flagged rows by lotItemCategory: %s"
          % ", ".join("%s=%d" % kv for kv in sorted(cats.items())))
    named = sum(1 for r in flagged if r["npc_name"])
    print("flagged rows whose enemy the GAME names: %d (the rest have no shipped name)" % named)
    print()
    for f in sorted(by_flag):
        rs = by_flag[f]
        print("flag %d  (%d row(s), lot(s) %s)%s"
              % (f, len(rs), ",".join(sorted({r["lot"] for r in rs}, key=int)),
                 "  @ %s %s" % (rs[0]["map_id"], rs[0]["part"]) if rs[0]["map_id"] else ""))
        for r in rs:
            print("    npc %-8s %-28s slot %s  x%-3s %6s%%  %s"
                  % (r["npc_id"], r["npc_name"] or ("c%s" % r["chr_id"]), r["slot"], r["num"],
                     r["chance_pct"], r["item_name"] or "(id %s)" % r["full_id"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="drift gate: exit 1 if enemy_drops.tsv is stale")
    ap.add_argument("--report", action="store_true",
                    help="flagged-drop summary from the COMMITTED tsv (no artifacts needed)")
    args = ap.parse_args(argv)

    if args.report:
        report()
        return 0

    rows = build_rows()
    text = render(rows)
    n, n_npc, n_lot, n_flagged, n_flags, n_placed = _summary(rows)
    if args.check:
        cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
        if cur != text:
            print("STALE: enemy_drops.tsv differs from a fresh datamine. Run: "
                  "python tools/datamine_enemy_drops.py", file=sys.stderr)
            print(stale_diff(cur, text), file=sys.stderr)
            return 1
        print("enemy_drops.tsv up to date (%d rows, %d npcs, %d lots, %d one-time rows over %d "
              "flags, %d flags placed)" % (n, n_npc, n_lot, n_flagged, n_flags, n_placed))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("wrote %s: %d rows, %d npcs, %d lots, %d one-time rows over %d flags, %d flags placed"
          % (OUT, n, n_npc, n_lot, n_flagged, n_flags, n_placed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
