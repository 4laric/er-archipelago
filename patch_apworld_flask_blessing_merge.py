#!/usr/bin/env python3
"""HARD-MERGE flask_upgrade_option + blessing_option into important_locations (pre-1.0, no users).

Their THREE modes collapse:
  - randomize          -> default (items shuffled; their locations are normal checks).
  - to_important       -> just list Seedtree/Church (flasks) / Fragment/Revered (blessings) in
                          important_locations. The default important_locations now includes all
                          four, so the old blessing default (to_important) is preserved.
  - do_not_randomize   -> new `vanilla_upgrades: OptionSet {flasks, blessings}` (lock at vanilla).

Deletes FlaskUpgradeOption + BlessingOption; adds VanillaUpgrades; adds Fragment/Revered to the
important_locations default; rewires generate_early + _fill_local_items; DROPS the two slot_data
"options" keys. Migration: `flask_upgrade_option: to_important` -> (already default);
`... do_not_randomize` -> `vanilla_upgrades: [flasks]`; blessing equivalents with [blessings].

Conventions: byte-level, CRLF-preserving, idempotent, py_compiles each file before writing,
.bak_fbmerge backups, aborts cleanly if any anchor drifted.

CAVEATS to verify on Windows:
 * Adding Fragment/Revered to the important_locations DEFAULT changes behavior ONLY for DLC seeds
   that previously set blessing_option: randomize (they now prioritize fragment/revered). Remove
   them from important_locations to opt out.
 * slot_data drops "flask_upgrade_option"/"blessing_option" -- grep the C# randomizer + C++ client
   + baker for those keys first; they are fill-time concepts and almost certainly unread.
"""
import os, sys, py_compile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OPTIONS = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "options.py")
INIT = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "__init__.py")

# ---------------- options.py ----------------
OPT_A_OLD = '''class FlaskUpgradeOption(Choice):
    """How to handle flask upgrades -- Golden Seeds (flask charges) and Sacred Tears (flask
    potency).

    - **Randomize:** shuffled into the pool; their locations are normal checks.
    - **To Important Locations:** their locations are forced to hold progression items
      (same effect as listing Seedtree/Church in important_locations).
    - **Do Not Randomize:** Golden Seeds and Sacred Tears stay at their vanilla locations
      (this overrides important_locations for those classes).
    """
    display_name = "Flask Upgrade Handling"
    option_randomize = 0
    option_to_important = 1
    option_do_not_randomize = 2
    default = 0'''
OPT_A_NEW = '''class VanillaUpgrades(OptionSet):
    """Lock upgrade-item families at their VANILLA locations -- removes them from the randomized
    pool and overrides important_locations for those classes. Replaces the old
    flask_upgrade_option / blessing_option "do not randomize" modes.

      flasks    -- Golden Seeds (flask charges) + Sacred Tears (flask potency) stay vanilla.
      blessings -- Scadutree Fragments + Revered Spirit Ashes stay vanilla (DLC only; ignored off).

    Empty (default) = everything is randomized. To instead FORCE these to hold progression, list
    Seedtree / Church / Fragment / Revered in important_locations (the default already does all 4)."""
    display_name = "Vanilla Upgrades (lock at vanilla)"
    valid_keys = {"flasks", "blessings"}'''

OPT_B_OLD = '''class BlessingOption(Choice):
    """How to handle Shadow Realm blessings -- Scadutree Fragments and Revered Spirit Ashes
    (DLC only; ignored when the DLC is off).

    - **Randomize:** shuffled into the pool; their locations are normal checks.
    - **To Important Locations:** their locations are forced to hold progression items
      (same effect as listing Fragment/Revered in important_locations).
    - **Do Not Randomize:** blessings stay at their vanilla locations (overrides
      important_locations for those classes).
    """
    display_name = "Shadow Realm Blessing Handling"
    option_randomize = 0
    option_to_important = 1
    option_do_not_randomize = 2
    # default to_important: Scadutree Fragments + Revered Ashes are priority when DLC is on
    default = 1'''

OPT_D_OLD = '''    default = ["Remembrance", "Seedtree", "Church", "Boss"]'''
OPT_D_NEW = '''    default = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"]'''

OPT_E_OLD = '''    torrent_start: TorrentStart
    flask_upgrade_option: FlaskUpgradeOption
    blessing_option: BlessingOption
    soft_progression: SoftProgression'''
OPT_E_NEW = '''    torrent_start: TorrentStart
    vanilla_upgrades: VanillaUpgrades
    soft_progression: SoftProgression'''

OPT_F_OLD = '''        MissableLocationBehaviorOption,
        FlaskUpgradeOption,
        MerchantBellLogic,'''
OPT_F_NEW = '''        MissableLocationBehaviorOption,
        VanillaUpgrades,
        MerchantBellLogic,'''

OPT_G_OLD = '''        MessmerKindleMax,
        BlessingOption,
    ]),'''
OPT_G_NEW = '''        MessmerKindleMax,
    ]),'''

OPTIONS_EDITS = [
    ("sub", OPT_A_OLD, OPT_A_NEW, "class VanillaUpgrades(OptionSet):"),
    ("del", OPT_B_OLD, "class BlessingOption(Choice):"),
    ("sub", OPT_D_OLD, OPT_D_NEW, '"Boss", "Fragment", "Revered"]'),
    ("sub", OPT_E_OLD, OPT_E_NEW, "vanilla_upgrades: VanillaUpgrades"),
    ("sub", OPT_F_OLD, OPT_F_NEW, "        VanillaUpgrades,"),
    ("sub", OPT_G_OLD, OPT_G_NEW, "        MessmerKindleMax,\n    ]),"),
]

