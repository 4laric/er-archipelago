"""Season 6 E1 adapters. Encounter identities come from generated project tables.

Source IDs refer to the hashed snapshots in DESIGN-bingo-objective-audit.md.
Generic boss families resolve to one concrete encounter on this AP board.
"""
# source template -> exact advisory names in our generated encounter table.
BOSSES = {
 "BASE-004": ("Morgott, the Omen King",), "BASE-005": ("Rykard, Lord of Blasphemy",),
 "BASE-006": ("Ancestor Spirit", "Regal Ancestor Spirit"), "BASE-007": ("Magma Wyrm Makar",),
 "BASE-008": ("Mohg, Lord of Blood",), "BASE-010": ("Leonine Misbegotten",),
 "BASE-013": ("Godskin Apostle",), "BASE-014": ("Godfrey, First Elden Lord",),
 "BASE-015": ("Valiant Gargoyle",), "BASE-016": ("Fia's Champion",),
 "BASE-017": ("Mohg, the Omen",), "BASE-018": ("Royal Knight Loretta",),
 "BASE-019": ("Commander O'Neil",), "BASE-020": ("Grafted Scion",),
 "BASE-023": ("Tree Sentinel",), "BASE-024": ("Crucible Knight",),
 "BASE-025": ("Elemer of the Briar",), "BASE-026": ("Crystalian (Spear)", "Putrid Crystalian (Spear)"),
 "BASE-027": ("Wormface",), "BASE-031": ("Dragonkin Soldier", "Dragonkin Soldier of Nokstella"),
 "BASE-034": ("Black Blade Kindred",), "BASE-068": ("Fire Giant",),
 "BASE-100": ("Ancient Dragon Lansseax",), "BASE-111": ("Malenia, Blade of Miquella",),
 "BASE-112": ("Borealis the Freezing Fog",), "BASE-115": ("Misbegotten Crusader",),
 "BASE-117": ("Roundtable Knight Vyke",),
 "DLC-005": ("Golden Hippopotamus",), "DLC-007": ("Bayle the Dread",),
 "DLC-009": ("Midra, Lord of Frenzied Flame",), "DLC-011": ("Radahn, Consort of Miquella",),
 "DLC-024": ("Ancient Dragon Senessax",), "DLC-032": ("Curseblade Labirith",),
 "DLC-037": ("Jori, Elder Inquisitor",), "DLC-043": ("Lamenter",),
 "DLC-048": ("Death Knight",), "DLC-061": ("Chief Bloodfiend",),
 "DLC-062": ("Putrescent Knight",), "DLC-064": ("Scadutree Avatar",),
 "DLC-065": ("Rellana, Twin Moon Knight",), "DLC-066": ("Metyr, Mother of Fingers",),
 "DLC-067": ("Base Serpent Messmer",), "DLC-068": ("Fallingstar Beast",),
 "DLC-069": ("Romina, Saint of the Bud",), "DLC-073": ("Ancient Dragon-Man",),
 "DLC-076": ("Death Rite Bird",), "DLC-086": ("Rakshasa",),
}
# Fixed encounter qualifiers from boss_healthbars/boss_sweeps and their EMEVD events.
# Duo/trio terminal flags wait for every member; Lansseax uses the final Altus encounter.
EXACT = {"BASE-014": {11000850}, "BASE-018": {1035500800}, "BASE-020": {10010800},
         "BASE-023": {1041510800}, "BASE-024": {1051360800}, "BASE-026": {31110800},
         "BASE-100": {1041520800}}
STATE_GOALS = (
 ("BASE-078", "flask_potency", (7,), "Flask potency", "Limgrave"),
 ("BASE-079", "flask_charges", (10,), "Flask charges", "Limgrave"),
 ("BASE-096", "level", (55, 60, 65), "Rune level", "Limgrave"),
 ("BASE-097", "faith", (30,), "Base Faith", "Limgrave"),
 ("BASE-098", "arcane", (30,), "Base Arcane", "Limgrave"),
 ("BASE-099", "intelligence", (30,), "Base Intelligence", "Limgrave"),
 ("DLC-002", "scadutree", (9, 10, 11), "Scadutree blessing", "Gravesite"),
 ("DLC-003", "spirit_ash", (5,), "Revered Spirit Ash blessing", "Gravesite"),
 ("DLC-083", "level", (80, 85), "Rune level", "Gravesite"),
)


