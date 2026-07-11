# Where do the apworld's location descriptions come from? (matt provenance)

Measured against the Nexus matt's-rando distribution on disk
(`Elden Ring Randomizer-428-v0-11-4 .../randomizer/diste/Base/itemslots.txt`) vs the current
apworld `locations.py`. `SoulsRandomizers` in the repo is an empty (un-checked-out) submodule, so
the distribution `itemslots.txt` is the reference.

## Two separate things, two different answers

**1. The location SET / keys — 100% matt's.**
All **4,150** keyed apworld locations use matt's static-randomizer `key` verbatim, and **every one
(4,150 / 4,150) is present in matt's `itemslots.txt`**. Zero apworld locations exist outside matt's
set. That file opens with an explicit notice:

> `# Location descriptions were written by and copyright thefifthmatt`

So the skeleton — which locations exist, and the id each is keyed by — is entirely matt-derived.
This is the *same class of data* that got the DS1 server strike; it is not clean-room.

**2. The human-readable descriptions — NOT copied; independently authored.**
Joining apworld description text to matt's `Text:` on shared keys (4,150):

| relationship | count | share |
|---|---|---|
| matt shipped only `aaaa` placeholder -> apworld text is **original** | 2,464 | 59% |
| apworld **reworded** matt's description (same facts, different words) | 1,648 | 40% |
| verbatim / substring of matt's prose | 38 | <1% |

The 38 "verbatim" are false positives — terse labels like `Golden Order Principia`, `Isolated
Merchant`, `seedtree` that happen to be substrings of matt's longer sentences (they're item/entity
names, not copied prose). Effective verbatim copying of matt's descriptive sentences: **~zero**.

Example (key `603347,...`): matt = *"In a chest up the hill at the enemy camp north of the Foot of
the Four Belfries"*; apworld = *"in left chest to N in upper camp"*. Same spot, rewritten.

## Notable: matt withholds most base-game descriptions from the distribution

The 2,464 `aaaa` placeholders cluster in **base-game** areas (liurnia 258, altus 196, limgrave 147,
caelid, leyndell, mountaintops, stormveil...), while the slots that still carry real text are heavily
**DLC** (scadualtus, gravesite, rauhruins, belurat, enirilim). So matt's *distributed* data has his
base-game prose redacted to placeholders — meaning the apworld **physically could not have copied**
the majority of them and had to write original text. (Likely-but-unconfirmed read: matt deliberately
keeps his copyrighted descriptions out of the redistributable; source is at
`github.com/thefifthmatt/SoulsRandomizers`, license terms not checked here.)

## What this means

- **"Unique to Bedrock's apworld"** = the reworded/original *descriptions* + his region-code
  taxonomy (LL/FFB etc.). Genuine authorship. But they're bolted onto **matt's location set**, so
  the apworld as a whole is a **derivative of matt's location data** with independently-written prose.
- **Bedrock's apworld is not matt-free.** Treating it as the "clean" foundation isn't quite right —
  it carries the same matt-location-set provenance that struck you before. You're in the same boat;
  that's an alignment point with him, not a wedge, and worth being transparent about.
- **The client is the cleanest layer of all.** It consumes keys -> flags — functional, game-derived
  identifiers (map/lot numbers), never matt's descriptions. So *whatever* happens with the apworld
  question, the client itself doesn't touch matt's copyrighted prose.
- **Going standalone does NOT escape matt.** Your own apworld would rest on the same location set.
  Only the client (keys/flags, functional) is provenance-clean. That's a real input to standalone-vs-
  collab: the risky layer is the apworld — anyone's — not the client.

*(Not legal advice — I'm not a lawyer. Copyrightability of a curated location set vs. functional ids
is a genuine grey area; if this matters for release, get a real read on matt's license.)*
