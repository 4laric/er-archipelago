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

## Silver Scarab (30207900) — recovered

The route is now corroborated from the supported Hidden Path grace: downstairs,
central platform, invisible walkway, south room, illusory wall, chest. This is
ordinary traversal with no inventory requirement. See `mfg_silver_scarab.json`
for the walkthrough, exact native pin, game-data identity and region witnesses.
The old imp-gate explanation was incorrect. The separate boss-door event is
lever-driven and its route is later in the walkthrough. Graven-Mass remains
excluded pending the combat/summon capability work above.