# ---------------- __init__.py ----------------
INIT_H_OLD = '''        # Dedicated tri-state options can also push a class to priority ("to important").
        if self.options.flask_upgrade_option.value == 1:
            selected_priority_classes += ["seedtree", "church"]
        if self.options.blessing_option.value == 1 and dlc:
            selected_priority_classes += ["fragment", "revered"]'''
INIT_H_NEW = '''        # flask_upgrade_option / blessing_option were merged away: their "to important" behavior is
        # now just listing Seedtree/Church/Fragment/Revered in important_locations (the default
        # includes all four). "do not randomize" -> vanilla_upgrades (below + in _fill_local_items).'''

INIT_I_OLD = '''        if self.options.flask_upgrade_option.value == 2 or (self.options.blessing_option.value == 2 and dlc):
            for locations in location_tables.values():
                for loc in locations:
                    if self.options.flask_upgrade_option.value == 2 and (loc.seedtree or loc.church):
                        self.all_priority_locations.discard(loc.name)
                    if self.options.blessing_option.value == 2 and dlc and (loc.fragment or loc.revered):
                        self.all_priority_locations.discard(loc.name)'''
INIT_I_NEW = '''        _vu = self.options.vanilla_upgrades.value
        if ("flasks" in _vu) or ("blessings" in _vu and dlc):
            for locations in location_tables.values():
                for loc in locations:
                    if "flasks" in _vu and (loc.seedtree or loc.church):
                        self.all_priority_locations.discard(loc.name)
                    if "blessings" in _vu and dlc and (loc.fragment or loc.revered):
                        self.all_priority_locations.discard(loc.name)'''

INIT_J_OLD = '''        # Flask upgrades / blessings -> lock at vanilla when do_not_randomize.
        if self.options.flask_upgrade_option.value == 2:
            self._lock_class_at_vanilla(lambda d: d.seedtree or d.church)
        if self.options.blessing_option.value == 2 and self.options.enable_dlc:
            self._lock_class_at_vanilla(lambda d: d.fragment or d.revered)'''
INIT_J_NEW = '''        # vanilla_upgrades: lock these families at their vanilla locations (was flask_upgrade_option
        # / blessing_option == do_not_randomize).
        _vu = self.options.vanilla_upgrades.value
        if "flasks" in _vu:
            self._lock_class_at_vanilla(lambda d: d.seedtree or d.church)
        if "blessings" in _vu and self.options.enable_dlc:
            self._lock_class_at_vanilla(lambda d: d.fragment or d.revered)'''

INIT_K_OLD = '''                "flask_upgrade_option": self.options.flask_upgrade_option.value,
                "blessing_option": self.options.blessing_option.value,
'''

INIT_EDITS = [
    ("sub", INIT_H_OLD, INIT_H_NEW, 'flask_upgrade_option / blessing_option were merged away'),
    ("sub", INIT_I_OLD, INIT_I_NEW, 'if ("flasks" in _vu) or ("blessings" in _vu and dlc):'),
    ("sub", INIT_J_OLD, INIT_J_NEW, 'vanilla_upgrades: lock these families at their vanilla locations'),
    ("del", INIT_K_OLD, '"flask_upgrade_option": self.options.flask_upgrade_option.value,'),
]

def apply_edits(text, edits):
    for edit in edits:
        kind = edit[0]
        if kind == "sub":
            _, old, new, marker = edit
            if old in text:
                c = text.count(old)
                if c != 1:
                    raise SystemExit(f"ABORT: anchor appears {c}x (expected 1): {marker!r}")
                text = text.replace(old, new, 1)
            elif marker in text:
                print(f"  [skip] already applied: {marker[:48]!r}")
            else:
                raise SystemExit(f"ABORT: anchor NOT FOUND and not already applied: {marker[:48]!r}")
        elif kind == "del":
            _, old, sig = edit
            if old in text:
                c = text.count(old)
                if c != 1:
                    raise SystemExit(f"ABORT: del-anchor appears {c}x (expected 1): {sig!r}")
                text = text.replace(old, "", 1)
            elif sig in text:
                raise SystemExit(f"ABORT: del-anchor drifted: {sig!r}")
            else:
                print(f"  [skip] already removed: {sig!r}")
    return text

def patch_file(path, edits):
    raw = open(path, "rb").read()
    total = raw.count(b"\n"); eol_crlf = raw.count(b"\r\n") == total and total > 0
    work = raw.decode("utf-8").replace("\r\n", "\n") if eol_crlf else raw.decode("utf-8")
    new_work = apply_edits(work, edits)
    if new_work == work:
        print(f"  {os.path.basename(path)}: no change (already merged)."); return
    out = (new_work.replace("\n", "\r\n") if eol_crlf else new_work).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(path + ".bak_fbmerge", "wb").write(raw)
    open(path, "wb").write(out)
    print(f"  {os.path.basename(path)}: patched ({'CRLF' if eol_crlf else 'LF'}); backup .bak_fbmerge")

def main():
    for p in (OPTIONS, INIT):
        if not os.path.isfile(p):
            print("ERROR not found:", p); return 1
    print("patching options.py ..."); patch_file(OPTIONS, OPTIONS_EDITS)
    print("patching __init__.py ..."); patch_file(INIT, INIT_EDITS)
    print("done. Re-gen; lint with: python er_yaml_lint.py Archipelago\\Players")
    return 0

if __name__ == "__main__":
    sys.exit(main())
