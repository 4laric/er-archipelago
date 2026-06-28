#!/usr/bin/env python3
"""Make a SEALED Limgrave actually dark + locked (no-Limgrave under num_regions pool+chain).

The pool+chain roll now seals Limgrave (patch_apworld_numregions_pool_chain_limgrave), but Limgrave
was hardcoded as the eternal open start hub in three slot_data paths that fire regardless of whether
it's sealed -- so a sealed Limgrave was left physically OPEN and fully LIT at load (the "christmas
tree", which also bypassed grace_rando):
  * start_region_freebie: to_limgrave (the DEFAULT) lights the full LIMGRAVE_START_GRACES set.
  * under to_limgrave, Limgrave is omitted from the lock map (_rli) -> no kick -> open.
  * the on-receipt LIMGRAVE_START_GRACES bundle on Limgrave Lock.

Fix: compute _limgrave_sealed once and gate all three -- a sealed Limgrave lights ZERO graces and IS
added to the lock map (kicked, like any sealed region); a KEPT Limgrave behaves exactly as before.

Idempotent, CRLF-safe, py_compiles, .bak_seallim backup. __init__.py only.
"""
import os, sys, py_compile, tempfile

INIT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "Archipelago", "worlds", "eldenring", "__init__.py")

DEF_OLD = '''        region_graces: Dict[str, list] = {}'''
DEF_NEW = '''        # A SEALED Limgrave (pool+chain rolls it out of the kept set) must be DARK + LOCKED like any
        # other sealed region -- NOT lit by the to_limgrave freebie or left physically open. Gate every
        # Limgrave start-hub special-case below on this. (er-numregions-pool-chain-limgrave)
        _limgrave_sealed = "Limgrave" in getattr(self, "_spine_sealed_regions", set())
        region_graces: Dict[str, list] = {}'''

C_OLD = '''            if getattr(self, "_random_start_region", None) and self.options.start_region_freebie.value != 1:
                region_graces["Limgrave Lock"] = sorted(set(
                    region_graces.get("Limgrave Lock", []) + list(LIMGRAVE_START_GRACES)))'''
C_NEW = '''            if getattr(self, "_random_start_region", None) and self.options.start_region_freebie.value != 1 and not _limgrave_sealed:
                region_graces["Limgrave Lock"] = sorted(set(
                    region_graces.get("Limgrave Lock", []) + list(LIMGRAVE_START_GRACES)))'''

B_OLD = '''        _rli = dict(REGION_LOCK_ITEM)
        if getattr(self, "_random_start_region", None) and self.options.start_region_freebie.value != 1:
            _rli["Limgrave"] = "Limgrave Lock"'''
B_NEW = '''        _rli = dict(REGION_LOCK_ITEM)
        if getattr(self, "_random_start_region", None) and (self.options.start_region_freebie.value != 1 or _limgrave_sealed):
            _rli["Limgrave"] = "Limgrave Lock"'''

A_OLD = '''            if self.options.start_region_freebie.value == 1:  # to_limgrave
                _rs_g += [int(f) for f in LIMGRAVE_START_GRACES]'''
A_NEW = '''            if self.options.start_region_freebie.value == 1 and not _limgrave_sealed:  # to_limgrave (only when Limgrave is kept)
                _rs_g += [int(f) for f in LIMGRAVE_START_GRACES]'''

EDITS = [
    ("sub", DEF_OLD, DEF_NEW, '_limgrave_sealed = "Limgrave" in getattr(self, "_spine_sealed_regions"'),
    ("sub", C_OLD, C_NEW, 'value != 1 and not _limgrave_sealed:'),
    ("sub", B_OLD, B_NEW, 'value != 1 or _limgrave_sealed):'),
    ("sub", A_OLD, A_NEW, 'value == 1 and not _limgrave_sealed:  # to_limgrave'),
]

def apply_edits(text, edits):
    for kind, old, new, marker in edits:
        # marker first: some NEW blocks contain OLD as a substring (we insert ABOVE the anchor),
        # so checking `old in text` first would re-apply. The marker only exists post-apply.
        if marker in text:
            print(f"  [skip] applied: {marker[:46]!r}")
        elif old in text:
            if text.count(old) != 1:
                raise SystemExit(f"ABORT: anchor x{text.count(old)}: {marker!r}")
            text = text.replace(old, new, 1)
        else:
            raise SystemExit(f"ABORT: anchor not found / not applied: {marker[:46]!r}")
    return text

def main():
    if not os.path.isfile(INIT):
        print("ERROR not found:", INIT); return 1
    raw = open(INIT, "rb").read()
    total = raw.count(b"\n"); crlf = raw.count(b"\r\n") == total and total > 0
    work = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
    nw = apply_edits(work, EDITS)
    if nw == work:
        print("__init__.py: no change."); return 0
    out = (nw.replace("\n", "\r\n") if crlf else nw).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(INIT + ".bak_seallim", "wb").write(raw)
    open(INIT, "wb").write(out)
    print(f"__init__.py: patched ({'CRLF' if crlf else 'LF'}); backup .bak_seallim")
    return 0

if __name__ == "__main__":
    sys.exit(main())
