#!/usr/bin/env python3
r"""item_naming.py -- ONE resolver for "what is the item in this ItemLotParam slot called?"

WHY THIS MODULE EXISTS. The answer takes three rules, all settled by READING THE PARAMS rather than
by inference (tools/sweep_unnamed_items.py's 2026-07-27 note carries the evidence):

  1. CATEGORY -> EquipParam TABLE is MEMBERSHIP, not name-matching. The id spaces overlap, so "which
     FMG has a name for this id" gets category 3 wrong (it votes Weapon 10/16 on collisions).
     "Which table CONTAINS the id" gives the clean ordering
     1 Goods | 2 Weapon | 3 Protector | 4 Accessory | 5 Gem | 6 CustomWeapon.
  2. WEAPON IDS CARRY THE UPGRADE LEVEL. 2550001..2550010 are ONE weapon (2550000) at +1..+10; only
     2550000 exists as an EquipParamWeapon row, and ReinforceParamWeapon confirms reinforceTypeId
     2200 has levels 0..10 -- exactly those ten lot ids. No ladder exceeds +25, so
     `id // 100 * 100` is a SAFE strip, not a lucky one.
  3. CATEGORY 6 IS EquipParamCustomWeapon -- a weapon + Ash of War PAIRING, which is why those ids
     resolve in no FMG at all. They name through baseWepId + gemId.

🛑 IT LIVED IN ONE PLACE AND WAS NEEDED IN TWO. `sweep_unnamed_items.py` used these rules to write a
WORKLIST -- it resolved "Dryleaf Arts with Ash of War: Palm Blast" for flag 400730 on 2026-07-27 --
while `gen_data.py`, which names the checks a PLAYER reads, had no access to them and emitted
`Scadu Altus :: check - around Liurnia Lake Shore [f400730]`: no item name, and a descriptor naming
the wrong lake. A repo that has already resolved a name and still ships `check` is not missing data,
it is missing a shared function. This is that function.

Both callers import from here, so a fourth rule fixes the worklist AND the world in one commit --
the property the split did not have.
"""
import csv
import os
import re
from collections import Counter, defaultdict

FMG_FAMILIES = ("Weapon", "Protector", "Accessory", "Goods", "Gem")
# (tag, msg dir, filename suffix) -- base FIRST so a base name wins over a DLC re-use of the id.
FMG_DIRS = (("base", "item-msgbnd-dcx", ""),
            ("dlc01", "item_dlc01-msgbnd-dcx", "_dlc01"),
            ("dlc02", "item_dlc02-msgbnd-dcx", "_dlc02"))
PARAM_OF_FAMILY = {"Weapon": "EquipParamWeapon", "Protector": "EquipParamProtector",
                   "Accessory": "EquipParamAccessory", "Goods": "EquipParamGoods",
                   "Gem": "EquipParamGem"}


def load_fmgs(inputs):
    """family -> {id: name}, merged base/dlc01/dlc02. `setdefault` so base wins on a re-used id."""
    out = {}
    for fam in FMG_FAMILIES:
        ids = {}
        for _tag, d, suf in FMG_DIRS:
            p = os.path.join(inputs, "msg", d, "%sName%s.fmg.xml" % (fam, suf))
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                for m in re.finditer(r'<text id="(\d+)">(.*?)</text>', fh.read(), re.S):
                    val = m.group(2)
                    if val and val not in ("%null%", "[ERROR]"):
                        ids.setdefault(int(m.group(1)), val)
        out[fam] = ids
    return out


def load_custom_weapons(inputs):
    """id -> (baseWepId, gemId) from EquipParamCustomWeapon (rule 3). {} when the param is absent."""
    p = os.path.join(inputs, "vanilla_er", "vanilla_er", "EquipParamCustomWeapon.csv")
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p, encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            if r.get("ID", "").strip().isdigit():
                try:
                    out[int(r["ID"])] = (int(r.get("baseWepId") or 0), int(r.get("gemId") or 0))
                except ValueError:
                    continue
    return out


