#!/usr/bin/env python3
"""Emit greenfield/eldenring/death_award_pairs.json -- the (trigger flag, check flag) pairs behind
EMEVD death-driven awards, so the client can detect a death the award never paid for:

  * clients#385 (the rouqs Leyndell Tree Spirit, 2026-08-22): the corpse-treasure family;
  * clients#395 (Azeem's Elden Beast, 2026-08-22): the boss-award latch family.

CORPSE-TREASURE FAMILY. Common events 90005300/90005301 award a treasure on a character's death:
`WaitFor(CharacterRatioDead(chr))` -> set the death flag -> `ForceCharacterTreasure` puts the lot
on the corpse. Their reload branch is unforgiving when `value == 0`: a set death flag on re-entry
force-kills the corpse WITHOUT re-forcing the treasure -- so a death the event missed (despawn,
fall, death during a load) or a corpse left unlooted across one reload leaves the check
PERMANENTLY unpayable in-game. Death flag up + check flag down is therefore a complete, save-
persistent signature of a missed award, and the client can fire the check from it retroactively.

BOSS-AWARD LATCH FAMILY. Common events 1100/1200 (`$Event(1100, Default, ...)`,
common.emevd.dcx.js) park on `WaitFor(triggerFlag)` and `AwardItemsIncludingClients(lot)` when a
boss's map script records the kill (e.g. m19_00's `$Event(19002800)` sets 9123 right after
`CharacterDead`). Trigger up + check down is the same signature, and the observed failure is just
as permanent: Azeem's 9123 went up with 510230 never set, across 50 minutes AND a full relaunch
with the trigger pre-set (the boot path is suppressed -- the `Unknown200476(trigger, lot)` prefix
behaves as a re-award suppressor). The sweep condition is exactly the game's own award condition,
so it cannot pay anything vanilla would not have: trigger up + latch down means the event itself
considers the award owed and unpaid.

Two pairs per init are possible. The init line is
`$InitializeEvent(slot, 1100|1200, trigger, lot, lot2, latch)`:

  * (trigger, LATCH) -- the latch is the event's `EndIf` flag, and for most bosses it IS the
    remembrance lot's getItemFlagId (the remembrance rides the boss's NpcParam.itemLotId_map, an
    engine award with no latch of its own; the latch is the only observable). Elden Beast:
    (9123, 510230). This also covers Godrick: (9101, 510010) pays the Remembrance of the Grafted
    check, which NO event line otherwise pairs with the trigger.
  * (trigger, LOT'S getItemFlagId) via flag_lots.tsv, when it differs from the latch -- the great
    rune case: Godrick's slot awards lot 10010 (Great Rune, flag 171) but latches on 510010, so
    (9101, 171) is the only pair that can pay the rune check if the family-A award missed while
    the family-B remembrance paid (a state vanilla cannot recover: the event has latched, the
    engine does not retry a dead boss).

Lots that are not checks (flag_lots.tsv non-members, e.g. the 60510/60440-latched slots) still
emit their latch pair: harmless, because the client intersects the table with the seed's own check
flags (`retained`) before sweeping. `lot2` is 0 on all 128 current inits; assert that stays true
rather than silently dropping a second award.

WHAT IS EXCLUDED. Corpse family: the six `value == 2` sites re-force the corpse treasure on every
reload, so death-up + check-down there means "not looted yet", not "lost" -- sweeping them would
eat a live corpse. Boss family: nothing -- all 128 inits share the one suppressing boot path.

TRIGGER SETTER AUDIT. The boss family is only as clean as its triggers: a trigger flag set by
anything other than the boss's death would let the sweep pay an unearned check. So every trigger
is audited for its literal `SetEventFlagID?(flag, ON)` sites across the corpus and the counts are
printed. Measured: 106 single-setter, 17 parameterized (set via a shared helper's argument --
spot-checked 9124/Malenia: never literally set, arrives through the boss-defeat helper; an inert
pair at worst), 5 multi-map (shared arena variants -- vanilla's own award event fires on the same
shared trigger, so the sweep stays vanilla-equivalent), 0 with a non-death literal setter.

GAME data, not seed data -- ships beside the dll like check_lots_table.json (build.ps1 -Me3Deploy
copies it; package_release stages it), read by any seed old or new. No slot_data, no contract.

Measured on the current corpus: 185 corpse check-joined pairs (179 sweepable, 6 excluded) + 129
boss-award pairs (128 latch + 1 great-rune lot flag) = 308 total.
"""
import json
import os
import re
import sys
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
EVENT_DIR = os.path.join(REPO, "elden_ring_artifacts", "event")
FLAG_LOTS = os.path.join(REPO, "greenfield", "flag_lots.tsv")
OUT = os.path.join(REPO, "greenfield", "eldenring", "death_award_pairs.json")

