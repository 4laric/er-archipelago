#!/usr/bin/env python3
"""patch_apworld_limgrave_caves_alias.py

FIX: `limgrave_caves` is a valid extra_region_locks key (options.py) and is documented
identically to `limgrave_underground`, but NOTHING is wired to it -- only
`limgrave_underground` has entrance rules + a lock-key in _EXTRA_LOCK_KEYS. So selecting
`limgrave_caves` silently does nothing (the Limgrave underground dungeons never get gated).

This patch aliases `limgrave_caves` -> `limgrave_underground` at the start of generate_early,
so the documented synonym actually drives the wired behavior. Idempotent.

RUN ON WINDOWS (repo root):  python patch_apworld_limgrave_caves_alias.py
Then gen-test:               .\build.ps1 -Randomizer -Generate
Expect: a seed with extra_region_locks: [limgrave_caves] now shows "Spelunker's Torch"
(the Limgrave Underground Lock) as a progression item gating Fringefolk Hero's Grave etc.,
identical to limgrave_underground.
"""
import io, os, sys

TARGET = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")

ANCHOR = "    def generate_early(self) -> None:\n        self.created_regions = set()\n"

INSERT = (
    "    def generate_early(self) -> None:\n"
    "        self.created_regions = set()\n"
    "        # Alias: `limgrave_caves` is a documented synonym for `limgrave_underground`\n"
    "        # (same 10 Limgrave underground dungeons). Only `limgrave_underground` is wired in\n"
    "        # the entrance rules + _EXTRA_LOCK_KEYS lock map, so normalize the synonym here\n"
    "        # before any region/lock logic reads extra_region_locks. Idempotent.\n"
    "        if \"limgrave_caves\" in self.options.extra_region_locks.value:\n"
    "            self.options.extra_region_locks.value.discard(\"limgrave_caves\")\n"
    "            self.options.extra_region_locks.value.add(\"limgrave_underground\")\n"
)

MARKER = 'limgrave_caves" in self.options.extra_region_locks.value:\n            self.options.extra_region_locks.value.discard'


def main():
    if not os.path.isfile(TARGET):
        sys.exit(f"ERROR: {TARGET} not found. Run from the repo root (where Archipelago\\ lives).")

    with io.open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    if MARKER in src:
        print("Already applied (alias normalization present). No change.")
        return

    if ANCHOR not in src:
        sys.exit(
            "ERROR: anchor not found. The head of generate_early may have changed.\n"
            "Expected to find:\n" + ANCHOR
        )

    new = src.replace(ANCHOR, INSERT, 1)
    if new == src:
        sys.exit("ERROR: replacement produced no change.")

    # Verify exactly one anchor occurrence was replaced.
    if new.count('value.add("limgrave_underground")') < 1:
        sys.exit("ERROR: post-replace sanity check failed.")

    with io.open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(new)

    print(f"OK: aliased limgrave_caves -> limgrave_underground in {TARGET}")
    print(f"    {len(src)} -> {len(new)} bytes")


if __name__ == "__main__":
    main()
