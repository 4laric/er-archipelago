"""M4G native-lot and independent-route witnesses for oracle region gaps (2026-09-10).

Coordinates establish placements, not new PlayArea measurements. Region membership,
all AP siblings, sweep containment and actual lock reachability are checked separately.
"""
import csv
import json
from pathlib import Path
import unittest

from BaseClasses import CollectionState
from test.bases import WorldTestBase
from worlds.eldenring.tables.data import LOCATIONS, REGIONS
from worlds.eldenring.tables.boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION

EXPECTED = {
    65420: "Ancient Ruins", 520800: "Gravesite", 540118: "Limgrave",
    2048417980: "Gravesite", 2049427700: "Abyssal", 2049427720: "Abyssal",
    2050417700: "Abyssal", 2051417700: "Abyssal", 2051417710: "Abyssal",
    2052427500: "Abyssal", 2050467500: "Scadu Altus", 2050467510: "Scadu Altus",
}


class MfgOracleRegionEvidence(unittest.TestCase):
    def test_all_native_lots_resolve_to_the_recorded_flags(self):
        root = next(p for p in Path(__file__).resolve().parents
                    if (p / "greenfield/gen_data.py").is_file())
        gf = root / "greenfield"
        evidence = json.loads((gf / "evidence/mfg_oracle_regions.json").read_text(encoding="utf-8"))
        with (gf / "flag_lots.tsv").open(encoding="utf-8") as fh:
            lots = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual({r["flag"] for r in evidence["rows"]}, set(EXPECTED))
        for row in evidence["rows"]:
            pin = row["pin"]
            flags = {int(r["flag"]) for r in lots
                     if r["table"] == pin["lotSource"] and int(r["lot"]) == pin["itemLotId"]}
            self.assertEqual(flags, {row["flag"]})
            self.assertEqual(row["region"], EXPECTED[row["flag"]])

    def test_region_and_sweep_ownership_agree_for_every_sibling(self):
        found = set()
        for region, locations in LOCATIONS.items():
            for name, ap, flag in locations:
                if flag not in EXPECTED:
                    continue
                found.add(flag)
                self.assertEqual(region, EXPECTED[flag], name)
                for trigger, members in DUNGEON_SWEEPS.items():
                    if ap in members:
                        self.assertEqual(SWEEP_REGION[trigger], region, (flag, trigger))
        self.assertEqual(found, set(EXPECTED))


class MfgOracleRegionLocks(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": len(REGIONS)}
    run_default_tests = False

    def test_correct_lock_is_needed_and_sufficient_with_other_requirements_held(self):
        flags = {ap: flag for rows in LOCATIONS.values() for _, ap, flag in rows}
        targets = [loc for loc in self.multiworld.get_locations(self.player)
                   if flags.get(loc.address) in EXPECTED]
        self.assertEqual({flags[loc.address] for loc in targets}, set(EXPECTED))
        everything = (list(self.multiworld.itempool)
                      + list(self.multiworld.precollected_items[self.player])
                      + [loc.item for loc in self.multiworld.get_locations(self.player)
                         if loc.item is not None])
        for region in set(EXPECTED.values()):
            lock = region + " Lock"
            state = CollectionState(self.multiworld)
            for item in everything:
                if item.advancement and item.name != lock:
                    state.collect(item, prevent_sweep=True)
            locations = [loc for loc in targets if EXPECTED[flags[loc.address]] == region]
            for loc in locations:
                self.assertFalse(loc.can_reach(state), f"{loc.name} bypasses {lock}")
            state.collect(self.world.create_item(lock), prevent_sweep=True)
            for loc in locations:
                self.assertTrue(loc.can_reach(state), f"{loc.name} still blocked with {lock}")
