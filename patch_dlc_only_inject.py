#!/usr/bin/env python3
"""
Apply the dlc_only injectable-seating fix to Archipelago/worlds/eldenring/__init__.py.

WHY THIS IS A SCRIPT (run it on Windows, not in the Cowork sandbox): the sandbox mount
serves a phantom-TRUNCATED view of this 216KB+ CRLF file (it "ends" mid fill_slot_data),
so a read-modify-write through the sandbox would destroy everything past line ~3395.
Run this with your real Python on Windows, where the file reads complete.

  cd C:\\Users\\alari\\Documents\\er-archipelago
  python patch_dlc_only_inject.py
  .\\build.ps1 -Generate     # then check precollected-to-start no longer lists DLC locks/shards

WHAT IT DOES (two coupled fixes so region_lock + the Messmer gate survive a trimmed pool):
  Fix A  Under dlc_only, only DLC-flagged mandatory injectables (DLC region locks + Messmer
         shards) compete for the limited in-world slots; base region locks are free transit
         and may spill to the start inventory harmlessly. Sizing + selection both updated.
  Fix B  Demand-restore: keep a sized reserve of the cheapest cut DLC filler locations as
         checks so create_items has freed slots to seat the DLC injectables in-world instead
         of spilling them to start (which silently disables the gating). Only as many as the
         DLC mandatory-injectable demand; leftover reserve slots just hold filler.

Safe: backs up the file, asserts every anchor matches exactly once, preserves the file's
line endings, byte-compiles the result, and refuses to write if anything is off or the file
is already patched.
"""
import os, sys, py_compile, shutil

P = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
if not os.path.exists(P):
    print(f"!! {P} not found -- run this from the repo root (er-archipelago).")
    sys.exit(1)

with open(P, "r", encoding="utf-8", newline="") as f:
    s = f.read()

# Integrity: full read (not a truncated mount view). fill_slot_data tail must be present.
for sentinel in ('"apIdsToItemIds": ap_ids_to_er_ids', "regionGraces", "def fill_slot_data"):
    if sentinel not in s:
        print(f"!! integrity check failed: '{sentinel}' missing -- refusing to write a "
              f"possibly-truncated file. Are you running this on Windows (real disk)?")
        sys.exit(2)

if "_inject_reserve_names" in s:
    print("Already patched (_inject_reserve_names present). Nothing to do.")
    sys.exit(0)

N = "\r\n" if "\r\n" in s else "\n"
orig_len = len(s)

def rep(s, old, new, label):
    c = s.count(old)
    if c != 1:
        print(f"!! {label}: expected exactly 1 anchor match, found {c}. Aborting (no write).")
        sys.exit(3)
    return s.replace(old, new)

# R1 -- init the reserve attribute at the top of generate_early
s = rep(s,
  "        self.created_regions = set()" + N,
  "        self.created_regions = set()" + N +
  "        self._inject_reserve_names = frozenset()" + N,
  "R1 init attr")

# R2 -- build the demand-restore reserve (after the dlc_only base-prereq precollect)
anchor2 = '                    self.multiworld.push_precollected(self.create_item("Dragon Heart x5"))' + N
block2 = anchor2 + (
"                # Fix B (demand-restore): keep a sized set of the cheapest cut DLC filler" + N +
"                # locations as checks so create_items has freed slots to seat the DLC region" + N +
"                # locks + Messmer shards IN-WORLD instead of spilling them to the start" + N +
"                # inventory (which silently disables region_lock + the Enir Ilim gate). Only" + N +
"                # as many as the DLC mandatory-injectable demand; leftover reserve slots just" + N +
"                # hold filler. Selected in DLC region order so early-sphere slots exist." + N +
"                if self.options.location_pool.value in (1, 2):" + N +
"                    _dlc_lock_demand = sum(" + N +
"                        1 for _n, _d in item_table.items()" + N +
"                        if getattr(_d, \"lock\", False) and getattr(_d, \"is_dlc\", False)" + N +
"                        and getattr(_d, \"inject\", False))" + N +
"                    _shard_demand = (self.options.messmer_kindle_max.value" + N +
"                                     if self.options.messmer_kindle else 1)" + N +
"                    _reserve_target = _dlc_lock_demand + _shard_demand" + N +
"                    _reserve = []" + N +
"                    for _rn in list(region_order_dlc):" + N +
"                        if len(_reserve) >= _reserve_target:" + N +
"                            break" + N +
"                        for _ld in location_tables.get(_rn, []):" + N +
"                            if len(_reserve) >= _reserve_target:" + N +
"                                break" + N +
"                            if not self._content_in_scope(_ld):" + N +
"                                continue" + N +
"                            if getattr(_ld, \"missable\", False):" + N +
"                                continue" + N +
"                            if _ld.name in self.all_excluded_locations:" + N +
"                                continue" + N +
"                            _di = item_table.get(_ld.default_item_name)" + N +
"                            if _di is None or _di.classification != ItemClassification.filler:" + N +
"                                continue" + N +
"                            if self._in_location_pool(_ld):" + N +
"                                continue" + N +
"                            _reserve.append(_ld.name)" + N +
"                    self._inject_reserve_names = frozenset(_reserve)" + N
)
s = rep(s, anchor2, block2, "R2 reserve compute")

