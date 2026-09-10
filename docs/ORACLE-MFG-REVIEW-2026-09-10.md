# MFG and web remainder review — 2026-09-10

**12 more checks corrected; 159 region rows remain open across 68 batches.** This continues [the September 9 review](ORACLE-MANUAL-REVIEW-2026-09-09.md). The [updated ledger](oracle-review-2026-09-10.tsv) retains every original row and its disposition.

The accepted vanilla MFG bundle supplied 7,031 native pins; all 16 input hashes were verified. Exact lot table and row identify each check. Coordinates were checked against independent route descriptions and our existing ground evidence; these are not new PlayArea volume measurements. [Recorded pins, identities and sources](../greenfield/evidence/mfg_oracle_regions.json).

| Flag | Corrected region | Evidence |
|---|---|---|
| 65420 | Ancient Ruins | Route runs from Rauh Ancient Ruins East across the upper bridge to the golem and West grace; native pin y553.347. Upper bridge item2045467050 measures bucket69410. [Route source](https://eip.gg/elden-ring/guides/ancient-ruins-of-rauh/) |
| 520800 | Gravesite | Native boss pin is m43_00. Initialized event43002800 sets9280; common slot80 event1200 awards20800. The alternate m34_10 setter is in uninitialized cut event34102800. Rivermouth bucket43000 belongs to Gravesite. [Route source](https://eip.gg/elden-ring/guides/rivermouth-cave-dungeon/) |
| 540118 | Limgrave | Native scarab pin is104.5m from Third Church of Marika, only13.5m height difference; the walkthrough locates this scarab north of that church in Limgrave, below the Caelid cliff. [Route source](https://www.powerpyx.com/elden-ring-all-ashes-of-war-locations/) |
| 2048417980 | Gravesite | Native enemy reward pin sits2.8m from Scadutree Fragment2048417700 at0.2m height difference; fragment exact volume is68000. Walkthrough reaches the knight at Church of Consolation from Gravesite Plain. [Route source](https://eip.gg/elden-ring/guides/gravesite-plain/) |
| 2049427700 | Abyssal | Native Aging Untouchable reward pin y-560.407,193.8m from Divided Falls with5.4m height difference. Divided Falls measures68600; map initializer binds character2049420200 to lot2049420700 through90005301. [Route source](https://vulkk.com/2024/08/14/shadow-of-the-erdtree-abyssal-woods-and-midras-manse-guide-all-unique-item-locations/) |
| 2049427720 | Abyssal | Native Aging Untouchable reward pin y-562.084,146.0m from Divided Falls with3.7m height difference. Map initializer binds character2049420202 to lot2049420720 through90005301. [Route source](https://vulkk.com/2024/08/14/shadow-of-the-erdtree-abyssal-woods-and-midras-manse-guide-all-unique-item-locations/) |
| 2050417700 | Abyssal | Native Aging Untouchable reward pin y-562.198,213.6m from Abyssal Woods grace. Map initializer binds character2050410200 to lot2050410700 through90005301; walkthrough places these nonrespawning enemies in the woods. [Route source](https://vulkk.com/2024/08/14/shadow-of-the-erdtree-abyssal-woods-and-midras-manse-guide-all-unique-item-locations/) |
| 2051417700 | Abyssal | Native talisman pin y-552.239 near Woodland Trail/Abyssal Woods. Map initializer binds character2051410200 to lot2051410700 through90005301. Guide identifies the talisman-bearing Aging Untouchable. [Route source](https://vulkk.com/2024/08/14/shadow-of-the-erdtree-abyssal-woods-and-midras-manse-guide-all-unique-item-locations/) |
| 2051417710 | Abyssal | Native Aging Untouchable reward pin y-551.656,255m from Abyssal Woods grace at0.2m height difference. Map initializer binds character2051410201 to lot2051410710 through90005301. [Route source](https://vulkk.com/2024/08/14/shadow-of-the-erdtree-abyssal-woods-and-midras-manse-guide-all-unique-item-locations/) |
| 2052427500 | Abyssal | Native Madding Hand pin y-551.814,130.3m from Woodland Trail at8.1m height difference. Map initializer binds character2052420300 to lot2052420500 through90005301. Walkthrough approaches from Woodland Trail. [Route source](https://roundtablehold.net/checklists/dlc_walkthrough.html) |
| 2050467500 | Scadu Altus | Ruins of Unte reward pin, same coordinates as Bloodsucking tear. Nearby item2050467730 (14.4m,1.4m height difference) and Castle Watering Hole grace measure69030. Walkthrough places both golems beside that grace. [Route source](https://eip.gg/elden-ring/guides/scadu-altus/) |
| 2050467510 | Scadu Altus | Other Unte golem pin near Castle Watering Hole, at0.1m height difference. Adjacent items2049467550/60 measure69030. Shared tile with elevated Hinterland does not put this river-floor reward in Shadow Keep. [Route source](https://eip.gg/elden-ring/guides/scadu-altus/) |

## Effect and validation

All 4,931 AP IDs and their flag bindings stay unchanged. Exactly 12 checks change region. Ten cease disagreeing with the oracle; Crimson-Sapping and Bloodfiend Hexer retain partition/membership differences, now recorded as confirmed from our evidence. The refreshed queue has 196 rows: 159 open and 37 confirmed. No oracle area labels, prose or rules were copied.

Sweep membership remains 4,114 entries: 32 old (trigger, flag) pairs are replaced by 32 new pairs. Ten corrected checks change owners, including all six Abyssal rewards moving to Midra. The remaining 22 reassignments stay within Shadow Keep as its allocation changes. No flag gains or loses sweep coverage. Crimson-Sapping and Bloodfiend Hexer remain unswept.

The executable witnesses check exact native lot identity, every sibling region, sweep containment, and reachability with the correct region lock absent versus present while all other requirements are held. Regeneration ran from gen_inputs.db after an unchanged-tree baseline produced no content diff. The focused regression suite and all 88 fill generations passed. Live collection has not been tested.

## Remaining decisions and evidence gaps

- **63 acquisition flags remain open**, including 17 without complete generated sweep fallback and 46 sweep-backed. Region corrections do not establish permanent-loss or quest prerequisites. The older handoff still explains these route questions; the updated ledger is the current row list.
- **26 missing-check flags remain unplaced.** MFG adds exact Farum Azula placement leads for f400293/f400294 (Bernahl lots 102921–102925), but one invasion location does not settle their alternate NPC-death routes. None were restored speculatively.
- **Crimson Hood f10007452:** native Stormveil placement and public quest guides conflict with the existing live Roundtable ruling. The Roundtable script flips collection flags; that alone is not a physical award-site witness. Keep this for targeted live confirmation.
- **Beast Claw f2047407980:** the web identifies Logur, but this exact flag still lacks an admitted native placement and prior reports conflict on identity. Confirm the flag and obtained item together.
- **Furnace tears:** f65420 is resolved here. f65450 has a native Ruins of Unte placement lead, but its awakening/material requirements remain separate. f65430/f65460 still need exact placement identity evidence before changing their regional homes; the general golem-placement gap is no longer a blanket claim.
- **Ensis, Rauh Base and other vertical boundaries:** a matching coordinate or nearby grace alone does not settle a locked approach. MFG supplied 22 previously absent positions across the old remainder, but those are evidence leads, not 22 automatic verdicts.

For manual review, provide flag/AP ID, obtained item, approach grace, player play-region bucket, required locks/keys and whether collection succeeds. For quest alternatives, identify accepted routes and the permanent-loss trigger.
