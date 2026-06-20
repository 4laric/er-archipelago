# SPEC — Soft-Consumable Cleanup (Twin Maiden shop + Gurranq de-rando)

Two independent options that pull "fun consumable" clutter out of the priority/progression
fill. patch_apworld_soft_consumables.py implements the apworld halves.

## Background

Stonesword Keys, Dragon Hearts and Deathroot are classified `progression` but each gates only
optional content (imp-statue seals, Dragon Communion shops, Gurranq's ladder). That drags them
into the fill and the important_locations priority pool, where they crowd real progression and
land junk-chain keys on important spots. The key/heart gates are modeled by the count-helpers
`_has_enough_keys` (cumulative to 46) and `_has_enough_hearts` (to 23) -- EXCEPT several checks
flagged `nokey=True` (Assassin's Prayerbook behind the 2nd imp statue; the whole Caelid Church
of Dragon Communion incantation shop) which bypass the gate entirely. That `nokey` bypass is a
latent access gap: a progression item there is reachable in AP logic but needs a key/heart the
randomizer doesn't guarantee.

## Option A: soft_consumable_shop (Toggle, default off)

Stonesword Keys + Dragon Hearts become **infinitely buyable at the Twin Maiden Husks**
(Roundtable, reachable from the start).

apworld (done, patch_apworld_soft_consumables.py):
- `_has_enough_keys` / `_has_enough_hearts` return True (the shop is always reachable, so the
  gates are trivially satisfied -- this also closes the `nokey` access gap).
- All six key/heart variants get `skip = True` in generate_early -> out of the randomized pool
  (their world locations backfill with filler). Hearts are left alone under dlc_only (that path
  precollects its own 25).
- The bool flows to the baker automatically via `slot_data["options"]` -> `opt["soft_consumable_shop"]`.

baker (DONE -- patch_baker_soft_consumable_shop.py): two edits, both anchor-validated.
- ArchipelagoForm.cs ConvertRandomizerOptions: `opt["soft_consumable_shop"] = archiOptions.GetValueOrDefault("soft_consumable_shop", false);` (BoolOptions reads it generically from slot_data).
- PermutationWriter.Write (before "// End Elden Ring edits"): when `opt["soft_consumable_shop"]`,
  clone Twin Maiden goods row **101802** (Spirit Calling Bell -- always-stocked goods, so
  equipType=3/costType=runes inherit correctly) into gap ids **101882 / 101883**, overriding
  equipId/value/sellQuantity(-1)/mtrlId(-1)/eventFlag_forStock(0)/forRelease(0):
  `AddTwinMaidenInfinite(101882, 8000, 2000)` and `(101883, 10060, 5000)`.

Confirmed from Paramdex: `s16 sellQuantity = -1` (-1 = infinite); Twin Maiden block = 101800-101899
(101882/101883 are gaps). VERIFY in-game after bake: both rows appear in the Twin Maiden menu at
2000 / 5000 and are infinite (if they don't show, the menu's id range / stock flag needs a tweak).
**Ship the baker shop and the apworld option together** -- enabling the option without the baked
rows leaves seals/communion unopenable in-game (a real softlock).

## Option B: derandomize_gurranq (Toggle, default off) -- apworld-only, ships standalone

Gurranq's deathroot ladder is 10 **missable** rewards behind a blind cumulative gate. The seven
mediocre beast incantations/AoW go vanilla; the three keepers are re-injected into the pool.

apworld (done):
- `item_table["Deathroot"].skip = True` (out of the pool) in generate_early.
- In _fill_local_items: precollect 9 Deathroot (satisfies the `has(Deathroot,N)` reachability
  rules), `_lock_class_at_vanilla` the 10 ladder LOCATIONS (matched by location name, so other
  copies of e.g. Ancient Dragon Smithing Stone aren't touched), then swap one filler each for
  Clawmark Seal + Beastclaw Greathammer + Ancient Dragon Smithing Stone (count-neutral). They
  end up both locked-vanilla at Gurranq AND a shuffled copy -- and stop being missable-only.

Ladder rewards: 1 Clawmark Seal (keep) + Beast Eye, 2 Bestial Sling, 3 Bestial Vitality,
4 AoW Beast's Roar, 5 Beast Claw, 6 Stone of Gurranq, 7 Beastclaw Greathammer (keep),
8 Gurranq's Beast Claw, 9 Ancient Dragon Smithing Stone (keep).

## Related backlog (TODO.md)

Inject an in-game sign near Gurranq listing all ladder rewards, so the blind cumulative gate
isn't opaque. Baker FMG/message injection; pairs with Option B.

## Testing

1. `python patch_apworld_soft_consumables.py` (repo root). Idempotent.
2. derandomize_gurranq: gen-test now (apworld-only). Spoiler: the 10 Gurranq checks vanilla;
   Clawmark Seal / Beastclaw Greathammer / Ancient Dragon Smithing Stone each appear shuffled.
3. soft_consumable_shop: only after the baker rows exist. Gen-test (keys/hearts gone from pool,
   gen succeeds), then bake + in-game confirm the two infinite Twin Maiden rows at 2000 / 5000.
