#!/usr/bin/env python3
"""Fix the num_regions POOL + CHAIN double-start-lock (rolled Limgrave has no chain slot).

Limgrave (spine step 1) has no chain lock (NUM_REGIONS_CHAIN_STEP_LOCK starts at step 2), so when
pool mode rolls Limgrave into the kept set under num_regions_chain it can't join the breadcrumb
chain -- its Limgrave Lock falls out as a loose off-chain progression lock that spills into the
start inventory ON TOP of the chain's single free link-0 lock (the observed "two start locks").

Two-part fix:
  1. region_spine.compute_num_regions_scope_pool gains chain_excludes_limgrave; when set it rolls
     from NUM_REGIONS_MIDDLE_STEPS (steps 2-8, no Limgrave) instead of NUM_REGIONS_POOL_STEPS. So
     under chain, Limgrave is never kept -> no off-chain lock, and a guaranteed non-Limgrave start.
  2. __init__ passes num_regions_chain to it, AND the pool re-root now injects Limgrave Lock ONLY
     when Limgrave is actually KEPT this seed (sealed Limgrave must not get a loose lock). This also
     tidies the non-chain pool case (a non-rolled Limgrave no longer gets a useless lock).

Idempotent, CRLF-safe, py_compiles, .bak_poolchain backups. Apply after the num_regions merge patch.
"""
import os, sys, py_compile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPINE = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "region_spine.py")
INIT = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "__init__.py")

# ---- region_spine.py ----
SP_R1_OLD = '''    all_lock_names: Set[str],
    active_cave_steps: Set[int] = frozenset(),
) -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:
    """Resolve a RANDOM short-capital seal scope with the great runes sourced from the POOL.'''
SP_R1_NEW = '''    all_lock_names: Set[str],
    active_cave_steps: Set[int] = frozenset(),
    chain_excludes_limgrave: bool = False,
) -> Tuple[Set[str], Set[str], Set[str], Set[str], int]:
    """Resolve a RANDOM short-capital seal scope with the great runes sourced from the POOL.'''

SP_R2A_OLD = '''    for _cs in _caves:
        _active_cave_dungeons |= set(CAVE_BUNDLE_STEPS[_cs]["regions"])
    max_total = len(NUM_REGIONS_POOL_STEPS) + len(_caves)    # overworld majors + active caves'''
SP_R2A_NEW = '''    for _cs in _caves:
        _active_cave_dungeons |= set(CAVE_BUNDLE_STEPS[_cs]["regions"])
    # chain mode: Limgrave (step 1) has no chain lock (NUM_REGIONS_CHAIN_STEP_LOCK starts at 2), so a
    # rolled Limgrave cannot join the breadcrumb chain -- it leaks a loose off-chain start lock.
    # Exclude it from the roll when chaining (Limgrave then seals; never a 2nd start lock).
    _pool_steps = NUM_REGIONS_MIDDLE_STEPS if chain_excludes_limgrave else NUM_REGIONS_POOL_STEPS
    max_total = len(_pool_steps) + len(_caves)    # overworld majors + active caves'''

SP_R2B_OLD = '''    if ALTUS_STEP in NUM_REGIONS_POOL_STEPS:
        effective = min(effective + 1, max_total)
        _rest_pool = [s for s in NUM_REGIONS_POOL_STEPS if s != ALTUS_STEP] + _caves
        picked = [ALTUS_STEP] + list(rng.sample(_rest_pool, max(0, effective - 1)))
    else:
        picked = list(rng.sample(list(NUM_REGIONS_POOL_STEPS) + _caves, effective))'''
SP_R2B_NEW = '''    if ALTUS_STEP in _pool_steps:
        effective = min(effective + 1, max_total)
        _rest_pool = [s for s in _pool_steps if s != ALTUS_STEP] + _caves
        picked = [ALTUS_STEP] + list(rng.sample(_rest_pool, max(0, effective - 1)))
    else:
        picked = list(rng.sample(list(_pool_steps) + _caves, effective))'''

SPINE_EDITS = [
    ("sub", SP_R1_OLD, SP_R1_NEW, "chain_excludes_limgrave: bool = False,"),
    ("sub", SP_R2A_OLD, SP_R2A_NEW, "_pool_steps = NUM_REGIONS_MIDDLE_STEPS if chain_excludes_limgrave"),
    ("sub", SP_R2B_OLD, SP_R2B_NEW, "if ALTUS_STEP in _pool_steps:"),
]

# ---- __init__.py ----
INIT_CALL_OLD = '''                        region_spine.compute_num_regions_scope_pool(
                            self.random,
                            self.options.num_regions.value,
                            _all_regions, _all_locks,
                            _active_caves,
                        )'''
INIT_CALL_NEW = '''                        region_spine.compute_num_regions_scope_pool(
                            self.random,
                            self.options.num_regions.value,
                            _all_regions, _all_locks,
                            _active_caves,
                            bool(self.options.num_regions_chain.value),
                        )'''

INIT_LOCK_OLD = '''            self._random_start_region = _ns_start
            if "Limgrave Lock" in item_table:
                item_table["Limgrave Lock"].inject = True'''
INIT_LOCK_NEW = '''            self._random_start_region = _ns_start
            # Inject Limgrave Lock ONLY when Limgrave is actually KEPT this seed. Under
            # num_regions_chain Limgrave is excluded from the roll (no chain slot) -> sealed, and a
            # sealed Limgrave must not get a loose lock (that was the off-chain 2nd start lock).
            if "Limgrave Lock" in item_table:
                item_table["Limgrave Lock"].inject = (
                    "Limgrave" not in getattr(self, "_spine_sealed_regions", set()))'''

INIT_EDITS = [
    ("sub", INIT_CALL_OLD, INIT_CALL_NEW, "bool(self.options.num_regions_chain.value),"),
    ("sub", INIT_LOCK_OLD, INIT_LOCK_NEW, "Inject Limgrave Lock ONLY when Limgrave is actually KEPT"),
]

def apply_edits(text, edits):
    for kind, old, new, marker in edits:
        if old in text:
            if text.count(old) != 1:
                raise SystemExit(f"ABORT: anchor x{text.count(old)}: {marker!r}")
            text = text.replace(old, new, 1)
        elif marker in text:
            print(f"  [skip] applied: {marker[:46]!r}")
        else:
            raise SystemExit(f"ABORT: anchor not found / not applied: {marker[:46]!r}")
    return text

def patch_file(path, edits):
    raw = open(path, "rb").read()
    total = raw.count(b"\n"); crlf = raw.count(b"\r\n") == total and total > 0
    work = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
    nw = apply_edits(work, edits)
    if nw == work:
        print(f"  {os.path.basename(path)}: no change."); return
    out = (nw.replace("\n", "\r\n") if crlf else nw).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(path + ".bak_poolchain", "wb").write(raw)
    open(path, "wb").write(out)
    print(f"  {os.path.basename(path)}: patched ({'CRLF' if crlf else 'LF'}); backup .bak_poolchain")

def main():
    for p in (SPINE, INIT):
        if not os.path.isfile(p):
            print("ERROR not found:", p); return 1
    print("patching region_spine.py ..."); patch_file(SPINE, SPINE_EDITS)
    print("patching __init__.py ..."); patch_file(INIT, INIT_EDITS)
    print("done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
