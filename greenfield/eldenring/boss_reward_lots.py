"""AUTO-GENERATED (tools/datamine_boss_reward_lots.py) -- DO NOT EDIT.

Mini-dungeon / scripted BOSS-REWARD lots: common.emevd awards these off a reward flag the
map EMEVD flips, so neither NpcParam nor the map-side common-event scan can see them.
BOSS_REWARD_TILE lets gen_data._recover_tile decode the 6-digit 5xxxxx flag family, which
carries no map encoding of its own and was therefore being dropped from the world.
"""
# handler -> what it is (auto-discovered by signature + award call, not hardcoded)
BOSS_REWARD_HANDLERS = {1100: 'ボス撃破_アイテム取得_XX -- Defeat boss_obtain item_XX', 1200: 'ボス撃破_アイテム取得_YY -- Defeat boss_obtain item_YY', 4857: ''}

BOSS_REWARD_TILE = {
    197: 'm14_00',   # lot 10180, reward flag 9118, handler 1100
    60440: 'm14_00',   # lot 10170, reward flag 9117, handler 1100
    60520: 'm11_00',   # lot 10050, reward flag 9105, handler 1100
    510010: 'm10_00',   # lot 10010, reward flag 9101, handler 1100
    510030: 'm10_01',   # lot 10030, reward flag 9103, handler 1100
    510040: 'm11_00',   # lot 10040, reward flag 9104, handler 1100
    510060: 'm11_05',   # lot 10060, reward flag 9106, handler 1100
    510070: 'm11_05',   # lot 10070, reward flag 9107, handler 1100
    510080: 'm12_04',   # lot 10080, reward flag 9108, handler 1100
    510090: 'm12_01',   # lot 10090, reward flag 9109, handler 1100
    510100: 'm12_02',   # lot 10100, reward flag 9110, handler 1100
    510110: 'm12_03',   # lot 10110, reward flag 9111, handler 1100
    510120: 'm12_05',   # lot 10120, reward flag 9112, handler 1100
    510140: 'm13_00',   # lot 10140, reward flag 9114, handler 1100
    510150: 'm13_00',   # lot 10150, reward flag 9115, handler 1100
    510160: 'm13_00',   # lot 10160, reward flag 9116, handler 1100
    510190: 'm15_00',   # lot 10190, reward flag 9119, handler 1100
    510200: 'm15_00',   # lot 10200, reward flag 9120, handler 1100
    510210: 'm16_00',   # lot 10210, reward flag 9121, handler 1100
    510220: 'm16_00',   # lot 10220, reward flag 9122, handler 1100
    510230: 'm19_00',   # lot 10230, reward flag 9123, handler 1100
    510250: 'm35_00',   # lot 10250, reward flag 9125, handler 1100
    510260: 'm39_20',   # lot 10260, reward flag 9126, handler 1100
    510280: 'm18_00',   # lot 10280, reward flag 9128, handler 1100
    510290: 'm16_00',   # lot 10290, reward flag 9129, handler 1100
    510300: 'm60_52_38',   # lot 10300, reward flag 9130, handler 1100
    510310: 'm60_52_52',   # lot 10310, reward flag 9131, handler 1100
    510320: 'm12_08',   # lot 10320, reward flag 9132, handler 1100
    510330: 'm12_09',   # lot 10330, reward flag 9133, handler 1100
    510340: 'm12_02',   # lot 10340, reward flag 9134, handler 1100
    510350: 'm12_03',   # lot 10350, reward flag 9135, handler 1100
    510400: 'm20_00',   # lot 10400, reward flag 9140, handler 1100
    510430: 'm20_01',   # lot 10430, reward flag 9143, handler 1100
    510440: 'm21_00',   # lot 10440, reward flag 9144, handler 1100
    510460: 'm21_01',   # lot 10460, reward flag 9146, handler 1100
    510480: 'm22_00',   # lot 10480, reward flag 9148, handler 1100
    510550: 'm25_00',   # lot 10550, reward flag 9155, handler 1100
    510560: 'm28_00',   # lot 10560, reward flag 9156, handler 1100
    510600: 'm61_44_45',   # lot 10600, reward flag 9160, handler 1100
    510620: 'm61_50_48',   # lot 10620, reward flag 9162, handler 1100
    510630: 'm61_54_39',   # lot 10630, reward flag 9163, handler 1100
    510640: 'm61_49_48',   # lot 10640, reward flag 9164, handler 1100
    510730: 'm34_13',   # lot 10730, reward flag 9173, handler 1100
    510740: 'm34_14',   # lot 10740, reward flag 9174, handler 1100
    510800: 'm60_43_30',   # lot 10800, reward flag 9180, handler 1100
    510810: 'm60_35_50',   # lot 10810, reward flag 9181, handler 1100
    510820: 'm60_39_54',   # lot 10820, reward flag 9182, handler 1100
    510830: 'm60_51_36',   # lot 10830, reward flag 9183, handler 1100
    510840: 'm60_51_57',   # lot 10840, reward flag 9184, handler 1100
    510900: 'm61_48_44',   # lot 10900, reward flag 9190, handler 1100
    520000: 'm30_00',   # lot 20000, reward flag 9200, handler 1200
    520010: 'm30_01',   # lot 20010, reward flag 9201, handler 1200
    520020: 'm30_02',   # lot 20020, reward flag 9202, handler 1200
    520030: 'm30_11',   # lot 20030, reward flag 9203, handler 1200
    520040: 'm30_04',   # lot 20040, reward flag 9204, handler 1200
    520050: 'm30_05',   # lot 20050, reward flag 9205, handler 1200
    520060: 'm30_03',   # lot 20060, reward flag 9206, handler 1200
    520070: 'm30_06',   # lot 20070, reward flag 9207, handler 1200
    520080: 'm30_08',   # lot 20080, reward flag 9208, handler 1200
    520090: 'm30_09',   # lot 20090, reward flag 9209, handler 1200
    520100: 'm30_10',   # lot 20100, reward flag 9210, handler 1200
    520110: 'm30_12',   # lot 20110, reward flag 9211, handler 1200
    520120: 'm30_07',   # lot 20120, reward flag 9212, handler 1200
    520130: 'm30_13',   # lot 20130, reward flag 9213, handler 1200
    520140: 'm30_14',   # lot 20140, reward flag 9214, handler 1200
    520150: 'm30_15',   # lot 20150, reward flag 9215, handler 1200
    520160: 'm30_16',   # lot 20160, reward flag 9216, handler 1200
    520170: 'm30_17',   # lot 20170, reward flag 9217, handler 1200
    520180: 'm30_18',   # lot 20180, reward flag 9218, handler 1200
    520190: 'm30_19',   # lot 20190, reward flag 9219, handler 1200
    520200: 'm30_20',   # lot 20200, reward flag 9220, handler 1200
    520210: 'm30_05',   # lot 20210, reward flag 9221, handler 1200
    520220: 'm35_00',   # lot 20220, reward flag 9222, handler 1200
    520300: 'm31_02',   # lot 20300, reward flag 9230, handler 1200
    520310: 'm31_01',   # lot 20310, reward flag 9231, handler 1200
    520320: 'm31_00',   # lot 20320, reward flag 9232, handler 1200
    520330: 'm31_03',   # lot 20330, reward flag 9233, handler 1200
    520340: 'm31_15',   # lot 20340, reward flag 9234, handler 1200
    520350: 'm31_17',   # lot 20350, reward flag 9235, handler 1200
    520360: 'm31_04',   # lot 20360, reward flag 9236, handler 1200
    520370: 'm31_05',   # lot 20370, reward flag 9237, handler 1200
    520380: 'm31_06',   # lot 20380, reward flag 9238, handler 1200
    520390: 'm31_07',   # lot 20390, reward flag 9239, handler 1200
    520400: 'm31_09',   # lot 20400, reward flag 9240, handler 1200
    520410: 'm31_18',   # lot 20410, reward flag 9241, handler 1200
    520420: 'm31_19',   # lot 20420, reward flag 9242, handler 1200
    520430: 'm31_21',   # lot 20430, reward flag 9243, handler 1200
    520440: 'm31_10',   # lot 20440, reward flag 9244, handler 1200
    520450: 'm31_20',   # lot 20450, reward flag 9245, handler 1200
    520460: 'm31_11',   # lot 20460, reward flag 9246, handler 1200
    520470: 'm31_12',   # lot 20470, reward flag 9247, handler 1200
    520480: 'm31_22',   # lot 20480, reward flag 9248, handler 1200
    520490: 'm31_19',   # lot 20490, reward flag 9249, handler 1200
    520600: 'm32_00',   # lot 20600, reward flag 9260, handler 1200
    520610: 'm32_01',   # lot 20610, reward flag 9261, handler 1200
    520620: 'm32_02',   # lot 20620, reward flag 9262, handler 1200
    520630: 'm32_04',   # lot 20630, reward flag 9263, handler 1200
    520640: 'm34_12',   # lot 20640, reward flag 9264, handler 1200
    520650: 'm32_05',   # lot 20650, reward flag 9265, handler 1200
    520660: 'm32_07',   # lot 20660, reward flag 9266, handler 1200
    520670: 'm32_08',   # lot 20670, reward flag 9267, handler 1200
    520680: 'm32_11',   # lot 20680, reward flag 9268, handler 1200
    520700: 'm40_00',   # lot 20700, reward flag 9270, handler 1200
    520710: 'm40_01',   # lot 20710, reward flag 9271, handler 1200
    520750: 'm41_00',   # lot 20750, reward flag 9275, handler 1200
    520760: 'm41_01',   # lot 20760, reward flag 9276, handler 1200
    520770: 'm41_02',   # lot 20770, reward flag 9277, handler 1200
    520810: 'm43_01',   # lot 20810, reward flag 9281, handler 1200
}

