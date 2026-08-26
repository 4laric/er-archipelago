# Region second opinion -- run report

Sources: Eldenpedia (CC BY-SA 4.0), Fandom Elden Ring Wiki (CC BY-SA 3.0) as
fallback, ERDB (MIT) probed and unused. Fextralife deliberately not consulted.
No wiki prose is reproduced: only region names, ids, page titles and verdicts.

## Counts

| verdict | rows |
| --- | ---: |
| AGREE | 51 |
| DISAGREE | 16 |
| AMBIGUOUS | 3 |
| AMBIGUOUS-GENERIC | 209 |
| NO-DATA | 26 |
| **total** | **305** |

`AMBIGUOUS-GENERIC` is refused without a network call: the item has many vanilla
copies, so no item page can name THIS placement. `NO-DATA` is weak evidence -- it
means the page was missing or named no place we recognise, not that we are right.

## DISAGREE

| flag | ap_id | tile | our region | external | item | source / page | msb vote |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1033457100 | 7774376 | m60_33_45 | Liurnia | A,i,n,s,e,l, ,R,i,v,e,r | Dragonscale Blade | eldenpedia / Dragonscale Blade | NO-COORDS |
| 1038527000 | 7772827 | m60_38_52 | Altus | M,t,., ,G,e,l,m,i,r | Pearldrake Talisman +1 | eldenpedia / Pearldrake Talisman +1 | Altus @ 215.0m, top-3 split |
| 1040507000 | 7772899 | m60_40_50 | Altus | C,a,e,l,i,d | Gravity Stone Fan | eldenpedia / Gravity Stone Fan | Altus @ 288.2m |
| 1041517020 | 7772928 | m60_41_51 | Altus | L,i,m,g,r,a,v,e | Silver-Pickled Fowl Foot | eldenpedia / Silver-Pickled Fowl Foot | Altus @ 255.4m |
| 1041517030 | 7772929 | m60_41_51 | Altus | C,a,e,l,i,d | Gravity Stone Chunk | eldenpedia / Gravity Stone Chunk | Altus @ 314.2m |
| 1042327100 | 7772940 | m60_42_32 | Weeping | L,i,u,r,n,i,a | Composite Bow | eldenpedia / Composite Bow | NO-COORDS |
| 1042397500 | 7772981 | m60_42_39 | Limgrave | M,t,., ,G,e,l,m,i,r | Scaled Helm | eldenpedia / Scaled Helm | NO-COORDS |
| 1042397500 | 7900253 | m60_42_39 | Limgrave | M,t,., ,G,e,l,m,i,r | Scaled Armor | eldenpedia / Scaled Armor | NO-COORDS |
| 1042397500 | 7900254 | m60_42_39 | Limgrave | M,t,., ,G,e,l,m,i,r | Scaled Gauntlets | eldenpedia / Scaled Gauntlets | NO-COORDS |
| 1042397500 | 7900255 | m60_42_39 | Limgrave | M,t,., ,G,e,l,m,i,r | Scaled Greaves | eldenpedia / Scaled Greaves | NO-COORDS |
| 1042547020 | 7774599 | m60_42_54 | Altus | M,t,., ,G,e,l,m,i,r,,,L,e,y,n,d,e,l,l | Holyproof Dried Liver | eldenpedia / Holyproof Dried Liver | Altus @ 144.5m |
| 1047567700 | 7773141 | m60_47_56 | Mountaintops of the Giants | C,o,n,s,e,c,r,a,t,e,d, ,S,n,o,w,f,i,e,l,d,,,M,o,h,g,w,y,n | Sanguine Noble Hood | fandom / Sanguine Noble Hood | NO-COORDS |
| 1047567700 | 7900258 | m60_47_56 | Mountaintops of the Giants | C,o,n,s,e,c,r,a,t,e,d, ,S,n,o,w,f,i,e,l,d | Sanguine Noble Robe | eldenpedia / Sanguine Noble Robe | NO-COORDS |
| 1048547990 | 7774712 | m60_48_54 | Mountaintops of the Giants | C,o,n,s,e,c,r,a,t,e,d, ,S,n,o,w,f,i,e,l,d | Rotten Battle Hammer | eldenpedia / Rotten Battle Hammer | Consecrated Snowfield @ 332.2m, top-3 split (SUSPECT-ANCHOR) |
| 1048557900 | 7773168 | m60_48_55 | Mountaintops of the Giants | C,o,n,s,e,c,r,a,t,e,d, ,S,n,o,w,f,i,e,l,d | Flowing Curved Sword | eldenpedia / Flowing Curved Sword | Consecrated Snowfield @ 338.9m, top-3 split (COARSE-LOD;SUSPECT-ANCHOR) |
| 1051417010 | 7774779 | m60_51_41 | Caelid | F,a,r,u,m, ,A,z,u,l,a | Cinquedea | eldenpedia / Cinquedea | Caelid @ 194.0m (CROSS-TILE-MSB;SUSPECT-ANCHOR) |

