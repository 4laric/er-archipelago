# NPC reward recovery (#1437)

M4G placement is accepted corroboration. Item-name equality is not evidence that two
award flags are duplicates: an alternate award path can independently grant the same item.

## Implemented: Eleonora's Poleblade

The existing AP location 7774254 now reads acquisition flag 400162 and rewrites map
lot 101621 slot 1. The old ground-lot copy 1039520700 / flag 1039527700 is no longer
a check. No other AP id or flag changed. This requires a new seed; changing the world
cannot repair locationFlags/checkLots already baked into an older seed.

Evidence: vanilla M4G pin 2400148 binds lot 101621 to m60_39_52. Committed flag_lots.tsv
maps that exact lot to 400162 and weapon 10050000. The extracted committed gen_inputs.db
contains m60_39_52_00.emevd.dcx.js:17, whose 90005792 invocation awards block 101620;
common_func's 90005792 waits for the hostile NPC's death and awards that block.
The report independently identifies the old ground copy as unused. The regional
label is Altus and the descriptor names Second Church of Marika. Existing conservative
questline/missability protection remains; this change does not claim full quest logic.

## Remaining families

- Devourer's Scepter 400293: M4G 2400040 locates lot 102921 in Farum Azula.
  flag_lots also lists 112901, and Bernahl has earlier Limgrave/Mt. Gelmir sources.
  One Farum pin cannot justify restricting the shared check to Farum.
- Beast Champion set 400294: M4G 2500033–2500036 locates four lots 102922–102925 in
  Farum. flag_lots also has 102930–102933 and 112902–112905; same multisite problem.
- Gelmir's Fury 400295: M4G 3100003 identifies Farum lot 102926. The same event
  m13_00_00_00:94 awards block 102920 after Bernahl's invasion. Existing 400291 is
  the separate Mt. Gelmir reward: calling it a duplicate solely by item name is
  insufficient. Suitable next recovery with missability protection and an appended ID.
- Dancer's Castanets 400181: lots 101810/111815 share a flag; extracted Patches talk
  scripts in m16_00, m31_00 and overworld buckets reference 101810. Resolve the actual
  quest branch and all sites before assigning a unique region.
- Numen's Rune 400452: lots 104502/104512 share the flag. Existing ordinary rune
  pickups do not make this reward a duplicate. Its NPC acquisition route remains
  unresolved in this track.

The accepted M4G input is the private vanilla transfer 20260905 recorded by the
placement audit. No live installation files were read.
