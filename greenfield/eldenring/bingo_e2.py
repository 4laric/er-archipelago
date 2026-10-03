"""E2 encounter rosters and acquisition objectives; identities from generated tables.

The catalogue is the expanded E2 audit, not newly invented square text. Native
healthbar members without a generated terminal owner are never counted separately.
"""
import json
from pathlib import Path
from itertools import combinations

CATALOGUE = json.loads(Path(__file__).with_name("bingo_e2_catalogue.json").read_text(encoding="utf-8"))

# Fight-level terminals, verified in boss_sweeps/EMEVD. Partner healthbars are not units.
DUOS = {12020800, 30100800, 30120800, 30140800, 31060800, 31070800,
        31100800, 31110800, 31150800, 31180800, 31200800, 31220800,
        32050800, 1041510800, 1048400800, 1049390800, 1051360800, 1248550800}
NPC_BASE_NAMES = {"Patches", "Adan, Thief of Fire", "Battlemage Hugues",
                  "Roundtable Knight Vyke", "Necromancer Garris", "Esgar, Priest of Blood",
                  "Sir Gideon Ofnir, the All-Knowing"}
NPC_DLC_NAMES = {"Knight of the Solitary Gaol", "Dancer of Ranah", "Red Bear", "Rakshasa", "Dryleaf Dane"}
DRAGON_HEART_NAMES = {"Flying Dragon Agheel", "Glintstone Dragon Smarag", "Glintstone Dragon Adula",
 "Decaying Ekzykes", "Flying Dragon Greyll", "Borealis the Freezing Fog", "Magma Wyrm",
 "Magma Wyrm Makar", "Great Wyrm Theodorix"}
LEGENDARY_TALISMANS = {"Radagon's Soreseal", "Marika's Soreseal", "Dragoncrest Greatshield Talisman",
 "Moon of Nokstella", "Old Lord's Talisman", "Radagon Icon", "Godfrey Icon", "Erdtree's Favor +2"}


def _roster(source, rows):
    n = lambda names: [r for r in rows if r["name"] in names]
    contains = lambda word: [r for r in rows if word.casefold() in r["name"].casefold()]
    by = {
      "011": lambda: contains("Red Wolf"), "015": lambda: contains("Gargoyle") + n({"Black Blade Kindred"}),
      "030": lambda: contains("God"), "032": lambda: n({"Magma Wyrm", "Magma Wyrm Makar", "Great Wyrm Theodorix"}),
      "033": lambda: contains("Fallingstar Beast"), "035": lambda: contains("Omenkiller") + [r for r in rows if r["flag"] == 31180800],
      "037": lambda: n({"Cemetery Shade"}), "039": lambda: contains("Misbegotten"),
      "040": lambda: contains("Watchdog"), "041": lambda: contains("Duelist"),
      "042": lambda: n({"Black Knife Assassin", "Alecto, Black Knife Ringleader"}),
      "044": lambda: n(DRAGON_HEART_NAMES), "045": lambda: n({"Erdtree Avatar", "Putrid Avatar"}),
      "046": lambda: contains("Night's Cavalry"), "047": lambda: n({"Tibia Mariner"}),
      "048": lambda: n({"Bell Bearing Hunter"}), "049": lambda: [r for r in rows if r["flag"] in DUOS],
      "050": lambda: contains("Night's Cavalry") + n({"Tree Sentinel", "Draconic Tree Sentinel"}),
      "051": lambda: contains("Tree"),
      "059": lambda: [r for r in rows if r["region"] in {"Limgrave", "Weeping"}],
      "060": lambda: [r for r in rows if r["region"] == "Liurnia"],
      "061": lambda: [r for r in rows if r["region"] == "Caelid"],
      "062": lambda: [r for r in rows if r["region"] in {"Altus", "Mt. Gelmir"}],
      "063": lambda: [r for r in rows if r["map"].startswith("m30_") and r["flag"] != 30050850],
      "064": lambda: [r for r in rows if r["map"].startswith("m31_") and r["flag"] not in {31000800, 31190850}],
      "065": lambda: [r for r in rows if r["map"].startswith("m32_") or r["name"] == "Magma Wyrm Makar"],
      "066": lambda: [r for r in rows if r["map"] in {"m30_08", "m30_09", "m30_10"}],
      "067": lambda: [r for r in rows if r["flag"] in {1033420800,1033450800,1036500800,1038410800,
                       1042370800,1042330800,1044350800,1039500800,1049390850,1053560800}],
      "113": lambda: contains("Astel"), "114": lambda: n(NPC_BASE_NAMES),
    }
    dlc = {
      "008": lambda: [r for r in rows if r["map"].startswith("m40_")],
      "015": lambda: n({"Ghostflame Dragon", "Jagged Peak Drake", "Ancient Dragon Senessax", "Bayle the Dread"}),
      "020": lambda: [r for r in rows if r["map"].startswith("m41_")],
      "021": lambda: n({"Divine Beast Dancing Lion"}),
      "026": lambda: n({"Red Bear", "Ralva the Great Red Bear", "Rugalea the Great Red Bear"}),
      "028": lambda: n(NPC_DLC_NAMES), "058": lambda: n(NPC_DLC_NAMES - {"Dryleaf Dane"}),
      "070": lambda: n({"Death Rite Bird", "Tree Sentinel", "Fallingstar Beast"}),
      "071": lambda: contains("Knight"),
    }
    return (dlc if "-DLC-" in source else by).get(source[-3:], lambda: [])()


