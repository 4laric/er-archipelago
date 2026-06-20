#!/usr/bin/env python3
r"""
patch_apworld_global_scadu_blessing.py  (run on Windows, in the repo root)

P1 apworld half of SPEC-global-scadutree-blessing.md. Adds the option
`global_scadutree_blessing` (DEFAULT OFF) and emits it in slot_data so the runtime
client can turn Scadutree Fragments into a game-wide Scadutree Blessing power curve.

  off (0)          -> vanilla; fragments do nothing outside the DLC. (default)
  player_only (1)  -> client applies the blessing globally to the player.
  scaled (2)       -> same player apply; meant to pair with completion_scaling lifted
                      into the DLC tier band (enemy side is a later baker change).
                      Behaves like player_only on the client for now.

Purely additive + the client reads it contains-guarded, so this is backward compatible;
the slot_data "versions" contract is intentionally NOT bumped here (see note at the end).

Edits (idempotent, CRLF-safe, makes .bak):
  - worlds/eldenring/options.py    : new GlobalScadutreeBlessing(Choice) + EROptions field
  - worlds/eldenring/__init__.py   : slot_data["options"]["global_scadutree_blessing"]

Pairs with patch_client_global_scadu_blessing.py (the client half).
"""
import os, sys, shutil

REPO = os.path.dirname(os.path.abspath(__file__))
ED   = os.path.join(REPO, "Archipelago", "worlds", "eldenring")
OPTIONS = os.path.join(ED, "options.py")
INIT    = os.path.join(ED, "__init__.py")


def load(path):
    if not os.path.isfile(path):
        sys.exit(f"ERROR: not found: {path}")
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def nl_of(text):
    return "\r\n" if "\r\n" in text else "\n"


def insert_after(text, anchor_line, new_lines, path):
    """anchor_line / new_lines are given WITHOUT terminators; terminator is auto-detected."""
    nl = nl_of(text)
    anchor = anchor_line + nl
    if text.count(anchor) != 1:
        sys.exit(f"ERROR in {os.path.basename(path)}: anchor not unique "
                 f"({text.count(anchor)}x): {anchor_line!r}")
    block = "".join(l + nl for l in new_lines)
    return text.replace(anchor, anchor + block, 1)


def insert_before(text, anchor_block_lines, new_lines, path):
    nl = nl_of(text)
    anchor = "".join(l + nl for l in anchor_block_lines)
    if text.count(anchor) != 1:
        sys.exit(f"ERROR in {os.path.basename(path)}: block anchor not unique "
                 f"({text.count(anchor)}x): {anchor_block_lines!r}")
    block = "".join(l + nl for l in new_lines)
    return text.replace(anchor, block + anchor, 1)


def save(path, text):
    shutil.copy2(path, path + ".bak_globalscadu")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    # verify round-trips on disk (mount truncation guard)
    with open(path, "r", encoding="utf-8", newline="") as f:
        back = f.read()
    if back != text:
        sys.exit(f"ERROR: write-back mismatch on {path} (truncation?). Restore the .bak.")
    print(f"  patched: {os.path.relpath(path, REPO)}  (.bak_globalscadu written)")


# ---- options.py -----------------------------------------------------------------------
opt = load(OPTIONS)
if "class GlobalScadutreeBlessing" in opt:
    print("options.py already has GlobalScadutreeBlessing; skipping.")
else:
    option_class = [
        "class GlobalScadutreeBlessing(Choice):",
        '    """EXPERIMENTAL (default off). Turn Scadutree Fragments into a GAME-WIDE power curve.',
        "    The runtime client counts how many Scadutree Fragments you hold, converts that to a",
        "    Scadutree Blessing level via the vanilla cost curve, and writes the game's stored blessing",
        "    level so the DLC blessing buff applies ANYWHERE -- not just the Land of Shadow. See",
        "    SPEC-global-scadutree-blessing.md.",
        "",
        "    - off:         vanilla. Fragments do nothing outside the DLC.",
        "    - player_only: apply the player blessing globally (enemies untouched). Power fantasy /",
        "                   accessibility knob.",
        "    - scaled:      same player apply; intended to pair with completion_scaling lifted into the",
        "                   DLC enemy-tier band (enemy side is a separate, later baker change). On the",
        "                   client this currently behaves like player_only; the value is shipped so",
        '                   seeds can opt in ahead of the enemy-side work."""',
        '    display_name = "Global Scadutree Blessing"',
        "    option_off = 0",
        "    option_player_only = 1",
        "    option_scaled = 2",
        "    default = 0",
        "",
    ]
    opt = insert_before(
        opt,
        ["@dataclass", "class EROptions(PerGameCommonOptions):"],
        option_class,
        OPTIONS,
    )
    opt = insert_after(
        opt,
        "    completion_scaling_basis: CompletionScalingBasis",
        ["    global_scadutree_blessing: GlobalScadutreeBlessing"],
        OPTIONS,
    )
    save(OPTIONS, opt)


# ---- __init__.py (slot_data emission) -------------------------------------------------
ini = load(INIT)
if '"global_scadutree_blessing"' in ini:
    print("__init__.py already emits global_scadutree_blessing; skipping.")
else:
    ini = insert_after(
        ini,
        '                "completion_scaling_floor": self.options.completion_scaling_floor.value,',
        ['                "global_scadutree_blessing": self.options.global_scadutree_blessing.value,'],
        INIT,
    )
    save(INIT, ini)


print("""
DONE (apworld half).

Next:
  1) python patch_client_global_scadu_blessing.py   (the client half)
  2) .\\build.ps1 -Generate                          (gen-test: default off = no change)
  3) set global_scadutree_blessing: player_only in a yaml to exercise it.

NOTE on the slot_data version contract: this key is additive and the client reads it
contains-guarded (missing => off), so beta.4 is left unchanged. If you'd rather keep the
per-build lockstep convention, bump "versions" in __init__.py + the randomizer + client
together; it is not required for this default-off, backward-compatible option.
""")
