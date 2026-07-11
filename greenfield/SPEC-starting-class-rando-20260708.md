# SPEC — Starting Class Randomization (greenfield) — 2026-07-08

Status: DRAFT / design only. No implementation yet (Alaric hold). Author target: greenfield apworld
option + slot_data contract key + Rust client (`eldenring-archipelago`) apply-on-connect.

## 1. Problem / intent

Let a seed randomize the player's **starting build** — the stat spread and starting equipment that a
vanilla ER class defines — instead of the player getting whatever class they picked at character
creation. "Randomize starting class" = the run begins as a seed-chosen class (or, v2, a synthetic
build), independent of the player's menu choice.

## 2. Goals / non-goals

Goals:
- Seed-deterministic: same seed (+ same slot) → same starting class, for consistency and racing.
- AP-clean: works within the normal AP flow (create character → load in → connect), with no
  pre-connection configuration required from the player.
- Logic-safe: cannot strand progression. In greenfield, progression is region locks, not gear/stats,
  so a start build swap is logically inert — the client can own it end to end without the generator
  reasoning about starting gear (documented invariant, see §7).
- Reuse existing client machinery (start-grant path, start-clobber gating, live inventory/stat write).

Non-goals (this rev):
- Fully synthetic classes (random stat spreads / gear that match no vanilla class) — deferred to v2 §9.
- Making starting gear/stats a logic input (would require generator-side reasoning; out of scope while
  greenfield logic is region-lock only).
- Randomizing the *keepsake* / starting gesture (cosmetic; can piggyback later).

## 3. The core constraint (why this shapes the design)

`CharaInitParam` — the param that defines each class's starting stats + equipment + items — is read
**only at the character-creation screen**, which happens **before** the client connects to AP. At that
moment there is no slot_data and no seed. So a seed-derived class **cannot** be baked into
`CharaInitParam` at creation time. This rules out the "obvious" mini-baker-on-CharaInitParam approach
as the primary mechanism (it can only be driven by a locally-known seed; see §8-A).

Therefore the chosen design applies the class **after connect, to the already-created live
character** — a respec — rather than at creation.

## 4. Chosen design (B): on-connect "force into rolled class"

### 4.1 apworld (greenfield)
- New feature `features/starting_class.py` with an option `starting_class`:
  - `off` (default) — no change.
  - `random` — generator rolls one of the 10 vanilla classes from the seed.
  - `<named class>` — force a specific class (Vagabond … Wretch), useful for testing/plando.
- Emits ONE slot_data contract key, e.g. `startingClass` (int: 0 = off, else the chosen
  `CharaInitParam` class row id or a 1..10 enum the client maps). Follow contract.py single-source
  conventions; add to the `(BOTH,)` profile if the Bedrock client should also honor it, else GREENFIELD.
- No location/item pool impact. No `create_items` / fill involvement. Pure slot_data.

### 4.2 client (`eldenring-archipelago`)
Apply once, on the first connect to a **fresh save**, gated exactly like the existing start grants:
- Trigger gate: reuse the start-clobber guard (`real_pickup_seen() || in_world >= 8s`) so the write
  never fires during the load screen (mirrors the Torch fix, memory `gf-start-item-clobber`).
- Idempotency latch: a save-persisted "starting class applied" flag (one event flag, or a SaveState
  field like the flag-poll baseline) so a reconnect / relog does NOT re-apply (would clobber a build
  the player has since leveled). Mirror the reconnect-persist pattern already used for start items and
  the flag-poll baseline.
- Steps on apply, using the rolled class's vanilla `CharaInitParam` row as the TEMPLATE (read live from
  `SoloParamRepository`, the same primitive minibaker.rs / no_weapon_reqs.rs use):
  1. Read template row fields: base attribute block (vig/mnd/end/str/dex/int/fth/arc + starting level),
     starting weapons/armor/talisman ids, starting goods.
  2. Write the live character's attribute block to the template values (player stat write; confirm the
     typed path — `scaling.rs` / player game-data access already reads stats).
  3. Swap starting gear: grant the template's starting items (existing `grant_full_id` path) and REMOVE
     the picked class's starting kit. Removal is the fiddly part (need the picked class's row too, diff
     the two, remove what the roll doesn't include). See open question §6.

