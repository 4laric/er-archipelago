# BRIEF: apworld content — check-name readability (#14) + region_lock gen-test (#13 remaining)

Repo: **apworld** `Archipelago/worlds/eldenring` (Python; full AP source checkout, generate
in-tree). Contract-FREE in the wire sense: `location_descriptions` is additive hint text and
soft-ordering is logic — neither bumps the slot_data version. Safe to run parallel with the client +
randomizer briefs. See BRIEF-PARALLEL-INDEX.md. TODO #14 and #13.

> Dev loop: change apworld options/logic → **REGENERATE** (`build.ps1 -Generate`, or `-All`). The
> sandbox can't run AP generation (needs Python 3.11+) — hand gen-test runs to Alaric, or reason +
> write the code and let him run it. `Archipelago/Players/` is read WHOLESALE by Generate.py (every
> file, not just *.yaml) — keep ONLY the intended player yaml there; stash backups elsewhere.

---

## Task A — make lean check NAMES parseable (#14)

One sentence: `lean` check names are cryptic (e.g. `LL/SeI: Glass Shard - to S on isle`) and players
can't read them; make them parseable WITHOUT the risky verbatim rename.

**Why not just rename:** `__init__.py` references many location names verbatim (entrance/location
rules, `_fill_local`), so renaming the strings breaks those refs. Two safe paths — do the cheap one,
optionally the second:
1. **Abbreviation legend (cheapest, ship this):** decode all ~30 region prefixes + common subarea
   codes into a reference doc (e.g. `docs/check-name-legend.md` in the apworld, or repo root). Source
   the prefixes from `locations.py` (`region_order`, `region_order_dlc`, `location_name_groups`,
   `location_tables`) — grep the actual prefixes rather than inventing them. Output: a table mapping
   prefix → human region/subarea name + a couple of worked examples.
2. **Populate `location_descriptions` (additive, non-breaking):** it's already imported and assigned
   (`__init__.py:11` import, `:52` `location_descriptions = location_descriptions`). Fill readable
   text per lean check; trackers/hints surface it depending on client. This is additive — no logic
   refs break. Scope to the lean set first (boss/key/remembrance/flask/blessing/progression tags).

**Out of scope (note for later):** a full readable-rename with ref updates — risky, decide separately.

**Test:** legend doc covers every prefix that appears in a `lean` apconfig (cross-check against a
generated seed's location list). If you do `location_descriptions`, confirm generation still succeeds
and descriptions appear for the lean checks.

---

## Task B — gen-test region_lock for deadlocks + light soft-ordering (#13 remaining)

One sentence: region gating reshapes the logic graph; generate several `region_lock` seeds, hunt
unreachable/unbeatable deadlocks (undergrounds first), and add light soft-ordering so difficulty
doesn't swing wildly.

**Context:** the region-fusion CLIENT + apworld contract are DONE. `region_lock` (WorldLogic value 0,
`options.py:30`) is the logic half — per-region `.lock` items, emergent/shuffled order, built by
`_region_lock()` (`__init__.py:1031`). `regionGraces` emits for `world_logic < 3`. This task hardens
the LOGIC, it does not touch the contract.

**Steps:**
1. **Gen-test:** generate several `region_lock` seeds (vary `graces_per_region` 0/1/3 — graces don't
   affect logic but exercise slot_data). Any "unreachable" / "unbeatable" / fill failure = a
   mis-gated region. The connection graph normally inherits gates through gated parents; ER's
   back-doors are the risk.
2. **Undergrounds are the prime suspects** (geographically cross-tier): Siofra (Limgrave-early),
   Nokron/Deeproot (post-Radahn), Ainsel/Lake of Rot (Liurnia/Caelid-era). Verify each resolves
   against the connection graph; fix the gating where a back-door lets a region open too early/late.
   See SPEC-region-chain.md "Open questions on the mapping" for the proposed assignments to check.
3. **Light soft-ordering:** add a few soft dependencies so a high-tier region can't open in sphere 1
   (keep it LIGHT — the bundled graces make non-linear order tolerable; don't rebuild the strict
   7-tier chain, that's the SPEC's fallback only).
4. **Watch the volcano_town loop** (`BRIEF-randomizer-bake-stability.md` Task A / TODO #7): region
   gating changing the graph may surface that bake-side loop. If a region_lock gen/bake deadlocks on
   volcano_town, it's that bug — link the finding, don't try to fix the C# from here.

**Test:** N seeds generate + are completable with no unreachable progression; a high-tier region
never opens in sphere 1; `graces_per_region` 0/1/3 all still emit valid `regionGraces`. (Bake +
in-game grace verification is the human integration gate in BRIEF-PARALLEL-INDEX.md, not this task.)

**Contract:** none. Do NOT change slot_data keys or the version range — region fusion's contract is
frozen and the client consumes it as-is.
