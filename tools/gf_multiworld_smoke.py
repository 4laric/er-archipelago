#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gf_multiworld_smoke.py -- generate a REAL multiworld and assert the cross-world properties.

WHY THIS EXISTS (Alaric, 2026-07-28). Everything that gates this apworld generates ONE world:
`gf_test`, the fuzz, the fill regression, the ZIP-GEN smoke. So every claim about how Elden Ring
behaves BESIDE other games has been argued rather than observed -- and on 2026-07-28 that produced a
concrete cost. A review of the player guide's `natural_progression` bullet ("keys are shuffled into
the multiworld ... anywhere and anyone's") reported the opposite: in a single-player harness every
key came back placed locally and locked. That reading was right about what it saw and wrong about
the game, and NOTHING IN CI COULD TELL THE TWO APART, because nothing in CI had ever run two slots.

This runs two Elden Ring slots beside two slots of a PARTNER game, once per partner. The partners
ship with Archipelago, are pure Python with no ROM and no extra pip dependency, and are realistic
rather than stubs -- a test world would not exercise a real foreign item pool.

WHY MORE THAN ONE PARTNER (2026-08-09). With a single partner, "ER reaches a foreign GAME" and "ER
reaches Hollow Knight" are the same sentence, and the difference is not academic: a sweep of
`region_locks_anywhere` measured the share of released region Locks that reach the partner at
0.30% (Terraria, 63 locations/slot), 0.46% (Hollow Knight, 203), 1.18% (TUNIC, 302), 1.80%
(DOOM 1993, 348) and 3.50% (Stardew Valley, 472) -- monotone in the partner's SIZE, over 24 seeds a
cell. Every cross-world number this apworld reports is therefore a number about the partner as much
as about us, and one partner cannot show that. The list is deliberately spread: ~100, ~200 and ~350
locations per slot.

🛑 TWO PARTNERS WERE TRIED AND REJECTED, and not for generating badly. Meritous (104 locations, 9
advancement) and Terraria (63 / 10) both generate clean and fast, but their advancement pools are so
thin that in 4 of 24 and 2 of 24 seeds respectively ONE ER slot received no foreign progression at
all -- which is precisely the vacuous pass `check_foreign_confinement` refuses to give. A partner
must be big enough to keep that check loaded; sizes here were chosen against measured zero-counts,
not reputation. (Bumper Stickers is small -- 100 locations -- but 63 of them are advancement, so it
brackets the low end without starving the check.)

WHAT IT ASSERTS, and none of it is "it generated". Every item runs ONCE PER PARTNER:

  1. CROSS-WORLD FLOW HAPPENS, BOTH WAYS. ER items reach foreign locations AND foreign items reach
     ER locations. A regression that quietly confined everything to its own world -- which is what a
     mis-set `local_item_only` or a broken `filler_foreign_pct` looks like -- generates perfectly and
     passes every single-player gate we have.
  2. ER REACHES A NON-ER GAME specifically. ER-to-ER traffic alone would satisfy (1) while the world
     was in fact unable to place into a foreign game.
  3. THE MOTIVATING CASE, BY NAME (CONTRIBUTING rule 11): under `natural_progression`, real vanilla
     keys land in OTHER players' worlds. Measured 2026-07-28: 42 placed, 12 foreign, including a
     Cursemark of Death in a Hollow Knight slot; re-measured 2026-08-03 on the same pinned seed:
     42 placed, 8 foreign. The floor asserted is `> 0`, not either number -- the counts move with
     fill and the guide's promise is only that they CAN travel.
  4. THE SLOT_DATA A SECOND SLOT ACTUALLY GETS. Three properties that a solo harness cannot even
     pose, all read off the multidata:
       a) `checkItemFlags` flags are a SUBSET of that slot's own `locationFlags` values. A flag
          outside it can never enter the client's collected-set, so its id is suppressed for the
          whole run FROM EVERY SOURCE and no amount of play releases it (#321's family).
       b) NO flag is mapped by TWO item ids -- the precondition the client checks at connect before
          enabling the flag-set disarm (er_logic::vanilla_suppress::flags_are_unshared). The world
          gate for this runs at `num_regions: 0` in the unit suite; here it runs on the SHIPPED
          yaml, twice, beside a foreign game.
       c) PER-SLOT INDEPENDENCE: two ER slots that kept DIFFERENT regions must emit DIFFERENT
          tables, and two that kept the same must emit the same. The world module is imported once
          for the whole generation, so any cross-slot cache hands slot 2 slot 1's tables -- and
          that is invisible to every single-slot gate we have.

  🛑 WHAT USED TO BE HERE. Item 4 was "NO AP-ID COLLISION between the two ER slots -- each slot's
  ids are its own." The code behind it parsed `[f12345]` out of location NAMES -- those are EVENT
  FLAGS, not AP ids -- and then, if the two sets were equal, printed `note: ... (expected)` and
  never touched `bad`. It could not fail. It was also unfalsifiable as posed: two slots of the same
  game share a datapackage, so their location ids ARE identical by construction, and the property
  that matters (placements are keyed by (slot, location)) is an AP structural guarantee, not ours.
  Deleted rather than repaired -- a green predicate that cannot go red is a comment with a runtime.

