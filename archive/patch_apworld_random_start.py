#!/usr/bin/env python3
"""
patch_apworld_random_start.py  --  apworld layer for Random Starting Region (idea #1).

SPEC: SPEC-random-starting-region.md  (build order: re-root + slot_data FIRST -- this patch).

What it adds (apworld only -- gen-testable on its own; baker WarpPlayer + client are follow-ups):
  options.py
    - RandomStartRegion (off / overworld / any_major)
    - StartRegionFreebie (hub_only / to_limgrave)
    - registers both on EROptions
  __init__.py
    - generate_early: roll a legal start region, PRE-COLLECT its lock (joins sphere 1 under the
      Limgrave-rooted warp graph), force region_access=warp. Off under dlc_only / any spine seal.
    - fill_slot_data: extend startGraces with the rolled region's full grace bundle (minus
      boss-arena/border graces) + open flag + Roundtable + The First Step (+ Limgrave graces if
      to_limgrave); emit startRegion + startWarpGrace for the future baked WarpPlayer.

Run on Windows (Claude does not run apworld patches -- see er-patches-run-on-windows memory):
    python patch_apworld_random_start.py
Idempotent: re-running is a no-op (detects its own markers). Binary I/O preserves CRLF.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OPTIONS = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "options.py")
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

CRLF = b"\r\n"


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _crlf(text):
    """str (LF) -> bytes (CRLF), so inserted blocks match the apworld's line endings."""
    return text.replace("\n", "\r\n").encode("utf-8")


def _insert_before(data, anchor_bytes, insert_bytes, label):
    n = data.count(anchor_bytes)
    if n != 1:
        raise SystemExit(f"[FAIL] {label}: anchor found {n} times (expected 1). Aborting, no write.")
    return data.replace(anchor_bytes, insert_bytes + anchor_bytes, 1)


def _insert_after(data, anchor_bytes, insert_bytes, label):
    n = data.count(anchor_bytes)
    if n != 1:
        raise SystemExit(f"[FAIL] {label}: anchor found {n} times (expected 1). Aborting, no write.")
    return data.replace(anchor_bytes, anchor_bytes + insert_bytes, 1)


# ---------------------------------------------------------------- options.py ----
OPT_CLASSES = '''\
class RandomStartRegion(Choice):
    """Roll a random overworld region to start in instead of Limgrave / The First Step. The chosen
    region becomes the free sphere-1 hub: its lock is pre-collected (so it joins sphere 1 under the
    Limgrave-rooted warp graph), and its grace bundle + map reveal + open flag fire at load. Requires
    a lock-based world_logic (region_lock / region_lock_bosses); forces region_access=warp. Inert
    under dlc_only (Gravesite is already the fixed hub) and under any region-seal goal
    (capital/region_count/messmer/godrick) for now.

    - off:        vanilla -- start at The First Step (Limgrave).
    - overworld:  roll among the overworld majors (Weeping, Liurnia, Caelid, Altus) -- each has a
                  clean warp grace + map piece. Safest.
    - any_major:  any region with a grace bundle + lock. Spicier; some lack a map pillar."""
    display_name = "Random Starting Region"
    option_off = 0
    option_overworld = 1
    option_any_major = 2
    default = 0

class StartRegionFreebie(Choice):
    """How much comes free with the rolled start region. The start region is always reachable with
    zero items (its lock is pre-collected); this controls whether Limgrave (Roundtable / early
    services / Torrent hand-off area) is also lit at load.

    - hub_only:    just the start region's graces + open flag.
    - to_limgrave: also light Limgrave's start graces so services are never stranded behind a lock
                   you happened not to start near (recommended)."""
    display_name = "Start Region Freebie"
    option_hub_only = 0
    option_to_limgrave = 1
    default = 1

'''

OPT_FIELDS = '''\
    random_start_region: RandomStartRegion
    start_region_freebie: StartRegionFreebie
'''

# ---------------------------------------------------------------- __init__.py ----
GE_BLOCK = '''\
        # Random starting region (SPEC-random-starting-region.md): roll a region to be the free
        # sphere-1 hub instead of Limgrave. Pre-collect its lock (so it joins sphere 1 under the
        # Limgrave-rooted warp graph) and force region_access=warp -- a geographically-deep start has
        # no zero-item physical route, so geographic access would softlock. Lock-based world_logic
        # only; off under dlc_only (Gravesite is already the fixed DLC hub) and under any spine seal
        # (capital/region_count/messmer/godrick reshape the kept set -- defer that combo).
        self._random_start_region = None
        _rsr_opt = self.options.random_start_region.value
        if _rsr_opt and self.options.world_logic.value in (0, 2) and not self.options.dlc_only:
            if getattr(self, "_spine_active", False):
                warning(f"{self.player_name}: random_start_region is set but a region-seal goal "
                        f"(capital/region_count/messmer/godrick) is active; ignoring it for now.")
            else:
                _OVERWORLD_START = ["Weeping Peninsula", "Liurnia of The Lakes", "Caelid", "Altus Plateau"]
                _cands = list(_OVERWORLD_START) if _rsr_opt == 1 else list(REGION_LOCK_ITEM.keys())
                _cands = [r for r in _cands
                          if r in REGION_LOCK_ITEM and r in REGION_GRACE_POINTS
                          and REGION_LOCK_ITEM[r] in item_table
                          and getattr(item_table[REGION_LOCK_ITEM[r]], "inject", False)]
                if _cands:
                    _choice = self.random.choice(sorted(_cands))
                    self._random_start_region = _choice
                    _lock = REGION_LOCK_ITEM[_choice]
                    item_table[_lock].inject = False
                    self.multiworld.push_precollected(self.create_item(_lock))
                    if self.options.region_access.value != 1:
                        self.options.region_access.value = 1
                        warning(f"{self.player_name}: random_start_region forces region_access=warp "
                                f"(geographic access from a deep start can softlock).")
                else:
                    warning(f"{self.player_name}: random_start_region found no legal start region "
                            f"under these settings; starting in Limgrave (vanilla).")
'''

