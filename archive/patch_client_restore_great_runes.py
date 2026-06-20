#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_client_restore_great_runes.py

Goal
----
When the player RECEIVES a great rune from Archipelago, automatically put it in
its in-game RESTORED state so it is usable immediately -- equip at a Site of
Grace + burn a Rune Arc -- WITHOUT having to visit a Divine Tower.

This supports the new `num_regions_rune_source = pool` mode (Track A,
patch_apworld_num_regions_pool_runes.py) where the great runes are INJECTED
into the item pool instead of being dropped by their boss. A pool-granted rune
arrives as the raw, *unrestored* goods item, which the vanilla game refuses to
equip until you activate it at the matching Divine Tower -- a tower that the
seal/region-lock may have sealed off entirely. So the client must restore it on
receipt.

Mechanism (EVIDENCE-based -- see HANDOFF-num-regions-pool-runes-trackB.md)
--------------------------------------------------------------------------
Elden Ring ships TWO EquipParamGoods rows per great rune:

    UNRESTORED (what a boss/pool drops)   RESTORED (what the tower gives you)
    -----------------------------------   ----------------------------------
    8148 Godrick's Great Rune        ->   191 Godrick's Great Rune
    8149 Radahn's Great Rune         ->   192 Radahn's Great Rune
    8150 Morgott's Great Rune        ->   193 Morgott's Great Rune
    8151 Rykard's Great Rune         ->   194 Rykard's Great Rune
    8152 Mohg's Great Rune           ->   195 Mohg's Great Rune
    8153 Malenia's Great Rune        ->   196 Malenia's Great Rune
    10080 Great Rune of the Unborn   ->   (no restore -- usable as received)

