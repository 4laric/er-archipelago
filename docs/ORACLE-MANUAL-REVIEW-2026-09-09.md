# Oracle review handoff — 2026-09-09

This is a bounded evidence pass, not a claim of full Matt parity. The oracle supplied disagreement flags only; every answer below comes from our placements, game scripts, generated tables or existing project rulings. No oracle area names, prose or graph rules are included.

## What changed

- **5 region rows / 4 flags corrected:** Isolated Merchant's Bell Bearing [2] (f400907) now joins his stock behind the Academy lock. Nascent Butterfly (f1039537040), Unseen Blade / Unseen Form (f1039537050), and Slumbering Egg (f1039537060) move from Mt. Gelmir to Altus on exact placement-volume evidence. Their AP IDs stay unchanged and their sweeps move to real bosses in the corrected region.
- **35 region rows confirmed:** complete available exact-volume coverage, or an explicit existing access/grace-ground ruling. These remain differences in partitioning, not proposed fixes.
- **2 more acquisition flags protected:** Golden Lion Shield (f400600) and Gourmet Scorpion Stew (f400722), following their dialogue callers and loss conditions. This follows the earlier Kris and Heirloom fix in the same PR.

Of the original **211 region rows**, **171 remain open**, grouped below into **74 review batches**. The refreshed live queue has 206 rows, including the 35 confirmed differences. Refresh also retires stale entries from older work; those retirements are not credited as fixes here.

Of the original **65 acquisition flags** reviewed in this pass, **63 remain open**: **17 without a complete generated sweep fallback**, followed by **46 sweep-backed flags**. A sweep-table entry is an alternate-route lead, not proof that the live client always grants it or that its boss prerequisites are satisfied. The filtered missable queue is narrower: 30 AP rows. These populations overlap with region review; do not add their totals as unique bugs.

The separate **26 missing-check flags** still lack an admitted region. Re-running the resolver against exactly those 26 produced zero resolutions: 9 common ESD buckets, 14 ambiguous multi-map candidates, and 3 without placement evidence. All 365 bundled ESD files were indexed. These need new placement evidence or a choice of intended acquisition route, not another blind regeneration.

[Full review ledger with all AP IDs, map placements, script award sites and sweep owners](oracle-review-2026-09-09.tsv). It retains all 211 starting region rows, including resolved ones, all 65 acquisition flags, and all 26 missing flags. The `review` status means unresolved, not proven wrong and not necessarily human-only work.

## Start with these decisions / observations