🛑 IT IS A SMOKE TEST, NOT A FILL REGRESSION. One seed, one option set, per partner. It answers "do
the cross-world properties hold at all", not "do they hold across the option matrix" -- `fuzz_gf.py`
and `run_fill_regression.ps1` own that, single-world. A green run here means the multiworld path is
not BROKEN; it does not mean it is tuned.

USAGE
    python tools/gf_multiworld_smoke.py --ap-dir <archipelago checkout>
    python tools/gf_multiworld_smoke.py --ap-dir <ap> --keep          # leave the output on disk
    python tools/gf_multiworld_smoke.py --ap-dir <ap> --partner hk    # one partner, for triage

Exit 0 pass, 1 fail, 4 SKIP (NO partner world is present in this Archipelago checkout -- a sparse
clone; CI checks out stock upstream in full, so it runs there).
"""
import argparse
import collections
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_AP_DIR = []   # set in main(); multidata() needs the AP root importable for Utils
ROOT = os.path.dirname(HERE)
SEED = "20260728"

# A spoiler line in a MULTIWORLD is `Location (Owner): Item (Owner)`; in a solo seed it has no
# parentheses at all. Anchoring on the 4-tuple is what makes this test structurally unable to pass
# on a single-player generation.
_ROW = re.compile(r"^(.*?) \(([^)]+)\): (.*?) \(([^)]+)\)$", re.M)

# The real vanilla keys natural_progression puts into circulation. Substring match on purpose --
# "Rykard's Great Rune" and "Remembrance of Hoarah Loux" are both members and neither is a fixed id.
_KEYS = ("Dectus", "Haligtree Secret Medallion", "Rold Medallion", "Remembrance", "Great Rune",
         "Academy Glintstone Key", "Carian Inverted Statue", "Pureblood", "Cursemark")

_Partner = collections.namedtuple("_Partner", "dir game slot body")

# THE PARTNER LIST. `dir` is the worlds/ package -- it is what decides SKIP, because a game NAME
# tells you nothing about whether this checkout carries it. `slot` prefixes the two slot names, so a
# spoiler and every message below still say which partner they are about. `body` is the game's own
# option block: kept as short as the game allows, because a partner's job here is to be a real
# foreign pool, not to be tuned.
#
# 🛑 EVERY ENTRY WAS GENERATED BEFORE IT WAS ADDED, headless, in a stock 0.6.7 checkout with the
# curated requirement set -- no ROM, no extra pip install, no prompt. That matters more than it
# sounds: only 49 of the 91 packages in worlds/ even IMPORT under those requirements (the rest want
# jellyfish, zilliandomizer, ... ), and an unimportable game does not fail loudly here, it fails as
# "unknown game" in yaml validation.
PARTNERS = (
    _Partner("hk", "Hollow Knight", "Hallownest", """  progression_balancing: 0
  accessibility: minimal
  RandomizeDreamers: true
  RandomizeSkills: true
  RandomizeCharms: true
  RandomizeKeys: true
  RandomizeGeoChests: false
  RandomizeMaps: false