Sources for the 191-196 / 8148-8153 pairing:
  * Paramdex/ER/Names/EquipParamGoods.txt rows 33-38 (191-196 "<Name>'s Great
    Rune") and 467-472 (8148-8153 "<Name>'s Great Rune").
  * Archipelago/worlds/eldenring/item script/GOODS.txt lines 15-20 name the
    191-196 rows "(Restored)" explicitly; lines 346-351 / 578 are the raw runes.
  * EIP Gaming catalog: "Godrick's Great Rune (Restored)" is the equippable
    item you hold AFTER restoring at the Divine Tower of Limgrave.

So "restore on receipt" == ALSO grant the matching (Restored) goods row. We do
this through the SAME proven grant path the progressive-bell overflow uses:
push a GOODS-packed FullID  (goodsId | 0x40000000)  onto
ItemRandomiser->receivedItemsQueue. GameHook decodes the 0x40000000 nibble as
the GOODS category and grants it via GrantFullID (one acquisition popup), so the
player ends up holding BOTH the raw rune (from Track A's normal grant) and the
restored variant -- and can equip the restored one immediately.

The Great Rune of the Unborn (Rennala, 10080) has NO Divine Tower and no
"(Restored)" row; it is usable as received, so it is intentionally NOT in the
restore map.

  >>> UNVERIFIED CAVEAT (read HANDOFF before shipping) <<<
The 191-196 IDs and the "grant the restored goods" model are corroborated by
three independent name/catalog sources above, but were NOT confirmed against
this fork's live regulation.bin from the sandbox (no param-row reader there).
If a playtest shows the granted 191-row is still "unrestored" (cannot equip),
the alternative is a per-rune restore EVENT FLAG set at the tower (Paramdex
shows FeTextEffectParam 21 "GREAT RUNE RESTORED" and ActionButtonParam
9080-9085 "Restore the power of the Great Rune", but the exact flag IDs were
NOT found in the sandbox and MUST NOT be invented). See the handoff's
"If goods-grant is insufficient" section.

Where it hooks
--------------
archipelago-client/ArchipelagoInterface.cpp, the on-receipt item handler --
the same block that already maps item NAME -> region grace flags, companion
"obtained" flags (kCompanionAcquireFlags), and key-item obtained flags
(kKeyItemAcquireFlags, from patch_client_rold_obtainedflag.py). We insert a
sibling map `kGreatRuneRestoreGoods` (NAME -> restored goods id) immediately
AFTER the key-item handler block, matching on the canonical AP item NAME that
Track A injects into the pool ("Godrick's Great Rune", etc.). It does NOT
`continue` -- the normal grant of the received rune still happens; the restored
variant is purely additive.

Conventions (matches patch_client_rold_obtainedflag.py)
-------------------------------------------------------
* Source is CRLF. We read as text with newline='' (preserve), back up, do a
  single asserted .replace(), write back with newline=''. A LF fallback anchor
  is provided in case the working copy was ever normalized.
* Idempotent: if APPLIED_MARKER is present, print and exit 0 (no write).
* If the anchor is missing, print [FAIL] and write NOTHING (non-zero exit).

How to run + build (Windows)
----------------------------
  cd C:\Users\alari\Documents\er-archipelago
  python patch_client_restore_great_runes.py
  # then rebuild the client:
  .\build.ps1 -Clean -All        (or -Client)
See HANDOFF-num-regions-pool-runes-trackB.md for full build + test steps.
"""

import os
import sys

TAG = "restore_great_runes"
APPLIED_MARKER = "kGreatRuneRestoreGoods"

CLIENT_DIR = r"C:\Users\alari\Documents\er-archipelago\Dark-Souls-III-Archipelago-client\archipelago-client"
TARGET = os.path.join(CLIENT_DIR, "ArchipelagoInterface.cpp")

# ---- Anchor: the END of the key-item-acquire handler (kKeyItemAcquireFlags),
# inserted by patch_client_rold_obtainedflag.py. We splice the great-rune
# restore map + handler immediately AFTER this closing block. This whole
# substring must be present verbatim (CRLF).
ANCHOR = (
    "\t\t\tauto keyIt = kKeyItemAcquireFlags.find(itemname);\r\n"
    "\t\t\tif (keyIt != kKeyItemAcquireFlags.end()) {\r\n"
    "\t\t\t\tfor (uint32_t flag : keyIt->second)\r\n"
    "\t\t\t\t\tCore->pendingGraceFlags.push_back(flag);\r\n"
    "\t\t\t\tspdlog::info(\"Key item '{}' received: queued {} obtained-flag(s)\",\r\n"
    "\t\t\t\t\titemname, keyIt->second.size());\r\n"
    "\t\t\t}\r\n"
)
ANCHOR_LF = ANCHOR.replace("\r\n", "\n")

# ---- Insertion: a sibling NAME -> restored-goods-id map + handler. On receipt
# of a great rune we push the matching (Restored) goods row through the normal
# grant queue as a GOODS-packed FullID (id | 0x40000000), exactly like the
# progressive-bell overflow grants a Lord's Rune (see ~30 lines below this in
# the same file: (DWORD)(2919 | 0x40000000)). This is ADDITIVE -- no `continue`
# -- so the raw rune grant still proceeds.
INSERT = (
    "\r\n"
    "\t\t\t// Great-rune restore-on-receipt: under num_regions_rune_source=pool the great runes are\r\n"
    "\t\t\t// INJECTED into the pool (patch_apworld_num_regions_pool_runes.py) and arrive as the raw,\r\n"
    "\t\t\t// UNRESTORED goods row, which the game won't let you equip until you activate it at the\r\n"
    "\t\t\t// matching Divine Tower (which the seal may have removed). ER ships a second 'restored'\r\n"
    "\t\t\t// EquipParamGoods row per rune (191-196; Paramdex EquipParamGoods 33-38, named \"(Restored)\"\r\n"
    "\t\t\t// in the apworld GOODS.txt). Granting that restored row = the same state the tower confers,\r\n"
    "\t\t\t// so the player can equip + Rune-Arc it immediately. We push it through the normal grant\r\n"
    "\t\t\t// queue as a GOODS-packed FullID (id | 0x40000000) -- identical mechanism to the Lord's Rune\r\n"
    "\t\t\t// overflow grant a few lines below. ADDITIVE: no `continue`, the raw rune still grants too.\r\n"
    "\t\t\t// The Great Rune of the Unborn (Rennala, 10080) has no tower / no restored row and is usable\r\n"
    "\t\t\t// as received, so it is intentionally absent.\r\n"
    "\t\t\tstatic const std::unordered_map<std::string, uint32_t> kGreatRuneRestoreGoods = {\r\n"
    "\t\t\t\t{ \"Godrick's Great Rune\",  191u },  // unrestored 8148 -> restored 191\r\n"
    "\t\t\t\t{ \"Radahn's Great Rune\",   192u },  // unrestored 8149 -> restored 192\r\n"
    "\t\t\t\t{ \"Morgott's Great Rune\",  193u },  // unrestored 8150 -> restored 193\r\n"
    "\t\t\t\t{ \"Rykard's Great Rune\",   194u },  // unrestored 8151 -> restored 194\r\n"
    "\t\t\t\t{ \"Mohg's Great Rune\",     195u },  // unrestored 8152 -> restored 195\r\n"
    "\t\t\t\t{ \"Malenia's Great Rune\",  196u },  // unrestored 8153 -> restored 196\r\n"
    "\t\t\t};\r\n"
    "\t\t\tauto runeIt = kGreatRuneRestoreGoods.find(itemname);\r\n"
    "\t\t\tif (runeIt != kGreatRuneRestoreGoods.end()) {\r\n"
    "\t\t\t\tItemRandomiser->receivedItemsQueue.push_front({\r\n"
    "\t\t\t\t\t(DWORD)(runeIt->second | 0x40000000), 1, sender, itemname,\r\n"
    "\t\t\t\t\titem.player == ap->get_player_number()\r\n"
    "\t\t\t\t});\r\n"
    "\t\t\t\tspdlog::info(\"Great rune '{}' received: also granting restored goods {} (usable now)\",\r\n"
    "\t\t\t\t\titemname, runeIt->second);\r\n"
    "\t\t\t}\r\n"
)
INSERT_LF = INSERT.replace("\r\n", "\n")


def main():
    if not os.path.isfile(TARGET):
        print("[FAIL] target not found: {}".format(TARGET))
        return 1

    with open(TARGET, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    if APPLIED_MARKER in text:
        print("already applied ({}): {} present".format(TAG, APPLIED_MARKER))
        return 0

    if ANCHOR in text:
        anchor, insert, nl = ANCHOR, INSERT, "CRLF"
    elif ANCHOR_LF in text:
        anchor, insert, nl = ANCHOR_LF, INSERT_LF, "LF"
    else:
        print("[FAIL] anchor (kKeyItemAcquireFlags handler block) not found in {}.".format(TARGET))
        print("[FAIL] Is patch_client_rold_obtainedflag.py applied first? Writing nothing.")
        return 2

    if text.count(anchor) != 1:
        print("[FAIL] anchor is not unique ({} matches); refusing to splice.".format(text.count(anchor)))
        return 3

    backup = TARGET + ".bak_" + TAG
    if not os.path.exists(backup):
        with open(backup, "w", encoding="utf-8", newline="") as bf:
            bf.write(text)
        print("backup written: {}".format(backup))
    else:
        print("backup already exists: {}".format(backup))

    new_text = text.replace(anchor, anchor + insert, 1)
    if new_text == text:
        print("[FAIL] replace() made no change despite anchor match; aborting.")
        return 4

    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)

    print("patched ({} newlines): {}".format(nl, TARGET))
    print("  + kGreatRuneRestoreGoods (Godrick 191, Radahn 192, Morgott 193,")
    print("    Rykard 194, Mohg 195, Malenia 196); Unborn left as-is.")
    print("  Rebuild the client (.\\build.ps1 -Clean -All) before testing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