1. **Euporia route (#1321):** mark the exact checks to include. No contiguous flag band is an acceptable substitute. Preserve the existing Stagefront fragment alternative via Dancing Lion or Enir Ilim access.
2. **Furnace golems:** capture the actual c4900 placement and player play-region bucket for f65420/f65430/f65450/f65460. The bundle lacks that placement family. In particular, f65460's Cerulean report cannot be settled by its current Gravesite pin.
3. **Conflicting drop identity:** f2047407980 is reported both as Logur's Beast Claw and a key-gated pot. Record the exact obtained item, flag and bucket before moving it.
4. **Jagged Peak boundary:** f2048417980 (Black Steel Greathammer) and f2049427700/f2049427720 (Swollen Grapes) lack coordinates. A nearby boss's tile ruling does not locate these pickups; one neighboring tile demonstrably straddles regions.
5. **Shared-flag alternatives:** f400285 and f400309 have several item lots. Test whether either collection route completes all sibling AP checks before deciding the missability or region of the whole flag.
6. **Moving NPCs:** for Nagakiba, Warrior Jar Shard, Moore's equipment and the unplaced NPC rewards, choose whether the AP home follows the earliest supported hand route or an explicit sweep route. A single exact measurement at one NPC stop does not settle all stops.

For a live ground check, return **flag/AP ID, item, approach grace, player play-region bucket, required locks/keys, and whether collection succeeds**. For a route decision, return **flag, accepted alternatives, prerequisite(s), and the permanent-loss trigger**. A screenshot or short clip is useful when elevation or a locked transition is the disputed fact.

## Priority acquisition review: no complete sweep fallback

Existing gates are called out to avoid asking you to re-decide settled work. Script references and alternate lot evidence are in the ledger.

| Flag | Check | What remains to establish |
|---|---|---|
| 60500 | Talisman Pouch | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 65430 | Cerulean-Sapping Cracked Tear | Furnace-golem family lacks c4900 placement evidence in the bundle; needs targeted game-data extraction or live observation, not an invented boss prerequisite. |
| 65450 | Bloodsucking Cracked Tear | Furnace-golem family lacks c4900 placement evidence in the bundle; needs targeted game-data extraction or live observation, not an invented boss prerequisite. |
| 65460 | Glovewort Crystal Tear | Furnace-golem family lacks c4900 placement evidence in the bundle; needs targeted game-data extraction or live observation, not an invented boss prerequisite. |
| 400031 | Lord of Blood's Favor | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 400159 | Discarded Palace Key | Existing questline_check_gates requires Miniature Ranni for the Baleful Shadow reward when item_shuffle is active; do not restore the bypassed mansion quest chain. Check permanent-loss semantics separately. |
| 400220 | Golden Seed | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 400285 | All-Knowing Greaves | Shared flag: map102850 Law of Causality AND map102864 All-Knowing Greaves. A dialogue-only analysis would omit the other collection route; settle the shared-flag acquisition semantics first. |
| 400309 | Blackguard's Bell Bearing | Shared flag spans the Death Lightning and Blackguard item lots. Review every lot route before changing the whole flag; the displayed Caelid region is also unresolved. |
| 400325 | Somber Ancient Dragon Smithing Stone | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 400380 | Sewer-Gaol Key | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 400490 | Royal Remains Greaves | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 400611 | New Cross Map | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 400661 | Beloved Stardust | Existing legacy_key_gates binds the Hole-Laden Necklace; Ymir reward dispatch and both bell ObjActs already traced there. Remaining question is permanent loss/alternate access, not a missing blanket necklace gate. |
| 11107900 | Clinging Bone | At least one AP sibling has no generated sweep fallback; prioritize complete hand-route and permanent-loss review. |
| 2050407000 | Ring the Finger Ruins of Dheo bell | Existing legacy_key_gates binds the Hole-Laden Necklace; Ymir reward dispatch and both bell ObjActs already traced there. Remaining question is permanent loss/alternate access, not a missing blanket necklace gate. |
| 2053467600 | Ring the Finger Ruins of Rhia bell | Existing legacy_key_gates binds the Hole-Laden Necklace; Ymir reward dispatch and both bell ObjActs already traced there. Remaining question is permanent loss/alternate access, not a missing blanket necklace gate. |

## Ground and region batches

Each row is a navigation batch, **not permission to move the entire tile**. Check each listed flag at its actual elevation/access path. Multi-item flags retain every AP sibling in the ledger. Rows with no physical map need a route/placement witness first.

| Batch / map | Current region(s) | Exact flags to review |
|---|---|---|
| ground-m11_00 | Leyndell | 11007195 |
| ground-m14_00 | Raya Lucaria Academy | 14007920 |
| ground-m35_00 | Leyndell | 35007030 |
| ground-m60_35_46 | Raya Lucaria Academy | 1035467700 |
| ground-m60_36_51 | Liurnia | 66730, 67840, 1036517000, 1036517700 |
| ground-m60_36_52 | Mt. Gelmir | 66740, 1036527010, 1036527020, 1036527030, 1036527050 |
| ground-m60_37_52 | Mt. Gelmir | 1037527020, 1037527030, 1037527040, 1037527050, 1037527060, 1037527080, 1037527090, 1037527100 |
| ground-m60_38_54 | Mt. Gelmir | 1038547000, 1038547010, 1038547020, 1038547030, 1038547050, 1038547070, 1038547080, 1038547090, 1038547100, 1038547110, 1038547700 |
| ground-m60_39_53 | Mt. Gelmir | 1039537000, 1039537010, 1039537020, 1039537030, 1039537070, 1039537080, 1039537700 |
| ground-m60_43_34 | Weeping | 1043347000, 1043347040, 1043347050 |
| ground-m60_44_34 | Weeping | 1044347000, 1044347010, 1044347040, 1044347050, 1044347060, 1044347070, 1044347080 |
| ground-m60_46_39 | Caelid | 540118, 1046397000, 1046397010, 1046397020 |
| ground-m60_46_40 | Caelid | 67650, 1046407000, 1046407010, 1046407020, 1046407040, 1046407060, 1046407700 |
| ground-m60_50_56 | Consecrated Snowfield | 1050567300, 1050567800 |
| ground-m60_51_54 | Mountaintops of the Giants | 540512 |
| ground-m60_51_55 | Consecrated Snowfield | 1051557300 |
| ground-m61_44_47 | Rauh Base | 2044477050 |
| ground-m61_45_46 | Rauh Base | 2045467020, 2045467040, 2045467995 |
| ground-m61_45_47 | Rauh Base | 2045477010, 2045477040, 2045477050, 2045477060, 2045477070, 2045477400 |
| ground-m61_46_46 | Ancient Ruins | 2046467020 |
| ground-m61_47_40 | Cerulean | 2047407010, 2047407020, 2047407980 |
| ground-m61_47_44 | Gravesite | 68790, 530865, 2047447730, 2047447820, 2047457180 |
| ground-m61_47_46 | Scadu Altus | 2047467010, 2047467030 |
| ground-m61_47_47 | Ancient Ruins | 2047477030, 2047477040, 2047477050, 2047477070, 2047477900, 2047477995 |
| ground-m61_48_41 | Jagged Peak | 2048417980 |
| ground-m61_48_44 | Ensis | 540902, 540920, 540922, 2048447010, 2048447020, 2048447040, 2048447080, 2048447500 |
| ground-m61_49_38 | Jagged Peak | 68850 |
| ground-m61_49_42 | Jagged Peak | 2049427700, 2049427720 |
| ground-m61_50_40 | Shadow Keep | 2050407000 |
| ground-m61_50_41 | Scadu Altus | 68670, 2050417010, 2050417700 |
| ground-m61_50_46 | Shadow Keep | 2050467500, 2050467510 |
| ground-m61_51_41 | Scadu Altus | 68720, 2051417000, 2051417700, 2051417710 |
| ground-m61_51_47 | Scadu Altus | 2051477010, 2051477020, 2051477030 |
| ground-m61_52_42 | Scadu Altus | 2052427500 |
| route-10007452 | Roundtable Hold | 10007452 |
| route-1039537750 | Mt. Gelmir | 1039537750 |
| route-1043527750 | Altus | 1043527750 |
| route-1043527760 | Altus | 1043527760 |
| route-2045477500 | Rauh Base | 2045477500 |
| route-2045477510 | Rauh Base | 2045477510 |
| route-2045477520 | Rauh Base | 2045477520 |
| route-2045477530 | Rauh Base | 2045477530 |
| route-2045477540 | Rauh Base | 2045477540 |
| route-2045477550 | Rauh Base | 2045477550 |
| route-2045477560 | Rauh Base | 2045477560 |
| route-2045477570 | Rauh Base | 2045477570 |
| route-2045477580 | Rauh Base | 2045477580 |
| route-2045477590 | Rauh Base | 2045477590 |
| route-2045477600 | Rauh Base | 2045477600 |
| route-2046477970 | Ancient Ruins | 2046477970 |
| route-2047477950 | Ancient Ruins | 2047477950 |
| route-400050 | Limgrave | 400050 |
| route-400070 | Altus | 400070 |
| route-400090 | Mt. Gelmir | 400090 |
| route-400103 | Raya Lucaria Academy | 400103 |
| route-400106 | Raya Lucaria Academy | 400106 |
| route-400163 | Altus | 400163 |
| route-400175 | Farum Azula | 400175 |
| route-400260 | Caelid | 400260 |
| route-400281 | Leyndell | 400281 |
| route-400309 | Caelid | 400309 |
| route-400320 | Haligtree | 400320 |
| route-400357 | Leyndell | 400357 |
| route-400391 | Roundtable Hold | 400391 |
| route-400400 | Caelid | 400400 |
| route-400600 | Enir Ilim | 400600 |
| route-400612 | Shadow Keep | 400612 |
| route-400645 | Enir Ilim | 400645 |
| route-400722 | Gravesite | 400722 |
| route-520800 | Roundtable Hold | 520800 |
| route-530950 | Roundtable Hold | 530950 |
| route-580100 | Belurat | 580100 |
| route-65420 | Scadu Altus | 65420 |
| route-65460 | Gravesite | 65460 |

## Lower-priority acquisition review: sweep routes exist

These are still open. Verify the intended sweep fallback and its runtime availability before declaring a vanilla missable route harmless. The ledger lists actual trigger IDs for every AP sibling; the displayed location wording is not used as evidence of coverage.

| Flag | Check | Current region(s) |
|---|---|---|
| 60430 | Memory Stone | Liurnia |
| 400036 | Festering Bloody Finger | Mohgwyn |
| 400050 | Grace Mimic | Limgrave |
| 400051 | Gostoc's Bell Bearing | Stormveil |
| 400073 | Letter from Volcano Manor | Mt. Gelmir |
| 400074 | Letter from Volcano Manor | Mt. Gelmir |
| 400075 | Red Letter | Mt. Gelmir |
| 400090 | Volcano Manor Invitation | Mt. Gelmir |
| 400148 | Preceptor's Trousers | Liurnia |
| 400149 | Pidia's Bell Bearing | Liurnia |
| 400163 | Nagakiba with Ash of War: Piercing Fang | Altus |
| 400164 | Ronin's Greaves | Mountaintops of the Giants |
| 400175 | Warrior Jar Shard | Farum Azula |
| 400180 | Letter to Patches | Mt. Gelmir |
| 400209 | Miriel's Bell Bearing | Liurnia |
| 400241 | Iji's Mirrorhelm | Liurnia |
| 400290 | Letter to Bernahl | Mt. Gelmir |
| 400291 | [Sorcery] Gelmir's Fury | Mt. Gelmir |
| 400292 | Blasphemous Claw | Farum Azula |
| 400401 | Eccentric's Breeches | Raya Lucaria Academy |
| 400412 | Blue Silver Mail Skirt | Liurnia |
| 400431 | Old Sorcerer's Legwraps | Caelid |
| 400441 | Azur's Manchettes | Mt. Gelmir |
| 400510 | Great Stars | Altus |
| 400594 | Ash of War: Swift Slash | Scadu Altus |
| 400620 | Letter for Freyja | Shadow Keep |
| 400690 | Fire Knight Queelign | Scadu Altus |
| 400712 | Igon's Greatbow with Ash of War: Igon's Drake Hunt | Jagged Peak |
| 400720 | Scorpion Stew | Belurat |
| 400721 | [Sorcery] Watchful Spirit | Belurat |
| 400723 | Gourmet Scorpion Stew | Belurat |
| 12017999 | Alabaster Lord's Sword | Ainsel River |
| 12057950 | War Surgeon Trousers | Mohgwyn |
| 16007950 | [Incantation] Aspects of the Crucible: Breath | Mt. Gelmir |
| 21007320 | Great Grave Glovewort | Scadu Altus |
| 35007993 | Somber Smithing Stone [7] | Leyndell |
| 39207500 | Bull-Goat Greaves | Liurnia |
| 1034517900 | Snow Witch Skirt | Liurnia |
| 1035467700 | Ash of War: Raptor of the Mists | Raya Lucaria Academy |
| 1039487100 | Gavel of Haima | Liurnia |
| 1039537700 | Black-Key Bolt | Mt. Gelmir |
| 1042397700 | Hammer Talisman | Limgrave |
| 1048387500 | Sacramental Bud | Caelid |
| 2046397060 | Furnace Visage | Cerulean |
| 2050467500 | Furnace Visage | Shadow Keep |
| 2051457700 | Furnace Visage | Scadu Altus |

## Missing checks: acquisition site needed

These names are the project's legacy region-map labels, not freshly validated item identities. They are not current AP checks and have no current AP ID. Supply the exact flag/lot and a repeatable site before restoring one.

| Flag | Project label | Available award script references |
|---|---|---|
| 60270 | Bloody Finger | talk/m60_00_00_00-only/t301006000.py:t301006000_x59:lot100340 |
| 400030 | Festering Bloody Finger | talk/m60_00_00_00-only/t301006000.py:t301006000_x53:lot100300 |
| 400060 | Sacrificial Twig | talk/m60_00_00_00-only/t311006000.py:t311006000_x3:lot100600; talk/m60_00_00_00-only/t311006000.py:t311006000_x44:lot100600 |
| 400069 | [Sorcery] Rancorcall | No award-site row in the condition table; see flag_lots and resolver. |
| 400100 | Sellen's Primal Glintstone | talk/m60_00_00_00-only/t316106000.py:t316106000_x3:lot101000; talk/m60_00_00_00-only/t316106000.py:t316106000_x45:lot101000 |
| 400102 | Sellian Sealbreaker | talk/m60_00_00_00-only/t316006000.py:t316006000_x55:lot101020 |
| 400140 | Seluvis's Potion | talk/m60_00_00_00-only/t307006000.py:t307006000_x11:lot101400; talk/m60_00_00_00-only/t307006000.py:t307006000_x8:lot101400 |
| 400141 | Magic Scorpion Charm | talk/m60_00_00_00-only/t307006000.py:t307006000_x13:lot101410 |
| 400143 | Seluvis's Introduction | talk/m60_00_00_00-only/t307006000.py:t307006000_x19:lot101430 |
| 400145 | Amber Draught | talk/m60_00_00_00-only/t307006000.py:t307006000_x5:lot101450 |
| 400170 | Exalted Flesh | talk/m13_00_00_00-only/t220001300.py:t220001300_x45:lot101700; talk/m32_07_00_00-only/t220003207.py:t220003207_x45:lot101700; talk/m60_00_00_00-only/t220006000.py:t220006000_x45:lot101700; talk/m60_00_00_00-only/t220016000.py:t220016000_x42:lot101700; talk/m60_00_00_00-only/t220026000.py:t220026000_x45:lot101700 |
| 400171 | Exalted Flesh | talk/m13_00_00_00-only/t220001300.py:t220001300_x69:lot101710; talk/m32_07_00_00-only/t220003207.py:t220003207_x69:lot101710; talk/m60_00_00_00-only/t220006000.py:t220006000_x69:lot101710; talk/m60_00_00_00-only/t220016000.py:t220016000_x66:lot101710; talk/m60_00_00_00-only/t220026000.py:t220026000_x69:lot101710 |
| 400172 | Jar | talk/m13_00_00_00-only/t220001300.py:t220001300_x53:lot101720; talk/m32_07_00_00-only/t220003207.py:t220003207_x53:lot101720; talk/m60_00_00_00-only/t220006000.py:t220006000_x53:lot101720; talk/m60_00_00_00-only/t220016000.py:t220016000_x50:lot101720; talk/m60_00_00_00-only/t220026000.py:t220026000_x53:lot101720; talk/m60_00_00_00-only/t220036000.py:t220036000_x3:lot101720; talk/m60_00_00_00-only/t220036000.py:t220036000_x43:lot101720 |
| 400181 | Dancer's Castanets | talk/m16_00_00_00-only/t309001600.py:t309001600_x11:lot101810; talk/m31_00_00_00-only/t309003100.py:t309003100_x11:lot101810; talk/m60_00_00_00-only/t309006000.py:t309006000_x11:lot101810 |
| 400182 | Magma Whip Candlestick | talk/m16_00_00_00-only/t309001600.py:t309001600_x27:lot101820; talk/m31_00_00_00-only/t309003100.py:t309003100_x27:lot101820; talk/m60_00_00_00-only/t309006000.py:t309006000_x27:lot101820 |
| 400189 | Patches' Bell Bearing | No award-site row in the condition table; see flag_lots and resolver. |
| 400271 | Mushroom | talk/m11_00_00_00-only/t223001100.py:t223001100_x14:lot102710; talk/m11_00_00_00-only/t223001100.py:t223001100_x49:lot102710; talk/m11_05_00_00-only/t223001105.py:t223001105_x14:lot102710; talk/m11_05_00_00-only/t223001105.py:t223001105_x49:lot102710; talk/m14_00_00_00-only/t223001400.py:t223001400_x38:lot102710; talk/m14_00_00_00-only/t223001400.py:t223001400_x5:lot102710; talk/m31_15_00_00-only/t223003115.py:t223003115_x14:lot102710; talk/m31_15_00_00-only/t223003115.py:t223003115_x49:lot102710; talk/m60_00_00_00-only/t223006000.py:t223006000_x14:lot102710; talk/m60_00_00_00-only/t223006000.py:t223006000_x49:lot102710 |
| 400293 | Devourer's Scepter | No award-site row in the condition table; see flag_lots and resolver. |
| 400294 | Beast Champion Helm | No award-site row in the condition table; see flag_lots and resolver. |
| 400331 | Weathered Dagger | talk/m11_10_00_00-only/t322001110.py:t322001110_x17:lot103310; talk/m12_03_00_00-only/t322001203.py:t322001203_x17:lot103310; talk/m12_03_00_00-only/t322011203.py:t322011203_x17:lot103310 |
| 400332 | Sacrificial Twig | talk/m11_10_00_00-only/t322001110.py:t322001110_x19:lot103320; talk/m12_03_00_00-only/t322001203.py:t322001203_x19:lot103320; talk/m12_03_00_00-only/t322011203.py:t322011203_x19:lot103320 |
| 400334 | Knifeprint Clue | talk/m11_10_00_00-only/t322001110.py:t322001110_x49:lot103340; talk/m12_03_00_00-only/t322001203.py:t322001203_x49:lot103340; talk/m12_03_00_00-only/t322011203.py:t322011203_x49:lot103340 |
| 400420 | Arsenal Charm | talk/m10_00_00_00-only/t334001000.py:t334001000_x50:lot104200; talk/m11_10_00_00-only/t334001110.py:t334001110_x3:lot104200; talk/m11_10_00_00-only/t334001110.py:t334001110_x45:lot104200; talk/m60_00_00_00-only/t334006000.py:t334006000_x48:lot104200 |
| 400421 | Stormhawk Axe | No award-site row in the condition table; see flag_lots and resolver. |
| 400451 | Hoslow's Petal Whip | No award-site row in the condition table; see flag_lots and resolver. |
| 530935 | Blessing of Marika | m61_50_47_00.emevd.dcx.js:2050472820:lot30935 |

## Evidence for the new fixes

- f400907: `msb_flag_region.tsv` has one enemy placement on m60_35_45, lot119030; `item_play_regions.tsv` measures volume1400011 / bucket14000. Existing merchant ruling in `gen_data.FLAG_REGION_OVERRIDE` already places all 16 stock checks behind the Academy key pocket. The death drop was the omitted sibling. It loses Smarag's Liurnia sweep and has no eligible Academy field-boss replacement; collect it from the merchant behind the corrected door. No other check loses sweep coverage.
- f1039537040/50/60: one ground placement each on m60_39_53; volumes6300001 (boundary override) and6300040 (tower) resolve to Altus bucket63000 in `region_groups.PLAY_REGION_GROUPS`. The old unspawned-boss regression pinned an obsolete region; it now checks survival and real same-region sweep ownership after correction.
- f400600: `t417002101_x45` and `t417006100_x45` call x52 only after21019371. x51 requires and consumes Goods2008015 (Letter for Freyja), setting21019371/4891. x52 awards map lot106000; x9/x23 blocks dead state4423. `flag_lots.tsv` has no other lot for this flag. Region remains open: proving a quest requirement does not establish the correct home region.
- f400722: `t402002000_x39` calls x48 only with20009286/20009290; x48 awards map107220 before refusal20009289. `m20_00` event20000702, using its constructor arguments, sets refusal when Messmer21010800 is dead without20009286. x23 guards dead state4483. This is distinct from the separate stew lots. Region remains open.

Generated from the isolated audit checkout. This handoff is a dated snapshot; the existing oracle TSV queues remain the supported refreshable review records.
