#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_spare_goods.py -- enumerate every SPARE EquipParamGoods row usable as a shop-preview slot.

Emits greenfield/spare_goods.tsv (one goods id per line), the full pool that
features/shops._LOCK_PREVIEW_SPARE_GOODS should draw from. The client re-icons a preview good's shared
FMG + icon GLOBALLY, so a region-lock / foreign-item shop slot must point at a good that is safe to
clobber: one that EXISTS (so the game can grant/preview it), has NO real name (nothing to overwrite),
and is referenced by NOTHING (so re-iconing it touches no legitimate item). That is the identical
criterion as gen_data.AP_PLACEHOLDER_GOODS (8852) -- this tool just enumerates ALL of them instead of
picking one, so the 64-row hand-list in shops.py can widen toward the full ~332-row pool and give every
foreign shop item its OWN distinct flowered name (today they SHARE once the 64 spares are exhausted --
shops.py logs the overflow warning).

Criterion (matt-free), mirroring gen_data.REPEATABLE_GOODS + AP_PLACEHOLDER_GOODS:
  * EXISTS   -- id is a row in EquipParamGoods.csv,
  * NO REAL NAME -- id has NO GoodsName.fmg entry, or its entry (base + item_dlc0*) is a placeholder
                (%null%/<?null?>/x/'' all count, so the in-game '[ERROR]' rows qualify). Since
                2026-08-03 the client CREATES missing FMG entries (fmg_inject INSERT, read-back
                validated), so an entry-LESS row is usable too -- it is emitted as INSERTABLE
                (fmg_entry=0) and sorts AFTER every redirectable row. SPEC-spare-goods-pool-growth.md
                section 3's prerequisite settled 2026-08-20: the on-disk group records of all three
                goods categories (base + both DLC msgbnds) are strictly ascending and disjoint
                (0 wide claims / 0 overlaps), so the mid-array insert the Nightreign convention
                would have broken is safe against ER's vanilla FMGs.
  * UNREFERENCED -- id appears in NO ItemLotParam_map/_enemy goods slot (lotItemCategory==1), NO
                ShopLineupParam / ShopLineupParam_Recipe goods row (equipType==3), and NO talk ESD
                inventory check. (The talk scan matters for cut bell-bearing rows: granting one can
                expose a broken Twin Maiden menu entry even though no lot or shop grants it.)
  * >= MIN_ID and != 8852 -- skip the low/system band and the reserved placeholder. 8852 is documented
                as "the lowest one clear of the low/system band", so MIN_ID = 8852 reproduces that band.

Reads elden_ring_artifacts (vanilla_params CSVs + unpacked witchy GoodsName FMG xml). Pure Python:
    python tools/datamine_spare_goods.py
