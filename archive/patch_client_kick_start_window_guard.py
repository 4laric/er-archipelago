#!/usr/bin/env python3
"""
patch_client_kick_start_window_guard.py -- stop the region-lock KICK from killing the player on the
new-game spawn in Limgrave.

WHY: This seed is world_logic=region_lock + random_start_region=overworld + start_region_freebie=hub_only.
Under hub_only the rolled hub is NOT Limgrave, so the apworld maps "Limgrave" -> "Limgrave Lock"
(__init__.py ~L4570) and Limgrave (area 61000-61001) goes into slot_data areaLockFlags as a LOCKED
region. On a fresh save the player transiently spawns in Limgrave (Stranded Graveyard -> First Step)
BEFORE the baked random-start warp pulls them to the rolled hub. The Core.cpp region-lock poll sees
locked Limgrave and sets KICK_FLAG (76970); with kill-keep-runes enforcement (patch_baker_kick_kill_
keep_runes.py, KICK_WARP=false) the baked reactor then KILLS the player. Net: "spawning in Limgrave
start kills you."

FIX (minimal, client-only): gate the KICK arm on a start-window guard. Don't enforce until the
random-start warp has fired -- i.e. until randomStartDoneFlag is set. Once it's set (persistent), the
player is already in the OPEN rolled hub, so enforcement arms normally for the rest of the run.
  - Non-random seeds: randomStartDoneFlag == 0  -> guard is always true -> behaviour UNCHANGED.
  - Random-start seeds: KICK suppressed during the transient Limgrave spawn, then armed post-warp.

Target: Dark-Souls-III-Archipelago-client/archipelago-client/Core.cpp (CRLF + TAB-indented).
Byte-level replace to preserve CRLF (the Edit tool truncates CRLF source). Idempotent; verifies on
disk. Run on Windows, then rebuild the client (build.ps1 -Client). No apworld/baker/regen needed
(flag protocol unchanged).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "Dark-Souls-III-Archipelago-client", "archipelago-client", "Core.cpp")

# Exact current line (4 tabs, CRLF). Replaced with a start-window-gated version.
OLD = (
    "\t\t\t\telse if (!kickLatched) { kickLatched = true; er_ap::game::SetEventFlag(76970, true); }"
)
NEW = (
    "\t\t\t\t// Start-window guard (Alaric 2026-06-20): on a random-start seed the player transiently\r\n"
    "\t\t\t\t// spawns in (locked) Limgrave before the baked warp pulls them to the rolled hub; the\r\n"
    "\t\t\t\t// kill-keep-runes enforcement would kill them on that spawn. Don't arm the KICK until the\r\n"
    "\t\t\t\t// random-start warp has fired (randomStartDoneFlag set). Non-random seeds: done flag 0 =>\r\n"
    "\t\t\t\t// guard always true => behaviour unchanged.\r\n"
    "\t\t\t\telse if (!kickLatched\r\n"
    "\t\t\t\t\t&& (randomStartDoneFlag == 0\r\n"
    "\t\t\t\t\t\t|| er_ap::game::GetEventFlagState((uint32_t)randomStartDoneFlag))) {\r\n"
    "\t\t\t\t\tkickLatched = true; er_ap::game::SetEventFlag(76970, true);\r\n"
    "\t\t\t\t}"
)

SENTINEL = b"Start-window guard (Alaric 2026-06-20)"


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)

    with open(TARGET, "rb") as f:
        data = f.read()

    if SENTINEL in data:
        print("Already patched (start-window guard); nothing to do.")
        return

    old_b = OLD.encode("utf-8")
    new_b = NEW.encode("utf-8")

    n = data.count(old_b)
    if n != 1:
        sys.exit("ERROR: anchor found %d times (expected 1). Aborting; no write." % n)

    out = data.replace(old_b, new_b, 1)

    # Length sanity (guard against silent truncation): out should grow by exactly the delta.
    if len(out) != len(data) - len(old_b) + len(new_b):
        sys.exit("ERROR: unexpected length after replace. Aborting; no write.")

    with open(TARGET, "wb") as f:
        f.write(out)

    # Verify on disk.
    with open(TARGET, "rb") as f:
        chk = f.read()
    assert SENTINEL in chk, "VERIFY FAILED: sentinel missing after write"
    assert chk.count(b"er_ap::game::SetEventFlag(76970, true)") == 1, \
        "VERIFY FAILED: expected exactly one KICK setter"
    assert old_b not in chk, "VERIFY FAILED: old anchor still present"
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: rebuild the client (build.ps1 -Client). No apworld/baker/regen needed.")


if __name__ == "__main__":
    main()