### 4.3 contract / tracker
- `startingClass` is slot_data only; not a location, not big-ticket, no tracker surface. Register the
  key in contract.py; regenerate contract_gen.rs. Client validates on connect (shape: int).

## 5. Determinism

The class is rolled generator-side from the AP seed and shipped in slot_data, so it is fully
deterministic and identical for every observer of the seed. The client applies verbatim — no client
RNG. (This is the key advantage over a char-create local scramble, §8-A.)

## 6. Open questions / risks

- **Gear removal**: cleanest is to diff the picked class's `CharaInitParam` starting-items against the
  rolled class's and remove the delta, then grant the rolled delta. Need to confirm the client can read
  which class the player picked (their initial loadout / the CharaInitParam id used at creation) — if
  not readable, fall back to "grant rolled kit, leave picked kit" (additive; less clean but safe).
- **Level coherence**: writing the attribute block changes the character level. Setting the whole block
  to a real vanilla class's values keeps it coherent (a legit class state). Avoid partial writes.
- **Visible respec**: the player sees their picked class for a beat before the swap. Cosmetic; document.
- **Stat-write safety**: writing attributes mid-frame — gate to in-world + game thread (same SAFETY
  contract as minibaker.rs writes). Verify no NG+/co-op interaction.
- **Interaction with auto_upgrade / start items**: order of application vs the existing start grants;
  apply class first, then start-inventory grants, so nothing is double-removed.

## 7. Logic-safety invariant (greenfield)

Progression = region Locks + required Great Runes, filled generator-side. Starting stats/gear are NOT
logic inputs. Therefore the class swap cannot make a seed unbeatable, and the generator need not model
it. If a future mode makes starting gear a logic gate, this invariant must be revisited (the option
would then need generator-side reachability reasoning).

## 8. Alternatives considered

- **(A) Char-create bake via mini-baker on `CharaInitParam`** — rewrite the 10 class rows at the
  creation screen. Mechanically valid (CharaInitParam is in `SoloParamRepository`; the client already
  bulk-rewrites sibling params), but there is **no seed at creation**, so it can only be driven by a
  locally-configured seed or a non-deterministic local scramble → breaks multiworld determinism and
  adds per-seed player config. Rejected as primary; retained as the vehicle for v2 synthetic classes.
- **(C) start_inventory only** — grant a random loadout as items, ignore stats. Simple (pure
  startgrant), but doesn't change the stat spread, so it isn't really "class" rando. Could ship as a
  lighter "starting gear rando" sub-option.

## 9. v2 — synthetic classes (future)

Once (B) is solid, mini-baker CAN rewrite `CharaInitParam` rows to synthetic builds (random stat
spreads, cross-class gear) — but still constrained by the char-create timing. Path: bake the synthetic
rows from a seed the client knows pre-connection (e.g. a value the player pastes into client config
alongside the server/slot), OR intercept creation via a detour and force the class just-in-time. Both
are heavier; only pursue if vanilla-class rando proves popular.

## 10. Testing plan

- apworld: unit test the option surface + slot_data emission (off/random/named); a gen_sweep to
  confirm `random` is stable per seed and a named value pins. No fill/beatability change expected —
  add a guard that the location/item pool is byte-identical with the option on vs off.
- client: pure `er-logic` replay tests for the apply-once latch (fresh-save applies; reconnect does
  NOT re-apply; relog after leveling is a no-op) — mirror the flag-poll baseline / start-grant replay
  suites. Live stat/gear write verified in-game (Alaric), not in CI.

## 11. Not doing yet

Per Alaric 2026-07-08: spec only, hold implementation.
