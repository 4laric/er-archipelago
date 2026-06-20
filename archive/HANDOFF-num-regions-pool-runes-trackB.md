# HANDOFF — Track B: restore great runes on AP receipt (client)

**Patch:** `patch_client_restore_great_runes.py`
**Target (Windows, build-only):** `Dark-Souls-III-Archipelago-client\archipelago-client\ArchipelagoInterface.cpp`
**Date:** 2026-06-19  •  **Author runs on Windows; sandbox cannot build the client.**

## What / why
Under the new `num_regions_rune_source = pool` mode (Track A,
`patch_apworld_num_regions_pool_runes.py`) the great runes are **injected into
the item pool** instead of being dropped by their boss. A pool-granted rune
arrives as the raw **UNRESTORED** goods item, which vanilla ER refuses to equip
until you activate it at the matching **Divine Tower** — and the seal/region-lock
may have removed that tower from the run. So the client must put the rune into
its **restored** (usable) state on receipt, with no tower visit.

## How it works
On item receipt, the existing handler in `ArchipelagoInterface.cpp` already maps
the incoming item **NAME** → region grace flags / companion "obtained" flags
(`kCompanionAcquireFlags`) / key-item flags (`kKeyItemAcquireFlags`). This patch
adds a **sibling** map `kGreatRuneRestoreGoods` (NAME → restored goods id)
immediately **after** the `kKeyItemAcquireFlags` handler block. When a great
rune is received it ALSO grants the **(Restored)** goods row by pushing a
GOODS-packed FullID `(restoredId | 0x40000000)` onto
`ItemRandomiser->receivedItemsQueue` — the **identical mechanism** the
progressive-bell overflow uses ~30 lines below to grant a Lord's Rune
`(DWORD)(2919 | 0x40000000)`. `GameHook` decodes the `0x40000000` nibble as the
GOODS category and grants via `GrantFullID`.

It is **additive** — there is **no `continue`** — so the raw rune still grants
through the normal path; the player ends up holding both the raw rune and the
restored variant, and can equip/Rune-Arc the restored one immediately.

## Rune → restore-token table (the IDs)

| AP item name (matched verbatim) | Unrestored goods | **Restored goods (granted)** | Evidence |
|---|---|---|---|
| Godrick's Great Rune | 8148 | **191** | Paramdex EquipParamGoods.txt L33 (191) + L467 (8148); apworld GOODS.txt L15 names 191 "(Restored)"; EIP catalog |
| Radahn's Great Rune | 8149 | **192** | Paramdex L34 + L468; apworld GOODS.txt L16 |
| Morgott's Great Rune | 8150 | **193** | Paramdex L35 + L469; apworld GOODS.txt L17 (the seed line in items.py: `#ERItemData("Morgott's Great Rune (Restored)", 193, ...)`) |
| Rykard's Great Rune | 8151 | **194** | Paramdex L36 + L470; apworld GOODS.txt L18 |
| Mohg's Great Rune | 8152 | **195** | Paramdex L37 + L471; apworld GOODS.txt L19 |
| Malenia's Great Rune | 8153 | **196** | Paramdex L38 + L472; apworld GOODS.txt L20 |
| Great Rune of the Unborn (Rennala) | 10080 | **— none —** | No Divine Tower, no "(Restored)" row; usable as received. Intentionally omitted. |

**Sources (file paths in this repo):**
- `Paramdex/ER/Names/EquipParamGoods.txt` rows 33–38 (restored 191–196) and 467–472 (unrestored 8148–8153).
- `Archipelago/worlds/eldenring/item script/GOODS.txt` L15–20 (the 191–196 rows explicitly labelled "(Restored)"); L346–351 + L578 (the raw runes).
- `Archipelago/worlds/eldenring/items.py` L1277–1282 (the commented `(Restored)` seed lines, incl. the Morgott 193 line from the original task brief).
- EIP Gaming: "Godrick's Great Rune (Restored)" = the equippable item held after restoring at the Divine Tower of Limgrave.

> Track A injects runes by these exact canonical names ("Godrick's Great Rune",
> "Great Rune of the Unborn", "Radahn's Great Rune", "Rykard's Great Rune" — see
> `NUM_REGIONS_STEP_GREAT_RUNE` in `patch_apworld_num_regions_pool_runes.py`).
> The map keys match those names verbatim, so the hook fires on the injected runes.
> The 3 non-spine runes (Morgott/Mohg/Malenia) are included too so the restore
> also works under any other mode that pool-grants them.

