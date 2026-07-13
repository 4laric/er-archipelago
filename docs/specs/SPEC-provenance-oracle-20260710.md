# SPEC: Provenance derivation oracle — make re-pinning illegal

**Status:** draft (2026-07-10) · **Owner:** Alaric · **Scope:** greenfield `gen_data.py` + a new tier-A test gate
**Motivating diagnosis:** the week's dominant work (cluster 1: "re-pin X to region Y", "recover N from HUB")
is interest paid on a missing arbiter. Every re-pin patches the *output* of a wrong derivation instead of
the derivation. This spec turns "Alaric notices in-game" into a CI predicate, so the whack-a-mole terminates.

---

## 1. The problem, concretely

`region_of(r)` (gen_data.py:927) is *almost* a pure function of a datamined row, but it resolves through a
stack of **hand-maintained in-code override dicts**:

- `FLAG_REGION_OVERRIDE` (gen_data.py:512) — per-acquisition-flag, wins over everything. ~40 rows, each with
  a prose comment justifying it.
- `DUNGEON_REGION_OVERRIDE` (gen_data.py:594) — per-map-id.
- `GLOBAL_RECOVER` (curated globals) — per-flag for `method in (global, global_filler)`.

Three structural gaps:

1. **No arbiter across independent region opinions.** The same location's region is asserted independently by
   `data.py` LOCATIONS, `boss_data.py` REGION_BOSSES, `boss_sweeps.py` membership, the grace `play_region_id`,
   and the flag's own map-tile decode. Nothing forces them to agree. **The Full Moon Queen bug is exactly this
   class**: `data.py` said Stormveil, `boss_data`/sweeps said Liurnia, flag 197 only fires at Raya Lucaria —
   three files holding independent opinions, caught only when a region Lock stranded in-game (2026-07-08).
2. **Overrides carry reasons in comments, not in data.** A machine can't tell a playtest-verified pin from a
   guess, can't report *why* a row exists, and can't detect when a row has become redundant.
3. **No shrink pressure.** When a derivation fix generalizes (e.g. the boundary-tile `play_region_id` fix that
   killed ~413 DLC mis-regions in one commit), the now-redundant per-flag overrides are never reaped. The
   override tables only grow.

The only arbiter today is Alaric playing the seed. That is why cluster-1 work feels unbounded: **it is
unbounded under that method.** There is no signal that says "the region map is done."

## 2. Definition of done

`region(location)` is a **pure function of datamined inputs**, plus exactly one explicit override table where
**every row carries a reason**, guarded by two CI predicates:

- **Predicate A — disagreement gate:** any location whose independent derivations disagree (at cluster
  granularity) *without* a matching override row → FAIL.
- **Predicate B — shrink gate:** any override row that the pure derivation would now produce on its own →
  FAIL (delete it). The override table monotonically shrinks as the derivation improves.

"Done" = both gates green with an *empty or minimal, fully-justified* override table. The map is provably
complete when no cross-derivation disagreement survives without a documented reason.