# The corpse-treasure family. Derived by scanning common_func for events whose body waits on
# CharacterRatioDead and forces a treasure; extend here (with the measurement) if a sibling appears.
AWARD_EVENTS = ("90005300", "90005301")
RX = re.compile(r"InitializeCommonEvent\(0, (" + "|".join(AWARD_EVENTS) + r")((?:, [\-\d]+)+)\)")

# The boss-award latch family: common events 1100/1200 park on WaitFor(trigger) and award a lot
# whose getItemFlagId is the check (clients#395). Every init lives in common.emevd's boot event
# (measured: 128 inits, all in this one file), as
#   $InitializeEvent(slot, 1100|1200, trigger, lot, lot2, latch)
COMMON_EVENT = os.path.join(EVENT_DIR, "common.emevd.dcx.js")
BOSS_EVENTS = ("1100", "1200")
RX_BOSS = re.compile(
    r"InitializeEvent\(\d+, (" + "|".join(BOSS_EVENTS) + r"), (\d+), (\d+), (\d+), (\d+)\)")
# For the trigger-setter audit: literal SetEventFlagID?(flag, ON) sites corpus-wide.
RX_SET_ON = re.compile(r"SetEventFlagID?\((\d+), ON\)")


def load_corpus():
    """{filename: decompressed text} for every readable event script."""
    texts = {}
    for root, _, files in os.walk(EVENT_DIR):
        for fn in files:
            path = os.path.join(root, fn)
            with open(path, "rb") as fh:
                raw = fh.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = zlib.decompress(raw).decode("utf-8", "replace")
                except zlib.error:
                    continue
            texts[fn] = text
    return texts


def corpse_pairs(texts, lot2flag):
    """clients#385 family: (death flag, check flag) per value==0 corpse-treasure init."""
    pairs = set()
    values = Counter()
    for text in texts.values():
        for m in RX.finditer(text):
            args = [int(x) for x in m.group(2).strip(", ").split(", ")]
            # (eventFlagId, chrEntityId, itemLotId, timeSeconds, value) -- uniform 5-arg on the
            # current corpus; a shorter form defaults value to 0, the conservative direction.
            if len(args) < 3 or args[2] == 0:
                continue
            lot = args[2]
            if lot not in lot2flag:
                continue
            value = args[4] if len(args) >= 5 else 0
            values[value] += 1
            if value == 0:
                pairs.add((args[0], lot2flag[lot]))
    return pairs, values


