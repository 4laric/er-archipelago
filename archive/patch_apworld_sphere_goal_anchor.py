#!/usr/bin/env python3
r"""patch_apworld_sphere_goal_anchor.py

Goal-anchor the sphere-ordered completion-scaling denominator so the GOAL region lands at
tier 1.0, with a smooth ramp up to it.

BUG (visible in ER_SPHERE_TIERS.txt): the sphere emit normalizes each region as
    _d = sphere / maxSphere ;  target = floor + curve(_d) * (1 - floor)
with maxSphere = the DEEPEST sphere any region reaches. Under minimal accessibility off-path
side content sweeps PAST the goal, so that junk bucket -- not the goal -- becomes the 1.0
anchor; the capital came out at 0.44 while off-path caves sat at 1.0. Backwards.

FIX: walk the spheres (mirroring MultiWorld.get_spheres) to find the first sphere where THIS
player's completion_condition holds (the goal-reach sphere), then anchor maxSphere on the goal
REGION's own sphere -- reach_sphere + 1, where its checks enumerate -- capped so genuinely
post-goal off-path regions don't inflate it. _d is clamped to 1.0 so anything deeper caps at
1.0. Result, e.g. a capital run: 0 -> 0.17 -> 0.52 -> 1.0 with the capital at 1.0.

Anchoring on the goal REGION's sphere (rather than the reach sphere) gives one extra gradient
step and puts the goal exactly at its own sphere = 1.0; it also stays correct when the goal
item is placed INSIDE the goal region (reach == region sphere), via the `<= _anchor` cap.

Handles three states: (a) fresh full source -> inserts the block + clamp; (b) v1 reach-anchored
block already applied -> upgrades it in place; (c) already region-anchored -> skips. Run on
Windows from repo root (or the eldenring apworld dir):
    python patch_apworld_sphere_goal_anchor.py
Order-independent w.r.t. patch_apworld_sphere_kept_only.py. CRLF-safe; idempotent.
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
def conv(s):
    return s.replace("\n", nl.decode("ascii")).encode("utf-8")

# The region-anchor distinguishing marker (present only in v2).
V2_TAIL = (
    "                if _goal_sph and _goal_sph >= 1:\n"
    "                    # Anchor on the goal REGION's sphere (goal-reach sphere + 1, where its\n"
    "                    # checks enumerate) instead of the reach sphere, so the played chain gets\n"
    "                    # one more gradient step and the goal region sits at exactly 1.0 at its\n"
    "                    # own sphere. Cap at goal_sph+1 so genuinely-post-goal off-path regions\n"
    "                    # don't inflate the denominator (they're clamped to 1.0 below).\n"
    "                    _anchor = _goal_sph + 1\n"
    "                    _maxsph = max(1, max((_s for _s in _region_sphere.values() if _s <= _anchor),\n"
    "                                         default=_goal_sph))\n"
)
V1_TAIL = (
    "                if _goal_sph and _goal_sph >= 1:\n"
    "                    _maxsph = _goal_sph\n"
)

if conv("Anchor on the goal REGION's sphere") in b:
    print("  [skip] region-anchored goal scaling already present.")
    sys.exit(0)

# (b) Upgrade an already-applied v1 reach-anchored block in place.
if conv(V1_TAIL) in b:
    if b.count(conv(V1_TAIL)) != 1:
        sys.exit("  [FAIL] v1 reach-anchor block found %d times (expected 1)." % b.count(conv(V1_TAIL)))
    b = b.replace(conv(V1_TAIL), conv(V2_TAIL), 1)
    with open(P, "wb") as f:
        f.write(b)
    print("  [ok]   upgraded reach-anchor -> region-anchor (one extra gradient step; goal = 1.0).")
    print("DONE -- regen and eyeball ER_SPHERE_TIERS.txt.")
    sys.exit(0)

if conv("Goal-anchored denominator") in b:
    sys.exit("  [FAIL] goal-anchor block present but not in the expected v1 form; not modified.")

# (a) Fresh apply: insert the full block + clamp.
A = "            for _rn, _sph in _region_sphere.items():\n"
B = "                _d = _sph / _maxsph\n"
for name, anc in (("A", A), ("B", B)):
    if b.count(conv(anc)) != 1:
        sys.exit("  [FAIL] anchor %s found %d times (expected 1). Is "
                 "patch_apworld_sphere_scaling.py applied unmodified?" % (name, b.count(conv(anc))))

GOAL_BLOCK = (
    "            # --- Goal-anchored denominator (capital/Morgott, godrick, messmer, region_count...) ---\n"
    "            # The completion region must land at tier 1.0, not whatever off-path region sweeps\n"
    "            # last under minimal accessibility. Walk the spheres (mirrors get_spheres) to find\n"
    "            # the first sphere where THIS player's completion_condition holds (goal-reach), then\n"
    "            # anchor maxSphere on the goal region's own sphere. _d is clamped to 1.0 below so\n"
    "            # regions deeper than the goal cap at 1.0. Falls back to prior maxSphere if the\n"
    "            # condition can't be evaluated -> inert / old behavior.\n"
    "            try:\n"
    "                from BaseClasses import CollectionState as _CS\n"
    "                _cc = self.multiworld.completion_condition.get(self.player)\n"
    "                _goal_sph = None\n"
    "                if _cc is not None:\n"
    "                    _gs = _CS(self.multiworld)\n"
    "                    for _gi, _gsphere in enumerate(_spheres):\n"
    "                        for _gloc in _gsphere:\n"
    "                            if getattr(_gloc, \"item\", None) is not None:\n"
    "                                _gs.collect(_gloc.item, True, _gloc)\n"
    "                        if _cc(_gs):\n"
    "                            _goal_sph = _gi\n"
    "                            break\n"
    + V2_TAIL +
    "            except Exception:\n"
    "                pass\n"
)

b = b.replace(conv(A), conv(GOAL_BLOCK) + conv(A), 1)
b = b.replace(conv(B), conv("                _d = min(1.0, _sph / _maxsph)\n"), 1)
with open(P, "wb") as f:
    f.write(b)
print("  [ok]   goal-anchored (region sphere) denominator + clamp applied (goal region -> tier 1.0).")
print("DONE -- regen and eyeball ER_SPHERE_TIERS.txt: the goal region should read 1.0.")