"""),
    # ~100 locations/slot, but 63 of them advancement -- the small end of the bracket that still
    # keeps check_foreign_confinement loaded. See the rejected-partner note in the module docstring.
    _Partner("bumpstik", "Bumper Stickers", "Bumpstik", """  progression_balancing: 0
  accessibility: minimal
"""),
    # ~348 locations/slot, the large end. Measured 1.80% of released region Locks reaching it
    # against 0.46% for Hollow Knight on the same ER options -- the spread this list exists for.
    _Partner("doom_1993", "DOOM 1993", "Doomguy", """  progression_balancing: 0
  accessibility: minimal
"""),
)


def _partner_yaml(partner, n):
    return ("name: %s%d\ngame: %s\ndescription: multiworld smoke partner\n%s:\n%s"
            % (partner.slot, n, partner.game, partner.game, partner.body))


def _er_yaml(name, natural):
    """The SHIPPED template, edited minimally -- so this tests what players actually generate."""
    src = os.path.join(ROOT, "release", "EldenRing.yaml")
    s = open(src, encoding="utf-8").read()
    s = re.sub(r"^name:.*$", "name: %s" % name, s, count=1, flags=re.M)
    # Small map: the cross-world properties do not need 31 regions, and CI time is not free.
    s = re.sub(r"^(\s*)num_regions:\s*\d+\s*$", r"\g<1>num_regions: 4", s, count=1, flags=re.M)
    if natural:
        s = re.sub(r"^(\s*)natural_progression:\s*false\s*$",
                   r"\g<1>natural_progression: true", s, count=1, flags=re.M)
    return s


def generate(ap_dir, players_dir, out_dir):
    """Run Generate.py. `--spoiler 1` = placements WITHOUT the playthrough calculation, which is the
    expensive half and which this test does not read."""
    env = dict(os.environ, AP_NONINTERACTIVE="1", SKIP_REQUIREMENTS_UPDATE="1")
    cmd = [sys.executable, "Generate.py", "--player_files_path", players_dir,
           "--outputpath", out_dir, "--spoiler", "1", "--seed", SEED]
    p = subprocess.run(cmd, cwd=ap_dir, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        tail = "\n".join(p.stdout.strip().split("\n")[-25:])
        sys.exit("FAIL: multiworld generation exited %d.\n%s" % (p.returncode, tail))
    zips = glob.glob(os.path.join(out_dir, "*.zip"))
    if not zips:
        sys.exit("FAIL: generation reported success but wrote no archive.")
    return zips[0]


# AP location flags bitfield: bit 0 = advancement (progression). Read from the multidata rather than
# guessed from item names -- a name heuristic would silently mis-class every partner game.
_FLAG_ADVANCEMENT = 0b001


def multidata(zip_path):
    """(slot_info, slot_data, locations) out of the .archipelago payload.

    The SPOILER cannot answer the confinement question: it names items but does not say which are
    advancement, and it does not carry slot_data. The multidata carries both, so the check below is
    made of the same facts the server runs on.
    """
    import zlib
    import Utils  # noqa: PLC0415  -- importable because main() put the AP root on sys.path
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if n.endswith(".archipelago")]
    if not names:
        sys.exit("FAIL: the archive carries no .archipelago multidata.")
    raw = z.read(names[0])
    md = Utils.restricted_loads(zlib.decompress(raw[1:]))
    return md["slot_info"], md.get("slot_data", {}), md["locations"]


def check_foreign_confinement(slot_info, slot_data, locations, report):
    """`confine_foreign_progression` (default ON): another world's ADVANCEMENT items may land only on
    THIS world's progression surface, never on its filler checks.

    🛑 THE OPTION'S OWN DOCSTRING SAYS "No effect in a solo seed". So until there was a multiworld in
    CI this promise had never been executed even once -- it is the single most multiworld-shaped
    property the apworld has, and it was also the least tested.
    """
    bad = []
    for player, info in sorted(slot_info.items()):
        if info.game != "Elden Ring":
            continue
        sd = slot_data.get(player) or {}
        surface = set(sd.get("progressionSurfaceLocations") or ())
        if not surface:
            bad.append("slot %d (Elden Ring) emitted an EMPTY progressionSurfaceLocations, so this "
                       "check would pass over nothing." % player)
            continue
        rows = locations.get(player) or {}
        foreign = [(lid, ip) for lid, (_iid, ip, fl) in rows.items()
                   if ip != player and (fl & _FLAG_ADVANCEMENT)]
        offsurface = [lid for lid, _ip in foreign if lid not in surface]
        donors = sorted({slot_info[ip].game for _l, ip in foreign})
        report("slot %d: surface %d, foreign progression placed here %d (from %s), off-surface %d"
               % (player, len(surface), len(foreign), ", ".join(donors) or "-", len(offsurface)))
        if not foreign:
            bad.append(
                "slot %d received NO foreign progression at all, so confine_foreign_progression was "
                "not exercised. Either fill placed none this seed (re-check the partner's pool) or "
                "the surface is barring everything -- a vacuous pass either way." % player)
        if offsurface:
            bad.append(
                "slot %d: %d foreign progression item(s) landed OFF the progression surface, e.g. "
                "location %s. confine_foreign_progression is default-ON and promises another world's "
                "advancement items only ever sit on your surface checks -- a player who took that "
                "promise would be hunting a key on a Smithing Stone pickup."
                % (player, len(offsurface), offsurface[0]))
    return bad


def check_slot_data_tables(slot_info, slot_data, report):
    """The three slot_data properties a SOLO harness cannot pose. Reads the multidata, so these are
    the same bytes the client parses at connect -- not the world object's in-process view."""
    bad = []
    er = [(p, slot_data.get(p) or {}) for p, i in sorted(slot_info.items()) if i.game == "Elden Ring"]
    if len(er) < 2:
        return ["expected at least 2 Elden Ring slots in the multidata; saw %d" % len(er)]

    for player, sd in er:
        cif = sd.get("checkItemFlags") or {}
        locflags = sd.get("locationFlags") or {}
        if not cif:
            bad.append(
                "slot %d emitted an EMPTY checkItemFlags. The client logs `vanilla suppressor "
                "INERT` and every lot-less check hands out its vanilla ware alongside the AP item. "
                "An empty table also makes (a) and (b) below pass over nothing." % player)
            continue
        if not locflags:
            bad.append("slot %d emitted an EMPTY locationFlags -- the flag poll is blind and no "
                       "check can register." % player)
            continue

        # (a) every armed flag must be reachable by the client's collected-set.
        loc_values = {int(v) for v in locflags.values()}
        armed = {int(f) for flags in cif.values() for f in flags}
        orphan = sorted(armed - loc_values)
        # (b) the flag-set disarm precondition.
        owners = collections.defaultdict(set)
        for full, flags in cif.items():
            for f in flags:
                owners[int(f)].add(str(full))
        shared = {f: sorted(ids) for f, ids in owners.items() if len(ids) > 1}

        report("slot %d: checkItemFlags %d id(s) / %d flag(s), locationFlags %d | orphan flags %d | "
               "flags mapped by 2+ ids %d" % (player, len(cif), len(armed), len(locflags),
                                              len(orphan), len(shared)))
        if orphan:
            bad.append(
                "slot %d: %d armed flag(s) are NOT values in that slot's own locationFlags, e.g. "
                "%s. Such a flag can never enter the client's collected-set, so `should_suppress` "
                "stays true for its item id for the WHOLE RUN, from every source -- including its "
                "own check, which then never delivers either."
                % (player, len(orphan), orphan[:5]))
        if shared:
            f0 = next(iter(shared))
            bad.append(
                "slot %d: %d acquisition flag(s) are mapped by MORE THAN ONE item id, e.g. flag %s "
                "-> ids %s. The client checks exactly this at connect (flags_are_unshared) before "
                "enabling the flag-set disarm, because setting one id's flag would otherwise "
                "release a neighbour whose check never fired -- the Traveler's Clothes leak. This "
                "seed would silently fall back to collected-set-only."
                % (player, len(shared), f0, shared[f0][:4]))

    # (c) PER-SLOT INDEPENDENCE. The world module is imported once for the whole generation.
    (pa, a), (pb, b) = er[0], er[1]
    locks_a = set((a.get("regionOpenFlags") or {}))
    locks_b = set((b.get("regionOpenFlags") or {}))
    same_regions = locks_a == locks_b
    lf_a, lf_b = set((a.get("locationFlags") or {})), set((b.get("locationFlags") or {}))
    cif_a, cif_b = set((a.get("checkItemFlags") or {})), set((b.get("checkItemFlags") or {}))
    report("slots %d vs %d: same kept regions=%s | locationFlags identical=%s (sym-diff %d) | "
           "checkItemFlags identical=%s (sym-diff %d)"
           % (pa, pb, same_regions, lf_a == lf_b, len(lf_a ^ lf_b),
              cif_a == cif_b, len(cif_a ^ cif_b)))
    if not same_regions and lf_a == lf_b:
        bad.append(
            "slots %d and %d kept DIFFERENT regions (%s vs %s) but emitted IDENTICAL locationFlags. "
            "The tables are scoped to `[HUB] + world._kept()`, so identical output from different "
            "region sets means one slot is reading the other's state -- the cross-slot cache class "
            "that no single-slot gate can see."
            % (pa, pb, sorted(locks_a - locks_b)[:3], sorted(locks_b - locks_a)[:3]))
    if same_regions and lf_a != lf_b:
        bad.append(
            "slots %d and %d kept the SAME regions but emitted DIFFERENT locationFlags (%d ids "
            "differ). The table is a pure function of the kept set, so this is non-determinism in "
            "a structure the client trusts to be stable." % (pa, pb, len(lf_a ^ lf_b)))
    return bad