This is not new machinery — `test_gf_grace_region_correctness.py` already implements Predicate A for **graces
only**, with the exact governing rule ("a checker that shares derivation code with the thing it checks is not
an oracle") and the cluster-granularity trick (check the 61xxx/62xxx/... thousands bucket, not the fine pid,
so legitimate intra-cluster curation isn't flagged). This spec **generalizes that test from graces to all
locations** and adds Predicate B.

---

## 3. Design

### 3.1 Externalize overrides into one reason-carrying table

Replace the three in-code dicts with a single loaded data file `greenfield/region_overrides.tsv`:

```
key_kind   key          region                    reason_code      evidence                              added
flag        197          Liurnia of the Lakes      boss_home        flag197=Rennala kill @ Raya Lucaria   2026-07-08
flag        1039507100   Altus Plateau             nn_boundary_tie  Godefroy evergaol; m60_39_50 NN-tie   2026-07-08
mapid       m32_00_00_00 Weeping Peninsula         coarse_bucket    Morne Tunnel physically in Weeping    2026-07-08
```

- `key_kind ∈ {flag, mapid}`; `reason_code` is a closed vocabulary (see 3.4) so Predicate B can decide
  reap-ability per class. `evidence` + `added` preserve today's comments as queryable fields.
- `gen_data` loads this once and builds `FLAG_REGION_OVERRIDE` / `DUNGEON_REGION_OVERRIDE` from it —
  `region_of()`'s control flow is unchanged; only the *source* of the dicts moves from code to data.
- Keep the file beside `region_map.csv` (gen input, not packaged). It joins the §5 input manifest.

### 3.2 Independent derivations (the oracle inputs)

For a location row, compute region by up to four *independent* paths. Independence is the whole point — each
must avoid the transform it audits (mirror the grace test's independence argument in a docstring per oracle).

- **O1 — grace/tile pid cluster.** For overworld rows: the `play_region_id` cluster from `grace_region_map`
  (already the grace oracle's source). Interior rows: the tile prefix's pid.
- **O2 — boss identity.** If the flag is a boss remembrance/drop (it's in `REGION_BOSSES`, `BOSS_DROP_FLAGS`,
  or `BOSS_HEALTHBARS`), the boss's region is authoritative. This is the axis that catches Full Moon Queen.
- **O3 — sweep membership.** The `boss_sweeps.py` region that scopes this flag's sweep.
- **O4 — flag self-decode.** The map tile encoded in the flag itself (interior `X0SS7000` → `mMM_SS`;
  field-boss `10<XX><YY>0800` → `m60_XX_YY`) → region. Already present as `_recover_tile` / `_unique_m60`.

Not every location has all four; the oracle uses whichever ≥2 exist.

### 3.3 Predicate A — disagreement gate (new tier-A test)

`tests/test_gf_region_provenance_oracle.py`:

```
for each location:
    opinions = {name: cluster(region) for name, region in available_derivations(loc)}
    if len(set(opinions.values())) > 1:          # cross-derivation disagreement
        assert loc.key in OVERRIDES,  f"{loc}: {opinions} disagree, no override row"
        # and the override's region must match the emitted region
```

Granularity = cluster (per the grace test), so intra-cluster curation (Wyndham → Altus) doesn't trip it, but a
cross-cluster split (data.py 61xxx-region vs boss_data 62xxx-region) is the unambiguous misbundle signature.
**This is the whack-a-mole terminator:** a newly-introduced mis-region is now either caught mechanically
(disagreement → red CI) or genuinely ambiguous (→ forces an override row *with a reason*). No third path where
it silently ships and waits for a playtest.

### 3.4 Predicate B — shrink gate (new test)

For each override row, re-run the pure derivation with that row **suppressed**:

```
for row in OVERRIDES:
    derived = region_of_pure(row.key, suppress=row.key)   # no override applied
    assert cluster(derived) != cluster(row.region) or row.reason_code in NN_TIE_CODES, \
        f"override {row.key} is now redundant (derivation yields {derived}); delete it"
```

`reason_code` gates the exemption: a `nn_boundary_tie` legitimately can't be derived (the NN vote genuinely
ties and picks wrong), so it's exempt from reaping; a `coarse_bucket` or `scan_mistile` override *should*
disappear once the coarse path is fixed, so it's reap-required. This is what forces the table to shrink: the
~413-mis-region DLC fix would have flagged its now-redundant per-flag overrides as deletable.

### 3.5 The final arbiter — pickup-time provenance log

CI oracles derive from the same artifacts the generator reads; the *ground* arbiter is what the client reads
under the player's feet (that's what enforces the region KICK). Close the loop:

- **Client:** on every check pickup, append `{flag_id, ap_id, live_play_region, seed}` to a
  `provenance.jsonl`. `live_play_region` = the `play_region` the game reports at pickup (already read for the
  KICK; see `play_region` id source note / BonfireWarpParam path).
- **Diff tool** `tools/verify_provenance_log.py`: join the log against `data.py` LOCATIONS by flag; any
  `cluster(live) != cluster(emitted)` is a real mis-region, reproducible from data (no re-roll needed —
  respects the high-bar-for-stale-seed rule).
- **Payoff:** every hour anyone plays — Alaric or a tester — becomes free provenance verification, and it
  feeds the tester cohort (§ "aim testers at generation + traversal"). This is the cheapest oracle available
  because the client already computes `live_play_region`.

---

## 4. Migration path (cheapest-first; each step independently shippable)

1. **Externalize overrides → `region_overrides.tsv`** (mechanical; behavior-preserving). Unblocks B.
2. **Wire O2+O3 into Predicate A** (boss identity vs data.py). Catches the Full Moon Queen *class* today with
   the two derivations that already exist. Highest value per hour.
3. **Add O4** (flag self-decode) to widen coverage to non-boss overworld drops.
4. **Predicate B shrink gate** — reap the first redundant overrides; prove the table can shrink.
5. **Pickup-time provenance log + diff tool** — the ground arbiter; ship alongside the tester instrumentation.

## 5. Worked example — Full Moon Queen (the regression this retires)

- `data.py`: flag 197 emitted under **Stormveil** (m10 mis-tile in region_map.csv).
- O2 (boss identity): flag 197 = Rennala's kill → `_BOSS_SPECIALS` 14000800 → **Liurnia**.
- Predicate A: `{data: Stormveil(61-cluster via m10), boss: Liurnia(62)}` disagree cross-cluster, no override
  row → **FAIL at gen time**, months before a seed strands a Lock on it.
- Resolution: add `flag 197 → Liurnia, reason=boss_home` (already the FLAG_REGION_OVERRIDE comment) — now a
  *justified data row*, and Predicate B keeps it (boss_home is derivable → actually reap-required once O2 is
  wired as the primary path, collapsing even this override).

## 6. Files touched

- `greenfield/gen_data.py` — load overrides from tsv (3.1); expose `region_of_pure(key, suppress=)` (3.4).
- `greenfield/region_overrides.tsv` — **new** single override table.
- `greenfield/eldenring_gf/tests/test_gf_region_provenance_oracle.py` — **new** Predicates A + B.
- `greenfield/eldenring_gf/tests/test_gf_grace_region_correctness.py` — refactor its oracle helpers into a
  shared `tests/_provenance_oracle.py` the new test reuses (don't duplicate the cluster map).
- `tools/verify_provenance_log.py` + client `provenance.jsonl` writer — **new** (step 5).
- CI: add the new test to `run_ci.ps1` / `ci-linux.sh` tier-A set.

---

## IMPLEMENTATION NOTES (2026-07-10, landed)

Alaric's steer: the ground-truth sources are the **witchy'd MSBs**, the **Smithbox param dump**, and
the **EMEVD event scripts** -- the MSBs carry the actual item placements and there are multiple
relevant param tables. That is exactly the authoritative **O0** this spec wanted, and it's now wired.

**The join (validated end-to-end):**
`elden_ring_artifacts/mapstudio/<map>-msb-dcx/Event/Treasure/*.xml` -> `<ItemLotID>` (the item lot
physically placed in that map) -> `vanilla_er/.../ItemLotParam_map.csv` `getItemFlagId01..08` -> the
acquisition flag. The map is the MSB's own id (dir name), so this is a flag -> map ground truth with
**zero** dependence on region_map.csv. Proven on m10_00 (Stormveil): **102/102** treasure flags agree
with data.py's Stormveil assignment; on m14_00 (Raya Lucaria): 66/66 -> Liurnia (Raya folds in).

**Shipped:**
- `tools/datamine_msb_item_regions.py` -- emits `greenfield/msb_flag_region.tsv` (flag, map_id,
  item_lot_id, treasure_name). Run on **Windows** over the full ~1000-map set (the scan is slow over
  the sandbox FUSE mount; `--maps` restricts for validation). Witchy dependency: the packed `.msb.dcx`
  is Oodle-blocked on Linux, so the witchy XML export must be produced on Windows (all 1028 maps are
  already witchy'd under `mapstudio/`).
- `greenfield/eldenring_gf/tests/test_gf_region_provenance_oracle.py` -- **Predicate A as same-map
  consistency**: every flag the MSB places in one physical map block must get ONE data.py region (the
  map's majority); a disagreer is a mis-pin unless a reasoned row in `region_overrides.tsv` justifies
  it. This needs no hand-built map->region table (independence preserved) and caught an injected
  Caelid mis-pin in a negative test. Skips cleanly until the tsv is regenerated on Windows.

**Refinement of the O-list vs. this landing:** same-map consistency subsumes O1/O4 for **map-placed**
items (chests, corpses, ground pickups -- the bulk of the re-pin churn). It does **not** yet cover
**enemy/boss DROP** mis-pins (e.g. flag 197 Rennala), which flow through `ItemLotParam_enemy` + the
enemy's MSB placement -- that's the documented **v2** of the extractor (O2 boss-identity remains the
cheap stopgap for those). Predicate B (shrink gate) and the pickup-time provenance log are still to do.

**Next (Windows):** `python tools/datamine_msb_item_regions.py` -> commit `msb_flag_region.tsv` ->
the oracle goes live over the full map set; then triage any real mis-pins it surfaces into
`region_overrides.tsv` or a region_map.csv fix.
