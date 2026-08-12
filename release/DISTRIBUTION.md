# Distribution

How this project is handed to players, and why.

## The rule everything else follows from

**The apworld and the client `.dll` are a HASH-MATCHED PAIR.** This is not a convention, it is
enforced. The apworld stamps a contract hash into `slot_data`; the client has one compiled in, and
on connect it compares them:

```
VERSION MISMATCH -- apworld sent [apworld/0.2.11 contract/36013f63 data/...] but this client
was BUILT against contract/8550ab05. The apworld and the client .dll are from different builds.
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

### And the yaml builder, which is a page rather than a download

<https://peliarch.ca/er/> serves the options wizard: the page most players will actually meet this
project through, because it is the only surface you can use before deciding whether to install
anything. `/er/` tracks the released build; `/er/beta/` tracks `main` and says so in a banner.

🛑 **It is pinned by nothing.** It is `wizard/wizard.html` copied to a box, on whatever schedule
somebody copies it, so it can be *ahead* of the newest tag -- and `POST /generate` on the same box
runs that box's own installed apworld, so it can be *behind* the page it serves. Neither skew is an
error a player sees: Archipelago drops an option it does not recognise and generates the seed
anyway, printing one line on a console nobody reads. That is why every yaml the builder writes
records the apworld version it was written for, and why the page names its channel.

Every release also ships `er-options-wizard.html`, the same page as a file, for anyone who would
rather not use a website.

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
* the world runs green on **stock upstream 0.6.7** -- the full test suite green and a real generation, no fork,
* there is **no proprietary data in the tree** (`PROVENANCE.md`), which is the thing that usually
  blocks a FromSoft world,
* the client is MIT and lives in its own repo, so it does not have to move upstream at all.

**Upstreaming remains the goal.** It is a bigger lever than any packaging decision we can make
here, and every release cut in the meantime should keep the world upstream-shaped rather than
drifting away from it.
