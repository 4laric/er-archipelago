# PLAYTEST SHEET — rune scaling (and two open in-game questions)

**For:** Alaric, next playtest. **Needs no new build** for §2 — it is kill-things-and-compare.
**Companion to:** `SPEC-rune-scaling-20260728.md` (where the numbers come from).

---

## 1. First: the 49 "missing" bosses were never missing

`GameAreaParam` has 216 rows; `boss_healthbars.py` has 244 entities; 195 join, 49 do not. **Not a
gap — the wrong arity.** `GameAreaParam` pays **per ARENA, once**, on the leader/base entity. The 49
split:

- **20** are a duplicate name whose sibling id joins.
- **29** have no row at all, and every one checked is a phase 2, a duo partner, an NPC summon, or an
  alt-map copy. Verified 9/9:

| non-joining entity | is really | arena that pays | pays |
|---|---|---|---|
| `19000810` Radagon | phase 1 of | `19000800` Elden Beast | 500,000 |
| `20010801` Promised Consort Radahn | phase 2 of | `20010800` Radahn, Consort | 500,000 |
| `21010801` Messmer the Impaler | phase 2 of | `21010800` Base Serpent Messmer | 400,000 |
| `13000801` Beast Clergyman | phase 1 of | `13000800` Maliketh | 220,000 |
| `16000801` God-Devouring Serpent | phase 1 of | `16000800` Rykard | 130,000 |
| `12020801` Valiant Gargoyle (Twinblade) | duo partner of | `12020800` Valiant Gargoyle | 30,000 |
| `31110801` Putrid Crystalian (Ringblade) | trio partner of | `31110800` (Spear) | 7,100 |
| `31200801` Cleanrot Knight (Sickle) | duo partner of | `31200800` (Spear) | 7,000 |
| `2050480810` Scadutree Avatar | shares arena with | `2050480860` | 120,000 |

🛑 **So key any rewrite on the `GameAreaParam` ROW, never on "every boss entity we know."** Iterating
our 244-entity table would miss 49 and tempt someone to invent values for a duo partner that is not
supposed to pay separately. (21 `GameAreaParam` rows have no entry in our boss table at all — arenas
we do not classify as bosses. Worth a look before claiming totality in the other direction.)

## 2. Zero-code confirmations — just kill them and read the number

Vanilla payouts, straight from `GameAreaParam.bonusSoul_single`. **Play VANILLA or a seed with
scaling effectively off**, since our scaling does not touch these today (that is the bug).

### 2a. THE DISCRIMINATOR — do this one first

Same boss, same name, two arenas, **10x apart**:

| where | entity | expected runes |
|---|---|---|
| Glintstone Dragon Adula — **Cathedral of Manus Celes** (first) | `1034500800` | **12,000** |
| Glintstone Dragon Adula — **Moonfolk Ruins / Ranni's Rise approach** | `1034420800` | **120,000** |

- **Both match →** the payout is keyed per ARENA, our id→row join is right, and ShadowTL's 120,000
  is the `1034420800` row exactly. Everything in the spec stands.
- **Both pay the same →** the join is wrong and the whole §1 model needs re-deriving. Stop there.

### 2b. Early confirmations, cheap to reach

| boss | entity | expected |
|---|---|---|
| Grafted Scion (tutorial) | `10010800` | 3,200 |
| Tree Sentinel (Limgrave) | `1042360800` | 3,200 |
| Deathbird | `1042380800` | 2,800 |
| Bell Bearing Hunter | `1042380850` | 2,700 |
| Bloodhound Knight Darriwil | `1044350800` | 1,900 |
| Mad Pumpkin Head | `1044360800` | 1,100 |

### 2c. One oddity worth an eyeball

`20010850` **Needle Knight Leda** reads `bonusSoul_single = 0`. Either she pays nothing from this
table (her runes come from elsewhere), or 0 is a real "no arena bonus". If she visibly pays runes,
this table is not the whole story for NPC-style bosses.

**Record for each: boss, expected, observed, NG level, any rune-boost gear worn.** A Gold Scarab
(+20%) or Gold-Pickled Fowl Foot (+30%) will multiply the observed number — take them off, or note
them, or the whole sheet reads as a mismatch.

## 3. Needs a build — the two questions a probe must answer

These decide the implementation and cannot be answered by playing:

1. **Is `GameAreaParam` reachable and writable at runtime** through the typed API, the way
   `check_lots.rs` / `enemy_drops.rs` reach their params? Read `bonusSoul_single` for `1034420800`
   and confirm it reads **120000** before writing anything. (Read-only first — the
   `scaling_probe.rs` pattern: latch after one dump, no writes.)
2. **When must the write land?** Before the arena loads, before the fog wall, or any time before the
   kill? This decides whether it is a connect-time sweep or a region-transition hook.

Suggested shape: extend `scaling_probe.rs` (already read-only and latched) to dump the row, then a
separate flag-gated write of ONE row to a distinctive value (e.g. Darriwil 1,900 → 9,999) so the
result is unmistakable.

## 4. While you are in there — two unrelated open questions

Both are from 2026-07-28 and both need the live oracle, not more datamining:

- **`f580600` Message from Leda** (Belurat, near Scaduview Cross) is now missable-tagged on your
  confirmation that it needs Messmer dead. Worth one look that the pickup is genuinely ABSENT before
  Messmer and present after — that is the assumption the tag rests on.
- **The Patches pair, Murkwater Cave** (`31007010` Cloth Garb / `31007030` Glass Shard). The EMEVD
  swaps them on state `3691`, so exactly one exists at a time. **Nobody has ever confirmed whether a
  player can get BOTH across one run.** Both are tagged missable for safety; if both are obtainable
  the tags are costing two filler slots for nothing.
