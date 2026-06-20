#!/usr/bin/env python3
r"""
patch_apworld_chain_host_skip_filled.py  (run on Windows from repo root)

Fixes a num_regions_chain crash when a pre-placement option (derandomize_gurranq / derandomize_questlines
/ any place_locked_item) has already locked a location that the chain breadcrumb host-picker then tries
to reuse:

    pre_fill -> place_locked_item -> Exception: Location "DB/(BS): Ancient Dragon Smithing Stone -
    Gurranq, deathroot reward 9 or kill Gurranq" already filled.

Two guards (independent of the random-start work):
  1. `_num_regions_chain_host` excludes already-filled locations from its candidate pool, so it
     picks a real, empty boss/check as the breadcrumb host.
  2. The pre_fill placement treats an already-filled host as "no host" -> precollect the lock instead
     (the existing None-host fallback), so a collision can never raise.

Idempotent. Binary I/O preserves CRLF. Asserts anchors (no write on mismatch).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


# 1) host-picker: drop already-filled candidates.
A1 = b'        cands = [l for l in cands if getattr(l, "address", None) is not None]\r\n'
B1 = (b'        cands = [l for l in cands if getattr(l, "address", None) is not None\r\n'
      b'                 and getattr(l, "item", None) is None]  # skip pre-placed (derandomize_*) locks\r\n')

# 2) placement: an already-filled host counts as no host (-> precollect fallback).
A2 = b'            if _host is None:\r\n'
B2 = b'            if _host is None or getattr(_host, "item", None) is not None:\r\n'


def main():
    if not os.path.isfile(INIT):
        raise SystemExit(f"[FAIL] not found: {INIT}")
    data = _read(INIT)
    if b'skip pre-placed (derandomize_*) locks' in data:
        print("[skip] chain host filled-guard already applied.")
        return
    if data.count(A1) != 1:
        raise SystemExit(f"[FAIL] host-picker anchor x{data.count(A1)} (want 1). No write.")
    if data.count(A2) != 1:
        raise SystemExit(f"[FAIL] placement anchor x{data.count(A2)} (want 1). No write.")
    data = data.replace(A1, B1, 1).replace(A2, B2, 1)
    _write(INIT, data)
    print("[ok] chain breadcrumb host now skips pre-placed locations.")


if __name__ == "__main__":
    main()
