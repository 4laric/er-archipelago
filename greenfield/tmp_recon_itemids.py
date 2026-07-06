import csv, os
from collections import defaultdict, Counter
csv.field_size_limit(10**7)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
AR = os.path.join(REPO, "elden_ring_artifacts")
SLP_DIR = os.path.join(AR, "vanilla_er", "vanilla_er")
PARAMS = [("EquipParamWeapon.csv", 0x00000000, "weapon"),
          ("EquipParamProtector.csv", 0x10000000, "armor"),
          ("EquipParamAccessory.csv", 0x20000000, "accessory"),
          ("EquipParamGoods.csv", 0x40000000, "goods"),
          ("EquipParamGem.csv", 0x80000000, "gem")]
name_entries = defaultdict(list)
per_cat = {}
for fn, nib, cat in PARAMS:
    p = os.path.join(SLP_DIR, fn)
    n = 0
    for r in csv.DictReader(open(p, encoding="utf-8", errors="replace")):
        nm = (r.get("Name") or "").strip()
        if not nm:
            continue
        try:
            rid = int(r["ID"])
        except (KeyError, ValueError):
            continue
        name_entries[nm].append((rid, nib, cat)); n += 1
    per_cat[cat] = n
print("named rows per cat:", per_cat)
print("distinct names total:", len(name_entries))
cross = [nm for nm, es in name_entries.items() if len({c for _, _, c in es}) > 1]
dup_within = [nm for nm, es in name_entries.items() if len(es) > len({c for _, _, c in es})]
print("names ambiguous ACROSS categories:", len(cross))
print("  sample cross-cat:", cross[:12])
print("names with intra-category dup ids:", len(dup_within))
prio = {cat: i for i, (_, _, cat) in enumerate(PARAMS)}
INDEX = {}
for nm, es in name_entries.items():
    best = sorted(es, key=lambda e: (prio[e[2]], e[0]))[0]
    INDEX[nm] = (best[0] | best[1], best[0], best[1], best[2])
SKIP = {"global", "global_filler", "shop_reference"}
rows = [r for r in csv.DictReader(open(os.path.join(HERE, "region_map.csv"))) if r["method"] not in SKIP]
BASE = 7770000
resolved = 0
unresolved = []
res_by_cat = Counter()
seen = Counter()
for i, r in enumerate(rows):
    nm = (r.get("item_name") or "").strip()
    seen[nm] += 1
    if nm in INDEX:
        resolved += 1; res_by_cat[INDEX[nm][3]] += 1
    else:
        unresolved.append(nm)
print("---- COVERAGE ----")
print("total location rows:", len(rows))
print("resolved to FullID:", resolved)
print("unresolved:", len(unresolved))
print("resolved by category:", dict(res_by_cat))
uc = Counter(unresolved)
print("distinct unresolved names:", len(uc))
print("distinct item_names in rows:", len(seen))
print("rows with empty item_name:", seen.get("", 0))
print("top unresolved (count, name):")
for nm, c in uc.most_common(15):
    print("   %5d  %r" % (c, nm))
