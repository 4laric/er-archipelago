# Grace Gates — Rust client spec

The apworld now hard-gates two folded sub-areas' **graces** so the player can't warp in before holding
the key item. This is the client half of `legacy_key_gates` / `leyndell_gate` (previously logic-only).
Apworld side: `greenfield/eldenring_gf/features/graces.py` + contract keys in `contract.py`. This doc is
the `eldenring-archipelago` (region.rs) work needed to consume it. Land it on `eldenring-client-draft`.

## Background

`regionGraces` maps an **item** to grace warp flags that light **when that item is received**. Region
Locks are items, so today the client lights a region's whole grace bundle on receipt of its
`"<Region> Lock"`. Raya Lucaria Academy (m14) is folded into Liurnia and Leyndell (m11) into Altus, so
one region Lock currently lights sub-area graces that vanilla gates behind the Academy Glintstone Key /
2 Great Runes — letting the player warp straight in. The gates move those graces off the region Lock.

## Contract changes (already emitted by the apworld)

1. **`regionGraces` — now keyed by ANY item, not only `"<Region> Lock"`.**
   The Raya graces (flags `714xx`) are pulled from `"Liurnia of the Lakes Lock"` and re-keyed under
   `"Academy Glintstone Key"`. Shape is unchanged (`{string: [u32]}`, `str_to_u32vec`).
   - **Client change:** light a `regionGraces` entry's flags on receipt of the **keyed item by name**,
     whether or not the name ends in `" Lock"`. If the current handler already resolves the key to a
     received-item event generically, **no change is needed** — verify it doesn't special-case Locks.

2. **`runeGatedGraces` (NEW) — `{ "N": [u32 grace flags] }`** (LISTVAL_INT_MAP / `str_to_u32vec`).
   Light the flags once the player has **received at least `N` Great Runes**. Only the `N=2` (Leyndell)
   entry is emitted today, and only when `leyndell_runes_required > 0`; the key is absent otherwise.

3. **`greatRuneItemIds` (NEW) — `[i64 FullIDs]`** (INT_LIST / `arr_i32`).
   The set of Great Rune item FullIDs to count `runeGatedGraces` against. Emitted only alongside
   `runeGatedGraces`.

## Client behavior to implement (region.rs)

- On item receipt, in addition to the existing `regionGraces` lookup, maintain a **count of received
  items whose FullID is in `greatRuneItemIds`** (count distinct runes; each Great Rune is unique, so a
  simple received-set intersection size is correct).
- Whenever that count changes, for each `(n_str, flags)` in `runeGatedGraces`: if `received_runes >=
  n_str.parse::<u32>()`, set `flags` (idempotent — same as lighting a grace bundle). Re-evaluate on
  every rune receipt so a late rune lights the graces retroactively; also evaluate once on (re)connect
  so a reconnecting client with the runes already in hand lights them.
- No new suppression/kick logic here — this is purely which graces light. The matching in-game
  hard-kick out of m14 / m11 until the key/runes are held is a separate follow-up (region kick-watch),
  not required for the grace gate.

## Winnability / safety

Region Locks remain the only progression; the apworld's `legacy_key_gates` / `leyndell_gate` already
keep AP fill from stranding a Lock behind the key/runes. If the client ships **before** this change,
the gated graces simply never light (the player walks in with the key instead of warping) — no
soft-lock. After this change, they light exactly on key / Nth-rune receipt.

## Test hooks (apworld side, already green)

`tests/test_gf_grace_gates.py`: gates armed → Raya graces off the Liurnia bundle and under
`"Academy Glintstone Key"`; Leyndell graces off the Altus bundle and in `runeGatedGraces["2"]` with
`greatRuneItemIds` populated; `71190` (Roundtable/HUB grace) stays in the Altus bundle. Gates off →
bundles unchanged, neither new key emitted.
