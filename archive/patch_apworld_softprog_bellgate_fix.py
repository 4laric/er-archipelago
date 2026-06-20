#!/usr/bin/env python3
r"""patch_apworld_softprog_bellgate_fix.py

Fix the soft_progression x smithing_bell_bearing_option contradiction that makes
Capital / Elden-Beast seeds report "Game appears as unbeatable" even though fill succeeds.

ROOT CAUSE
----------
  * soft_progression (true) demotes EVERY item whose name contains "Bell Bearing" --
    including the Progressive Smithing / Somberstone Miner's Bell Bearing items --
    from `progression` to `useful` (__init__.py ~L309-313).
  * smithing_bell_bearing_option defaults to `progression_randomize` (value 1), which
    adds ENTRANCE RULES gating Altus Plateau / Capital Outskirts / Flame Peak / Farum
    Azula on exactly those bell bearings (__init__.py L2084-2094). Capital Outskirts is
    the ONLY route to Leyndell -> Morgott.
  * Main.py's post-fill can_beat_game() collects only `advancement` items, so it never
    picks up the now-`useful` bells -> the Capital Outskirts gate can never open ->
    the goal is unreachable -> FillError("Game appears as unbeatable").
  * fill_restrictive precollects `useful`/`filler` items into its base sweep state, so
    fill itself still passes -- hence the tell-tale "fill OK / unbeatable" split.

This is not num_regions-specific: any soft_progression seed that must path through
Capital Outskirts hits it. A num_regions seal just makes that the only path, so it
becomes fatal instead of merely shrinking the reachable set.

THE FIX
-------
Only apply the smithing-bell entrance gates when the bells are actually progression --
i.e. skip them when soft_progression has demoted them. The progression-randomize feature
is preserved untouched for seeds that do NOT run soft_progression (their bells stay
progression and the gate works as designed).

    -    if self.options.smithing_bell_bearing_option.value == 1:
    +    if self.options.smithing_bell_bearing_option.value == 1 and not self.options.soft_progression.value:

Run on Windows from the repo root (or the eldenring apworld dir):
    python patch_apworld_softprog_bellgate_fix.py

CRLF-safe byte splice; idempotent (re-running is a no-op once applied). Only the
L2084 ENTRANCE-RULE block is touched -- the identical-looking L285 item-classification
promotion block is left alone (it is anchored by the unique '# Smithing bell bearing
rules' comment on the preceding line).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [
    HERE,
    os.path.join(HERE, "Archipelago", "worlds", "eldenring"),
    os.getcwd(),
]
PKG = next((d for d in CANDIDATES if os.path.exists(os.path.join(d, "__init__.py"))
            and os.path.exists(os.path.join(d, "region_spine.py"))), None)
if not PKG:
    sys.exit("ERROR: could not find the eldenring apworld dir (need __init__.py + region_spine.py).")


def _nl(b: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in b else b"\n"


def _conv(text: str, nl: bytes) -> bytes:
    return text.replace("\n", nl.decode("ascii")).encode("utf-8")


# The unique anchor (comment line guarantees we hit the L2084 entrance-rule block, not the
# identical-looking L285 classification block). We replace the bare `== 1:` guard with a guard
# that also requires soft_progression to be OFF.
OLD = (
    "        # Smithing bell bearing rules\n"
    "        if self.options.smithing_bell_bearing_option.value == 1:\n"
)
NEW = (
    "        # Smithing bell bearing rules\n"
    "        # soft_progression demotes ALL \"Bell Bearing\" items (incl. the Progressive Smithing /\n"
    "        # Somberstone bells) progression -> useful (see ~L309). These entrance rules gate Altus /\n"
    "        # Capital Outskirts / Flame Peak / Farum on those bells, but can_beat_game() collects only\n"
    "        # 'advancement' items -- so once demoted the gate is unsatisfiable and the seed reports\n"
    "        # \"unbeatable\" (fill precollects useful items and still passes: the fill-OK/unbeatable\n"
    "        # split). The progression-randomize feature only makes sense while the bells stay\n"
    "        # progression, so skip the gate when soft_progression has pulled them down to useful.\n"
    "        # (patch_apworld_softprog_bellgate_fix.py)\n"
    "        if self.options.smithing_bell_bearing_option.value == 1 and not self.options.soft_progression.value:\n"
)
MARKER = "smithing_bell_bearing_option.value == 1 and not self.options.soft_progression.value"


def main():
    p = os.path.join(PKG, "__init__.py")
    with open(p, "rb") as f:
        b = f.read()
    nl = _nl(b)
    _nlname = "CRLF" if nl == b"\r\n" else "LF"
    print("Patching: %s  (newline=%s)" % (p, _nlname))

    if _conv(MARKER, nl) in b or MARKER.encode("utf-8") in b:
        print("  [skip] already patched (soft_progression guard present).")
        sys.exit(0)

    old = _conv(OLD, nl)
    new = _conv(NEW, nl)
    n = b.count(old)
    if n != 1:
        print(f"  [FAIL] expected exactly 1 occurrence of the anchor, found {n}. NOT modified.")
        print("         (Has the file changed? The anchor is the '# Smithing bell bearing rules'")
        print("          comment immediately followed by the `== 1:` guard.)")
        sys.exit(1)

    out = b.replace(old, new, 1)
    with open(p, "wb") as f:
        f.write(out)
    print("  [ok]   guarded the smithing-bell entrance gate with `not soft_progression`.")
    print("DONE")
    sys.exit(0)


if __name__ == "__main__":
    main()