"""
import ast
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AR = os.path.join(ROOT, "elden_ring_artifacts")
OUT = os.path.join(ROOT, "greenfield", "spare_goods.tsv")

# 8852 is the reserved AP_PLACEHOLDER_GOODS and is documented as the lowest row clear of the low/system
# band; use it as the inclusive floor and exclude the placeholder itself.
MIN_ID = 8852
PLACEHOLDER = 8852

_TEXT_RE = re.compile(r'<text id="(\d+)"[^>]*>(.*?)</text>', re.S)
_NULLS = ("%null%", "&lt;?null?&gt;", "x", "")


def _fmg_texts(paths):
    """{goods id: raw name text} across the given FMG xml paths (later files win). Keeps EVERY entry,
    including placeholder/null text, so the caller can learn which strings are placeholders."""
    texts = {}
    for path in paths:
        if not os.path.isfile(path):
            continue
        for m in _TEXT_RE.finditer(open(path, encoding="utf-8", errors="replace").read()):
            texts[int(m.group(1))] = m.group(2).strip()
    return texts


def _params_dir():
    for cand in (os.path.join(AR, "vanilla_er", "vanilla_er"),
                 os.path.join(AR, "vanilla_params")):
        if os.path.isdir(cand):
            return cand
    return None


def _referenced(pdir):
    """{goods id: 'source'} for every goods id referenced by a lot slot (category 1) or a shop/recipe
    row (equipType 3). Keeps the FIRST witnessing source so the diagnostic can say WHY a row was cut."""
    ref = {}
    for fn in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
        p = os.path.join(pdir, fn)
        if not os.path.isfile(p):
            print(f"WARNING: {fn} missing under {pdir} -- lot references not counted.", file=sys.stderr)
            continue
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                lot = (list(r.values())[0] if r else "?")
                for i in range(1, 9):
                    try:
                        iid = int(r.get("lotItemId%02d" % i, 0) or 0)
                        cat = int(r.get("lotItemCategory%02d" % i, 0) or 0)
                    except ValueError:
                        continue
                    if iid > 0 and cat == 1:            # 1 == Goods
                        ref.setdefault(iid, f"{fn}:lot{lot}")
    for fn in ("ShopLineupParam.csv", "ShopLineupParam_Recipe.csv"):
        p = os.path.join(pdir, fn)
        if not os.path.isfile(p):
            print(f"WARNING: {fn} missing under {pdir} -- shop references not counted.", file=sys.stderr)
            continue
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                try:
                    if int(r.get("equipType", 3) or 3) != 3:   # goods only
                        continue
                    eid = int(r.get("equipId", 0) or 0)
                except ValueError:
                    continue
                if eid > 0:
                    ref.setdefault(eid, f"{fn}")
    return ref


def _call_name(node):
    return node.func.id if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) else None


def _int(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, int) else None


def _talk_goods_references(paths):
    """Goods ids inspected by talk ESD, including affine ``base + GetWorkValue`` runs.

    Twin Maiden Husks enumerate every possible bell-bearing row this way. Some cut rows have no
    name, lot, or shop reference, but granting one still creates a broken bell-bearing menu entry.
    Derive the run from the script instead of maintaining a positional blacklist that drifts when
    FromSoftware insert rows.
    """
    out = {}
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
        except (OSError, SyntaxError):
            continue
        source = os.path.basename(path)
        for loop in (n for n in ast.walk(tree) if isinstance(n, ast.While)):
            bounds = []
            for n in ast.walk(loop):
                if not (isinstance(n, ast.Compare) and len(n.ops) == 1
                        and isinstance(n.ops[0], ast.Gt) and len(n.comparators) == 1):
                    continue
                if _call_name(n.left) == "GetWorkValue":
                    bound = _int(n.comparators[0])
                    if bound is not None:
                        bounds.append(bound)
            if not bounds:
                continue
            bound = min(bounds)
            for n in ast.walk(loop):
                if _call_name(n) != "ComparePlayerInventoryNumber" or len(n.args) < 2:
                    continue
                item = n.args[1]
                if not (isinstance(item, ast.BinOp) and isinstance(item.op, ast.Add)):
                    continue
                base = _int(item.left)
                if base is None or _call_name(item.right) != "GetWorkValue":
                    continue
                for goods_id in range(base, base + bound + 1):
                    out.setdefault(goods_id, f"talk ESD {source}")
        for n in ast.walk(tree):
            if _call_name(n) == "ComparePlayerInventoryNumber" and len(n.args) >= 2:
                goods_id = _int(n.args[1])
                if goods_id and goods_id > 0:
                    out.setdefault(goods_id, f"talk ESD {source}")
    return out


# The 64 rows currently hand-listed in features/shops._LOCK_PREVIEW_SPARE_GOODS -- a KNOWN-GOOD set
# (verified in playtest: locks flowered onto them without clobbering any real good). We cross-check the
# derived pool against these: any known-good spare this tool would EXCLUDE is a scan bug, and the
# diagnostic prints exactly why (absent / named / referenced-by-what), so a mismatch is self-explaining
# rather than a silent under-count.
_KNOWN_GOOD = (
    9314, 9315, 9316, 9317, 9318, 9319, 9332, 9333, 9334, 9335, 9336, 9337, 9338, 9339,
    9349, 9350, 9351, 9352, 9353, 9354, 9355, 9356, 9357, 9358, 9359, 9366, 9367, 9368,
    9369, 9370, 9394, 9395, 9396, 9397, 9398, 9399, 9404, 9405, 9406, 9407, 9408, 9409,
    9410, 9424, 9425, 9426, 9427, 9428, 9429, 9430, 9442, 9443, 9444, 9445, 9446, 9447,
    9448, 9449, 9450, 50200, 50201, 50202, 50203, 51760,
)


def main():
    pdir = _params_dir()
    if not pdir:
        print(f"no vanilla params dir under {AR} -- nothing written.", file=sys.stderr)
        return 1
    epg = os.path.join(pdir, "EquipParamGoods.csv")
    if not os.path.isfile(epg):
        print(f"missing {epg} -- nothing written.", file=sys.stderr)
        return 1

    exists = set()
    with open(epg, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        id_col = rdr.fieldnames[0]                      # first column is the row ID
        for r in rdr:
            try:
                exists.add(int(r[id_col]))
            except (ValueError, KeyError, TypeError):
                continue

    texts = _fmg_texts([os.path.join(AR, "msg", "item-msgbnd-dcx", "GoodsName.fmg.xml")] +
                       glob.glob(os.path.join(AR, "msg", "item_dlc0*-msgbnd-dcx", "GoodsName*.fmg.xml")))
    if not texts:
        print("no GoodsName FMG entries found -- refusing to emit (every row would look nameless).",
              file=sys.stderr)
        return 1

    # ⭐ THE POOL NEEDS *TWO* PROPERTIES, KEPT DISTINCT (separated 2026-07-25, WIDENED 2026-08-20).
    #
    #   SAFETY:      nothing else wears this row's identity -> no real name, referenced by nothing.
    #   WRITABILITY: the client can give the row a name.
    #
    # WRITABILITY used to mean "the FMG must already have an ENTRY for the id", because
    # `fmg_inject::extend_swap_overrides` could only REDIRECT the string slot of an id already in a
    # vanilla FMG group. Since 2026-08-03 it can also INSERT a new group record mid-array (read-back
    # validated through the game's own SearchStringTable; er-logic fmg_groups::merged_order is the
    # ascending+disjoint gate). So writability now has TWO shapes, and the tsv's third column names
    # which one a row needs:
    #
    #   fmg_entry=1  REDIRECTABLE -- a placeholder entry exists (`[ERROR]`, `%null%`, ...); every
    #                client since the FMG override shipped can name these.
    #   fmg_entry=0  INSERTABLE  -- no entry at all; the client must CREATE one. Only clients with
    #                the 2026-08-03 insert path can name these, so they sort LAST and a seed that
    #                spends one declares requiresClientFeatures (features/shops.py, issue #937).
    #
    # The mid-array insert was blocked on SPEC-spare-goods-pool-growth.md section 3: Nightreign's
    # vanilla FMGs use boundary-claim groups (last_id == next.first_id), which the disjointness gate
    # rejects. Settled 2026-08-20 by parsing the ON-DISK group records ({stringIndexBase, firstId,
    # lastId} at 0x28, the same layout fmg_inject::parse reads at runtime): GoodsName/GoodsInfo/
    # GoodsCaption, base + both DLC msgbnds, are strictly ascending with ZERO wide claims and ZERO
    # overlaps -- ER does not share NR's convention, so the insert path's gate holds. (The runtime
    # startup probe the SPEC asks for is still worth shipping as belt-and-suspenders; the static
    # number is what unblocked this.)
    #
    # An EMPTY placeholder entry remains the ideal redirectable shape: that is the `[ERROR]` render,
    # and 8852 -- the lot placeholder that dress_placeholder successfully renames to "Archipelago
    # Item" -- is exactly that shape.
    #
    # LEARN the placeholder strings instead of guessing them -- two independent signals, unioned:
    #  (1) KNOWN-GOOD: the 64 hand-listed spares carry NO real name (shops.py: "[ERROR] placeholder
    #      name, no real name to clobber") yet the FMG has an ENTRY for them, so whatever text they
    #      hold IS a placeholder token.
    #  (2) FREQUENCY: a real good's name is ~unique, but a dummy string ("[ERROR]" and any siblings) is
    #      shared across hundreds of unused rows. So any text appearing on >= FREQ_MIN rows is a
    #      placeholder -- this catches dummy VARIANTS the known-good set never happened to use, which is
    #      what capped the first pass at 82 (known-good only taught it one token).
    # A row whose text is any learned placeholder (or a static null) counts as UNNAMED. Self-calibrating:
    # no hardcoded "[ERROR]" that drifts with a witchy/locale change.
    FREQ_MIN = 8                                          # no real ER goods name repeats this often
    from collections import Counter
    freq = Counter(texts.values())
    placeholders = set(_NULLS)
    placeholders |= {t for t, n in freq.items() if n >= FREQ_MIN}
    placeholders |= {texts[g] for g in _KNOWN_GOOD if g in texts}     # belt-and-suspenders
    named = {g for g, t in texts.items() if t not in placeholders}
    _learned = sorted(((freq[p], p) for p in placeholders if p not in _NULLS), reverse=True)
    print(f"learned {len(_learned)} placeholder token(s) [text xN]: "
          + ", ".join(f"{p!r} x{n}" for n, p in _learned[:8]), file=sys.stderr)

    referenced = _referenced(pdir)
    talk_refs = _talk_goods_references(glob.glob(os.path.join(AR, "talk", "**", "*.py"),
                                                 recursive=True))
    for goods_id, source in talk_refs.items():
        referenced.setdefault(goods_id, source)

    # 🛑 THE BELL-BEARING RUNS, PINNED (2026-08-20). The Twin Maiden Husks enumerate bell bearings
    # by affine inventory runs -- 8910 + GetWorkValue (bound 55), and 2008900 + GetWorkValue
    # (bound 10) for the DLC bearings -- and a GRANTED cut row in one of those runs exposes a
    # broken bell-bearing menu entry. A shop preview good IS granted on purchase, so a spare in
    # the run is the exact hazard the talk scan exists for. But the script that proves it lives
    # with the Roundtable talk ESD, which is NOT guaranteed to be in the artifact set (this box's
    # talk artifacts are the m60-only subset), and an incomplete scan fails SILENTLY -- it did
    # here: 8914/8949/8950 slipped into the pool until test_gf_spare_goods_order's fixture (which
    # pins the same two runs) redded on the emitted tsv. The derived runs above stay the primary
    # mechanism; these pins are the floor under it, and the test keeps the two honest about each
    # other -- if a script-derived run ever disagrees with the pins, that test fails.
    for _bell in list(range(8910, 8910 + 56)) + list(range(2008900, 2008900 + 11)):
        referenced.setdefault(_bell, "PINNED Twin Maiden bell-bearing run (test fixture)")

    # SENTINEL/TEMPLATE guard: params carry a default row (id 999999999 and similarly the huge
    # 2^31-ish rows) that is nameless + unreferenced and would masquerade as a spare. A real
    # EquipParamGoods good id is <= 6 digits; cap at MAX_ID so no template row leaks into the pool.
    MAX_ID = 999999

    def _cut_reason(g):
        if g < MIN_ID:
            return "floored (<%d)" % MIN_ID
        if g == PLACEHOLDER:
            return "reserved placeholder"
        if g > MAX_ID:
            return "sentinel/template (>%d)" % MAX_ID
        if g not in exists:
            return "ABSENT from EquipParamGoods"
        if g in named:
            return "HAS GoodsName"
        # NO `g not in texts` cut since 2026-08-20 (issue #937): an entry-less row is INSERTABLE --
        # the client creates its FMG entry. It is emitted in tier 3, not excluded.
        if g in referenced:
            return "REFERENCED by %s" % referenced[g]
        return None                                     # survives -> a spare

    spares = sorted(g for g in exists if _cut_reason(g) is None)

    # ⭐ THREE TIERS, ORDER IS THE FEATURE (completeness tiering 2026-07-29; insertable tier
    # 2026-08-20, issue #937). shops.py indexes this pool POSITIONALLY, so ORDER decides which rows
    # a seed actually spends:
    #
    #   tier 1  REDIRECTABLE + complete (GoodsName + GoodsInfo + GoodsCaption entries) -- a full
    #           preview any client can write.
    #   tier 2  REDIRECTABLE, name-only -- nameable by any client; the client creates the missing
    #           GoodsInfo/GoodsCaption entries since 2026-08-03.
    #   tier 3  INSERTABLE (no GoodsName entry at all) -- needs the client's mid-array INSERT.
    #
    # Tiers 1+2 are exactly the pre-widening pool in the pre-widening order, so a seed that never
    # reaches tier 3 draws byte-identical previews to before (SPEC section 6 acceptance), and only
    # a seed that SPENDS a tier-3 row declares requiresClientFeatures. Requiring completeness was
    # never a filter for the same reason as before: it would cut the pool below the ~54 region
    # locks that each need a distinct row.
    _info = _fmg_texts(glob.glob(os.path.join(AR, "msg", "**", "GoodsInfo.fmg.xml"), recursive=True))
    _cap = _fmg_texts(glob.glob(os.path.join(AR, "msg", "**", "GoodsCaption.fmg.xml"), recursive=True))
    if not _info or not _cap:
        print("no GoodsInfo/GoodsCaption FMG entries found -- refusing to emit an unordered pool "
              "(an empty result is a FAILURE, not a clean run).", file=sys.stderr)
        return 1
    _redirect = {g for g in spares if g in texts}
    _full = {g for g in spares if g in texts and g in _info and g in _cap}
    _tier2 = sorted(_redirect - _full)
    _tier3 = sorted(set(spares) - _redirect)
    spares = sorted(_full) + _tier2 + _tier3
    print(f"pool tiers: {len(_full)} redirectable+complete (emitted FIRST), {len(_tier2)} "
          f"redirectable name-only, {len(_tier3)} INSERTABLE (emitted LAST -- the client creates "
          f"their FMG entries, and a seed that spends one declares requiresClientFeatures).",
          file=sys.stderr)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_spare_goods.py -- EquipParamGoods rows that EXIST,\n")
        f.write("# have NO real name (a placeholder GoodsName entry, or -- tier 3 -- no entry at all:\n")
        f.write("# the client CREATES it via the 2026-08-03 fmg_inject INSERT path), and are referenced\n")
        f.write("# by NO lot/shop/recipe/talk ESD. The pool for\n")
        f.write("# features/shops._LOCK_PREVIEW_SPARE_GOODS (region-lock + foreign-item previews).\n")
        f.write(f"# floor id={MIN_ID}, cap id={MAX_ID}, excludes reserved placeholder {PLACEHOLDER}.\n")
        f.write(f"# ORDERED in three tiers: the first {len(_full)} rows are redirectable and carry\n")
        f.write(f"# GoodsName+Info+Caption (a full preview); the next {len(_tier2)} are redirectable\n")
        f.write(f"# name-only; the last {len(_tier3)} are INSERTABLE (fmg_entry=0 -- no vanilla FMG\n")
        f.write("# entry; the client must create it, so a seed spending one of these declares\n")
        f.write("# requiresClientFeatures). shops.py indexes this pool positionally: order IS priority.\n")
        f.write("goods_id\tfmg_full\tfmg_entry\n")
        for g in spares:
            f.write(f"{g}\t{1 if g in _full else 0}\t{1 if g in _redirect else 0}\n")
    print(f"wrote {OUT}: {len(spares)} spare goods rows ({len(_redirect)} redirectable + "
          f"{len(_tier3)} insertable; exists={len(exists)} named={len(named)} "
          f"referenced={len(referenced)})")

    # EXCLUSION BREAKDOWN over the in-range existing rows -- shows whether NAME or REFERENCE is the
    # limiting filter if the pool is still short of the ~332 target.
    from collections import Counter as _C
    _reasons = _C(_cut_reason(g) or "SPARE"
                  for g in exists if MIN_ID <= g <= MAX_ID and g != PLACEHOLDER)
    print("in-range breakdown: " + ", ".join(f"{k}={v}" for k, v in _reasons.most_common()),
          file=sys.stderr)

    # SELF-DIAGNOSTIC: every known-good hand-listed spare this pool would drop is a scan bug -- say why.
    missing = [(g, _cut_reason(g)) for g in _KNOWN_GOOD if g not in set(spares)]
    if missing:
        print(f"\n!! {len(missing)}/{len(_KNOWN_GOOD)} KNOWN-GOOD spares (shops._LOCK_PREVIEW_SPARE_GOODS) "
              f"are NOT in the derived pool -- the criterion is mis-classifying them:", file=sys.stderr)
        for g, why in missing:
            print(f"     {g}: {why}", file=sys.stderr)
        print("   Fix the scan (or the artifact set) until this list is empty before widening shops.py.",
              file=sys.stderr)
    else:
        print(f"OK: all {len(_KNOWN_GOOD)} known-good spares are in the derived pool.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
