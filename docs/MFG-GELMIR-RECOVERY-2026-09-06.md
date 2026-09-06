# Gelmir's Fury: separate Bernahl rewards (#1437)

Accepted vanilla M4G pin3100003 locates map lot102926 at m13_00_00 (Farum Azula).
The committed vanilla param row awards goods4810, quantity1, probability1000/1000,
acquisition flag400295. The extracted event m13_00_00_00.emevd.dcx.js:94 invokes
90005792 for Bernahl entity13000710 with reward block102920. That common function
waits for the hostile NPC's death and awards the block, including row102926.

The earlier Volcano Manor dialogue reward is a different row102910, quantity1,
acquisition flag400291. The extracted t326001600.py:x42 awards it after dialogue
condition7605. Equal item names never established that these two flags were duplicates.

This recovery appends AP7774649 after the seven Somber recoveries. Both reward rows
are replaced independently, and the Farum check remains questline/missable to prevent
progression placement. No inferred NPC state or quest condition is promoted to a
proven access rule. Killing Bernahl earlier and invasion availability still need
complete access modeling; the retained progression bar handles that uncertainty.

The source is the accepted private vanilla transfer20260905 used by the M4G audit;
flag_lots.tsv independently preserves row102926/flag400295. No live game files were read.
