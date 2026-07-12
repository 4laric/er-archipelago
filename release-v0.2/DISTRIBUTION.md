# Distribution

How this project is handed to players, and why.

## The rule everything else follows from

**The apworld and the client `.dll` are a HASH-MATCHED PAIR.** This is not a convention, it is
enforced. The apworld stamps a contract hash into `slot_data`; the client has one compiled in, and
on connect it compares them:

```
VERSION MISMATCH -- apworld sent [apworld/0.2.0 contract/36013f63 data/...] but this client
was BUILT against contract/<other>. The apworld and the client .dll are from different builds.
```

A mismatched pair does not fail loudly at the door. **It boots, connects, and then behaves subtly
wrong** -- the client reads `slot_data` shapes that are not the ones it is being sent. That is the
worst failure mode a randomizer can have, and it is entirely preventable at the distribution layer.

So: **do not let people acquire the two halves separately.** Everything below is downstream of that.

## What we publish

**GitHub Releases is the single source of truth.** One tag, two assets:

| Asset | Who needs it |
|---|---|
| `ER-Archipelago-v<ver>.zip` | **Players.** Contains the apworld, the client `.dll`, and the docs. One download, guaranteed matched. |
| `eldenring.apworld` (bare) | **Hosts.** Someone generating a multiworld needs the apworld and nothing else -- they may not even be playing Elden Ring. Making them pull a 10 MB bundle with a game-mod DLL in it, to generate someone else's seed, is friction for nothing. |

Both come off the **same tag**, so the pairing stays obvious even when someone takes only one.

The residual risk is **host/player skew**: the host generates with apworld vN while a player runs
client vM. That one cannot be prevented by packaging -- it is a property of multiworlds -- so it is
handled where it can be: the handshake catches it, and it is documented as a symptom.

> **The apworld and the client must come from the same release tag.**
> If you see `VERSION MISMATCH` in the client log, that is what it means. Redownload both from the
> same release. Do not report bugs from a mismatched pair -- they will not be real.

## What we do NOT do

**No mirrors.** Not on Nexus, not in a Discord pin, not a re-upload "for convenience". A mirror
goes stale, you cannot un-ship it, and a stale mirror of *this* artifact produces exactly the
mismatched pair the whole design is trying to prevent. Link to the release page.

(This is the same courtesy we extend to thefifthmatt's randomizer -- link, do not scatter -- and
it applies to us for a harder reason than politeness.)

**We do not bundle matt's randomizer.** See `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md`.

## The real distribution answer is upstream

Packaging is a workaround. The way people actually **find and install** Archipelago worlds is the
official supported-games list and the AP Launcher's built-in world installer -- and both of those
come from being merged into `ArchipelagoMW/Archipelago`.

We are closer to that than it looks:

* the game id is already conventional -- **`Elden Ring`**, with the space (39 of 62 upstream worlds
  have one; it is `Dark Souls III`, not `DarkSouls3`),
* the world runs green on **stock upstream 0.6.7** -- 572 tests and a real generation, no fork,
* there is **no proprietary data in the tree** (`PROVENANCE.md`), which is the thing that usually
  blocks a FromSoft world,
* the client is MIT and lives in its own repo, so it does not have to move upstream at all.

**Upstreaming is the v0.3 goal.** It is a bigger lever than any packaging decision we can make
here, and every release cut in the meantime should keep the world upstream-shaped rather than
drifting away from it.
