#!/usr/bin/env python3
"""
patch_apworld_hint_full_region.py -- spell out full region names in Archipelago hints.

WHAT: rewrites World.extend_hint_information for the ER apworld so the hint "entrance" field
(the text AP appends after "... is at <check name>") reads the check's FULL parent-region name
instead of leaving you to decode the 'LG' / 'MtG' prefix baked into the check name. Long land
names are abbreviated (Liurnia, Altus, Mountaintops, Snowfield, Mohgwyn, Farum Azula). When
dungeon_sweep is on, swept member checks also get an "(auto-granted with <boss reward>)" tag
naming the trigger boss-drop that releases the whole group.

WHY IT WORKS OFF-HOST: extend_hint_information runs at GENERATION time. Main.py (L243-244) calls
it, stamps the result into er_hint_data, and freezes that into the multidata (.archipelago) file
(L336/350). MultiServer.py just reads er_hint_data back (L540) and echoes it onto each hint
(L1271: text += f" at {hint.entrance}"). So the enriched text is baked into the seed at gen time
-- it works on ANY host you hand the apworld to, with no server or client changes. The only way
to miss it is to generate against a stock apworld.

DATA SOURCE: location.parent_region.name -- authoritative and drift-proof (it IS the "Resolves to"
column in docs/check-name-legend.md). Overworld checks resolve to the land (Limgrave, Mt. Gelmir);
sub-dungeon checks resolve to the dungeon (Sellia Crystal Tunnel). No new data files needed.

Target: Archipelago/worlds/eldenring/__init__.py (CRLF). Byte-level slice/replace, ast-validated,
CRLF preserved, idempotent. Run on Windows, then re-gen (hints appear in the server). No client/
baker build.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")

START = b"    def extend_hint_information(self, hint_data):\r\n"
END = b"    def fill_slot_data(self) -> Dict[str, object]:\r\n"
SENTINEL = b"# (1) full region name for every check"

NEW_METHOD = (
    b"    def extend_hint_information(self, hint_data):\r\n"
    b"        \"\"\"AP hint enrichment, computed at GENERATION time and frozen into er_hint_data in the\r\n"
    b"        multidata (Main.py) -- works on any host, no server/client code. (1) Every check's hint\r\n"
    b"        entrance is set to its full parent-region name (long lands abbreviated), so hints spell\r\n"
    b"        out e.g. 'Mt. Gelmir' instead of the 'MtG' prefix baked into the check name. (2) When\r\n"
    b"        dungeon_sweep is on, swept members also get an '(auto-granted with <boss reward>)' tag\r\n"
    b"        naming the trigger boss-drop that releases the whole group.\"\"\"\r\n"
    b"        info = hint_data.setdefault(self.player, {})\r\n"
    b"        # abbreviated labels for the verbose land names (startswith, first match wins)\r\n"
    b"        _region_labels = (\r\n"
    b"            (\"Liurnia of The Lakes\", \"Liurnia\"),\r\n"
    b"            (\"Mountaintops of the Giants\", \"Mountaintops\"),\r\n"
    b"            (\"Consecrated Snowfield\", \"Snowfield\"),\r\n"
    b"            (\"Altus Plateau\", \"Altus\"),\r\n"
    b"            (\"Mohgwyn Palace\", \"Mohgwyn\"),\r\n"
    b"            (\"Crumbling Farum Azula\", \"Farum Azula\"),\r\n"
    b"            (\"Farum Azula\", \"Farum Azula\"),\r\n"
    b"        )\r\n"
    b"        # (1) full region name for every check\r\n"
    b"        for loc in self._get_our_locations():\r\n"
    b"            if loc.address is None:\r\n"
    b"                continue\r\n"
    b"            region = getattr(loc.parent_region, \"name\", None)\r\n"
    b"            if not region:\r\n"
    b"                continue\r\n"
    b"            for _pre, _lbl in _region_labels:\r\n"
    b"                if region.startswith(_pre):\r\n"
    b"                    region = _lbl\r\n"
    b"                    break\r\n"
    b"            info[loc.address] = region\r\n"
    b"        # (2) sweep boss tag for dungeon-swept members\r\n"
    b"        if self.options.dungeon_sweep != 0:\r\n"
    b"            _dsw, groups = self._compute_dungeon_sweeps()\r\n"
    b"            for trigger, members in groups:\r\n"
    b"                tn = trigger.name\r\n"
    b"                reward = tn.split(\":\", 1)[1].split(\" - \", 1)[0].strip() if \":\" in tn else tn\r\n"
    b"                tag = \" (auto-granted with \" + reward + \")\"\r\n"
    b"                for m in members:\r\n"
    b"                    if m.address is None or m.address == trigger.address:\r\n"
    b"                        continue\r\n"
    b"                    base = info.get(m.address, \"\")\r\n"
    b"                    info[m.address] = (base + tag) if base else (reward + tag)\r\n"
)


def main():
    if not os.path.isfile(TARGET):
        sys.exit("ERROR: not found: %s" % TARGET)
    with open(TARGET, "rb") as f:
        data = f.read()

    if SENTINEL in data:
        print("Already patched (hint full-region); nothing to do.")
        return

    for nm, anc in [("START", START), ("END", END)]:
        if data.count(anc) != 1:
            sys.exit("ERROR: anchor %s found %d (want 1). Aborting; no write."
                     % (nm, data.count(anc)))

    i = data.find(START)
    j = data.find(END)
    if not (i < j):
        sys.exit("ERROR: unexpected anchor ordering (START must precede END). Aborting; no write.")

    out = data[:i] + NEW_METHOD + data[j:]

    try:
        ast.parse(out.decode("utf-8"))
    except SyntaxError as e:
        sys.exit("ERROR: result does not parse (%s). Aborting; no write." % e)

    with open(TARGET, "wb") as f:
        f.write(out)

    with open(TARGET, "rb") as f:
        chk = f.read()
    assert SENTINEL in chk, "VERIFY FAILED: sentinel missing"
    assert chk.count(START) == 1 and chk.count(END) == 1, "VERIFY FAILED: anchor count drift"
    assert b"info[loc.address] = region" in chk, "VERIFY FAILED: region line missing"
    ast.parse(chk.decode("utf-8"))
    print("Patched + verified on disk: %s" % TARGET)
    print("Next: re-gen. Hints now spell out the full region name (+ sweep tag). No build needed.")


if __name__ == "__main__":
    main()
