"""AUTO-GENERATED (tools/datamine_boss_drops.py). Boss-healthbar enemy DROPS
(field/evergaol/dragon bosses; remembrance/great-rune majors excluded). getItemFlagId
set + names for gen_data to tag 'Boss'. Matt-free (EMEVD common-event args + params)."""
BOSS_DROP_FLAGS = frozenset({
    530620,  # Dragon Halberd
    530600,  # Dragonscale Blade
    12037950,  # Siluria's Tree
    65060,  # Speckled Hardtear
    530965,  # Ash of War: Aspects of the Crucible: Wings
    1052417100,  # Ash of War: Bloodhound's Step
    530855,  # Ash of War: Ghostflame Call
    1049377100,  # Ash of War: Poison Moth Flight
    1049397850,  # Battlemage Hugues
    530955,  # Black Steel Greatshield
    65050,  # Cerulean Crystal Tear
    65250,  # Cerulean Hidden Tear
    530405,  # Commander's Standard
    65070,  # Crimson Bubbletear
    65000,  # Crimsonspill Crystal Tear
    530530,  # Death Ritual Spear
    1049377110,  # Death's Poker
    530550,  # Dragon Heart
    530420,  # Dragon Heart
    530510,  # Dragon Heart
    530860,  # Dragon Heart
    530840,  # Dragon Heart
    530850,  # Dragon Heart
    530945,  # Dragon Heart
    530800,  # Dragon Heart
    65280,  # Flame-Shrouding Cracked Tear
    530505,  # Gargoyle's Black Blades
    530425,  # Gargoyle's Blackblade
    65310,  # Holy-Shrouding Cracked Tear
    65300,  # Lightning-Shrouding Cracked Tear
    65080,  # Opaline Bubbletear
    65110,  # Opaline Hardtear
    530930,  # Pelt of Ralva
    65160,  # Ruptured Crystal Tear
    65170,  # Ruptured Crystal Tear
    530845,  # Star-Lined Sword
    65260,  # Stonebarb Cracked Tear
    65130,  # Thorny Cracked Tear
    530940,  # [Incantation] Divine Beast Tornado
    530905,  # [Incantation] Roar of Rugalea
    530515,  # [Incantation] Vyke's Dragonbolt
    1048577700,  # [Sorcery] Explosive Ghostflame
    530960,  # [Sorcery] Gravitational Missile
    530805,  # Ancient Dragon Smithing Stone
    530861,  # Somber Ancient Dragon Smithing Stone
    530130,  # Bloodhound's Fang
    530120,  # [Incantation] Aspects of the Crucible: Tail
    530265,  # Black Knife Tiche
    65040,  # Cerulean Crystal Tear
    530250,  # [Sorcery] Greatblade Phalanx
    530260,  # Dragon Heart
    530210,  # Dragon Heart
    530225,  # Crucible Knot Talisman
    530100,  # Golden Halberd
    530390,  # Dragon Heart
    1036457400,  # [Sorcery] Ancient Death Rancor
    1036487400,  # Ash of War: Giant Hunt
    530255,  # [Sorcery] Meteorite
    530375,  # Somber Smithing Stone [6]
    1037427400,  # Red-Feathered Branchsword
    1037467400,  # Meat Peddler's Bell Bearing
    530300,  # [Incantation] Lansseax's Glaive
    60450,  # Memory Stone
    65180,  # Leaden Hardtear
    530245,  # [Incantation] Flame of the Fell God
    65290,  # Magic-Shrouding Cracked Tear
    530385,  # Deathroot
    1039437400,  # Ash of War: Ice Spear
    530240,  # Deathroot
    1039517200,  # Ash of War: Shared Order
    530350,  # Black Knife
    530310,  # Somber Smithing Stone [5]
    1042337100,  # Radagon's Scarseal
    1042387400,  # Blue-Feathered Branchsword
    1042387410,  # Bone Peddler's Bell Bearing
    530325,  # Godskin Peeler
    65090,  # Crimsonburst Crystal Tear
    530110,  # Dragon Heart
    1043377400,  # Ash of War: Repeating Thrust
    1043537400,  # Medicine Peddler's Bell Bearing
    1044327410,  # Ash of War: Barricade Shield
    1044327400,  # Sacrificial Axe
    1044537300,  # Twinbird Kite Shield
    530170,  # Deathroot
    530315,  # Dragon Greatclaw
    65100,  # Greenburst Crystal Tear
    530400,  # Dragon Heart
    1048417800,  # Gravity Stone Peddler's Bell Bearing
})

