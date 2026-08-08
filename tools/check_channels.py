#!/usr/bin/env python3
"""check_channels.py -- the publish channels name things that exist, and point the right way.

`release/CHANNELS.tsv` is the pointer that makes "beta" and "stable" mean something. A pointer
nobody checks is worse than no pointer: it reads as authoritative and can name a tag that was never
cut, or claim stable is somewhere it is not, and the first person to find out is a player who
downloaded the wrong thing.

WHAT IT ASSERTS, and why each one is here rather than assumed:

  1. Every `tag` column value is a REAL git tag (or the literal `main`, which only `beta` may use).
     A typo'd tag is the whole failure mode -- the ledger still parses, still renders, still looks
     right, and points at nothing.
  2. `stable` is not AHEAD of the newest tag. Stable naming a tag that does not exist yet is how a
     "promote" lands before the cut it promotes.
  3. Exactly one row per channel is CURRENT (the last one wins, and the file is append-only), and
     `promoted_on` never goes backwards within a channel -- otherwise the history the append-only
     rule buys is not readable in order.

🛑 IT DOES NOT ASSERT THAT STABLE IS THE NEWEST TAG. Trailing is the POINT of a stable channel; a
gate that demanded stable == newest would forbid the only behaviour the channel is for.

Exit 0 clean, 1 with findings. Offline: reads git refs, nothing network.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "release", "CHANNELS.tsv")
CHANNELS = ("stable", "beta")
MOVING = "main"          # only `beta` may name a moving ref


def rows(path=None):
    path = path or LEDGER
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                out.append((n, None, None, None, "not 3+ tab-separated columns: %r" % line))
                continue
            out.append((n, parts[0].strip(), parts[1].strip(), parts[2].strip(), None))
    return out


def known_tags():
    r = subprocess.run(["git", "-C", ROOT, "tag", "-l", "v*"], capture_output=True, text=True)
    return {t.strip() for t in r.stdout.split() if t.strip()}


def _ver(tag):
    """(0,3,7) from 'v0.3.7'; None if it is not a plain release tag."""
    try:
        return tuple(int(p) for p in tag.lstrip("v").split("."))
    except ValueError:
        return None


def check(path=None, tags=None):
    # 🛑 PATH IS A PARAMETER, NOT A MODULE GLOBAL READ AT DEF TIME. It started as
    # `def rows(path=LEDGER)`, which binds the default ONCE at import -- so the test that proves
    # this gate can fail monkey-patched the global, got the real ledger anyway, and passed while
    # asserting nothing. A gate whose negative case cannot be reached is not a gate.
    path = path or LEDGER
    bad = []
    if not os.path.isfile(path):
        return ["%s is missing -- the channels have no pointer" % os.path.relpath(path, ROOT)]
    tags = known_tags() if tags is None else set(tags)
    # 🛑 A SHALLOW CLONE HAS NO TAGS, AND THE HALF THAT NEEDS THEM THEN DOES NOT RUN. Failing every
    # row instead would make this red on a checkout depth, which is a gate people learn to ignore --
    # but a gate that silently reports nothing is the worse of the two, so `main()` PRINTS that the
    # tag half was skipped (the same shape as check_release_notes' "window: UNCHECKED"). The
    # authoritative run is the `generators` job, which checks out fetch-depth: 0 + fetch-tags.
    # `tags` is injectable so this branch is testable without re-cloning at a different depth --
    # CI red on 2026-08-08: the negative test assumed tags were present and passed vacuously there.
    shallow = not tags
    current = {}
    last_date = {}
    for n, chan, tag, date, err in rows(path):
        if err:
            bad.append("line %d: %s" % (n, err))
            continue
        if chan not in CHANNELS:
            bad.append("line %d: unknown channel %r (expected one of %s)" % (n, chan, ", ".join(CHANNELS)))
            continue
        if tag == MOVING:
            if chan != "beta":
                bad.append("line %d: only `beta` may point at `%s`; %r must name a tag" % (n, MOVING, chan))
        elif not shallow and tag not in tags:
            bad.append("line %d: %s points at %r, which is not a tag in this repo" % (n, chan, tag))
        if chan in last_date and date < last_date[chan]:
            bad.append("line %d: %s promoted_on %s is earlier than the previous row's %s "
                       "(the file is append-only, so rows must run forwards)" % (n, chan, date, last_date[chan]))
        last_date[chan] = date
        current[chan] = tag
    for chan in CHANNELS:
        if chan not in current:
            bad.append("no row for channel %r" % chan)
    if not shallow and current.get("stable") and current["stable"] != MOVING:
        sv = _ver(current["stable"])
        newest = max((v for v in (_ver(t) for t in tags) if v), default=None)
        if sv and newest and sv > newest:
            bad.append("stable points at %s but the newest tag in the repo is v%s -- a promotion "
                       "cannot precede the cut it promotes" % (current["stable"], ".".join(map(str, newest))))
    return bad


def main():
    tags = known_tags()
    if not tags:
        print("  tags: UNCHECKED -- no v* tags in this checkout (shallow clone). The "
              "'is that a real tag' half did NOT run, so a green result here says nothing about it.")
    bad = check()
    if bad:
        print("[FAIL] release/CHANNELS.tsv:")
        for b in bad:
            print("   " + b)
        return 1
    cur = {}
    for _n, chan, tag, date, err in rows():
        if not err and chan in CHANNELS:
            cur[chan] = (tag, date)
    print("[ok] channels: " + " | ".join("%s -> %s (%s)" % (c, cur[c][0], cur[c][1]) for c in CHANNELS if c in cur))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
