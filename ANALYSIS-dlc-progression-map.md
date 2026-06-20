# SotE DLC progression map — how the Land of Shadow actually gates

Purpose: understand how DLC progression works across all areas, so chokepoint locks / sweeps can be
placed correctly (`SPEC-chokepoint-locks.md`). Built from the apworld DLC region graph (`__init__.py`
`create_connection` block, the randomizer's own model) cross-checked against Fextralife.

**Headline:** the DLC is **hub-and-spoke**, not a linear corridor of mid-boss chokepoints like the
base legacy dungeons. There's a short *hard* critical path and a lot of optional spokes, and the
spokes are gated by **three different things** — bosses, *items*, and *world-state flags* — not just
bosses. That's the "other distinction" worth encoding.

---

## The hard critical path (Gravesite → final boss)

```
Gravesite Plain  →  Castle Ensis [Rellana]  →  Scadu Altus (hub)  →  Shadow Keep [Messmer → Messmer's Kindling]
                 →  Ancient Ruins of Rauh [Romina]  →  burn sealing tree (Kindling)  →  Enir-Ilim [Promised Consort Radahn]
```

| Step | Area | Gate to the NEXT step | Gate type |
|------|------|----------------------|-----------|
| entry | **Gravesite Plain** | (DLC entry: Mohg+Radahn + touch cocoon) — free hub in `dlc_only` | boss/event |
| 1 | **Castle Ensis** | Rellana → opens the road to Scadu Altus (apworld's only Scadu edge is `Castle Ensis → Scadu Altus`) | **boss** (soft — alt routes exist in vanilla) |
| 2 | **Scadu Altus** | central hub; spokes below | — |
| 3 | **Shadow Keep** | Messmer the Impaler → drops **Messmer's Kindling** | **boss** + item reward |
| 4 | **Ancient Ruins of Rauh** | Romina, Saint of the Bud → access to the sealing tree | **boss** |
| 5 | sealing tree | burn it with **Messmer's Kindling** → teleport to Enir-Ilim | **item gate** |
| 6 | **Enir-Ilim** | Promised Consort Radahn (final) | boss (goal) |

So the only *non-boss* hard gate on the main path is **Messmer's Kindling** (item). The apworld
already models this (Enir Ilim gated on Messmer's Kindling; `messmer_kindle` option).

---

## Scadu Altus hub — the optional spokes (and how each is gated)

| Spoke (area) | Reached from | Gate type | Notes |
|---|---|---|---|
| **Belurat, Tower Settlement** [Dancing Lion] | Gravesite Plain | walk-in | optional remembrance; Belurat Gaol = minor dungeon off it |
| **Jagged Peak** [Bayle] | Gravesite → Dragon's Pit → Jagged Peak Foot | **boss** (Ancient Dragon-Man mid-climb → summit) | linear boss climb — base-style choke; Bayle flag 510630 |
| **Cerulean Coast** | Gravesite → Ellac River | walk-in | leads to Stone Coffin + Finger Ruins of Rhia |
| **Stone Coffin Fissure** [Putrescent Knight] | Cerulean Coast | **state** (light the coffin cocoons/sparks to open the path down) | |
| **Charo's Hidden Grave → Lamenter's Gaol** | Jagged Peak Foot | **key** (Gaol Upper/Lower Level Keys) | minor dungeon |
| **Shadow Keep, Church District → Church District Lower → Scadutree Base** | Scadu Altus | **state** (roof ladder → **drain** mechanism; flooded until drained) | the chokepoint you flagged; no boss |
| **Storehouse Back → Scaduview → Hinterland → Finger Ruins of Dheo** | Shadow Keep Church District | walk-in / traversal | Dheo holds one of the Metyr bells |
| **Cathedral of Manus Metyr → Finger Ruins of Miyr → Metyr** | Scadu Altus | **item + multi-state** | needs **Hole-Laden Necklace**, ring bells at **Dheo *and* Rhia**, then the bell under the cathedral throne (your pasted example) |
| **Recluses' River → Darklight Catacombs → Abyssal Woods → Midra's Manse** [Midra] | Shadow Keep | **state/stealth** (Abyssal Woods: avoid the Inquisitor/Winter-Lantern patrol; light braziers) | frenzied-flame spoke |
| **Rauh Base / Scorpion River Catacombs / Taylew's & Starfall Forges / Ruined Forges** | Scadu Altus | walk-in / minor | side dungeons |

**Power gate, not access:** Scadutree Fragments (blessing level) and Revered Spirit Ash (summon
level) scale you up but never gate area access. Treat separately from chokepoints.

---

## The gate taxonomy (the actionable part)

DLC progression uses **three gate types**, vs the base game's near-uniform "mid-boss":

1. **Boss gates** — Rellana (→Scadu Altus), Ancient Dragon-Man (→Bayle), Romina (→sealing tree),
   the remembrance end-bosses. These work with the base-style choke-boss lock (gate the after-region
   on the DefeatFlag; sweep the before-checks on kill).
2. **Item gates** — Messmer's Kindling (→Enir Ilim), Hole-Laden Necklace + the two Finger bells
   (→Metyr), Gaol keys (→Lamenter's lower). These map naturally onto the **region-lock item** model
   (the item *is* the key), not a sweep trigger.
3. **State-flag gates** — Shadow Keep church **drain**, Stone Coffin cocoon-lighting, Abyssal Woods
   stealth/braziers. These are the "other distinction": gate the after-region on a **world-state
   event flag**, and the sweep trigger is that flag (identical plumbing to a DefeatFlag).

### Implications for `SPEC-chokepoint-locks.md`
- The **legacy DLC dungeons** (Belurat, Castle Ensis, Enir-Ilim) really are single-boss — no
  internal mid-boss to split, as suspected. Don't force a choke onto them.
- **Shadow Keep** is the exception with a real internal chokepoint: the **drain** (state flag),
  splitting `Church District (15)` → `Church District Lower (19)` → `Scadutree Base`. Capture the
  drain event flag and gate/sweep on it.
- **Jagged Peak / Bayle** behaves like a base-game boss choke (Ancient Dragon-Man → summit).
- The Metyr / Finger-Ruins bell network is an **item+multi-state** gate — too bespoke for the choke
  lock; if gated at all it belongs in the region-lock-item model (Hole-Laden Necklace as a key), not
  the sweep.

### Flags still to capture (in-game / EMEVD)
Shadow Keep drain state flag; Ancient Dragon-Man DefeatFlag; Rellana / Romina / Messmer DefeatFlags
(Messmer & remembrance bosses are in the boss-attribution enumeration already); Stone Coffin
cocoon-light flag; Abyssal Woods brazier/stealth flag. Item gates (Kindling, Hole-Laden Necklace,
Gaol keys) don't need flags — they're pool items.

---

Sources: Fextralife — [Shadow Keep](https://eldenring.wiki.fextralife.com/Shadow+Keep),
[Enir-Ilim](https://eldenring.wiki.fextralife.com/Enir-Ilim),
[Messmer's Kindling](https://eldenring.wiki.fextralife.com/Messmer's+Kindling),
[Shadow Lands Game Progress Route](https://eldenring.wiki.fextralife.com/Shadow+Lands+Game+Progress+Route);
plus the apworld DLC region graph (`Archipelago/worlds/eldenring/__init__.py`).
