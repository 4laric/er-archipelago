#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_client_grace_items_20260621.py

Grace-rando CLIENT patch (C++). Run on Windows by Alaric.

Adds a `graceItems` slot_data map ({AP item name -> single ER warp-unlock event
flag}) to the runtime client, so that when a grace AP item is received, the
client queues that one flag onto the EXISTING pendingGraceFlags queue (drained by
CCore::FlushPendingGraceFlags on an in-game tick) -- identical mechanism to how
region-lock items already queue their grace flags by item NAME.

This patch ONLY touches the warp-unlock-flag path. It does NOT touch any
"already touched" activation flag (separate follow-up).

Targets (all under Dark-Souls-III-Archipelago-client/archipelago-client/):

  1. Core.h
     - ADD a `graceItems` member declaration after the `regionGraces` member.

  2. ArchipelagoInterface.cpp  (slot_connected handler)
     - ADD a parse block (clear + parse graceItems) immediately AFTER the
       existing regionGraces parse block.

  3. ArchipelagoInterface.cpp  (items_received handler)
     - ADD a lookup/queue block immediately AFTER the existing `graceIt`
       (regionGraces) lookup block.

DEVIATIONS FROM THE TASK EXCERPTS (confirmed by reading the files on disk):
  * The received-item name variable is `itemname` (lowercase), as in the excerpt.
  * Core.h: the regionGraces member is the full-width declaration
        std::unordered_map<std::string, std::vector<uint32_t>> regionGraces;
    indented with ONE leading TAB (not spaces). The new line matches that
    tab indentation.
  * ArchipelagoInterface.cpp slot_connected: the existing block is
        Core->regionGraces.clear();
        if (data.contains("regionGraces")) {
            data.at("regionGraces").get_to(Core->regionGraces);
            if (!Core->regionGraces.empty()) {
                spdlog::info("Region grace bundle: ...", Core->regionGraces.size());
            }
        }
    indented with TWO leading TABS (the inner lines 3/4 tabs). It is immediately
    followed (after a blank line) by the regionOpenFlags block. We anchor the
    insertion on the unique closing of the regionGraces block + the blank line +
    the start of the regionOpenFlags comment, and insert our block between them.
  * ArchipelagoInterface.cpp items_received: the existing graceIt block is
    indented with THREE leading TABS and is immediately followed (after a blank
    line) by the regionOpenFlags `openIt` block. We anchor on the closing of the
    graceIt block + the blank line + the regionOpenFlags comment, and insert
    our block between them.
  * All indentation in the added code uses TABS to match the surrounding source.

