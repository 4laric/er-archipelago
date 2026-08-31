# Tarnished Edition: repair Torrent after running Matt's randomizer

Matt's Elden Ring Randomizer v0.11.4 writes a pre-1.17 `regulation.bin`. Elden Ring 1.17 added four
`RideParam` rows and four matching `NpcParam` rows used by the new Spectral Steed appearances. When
either half is absent, Torrent may stop answering the whistle.

`tarnished-torrent-rideparam-1.17.json` is a Smithbox Param Delta Patch containing the four new
`RideParam` rows (`80020`, `80030`, `80040`, `80050`) and their four matching `NpcParam` rows
(`80020000`, `80030000`, `80040000`, `80050000`). A comparison of Matt v0.11.4 with vanilla 1.17
found the base Torrent rows identical, making these safe clones with the verified 1.17 changes.

## Recommended post-randomization repair

Run Matt's randomizer first. After it finishes, close both the randomizer and Elden Ring, then run
the repair from the Archipelago release folder:

```powershell
py .\me3\torrent_rideparam_repair.py --regulation "C:\path\to\randomizer\regulation.bin"
```

The repair needs Soulstruct's fixed 2.3.2 source build. Install it once if the command reports that
`ParamCrypt` metadata is missing. The PyPI 2.3.2 wheel is incomplete, so use the fixed upstream
source snapshot:

```powershell
py -m pip install --force-reinstall --no-cache-dir https://github.com/Grimrukh/soulstruct/archive/d59dc41e607ed4221378519c81609557241dce6b.zip
```

Then repeat the repair command. It decrypts the regulation with Soulstruct but rewrites only the raw `RideParam` and
`NpcParam` binder entries. It preserves every existing binder entry and existing row byte-for-byte,
refuses partial or conflicting repairs, verifies the encrypted result, makes a timestamped backup,
and replaces the target atomically. A second run is an idempotent no-op.

**Repeat the repair after every Matt reroll.** Matt rewrites `regulation.bin` whenever it generates
a seed, so a repair performed before randomizing is immediately replaced. The final repair message
must say either that the rows were patched or that all eight rows were already present.

## Manual Smithbox mode

1. Run Matt's randomizer first and close Elden Ring.
2. Back up Matt's generated `randomizer/regulation.bin`.
3. Open that randomizer output as an Elden Ring project in a current Smithbox release.
4. Open **Param Editor → Tools → Param Delta Patcher**, then use **Open Delta Folder**.
5. Copy `tarnished-torrent-rideparam-1.17.json` into that folder and refresh the patch list.
6. Select the patch. Enable **Include Added Rows**. Leave **Allow Row Overwrite** disabled.
7. Preview the import: it must show exactly four additions to `RideParam` and four additions to
   `NpcParam`, with the IDs listed above. Import it and save the params.
8. Confirm Smithbox wrote the repaired `regulation.bin` into Matt's output, then launch normally.

The delta uses Smithbox's native Param Delta Patcher format. It was generated from the verified
vanilla 1.17 `RideParam` corpus; Smithbox itself is not bundled.

Reapply after generating a new Matt seed if the randomizer rewrites `regulation.bin`. Once Matt's
output already contains these rows, do not force an overwrite; the repair is obsolete and should be
skipped.

This file is deliberately an eight-row delta, not a redistributed or pre-merged `regulation.bin`, so
it cannot replace Matt's enemy, boss, class, or balance edits.
