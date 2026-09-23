"""Hand-curated (NOT auto-generated): one gating-boss defeat flag per named region, for the
`region_sweep` option (SPEC-region-completion-release.md). Priority per region, per Alaric's ruling
2026-09-23: Great Rune boss, else the region's biggest Remembrance boss, else its MajorBoss. Two
regions (Limgrave, Gravesite) had no candidate at any of the three tiers and were picked directly by
Alaric -- see SPEC-region-completion-release.md §1c for the reasoning behind every entry and the three
tie-breaks (Farum Azula, Shadow Keep, Liurnia) in §1b.

Every flag here is also a key in tables.boss_sweeps.SWEEP_REGION (or, for the two direct picks, a
recognized boss_healthbars flag), so region_sweep composes with the existing sweep_trigger_reachable /
runtime_sweep_skips machinery in features/boss_locks.py without new plumbing.
"""

REGION_GATING_BOSS = {
    # Great Rune bosses
    'Stormveil': 10000800,               # Godrick the Grafted
    'Leyndell': 11000800,                # Morgott, the Omen King
    'Caelid': 1252380800,                # Starscourge Radahn (festival-alias flag)
    'Mt. Gelmir': 16000800,              # Rykard, Lord of Blasphemy
    'Mohgwyn': 12050800,                 # Mohg, Lord of Blood
    'Haligtree': 15000800,               # Malenia, Blade of Miquella
    'Raya Lucaria Academy': 14000800,    # Rennala, Queen of the Full Moon

    # Remembrance bosses
    'Ainsel River': 12040800,            # Astel, Naturalborn of the Void
    'Siofra River': 12090800,            # Regal Ancestor Spirit
    'Deeproot Depths': 12030850,         # Lichdragon Fortissax
    'Farum Azula': 13000800,             # Maliketh, the Black Blade (over Placidusax, optional)
    'Belurat': 20000800,                 # Divine Beast Dancing Lion
    'Enir Ilim': 20010800,               # Radahn, Consort of Miquella
    'Scadu Altus': 25000800,             # Metyr, Mother of Fingers
    'Shadow Keep': 21010800,             # Base Serpent Messmer (over Gaius / Scadutree Avatar)
    'Cerulean': 22000800,                # Putrescent Knight
    'Abyssal': 28000800,                 # Midra, Lord of Frenzied Flame
    'Ancient Ruins': 2044450800,         # Romina, Saint of the Bud
    'Ensis': 2048440800,                 # Rellana, Twin Moon Knight
    'Mountaintops of the Giants': 1252520800,  # Fire Giant (festival-alias flag)

    # MajorBoss fallbacks
    'Ashen Capital': 11050800,           # Godfrey, First Elden Lord
    'Weeping': 1043300800,               # Leonine Misbegotten, Castle Morne Boss
    'Liurnia': 1035500800,               # Royal Knight Loretta (over Magma Wyrm Makar, minor dungeon)
    'Altus': 1039540800,                 # Elemer of the Briar
    'Consecrated Snowfield': 1050560800,  # Great Wyrm Theodorix
    'Rauh Base': 2044470800,             # Rugalea the Great Red Bear
    'Jagged Peak': 2054390800,           # Bayle the Dread

    # Direct picks (no Great Rune / Remembrance / MajorBoss candidate existed) -- Alaric, 2026-09-23
    'Limgrave': 1043360800,              # Flying Dragon Agheel
    'Gravesite': 41010800,               # Curseblade Labirith
}
