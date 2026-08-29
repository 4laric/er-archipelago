# Tarnished Edition: repair Torrent after running Matt's randomizer

Matt's Elden Ring Randomizer v0.11.4 writes a pre-1.17 `regulation.bin`. Elden Ring 1.17 added four
`RideParam` rows used by the new Spectral Steed appearances. When those rows are absent, Torrent may
stop answering the whistle.

`tarnished-torrent-rideparam-1.17.json` is a Smithbox Param Delta Patch containing only those four
new rows: `80020`, `80030`, `80040`, and `80050`. A comparison of Matt v0.11.4's exported table with
vanilla 1.17 found no other added, removed, or modified `RideParam` rows.

## One-command installer mode

The release's existing Matt installer can patch the rows while it wires in the client:

```powershell
.\me3\install-into-matts-rando.ps1 -Randomizer "C:\path\to\randomizer" -WithTorrentRepair
```

This mode requires Soulstruct 2.3.2's fixed source build. Its PyPI 2.3.2 wheel omitted two
ParamCrypt metadata files, so install the fixed upstream commit for the same Python first:

```powershell
py -m pip install "soulstruct @ git+https://github.com/Grimrukh/soulstruct.git@d59dc41e"
```

The installer decrypts the regulation with Soulstruct but rewrites only the raw `RideParam` binder
entry. It preserves all existing binder entries and RideParam rows byte-for-byte, refuses partial
or conflicting repairs, verifies the encrypted result, makes a timestamped backup, and replaces
the target atomically. A second run is an idempotent no-op.

## Manual Smithbox mode

1. Run Matt's randomizer first and close Elden Ring.
2. Back up Matt's generated `randomizer/regulation.bin`.
3. Open that randomizer output as an Elden Ring project in a current Smithbox release.
4. Open **Param Editor → Tools → Param Delta Patcher**, then use **Open Delta Folder**.
5. Copy `tarnished-torrent-rideparam-1.17.json` into that folder and refresh the patch list.
6. Select the patch. Enable **Include Added Rows**. Leave **Allow Row Overwrite** disabled.
7. Preview the import: it must show exactly four additions to `RideParam`, with IDs `80020`,
   `80030`, `80040`, and `80050`. Import it and save the params.
8. Confirm Smithbox wrote the repaired `regulation.bin` into Matt's output, then launch normally.

The delta uses Smithbox's native Param Delta Patcher format. It was generated from the verified
vanilla 1.17 `RideParam` corpus; Smithbox itself is not bundled.

Reapply after generating a new Matt seed if the randomizer rewrites `regulation.bin`. Once Matt's
output already contains these rows, do not force an overwrite; the repair is obsolete and should be
skipped.

This file is deliberately a four-row delta, not a redistributed or pre-merged `regulation.bin`, so
it cannot replace Matt's enemy, boss, class, or balance edits.
