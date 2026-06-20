#!/usr/bin/env python3
"""
patch_baker_kick_kill_keep_runes.py -- region-lock enforcement: KILL the player (no rune loss)
instead of warping them out.

When the player crosses into a still-locked region, the client sets KICK_FLAG (76970) every tick
and the baked common.emevd reactor (RegionFogGates.Apply, USE_PLAY_REGION_KICK branch) reacts.
Today that reactor WarpPlayers the player back to a safe Limgrave grace (KICK_WARP=true). Alaric
wants cosmetic/polish behaviour instead: the player simply DIES on breaking the lock, but keeps
their runes (no bloodstain / no penalty).

Mechanism: EMEVD 2004[4] Force Character Death (Entity ID, Should Receive Runes: BOOL). The reactor
already has a kill branch -- it just (a) wasn't selected (KICK_WARP=true) and (b) passed
Should Receive Runes = FALSE (diagnostic kill -> normal death penalty, runes drop). This patch:
  1. KICK_WARP true -> false        (select the kill branch instead of the warp)
  2. kill arg (byte)0 -> (byte)1    (Should Receive Runes = TRUE -> player keeps runes)

Confirmed against er-common.emedf.json: every vanilla ForceCharacterDeath passes FALSE for scripted
ENEMY removals (no rune award); TRUE (the EMEDF default) on a player death means the death awards/
keeps the player's runes -- i.e. no loss. The existing "[kill]" log line is reached automatically
once KICK_WARP is false.

NOTE (residual): a pure kill respawns the player at their LAST grace. Crossing a region border, that
grace is on the unlocked side in virtually all cases, so no death loop. If you ever rested at a grace
INSIDE a locked region you could re-die on respawn -- flip KICK_WARP back to true to restore the
warp-out fallback. The client-side kickLatched re-arm + the reactor's 1s debounce are unchanged.

Target: SoulsRandomizers/RandomizerCommon/RegionFogGates.cs (LF). Idempotent. Run on Windows, then
rebuild SoulsRandomizers (Release) and re-bake. No client rebuild needed (flag protocol unchanged).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "RegionFogGates.cs")

# (description, old, new) -- each `old` must occur exactly once.
EDITS = [
    (
        "select kill branch (KICK_WARP false)",
        "        private const bool KICK_WARP = true;",
        "        private const bool KICK_WARP = false;  // Alaric 2026-06-19: kill-keep-runes enforcement (break lock => die, no rune loss). Flip back to true to restore warp-out.",
    ),
    (
        "kill keeps runes (Should Receive Runes = TRUE)",
        "ki.Add(new EMEVD.Instruction(2004, 4, new List<object> { (uint)PLAYER, (byte)0 }));              // Force Character Death(player)",
        "ki.Add(new EMEVD.Instruction(2004, 4, new List<object> { (uint)PLAYER, (byte)1 }));              // Force Character Death(player) -- Should Receive Runes=TRUE => keep runes (no bloodstain)",
    ),
]


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)

    with open(TARGET, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    if "\r\n" in text:
        sys.exit("ERROR: %s has CRLF line endings; expected LF. Aborting to avoid corruption." % TARGET)

    already = all(new in text for _, _, new in EDITS)
    if already and all(old not in text for _, old, _ in EDITS):
        print("Already patched (kill-keep-runes); nothing to do.")
        return

    for desc, old, new in EDITS:
        if new in text and old not in text:
            print("  [skip] %s -- already applied" % desc)
            continue
        n = text.count(old)
        if n != 1:
            sys.exit("ERROR: anchor for '%s' found %d times (expected 1). Aborting." % (desc, n))
        text = text.replace(old, new, 1)
        print("  [ok]   %s" % desc)

    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(text)

    # Verify on disk (per CRLF/truncation lessons): re-read and assert.
    with open(TARGET, "r", encoding="utf-8", newline="") as f:
        chk = f.read()
    for desc, old, new in EDITS:
        assert new in chk and old not in chk, "VERIFY FAILED: %s" % desc
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: rebuild SoulsRandomizers (Release) and re-bake. No client rebuild needed.")


if __name__ == "__main__":
    main()