def _collection(row, tables):
    cat, goods, dlc = tables.item_catalog, tables.modules["item_ids"].GOODS_TYPE, set(tables.dlc_item_names)
    names = sorted(cat)
    scoped = [n for n in names if (n in dlc) == (row["scope"] == "dlc")]
    source, target = row["source"], row["target"]
    explicit = {
      "BASE-069": ["Somberstone Miner's Bell Bearing [1]", "Somberstone Miner's Bell Bearing [2]"],
      "BASE-070": ["Smithing-Stone Miner's Bell Bearing [1]", "Smithing-Stone Miner's Bell Bearing [2]"],
      "BASE-071": ["Glovewort Picker's Bell Bearing [1]", "Ghost-Glovewort Picker's Bell Bearing [1]"],
      "BASE-072": ["Glovewort Picker's Bell Bearing [2]", "Ghost-Glovewort Picker's Bell Bearing [2]"],
      "BASE-073": ["Margit's Shackle", "Mohg's Shackle"], "BASE-080": ["Cracked Pot"],
      "BASE-081": ["Ritual Pot"], "BASE-083": ["Radagon's Scarseal", "Marika's Scarseal"],
      "BASE-086": ["Fingerslayer Blade"], "BASE-108": ["Memory Stone"],
      "BASE-110": ["Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)"],
      "BASE-116": ["Moon of Nokstella"], "BASE-120": ["Imbued Sword Key"],
      "DLC-022": ["Gaius's Greaves"], "DLC-025": ["Swordhand of Night Jolán"],
      "DLC-035": ["Dragon Heart"], "DLC-036": [row["label"].removeprefix("Collect the ").removesuffix(" Talisman") + " Talisman"],
      "DLC-039": ["Scorpion Stew"], "DLC-040": ["Golden Braid"], "DLC-046": ["Leda's Rune"],
      "DLC-053": ["Hefty Cracked Pot"], "DLC-057": ["Igon's Furled Finger"],
      "DLC-074": ["Gravebird Helm", "Gravebird Armor", "Gravebird Bracelets", "Gravebird Anklets"],
      "DLC-075": ["Death Mask Helm", "Winged Serpent Helm", "Salza's Hood"],
      "DLC-077": ["Blessing of Marika"],
    }
    key = source.removeprefix("S6-")
    qty = key in {"BASE-080", "BASE-081", "BASE-108", "BASE-120", "DLC-035", "DLC-053", "DLC-077"}
    if key in explicit:
        chosen = explicit[key]
        if not all(n in cat for n in chosen): return None
        if not qty: target = len(chosen)
    elif key == "BASE-082":
        chosen = sorted(LEGENDARY_TALISMANS & set(cat)) if "Legendary" in row["label"] else [n for n in scoped if cat[n] >> 28 == 2]
    elif key in {"BASE-094", "BASE-095"}: chosen = [n for n in scoped if goods.get(n) == (5 if key == "BASE-094" else 16)]
    elif key in {"BASE-105", "BASE-122"}: chosen = [n for n in scoped if cat[n] >> 28 == 0 and cat[n] // 1000000 == (33 if key == "BASE-105" else 34)]
    # These dual-use flags are explicitly blocked by the delivery contract. A
    # guaranteed AP copy cannot establish a safe native acquisition yet.
    elif key == "BASE-121": return None
    elif key == "DLC-001": chosen = [n for n in scoped if "Bell Bearing" in n and any(w in n for w in ["Mushroom-Seller", "String-Seller", "Greasemonger", "Moldmonger", "Herbalist"]) ]
    elif key == "DLC-019": chosen = [n for n in scoped if "Forager Brood Cookbook" in n]
    elif key == "DLC-033": chosen = [n for n in scoped if cat[n] >> 28 == 8]
    elif key == "DLC-034": chosen = [n for n in scoped if goods.get(n) == 7]
    elif key == "DLC-080": chosen = [n for n in names if n in {"Ancient Dragon Smithing Stone", "Somber Ancient Dragon Smithing Stone", "Great Grave Glovewort", "Great Ghost Glovewort"}]
    elif key == "DLC-050":
        bundles = tables.modules["item_ids"].ARMOR_BUNDLES
        units = [{"items": [[fid] for fid in ids], "count": 1, "names": [next(n for n,v in cat.items() if v == fid) for fid in ids]} for ids in bundles.values() if len(ids) == 4 and all(any(n in dlc and v == fid for n,v in cat.items()) for fid in ids)]
        return {"target": target, "members": units} if len(units) >= target else None
    else: return None
    if len(chosen) < (1 if qty else target): return None
    return {"target": 1 if qty else target, "members": [{"items": [[cat[n]]], "count": target if qty else 1, "monotone": n in {"Cracked Pot", "Ritual Pot", "Memory Stone", "Hefty Cracked Pot"}, "names": [n]} for n in chosen]}


def candidates(tables, eligible, region_limit):
    from .region_spine import DLC_REGIONS, parent_chain
    hb = tables.modules["boss_healthbars"].BOSS_HEALTHBARS
    spine = tables.modules["boss_sweeps"]
    # Only flags with an owning generated terminal sweep can count; partner bars lack one.
    rows = [{"flag": f, "name": r[3], "map": r[0], "region": spine.SWEEP_ARENA_REGION.get(f, spine.SWEEP_REGION.get(f)), "weight": 2 if f == 12020800 else 1}
            for f,r in hb.items() if spine.SWEEP_ARENA_REGION.get(f, spine.SWEEP_REGION.get(f)) in eligible and f not in {31000800}]
    out, unavailable = [], []
    for row in CATALOGUE:
        regions = {"Gravesite" if row["scope"] == "dlc" else "Limgrave"}
        if row["kind"] == "collection":
            group = _collection(row, tables)
            if group is None or not regions <= set(eligible):
                unavailable.append(row["variant"]); continue
            # Curate a sufficient guaranteed supply; alternatives remain qualifying acquisitions.
            supply = []
            for member in group["members"][:group["target"]]:
                supply += [[n, member["count"]] for n in member["names"]]
            for member in group["members"]: member.pop("names")
            out.append(dict(flag=0, region=next(iter(regions)), regions=sorted(regions),
                label=row["label"] + (" (AP deliveries)" if row["source"] in {"S6-BASE-120", "S6-DLC-035", "S6-DLC-077"} else " (local acquisition or AP delivery)"), family=row["source"], source=row["source"],
                variant=row["variant"], collection=[group], requirements=supply, supply_goal=True))
            continue
        scoped = [r for r in rows if (r["region"] in DLC_REGIONS) == (row["scope"] == "dlc")]
        groups = []
        if row["source"] == "S6-BASE-036":
            groups = [(2, [r for r in scoped if r["name"] == "Deathbird"]), (1, [r for r in scoped if r["name"] == "Death Rite Bird"])]
        elif row["source"] == "S6-DLC-082":
            groups = [(1, [r for r in scoped if r["name"] in names]) for names in [
              {"Red Bear", "Ralva the Great Red Bear", "Rugalea the Great Red Bear"}, {"Divine Beast Dancing Lion"}, {"Golden Hippopotamus"}]]
        else: groups = [(row["target"], _roster(row["source"], scoped))]
        if any(sum(r["weight"] if row["source"] == "S6-BASE-015" else 1 for r in members) < target for target,members in groups):
            unavailable.append(row["variant"]); continue
        # Choose a sufficient contributor footprint within the region budget. Each viable
        # footprint is a candidate so a wider board can pick a compatible route after the draw.
        owners = sorted({r["region"] for _,members in groups for r in members})
        emitted = 0
        for size in range(1, min(len(owners), region_limit)+1):
            for footprint in combinations(owners, size):
                closure = set(footprint) | {p for r in footprint for p in parent_chain(r)}
                if len(closure) > region_limit: continue
                counter=[]
                for target,members in groups:
                    units=[dict(flag=r["flag"], region=r["region"], label=r["name"], weight=r["weight"] if row["source"] == "S6-BASE-015" else 1) for r in members if r["region"] in footprint]
                    if sum(u["weight"] for u in units) < target: break
                    counter.append(dict(target=target, members=units))
                else:
                    out.append(dict(flag=0, region=footprint[0], regions=list(footprint), label=row["label"],
                        family=row["source"], source=row["source"], variant=row["variant"], counter=counter, requirements=[]))
                    emitted += 1
            if emitted: break
        if not emitted: unavailable.append(row["variant"])
    return out, unavailable
