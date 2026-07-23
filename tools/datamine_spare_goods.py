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
  * NO NAME  -- id has no GoodsName.fmg entry (base + item_dlc0*; %null%/<?null?>/x/'' all count as no
                name, so the in-game '[ERROR]' rows qualify),
  * UNREFERENCED -- id appears in NO ItemLotParam_map/_enemy goods slot (lotItemCategory==1) and NO
                ShopLineupParam / ShopLineupParam_Recipe goods row (equipType==3). (A crafting recipe's
                output is a named good, so the name test already excludes craftables; the shop-recipe
                table is scanned anyway to match the '/ recipe' half of the criterion verbatim.)
  * >= MIN_ID and != 8852 -- skip the low/system band and the reserved placeholder. 8852 is documented
                as "the lowest one clear of the low/system band", so MIN_ID = 8852 reproduces that band.

Reads elden_ring_artifacts (vanilla_params CSVs + unpacked witchy GoodsName FMG xml). Pure Python:
    python tools/datamine_spare_goods.py
"""
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

    # LEARN the placeholder strings instead of guessing them. The 64 known-good spares carry NO real
    # name (shops.py: "[ERROR] placeholder name, no real name to clobber"), yet the FMG has an ENTRY for
    # them -- so whatever text those rows hold IS a placeholder token. Any row whose text is one of those
    # tokens (or a static null) counts as UNNAMED. Self-calibrating: no hardcoded "[ERROR]" that could
    # drift with a witchy/locale change.
    placeholders = set(_NULLS)
    for g in _KNOWN_GOOD:
        if g in texts:
            placeholders.add(texts[g])
    named = {g for g, t in texts.items() if t not in placeholders}
    print(f"learned {len(placeholders) - len(_NULLS)} placeholder token(s) from known-good rows: "
          f"{sorted(p for p in placeholders if p not in _NULLS)[:8]}", file=sys.stderr)

    referenced = _referenced(pdir)

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
        if g in referenced:
            return "REFERENCED by %s" % referenced[g]
        return None                                     # survives -> a spare

    spares = sorted(g for g in exists if _cut_reason(g) is None)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_spare_goods.py -- EquipParamGoods rows that EXIST,\n")
        f.write("# have NO GoodsName, and are referenced by NO lot/shop/recipe. The safe-to-clobber pool\n")
        f.write("# for features/shops._LOCK_PREVIEW_SPARE_GOODS (region-lock + foreign-item previews).\n")
        f.write(f"# floor id={MIN_ID}, cap id={MAX_ID}, excludes reserved placeholder {PLACEHOLDER}.\n")
        f.write("goods_id\n")
        for g in spares:
            f.write(f"{g}\n")
    print(f"wrote {OUT}: {len(spares)} spare goods rows "
          f"(exists={len(exists)} named={len(named)} referenced={len(referenced)})")

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