### ⚠️ UNVERIFIED — read before shipping
The 191–196 IDs and the **"grant the restored goods row = restored state"**
model are corroborated by THREE independent name/catalog sources above, but were
**NOT confirmed against this fork's live `regulation.bin`** from the sandbox
(no param-row reader there; Paramdex ships defs+names only, not row data). Treat
as **high-confidence-but-playtest-gated**, not proven.

**If the goods-grant is insufficient** (playtest shows the granted 191-row still
can't be equipped / shows "unrestored"): the alternative mechanism is a per-rune
**restore EVENT FLAG** set at the tower. Paramdex hints at it
(`FeTextEffectParam` 21 "GREAT RUNE RESTORED"; `ActionButtonParam` 9080–9085
"Restore the power of the Great Rune") but the **exact event-flag IDs were NOT
found in the sandbox**. **DO NOT invent them** — invented ER flags silently
no-op. Source them from the divine-tower EMEVD (e.g. the
`Elden Ring Randomizer-428.../randomizer/diste/Vanilla/m34_*` tower maps, which
are binary `.emevd.dcx` — decompile with EventScriptTools / DSMapStudio on
Windows) or from a known great-rune flag table, then add a parallel
`kGreatRuneRestoreFlags` map draining onto `Core->pendingGraceFlags` (same shape
as `kKeyItemAcquireFlags`).

## Precondition / ordering
This patch's **anchor is the `kKeyItemAcquireFlags` handler block** added by
`patch_client_rold_obtainedflag.py`. That patch must be applied **first**
(it already is in the current working tree — verified). If the anchor is
missing the script prints `[FAIL]` and writes nothing.

## Build on Windows
```powershell
cd C:\Users\alari\Documents\er-archipelago

# 0) PRECONDITION: confirm the client submodule working tree is sane first.
git -C Dark-Souls-III-Archipelago-client status
#   ArchipelagoInterface.cpp should already show the kKeyItemAcquireFlags edit.
#   If the file looks truncated/corrupt vs HEAD, restore before patching:
#     git -C Dark-Souls-III-Archipelago-client restore archipelago-client/ArchipelagoInterface.cpp
#   (then re-apply patch_client_rold_obtainedflag.py first.)

# 1) apply this patch (idempotent; writes a .bak_restore_great_runes backup)
python patch_client_restore_great_runes.py

# 2) verify the splice on disk
Select-String -Path Dark-Souls-III-Archipelago-client\archipelago-client\ArchipelagoInterface.cpp `
  -Pattern "kGreatRuneRestoreGoods"

# 3) rebuild the client (kill any stale :38281 server first per build convention)
.\build.ps1 -Clean -All        # or -Client for a client-only rebuild
```
If the mount/Edit ever truncates the file, do NOT re-write to "fix" it — freeze,
`git restore` the file, re-apply patches, rebuild. (Per repo memory: a corrective
re-write is what truncated `__init__.py` once.)

## How to test
1. Generate + bake a seed with `num_regions` Capital mode and
   `num_regions_rune_source: pool` (Track A) so great runes are injected into the
   pool. (Or, fastest: any seed, then `!getitem Godrick's Great Rune` from the AP
   server console to force-send it.)
2. Connect the client, receive a great rune (e.g. **Godrick's Great Rune**).
   - Client log should show: `Great rune '...' received: also granting restored goods 191 (usable now)`.
3. In game: open Inventory → Key Items / Great Runes; **equip the Great Rune at a
   Site of Grace** (Menu → Great Runes). It should equip **without** the
   "restore at a Divine Tower" prompt.
4. Use a **Rune Arc** → the rune's buff applies (Godrick = +5 all attributes).
5. Confirm the **Great Rune of the Unborn** (Rennala) also works when received
   (it needs no restore — no extra grant is expected for it).

## Risks
- **Unverified IDs** (above) — the one real risk. Playtest gates shipping.
- **Double item visually**: the player holds both the raw rune and the restored
  variant. Cosmetic only; if undesirable, a follow-up could `removeFromInventory`
  the raw 8148-row (GameHook already exposes `removeFromInventory`) — left out
  here to keep the patch minimal and avoid an extra failure mode.
- **Acquisition popups**: one extra popup per rune (the restored grant). Matches
  the existing Lord's-Rune-overflow UX; acceptable.
- **Anchor drift**: if `kKeyItemAcquireFlags` is renamed/removed upstream the
  patch fails loudly (`[FAIL]`, no write) rather than corrupting the file.

## Status
- `patch_client_restore_great_runes.py` written, `py_compile` clean, dry-run on a
  /tmp copy of the real source: anchor unique, CRLF preserved, braces balanced
  (173/173), file not truncated, second run = idempotent no-op.
- **Mount client source deliberately NOT edited** (Windows build only).
- **NEEDS: Windows apply + client rebuild + playtest** (verify restored runes equip).
