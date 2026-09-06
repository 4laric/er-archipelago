# Diallos's Jarburg Numen's Rune (#1437)

This check is acquisition flag400452, quantity1 of goods2913. It is separate from
ordinary Numen's Rune pickups: equal vanilla items do not imply equal acquisition flags.
M4G pin3900138 places lot104512 at m60_39_44/Jarburg. Committed NpcParam523140220
uses itemLotId_map104510 and itemLotId_enemy=-1. The contiguous map batch104510–104512
ends with this rune under its own flag400452; primary rows use400451. The committed
MSB flag-region table places primary400451 / lot104510 / c0000_9001 in that same tile.

The M4G pin labels its source `enemy`, but104512 is a map-table row, not an enemy-table
row. The accepted placement remains useful while that table label remains contradictory.
Recovery uses the map namespace and questline/missability protection. No exclusive NPC
quest rule is inferred, and required progression cannot be placed here.

AP7774651 is appended after Silver Scarab7774650. Both old/new same-flag rune lot variants
are handled by the existing flag-lot replacement derivation. The specific live route is
NpcParam523140220 -> map batch104510 -> row104512 -> flag400452.

This does not claim the runtime M4G pin now matches: its enemy label may still prevent a
lot-key join. A flag-based bridge may reconcile it, but that has not been smoke-tested.
The original table mismatch remains an explicit follow-up under #1437.
