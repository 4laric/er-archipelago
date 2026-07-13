# Legacy-dungeon chokepoint bosses — before/after check map

Question: for the headline legacy dungeons whose mid-boss is a hard chokepoint (Red Wolf,
Loretta, Golden Godfrey, Godskin Duo), which checks sit *before* the boss vs *after*?

**Do we already have this? No.** `boss-attribution-dryrun.csv` only gives per-boss check *counts*
(nearest-in-region attribution for the sweep), not a before/after split. The region graph encodes
the chokepoint cleanly in **only one** of the four (Farum Azula). For the rest, before/after has to
be derived from the per-check **sub-area prefix** (the `XX/YY:` tag = which Site-of-Grace area the
check sits in) plus the boss's own drop tag and, for Caria Manor, the explicit "before/after boss"
text already in the descriptions.

Confidence is labelled per dungeon. The cleanest signal is region split > description text >
sub-area prefix + critical-path order.

---

## 1. Raya Lucaria Academy — Red Wolf of Radagon  *(medium confidence)*

Boss anchor: **Memory Stone — boss drop**, tagged sub-area **SC** (key `140000,0:0000060440`).
Total dungeon = 111 checks across 4 apworld regions (Academy 70, Academy Main 36, Chest 1,
Library 4). **The region split is NOT the chokepoint** — both Academy and Academy Main mix sub-areas.

Critical path (shallow → deep) and sub-area counts:

| Order | Sub-area | Code | Checks | vs Red Wolf |
|------:|----------|:----:|------:|-------------|
| 1 | Main Academy Gate | MAG | 23 | **before** (unambiguous — entrance/seal landing, isolated merchant, seedtree) |
| 2 | Church of the Cuckoo | CC | 19 | before *(verify — see note)* |
| 3 | Schoolhouse Classroom | SC | 21 | **boss arena** (Red Wolf's Memory Stone is tagged here) |
| 4 | Debate Parlor | DB | 37 | **after** (rooftops, long-jump, shortcut) |
| 5 | Grand Library (Rennala) | RLGL | 9 | **after** (deepest) |
| – | Rennala main-boss drops | – | 2 | after |

So **before ≈ MAG + CC = 42**, boss band = SC (21), **after ≈ DB + RLGL + Rennala = 48**.

> Note: the one wobble is whether **Church of the Cuckoo** is before or after Red Wolf. I placed it
> *before* because the Red Wolf drop is bucketed in SC (the grace you light past the fight). MAG is
> unambiguously pre-boss; DB + RLGL + Rennala are unambiguously post. If CC turns out to be past Red
> Wolf in-game, before shrinks to MAG (23). Worth a 1-minute in-game confirm of the CC↔SC boundary.

---

## 2. Miquella's Haligtree → Elphael — Loretta, Knight of the Haligtree  *(clean, region-encoded)*

Boss anchor: **Loretta's War Sickle / Loretta's Mastery — boss drop** (key `150000,0:0000510190`,
defeat-flag candidate **510190**), tagged **HTP** (Haligtree Town Plaza). The apworld splits the
dungeon at her, like Farum Azula:

- **Before Loretta** — `Miquella's Haligtree` region = **41 checks** (the canopy/branch platforming
  section). Sub-areas: Haligtree Canopy HC 18, **Haligtree Town Plaza HTP 15 = Loretta's arena/own
  drops**, Haligtree Town HT 8. She sits at HTP, the deep end of this region, so essentially the
  whole canopy section is on her near side.
- **After Loretta** — `Elphael, Brace of the Haligtree` region = **66 checks** (the city). Sub-areas:
  Elphael Inner Wall EIW 25, Prayer Room PR 25, Drainage Channel DC 8, **Haligtree Roots HR 7 =
  Malenia** (Remembrance of the Rot Goddess + Malenia's Great Rune), HP 1. (The other "boss drop"
  tags in Elphael — Golden Seed in the rot pond, Lord's Rune/Rotten Staff on the outer wall — are
  Elphael field/minibosses, not the chokepoint.)

> Clean split: the `Miquella's Haligtree` ↔ `Elphael` region boundary *is* the Loretta chokepoint.
> Her own drops sit in the "before" region (same as Godskin Duo); everything in Elphael is strictly
> past her, ending at Malenia.

---

## 3. Leyndell, Royal Capital — Golden Godfrey (Godfrey's golden shade)  *(clean, region-encoded)*

The golden shade has **no randomized drop** (vanilla gives only a Hero's Rune), so there's no boss
check to anchor — it's a **positional gate** to the Elden Throne. The chokepoint is encoded by the
region split:

- **Before Golden Godfrey** — `Leyndell, Royal Capital` (121) + `Leyndell, Royal Capital Unmissable`
  (23) = **144 checks**. Sub-areas: Avenue Balcony AB 61, FMFF 25, LCC 18, East Capital Rampart
  ECR 11, etc. (essentially the whole capital is reachable before the shade).
- **Chokepoint** — Golden Godfrey at the **Erdtree Sanctuary (ES)**.
- **After Golden Godfrey** — `Leyndell, Royal Capital Throne` (**12 checks**): Erdtree Sanctuary ES,
  Queen's Bedchamber QB (**Morgott** — Remembrance of the Omen King, key `110000,0:0000510040`),
  West Capital Rampart WCR, Elden Throne ET.

> So Golden Godfrey gates only the small Throne pocket (which is essentially the Morgott run-up).
> Morgott himself is the true dungeon end-boss; Godfrey's shade is the immediate sub-chokepoint
> before him. ES is technically the staging grace just before the shade.

---

## 4. Crumbling Farum Azula — Godskin Duo  *(cleanest — the region boundary IS the chokepoint)*

Boss anchor: **Smithing-Stone Miner's Bell Bearing [4] / Ash of War: Black Flame Tornado — boss
drop** (key `130000,0:0000510140`, defeat-flag candidate **510140**), tagged **DTT**.

The apworld already splits this dungeon exactly at Godskin Duo:

- **Before Godskin Duo** — `Farum Azula` region = **44 checks** (sub-areas: TFB 18, Dragon Temple DT
  11, Crumbling Beast Grave CBG 6, CBG Depths CBGD 5, **DTT 2 = Godskin Duo's own drop**, MotG 2).
- **After Godskin Duo** — `Farum Azula Main` region = **58 checks** (Dragon Temple Rooftop DTR 18,
  Lift DTL 17, **Beside the Great Bridge BGB 12 = Maliketh + Dragonlord Placidusax remembrances**,
  Dragon Temple Altar DTA 11).

> Godskin Duo's own drops sit in the "before" region; everything in `Farum Azula Main` is strictly
> past them. If you ever want a boss-gated lock here, you get it almost for free off the existing
> region boundary.

---

## Summary

| Dungeon | Chokepoint boss | Before | Boss | After | How derived |
|---------|-----------------|-------:|-----:|------:|-------------|
| Raya Lucaria Academy | Red Wolf of Radagon | ~42 (MAG+CC) | 21 (SC) | ~48 (DB+RLGL+Rennala) | sub-area prefix + path order |
| Miquella's Haligtree | Loretta, Knight of the Haligtree | 41 (canopy, incl. her drop) | – | 66 (Elphael → Malenia) | **region split = chokepoint** |
| Leyndell | Golden Godfrey (shade) | 144 (whole capital) | 0 (no drop) | 12 (Throne/Morgott) | region split |
| Crumbling Farum Azula | Godskin Duo | 44 (incl. its drop) | – | 58 (Maliketh/Placidusax) | **region split = chokepoint** |

### Feasibility note (if the goal is boss-gating the back half)
- **Farum Azula** is trivial — `Farum Azula Main` already isolates the post-Godskin half; gate that
  region's entrance on Godskin Duo's defeat flag (~510140).
- **Leyndell** is easy — gate the `…Throne` region on Golden Godfrey's defeat flag (the shade has no
  drop, so you'd reference the DefeatFlag directly, not a check). Pull the exact flag from the
  boss-attribution data (`SPEC-boss-attribution.md` / `BossAttribution.cs`).
- **Miquella's Haligtree** is trivial — `Elphael, Brace of the Haligtree` already isolates the whole
  post-Loretta half; gate that region's entrance on Loretta's defeat flag (~510190). Same pattern as
  Farum Azula.
- **Raya Lucaria** needs a sub-area→region carve first (the back half isn't its own region; it's
  DB+RLGL inside the existing two regions), and the CC↔SC boundary verified.

So three of the four (Farum Azula, Haligtree, Leyndell) are boss-gateable off existing region
boundaries; only Raya Lucaria needs a carve.

Defeat-flag candidates from boss drops: Loretta (Haligtree) 510190, Godskin Duo 510140, Morgott
510040. Red Wolf drops via item event flag (060440), not a 510xxx lot — get its true DefeatFlag from
the boss-attribution enumeration; Golden Godfrey's shade likewise (no drop).