# R3 -- _in_location_pool keeps reserve locations as checks
old3 = ("        pool = self.options.location_pool.value" + N +
        "        if pool == 0:" + N +
        "            return True" + N)
new3 = old3 + (
"        # Fix B (demand-restore): reserved cut-filler locations are kept as checks to" + N +
"        # provide freed slots for DLC injectables (see generate_early)." + N +
"        if (data.name or \"\") in getattr(self, \"_inject_reserve_names\", frozenset()):" + N +
"            return True" + N)
s = rep(s, old3, new3, "R3 inpool reserve")

# R4 -- defer list init in create_items
s = rep(s,
  "        deferred_bad_gear: List[str] = []" + N,
  "        deferred_bad_gear: List[str] = []" + N +
  "        deferred_inject_reserve: List[str] = []" + N,
  "R4 defer init")

# R5 -- create_items scan routes reserve locations to the deferred list
s = rep(s,
  "                deferred_small_runes.append(default_item_name)" + N,
  "                deferred_small_runes.append(default_item_name)" + N +
  "            elif location.name in self._inject_reserve_names:" + N +
  "                deferred_inject_reserve.append(default_item_name)" + N,
  "R5 scan branch")

# R6 -- Fix A sizing (DLC-only mandatory) + Fix B reserve drop
old6 = ("        injectable_mandatory_count = sum(" + N +
"            1 for _inj in self._all_injectable_items()" + N +
"            if _inj.classification == ItemClassification.progression" + N +
"        )" + N +
"        _shortfall = max(0, injectable_mandatory_count - num_required_extra_items)" + N +
"        _num_runes_to_skip = min(_shortfall, len(deferred_small_runes))" + N +
"        deferred_small_runes.sort(key=self._small_golden_rune_tier)" + N +
"        num_required_extra_items += _num_runes_to_skip" + N +
"        for _rune_name in deferred_small_runes[_num_runes_to_skip:]:" + N +
"            self.local_itempool.append(self.create_item(_rune_name))" + N)
new6 = ("        # Fix A: under dlc_only only DLC-flagged mandatory injectables need IN-WORLD" + N +
"        # slots; base region locks are free transit and may spill to the start inventory" + N +
"        # harmlessly, so we do not size the demand-drop to seat them." + N +
"        if self.options.dlc_only:" + N +
"            injectable_mandatory_count = sum(" + N +
"                1 for _inj in self._all_injectable_items()" + N +
"                if _inj.classification == ItemClassification.progression" + N +
"                and getattr(_inj, \"is_dlc\", False)" + N +
"            )" + N +
"        else:" + N +
"            injectable_mandatory_count = sum(" + N +
"                1 for _inj in self._all_injectable_items()" + N +
"                if _inj.classification == ItemClassification.progression" + N +
"            )" + N +
"        _shortfall = max(0, injectable_mandatory_count - num_required_extra_items)" + N +
"        _num_runes_to_skip = min(_shortfall, len(deferred_small_runes))" + N +
"        deferred_small_runes.sort(key=self._small_golden_rune_tier)" + N +
"        num_required_extra_items += _num_runes_to_skip" + N +
"        for _rune_name in deferred_small_runes[_num_runes_to_skip:]:" + N +
"            self.local_itempool.append(self.create_item(_rune_name))" + N +
"        # Fix B: still short after runes? drop reserved cut-filler items to free their" + N +
"        # slots for the DLC injectables; any not needed return to the pool as filler." + N +
"        _shortfall2 = max(0, injectable_mandatory_count - num_required_extra_items)" + N +
"        _num_reserve_to_skip = min(_shortfall2, len(deferred_inject_reserve))" + N +
"        num_required_extra_items += _num_reserve_to_skip" + N +
"        for _res_name in deferred_inject_reserve[_num_reserve_to_skip:]:" + N +
"            self.local_itempool.append(self.create_item(_res_name))" + N)
s = rep(s, old6, new6, "R6 shortfall sizing + reserve drop")

