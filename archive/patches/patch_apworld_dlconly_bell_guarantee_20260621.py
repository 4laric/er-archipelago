#!/usr/bin/env python3
r"""patch_apworld_dlconly_bell_guarantee_20260621.py

FEATURE (Alaric 2026-06-21): under dlc_only, GUARANTEE every progressive stone-bell copy lands.

Today the progressive bells ride the injectable-slot budget as OPTIONAL items, so on a tight
dlc_only/messmer seed only the leftover budget seats them (~23 of 50 with progressive_bell_count:25).
Alaric wants the player to get ALL bell-bearing upgrade tiers AND a wave of Lord's Runes early (the
overflow copies past 4 Smithing / 5 Somber tiers pay out as Lord's Runes client-side), so the FULL
progressive_bell_count of EACH bell must seat.

HOW: a count-neutral pool swap (mirrors dlc_gear_curation / relevance_uplift / pool_builder). Under
dlc_only it drops the cheapest filler -- low-tier crafting materials (rune value 0) FIRST, then
base-game rune drops (Golden/Shadow runes) -- and adds the bell copies in their place. Bells added ==
filler dropped, so pool size is unchanged and the bell LOCATIONS were never touched. The discrete
bells are still removed from the pool (unchanged) and the bells distribute via normal fill (useful
items, reachable under accessibility: minimal).

Non-dlc_only behaviour is UNCHANGED: the bells keep the original injectable-budget path. The dlc_only
arm of that path is removed (the swap owns it) to avoid double-seating.

TOUCHES worlds/eldenring/__init__.py (two edits, transactional):
  1. _all_injectable_items: gate the bell-copy injection to `not dlc_only`.
  2. create_items: append the dlc_only bell-guarantee swap after the pool_builder swap block.

Idempotent (aborts if MARKER present). CRLF-preserving. Byte-compiles + self-restores on failure.

RUN ON WINDOWS from the repo root:
    python patch_apworld_dlconly_bell_guarantee_20260621.py
    .\build.ps1 -Apworld -Generate     # gen-test (footer)
"""
import io, os, sys, py_compile, shutil

INIT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER = "bell GUARANTEE"


EDITS = [
    # 1) Don't inject bell copies into the injectable budget under dlc_only -- the swap owns them.
    (
        "        if self._progressive_bells_active():\n"
        "            # Pool copies per bell are yaml-tunable (progressive_bell_count); PROGRESSIVE_BELL_POOL_COUNT\n"
        "            # supplies the bell NAMES + the documented default. Applies to both bells equally.\n"
        "            _pool_n = self.options.progressive_bell_count.value\n"
        "            for _bn in PROGRESSIVE_BELL_POOL_COUNT:\n"
        "                items += [item_table[_bn] for _ in range(_pool_n)]\n",

        "        if self._progressive_bells_active() and not self.options.dlc_only:\n"
        "            # Pool copies per bell are yaml-tunable (progressive_bell_count); PROGRESSIVE_BELL_POOL_COUNT\n"
        "            # supplies the bell NAMES + the documented default. Applies to both bells equally.\n"
        "            # dlc_only is EXCLUDED here: it seats the full count via the count-neutral bell\n"
        "            # GUARANTEE swap in create_items (funded by scrubbing cheap filler) instead.\n"
        "            _pool_n = self.options.progressive_bell_count.value\n"
        "            for _bn in PROGRESSIVE_BELL_POOL_COUNT:\n"
        "                items += [item_table[_bn] for _ in range(_pool_n)]\n",
    ),
    # 2) The bell GUARANTEE swap, inserted after the pool_builder swap block.
    (
        "            for _name in _ladder[:_n]:\n"
        "                self.local_itempool.append(self._create_uplift_item(_name))\n"
        "\n"
        "        # Extra filler items for locations containing skip items\n",

        "            for _name in _ladder[:_n]:\n"
        "                self.local_itempool.append(self._create_uplift_item(_name))\n"
        "\n"
        "        # progressive bell GUARANTEE (dlc_only, Alaric 2026-06-21): seat the FULL\n"
        "        # progressive_bell_count copies of EACH stone bell, funded by a COUNT-NEUTRAL swap that\n"
        "        # drops the cheapest filler -- low-tier crafting materials (rune value 0) first, then\n"
        "        # base-game rune drops -- and adds the bells in their place. Guarantees every bell-bearing\n"
        "        # upgrade TIER lands and the overflow copies pay out as Lord's Runes early. Non-dlc_only\n"
        "        # keeps the injectable-budget path in _all_injectable_items. See er-progressive-stone-bells\n"
        "        # / er-bell-overflow-rune.\n"
        "        if self._progressive_bells_active() and self.options.dlc_only:\n"
        "            _bell_names = list(PROGRESSIVE_BELL_POOL_COUNT)\n"
        "            _per = self.options.progressive_bell_count.value\n"
        "            _want = _per * len(_bell_names)\n"
        "            _spared = getattr(self, \"_spared_comedy_junk\", set())\n"
        "            _droppable = [it for it in self.local_itempool\n"
        "                          if it.classification == ItemClassification.filler\n"
        "                          and it.name not in _spared\n"
        "                          and it.name not in _bell_names]\n"
        "            # cheapest first: crafting mats (rune value 0) before Golden/Shadow rune drops.\n"
        "            _droppable.sort(key=lambda it: getattr(it.data, \"runes\", 0) or 0)\n"
        "            _drop_n = min(_want, len(_droppable))\n"
        "            for _it in _droppable[:_drop_n]:\n"
        "                self.local_itempool.remove(_it)\n"
        "            _counts = {n: 0 for n in _bell_names}\n"
        "            _seated = 0\n"
        "            _bi = 0\n"
        "            while _seated < _drop_n and not all(_counts[n] >= _per for n in _bell_names):\n"
        "                _n = _bell_names[_bi % len(_bell_names)]\n"
        "                if _counts[_n] < _per:\n"
        "                    self.local_itempool.append(self.create_item(_n))\n"
        "                    _counts[_n] += 1\n"
        "                    _seated += 1\n"
        "                _bi += 1\n"
        "            if _seated < _want:\n"
        "                warning(f\"{self.player_name}: progressive bells -- seated {_seated}/{_want} \"\n"
        "                        f\"(filler funding exhausted); lower progressive_bell_count or widen the pool.\")\n"
        "\n"
        "        # Extra filler items for locations containing skip items\n",
    ),
]


