# ALttPR duplicate-item fill failure — 2026-09-10

The reported ER 0.6.0.6 `fill_hook_shim` assertion is reproducible with the supplied 25-player / 23-game room on Archipelago 0.6.7. Its root cause is **ALttPR 1.5.0 removing an equal item instead of the item object it just placed**. No ER placement change is needed.

## Evidence

- The supplied Elden Ring archive matches published 0.6.0.6 exactly: SHA-256 `1e5338869438a1e0db03714b562827545898f0f583f23d3500d4160057caa7e3`.
- The supplied custom `alttpr.apworld` declares world version 1.5.0 and has SHA-256 `9dc9379bfb686639604cbd8e68e43ba42fa0169913b2d14ee8b448dbc143649a`.
- AP 0.6.7 `BaseClasses.Item.__eq__` compares item name and player, not object identity. Two Small Heart copies for one player therefore compare equal.
- `alttpr/World.py:198` calls `Items.place_junk_items_in_pots` from its per-world fill hook, before ER's stage hook. In the supplied `alttpr/Items.py`, lines 522 and 542 call `filleritempool.remove(item)` after placing a shuffled copy. They can remove an unplaced equal copy. The progression-removal site at line 518 also uses equality and is repaired to exact identity.
- Instrumentation at ER hook entry finds 263 already-placed ALttPR objects still present in the classified lists. The original ER assertion detects that corruption. Merely filtering them out leaves 263 empty locations at final fill, so removing or relaxing the ER assertion is not a fix.
- The supplied Zelda settings include `potsanity: lottery`, underworld enemy drops, and `local_fill_percent: 80`. The affected routine handles both pot overflow and local junk placement.

The existing multiworld smoke passes with Hollow Knight, Bumper Stickers, DOOM 1993, The Wind Waker and Heretic. Those partners do not exercise this custom ALttPR routine. Twelve additional probes of the released ER archive also pass with default ER settings. This demonstrates the coverage gap; it does not dismiss the reported failure.

## Apply the repair

Use the repository's [repair tool](../tools/repair_alttpr_item_identity.py) with Python 3.11 or newer:

```powershell
python tools/repair_alttpr_item_identity.py "D:\Archipelago\custom_worlds\alttpr.apworld" --output "D:\Archipelago\alttpr-repaired.apworld"
```

Keep the original as a backup **outside** `custom_worlds`, then install the repaired file there as `alttpr.apworld`. Generate the room again. The ER package and YAMLs can remain as supplied.

The helper accepts only the verified `alttpr/Items.py` SHA-256 `2c6f5b56c20d65d6f36edb52a99f73421acc01367ca4162faa70e438ef5c2bf6`. It refuses an existing output, an in-place overwrite, unknown source, and already-repaired source. It changes three removal sites, checks the resulting Python syntax, preserves all other members, and verifies the output archive. No third-party package or player bundle is committed to this repository.

For the supplied archive, the repaired package SHA-256 is `d6a8ad8ed7b63159eb97ad0317b163de0d0b844941935572a685d0db54895b83`.

## Validation

- The unchanged release artifact reproduces the exact reported assertion, including matching per-pass placement counts.
- Executing the supplied ALttPR function with two equal but distinct AP Item instances reproduces corruption in both the local-fill and pot-overflow paths; the repaired function preserves the unplaced copy in both.
- The reported full room and a second seed both generate final archives successfully with only `alttpr/Items.py` repaired and ER unchanged.
- Repair-tool tests cover equal-copy preservation, rejection of unknown source, archive-member preservation, input preservation, and refusing existing/in-place output.

The supplied archives and generation logs are local investigation inputs. This repair is a targeted compatibility aid, not a new official ALttPR release or a change to the Elden Ring client.