# R7 -- _create_injectable_items prioritizes DLC mandatory under dlc_only
old7 = ("        number_to_inject = min(num_required_extra_items, len(all_injectable_items))" + N +
"        inj_items = (" + N +
"            self.random.sample(" + N +
"                injectable_mandatory," + N +
"                k=min(len(injectable_mandatory), number_to_inject)" + N +
"            )" + N +
"            + self.random.sample(" + N +
"                injectable_optional," + N +
"                k=max(0, number_to_inject - len(injectable_mandatory))" + N +
"            )" + N +
"        )" + N)
new7 = ("        number_to_inject = min(num_required_extra_items, len(all_injectable_items))" + N +
"        # Fix A: under dlc_only, prioritize DLC-flagged mandatory injectables (DLC region" + N +
"        # locks + Messmer shards) for the limited in-world slots; base locks lose the tie" + N +
"        # and spill to the start inventory below (harmless -- base is free transit here)." + N +
"        if self.options.dlc_only:" + N +
"            _dlc_mand = [it for it in injectable_mandatory if getattr(it, \"is_dlc\", False)]" + N +
"            _base_mand = [it for it in injectable_mandatory if not getattr(it, \"is_dlc\", False)]" + N +
"            self.random.shuffle(_dlc_mand)" + N +
"            self.random.shuffle(_base_mand)" + N +
"            _ordered_mand = _dlc_mand + _base_mand" + N +
"            _chosen_mand = _ordered_mand[:min(len(_ordered_mand), number_to_inject)]" + N +
"        else:" + N +
"            _chosen_mand = self.random.sample(" + N +
"                injectable_mandatory," + N +
"                k=min(len(injectable_mandatory), number_to_inject)" + N +
"            )" + N +
"        inj_items = (" + N +
"            _chosen_mand" + N +
"            + self.random.sample(" + N +
"                injectable_optional," + N +
"                k=max(0, number_to_inject - len(injectable_mandatory))" + N +
"            )" + N +
"        )" + N)
s = rep(s, old7, new7, "R7 inject select")

# Backup, write (preserving line endings), verify on disk
bak = P + ".bak_dlcinject"
shutil.copy2(P, bak)
with open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)

# Verify: still has the tail, has the new code, and byte-compiles
with open(P, "r", encoding="utf-8", newline="") as f:
    chk = f.read()
ok = all(x in chk for x in ("_inject_reserve_names", "deferred_inject_reserve",
                            "regionGraces", "def fill_slot_data"))
if not ok:
    print("!! post-write sanity failed; restoring backup.")
    shutil.copy2(bak, P)
    sys.exit(4)
try:
    py_compile.compile(P, doraise=True)
except py_compile.PyCompileError as e:
    print("!! byte-compile FAILED; restoring backup.\n", e)
    shutil.copy2(bak, P)
    sys.exit(5)

# Purge stale bytecode so the next gen recompiles from source
for root, _dirs, files in os.walk(os.path.join("Archipelago", "worlds", "eldenring")):
    if os.path.basename(root) == "__pycache__":
        for fn in files:
            try: os.remove(os.path.join(root, fn))
            except OSError: pass

print(f"OK: patched {P} ({orig_len} -> {len(s)} chars, +{len(s)-orig_len}). "
      f"Backup at {bak}. Bytecode purged. Run: .\\build.ps1 -Generate")