def load_param_ids(inputs, name):
    """The id set of one EquipParam table, or None when the CSV is absent.

    None vs set() is load-bearing: "corpus not present" and "searched and empty" are different
    facts, and collapsing them is how a missing param becomes a silent wrong answer.
    """
    p = os.path.join(inputs, "vanilla_er", "vanilla_er", name + ".csv")
    if not os.path.exists(p):
        return None
    ids = set()
    with open(p, encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh):
            if row and row[0].strip().lstrip("-").isdigit():
                ids.add(int(row[0]))
    return ids


def load_family_ids(inputs):
    """family -> id set, for the membership vote. An absent param contributes an empty set."""
    return {fam: (load_param_ids(inputs, param) or set())
            for fam, param in PARAM_OF_FAMILY.items()}


def learn_category_families(pairs, family_ids, custom=None):
    """{str(lotItemCategory): family} by PARAM MEMBERSHIP (rule 1). `pairs` = iter of (cat, item_id).

    🛑 Vote over EVERY row with an item id, not just already-named ones: membership needs no name,
    and restricting to named rows lets the Goods-heavy majority swamp the small categories (it read
    category 5 as Goods 5/13 instead of Gem 88/112). A category with no evidence is ABSENT from the
    result rather than guessed -- callers must treat a missing category as unknown, never as Goods.

    🛑 `custom` (EquipParamCustomWeapon) VOTES TOO, or category 6 is mislabelled. Its ids collide
    with the Protector space, so a vote over the five FMG-backed tables alone reports
    `6 -> Protector`. That does not corrupt a NAME -- resolve_name checks the custom table before it
    looks at the family -- but it makes the printed map a false statement about the game, and a
    reader who trusts it will draw the wrong conclusion the next time category 6 comes up.
    """
    votes = defaultdict(Counter)
    tables = dict(family_ids)
    if custom:
        tables["CustomWeapon"] = set(custom)
    for cat, iid in pairs:
        if iid is None:
            continue
        for fam, s in tables.items():
            if iid in s or (iid // 100) * 100 in s:
                votes[str(cat)][fam] += 1
    return {cat: c.most_common(1)[0][0] for cat, c in votes.items() if c}


def resolve_name(iid, family, fmgs, custom):
    """(name, verdict) for one lot slot; name is None when nothing here can name it.

    `family` is the learned family for the slot's category, or None when unknown. Rules are tried in
    the docstring's order and the verdict says WHICH fired -- a name with no verdict cannot be
    audited, which is the whole reason the worklist carries verdicts too.
    """
    if iid is None:
        return None, "no item id"
    if iid in custom:                                   # rule 3
        bw, gem = custom[iid]
        wn = (fmgs.get("Weapon", {}).get(bw)
              or fmgs.get("Weapon", {}).get((bw // 100) * 100) or "weapon %d" % bw)
        gn = fmgs.get("Gem", {}).get(gem) or "gem %d" % gem
        lvl = bw % 100
        return ("%s%s with %s" % (wn, "+%d" % lvl if lvl else "", gn),
                "EquipParamCustomWeapon (weapon + Ash of War)")
    own = fmgs.get(family or "", {})
    if iid in own:
        return own[iid], "own-category FMG"
    base = (iid // 100) * 100                           # rule 2
    if base != iid and base in own:
        return own[base], "own-category FMG after stripping reinforcement (base %d)" % base
    elsewhere = sorted(f for f, d in fmgs.items() if iid in d or (base != iid and base in d))
    if elsewhere:
        return None, ("WRONG FAMILY: id resolves only in %s -- the category -> family map is the "
                      "open question" % ",".join(elsewhere))
    return None, "ABSENT from every param and FMG here"


class Namer:
    """Load the three corpora once, then ask many times. `available` is False with no artifacts."""

    def __init__(self, inputs):
        self.inputs = inputs
        self.fmgs = load_fmgs(inputs)
        self.custom = load_custom_weapons(inputs)
        self.family_ids = load_family_ids(inputs)
        self.families = {}
        self.available = bool(self.custom or any(self.fmgs.values()))

    def learn(self, pairs):
        self.families = learn_category_families(pairs, self.family_ids, self.custom)
        return self.families

    def name(self, iid, category):
        return resolve_name(iid, self.families.get(str(category)), self.fmgs, self.custom)