Properties: CRLF-safe (reads/writes with newline='' so existing line endings are
preserved; inserted text uses the file's detected newline), fully idempotent
(detects sentinel `graceItems` strings and no-ops), and re-reads every target
file after writing to verify each inserted string is present on disk.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Resolve repo root (this script lives at the repo root).
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(
    REPO_ROOT,
    "Dark-Souls-III-Archipelago-client",
    "archipelago-client",
)

CORE_H = os.path.join(CLIENT_DIR, "Core.h")
IFACE_CPP = os.path.join(CLIENT_DIR, "ArchipelagoInterface.cpp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_text(path):
    """Read preserving original line endings (newline='' => no translation)."""
    with open(path, "r", newline="", encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    """Write preserving embedded line endings (newline='' => no translation)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(text)


def detect_newline(text):
    """Return the dominant newline used in the file."""
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"


def to_eol(block_lf, eol):
    """Convert an LF-authored block to the file's newline convention."""
    # block_lf is authored with '\n'; normalize any stray CR then re-emit.
    normalized = block_lf.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", eol)


# ---------------------------------------------------------------------------
# Sentinels (idempotency detection) -- unique substrings of the added code.
# ---------------------------------------------------------------------------
SENTINEL_CORE_H = "std::unordered_map<std::string, uint32_t> graceItems;"
SENTINEL_PARSE = 'data.contains("graceItems")'
SENTINEL_RECV = "Core->graceItems.find(itemname)"


# ---------------------------------------------------------------------------
# Patch 1: Core.h member declaration
# ---------------------------------------------------------------------------
CORE_H_ANCHOR = (
    "\tstd::unordered_map<std::string, std::vector<uint32_t>> regionGraces;"
)

CORE_H_ADD_LF = (
    "\n"
    "\t// Grace rando (slot_data \"graceItems\"; SPEC-grace-rando.md): AP item NAME ->\n"
    "\t// ONE warp-unlock event flag set when that grace item is received. Reuses the\n"
    "\t// regionGraces pattern (keyed by NAME, drained via pendingGraceFlags +\n"
    "\t// FlushPendingGraceFlags). Present only when grace rando is active; empty otherwise.\n"
    "\tstd::unordered_map<std::string, uint32_t> graceItems;"
)


# ---------------------------------------------------------------------------
# Patch 2: ArchipelagoInterface.cpp slot_connected parse block
# ---------------------------------------------------------------------------
# Anchor: the END of the regionGraces parse block. We match the unique closing
# of that block up to (but not including) the regionOpenFlags comment, then
# insert the graceItems parse block in the blank gap.
PARSE_ANCHOR = (
    "\t\t\tif (!Core->regionGraces.empty()) {\n"
    "\t\t\t\tspdlog::info(\"Region grace bundle: {} region(s) will unlock graces on lock-item receipt\",\n"
    "\t\t\t\t\tCore->regionGraces.size());\n"
    "\t\t\t}\n"
    "\t\t}\n"
)

PARSE_ADD_LF = (
    "\n"
    "\t\t// Grace rando (SPEC-grace-rando.md): AP item name -> one warp-unlock flag.\n"
    "\t\t// Parsed alongside regionGraces; queued on receipt and set through the same\n"
    "\t\t// pendingGraceFlags drain (CCore::FlushPendingGraceFlags).\n"
    "\t\tCore->graceItems.clear();\n"
    "\t\tif (data.contains(\"graceItems\")) {\n"
    "\t\t\tdata.at(\"graceItems\").get_to(Core->graceItems);\n"
    "\t\t\tif (!Core->graceItems.empty())\n"
    "\t\t\t\tspdlog::info(\"Grace rando: {} grace item(s) will set a warp flag on receipt\",\n"
    "\t\t\t\t\tCore->graceItems.size());\n"
    "\t\t}\n"
)


# ---------------------------------------------------------------------------
# Patch 3: ArchipelagoInterface.cpp items_received lookup/queue block
# ---------------------------------------------------------------------------
# Anchor: the END of the regionGraces graceIt block.
RECV_ANCHOR = (
    "\t\t\tauto graceIt = Core->regionGraces.find(itemname);\n"
    "\t\t\tif (graceIt != Core->regionGraces.end()) {\n"
    "\t\t\t\tfor (uint32_t flag : graceIt->second) {\n"
    "\t\t\t\t\tCore->pendingGraceFlags.push_back(flag);\n"
    "\t\t\t\t}\n"
    "\t\t\t\tspdlog::info(\"Region lock '{}' received: queued {} grace flag(s)\",\n"
    "\t\t\t\t\titemname, graceIt->second.size());\n"
    "\t\t\t}\n"
)

RECV_ADD_LF = (
    "\n"
    "\t\t\t// Grace rando: if this item is a grace item, queue its single warp-unlock\n"
    "\t\t\t// flag for FlushPendingGraceFlags. Same queue/drain as the region-lock graces;\n"
    "\t\t\t// SetEventFlag is idempotent + save-persisted, so re-queue on reconnect is safe.\n"
    "\t\t\tauto graceItemIt = Core->graceItems.find(itemname);\n"
    "\t\t\tif (graceItemIt != Core->graceItems.end()) {\n"
    "\t\t\t\tCore->pendingGraceFlags.push_back(graceItemIt->second);\n"
    "\t\t\t\tspdlog::info(\"Grace item '{}' received: queued warp flag {}\",\n"
    "\t\t\t\t\titemname, graceItemIt->second);\n"
    "\t\t\t}\n"
)


# ---------------------------------------------------------------------------
# Apply one anchored insertion-after.
# ---------------------------------------------------------------------------
def apply_insert_after(text, anchor_lf, add_lf, eol, label, results):
    """
    Insert `add_lf` immediately after the (eol-normalized) `anchor_lf` in `text`.
    Returns (new_text, changed_bool). Records failures in `results`.
    """
    anchor = to_eol(anchor_lf, eol)
    add = to_eol(add_lf, eol)
    idx = text.find(anchor)
    if idx == -1:
        results.append((label, "FAIL", "anchor not found"))
        return text, False
    if text.count(anchor) > 1:
        results.append((label, "FAIL", "anchor not unique (%d matches)" % text.count(anchor)))
        return text, False
    insert_at = idx + len(anchor)
    new_text = text[:insert_at] + add + text[insert_at:]
    results.append((label, "APPLIED", "inserted after anchor"))
    return new_text, True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    overall_ok = True
    results = []

    # Pre-flight: confirm files exist.
    for p in (CORE_H, IFACE_CPP):
        if not os.path.isfile(p):
            print("FAIL: target file not found: %s" % p)
            return 2

    # ---- Core.h ----
    core_text = read_text(CORE_H)
    core_eol = detect_newline(core_text)
    if SENTINEL_CORE_H in core_text:
        results.append(("Core.h graceItems member", "IDEMPOTENT", "already present"))
    else:
        if to_eol(CORE_H_ANCHOR, core_eol) not in core_text:
            results.append(("Core.h graceItems member", "FAIL", "regionGraces anchor not found"))
            overall_ok = False
        else:
            core_text, changed = apply_insert_after(
                core_text, CORE_H_ANCHOR, CORE_H_ADD_LF, core_eol,
                "Core.h graceItems member", results,
            )
            if changed:
                write_text(CORE_H, core_text)
            else:
                overall_ok = False

    # ---- ArchipelagoInterface.cpp (both edits) ----
    iface_text = read_text(IFACE_CPP)
    iface_eol = detect_newline(iface_text)
    iface_changed = False

    # Patch 2: slot_connected parse block.
    if SENTINEL_PARSE in iface_text:
        results.append(("ArchipelagoInterface.cpp parse block", "IDEMPOTENT", "already present"))
    else:
        before = iface_text
        iface_text, changed = apply_insert_after(
            iface_text, PARSE_ANCHOR, PARSE_ADD_LF, iface_eol,
            "ArchipelagoInterface.cpp parse block", results,
        )
        if changed:
            iface_changed = True
        elif iface_text == before:
            overall_ok = False

    # Patch 3: items_received lookup block.
    if SENTINEL_RECV in iface_text:
        results.append(("ArchipelagoInterface.cpp recv block", "IDEMPOTENT", "already present"))
    else:
        before = iface_text
        iface_text, changed = apply_insert_after(
            iface_text, RECV_ANCHOR, RECV_ADD_LF, iface_eol,
            "ArchipelagoInterface.cpp recv block", results,
        )
        if changed:
            iface_changed = True
        elif iface_text == before:
            overall_ok = False

    if iface_changed:
        write_text(IFACE_CPP, iface_text)

    # ---- Verify on disk: re-read and confirm every sentinel is present. ----
    verify = []
    core_disk = read_text(CORE_H)
    iface_disk = read_text(IFACE_CPP)
    verify.append(("Core.h :: " + SENTINEL_CORE_H, SENTINEL_CORE_H in core_disk))
    verify.append(("ArchipelagoInterface.cpp :: " + SENTINEL_PARSE, SENTINEL_PARSE in iface_disk))
    verify.append(("ArchipelagoInterface.cpp :: " + SENTINEL_RECV, SENTINEL_RECV in iface_disk))

    # ---- Report ----
    print("=" * 72)
    print("patch_client_grace_items_20260621.py")
    print("=" * 72)
    print("Core.h    : %s (EOL=%s)" % (CORE_H, repr(core_eol)))
    print("Iface.cpp : %s (EOL=%s)" % (IFACE_CPP, repr(iface_eol)))
    print("-" * 72)
    print("Edits:")
    for label, status, detail in results:
        print("  [%-11s] %-45s %s" % (status, label, detail))
        if status == "FAIL":
            overall_ok = False
    print("-" * 72)
    print("On-disk verification:")
    for label, ok in verify:
        print("  [%s] %s" % ("OK " if ok else "MISSING", label))
        if not ok:
            overall_ok = False
    print("-" * 72)

    any_applied = any(s == "APPLIED" for _, s, _ in results)
    all_idem = all(s == "IDEMPOTENT" for _, s, _ in results) and len(results) == 3

    if not overall_ok:
        print("RESULT: FAIL")
        return 1
    if all_idem:
        print("RESULT: IDEMPOTENT (no changes; all three edits already present)")
        return 0
    if any_applied:
        print("RESULT: PASS (edits applied; all sentinels verified on disk)")
        return 0
    print("RESULT: PASS (no-op; sentinels verified on disk)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
