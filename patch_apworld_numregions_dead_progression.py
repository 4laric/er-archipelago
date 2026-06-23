#!/usr/bin/env python3
r"""patch_apworld_numregions_dead_progression.py

Stop DEAD PROGRESSION from overflowing the fill in num_regions / spine-seal seeds.

SYMPTOM (after patch_apworld_important_locations_scope cleared the remembrance/priority side):
    Fill.FillError: No more spots to place 6 items. Remaining locations are invalid.
    unplaced = Morgott's/Radahn's/Malenia's/Mohg's Great Rune, Erudition,
               Nomadic Warrior's Cookbook [19]
A num_regions=4 Capital chain run: only ~4 kept regions of randomizable slots, yet several
items remain PROGRESSION while gating nothing reachable, so they have no valid home.

TWO SOURCES OF DEAD PROGRESSION
-------------------------------
(A) SURPLUS GREAT RUNES. num_regions's pool rune-source meets Leyndell's count gate with
    _inject_runes + kept-step runes (the gate-counting set). Separately, sealed-region runes
    that are NOT that set are queued in self._deadkey_rune_queue (== local _free) and swapped
    into the pool for dead/redundant vanilla keys in create_items via create_item(rune) -- which
    uses the rune's DEFAULT classification == PROGRESSION. So each dead-key swap injects an EXTRA
    progression great rune that demands a reachable kept home -> overflow. They are not needed by
    the gate, so demote the _free runes to useful: the swap then creates them as useful (still
    placed at the dead-key location, count-neutral, but out of the progression/priority fill).

(B) ORPHANED SIDE-GATE GOODS. Items like Erudition (gates only the Liurnia Converted-Tower
    puzzle checks) and Nomadic Warrior's Cookbook [19] / Battlefield Priest's Cookbook [4]
    (gate a single crafting check) are progression+inject, but when their region is sealed the
    gating rules are never added (the locations aren't randomized) -- they gate nothing yet stay
    progression. The apworld already has a "fun consumable" demotion block for exactly this class
    of optional-side-content progression, but it is currently disabled (`if False`, a deliberate
    "keep them progression under accessibility=full" call). Re-enable it ONLY under a spine seal
    (_spine_active -- num_regions / region_count / messmer / godrick, all forced to accessibility
    minimal) and extend its prefix list with the orphaned side-gate goods. Non-spine seeds are
    untouched, so the accessibility=full reasoning behind the `if False` still holds there.

Run on Windows from repo root (or the eldenring apworld dir), AFTER
patch_apworld_important_locations_scope.py:
    python patch_apworld_numregions_dead_progression.py
CRLF-safe byte splice; idempotent; every anchor is count-guarded.
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

MARKER = "patch_apworld_numregions_dead_progression"
if MARKER.encode("utf-8") in b:
    print("  [skip] num_regions dead-progression demotion already present.")
    sys.exit(0)

def splice(buf, old_s, new_s, label):
    old = conv(old_s); new = conv(new_s)
    n = buf.count(old)
    if n != 1:
        sys.exit("  [FAIL] anchor '%s' found %d times (expected 1); not modified." % (label, n))
    return buf.replace(old, new)

# ---- Edit A: demote surplus sealed-region great runes (the dead-key swap queue) ----
A_OLD = (
    "            self._deadkey_rune_queue = _free\n"
)
A_NEW = (
    "            self._deadkey_rune_queue = _free\n"
    "            # patch_apworld_numregions_dead_progression (A): _free are SURPLUS sealed-region\n"
    "            # great runes (NOT the gate-counting set -- that is _inject_runes + kept-step runes).\n"
    "            # They only enter the pool via the dead-key swap in create_items, which does\n"
    "            # create_item(rune) at the rune's DEFAULT classification == progression -> each then\n"
    "            # demands a reachable kept home and overflows the tiny kept fill. Demote them to useful\n"
    "            # so the swap creates them as useful (still placed at the dead-key location,\n"
    "            # count-neutral, but out of the progression/priority fill). Gate stays satisfiable.\n"
    "            for _drn in _free:\n"
    "                if _drn in item_table and item_table[_drn].classification == ItemClassification.progression:\n"
    "                    item_table[_drn].classification = ItemClassification.useful\n"
    "                    item_table[_drn].filler = False\n"
)
b = splice(b, A_OLD, A_NEW, "deadkey queue assignment")

# ---- Edit B1: re-enable the side-content demotion block, gated on spine seal ----
B1_OLD = (
    "        if False:  # demote OFF (2026-06-18): keep fun consumables progression for accessibility full\n"
)
B1_NEW = (
    "        if getattr(self, \"_spine_active\", False):  # patch_apworld_numregions_dead_progression (B):\n"
    "            # was `if False` (keep these progression under accessibility=full). Under a spine seal\n"
    "            # (num_regions / region_count / messmer / godrick -- always accessibility minimal) these\n"
    "            # optional-side-content goods gate sealed regions -> dead progression that overflows the\n"
    "            # tiny kept fill. Demote them here ONLY for spine seals; non-spine seeds are unchanged.\n"
)
b = splice(b, B1_OLD, B1_NEW, "fun-demotion gate")

# ---- Edit B2: extend the prefix list with the orphaned side-gate goods ----
B2_OLD = (
    "                             \"Imbued Sword Key\", \"Sewer-Gaol Key\", \"Giant's Prayerbook\"]\n"
)
B2_NEW = (
    "                             \"Imbued Sword Key\", \"Sewer-Gaol Key\", \"Giant's Prayerbook\",\n"
    "                             # patch_apworld_numregions_dead_progression: optional-side-gate goods\n"
    "                             # seen orphaned under num_regions seals (gate only sealed-region\n"
    "                             # checks: Erudition -> Liurnia Converted Tower; cookbooks -> one\n"
    "                             # crafting check). Demoted only when progression. Extend freely.\n"
    "                             \"Erudition\", \"Nomadic Warrior's Cookbook [19]\",\n"
    "                             \"Battlefield Priest's Cookbook [4]\"]\n"
)
b = splice(b, B2_OLD, B2_NEW, "fun prefix list tail")

with open(P, "wb") as f:
    f.write(b)
print("  [ok] num_regions dead-progression demotion (surplus runes + side-gate goods) applied to %s" % P)