SG_BLOCK = '''\
        # Random starting region: grant the rolled region's full grace bundle at load (minus
        # boss-arena/border graces, same skip sets as the region_graces bundle above), plus its open
        # flag + Roundtable (71190) + The First Step (76101) anchor, so it is fully fast-travelable
        # from the jump (mirrors LIMGRAVE_START_GRACES). start_region_freebie=to_limgrave also lights
        # Limgrave's graces so early services/Roundtable are never stranded. Physical spawn (baked
        # WarpPlayer) is a follow-up baker increment; startRegion + startWarpGrace carry the target.
        _rsr = getattr(self, "_random_start_region", None)
        _rsr_warp_grace = 0
        if _rsr and self.options.world_logic < 3:
            _RS_SKIP = frozenset({71240, 76422, 76508, 76509, 76852, 76853, 76930, 76931,
                                  73204, 73207, 76209, 76229, 76301, 76350, 76351, 76356})
            _rs_pts = [p for p in REGION_GRACE_POINTS.get(_rsr, []) if p[0] not in _RS_SKIP]
            _rs_g = [int(p[0]) for p in _rs_pts]
            _rs_g += [71190, 76101]  # Roundtable + The First Step anchor
            _rs_of = region_open_flags.get(REGION_LOCK_ITEM.get(_rsr))
            if _rs_of:
                _rs_g.append(int(_rs_of))
            if self.options.start_region_freebie.value == 1:  # to_limgrave
                _rs_g += [int(f) for f in LIMGRAVE_START_GRACES]
            start_graces = sorted(set(start_graces + _rs_g))
            # Central grace (nearest centroid) = the baked WarpPlayer target, for the follow-up.
            if _rs_pts:
                _cx = sum(p[1] for p in _rs_pts) / len(_rs_pts)
                _cz = sum(p[2] for p in _rs_pts) / len(_rs_pts)
                _rsr_warp_grace = int(min(_rs_pts, key=lambda p: (p[1] - _cx) ** 2 + (p[2] - _cz) ** 2)[0])
        self._rsr_warp_grace = _rsr_warp_grace
'''

SD_BLOCK = '''\
            # Random starting region (SPEC-random-starting-region.md): rolled hub region name + its
            # central warp grace, for the baked WarpPlayer that drops the player in at load (follow-up
            # baker increment, mirrors dlcEntryWarpFlag). "" / 0 when off.
            "startRegion": getattr(self, "_random_start_region", None) or "",
            "startWarpGrace": getattr(self, "_rsr_warp_grace", 0),
'''


def patch_options(data):
    if b"random_start_region: RandomStartRegion" in data:
        print("[skip] options.py already patched.")
        return data, False
    data = _insert_before(
        data,
        b"@dataclass\r\nclass EROptions(PerGameCommonOptions):",
        _crlf(OPT_CLASSES),
        "options.py classes",
    )
    data = _insert_after(
        data,
        b"    region_count: RegionCount\r\n",
        _crlf(OPT_FIELDS),
        "options.py EROptions fields",
    )
    return data, True


def patch_init(data):
    if b"self._random_start_region = None" in data:
        print("[skip] __init__.py already patched.")
        return data, False
    data = _insert_before(
        data,
        b"        exclude_local_item_only_lowercase = [key.lower() for key in self.options.exclude_local_item_only.value]",
        _crlf(GE_BLOCK),
        "__init__.py generate_early block",
    )
    data = _insert_before(
        data,
        b"        start_items: List[int] = []",
        _crlf(SG_BLOCK),
        "__init__.py start_graces block",
    )
    data = _insert_after(
        data,
        b'            "startGraces": start_graces,\r\n',
        _crlf(SD_BLOCK),
        "__init__.py slot_data keys",
    )
    return data, True


def main():
    for p in (OPTIONS, INIT):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")

    opt = _read(OPTIONS)
    opt2, opt_changed = patch_options(opt)
    ini = _read(INIT)
    ini2, ini_changed = patch_init(ini)

    if opt_changed:
        _write(OPTIONS, opt2)
        print(f"[ok] patched {OPTIONS}")
    if ini_changed:
        _write(INIT, ini2)
        print(f"[ok] patched {INIT}")
    if not (opt_changed or ini_changed):
        print("[done] nothing to do (already patched).")
    else:
        print("[done] random-start apworld layer applied. Rebuild the .apworld and gen-test.")


if __name__ == "__main__":
    main()