def placements(zip_path):
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if "Spoiler" in n]
    if not names:
        sys.exit("FAIL: the archive carries no spoiler, so nothing can be asserted about placement.")
    rows = _ROW.findall(z.read(names[0]).decode("utf-8", errors="replace"))
    if not rows:
        sys.exit("FAIL: parsed ZERO placements. Either the spoiler format changed or this was a solo "
                 "seed -- an empty result is a failure, not a clean run.")
    return rows


def check(rows, natural, report, partner):
    """-> list of failure strings. Every check names what a green would have hidden."""
    bad = []
    er = {p for _l, p, _i, _ip in rows if p.startswith("Erdtree")}
    foreign_slots = {p for _l, p, _i, _ip in rows if p.startswith(partner.slot)}
    if len(er) < 2 or len(foreign_slots) < 2:
        bad.append("expected 2 Elden Ring and 2 %s slots; saw ER=%s partner=%s"
                   % (partner.game, sorted(er), sorted(foreign_slots)))
        return bad

    out_of_er = [(l, lp, i, ip) for l, lp, i, ip in rows if ip in er and lp != ip]
    into_er = [(l, lp, i, ip) for l, lp, i, ip in rows if lp in er and ip != lp]
    to_partner = [r for r in out_of_er if r[1] in foreign_slots]
    report("cross-world: %d ER items placed abroad (%d of them in %s), %d foreign items placed in ER"
           % (len(out_of_er), len(to_partner), partner.game, len(into_er)))

    # 1 + 2. Floors are deliberately low: this asserts the PATH works, not a distribution.
    if not out_of_er:
        bad.append("NO Elden Ring item reached another player's world. Every ER item stayed home -- "
                   "which is what a broken filler_foreign_pct or a stuck local_item_only looks like, "
                   "and it generates and passes every single-world gate we have.")
    if not into_er:
        bad.append("NO foreign item was placed on an Elden Ring location. ER accepted nothing from "
                   "the multiworld.")
    if not to_partner:
        bad.append("ER items reached other ER slots but NOT %s. ER-to-ER traffic alone would satisfy "
                   "a naive cross-world check while the world was unable to place into a foreign "
                   "GAME." % partner.game)

    # 3. THE MOTIVATING CASE.
    if natural:
        keys = [(l, lp, i, ip) for l, lp, i, ip in rows
                if ip in er and any(k in i for k in _KEYS)]
        foreign = [r for r in keys if r[1] != r[3]]
        report("natural_progression: %d key/remembrance item(s) placed, %d in ANOTHER player's world"
               % (len(keys), len(foreign)))
        if not keys:
            bad.append("natural_progression produced NO real vanilla keys. The mode's whole premise "
                       "is that regions open on real keys -- if none exist, it is not doing anything.")
        elif not foreign:
            bad.append(
                "under natural_progression, EVERY real key stayed in its own world. The player guide "
                "promises they are 'shuffled into the multiworld ... anywhere and anyone's'. Either "
                "the guide is now wrong or placement regressed. (Measured 2026-07-28: 42 keys, 12 "
                "foreign, including a Cursemark of Death in a Hollow Knight slot.)")
        else:
            report("   e.g. %s (%s) -> %s (%s)" % (foreign[0][2][:38], foreign[0][3],
                                                   foreign[0][0][:38], foreign[0][1]))
    return bad


