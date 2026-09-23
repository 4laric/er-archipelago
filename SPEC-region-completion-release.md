# SPEC: region-completion release (design 2)

Status: PROPOSED, 2026-09-23. Measured against `main` @ `d3b14a72`.

This is "design 2" of the two named in [SPEC-broaden-sweeps.md](SPEC-broaden-sweeps.md) §0: **instead
of widening what an individual boss's sweep reaches, add a mode where beating a region's boss(es)
releases every remaining check in that named region.** Not a replacement for the existing sweep
ladder (`dungeon_sweep: none|minidungeons|all|bosses`) -- an alternative top rung a player opts into.

Origin: DivinePuma on Discord, 2026-09-23, asking whether beating Radahn could check the whole of
Caelid for an all-regions race against a friend on a much smaller game. Confirmed: this existed
before and was removed; design 1 (the current sweep ladder) replaced it because it does not strand
progression the way a naive region-clear can.

**Revised per Alaric, 2026-09-23: the trigger is the last GATING boss, not any boss** (see §1) --
Great Rune boss where the region has one, else the region's biggest Remembrance boss, else its major
boss. This trades the zero-judgment "any boss" rule for a curated one-trigger-per-region table, in
exchange for matching what a region's boss actually felt like when this existed before.

---

## 0. Answer first

The mechanism is small: `SWEEP_REGION` in
[boss_sweeps.py](greenfield/eldenring/tables/boss_sweeps.py) already maps every sweep trigger to the
named region its boss stands in, and `region_of` (see SPEC-broaden-sweeps.md §4) already assigns a
trustworthy region to all but 211 of the 3792 sweepable/payload checks. Region completion is "grant
every check whose `region_of` matches, once any trigger in `SWEEP_REGION` for that region has fired" --
no new region data, no new geometry.

The work is not the lookup. It is three judgment calls this doc exists to pin down:

1. **Which boss(es) fire it** -- every boss in the region, or only the one(s) that gate leaving it?
2. **What is exempted** -- same three carve-outs `full_area_sweeps` already has (another boss's
   reward/remembrance/Great Rune, quest-gate key items, merchant stock), plus a new one this design
   needs that the others don't: **regions with an unspawned/dead boss** (SPEC-broaden-sweeps.md §9)
   need a substitute trigger or they can never complete.
3. **Interaction with `dungeon_sweep`** -- a new top rung, or a standalone toggle that composes with
   the existing ladder?

Recommendation: **§1 last-gating-boss (per Alaric), §2 same carve-outs as `full_area_sweeps` plus the
dead-boss table, §3 standalone toggle** (`region_sweep: false` by default), not a ladder rung --
reasoning below.

---

## 1. Trigger: the region's single gating boss, picked by a fixed priority

Per Alaric's call: one curated trigger per region, not "whichever boss falls first." The priority
ladder, applied per region:

1. **Great Rune boss**, if the region has one. `features/great_runes.py::GREAT_RUNE_DETECT_FLAGS`
   already gives six of these as `{location ap_id: boss defeat flag}` -- Stormveil/Godrick
   `10000800`, Caelid/Radahn `1252380800` (the festival-alias form, per that file's warning --
   `1052380800` never fires), Leyndell/Morgott `11000800`, Mt. Gelmir/Rykard `16000800`,
   Mohgwyn/Mohg `12050800`, Haligtree/Malenia `15000800`. Raya Lucaria's rune is the seventh and sits
   on Rennala, whose flag is `14000800`/`14000850` (Full Moon Queen, `SWEEP_REGION` already keys it
   "Raya Lucaria Academy") even though Rennala's rune detection itself runs through f197 rather than
   `GREAT_RUNE_DETECT_FLAGS` -- the sweep trigger and the rune-possession trigger are different flags
   on the same boss, which is fine, only the sweep trigger matters here.
2. **Biggest Remembrance boss**, for a region with no Great Rune. `tables/boss_data.py` carries the
   name/reward-flag rows (e.g. `510430` -> "Remembrance of a God and a Lord"), and
   `tables/boss_reward_lots.py::BOSS_REWARD_DEFEAT` maps each reward flag to the boss's own defeat
   flag -- the same join `great_runes.py` uses for its six. Most non-rune regions hold exactly one
   Remembrance boss (Fire Giant/Mountaintops, Loretta/Consecrated Snowfield, Godskin Duo or the
   Tree Sentinel duo/Altus, etc.) so the join is enough on its own. A handful hold more than one
   (Shadow Keep alone has several DLC Remembrances) -- "biggest" there is a judgment call this spec
   does not automate; it needs a short curated override list, reviewed by Alaric, rather than an
   invented ranking (boss health, drop tier, and fight order all disagree with each other often
   enough that none of them is a safe proxy).