## MSB nearest-grace vote

A second and SEPARATE opinion, computed offline from our own committed MSB
coordinates (`tools/msb_region_vote.py`): fold the check into the overworld frame,
vote the region of the nearest region-attributed Site of Grace.

**92.9% on a 2169-check control set (--calibrate, 2026-08-26) -- roughly one row in fourteen is WRONG, so this is a RANKING signal for hand-adjudication, never an adjudicator. It does NOT describe a PLAYAREA-CONFIRMED row: those are RULINGS from the PlayArea point-in-volume test (docs/PLAYAREA-ITEM-SCAN.md), they REPLACED the vote, and the 518 of them in the control population are excluded from the number above rather than flattering it.**

It is NOT independent of the nearest-neighbour hop that produced these regions, so a
vote that AGREES with us corroborates nothing; a vote that disagrees is a QUESTION.

| | rows |
| --- | ---: |
| vote cast | 268 |
| vote backs our region | 246 |
| vote disagrees with our region | 22 |
| of those, on a SUSPECT-ANCHOR grace | 19 |
| no vote (no coords / no anchor) | 37 |

### Votes against our region

| flag | tile | our region | wiki | msb vote | anchor grace | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1042347000 | m60_42_34 | Weeping | -- | Limgrave @ 240.6m, top-3 split | 76113 Seaside Ruins | AMBIGUOUS-GENERIC |
| 1042347030 | m60_42_34 | Weeping | Weeping | Limgrave @ 223.9m | 76113 Seaside Ruins | AGREE |
| 1046577300 | m60_46_57 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 533.7m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1046577800 | m60_46_57 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 555.8m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1047567310 | m60_47_56 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 254.9m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1047567320 | m60_47_56 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 363.2m, top-3 split (COARSE-LOD;SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1047567330 | m60_47_56 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 304.3m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1047577300 | m60_47_57 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 664.6m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1047577310 | m60_47_57 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 682.3m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048547800 | m60_48_54 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 337.4m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048547810 | m60_48_54 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 329.8m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048547820 | m60_48_54 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 335.2m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048547830 | m60_48_54 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 342.7m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048547840 | m60_48_54 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 331.5m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048547990 | m60_48_54 | Mountaintops of the Giants | Consecrated Snowfield | Consecrated Snowfield @ 332.2m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | DISAGREE |
| 1048547990 | m60_48_54 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 332.2m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | NO-DATA |
| 1048557300 | m60_48_55 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 163.1m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1048557600 | m60_48_55 | Mountaintops of the Giants | Consecrated Snowfield,Mountaintops of the Giants | Consecrated Snowfield @ 156.1m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AGREE |
| 1048557900 | m60_48_55 | Mountaintops of the Giants | Consecrated Snowfield | Consecrated Snowfield @ 338.9m, top-3 split (COARSE-LOD;SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | DISAGREE |
| 1048587300 | m60_48_58 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 809.8m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1049567350 | m60_49_56 | Mountaintops of the Giants | -- | Consecrated Snowfield @ 510.5m, top-3 split (SUSPECT-ANCHOR) | 73211 Yelough Anix Tunnel | AMBIGUOUS-GENERIC |
| 1050567600 | m60_50_56 | Mountaintops of the Giants | -- | Consecrated Snowfield @ m (PLAYAREA-CONFIRMED) |  | AMBIGUOUS-GENERIC |

