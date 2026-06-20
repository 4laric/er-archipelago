# Seed 97943139363536579023 — saved to finish later

Slot **Alaric** · server `localhost:38281` · location_flags **688** · regulation baked **2026‑06‑16 21:51** · preflight **PASS**.

This is the seed your current in‑game save matches. Because every `-Bake`/`-Deploy` overwrites the game‑root files, your save desyncs the moment you build any other seed. This folder pairs the save with its exact seed so you can resume any time.

## What's here now
- `ap-server/AP_97943139363536579023.zip` — AP multidata (host this to resume) + spoiler inside
- `ap-server/AP_97943139363536579023.apsave` — AP server progress (items received/sent)
- `ap-server/AP_97943139363536579023_Spoiler.txt` — extracted spoiler, for reference
- `EldenRing-dlc-only.yaml` — the slot yaml that generated it
- `deploy_manifest.txt` — the 163 deployed mod files this seed needs
- `snapshot_seed.ps1` / `restore_seed.ps1` — capture / redeploy the Windows‑only pieces

The save `.sl2` and the deployed game files (regulation.bin, event\, msg\, script\, map\) live outside this sandbox, so they're captured by the script below — not yet in this folder.

## To finish capturing (do this now, on Windows)
After your last play session for this seed:

```powershell
cd "C:\Users\alari\Documents\er-archipelago\seeds-archive\seed-97943139363536579023"
.\snapshot_seed.ps1
```

That adds `game-files\`, `mods\`, and `save\<steamid>\` and refreshes the live `.apsave`. The seed is then fully self‑contained — safe to keep building other seeds.

## To resume later

```powershell
cd "C:\Users\alari\Documents\er-archipelago\seeds-archive\seed-97943139363536579023"
.\restore_seed.ps1
```

It redeploys the game files + mods, restores the AP files to `Archipelago\output`, and puts the `.sl2` back (backing up whatever's currently in place first). Then host `AP_97943139363536579023.zip`, launch ER through your mod loader, and **Load Game**.

> Tip: `restore_seed.ps1 -SkipSave` redeploys the seed without touching your current save.
