# Tarnished Edition patch day (2026-08-28) — the runbook

The world-repo half of #241. The CLIENT half — the version gate, the `fromsoftware-rs` RVA pin, the
Discord gap message — lives in `from-software-archipelago-clients/RELEASE-CONTINGENCY-TARNISHED.md`
and is not repeated here. Read both.

The point of this file is that the post-patch work should be **mechanical**, not investigative. Every
step below that could be done before the pack shipped **has been**, and its result is recorded here as
a "before" so the "after" is a diff rather than a fresh datamine.

---

## 1. The pre-patch baseline (recorded 2026-08-24, BEFORE the pack)

The 08-04 finding on #241 was that checkbox 1 — "record the new `eldenring.exe` version" — had **no
old value to compare against**. This closes the param half of that gap. The `.exe` half still needs a
Windows box and is listed in §4.

| fact | value |
|---|---|
| `gen_inputs.db` sha256 | `b200647169aac9bf7e91e8a92fb767a4903e9f1902b521ad6fa7c54204eef2d1` |
| last commit to touch it | `00903b211389aabfe51e99492ef26ea0348c5312` (2026-08-07) |
| param tables in the bundle | 239 |
| param-corpus digest | `382d0f25d9345461ed0d5e909416f11f5c2bc20b90cc0311b4854ff132e4ddbc` |
| total CSV lines across all 239 | 179 766 |
| `SpEffectParam` | 11 325 rows x 373 cols |
| `EquipParamProtector` | 820 rows x 253 cols |
| `EquipParamGoods` | 2 326 rows x 122 cols |
| `CharaInitParam` | 3 240 rows x 119 cols |

The corpus digest is `sha256` over `path || sha256(decompressed csv)` for each of the 239
`vanilla_er/vanilla_er/*.csv` blobs, in path order. Reproduce it with:

```bash
python3 - <<'PY'
import sqlite3, zlib, hashlib
db = sqlite3.connect("gen_inputs.db")
h = hashlib.sha256()
for (p,) in db.execute("SELECT path FROM files WHERE path LIKE 'vanilla_er/vanilla_er/%.csv' ORDER BY path"):
    b = db.execute("SELECT blob FROM files WHERE path=?", (p,)).fetchone()[0]
    h.update(p.encode()); h.update(hashlib.sha256(zlib.decompress(b)).digest())
print(h.hexdigest())
PY
```

The four row/column counts are the ones that matter on patch day and why:

* **`EquipParamProtector`** — the four new armor sets land here. The added row ids are what you feed
  the catalog lookup in §3 step 5.
* **`CharaInitParam`** — the two new starting classes land here. Not catalog items, so they need no
  pool exclusion; they DO intersect the start-grant work.
* **`SpEffectParam`** — new armor brings new SpEffect references, which is the whole silent-failure
  risk (§2).
* **column counts** — a changed header invalidates every ordinal/offset assumption downstream.
  `tools/diff_gen_inputs.py` calls this out explicitly (`COLUMN LAYOUT CHANGED`).

## 2. Re-verified against the CURRENT (pre-patch) dump, 2026-08-24

All four repurposed rows in `er-logic/src/safe_speffect_rows.rs::CLAIMED` re-verified clean against
`gen_inputs.db` at the sha above, via `python tools/verify_safe_speffect_row.py 20012080 20010827
20012081 20012082`:

| row | owner | verdict |
|---|---|---|
| 20012080 | `no_equip_load` | no-op, silent, permanent; occurs exactly once across all 239 tables |
| 20010827 | `no_fall_damage` | same |
| 20012081 | `scadu_blessing` | same |
| 20012082 | `traps::no_flask` | same |

That is the "before" the post-patch run is compared against: **the same command on the new dump must
print the same four verdicts.** Anything else and the row is no longer spare — claim a different one,
do not relax the criteria.

🛑 **20012082 was NOT in the #241 checklist command, and was NOT in the watch list.** It was claimed
2026-08-10, two weeks after the tooling was written, and both the tool's `WATCHED` list and the test
that was supposed to prevent exactly this drift carried a hand-typed copy of the OTHER three. Fixed
2026-08-24: the drift test now parses `CLAIMED` out of the registry when the client submodule is
checked out (it is, in the tests job), so a fifth claimed row cannot outrun the guard the way the
fourth did. The lesson generalises — **a hand-copied list cannot guard a hand-copied list.**

## 3. The patch-day sequence (in order; nothing here is investigative)

1. **Freeze the reference build name.** Record in #241 and in the next release notes which release
   was current at the moment of the patch ("the pre-Tarnished reference is v0.4.x at SHA ..."). From
   that morning on, a bug report without a game version is unanswerable. `release/CHANNELS.tsv`'s
   `stable` row names it; nothing to compute.
