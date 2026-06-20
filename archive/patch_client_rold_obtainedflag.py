#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_client_rold_obtainedflag.py

Goal
----
When the player receives certain vanilla KEY ITEMS, set their vanilla
"obtained" event flag. The game gates progression on these flags, not on
inventory, so a raw client grant (goods) leaves the gate sealed.

Concretely: the Grand Lift of Rold reads event flag 400001 ("Rold Medallion
obtained"). The client granted goods 8107 (Rold Medallion) but never set
400001, so the lift stayed sealed. Same shape for the Drawing-Room Key
(400072), which gates the Volcano Manor drawing-room transition.

This mirrors the existing `kCompanionAcquireFlags` handler in
ArchipelagoInterface.cpp: a NAME -> {event flags} map whose flags are pushed
onto Core->pendingGraceFlags, flushed on a settled in-game tick by
CCore::FlushPendingGraceFlags() via the idempotent + save-persisted
SetEventFlag.

Design choice
-------------
We add a SEPARATE static map `kKeyItemAcquireFlags` right after the existing
`kCompanionAcquireFlags` block, plus its own lookup/queue snippet, rather than
extending the companion map. Reasons:
  * The companion map is documented as "possession-gated companion item"; key
    items (Rold Medallion / Drawing-Room Key) are a distinct concept. Keeping
    them separate keeps each map's comment accurate and avoids disturbing the
    companion entries (the task asked to keep the companion map undisturbed).
  * It is purely additive: a second const map + a second find()/push loop. No
    existing line is mutated, lowering merge/regression risk.

Conventions
-----------
* C++ source is CRLF; this script reads the file as text in Python, backs it
  up, does a string .replace() asserting the anchor is present, and writes
  back preserving newlines (newline='' on both read and write).
* Idempotent: if the applied-marker is already present, prints "already
  applied" and exits 0.
"""

import os
import sys

TAG = "rold_obtainedflag"
APPLIED_MARKER = "kKeyItemAcquireFlags"

CLIENT_DIR = r"C:\Users\alari\Documents\er-archipelago\Dark-Souls-III-Archipelago-client\archipelago-client"
TARGET = os.path.join(CLIENT_DIR, "ArchipelagoInterface.cpp")

# ---- Anchor: the END of the existing companion-acquire handler. We insert the
# new key-item map + handler immediately AFTER this closing block so we do not
# touch the companion map itself. This whole substring must be present verbatim.
ANCHOR = (
    "\t\t\tauto compIt = kCompanionAcquireFlags.find(itemname);\r\n"
    "\t\t\tif (compIt != kCompanionAcquireFlags.end()) {\r\n"
    "\t\t\t\tfor (uint32_t flag : compIt->second)\r\n"
    "\t\t\t\t\tCore->pendingGraceFlags.push_back(flag);\r\n"
    "\t\t\t\tspdlog::info(\"Companion item '{}' received: queued {} acquisition flag(s)\",\r\n"
    "\t\t\t\t\titemname, compIt->second.size());\r\n"
    "\t\t\t}\r\n"
)

# Fallback anchor with LF newlines, in case the working copy was normalized.
ANCHOR_LF = ANCHOR.replace("\r\n", "\n")

# ---- Insertion: a sibling map + handler, same drain (pendingGraceFlags). CRLF.
INSERT = (
    "\r\n"
    "\t\t\t// Key-item acquisition flags: vanilla KEY ITEMS whose progression gate reads an\r\n"
    "\t\t\t// \"obtained\" EVENT FLAG, not inventory. A raw client goods-grant leaves the gate\r\n"
    "\t\t\t// sealed, so set the flag here. Same NAME->flags shape + same pendingGraceFlags drain\r\n"
    "\t\t\t// (FlushPendingGraceFlags -> SetEventFlag, idempotent + save-persisted) as the\r\n"
    "\t\t\t// companion map above. Kept separate from kCompanionAcquireFlags so each map's intent\r\n"
    "\t\t\t// stays clear. Add an entry for any future flag-gated key item.\r\n"
    "\t\t\tstatic const std::unordered_map<std::string, std::vector<uint32_t>> kKeyItemAcquireFlags = {\r\n"
    "\t\t\t\t{ \"Rold Medallion\",   { 400001u } },  // Grand Lift of Rold gates on 400001 (was sealed)\r\n"
    "\t\t\t\t{ \"Drawing-Room Key\", { 400072u } },  // Volcano Manor drawing-room transition\r\n"
    "\t\t\t};\r\n"
    "\t\t\tauto keyIt = kKeyItemAcquireFlags.find(itemname);\r\n"
    "\t\t\tif (keyIt != kKeyItemAcquireFlags.end()) {\r\n"
    "\t\t\t\tfor (uint32_t flag : keyIt->second)\r\n"
    "\t\t\t\t\tCore->pendingGraceFlags.push_back(flag);\r\n"
    "\t\t\t\tspdlog::info(\"Key item '{}' received: queued {} obtained-flag(s)\",\r\n"
    "\t\t\t\t\titemname, keyIt->second.size());\r\n"
    "\t\t\t}\r\n"
)

INSERT_LF = INSERT.replace("\r\n", "\n")


def main():
    if not os.path.isfile(TARGET):
        print("ERROR: target not found: {}".format(TARGET))
        return 1

    with open(TARGET, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    if APPLIED_MARKER in text:
        print("already applied ({}): {} present".format(TAG, APPLIED_MARKER))
        return 0

    # Pick the matching newline variant.
    if ANCHOR in text:
        anchor, insert = ANCHOR, INSERT
    elif ANCHOR_LF in text:
        anchor, insert = ANCHOR_LF, INSERT_LF
    else:
        raise RuntimeError(
            "Anchor (companion-acquire handler block) not found in {}. "
            "Aborting without changes.".format(TARGET)
        )

    # Back up.
    backup = TARGET + ".bak_" + TAG
    if not os.path.exists(backup):
        with open(backup, "w", encoding="utf-8", newline="") as bf:
            bf.write(text)
        print("backup written: {}".format(backup))
    else:
        print("backup already exists: {}".format(backup))

    # Insert the new block right after the companion handler.
    new_text = text.replace(anchor, anchor + insert, 1)
    if new_text == text:
        raise RuntimeError("replace() made no change despite anchor match; aborting.")

    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)

    print("patched: {}".format(TARGET))
    print("  + kKeyItemAcquireFlags (Rold Medallion 400001, Drawing-Room Key 400072)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
