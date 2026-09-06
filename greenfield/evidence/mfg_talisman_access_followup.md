# Talisman access follow-up (#1437)

Reviewed 2026-09-06 against the extracted, committed gen_inputs.db event corpus.
Neither talisman is restored by the Briars source correction.

## Graven-Mass Talisman (1050567820)

The physical seal is an enemy-combat predicate, not a direct inventory check.
`event/m60_50_56_00.emevd.dcx.js` initializes event **1050562250** with arguments
`1050560250, 1050566250, 1050560250, 1050560251, 35000, 17170, 17171`.
Its three alternative branches each require one of those character entities to
have **both** effects 17170 and 17171 and `HPRatio <= 0`. Only then does it set
seal flag 1050560250 and disable seal asset 1050566250.

The player's Fanged Imp Ashes proposal is a useful route to model, but possession
alone is not this game's condition. Before restoring, trace how these effects
are applied and validate summoning and enemy-randomizer behavior. Consumable
alternatives need count/missability treatment rather than treating possession of
one consumable as reusable capability. The wiki also reports Crystal Darts:
https://eldenring.wiki.gg/wiki/Albinauric_Rise
That is a route lead; the effect-source chain is not yet verified here.

## Silver Scarab (30207900)

The existing exclusion's imp-gate explanation has not been substantiated.
The committed treasure asset is 30201670 / lot 30200900 in m30_20, and the
accepted pin corroborates its physical placement. The vanilla map event
initializes common event 90005650 for *different* assets 30201540/30201541;
that alone cannot establish that the Silver Scarab chest requires the imp gate.

Restore after checking the route from the supported Hidden Path grace, including
invisible floors and illusory wall, against randomized access. Absence of a chest
lock instruction is not proof that the terrain route is reachable. Keep this
separate from Graven-Mass's confirmed scripted seal.