2. **Settle the entitlement assumption from the depot list, not the patch notes.** SteamDB shows
   which depots the build touched within minutes. **1245621** (ELDEN RING Content) is the base-game
   depot every owner has. If it changed, every PC install's regulation changed and the rest of this
   list is mandatory; if only a new DLC depot appeared, the work collapses to step 5 alone.
3. **Fresh 239-param dump on Windows** (Smithbox), recompile `gen_inputs.db` (`tools/gen_inputs.py`).
   🛑 The sandbox cannot do this half: sandbox regen works OFF `gen_inputs.db`, so it is meaningless
   until the DB is re-dumped from the patched game.
4. **Run the two instruments.** Both are read-only and take seconds:
   ```bash
   git show 00903b21:gen_inputs.db > /tmp/old_gen_inputs.db
   python tools/diff_gen_inputs.py /tmp/old_gen_inputs.db gen_inputs.db
   python tools/verify_safe_speffect_row.py 20012080 20010827 20012081 20012082
   ```
   `diff_gen_inputs.py` exits 1 **only** when a watched id gains a reference — the silent-failure
   case. New rows elsewhere are informational and exit 0, so patch day does not end in a red gate
   nobody can act on.
5. **Paste the new item names into the exclusion hook.** After regen, put the new armor (and any new
   goods) catalog names — exactly as they appear in `ITEM_CATALOG` — into
   `greenfield/eldenring/tarnished_pack.py :: TARNISHED_PACK_ITEM_NAMES`. That set publishes into
   `gf_dlc_excluded`, which every pool-augmentation path already reads, so no other wiring exists to
   forget. The hook shipped empty in #970 and a mutation test already proves a planted name is
   excluded under DLC on and off. Starting classes and Torrent skins are not catalog items.

   🛑 **The name must be spelled the way ITEM_CATALOG spells it, and that is now enforced.** A
   guessed or mistyped name is accepted by every set operation in the pool paths and excludes
   NOTHING -- the pack item stays placeable, and nothing goes red. `test_gf_tarnished_pack_wiring.py
   :: test_every_pack_name_is_a_real_catalog_name` asserts membership, so the paste is witnessed.
   This REPLACED `test_empty_until_patch_day`, which hard-asserted the set was empty and would have
   turned this very step into a red suite -- an expiring ratchet nothing in this runbook warned
   about. Do the paste AFTER the regen in step 6's order, or the catalog it checks against is the
   pre-patch one.
6. **Regen**, in the normal order — the stamp is LAST. Expect `inputs_hash` to move; that IS the
   signal that seeds built before and after the patch are not comparable.
7. **Client offsets** — hand off to
   `from-software-archipelago-clients/RELEASE-CONTINGENCY-TARNISHED.md`. The bottleneck is upstream's
   RVA table, not us, and the pin bump is a release decision, never a feature PR.

## 4. Still gated on the pack drop — nothing here can be pulled forward

* The **patch notes / depot reading** (step 2). The entitlement question — does `regulation.bin`
  change for players who do NOT buy the pack — is **not settleable from the public record**; the
  storefront FAQ and every "it's paid DLC" headline answer a different question (see #241, 08-04).
* The **fresh Windows param dump** (step 3). Needs the patched game installed.
* Therefore both instruments in step 4: they need the new bundle as their right-hand side.
* The **item names** (step 5). They do not exist until the regulation ships.
* The **`eldenring.exe` PE `ProductName`**, as well as the version. The client's gate rejects on
  product name too, and that arm's message reads "this is not Elden Ring / check the mod is
  installed against Elden Ring" -- actively misleading advice if the Tarnished Edition executable
  ships a changed product string. Record what the new exe reports; if it is not `elden ring`, the
  gate's `Rejection::Product` wording (`er-logic/src/game_version.rs`) needs a Tarnished arm, not
  just a new version constant.
* The **`eldenring.exe` file version**, old and new. Nothing in this repo has ever recorded one, and
  the sandbox has no game install. 🛑 If a Windows box is available before the 28th, record the
  current exe's file version here — five minutes now, an investigation later.
* The **upstream RVA table** for the new executable, and the live smoke test that is the only real
  proof the addresses are right.

## 5. Known blind spot in the instrument

`diff_gen_inputs.py` cannot watch the **base-game** scaling ladder/band
(`er_logic::scaling::SCALING_ID_RANGE = 7000..8000`). The watched-id scan tokenises integers and
tests membership, so four-digit ids collide with ordinary cell VALUES in every one of the 239 tables;
a watch entry there would fire on essentially every patch and train the reader to ignore the guard.
Those rows are covered by the informational row diff instead — on patch day run
`python tools/diff_gen_inputs.py old.db gen_inputs.db --only SpEffectParam` and read the changed-row
list for anything in `7000..7999` by eye. The DLC block (`20007000..20007750`, ladder AND band) has
no such collision problem and IS watched.