BOSS_REWARD_LOT = {
    197: 10180,
    60440: 10170,
    60520: 10050,
    510010: 10010,
    510030: 10030,
    510040: 10040,
    510060: 10060,
    510070: 10070,
    510080: 10080,
    510090: 10090,
    510100: 10100,
    510110: 10110,
    510120: 10120,
    510140: 10140,
    510150: 10150,
    510160: 10160,
    510190: 10190,
    510200: 10200,
    510210: 10210,
    510220: 10220,
    510230: 10230,
    510250: 10250,
    510260: 10260,
    510280: 10280,
    510290: 10290,
    510300: 10300,
    510310: 10310,
    510320: 10320,
    510330: 10330,
    510340: 10340,
    510350: 10350,
    510400: 10400,
    510430: 10430,
    510440: 10440,
    510460: 10460,
    510480: 10480,
    510550: 10550,
    510560: 10560,
    510600: 10600,
    510620: 10620,
    510630: 10630,
    510640: 10640,
    510730: 10730,
    510740: 10740,
    510800: 10800,
    510810: 10810,
    510820: 10820,
    510830: 10830,
    510840: 10840,
    510900: 10900,
    520000: 20000,
    520010: 20010,
    520020: 20020,
    520030: 20030,
    520040: 20040,
    520050: 20050,
    520060: 20060,
    520070: 20070,
    520080: 20080,
    520090: 20090,
    520100: 20100,
    520110: 20110,
    520120: 20120,
    520130: 20130,
    520140: 20140,
    520150: 20150,
    520160: 20160,
    520170: 20170,
    520180: 20180,
    520190: 20190,
    520200: 20200,
    520210: 20210,
    520220: 20220,
    520300: 20300,
    520310: 20310,
    520320: 20320,
    520330: 20330,
    520340: 20340,
    520350: 20350,
    520360: 20360,
    520370: 20370,
    520380: 20380,
    520390: 20390,
    520400: 20400,
    520410: 20410,
    520420: 20420,
    520430: 20430,
    520440: 20440,
    520450: 20450,
    520460: 20460,
    520470: 20470,
    520480: 20480,
    520490: 20490,
    520600: 20600,
    520610: 20610,
    520620: 20620,
    520630: 20630,
    520640: 20640,
    520650: 20650,
    520660: 20660,
    520670: 20670,
    520680: 20680,
    520700: 20700,
    520710: 20710,
    520750: 20750,
    520760: 20760,
    520770: 20770,
    520810: 20810,
}