def self_test():
    """Fire every branch of `check_slot_data_tables` DELIBERATELY.

    🛑 WHY THIS EXISTS. The three properties this file added are all currently TRUE, so a green
    smoke run proves the checks were reached -- not that they can go red. CONTRIBUTING: "an unfired
    guard is UNTESTED". Every case below is a hand-built slot_data that must FAIL, plus one that
    must PASS, so a future refactor that silently defangs a branch is caught here instead of the
    next time the property actually breaks.

    Costs no generation and no Archipelago -- runs in milliseconds, so CI can run it before the
    expensive half and fail fast.
    """
    class _Info:
        def __init__(self, game):
            self.game = game

    ER = {1: _Info("Elden Ring"), 2: _Info("Elden Ring"), 3: _Info("Hollow Knight")}

    def sd(cif, locflags, locks):
        return {"checkItemFlags": cif, "locationFlags": locflags, "regionOpenFlags": locks}

    # A clean pair: two slots, different kept regions, different tables, every flag collectable
    # and owned by exactly one id.
    good_a = sd({"100": [11], "200": [12]}, {"7770001": 11, "7770002": 12}, {"Limgrave Lock": 1})
    good_b = sd({"300": [21]}, {"7770003": 21}, {"Caelid Lock": 2})

    cases = [
        ("clean pair passes", {1: good_a, 2: good_b}, None),
        ("orphan flag",
         {1: sd({"100": [11], "200": [99]}, {"7770001": 11}, {"Limgrave Lock": 1}), 2: good_b},
         "NOT values in that slot's own locationFlags"),
        ("flag mapped by two ids",
         {1: sd({"100": [11], "200": [11]}, {"7770001": 11}, {"Limgrave Lock": 1}), 2: good_b},
         "mapped by MORE THAN ONE item id"),
        ("different regions, identical tables (cross-slot cache)",
         {1: good_a, 2: sd(good_a["checkItemFlags"], good_a["locationFlags"], {"Caelid Lock": 2})},
         "emitted IDENTICAL locationFlags"),
        ("same regions, different tables (non-determinism)",
         {1: good_a, 2: sd({"300": [21]}, {"7770009": 21}, {"Limgrave Lock": 1})},
         "emitted DIFFERENT locationFlags"),
        ("empty checkItemFlags",
         {1: sd({}, {"7770001": 11}, {"Limgrave Lock": 1}), 2: good_b},
         "EMPTY checkItemFlags"),
        ("empty locationFlags",
         {1: sd({"100": [11]}, {}, {"Limgrave Lock": 1}), 2: good_b},
         "EMPTY locationFlags"),
        ("only one ER slot", {1: good_a}, "expected at least 2 Elden Ring slots"),
    ]

    print("=== self-test: every guard must fire on its own fault ===")
    problems = []
    for name, slots, want in cases:
        info = {p: ER[p] for p in slots} if len(slots) > 1 else {1: ER[1]}
        got = check_slot_data_tables(info, slots, lambda _m: None)
        if want is None:
            if got:
                problems.append("%-52s expected PASS, got: %s" % (name, got[0][:90]))
            else:
                print("  ok    %-52s passes" % name)
        elif not got:
            problems.append("%-52s expected a FAILURE, got a clean pass -- this guard is INERT"
                            % name)
        elif not any(want in f for f in got):
            problems.append("%-52s failed for the WRONG reason: %s" % (name, got[0][:90]))
        else:
            print("  ok    %-52s fails as designed" % name)

    # THE PARTNER LIST ITSELF IS DATA, and a typo in it degrades this whole file to a SKIP rather
    # than a failure -- so it is checked here, where no Archipelago is needed. Duplicate slot
    # prefixes are the sharp one: `check()` selects the partner's slots by name prefix, so two
    # partners sharing a prefix would silently mix pools if the list ever grew by copy-paste.
    if len(PARTNERS) != len({p.dir for p in PARTNERS}):
        problems.append("PARTNERS has a duplicate worlds/ dir")
    if len(PARTNERS) != len({p.slot for p in PARTNERS}):
        problems.append("PARTNERS has a duplicate slot prefix; check() picks slots by prefix")
    for p in PARTNERS:
        if p.slot.startswith("Erdtree"):
            problems.append("partner %s uses an Erdtree* slot prefix, which check() reads as ER"
                            % p.game)
    print("  ok    %-52s %d partner(s), distinct dirs and prefixes"
          % ("partner list is well-formed", len(PARTNERS)))

    if problems:
        print("SELF-TEST: FAIL")
        for pr in problems:
            print("  * %s" % pr)
        return 1
    print("SELF-TEST: PASS -- %d guard(s) proven able to go red\n" % (len(cases) - 1))
    return 0


