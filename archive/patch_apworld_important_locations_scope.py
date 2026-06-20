#!/usr/bin/env python3
r"""patch_apworld_important_locations_scope.py

Make the important_locations PRIORITY pass num_regions- and Enia-aware, and stop it
starving the fill in constrained (region_lock / num_regions) seeds.

SYMPTOM
-------
    Fill.FillError: No more spots to place 7 items. Remaining locations are invalid.
with the unplaced set = genuine progression (region locks, the Leyndell Drawing-Room Key,
great runes, remembrances) -- e.g. a num_regions=4 Capital chain run.

ROOT CAUSE
----------
generate_early builds self.all_priority_locations with an UNCONDITIONAL sweep over every
region in location_tables: any location matching a selected important_locations class
(Boss / Remembrance / Church / Seedtree / ...) becomes LocationProgressType.PRIORITY,
with zero awareness of (a) which regions num_regions actually kept, or (b) how few
randomizable slots a kept region has. AP's priority pass then force-fills a progression
item into every PRIORITY slot BEFORE the main fill. In a tiny kept set that claims the
scarce early/kept slots the chain locks + injected runes uniquely need, so they have
nowhere reachable to land. Separately, with randomize_enia OFF a Remembrance gates only
the (vanilla) Enia turn-in -> it is NOT real progression, yet its drop-location is still
promoted to PRIORITY and the item is still progression, both crowding the fill.

FIX (three coordinated, low-blast-radius changes in generate_early)
-------------------------------------------------------------------
(1) IN-SCOPE filter: a location is eligible for PRIORITY only if _is_location_available()
    (randomized + in pool). Sealed (num_regions / spine) regions and vanilla Enia slots
    fail this, so the previous marking was a latent no-op at best -- make it explicit.
(2) HEADROOM cap (spine seals only -- num_regions / region_count / messmer / godrick):
    keep >= _PRIO_HEADROOM free, randomizable, non-excluded slots per region so the lock
    chain + injected runes can always thread through. Inert on non-spine seeds.
(3) REMEMBRANCE reality check: a Remembrance item only gates the Enia turn-in checks, so
    it is real progression ONLY when randomize_enia is on (reachability goals like
    ending_condition==2 use the LOCATIONS, not the items). When randomize_enia is OFF,
    drop "remembrance" from the priority classes AND demote Remembrance items to useful
    (mirrors the fun-consumable demotion; names added to _fun_demoted so the gate-shorthand
    asserts in _add_location_rule/_add_entrance_rule stay relaxed).

Great runes are NOT touched here: num_regions already frees sealed-region runes via the
_deadkey_rune_queue (leftovers -> filler). If runes still overflow after this, that's the
lever to revisit -- separately.

Run on Windows from repo root (or the eldenring apworld dir):
    python patch_apworld_important_locations_scope.py
CRLF-safe byte splice; idempotent.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANDS = [HERE, os.path.join(HERE, "Archipelago", "worlds", "eldenring")]
PKG = next((d for d in CANDS if os.path.exists(os.path.join(d, "__init__.py"))
            and os.path.exists(os.path.join(d, "grace_data.py"))), None)
if not PKG:
    sys.exit("ERROR: eldenring apworld dir not found (run from repo root or the apworld dir).")
P = os.path.join(PKG, "__init__.py")

with open(P, "rb") as f:
    b = f.read()
nl = b"\r\n" if b"\r\n" in b else b"\n"
def conv(s): return s.replace("\n", nl.decode("ascii")).encode("utf-8")

MARKER = "patch_apworld_important_locations_scope"
if MARKER.encode("utf-8") in b:
    print("  [skip] important_locations scope/headroom already present.")
    sys.exit(0)

# ---- Edit A: replace the unconditional priority sweep ----
SWEEP_OLD = conv(
    "        for locations in location_tables.values():\n"
    "            for loc in locations:\n"
    "                if any(priority_class_predicates[c](loc) for c in selected_priority_classes):\n"
    "                    self.all_priority_locations.update({loc.name})\n"
)
SWEEP_NEW = conv(
    "        # --- num_regions / Enia-aware priority selection (patch_apworld_important_locations_scope) ---\n"
    "        # A Remembrance item only gates the Enia turn-in checks, so it is real progression ONLY\n"
    "        # when randomize_enia is on. With Enia vanilla it buys optional gear 1:1 and gates nothing\n"
    "        # -> never promote its drop-location to PRIORITY (it would crowd the constrained fill).\n"
    "        if not self.options.randomize_enia:\n"
    "            selected_priority_classes = [c for c in selected_priority_classes if c != \"remembrance\"]\n"
    "        # (1) IN-SCOPE filter: only randomized, in-pool, non-excluded locations are PRIORITY-eligible.\n"
    "        #     Sealed (num_regions / spine) regions and vanilla Enia slots fail _is_location_available.\n"
    "        # (2) HEADROOM cap (spine seals only): keep >= _PRIO_HEADROOM free randomizable slots per\n"
    "        #     region so the lock chain + injected runes always have a reachable home (else the\n"
    "        #     priority pass eats the scarce kept slots -> 'No more spots to place N items.').\n"
    "        _spine_seal = bool(getattr(self, \"_spine_active\", False))\n"
    "        _PRIO_HEADROOM = 2\n"
    "        for _region_name, _region_locs in location_tables.items():\n"
    "            _avail = [l for l in _region_locs\n"
    "                      if self._is_location_available(l) and l.name not in self.all_excluded_locations]\n"
    "            _cand = [l for l in _avail\n"
    "                     if any(priority_class_predicates[c](l) for c in selected_priority_classes)]\n"
    "            if _spine_seal and _cand:\n"
    "                _allowed = max(0, len(_avail) - _PRIO_HEADROOM)\n"
    "                if len(_cand) > _allowed:\n"
    "                    _cand = sorted(_cand, key=lambda l: l.name)[:_allowed]\n"
    "            for l in _cand:\n"
    "                self.all_priority_locations.update({l.name})\n"
)
if b.count(SWEEP_OLD) != 1:
    sys.exit("  [FAIL] priority sweep anchor found %d times (expected 1); not modified." % b.count(SWEEP_OLD))
b = b.replace(SWEEP_OLD, SWEEP_NEW)

# ---- Edit B: demote Remembrance items when randomize_enia is OFF ----
DISCARD_OLD = conv(
    "                    if self.options.blessing_option.value == 2 and dlc and (loc.fragment or loc.revered):\n"
    "                        self.all_priority_locations.discard(loc.name)\n"
)
DISCARD_NEW = DISCARD_OLD + conv(
    "\n"
    "        # Remembrance items gate only the Enia turn-in checks (see priority block above). With\n"
    "        # randomize_enia OFF they gate nothing required -> demote them out of progression so they\n"
    "        # stop crowding the constrained (region_lock / num_regions) progression+priority fill.\n"
    "        # Added to _fun_demoted so the gate-shorthand asserts stay relaxed. Reachability goals\n"
    "        # (ending_condition==2) use the LOCATIONS not the items, so this is goal-safe.\n"
    "        # (patch_apworld_important_locations_scope)\n"
    "        if not self.options.randomize_enia:\n"
    "            self._fun_demoted = getattr(self, \"_fun_demoted\", set())\n"
    "            _rem_demoted = 0\n"
    "            for _tbl in (item_table, item_table_vanilla):\n"
    "                for _data in _tbl.values():\n"
    "                    if (_data.classification == ItemClassification.progression\n"
    "                            and _data.name.startswith(\"Remembrance\")):\n"
    "                        _data.classification = ItemClassification.useful\n"
    "                        _data.filler = False\n"
    "                        self._fun_demoted.add(_data.name)\n"
    "                        _rem_demoted += 1\n"
)
if b.count(DISCARD_OLD) != 1:
    sys.exit("  [FAIL] discard-block anchor found %d times (expected 1); not modified." % b.count(DISCARD_OLD))
b = b.replace(DISCARD_OLD, DISCARD_NEW)

with open(P, "wb") as f:
    f.write(b)
print("  [ok] important_locations scope/headroom + remembrance demotion applied to %s" % P)
