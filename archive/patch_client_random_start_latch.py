#!/usr/bin/env python3
"""
patch_client_random_start_latch.py -- runtime client Chapel latch for Random Starting Region (#1).
SPEC: SPEC-random-starting-region.md. Mirrors the dlc_only auto-entry latch exactly.

When the poll sees the player in randomStartAreaId (Chapel of Anticipation, = 18000) on a fresh save,
it sets randomStartWarpFlag (76969) ONCE -> baked common.emevd WarpPlayer -> the rolled start region
(see patch_baker_random_start_warp_v2_datadriven.py). A persistent randomStartDoneFlag (76968) guards
the optional late Chapel revisit / reconnect, so it fires once per save.

Edits (all 3 files CRLF + TAB-indented):
  Core.h                    : 3 int32_t fields (randomStartWarpFlag/AreaId/DoneFlag).
  ArchipelagoInterface.cpp  : read them from slot_data (next to the dlc auto-entry read).
  Core.cpp                  : poll latch (next to the dlc auto-entry latch).

Flags come from slot_data (patch_apworld_random_start_warpflags.py); 0 => inert on non-random seeds.
Run on Windows; rebuild the client. Idempotent. CRLF + tabs preserved.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "Dark-Souls-III-Archipelago-client", "archipelago-client")
CORE_H = os.path.join(BASE, "Core.h")
AI = os.path.join(BASE, "ArchipelagoInterface.cpp")
CORE_CPP = os.path.join(BASE, "Core.cpp")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


def _ins_after(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + insert, 1)


# ---- Core.h (1-tab fields) ----
COREH_ANCHOR = _crlf("\tint32_t dlcStartAreaId = 0;\n")
COREH_INS = _crlf(
    "\t// Random starting region (slot_data randomStartWarpFlag/AreaId/DoneFlag): when the poll sees\n"
    "\t// the player in randomStartAreaId (Chapel) it sets randomStartWarpFlag (76969) ONCE -> baked\n"
    "\t// common.emevd WarpPlayer -> the rolled start region. randomStartDoneFlag (76968) persists so it\n"
    "\t// fires once per save. 0/absent on non-random-start seeds. See patch_baker_random_start_warp_v2_datadriven.py.\n"
    "\tint32_t randomStartWarpFlag = 0;\n"
    "\tint32_t randomStartAreaId = 0;\n"
    "\tint32_t randomStartDoneFlag = 0;\n"
)

# ---- ArchipelagoInterface.cpp (2-tab reads) ----
AI_ANCHOR = _crlf(
    '\t\t\tspdlog::info("DLC auto-entry: flag {} fires when player enters area {}", Core->dlcEntryWarpFlag, Core->dlcStartAreaId);\n'
)
AI_INS = _crlf(
    "\t\t// Random starting region: same latch pattern as DLC auto-entry, for the rolled start region.\n"
    '\t\tCore->randomStartWarpFlag = data.value("randomStartWarpFlag", 0);\n'
    '\t\tCore->randomStartAreaId   = data.value("randomStartAreaId", 0);\n'
    '\t\tCore->randomStartDoneFlag = data.value("randomStartDoneFlag", 0);\n'
    "\t\tif (Core->randomStartWarpFlag)\n"
    '\t\t\tspdlog::info("Random start: flag {} fires when player enters area {}", Core->randomStartWarpFlag, Core->randomStartAreaId);\n'
)

# ---- Core.cpp (4-tab latch; insert after the dlc latch's closing brace) ----
CORECPP_ANCHOR = _crlf(
    '\t\t\t\t\tspdlog::info("DLC auto-entry: in start area {} -> set flag {} -> warp to Gravesite Plain", pr, dlcEntryWarpFlag);\n'
    "\t\t\t\t}\n"
)
CORECPP_INS = _crlf(
    "\n"
    "\t\t\t\t// Random starting region (mirrors DLC auto-entry): on the intro Chapel, set the baked warp\n"
    "\t\t\t\t// flag ONCE -> common.emevd WarpPlayer -> the rolled start region. Persistent randomStartDoneFlag\n"
    "\t\t\t\t// guards the optional late Chapel revisit / reconnect.\n"
    "\t\t\t\tstatic bool randomStartLatched = false;\n"
    "\t\t\t\tif (randomStartWarpFlag && randomStartAreaId && randomStartDoneFlag && pr == randomStartAreaId\n"
    "\t\t\t\t\t&& !er_ap::game::GetEventFlagState((uint32_t)randomStartDoneFlag) && !randomStartLatched) {\n"
    "\t\t\t\t\trandomStartLatched = true;\n"
    "\t\t\t\t\ter_ap::game::SetEventFlag((uint32_t)randomStartDoneFlag, true);\n"
    "\t\t\t\t\ter_ap::game::SetEventFlag((uint32_t)randomStartWarpFlag, true);\n"
    '\t\t\t\t\tspdlog::info("Random start: in area {} -> set flag {} -> warp to start region", pr, randomStartWarpFlag);\n'
    "\t\t\t\t}\n"
)


def main():
    for p in (CORE_H, AI, CORE_CPP):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")
    h = _read(CORE_H)
    a = _read(AI)
    c = _read(CORE_CPP)
    changed = False
    if b"randomStartWarpFlag" not in h:
        h = _ins_after(h, COREH_ANCHOR, COREH_INS, "Core.h fields"); _write(CORE_H, h)
        print("[ok] patched Core.h"); changed = True
    else:
        print("[skip] Core.h already patched.")
    if b"randomStartWarpFlag" not in a:
        a = _ins_after(a, AI_ANCHOR, AI_INS, "ArchipelagoInterface read"); _write(AI, a)
        print("[ok] patched ArchipelagoInterface.cpp"); changed = True
    else:
        print("[skip] ArchipelagoInterface.cpp already patched.")
    if b"randomStartLatched" not in c:
        c = _ins_after(c, CORECPP_ANCHOR, CORECPP_INS, "Core.cpp latch"); _write(CORE_CPP, c)
        print("[ok] patched Core.cpp"); changed = True
    else:
        print("[skip] Core.cpp already patched.")
    print("[done] client random-start latch applied. Rebuild the client (build.ps1 -Client)." if changed
          else "[done] nothing to do.")


if __name__ == "__main__":
    main()