# reward getItemFlagId -> boss DEFEAT flag (PlayRegionParam boss-area join key; a reward
# flag with no single defeat event -- shared/duo reward flags -- is omitted, never guessed).
BOSS_REWARD_DEFEAT = {
    197: 14000800,   # defeat flag (boss-area key)
    60440: 14000850,   # defeat flag (boss-area key)
    60520: 11000850,   # defeat flag (boss-area key)
    510010: 10000800,   # defeat flag (boss-area key)
    510030: 10010800,   # defeat flag (boss-area key)
    510040: 11000800,   # defeat flag (boss-area key)
    510060: 11050850,   # defeat flag (boss-area key)
    510070: 11050800,   # defeat flag (boss-area key)
    510080: 12040800,   # defeat flag (boss-area key)
    510090: 12010800,   # defeat flag (boss-area key)
    510100: 12020800,   # defeat flag (boss-area key)
    510110: 12030850,   # defeat flag (boss-area key)
    510120: 12050800,   # defeat flag (boss-area key)
    510140: 13000850,   # defeat flag (boss-area key)
    510150: 13000830,   # defeat flag (boss-area key)
    510160: 13000800,   # defeat flag (boss-area key)
    510190: 15000850,   # defeat flag (boss-area key)
    510200: 15000800,   # defeat flag (boss-area key)
    510210: 16000850,   # defeat flag (boss-area key)
    510220: 16000800,   # defeat flag (boss-area key)
    510230: 19000800,   # defeat flag (boss-area key)
    510250: 35000800,   # defeat flag (boss-area key)
    510260: 39200800,   # defeat flag (boss-area key)
    510280: 18000800,   # defeat flag (boss-area key)
    510290: 16000860,   # defeat flag (boss-area key)
    510300: 1052380800,   # defeat flag (boss-area key)
    510310: 1052520800,   # defeat flag (boss-area key)
    510320: 12080800,   # defeat flag (boss-area key)
    510330: 12090800,   # defeat flag (boss-area key)
    510340: 12020850,   # defeat flag (boss-area key)
    510350: 12030800,   # defeat flag (boss-area key)
    510400: 20000800,   # defeat flag (boss-area key)
    510430: 20010800,   # defeat flag (boss-area key)
    510440: 21000850,   # defeat flag (boss-area key)
    510460: 21010800,   # defeat flag (boss-area key)
    510480: 22000800,   # defeat flag (boss-area key)
    510550: 25000800,   # defeat flag (boss-area key)
    510560: 28000800,   # defeat flag (boss-area key)
    510600: 2044450800,   # defeat flag (boss-area key)
    510620: 2050480800,   # defeat flag (boss-area key)
    510630: 2054390800,   # defeat flag (boss-area key)
    510640: 2049480800,   # defeat flag (boss-area key)
    510730: 34130800,   # defeat flag (boss-area key)
    510740: 34140850,   # defeat flag (boss-area key)
    510800: 1043300800,   # defeat flag (boss-area key)
    510810: 1035500800,   # defeat flag (boss-area key)
    510820: 1039540800,   # defeat flag (boss-area key)
    510830: 1051360800,   # defeat flag (boss-area key)
    510840: 1051570800,   # defeat flag (boss-area key)
    510900: 2048440800,   # defeat flag (boss-area key)
    520000: 30000800,   # defeat flag (boss-area key)
    520010: 30010800,   # defeat flag (boss-area key)
    520020: 30020800,   # defeat flag (boss-area key)
    520030: 30110800,   # defeat flag (boss-area key)
    520040: 30040800,   # defeat flag (boss-area key)
    520050: 30050800,   # defeat flag (boss-area key)
    520060: 30030800,   # defeat flag (boss-area key)
    520070: 30060800,   # defeat flag (boss-area key)
    520080: 30080800,   # defeat flag (boss-area key)
    520090: 30090800,   # defeat flag (boss-area key)
    520100: 30100800,   # defeat flag (boss-area key)
    520110: 30120800,   # defeat flag (boss-area key)
    520120: 30070800,   # defeat flag (boss-area key)
    520130: 30130800,   # defeat flag (boss-area key)
    520140: 30140800,   # defeat flag (boss-area key)
    520150: 30150800,   # defeat flag (boss-area key)
    520160: 30160800,   # defeat flag (boss-area key)
    520170: 30170800,   # defeat flag (boss-area key)
    520180: 30180800,   # defeat flag (boss-area key)
    520190: 30190800,   # defeat flag (boss-area key)
    520200: 30200800,   # defeat flag (boss-area key)
    520210: 30050850,   # defeat flag (boss-area key)
    520220: 35000850,   # defeat flag (boss-area key)
    520300: 31020800,   # defeat flag (boss-area key)
    520310: 31010800,   # defeat flag (boss-area key)
    520330: 31030800,   # defeat flag (boss-area key)
    520340: 31150800,   # defeat flag (boss-area key)
    520350: 31170800,   # defeat flag (boss-area key)
    520360: 31040800,   # defeat flag (boss-area key)
    520370: 31050800,   # defeat flag (boss-area key)
    520380: 31060800,   # defeat flag (boss-area key)
    520390: 31070800,   # defeat flag (boss-area key)
    520400: 31090800,   # defeat flag (boss-area key)
    520410: 31180800,   # defeat flag (boss-area key)
    520420: 31190800,   # defeat flag (boss-area key)
    520430: 31210800,   # defeat flag (boss-area key)
    520440: 31100800,   # defeat flag (boss-area key)
    520450: 31200800,   # defeat flag (boss-area key)
    520460: 31110800,   # defeat flag (boss-area key)
    520470: 31120800,   # defeat flag (boss-area key)
    520480: 31220800,   # defeat flag (boss-area key)
    520490: 31190850,   # defeat flag (boss-area key)
    520600: 32000800,   # defeat flag (boss-area key)
    520610: 32010800,   # defeat flag (boss-area key)
    520620: 32020800,   # defeat flag (boss-area key)
    520630: 32040800,   # defeat flag (boss-area key)
    520640: 34120800,   # defeat flag (boss-area key)
    520650: 32050800,   # defeat flag (boss-area key)
    520660: 32070800,   # defeat flag (boss-area key)
    520670: 32080800,   # defeat flag (boss-area key)
    520680: 32110800,   # defeat flag (boss-area key)
    520700: 40000800,   # defeat flag (boss-area key)
    520710: 40010800,   # defeat flag (boss-area key)
    520750: 41000800,   # defeat flag (boss-area key)
    520760: 41010800,   # defeat flag (boss-area key)
    520770: 41020800,   # defeat flag (boss-area key)
    520810: 43010800,   # defeat flag (boss-area key)
}