3. **Major boss**, fallback for a region with neither. `tables/location_tags.py`'s `MajorBoss` tag
   (the same category `progression_surface`'s default list already trusts) identifies the
   region's headline non-Remembrance, non-Rune fight -- e.g. Godefroy/Weeping Peninsula.

This produces `REGION_GATING_BOSS: Dict[str, int]` (region name -> single defeat flag), a NEW small
curated table, built once from the three joins above and hand-checked against the exception in §2.
It replaces `SWEEP_REGION`'s many-triggers-per-region shape as region-completion's OWN mapping;
`SWEEP_REGION` itself is untouched and keeps serving design 1.

One consequence worth saying plainly: unlike "any boss," this can genuinely gate a player on a fight
they'd rather skip or save for last -- Radahn, Malenia, Rennala and friends are not optional in the
way a stray field boss is. That is the intended trade (matches how it used to feel), not an oversight.

### 1a. The table, built

Traced by hand through the three joins in §1 (`GREAT_RUNE_DETECT_FLAGS`, the Remembrance rows in
`tables/boss_data.py` joined through `tables/boss_reward_lots.py::BOSS_REWARD_DEFEAT`, and the
`MajorBoss` tag in `tables/location_tags.py`), with every name cross-checked against
`tables/boss_healthbars.py` so this isn't a flag-number guess:

| region | flag | boss | tier |
|---|---|---|---|
| Stormveil | `10000800` | Godrick the Grafted | Great Rune |
| Leyndell | `11000800` | Morgott, the Omen King | Great Rune |
| Caelid | `1252380800` | Starscourge Radahn | Great Rune (festival-alias flag, per great_runes.py) |
| Mt. Gelmir | `16000800` | Rykard, Lord of Blasphemy | Great Rune |
| Mohgwyn | `12050800` | Mohg, Lord of Blood | Great Rune |
| Haligtree | `15000800` | Malenia, Blade of Miquella | Great Rune |
| Raya Lucaria Academy | `14000800` | Rennala, Queen of the Full Moon | Great Rune |
| Ashen Capital | `11050800` | Godfrey, First Elden Lord | MajorBoss |
| Ainsel River | `12040800` | Astel, Naturalborn of the Void | Remembrance |
| Siofra River | `12090800` | Regal Ancestor Spirit | Remembrance |
| Deeproot Depths | `12030850` | Lichdragon Fortissax | Remembrance |
| Farum Azula | `13000800` | Maliketh, the Black Blade | Remembrance (picked over Placidusax `13000830` -- mandatory vs. optional, §1b) |
| Belurat | `20000800` | Divine Beast Dancing Lion | Remembrance |
| Enir Ilim | `20010800` | Radahn, Consort of Miquella | Remembrance |
| Scadu Altus | `25000800` | Metyr, Mother of Fingers | Remembrance |
| Shadow Keep | `21010800` | Base Serpent Messmer | Remembrance (picked over Commander Gaius `2049480800` / Scadutree Avatar `2050480800`, §1b) |
| Cerulean | `22000800` | Putrescent Knight | Remembrance |
| Abyssal | `28000800` | Midra, Lord of Frenzied Flame | Remembrance |
| Ancient Ruins | `2044450800` | Romina, Saint of the Bud | Remembrance |
| Ensis | `2048440800` | Rellana, Twin Moon Knight | Remembrance |
| Mountaintops of the Giants | `1252520800` | Fire Giant | Remembrance (festival-alias flag, same pattern as Radahn) |
| Weeping | `1043300800` | Leonine Misbegotten, Castle Morne Boss | MajorBoss |
| Liurnia | `1035500800` | Royal Knight Loretta | MajorBoss (picked over Magma Wyrm Makar `39200800`, a `dungeon`-class minor boss, §1b) |
| Altus | `1039540800` | Elemer of the Briar | MajorBoss |
| Consecrated Snowfield | `1050560800` | Great Wyrm Theodorix | MajorBoss |
| Rauh Base | `2044470800` | Rugalea the Great Red Bear | MajorBoss |
| Jagged Peak | `2054390800` | Bayle the Dread | MajorBoss |
| Limgrave | `1043360800` | Flying Dragon Agheel | Alaric's call, §1c -- no MajorBoss/Remembrance/Rune candidate exists |
| Gravesite | `41010800` | Curseblade Labirith | Alaric's call, §1c -- no MajorBoss/Remembrance/Rune candidate exists |

All 29 named regions now have a gating boss. 27 resolve mechanically through the stated priority; the
last two (Limgrave, Gravesite) had no Great Rune/Remembrance/MajorBoss candidate at all and were
picked directly rather than derived (§1c).

### 1b. Ties resolved, and why

* **Farum Azula** -- Maliketh over Placidusax. Maliketh is the mandatory boss standing in the way of
  the Rune of Death; Placidusax is an optional secret fight reachable only after Maliketh anyway, so
  gating on him would make Maliketh's own kill insufficient to release a region his death already
  unlocks the path to. Maliketh is also the only one of the two `MAJOR_SWEEP_TRIGGERS` (in
  `boss_sweeps.py`) marks structurally required.
* **Shadow Keep** -- Messmer over Commander Gaius / Scadutree Avatar. Messmer's Remembrance is
  literally named "Remembrance of the Impaler" and he is the Shadow Keep's own legacy-dungeon boss
  (the capital's throne room, same shape as Morgott/Leyndell or Mohg/Mohgwyn); Gaius and the
  Scadutree Avatar are optional field/legacy bosses elsewhere in the region.
* **Liurnia** -- Royal Knight Loretta over Magma Wyrm Makar. Loretta is `MajorBoss`-tagged and gates
  the Academy approach; Makar is a `dungeon`-class boss inside one optional minor dungeon
  (Ruin-Strewn Precipice) and was never a candidate at the same tier.

None of these three change the region's completion condition in a way that stalls out: each pick is
either the region's sole `MAJOR_SWEEP_TRIGGERS` member or a Remembrance boss with no MajorBoss rival.

### 1c. The two regions with no mechanical candidate -- picked directly

* **Limgrave** has no Great Rune, no Remembrance boss, and none of its sweep triggers
  (`18000800`/`18000850`, `30020800`, `30040800`, `30110800`, `31000800`/`31000850`, `31030800`,
  `31150800`, `31170800`, `32010800`, and the several `104x`/`105x` field triggers `SWEEP_REGION`
  lists as Limgrave) are `MajorBoss`-tagged -- confirmed against `MAJOR_SWEEP_TRIGGERS`, which
  contains none of them. This tracks: Limgrave is the tutorial region and its named bosses are
  `FieldBoss` / `MinorDungeonBoss` tier by design. **Alaric's pick: Flying Dragon Agheel, `1043360800`**
  -- the region's most recognizable field boss (the dragon at the lake), a `field`-class trigger
  already in `SWEEP_REGION` under Limgrave with no MajorBoss rival to outrank it.
* **Gravesite** similarly has no Great Rune or Remembrance boss, and its sweep triggers
  (`40000800`/`40010800` Death Knight, `41000800`/`41010800`/`41020800` minor dungeon bosses,
  `43000800`/`43010800` catacomb bosses) are all `dungeon`-class per `boss_healthbars.py`, none
  `MajorBoss`. The region's headline boss by reputation, Blackgaol Knight, isn't in `SWEEP_REGION` at
  all -- he grants no sweep group of his own, so he's not usable without new plumbing.
  **Alaric's pick: Curseblade Labirith, `41010800`** -- already a wired sweep trigger, no new detect
  flag needed.

Both picks are direct calls rather than derivations, same as any curated override -- recorded here so
a future regen doesn't try to re-derive them from a priority rule that doesn't reach either boss.

---

## 2. Exemptions

Same three the docs for `full_area_sweeps` in
[EldenRing.yaml](release/EldenRing.yaml) already carry, because a region-wide grant is `full_area_sweeps`
turned up to the whole map and should not strand progression any more than that setting does:

* another boss's own reward, remembrance, or Great Rune stay put -- only that boss's own kill grants
  those, region completion never substitutes for beating a specific boss
* quest/gate key items stay put -- a region clear cannot hand you a key that unlocks something outside
  the region, or the "kept a region you can already reach" invariant that makes sweeps safe breaks
* merchant stock stays put, as always

One check **only region completion needs**, because a curated single trigger makes the failure mode
sharper than design 1's "any boss": if `REGION_GATING_BOSS` ever pointed a region at one of the five
dead/unspawned-boss triggers from SPEC-broaden-sweeps.md §9 (`contract._RUNTIME_SWEEP_SKIP_REASONS`),
that region could NEVER complete -- no player action sets a flag that's dead code. None of the five
are Great Rune, Remembrance, or `MajorBoss`-tagged fights (they're obscure field/tower bosses that
were never spawned at all), so the three-tier priority in §1 should never reach for one by
construction -- but the acceptance test for this spec must assert it explicitly rather than trust
that: **no value in `REGION_GATING_BOSS` may appear in `_RUNTIME_SWEEP_SKIP_REASONS`**, checked at
build time so a future edit to either table cannot silently produce an unwinnable region. If a
future region's only candidate gating boss ever turned out to be dead, it needs either a substitute
flag) or the option itself to refuse to enable with that region in the pool.

---

## 3. Where it sits relative to `dungeon_sweep`

**Standalone toggle**, `region_sweep: false`, not a fifth rung on the `dungeon_sweep` ladder:

* the ladder (`none|minidungeons|all|bosses`) is about WHICH CLASSES of boss grant a sweep at all --
  it's additive in scope, each rung a strict superset of the last's trigger set. Region completion is
  a different axis: given that a boss fires, HOW MUCH does it grant. Bolting it onto the ladder as a
  fifth value would make `dungeon_sweep: region` silently also imply `bosses`, `full_area_sweeps`, and
  every other sweep-adjacent option, which is exactly the kind of one-option-does-five-things design
  the yaml already avoids elsewhere (see the `full_area_sweeps` docstring: it's a modifier, not a rung).
* a standalone toggle can compose: `region_sweep: true` with `dungeon_sweep: minidungeons` still lets
  minor-dungeon bosses release their own dungeon per the existing rule, AND now the region's gating
  boss (§1) releases the whole region on top. `region_sweep: true` with `dungeon_sweep: none` means no
  boss grants anything at all -- consistent, since `none` already means sweeps are off entirely
  regardless of any other option, and the gating boss's own kill is itself a sweep trigger.
* it should imply `full_area_sweeps: true` for a region it releases (the same "no other boss's
  reward/remembrance/rune/quest key" exemption applies, and a region grant that still withheld
  progression-tagged filler on its own toggle would be a second, redundant flag). Recommend: turning on
  `region_sweep` sets the effective progression-inclusion behavior to match `full_area_sweeps` for the
  checks it grants, without requiring the player to also flip `full_area_sweeps` for their whole seed.

---

## 4. Acceptance tests

1. `test_region_sweep_covers_all_named_regions` -- every region in `SWEEP_REGION`'s value set has an
   entry in `REGION_GATING_BOSS`, and that entry's flag is not in `_RUNTIME_SWEEP_SKIP_REASONS` (§2).
2. `test_region_sweep_respects_carveouts` -- a region-completion grant excludes the three
   `full_area_sweeps` carve-outs (own-boss reward/remembrance/rune, quest-gate keys, merchant stock),
   reusing whatever filter `full_area_sweeps` already applies rather than re-deriving it.
3. `test_region_sweep_disjoint_from_hub` -- HUB-region checks (Roundtable Hold / unresolved) are never
   granted by a region trigger, same exclusion `_filler_only` payload already applies in design 1.
4. `test_region_sweep_off_by_default_matches_existing_seeds` -- `region_sweep: false` (default)
   produces byte-identical output to today, i.e. this is purely additive and opt-in.
5. `test_region_sweep_composes_with_dungeon_sweep_none` -- `region_sweep: true` +
   `dungeon_sweep: none` grants nothing (no trigger fires because no sweep class is enabled at all).
6. `test_region_gating_boss_priority` -- every `REGION_GATING_BOSS` entry that isn't a curated
   override resolves via the documented priority (Great Rune via `GREAT_RUNE_DETECT_FLAGS`, else
   Remembrance via the `BOSS_REWARD_DEFEAT` join, else `MajorBoss` tag) rather than being hand-picked
   out of step with §1 -- guards against the table drifting from its own stated rule as regions get
   added or bosses get reclassified.

---

## 5. What this does NOT change

* The existing per-boss sweep ladder (design 1, SPEC-broaden-sweeps.md) ships unconditionally and is
  unaffected -- `region_sweep` is additive on top of it, not a replacement.
* No new region/geometry data. `SWEEP_REGION` and `region_of` are reused as-is.
* The 211 PENDING-position checks (SPEC-broaden-sweeps.md §5) that no spatial sweep can ever reach ARE
  reachable here, same as any other check in a completed region -- this is in fact the whole argument
  for design 2 existing alongside design 1 (SPEC-broaden-sweeps.md §5, last paragraph).

## 6. Open questions

1. Exact wording/placement in `EldenRing.yaml` and the wizard -- propose next to `full_area_sweeps`,
   since the two are closely related in effect.
2. Whether `reveal_sweep_boss_names` needs a region-completion-specific note (a region clear is a much
   bigger spoiler surface than one boss's sweep list).
3. ~~Limgrave and Gravesite have no clean gating-boss candidate~~ RESOLVED 2026-09-23: Agheel
   (`1043360800`) and Curseblade Labirith (`41010800`), Alaric's direct picks (§1c). All 29 regions
   in `REGION_GATING_BOSS` (§1a) are now filled.
