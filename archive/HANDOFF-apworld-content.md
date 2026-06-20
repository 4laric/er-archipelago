# HANDOFF — apworld content (#14 readability + #13 region_lock hardening)

Done in-sandbox; the gen-test (#13 step 1) needs you to run AP (Python 3.11+). No slot_data
keys or version range touched — region-fusion contract stays frozen.

## Task A — lean check names readable (#14)  ✅ shipped

**1. Legend doc** — `Archipelago/worlds/eldenring/docs/check-name-legend.md`.
Auto-derived from `locations.py` (not invented): all **57 region prefixes** + **264 subarea
codes** across the **443 lean checks**, each subcode resolved to the exact region entry it lives
in. Includes the naming convention, worked examples, and a "known data anomalies" section.

Anomalies worth a cleanup pass later (decode fine, just non-standard):
- **`SV` is overloaded** — Stormveil (base) *and* DLC Scaduview/Scadutree (`SV/SKBG`, `SV/(SC)`).
- **`SA?FR`** — a literal `?` where `/` belongs (single check: Aspects of the Crucible: Wings).
  Should be `SA/FR`.
- Compound `|` tags (`BTS|EI`, `LRC|LAC`, `MP/PALR|(MDM)`) = checks straddling two phases.
- Suffix-without-slash (`LG(TCM)`, `WP(CBC)`); stray `BS:` (Bestial Sanctum) and `Cross:` (Leda
  questline, not a region).

**2. `location_descriptions` populated** — `locations.py`, new import-time block right after the
`location_descriptions = { … }` literal (`_er_describe_lean_checks()`). It decodes each lean
check's `REGION/SUBAREA` into the precise region name (the `location_tables` key), tags the check
type, and keeps the original directional hint. **Additive only** — keyed by the verbatim location
name via `setdefault`, so no entrance/location-rule refs break. Generates **443** descriptions.

Example output:
```
"SV/SeC: Godrick's Great Rune - mainboss drop"
   → "Stormveil Castle. Main boss reward. mainboss drop"
"CL/(SCT): Somber Smithing Stone [7] - scarab to NE"
   → "Sellia Crystal Tunnel. Minor-dungeon boss reward. scarab to NE"
"LL/(DV): Cursemark of Death - top of tower"
   → "Carian Study Hall (Inverted). Key item. top of tower"
```
Syntax-checked (`py_compile`), CRLF preserved. **Your verify:** generate a seed and confirm
generation still succeeds and the descriptions surface in your tracker/hint client.

## Task B — region_lock deadlock + soft-order audit (#13)

### Underground audit — no deadlocks found
Traced the full connection graph against `_region_lock()` and `grace_data.py`:

| Region | Graph parent(s) | Lock / extra gate | Verdict |
|---|---|---|---|
| Siofra River | Limgrave | SE Underground Lock | early, fine |
| Nokron Eternal City Start | Limgrave | SE Underground Lock + Starscourge remembrance | post-Radahn, fine |
| Deeproot Depths | Nokron → Deeproot | **North** Underground Lock | consistent w/ grace bundle; not a deadlock |
| Deeproot Depths Upper | Frenzied Flame Proscription | `_can_go_to(FFP)` | **terminal** — does NOT chain into Deeproot Depths |
| Ainsel River / Main | Liurnia | North Underground Lock | fine |
| Lake of Rot | Ainsel Main | SW Underground Lock | 3-deep (Liurnia→North→SW) but reachable |
| Moonlight Altar | Lake of Rot | Dark Moon Ring | fine |

**Suspected back-doors checked and cleared:** the Four Belfries portal nodes
(`(Nokron)`, `(Farum Azula)`, `(Chapel of Anticipation)`) and `Deeproot Depths Upper` are all
**terminal regions** (no outgoing `create_connection`), so they hold their own loot but do not
bypass any region lock. Entrance locks and `grace_data.py REGION_LOCK_ITEM` agree throughout
(e.g. Deeproot = North Underground Lock for both access and graces).

**Observations to confirm in gen-test (not bugs):**
- Nokron effectively needs **Altus** reachable — its Starscourge-remembrance gate routes through
  Wailing Dunes, which requires `_can_go_to(Altus)`. SPEC wanted Nokron≈tier-3; it lands ~tier-4.
- Lake of Rot needs two underground keys (North + SW). Deeper than SPEC's tier-2 but completable.
- If you'd rather Deeproot read as SE/Nokron-tier, you'd move it to `South East Underground Lock`
  in **both** `_region_lock()` and `grace_data.py REGION_LOCK_ITEM` together (keeps the bundle in
  sync). Left as-is — it's internally consistent and not a deadlock.

### High-tier regions are already protected from sphere 1
Mountaintops (Rold + great runes + Forbidden Lands), Flame Peak (3 bell bearings), Leyndell Ashen
(5 bell bearings + Ashen Lock), Haligtree / Consecrated Snowfield (behind Forbidden Lands), Farum
Azula (only reachable via Flame Peak ← Mountaintops) — all gated by parent chains/items, so their
lock key being early can't open them in sphere 1.

### One soft-order added (#13 step 3) — light, item-based
The only genuine sphere-1 risk was the **early Varré/Pureblood-medal rush to Mohgwyn** (reachable
straight from Limgrave via the sending gate). Added inside the existing `if self.options.soft_logic:`
block in `__init__.py`:
```python
self._add_entrance_rule("Mohgwyn Palace", "Liurnia Lock")
```
Item check only (no `_can_go_to` chaining — that recurses, per the deathless note); mirrors the
`region_boss` "Liurnia Bosses" gate. Cannot deadlock: nothing en route to Liurnia needs Mohgwyn,
and the DLC entry (Mohgwyn→Gravesite) is meant to be mid-game. Syntax-checked, CRLF preserved.
Deliberately kept to this one line — the rest of the tiers are already safe, and the SPEC says the
strict chain is a fallback only.

### Gen-test procedure (your turn — sandbox can't run AP)
Three ready configs in `gen-test/` (identical to the validated Alaric.yaml except the gating knobs;
`world_logic: region_lock`, `soft_logic: true`, `location_pool: lean`, `graces_per_region` = 0 / 1 / 3):

1. `Archipelago/Players/` is read **wholesale** — stash any current yaml, then copy in **one**
   gen-test file at a time:
   `Copy-Item gen-test/ER_regionlock_graces1.yaml Archipelago/Players/` (clear Players first).
2. `./build.ps1 -Generate` (run a few seeds per config — vary the seed).
3. **Pass** = generates + completable, **no** "unreachable"/"unbeatable"/fill failure; check the
   spoiler that no high-tier region (Farum/Ashen/Haligtree/Mountaintops/Mohgwyn) sits in sphere 1;
   confirm all three grace counts still emit valid `regionGraces`.
4. **If a region_lock gen/bake deadlocks on `volcano_town`** → that's the bake-side loop
   (`BRIEF-randomizer-bake-stability.md` Task A / TODO #7), **not** this change. Link the finding;
   don't try to fix the C# from here.

Bake + in-game grace verification stays the human integration gate (BRIEF-PARALLEL-INDEX.md).
