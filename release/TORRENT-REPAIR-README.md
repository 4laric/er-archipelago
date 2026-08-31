# Tarnished Torrent Repair

This is a small post-randomization compatibility patch for Matt's Elden Ring Randomizer v0.11.4
on Elden Ring 1.17. Matt rewrites `regulation.bin` from a pre-1.17 base, removing four Spectral
Steed `RideParam` rows and their four matching `NpcParam` rows. Torrent can then stop answering
the whistle.

## Run after every randomization

1. Generate the seed with Matt's randomizer, then close the randomizer and Elden Ring.
2. Extract this repair anywhere.
3. Open PowerShell in the extracted folder and run the Python script directly:

```powershell
py .\torrent_rideparam_repair.py --regulation "C:\path\to\randomizer\regulation.bin"
```

If it reports missing `ParamCrypt` metadata, install the fixed Soulstruct source snapshot once, then
repeat the repair command:

```powershell
py -m pip install --force-reinstall --no-cache-dir https://github.com/Grimrukh/soulstruct/archive/d59dc41e607ed4221378519c81609557241dce6b.zip
```

The repair makes a timestamped backup, changes only the eight verified Torrent rows, verifies the
encrypted result, and replaces `regulation.bin` atomically. A repeated run without regenerating is
a safe no-op.

Matt rewrites `regulation.bin` whenever it generates a seed, so run this repair again after each
randomization and before launching the game.

`tarnished-torrent-rideparam-1.17.json` is included as a manual Smithbox Param Delta Patch fallback.
See `TARNISHED-TORRENT-REPAIR.md` for those instructions.