def _newline_of(t): return "\r\n" if "\r\n" in t else "\n"


def main():
    if not os.path.isfile(INIT):
        print(f"ERROR: not found: {INIT} (run from the repo root).")
        return 2
    raw = io.open(INIT, "r", encoding="utf-8", newline="").read()
    if MARKER in raw:
        print(f"Already applied (marker '{MARKER}' present). No-op.")
        return 0
    nl = _newline_of(raw)
    text = raw.replace("\r\n", "\n")
    for anchor, repl in EDITS:
        a = anchor.replace("\r\n", "\n")
        n = text.count(a)
        if n != 1:
            print(f"ABORT (no change): anchor not unique (found {n}x):\n----\n{a[:200]}\n----")
            return 1
        text = text.replace(a, repl.replace("\r\n", "\n"), 1)
    out = text.replace("\n", nl)

    bak = INIT + ".bak_bellguarantee"
    shutil.copy2(INIT, bak)
    try:
        with io.open(INIT, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        py_compile.compile(INIT, doraise=True)
    except Exception as e:
        print(f"FAILED ({e}); restoring backup.")
        shutil.copy2(bak, INIT)
        return 1

    pc = os.path.join(os.path.dirname(INIT), "__pycache__")
    if os.path.isdir(pc):
        for fn in os.listdir(pc):
            try:
                os.remove(os.path.join(pc, fn))
            except OSError:
                pass
    print("OK. Applied dlc_only progressive-bell guarantee. Backup: " + bak)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================================
# GEN-TEST (your EldenRing-Alaric.yaml: dlc_only + messmer + progressive_stone_bells:true +
# progressive_bell_count:25), then .\build.ps1 -Apworld -Generate. PASS =
#   * gen SUCCESS, no FillError;
#   * spoiler holds 25 Progressive Smithing-Stone + 25 Progressive Somberstone bells placed as
#     checks (was 13 + 10);
#   * a matching ~50 of the cheapest filler (crafting mats first, then Golden/Shadow runes) are
#     GONE from the pool -- their locations now hold the bells or other filler;
#   * if a "progressive bells -- seated N/50" warning prints, the pool ran out of cheap filler to
#     drop (turn progressive_bell_count down, or widen location_pool).
# In-game: all bell tiers obtainable + a wave of Lord's Runes from the overflow copies.
# =============================================================================================
