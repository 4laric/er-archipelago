#!/usr/bin/env python3
"""check_sweep_cut_partition.py -- the sweep cut is written down three times; make them agree.

A dungeon sweep's membership is decided in two places that never see each other:

* `greenfield/gen_data.py` BAKES the member lists at regen time, cutting `_SWEEP_NEVER_TAGS` -- the
  permanent floor: another boss's reward, a Remembrance, a Great Rune, a key item, merchant stock.
* `greenfield/eldenring/features/boss_locks.py` cuts `_SWEEP_SURFACE_CUTTABLE` PER SEED against
  that seed's Progression Surface -- the collectathon and rarity lines, which are ordinary loot
  unless the player said they may hold progression.

Two failures follow from that split, and neither has a natural owner:

1. A CLASS FALLS THROUGH THE CRACK. `contract.SURFACE_CLASSES` is the vocabulary. A new premium
   class filed in NEITHER set is baked into every sweep and cut by nobody -- the sweep silently
   starts handing it out. The halves must PARTITION the vocabulary so adding a class forces a
   decision instead of defaulting to "sweepable".
2. THE BAKE ADMITS WHAT THE CUT CANNOT REACH. If gen_data admits a class the feature does not name,
   the per-seed cut cannot take it back and the surface option quietly stops covering it. The two
   `_SWEEP_SURFACE_CUTTABLE` copies must be IDENTICAL, not merely compatible.

Why a tools/ gate and not a unit test: the apworld suite runs against an INSTALLED world and
`gen_data.py` is not installed, so a test that reads it there can only SKIP -- a green tick over
nothing. This runs in the generators job, where the whole repo is on disk. AP-free by construction:
it reads the three files as TEXT and never imports them (gen_data needs `elden_ring_artifacts`,
boss_locks needs Archipelago).
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(REPO, "greenfield", "gen_data.py")
FEATURE = os.path.join(REPO, "greenfield", "eldenring", "features", "boss_locks.py")
CONTRACT = os.path.join(REPO, "greenfield", "eldenring", "contract.py")


def _members(path, name, opener, closer):
    """The string members of a `name = <opener>...<closer>` literal in `path`.

    Textual and STRICT: a missing constant is an error and an empty parse is an error. An empty set
    would make every comparison below pass vacuously -- the exact shape of the
    `getattr(contract, "IMPORTANT_LOCATION_TYPES", ())` hole this repo has already been bitten by.
    """
    src = open(path, encoding="utf-8").read()
    m = re.search(re.escape(name) + r"\s*=\s*" + opener + r"(.*?)" + closer, src, re.S)
    if m is None:
        sys.exit("check_sweep_cut_partition: FAIL %s has no `%s` literal. The sweep cut moved or "
                 "was renamed; this gate cannot speak for it."
                 % (os.path.relpath(path, REPO), name))
    found = re.findall(r'"([A-Za-z]+)"', m.group(1))
    if not found:
        sys.exit("check_sweep_cut_partition: FAIL %s's `%s` parsed EMPTY -- refusing to compare "
                 "against nothing." % (os.path.relpath(path, REPO), name))
    return set(found)


def main():
    vocab = _members(CONTRACT, "SURFACE_CLASSES", r"\[", r"\]")
    floor = _members(GEN, "_SWEEP_NEVER_TAGS", r"frozenset\(\{", r"\}\)")
    cut_gen = _members(GEN, "_SWEEP_SURFACE_CUTTABLE", r"frozenset\(\{", r"\}\)")
    cut_feat = _members(FEATURE, "_SWEEP_SURFACE_CUTTABLE", r"frozenset\(\{", r"\}\)")
    # The THIRD bucket, added with SweepSlot. Every other vocabulary member names a location TAG, so
    # the question "is a check of this class sweepable?" has an answer gen_data can bake. A DERIVED
    # class has no tag at all -- it IS a sweep member, chosen per seed -- so it belongs to neither
    # half, and the "unfiled" check below would otherwise demand it be filed in one of them and be
    # wrong either way. It still has to be declared, in contract, on purpose: falling through the
    # crack silently is exactly what this gate exists to stop.
    derived = _members(CONTRACT, "SURFACE_DERIVED_CLASSES", r"frozenset\(\{", r"\}\)")

    fails = []
    both_derived = derived & (floor | cut_gen)
    if both_derived:
        fails.append("%s is declared DERIVED but is also cut by the sweep. A derived class is a "
                     "sweep member by definition; cutting it deletes the class." % sorted(both_derived))
    stray = derived - vocab
    if stray:
        fails.append("%s is in contract.SURFACE_DERIVED_CLASSES but not in SURFACE_CLASSES, so no "
                     "player can select it and nothing evaluates it." % sorted(stray))
    both = floor & cut_gen
    if both:
        fails.append("%s is in BOTH halves: it reads as permanently excluded while its per-seed "
                     "cut silently does nothing." % sorted(both))
    unfiled = vocab - floor - cut_gen - derived
    if unfiled:
        fails.append("%s is in contract.SURFACE_CLASSES but in NEITHER half, so it is baked into "
                     "every sweep and cut by nobody. File it in gen_data._SWEEP_NEVER_TAGS (never "
                     "sweepable) or _SWEEP_SURFACE_CUTTABLE (sweepable unless the seed's "
                     "Progression Surface claims it)." % sorted(unfiled))
    invented = (floor | cut_gen) - vocab
    if invented:
        fails.append("%s is cut by the sweep but is not a contract.SURFACE_CLASSES member -- no "
                     "location can carry it, so the cut is dead text." % sorted(invented))
    if cut_gen != cut_feat:
        fails.append("gen_data admits %s but features/boss_locks can only cut %s; the difference "
                     "(%s) is baked into every sweep with no per-seed cut behind it."
                     % (sorted(cut_gen), sorted(cut_feat), sorted(cut_gen ^ cut_feat)))

    if fails:
        for f in fails:
            print("check_sweep_cut_partition: FAIL " + f)
        return 1
    print("check_sweep_cut_partition: OK -- %d classes partition into %d never-sweepable + %d "
          "surface-cuttable + %d derived, and the feature cuts all %d."
          % (len(vocab), len(floor), len(cut_gen), len(derived), len(cut_feat)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