def run_partner(ap_dir, partner, keep):
    """Both option sets against ONE partner. -> list of failure strings, already labelled."""
    failures = []
    for natural in (False, True):
        mode = "natural_progression ON" if natural else "default (region locks)"
        label = "%s / %s" % (partner.game, mode)   # every failure says WHICH partner produced it
        print("\n=== multiworld: 2x Elden Ring + 2x %s -- %s ===" % (partner.game, mode))
        work = tempfile.mkdtemp(prefix="gf_mw_")
        players, out = os.path.join(work, "players"), os.path.join(work, "out")
        os.makedirs(players); os.makedirs(out)
        try:
            for i, nm in enumerate(("ErdtreeOne", "ErdtreeTwo"), 1):
                open(os.path.join(players, "ER_%d.yaml" % i), "w", encoding="utf-8").write(
                    _er_yaml(nm, natural))
            for n in (1, 2):
                open(os.path.join(players, "P_%d.yaml" % n), "w", encoding="utf-8").write(
                    _partner_yaml(partner, n))
            zip_path = generate(ap_dir, players, out)
            rows = placements(zip_path)
            print("  generated %s -- %d placements" % (os.path.basename(zip_path), len(rows)))
            failures += ["[%s] %s" % (label, f)
                         for f in check(rows, natural, lambda m: print("  " + m), partner)]
            si, sd, locs = multidata(zip_path)
            failures += ["[%s] %s" % (label, f)
                         for f in check_foreign_confinement(si, sd, locs,
                                                            lambda m: print("  " + m))]
            failures += ["[%s] %s" % (label, f)
                         for f in check_slot_data_tables(si, sd, lambda m: print("  " + m))]
        finally:
            if keep:
                print("  kept: %s" % work)
            else:
                shutil.rmtree(work, ignore_errors=True)
    return failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ap-dir", help="an Archipelago checkout with the world installed "
                                     "(not needed with --self-test)")
    ap.add_argument("--keep", action="store_true", help="leave the generated output on disk")
    ap.add_argument("--partner", help="run only this partner (its worlds/ dir, e.g. hk). For "
                                      "triage -- CI runs the whole list.")
    ap.add_argument("--self-test", action="store_true",
                    help="fire every slot_data guard on a hand-built fault and exit. Needs no "
                         "Archipelago and no generation; proves the guards can go RED.")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.ap_dir:
        ap.error("--ap-dir is required unless --self-test is given")

    ap_dir = os.path.abspath(args.ap_dir)
    _AP_DIR.append(os.path.join(ap_dir, "_"))   # multidata() needs the AP root importable for Utils
    sys.path.insert(0, ap_dir)
    if not os.path.isdir(os.path.join(ap_dir, "worlds", "eldenring")):
        sys.exit("FAIL: %s has no worlds/eldenring -- install the world first "
                 "(python tools/gf_test.py --install-only --ap-dir %s)." % (ap_dir, ap_dir))

    wanted = PARTNERS
    if args.partner:
        wanted = tuple(p for p in PARTNERS if p.dir == args.partner)
        if not wanted:
            ap.error("--partner %s is not in PARTNERS (%s)"
                     % (args.partner, ", ".join(p.dir for p in PARTNERS)))
    present = [p for p in wanted if os.path.isdir(os.path.join(ap_dir, "worlds", p.dir))]
    absent = [p for p in wanted if p not in present]
    for p in absent:
        # NOT a silent drop. A partner that vanishes from the checkout takes its coverage with it,
        # and the one thing worse than losing coverage is losing it quietly -- so it is named here
        # and the count is repeated in the PASS line.
        print("note: worlds/%s absent -- %s not exercised in this checkout." % (p.dir, p.game))
    if not present:
        # SKIP, not fail: a sparse/partial checkout legitimately lacks them. CI checks out stock
        # upstream in full. Exit 4 so a harness can tell "not applicable" from "broken" -- the same
        # convention gen_region_locks uses.
        print("SKIP (4): %s carries NONE of the partner worlds (%s), so there is no partner game to "
              "generate beside. This gate needs a full upstream checkout."
              % (ap_dir, ", ".join(p.dir for p in wanted)))
        return 4

    failures = []
    for partner in present:
        failures += run_partner(ap_dir, partner, args.keep)

    print()
    if failures:
        print("MULTIWORLD SMOKE: FAIL")
        for f in failures:
            print("  * %s" % f)
        return 1
    print("MULTIWORLD SMOKE: PASS over %d partner(s) -- %s.\n"
          "      Cross-world flow works in both directions, ER reaches a foreign game, "
          "natural_progression keys\n      are placeable in other players' worlds, foreign "
          "progression lands only on the progression surface,\n      and each slot's "
          "checkItemFlags is collectable, unshared, and its own."
          % (len(present), ", ".join(p.game for p in present)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
