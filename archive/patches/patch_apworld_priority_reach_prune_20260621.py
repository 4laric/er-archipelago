#!/usr/bin/env python3
# patch_apworld_priority_reach_prune_20260621.py  (run on Windows from repo root)
#
# Make the PRIORITY (important_locations) set reachability-aware. A location marked PRIORITY that
# is unreachable even under the max-item state can never hold a progression item, so AP's priority
# fill deadlocks: "No more spots to place N items. Remaining locations are invalid." (Fill.py
# distribute_items_restrictive -> Priority Retry, "Already placed 0"). Observed on region_lock +
# num_regions + warp with randomize_enia ON (default): the Radahn remembrance boss-drop (Wailing
# Dunes, festival-gated) and any sealed-region priority slot are forced as priority but never
# reachable. This prunes such locations back to DEFAULT in pre_fill (rules built + chain
# breadcrumbs placed, so get_all_state is accurate), leaving only satisfiable priority slots.
# Idempotent; aborts if an anchor moved. Repackage the apworld + gen-test the failing seeds.

import sys, io, os
DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "_prune_unreachable_priority"

METHOD_ANCHOR = "    def pre_fill(self) -> None: #MARK: Pre-fill"
METHOD_BLOCK = (
'    def _prune_unreachable_priority(self) -> None:\n'
'        """Reachability-aware PRIORITY prune (patch priority_reach_prune). A location marked\n'
'        PRIORITY that is unreachable even under the max-item state can never hold a progression\n'
'        item, so AP\'s priority fill dies ("No more spots ... Remaining locations are invalid",\n'
'        Priority Retry, "Already placed 0"). Demote such locations to DEFAULT so only satisfiable\n'
'        priority slots remain. Fixes randomize_enia=on + region_lock + warp stranding the Radahn\n'
'        (festival-gated Wailing Dunes) remembrance boss-drop and any sealed-region priority slot.\n'
'        Runs from pre_fill (rules built + chain breadcrumbs placed) so get_all_state is accurate."""\n'
'        if not getattr(self, "all_priority_locations", None):\n'
'            return\n'
'        try:\n'
'            _state = self.multiworld.get_all_state(False)\n'
'        except Exception as _e:\n'
'            warning(f"{self.player_name}: priority reach-prune skipped (get_all_state failed: {_e}).")\n'
'            return\n'
'        _pruned = []\n'
'        for _loc in self.multiworld.get_locations(self.player):\n'
'            if _loc.progress_type == LocationProgressType.PRIORITY and not _loc.can_reach(_state):\n'
'                _loc.progress_type = LocationProgressType.DEFAULT\n'
'                self.all_priority_locations.discard(_loc.name)\n'
'                _pruned.append(_loc.name)\n'
'        if _pruned:\n'
'            warning(f"{self.player_name}: priority reach-prune demoted {len(_pruned)} unreachable "\n'
'                    f"PRIORITY location(s) to DEFAULT (e.g. {_pruned[0]}).")\n'
'\n'
'    def pre_fill(self) -> None: #MARK: Pre-fill'
)

RET_ANCHOR = (
'        if not getattr(self, "_num_regions_chain", False):\n'
'            return\n'
'        _order = getattr(self, "_num_regions_chain_order", [])\n'
'        if not _order:\n'
'            return'
)
RET_BLOCK = (
'        if not getattr(self, "_num_regions_chain", False):\n'
'            self._prune_unreachable_priority()\n'
'            return\n'
'        _order = getattr(self, "_num_regions_chain_order", [])\n'
'        if not _order:\n'
'            self._prune_unreachable_priority()\n'
'            return'
)

END_ANCHOR = (
'            _host.place_locked_item(self.create_item(_lock_name))\n'
'\n'
'\n'
'    def set_rules(self) -> None: #MARK: Rules'
)
END_BLOCK = (
'            _host.place_locked_item(self.create_item(_lock_name))\n'
'        self._prune_unreachable_priority()\n'
'\n'
'\n'
'    def set_rules(self) -> None: #MARK: Rules'
)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path); return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if "def _prune_unreachable_priority" in body:
        print("ALREADY APPLIED -- no change."); return 0
    for tag, anc in (("method", METHOD_ANCHOR), ("returns", RET_ANCHOR), ("end", END_ANCHOR)):
        if body.count(anc) != 1:
            print("ERROR: anchor %s found %d (expected 1). Aborting." % (tag, body.count(anc))); return 3
    body = body.replace(METHOD_ANCHOR, METHOD_BLOCK, 1)
    body = body.replace(RET_ANCHOR, RET_BLOCK, 1)
    body = body.replace(END_ANCHOR, END_BLOCK, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    chk = out.replace("\r\n", "\n")
    ok = (chk.count("def _prune_unreachable_priority") == 1
          and chk.count("self._prune_unreachable_priority()") == 3)
    print("APPLIED." if ok else "WROTE but verify FAILED -- inspect.")
    print("  prune calls wired:", chk.count("self._prune_unreachable_priority()"), "(expect 3)")
    return 0 if ok else 5

if __name__ == "__main__":
    raise SystemExit(main())