def boss_pairs(texts, lot2flag):
    """clients#395 family: (trigger, latch) per 1100/1200 init, plus (trigger, lot flag) when the
    awarded lot's getItemFlagId differs from the latch (the great-rune split, e.g. Godrick).
    Also the trigger-setter audit: literal SetEventFlagID?(trigger, ON) sites corpus-wide."""
    common = None
    for fn, text in texts.items():
        if fn == "common.emevd.dcx.js":
            common = text
            break
    if common is None:
        sys.exit("FATAL: common.emevd.dcx.js unreadable -- the 1100/1200 inits live there. "
                 "Nothing written.")
    pairs = set()
    triggers = set()
    lot2_zero = 0
    for m in RX_BOSS.finditer(common):
        _fam, trigger, lot, lot2, latch = m.groups()
        trigger, lot, lot2, latch = int(trigger), int(lot), int(lot2), int(latch)
        triggers.add(trigger)
        pairs.add((trigger, latch))
        lotflag = lot2flag.get(lot)
        if lotflag is not None and lotflag != latch:
            pairs.add((trigger, lotflag))
        if lot2 == 0:
            lot2_zero += 1
    if not pairs:
        sys.exit("FATAL: ZERO 1100/1200 inits parsed from common.emevd.dcx.js -- the corpus "
                 "shape changed. Nothing written.")
    total_inits = sum(1 for _ in RX_BOSS.finditer(common))
    if lot2_zero != total_inits:
        sys.exit("FATAL: %d of %d 1100/1200 inits carry a nonzero lot2 -- the second award would "
                 "be swept blind. Teach boss_pairs to join lot2's flag first. Nothing written."
                 % (total_inits - lot2_zero, total_inits))
    # Setter audit (reported, not gated -- see the module docstring for the measured distribution
    # and why multi-map/parameterized setters keep the sweep vanilla-equivalent).
    setter_sites = {t: [] for t in triggers}
    for fn, text in texts.items():
        for m in RX_SET_ON.finditer(text):
            flag = int(m.group(1))
            if flag in setter_sites:
                setter_sites[flag].append(fn)
    audit = Counter(len(v) for v in setter_sites.values())
    return pairs, triggers, audit


def main():
    if not os.path.isdir(EVENT_DIR):
        sys.exit("FATAL: %s missing -- run tools/gen_inputs.py --ensure elden_ring_artifacts. "
                 "Nothing written." % EVENT_DIR)
    if not os.path.isfile(FLAG_LOTS):
        sys.exit("FATAL: greenfield/flag_lots.tsv missing -- the lot->check join needs it. "
                 "Nothing written.")
    lot2flag = {}
    with open(FLAG_LOTS, encoding="utf-8-sig") as fh:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                continue
            p = ln.rstrip("\n").split("\t")
            if p[0].isdigit() and len(p) > 2 and p[1] == "map":
                lot2flag[int(p[2])] = int(p[0])

    texts = load_corpus()
    if not texts:
        sys.exit("FATAL: %d event file(s) scanned and ZERO readable -- the corpus shape changed. "
                 "Nothing written." % len(texts))
    pairs, values = corpse_pairs(texts, lot2flag)
    if not pairs:
        sys.exit("FATAL: %d event file(s) scanned and ZERO sweepable corpse pairs found -- the "
                 "corpus shape changed. Nothing written." % len(texts))
    n_corpse = len(pairs)
    b_pairs, triggers, audit = boss_pairs(texts, lot2flag)
    pairs |= b_pairs

    out = {
        "comment": ("AUTO-GENERATED by tools/gen_death_award_pairs.py -- (trigger flag, check flag) "
                    "pairs for EMEVD death-driven awards: corpse-treasure (value==0 sites only, "
                    "clients#385) and the 1100/1200 boss-award latches (clients#395). Trigger UP "
                    "+ check DOWN in a save = the award was missed and is unrecoverable in-game; "
                    "the client fires the check. The trigger here is the award latch/death flag, "
                    "set exactly when the game records the kill."),
        "pairs": [{"death_flag": d, "check_flag": c} for d, c in sorted(pairs)],
    }
    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("death_award_pairs: %d sweepable pair(s) written "
          "(%d corpse [value dist over check-joined inits: %s; non-zero EXCLUDED -- their corpses "
          "re-offer] + %d boss-award [1100/1200 latches + split great-rune lot flags]) -> %s"
          % (len(pairs), n_corpse, dict(sorted(values.items())), len(b_pairs),
             os.path.relpath(OUT, REPO)))
    print("boss-award trigger setter audit (literal SetEventFlagID?(trigger, ON) sites per "
          "trigger): %s -- see the module docstring for why 0/2+ counts stay vanilla-equivalent"
          % dict(sorted(audit.items())))


if __name__ == "__main__":
    main()