# flag -> the boss ENTITY that drops it, and the CLASS of the map it stands in.
# The entity and the lot arrive together in the same common-event args
# ($Event(90005860, ..., chrEntityId, ..., itemLotId, ...)), and this tool has always
# read both -- it just discarded the entity, so nothing could join a boss CHECK to its
# boss. That join is what LegacyBoss/Underground/FieldBoss need, and it could not be
# recovered downstream: DUNGEON_SWEEPS is filler-only by construction, so a boss reward
# check is never inside its own sweep (measured: legacy sweeps x Boss-tagged aps = 0).
# CLASS is by containing emevd map, via datamine_boss_healthbars._class -- ONE definition,
# imported, not restated: m30=catacomb m31=cave m32=tunnel m60=field,
# m34/m39/m40/m41/m42/m43=dungeon (minor), everything else=legacy.
BOSS_DROP_ENTITY = {
    530620: 12020830,  # m12_02_00_00 Dragon Halberd
    530600: 12010850,  # m12_01_00_00 Dragonscale Blade
    12037950: 12030390,  # m12_03_00_00 Siluria's Tree
    65060: 1041530800,  # m60_41_53_00 Speckled Hardtear
    530965: 2049430850,  # m61_49_43_00 Ash of War: Aspects of the Crucible: Wings
    1052417100: 1052410850,  # m60_52_41_00 Ash of War: Bloodhound's Step
    530855: 2047390800,  # m61_47_39_00 Ash of War: Ghostflame Call
    1049377100: 1049370800,  # m60_49_37_00 Ash of War: Poison Moth Flight
    1049397850: 1049390850,  # m60_49_39_00 Battlemage Hugues
    530955: 2047450800,  # m61_47_45_00 Black Steel Greatshield
    65050: 1052560800,  # m60_52_56_00 Cerulean Crystal Tear
    65250: 1037540810,  # m60_37_54_00 Cerulean Hidden Tear
    530405: 1049380800,  # m60_49_38_00 Commander's Standard
    65070: 1052560800,  # m60_52_56_00 Crimson Bubbletear
    65000: 1041530800,  # m60_41_53_00 Crimsonspill Crystal Tear
    530530: 1050570800,  # m60_50_57_00 Death Ritual Spear
    1049377110: 1049370850,  # m60_49_37_00 Death's Poker
    530550: 1050560800,  # m60_50_56_00 Dragon Heart
    530420: 1052410800,  # m60_52_41_00 Dragon Heart
    530510: 1054560800,  # m60_54_56_00 Dragon Heart
    530860: 2045440800,  # m61_45_44_00 Dragon Heart
    530840: 2048380850,  # m61_48_38_00 Dragon Heart
    530850: 2049410800,  # m61_49_41_00 Dragon Heart
    530945: 2049430800,  # m61_49_43_00 Dragon Heart
    530800: 2052400800,  # m61_52_40_00 Dragon Heart
    65280: 1047400800,  # m60_47_40_00 Flame-Shrouding Cracked Tear
    530505: 1049520800,  # m60_49_52_00 Gargoyle's Black Blades
    530425: 1051430800,  # m60_51_43_00 Gargoyle's Blackblade
    65310: 1038480800,  # m60_38_48_00 Holy-Shrouding Cracked Tear
    65300: 1038480800,  # m60_38_48_00 Lightning-Shrouding Cracked Tear
    65080: 1043330800,  # m60_43_33_00 Opaline Bubbletear
    65110: 1051400800,  # m60_51_40_00 Opaline Hardtear
    530930: 2049450800,  # m61_49_45_00 Pelt of Ralva
    65160: 1033430800,  # m60_33_43_00 Ruptured Crystal Tear
    65170: 1050570850,  # m60_50_57_00 Ruptured Crystal Tear
    530845: 2046400800,  # m61_46_40_00 Star-Lined Sword
    65260: 1051400800,  # m60_51_40_00 Stonebarb Cracked Tear
    65130: 1050570850,  # m60_50_57_00 Thorny Cracked Tear
    530940: 2046460800,  # m61_46_46_00 [Incantation] Divine Beast Tornado
    530905: 2044470800,  # m61_44_47_00 [Incantation] Roar of Rugalea
    530515: 1053560800,  # m60_53_56_00 [Incantation] Vyke's Dragonbolt
    1048577700: 1048570800,  # m60_48_57_00 [Sorcery] Explosive Ghostflame
    530960: 2052480800,  # m61_52_48_00 [Sorcery] Gravitational Missile
    530805: 2054390850,  # m61_54_39_00 Ancient Dragon Smithing Stone
    530861: 2045440800,  # m61_45_44_00 Somber Ancient Dragon Smithing Stone
    530130: 1044350800,  # m60_44_35_00 Bloodhound's Fang
    530120: 1042370800,  # m60_42_37_00 [Incantation] Aspects of the Crucible: Tail
    530265: 1033420800,  # m60_33_42_00 Black Knife Tiche
    65040: 1033430800,  # m60_33_43_00 Cerulean Crystal Tear
    530250: 1033450800,  # m60_33_45_00 [Sorcery] Greatblade Phalanx
    530260: 1034420800,  # m60_34_42_00 Dragon Heart
    530210: 1034450800,  # m60_34_45_00 Dragon Heart
    530225: 1035420800,  # m60_35_42_00 Crucible Knot Talisman
    530100: 1042360800,  # m60_42_36_00 Golden Halberd
    530390: 1035530800,  # m60_35_53_00 Dragon Heart
    1036457400: 1036450340,  # m60_36_45_00 [Sorcery] Ancient Death Rancor
    1036487400: 1036480340,  # m60_36_48_00 Ash of War: Giant Hunt
    530255: 1036500800,  # m60_36_50_00 [Sorcery] Meteorite
    530375: 1036540800,  # m60_36_54_00 Somber Smithing Stone [6]
    1037427400: 1037420340,  # m60_37_42_00 Red-Feathered Branchsword
    1037467400: 1037460800,  # m60_37_46_00 Meat Peddler's Bell Bearing
    530300: 1037510800,  # m60_37_51_00 [Incantation] Lansseax's Glaive
    60450: 1037530800,  # m60_37_53_00 Memory Stone
    65180: 1037540810,  # m60_37_54_00 Leaden Hardtear
    530245: 1038410800,  # m60_38_41_00 [Incantation] Flame of the Fell God
    65290: 1038480800,  # m60_38_48_00 Magic-Shrouding Cracked Tear
    530385: 1038520340,  # m60_38_52_00 Deathroot
    1039437400: 1039430340,  # m60_39_43_00 Ash of War: Ice Spear
    530240: 1039440800,  # m60_39_44_00 Deathroot
    1039517200: 1039510800,  # m60_39_51_00 Ash of War: Shared Order
    530350: 1040520800,  # m60_40_52_00 Black Knife
    530310: 1041500800,  # m60_41_50_00 Somber Smithing Stone [5]
    1042337100: 1042330800,  # m60_42_33_00 Radagon's Scarseal
    1042387400: 1042380800,  # m60_42_38_00 Blue-Feathered Branchsword
    1042387410: 1042380850,  # m60_42_38_00 Bone Peddler's Bell Bearing
    530325: 1042550800,  # m60_42_55_00 Godskin Peeler
    65090: 1043330800,  # m60_43_33_00 Crimsonburst Crystal Tear
    530110: 1043360800,  # m60_43_36_00 Dragon Heart
    1043377400: 1043370340,  # m60_43_37_00 Ash of War: Repeating Thrust
    1043537400: 1043530800,  # m60_43_53_00 Medicine Peddler's Bell Bearing
    1044327410: 1044320342,  # m60_44_32_00 Ash of War: Barricade Shield
    1044327400: 1044320340,  # m60_44_32_00 Sacrificial Axe
    1044537300: 1044530800,  # m60_44_53_00 Twinbird Kite Shield
    530170: 1045390800,  # m60_45_39_00 Deathroot
    530315: 1045520800,  # m60_45_52_00 Dragon Greatclaw
    65100: 1047400800,  # m60_47_40_00 Greenburst Crystal Tear
    530400: 1048370800,  # m60_48_37_00 Dragon Heart
    1048417800: 1048410800,  # m60_48_41_00 Gravity Stone Peddler's Bell Bearing
}
BOSS_DROP_CLASS = {
    530620: 'legacy',
    530600: 'legacy',
    12037950: 'legacy',
    65060: 'field',
    530965: 'legacy',
    1052417100: 'field',
    530855: 'legacy',
    1049377100: 'field',
    1049397850: 'field',
    530955: 'legacy',
    65050: 'field',
    65250: 'field',
    530405: 'field',
    65070: 'field',
    65000: 'field',
    530530: 'field',
    1049377110: 'field',
    530550: 'field',
    530420: 'field',
    530510: 'field',
    530860: 'legacy',
    530840: 'legacy',
    530850: 'legacy',
    530945: 'legacy',
    530800: 'legacy',
    65280: 'field',
    530505: 'field',
    530425: 'field',
    65310: 'field',
    65300: 'field',
    65080: 'field',
    65110: 'field',
    530930: 'legacy',
    65160: 'field',
    65170: 'field',
    530845: 'legacy',
    65260: 'field',
    65130: 'field',
    530940: 'legacy',
    530905: 'legacy',
    530515: 'field',
    1048577700: 'field',
    530960: 'legacy',
    530805: 'legacy',
    530861: 'legacy',
    530130: 'field',
    530120: 'field',
    530265: 'field',
    65040: 'field',
    530250: 'field',
    530260: 'field',
    530210: 'field',
    530225: 'field',
    530100: 'field',
    530390: 'field',
    1036457400: 'field',
    1036487400: 'field',
    530255: 'field',
    530375: 'field',
    1037427400: 'field',
    1037467400: 'field',
    530300: 'field',
    60450: 'field',
    65180: 'field',
    530245: 'field',
    65290: 'field',
    530385: 'field',
    1039437400: 'field',
    530240: 'field',
    1039517200: 'field',
    530350: 'field',
    530310: 'field',
    1042337100: 'field',
    1042387400: 'field',
    1042387410: 'field',
    530325: 'field',
    65090: 'field',
    530110: 'field',
    1043377400: 'field',
    1043537400: 'field',
    1044327410: 'field',
    1044327400: 'field',
    1044537300: 'field',
    530170: 'field',
    530315: 'field',
    65100: 'field',
    530400: 'field',
    1048417800: 'field',
}