def candidates(healthbars, arenas, eligible, *, progressive_flasks=True, blessing_mode=0, sweep_regions=None):
    out = []
    for source, names in BOSSES.items():
        for flag, info in healthbars.items():
            region = arenas.get(flag)
            # These overworld E1 encounters have no arena row; their own sweep has
            # a generated single-region owner. Do not extend this fallback to other bosses.
            if source in {"BASE-019", "BASE-100", "BASE-112"}:
                region = (sweep_regions or {}).get(flag)
            # The intro map belongs to Stormveil's grouping; revisiting needs the Belfries key.
            if source == "BASE-020" and flag == 10010800:
                region = "Stormveil"
            if info[3] not in names or region not in eligible:
                continue
            if source in EXACT and flag not in EXACT[source]:
                continue
            if source.startswith("BASE") and str(info[0]).startswith(("m20", "m21", "m22", "m25", "m28", "m61", "m40", "m41", "m43")):
                continue
            if source.startswith("DLC") and not str(info[0]).startswith(("m20", "m21", "m22", "m25", "m28", "m61", "m40", "m41", "m43")):
                continue
            cell = {"flag": flag, "region": region, "label": f"Defeat {info[3]} ({region})",
                    "family": "S6-" + source, "source": "S6-" + source, "requirements": []}
            encounter_labels = {"BASE-023": "Tree Sentinel duo", "BASE-024": "Crucible Knight and Misbegotten Warrior",
                                "BASE-026": "Putrid Crystalian trio", "BASE-015": "Valiant Gargoyle duo"}
            if source in encounter_labels:
                cell["label"] = f"Defeat {encounter_labels[source]} ({region})"
            if source == "BASE-020":
                cell.update(regions=[region, "Liurnia"], requirements=[["Imbued Sword Key", 1]])
                if "Liurnia" not in eligible:
                    continue
            if source == "DLC-066":
                # Both Finger Ruins bells: Rhia in Cerulean, Dheo behind Shadow Keep.
                cell["regions"] = [region, "Cerulean", "Shadow Keep"]
                if not set(cell["regions"]) <= set(eligible):
                    continue
            out.append(cell)
    for source, metric, targets, label, region in STATE_GOALS:
        if region not in eligible or (metric.startswith("flask") and not progressive_flasks):
            continue
        # Catch-up floors also manufacture blessing observations; only the earned vanilla mode.
        if metric == "scadutree" and blessing_mode != 0:
            continue
        for target in targets:
            requirements = []
            if metric == "flask_potency": requirements = [["Progressive Flask Upgrade", target * 2]]
            if metric == "flask_charges": requirements = [["Progressive Flask Upgrade", (target - 4) * 2 - 1]]
            if metric == "scadutree":
                units = {9: 17, 10: 20, 11: 23}[target]
                requirements = [["Scadutree Fragment x2", (units + 1) // 2]]
            if metric == "spirit_ash": requirements = [["Revered Spirit Ash", 9]]
            out.append({"flag": 0, "region": region, "label": f"Reach {label} {target}",
                        "state": {"metric": metric, "target": target}, "family": "state:" + metric,
                        "source": "S6-" + source, "requirements": requirements,
                        "supply_goal": bool(requirements)})
    return out


def select(candidates, seed, *, region_limit, parents, start_pool=(), starts=1):
    """E1 draw: distinct encounters/source families, one upgrade supply goal, full closure."""
    import hashlib
    import random
    from .bingo_board import BINGO_LOCATION_BASE
    rng = random.Random(hashlib.sha256(str(seed).encode()).digest())
    candidates = sorted(candidates, key=lambda c: (c.get("source", ""), c["flag"], c["label"]))
    def closure(cell):
        regions = set(cell.get("regions", [cell["region"]]))
        for owner in tuple(regions):
            seen = {owner}
            while owner in parents:
                owner = parents[owner]
                if owner in seen:
                    raise ValueError("bingo region parents contain a cycle")
                seen.add(owner)
                regions.add(owner)
        return regions
    for _ in range(256):
        order = rng.sample(candidates, len(candidates))
        opening = []
        for cell in order:
            if cell["region"] in start_pool and cell["region"] not in {c["region"] for c in opening}:
                opening.append(cell)
                if len(opening) == starts:
                    break
        if start_pool and len(opening) != starts:
            raise ValueError("bingo start_region_pool needs enough distinct objective regions")
        selected, regions, families, flags = [], set(), set(), set()
        supply = False
        hits, counters = {}, 0
        for cell in opening + [c for c in order if c not in opening]:
            family = cell.get("family", f"boss:{cell['flag']}")
            needed = regions | closure(cell)
            from .features.bingo import evidence_flags
            evidence = evidence_flags(cell)
            if (family in families or (cell["flag"] and cell["flag"] in flags)
                    or (supply and cell.get("supply_goal")) or len(needed) > region_limit
                    or (cell.get("counter") and counters >= 3)
                    or any(hits.get(f, 0) >= 2 for f in evidence)):

                continue
            selected.append(cell)
            regions, supply = needed, supply or cell.get("supply_goal", False)
            families.add(family)
            counters += bool(cell.get("counter"))
            for f in evidence: hits[f] = hits.get(f, 0) + 1
            flags.add(cell["flag"])
            if len(selected) == 25:
                break
        if len(selected) == 25 and all(c in selected for c in opening):
            rng.shuffle(selected)
            return [dict(c, location=BINGO_LOCATION_BASE + i) for i, c in enumerate(selected)]
    raise ValueError(f"bingo E1 cannot fit 25 distinct objectives in {region_limit} regions")
