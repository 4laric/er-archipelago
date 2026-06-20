#!/usr/bin/env python3
"""
patch_apworld_hint_extender.py -- surface the dungeon-sweep trigger boss in Archipelago hints.

WHAT: implements World.extend_hint_information for the ER apworld. When a player hints a check that is
swept by a boss drop (dungeon_sweep on), the hint's "entrance" field now reads e.g.
  "... is at SV/Liftside Chamber: ... (defeat boss: SV/SeC: Godrick's Great Rune - mainboss drop)".
AP renders whatever string we attach as the hint entrance (Main.py builds er_hint_data and stamps it
onto each Hint.entrance), so no client change is needed.

HOW (no logic duplication -- your note): the dungeon-sweep grouping currently lives inline in
fill_slot_data (~L4438-4533). This patch EXTRACTS it verbatim into a shared method
`_compute_dungeon_sweeps(self) -> (dungeon_sweeps, groups)`:
  - dungeon_sweeps = {str(trigger.address): [member ids]}   (unchanged; what fill_slot_data emits)
  - groups          = [(trigger_loc, [member_locs]), ...]    (new; what the hint builder consumes)
fill_slot_data now calls it (`dungeon_sweeps, _ = self._compute_dungeon_sweeps()`), and
extend_hint_information calls it too. add_sweep gains one line to record each group.

COVERAGE: (1) overworld/field/capstone checks are named from the committed static dump
boss_attribution.json (see dump_boss_attribution.py) -- "near boss: <vanilla boss>", a landmark that
holds up under enemy_rando. (2) dungeon/legacy checks (incl. boss-drop sweep triggers) fall back to the
apworld-computed sweep groups -- "defeat boss: <trigger>". If boss_attribution.json is absent, (1) is
skipped and only (2) applies (back-compat). Requires `import` access; uses os/json locally.

Target: Archipelago/worlds/eldenring/__init__.py (CRLF). Byte-level slice/insert, ast-validated, CRLF
preserved. Idempotent. Run on Windows, then re-gen (hints appear in the server). No client/baker build.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

FILL_DEF   = b"    def fill_slot_data(self) -> Dict[str, object]:\r\n"
BLK_START  = b"        dungeon_sweeps: Dict[str, List[int]] = {}\r\n"
BLK_END    = b"                        add_sweep(_sc_trig, _sc)\r\n"
ADDSWEEP   = b"                    dungeon_sweeps[str(trigger.address)] = ids\r\n"
SENTINEL   = b"def _compute_dungeon_sweeps"

ONELINER = b"        dungeon_sweeps, _ = self._compute_dungeon_sweeps()\r\n"

COMPUTE_HEAD = (
    b"\r\n"
    b"    def _compute_dungeon_sweeps(self):\r\n"
    b"        \"\"\"Shared dungeon-sweep grouping for fill_slot_data (dungeonSweeps slot_data) and\r\n"
    b"        extend_hint_information ('defeat boss' hints). Returns (dungeon_sweeps, groups): dungeon_sweeps\r\n"
    b"        = {str(trigger.address): [member ids]}; groups = [(trigger_loc, [member_locs]), ...]. Empty when\r\n"
    b"        dungeon_sweep is off. SPEC-dungeon-sweep.md.\"\"\"\r\n"
)
COMPUTE_TAIL = b"        return dungeon_sweeps, groups\r\n"

LOAD_METHOD = (
    b"\r\n"
    b"    def _load_boss_attribution(self):\r\n"
    b"        \"\"\"Cached static VANILLA boss-attribution dump {str(apLocId): [defeatFlag, bossName]},\r\n"
    b"        captured from one full bake's apconfig sweep_flags (dump_boss_attribution.py). Names the\r\n"
    b"        boss whose location holds each overworld/field/capstone check -- a landmark that holds up\r\n"
    b"        even under enemy_rando. Empty dict if the file is absent. Cached on the class.\"\"\"\r\n"
    b"        cache = getattr(type(self), \"_boss_attr_cache\", None)\r\n"
    b"        if cache is None:\r\n"
    b"            import os as _os, json as _json\r\n"
    b"            try:\r\n"
    b"                with open(_os.path.join(_os.path.dirname(__file__), \"boss_attribution.json\"),\r\n"
    b"                          encoding=\"utf-8\") as _f:\r\n"
    b"                    cache = _json.load(_f)\r\n"
    b"            except Exception:\r\n"
    b"                cache = {}\r\n"
    b"            type(self)._boss_attr_cache = cache\r\n"
    b"        return cache\r\n"
)

EXTEND_METHOD = (
    b"\r\n"
    b"    def extend_hint_information(self, hint_data):\r\n"
    b"        \"\"\"Show in AP hints which boss' location holds each check. (1) the static vanilla\r\n"
    b"        boss-attribution dump names overworld/field/capstone checks ('near boss: X'); (2) the\r\n"
    b"        apworld-computed dungeon-sweep groups fill the rest ('defeat boss: <trigger>'), incl.\r\n"
    b"        boss-drop checks that are a sweep trigger. Gated on dungeon_sweep being on.\"\"\"\r\n"
    b"        if self.options.dungeon_sweep == 0:\r\n"
    b"            return\r\n"
    b"        info = hint_data.setdefault(self.player, {})\r\n"
    b"        attr = self._load_boss_attribution()\r\n"
    b"        if attr:\r\n"
    b"            for loc in self._get_our_locations():\r\n"
    b"                if loc.address is None:\r\n"
    b"                    continue\r\n"
    b"                ent = attr.get(str(loc.address))\r\n"
    b"                if ent:\r\n"
    b"                    info[loc.address] = \"near boss: \" + ent[1]\r\n"
    b"        _dsw, groups = self._compute_dungeon_sweeps()\r\n"
    b"        for trigger, members in groups:\r\n"
    b"            label = \"defeat boss: \" + trigger.name\r\n"
    b"            for m in members:\r\n"
    b"                if m.address is None or m.address == trigger.address:\r\n"
    b"                    continue\r\n"
    b"                info.setdefault(m.address, label)\r\n"
)


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()

    if SENTINEL in data:
        print("Already patched (hint extender); nothing to do.")
        return

    for nm, anc, want in [("FILL_DEF", FILL_DEF, 1), ("BLK_START", BLK_START, 1),
                          ("BLK_END", BLK_END, 1), ("ADDSWEEP", ADDSWEEP, 1)]:
        if data.count(anc) != want:
            sys.exit("ERROR: anchor %s found %d (want %d). Aborting; no write."
                     % (nm, data.count(anc), want))

    i = data.find(BLK_START)
    j = data.find(BLK_END) + len(BLK_END)
    if not (data.find(FILL_DEF) < i < j):
        sys.exit("ERROR: unexpected anchor ordering. Aborting; no write.")

    block = data[i:j]
    # Build the shared-method body from the block: add `groups = []` and record each group.
    block_mod = block.replace(
        BLK_START, BLK_START + b"        groups = []\r\n", 1)
    block_mod = block_mod.replace(
        ADDSWEEP, ADDSWEEP + b"                    groups.append((trigger, members))\r\n", 1)
    new_methods = COMPUTE_HEAD + block_mod + COMPUTE_TAIL + LOAD_METHOD + EXTEND_METHOD

    # 1) replace the inline block with the call
    out = data[:i] + ONELINER + data[j:]
    # 2) insert the new methods before fill_slot_data (fill_def is before the block, unaffected by step 1)
    k = out.find(FILL_DEF)
    out = out[:k] + new_methods + out[k:]

    # Validate syntax before writing.
    try:
        ast.parse(out.decode("utf-8"))
    except SyntaxError as e:
        sys.exit("ERROR: result does not parse (%s). Aborting; no write." % e)

    with open(TARGET, "wb") as f:
        f.write(out)

    with open(TARGET, "rb") as f:
        chk = f.read()
    assert SENTINEL in chk and b"def extend_hint_information" in chk \
        and b"def _load_boss_attribution" in chk, "VERIFY FAILED"
    assert chk.count(b"dungeon_sweeps, _ = self._compute_dungeon_sweeps()") == 1, "VERIFY FAILED: call missing"
    assert chk.count(ADDSWEEP) == 1, "VERIFY FAILED: addsweep moved/dup"
    ast.parse(chk.decode("utf-8"))
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: re-gen. Hints now show 'defeat boss: <trigger>'. No client/baker build needed.")


if __name__ == "__main__":
    main()
