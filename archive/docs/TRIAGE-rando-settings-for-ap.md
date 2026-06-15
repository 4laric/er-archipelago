# Triage: wiring randomizer settings into the AP YAML

Goal: of the GUI settings bypassed under AP (see REFERENCE-er-randomizer-gui-under-ap.md),
which are worth wiring into apworld YAML, sorted by effort vs value.

## The constraint that shapes everything

The buildable source (SoulsRandomizers/EldenRingRandomizer) is **behind the v0.11.4 GUI in
the screenshots**. Many eye-catching options exist only in upstream, NOT in the source you
compile: "spawn night bosses at all hours", "ignore arena size", "enemy colors", "Mountaintop
shortcuts", "guaranteed drop copies", "DLC max-upgrade", "horse blinders", "Aging Touchables",
"spiritspring seals", "starting keepsakes". Those can't be "wired" — they must be **ported
from upstream first**, which runs into the thefifthmatt fork-licensing concern
([[er-ecosystem-upstreams]]). Treat porting as a separate, heavier decision.

So the real triage splits three ways:

- **Tier A — flag exists in your source, just unset in AP.** Cheapest possible: add a YAML
  option, pass it in slot_data, set one `opt[...]` line in `ConvertRandomizerOptions`
  (ArchipelagoForm.cs ER case). Regen only.
- **Tier B — apworld-logic only, no randomizer change.** Add a YAML option + rules in
  `__init__.py`. Independent of the version lag. Clean.
- **Tier C — feature not in your source.** Requires an upstream port (effort + licensing)
  before any wiring. Park unless the value justifies the merge.

---

## Tier A — cheap flag wires — IMPLEMENTED 2026-06-13

Shipped four options. Each adds a YAML `Toggle`, a real-bool slot_data entry (so it survives
the static randomizer's bool-only options filter, like `no_weapon_requirements`), and one
`opt[...]` line in `ConvertRandomizerOptions` (ArchipelagoForm.cs ER case). Regen required.

| YAML option | opt key | Consumed at | Gated on enemy rando? | Value |
|---|---|---|---|---|
| `swap_multiboss` | `swapboss` | EnemyRandomizer.cs:1165 | yes | **Med** — variety in mini-dungeon multi-boss arenas. |
| `boss_runes_match` | `swaprewards` | EnemyRandomizer.cs:893, 8122 | yes | **Low** — relocated boss drops the original spot's runes. |
| `impolite_enemies` | `impolite` | EnemyRandomizer.cs:2930 | yes | **Low-med** — enemies aggro more readily in groups. |
| `disable_serpent_hunter_upgrade` | `nerfsh` | CharacterWriter.cs:381 | **no** (standalone bake edit) | **Low** — niche balance. |

**DROPPED — `night` ("Include night-only bosses"):** on inspection it's consumed only on the
racemode/item-placement side (AnnotationData.cs:397 -> `NoRaceModeTags`,
PermutationWriter.cs:634 -> item filter tags). The enemy pass picks night bosses by
`EnemyClass.NightMiniboss` directly, not via this option. Under AP the item side is bypassed,
so wiring `night` would be **inert** — not a real night-boss win. The actual night-boss
feature you want ("spawn at all hours") remains Tier C (EMEVD, not in source).

Also skipped: `invertgestures` / `invertenvbgm` (no opt consumption found — inert);
`default_custom` / custom enemy placement (preset-driven, not a simple bool).

---

## Tier B — apworld-logic wins (no randomizer dependency)

Version lag doesn't touch these; they live entirely in the apworld. Higher value per unit
effort than most of Tier A, just more than one line.

| Setting | What's needed | Value |
|---|---|---|
| Configurable Great Runes for **final boss** and **Mountaintops** | Extend the `great_runes_required` pattern (already gates Leyndell) to the other two thresholds the GUI exposes. Pure logic + slot_data. | **Med-high** — real difficulty/pacing control. |
| Early Mohgwyn Palace | Mirror `early_legacy_dungeons`: force the Pureblood Knight's Medal early. Small logic add. | **Med** |
| Deathless routing | Exclude the Volcano Manor abduction from logic (option text already describes it). Logic-only. | **Low-med** |
| Finish `region_bosses` / `region_lock_bosses` | Already specced separately — see SPEC-region-boss-gating.md. Biggest of these. | **High** (but largest scope) |

---

## Tier C — high value, but needs an upstream port first

Not in your source; each requires lifting the feature from upstream v0.11.4 (licensing
caveat) before it can be wired. Listed by value.

| Setting | Value | Why it's expensive |
|---|---|---|
| **Spawn night bosses at all hours** | **High** (you've asked for it) | Not an `opt[]` in your source; it's an EMEVD time-gate removal. Port + event work, not a flag flip. |
| Ignore arena size for boss placement | **Med-high** | Enables many more boss-into-arena placements (big variety win for enemy rando). Upstream-only. |
| Aging Touchables / Abyssal horse blinders | **Med** | DLC combat QoL. Upstream-only. |
| Enemy colors / Mountaintop shortcuts / guaranteed drop copies / DLC max-upgrade / keepsakes | **Low** | Cosmetic or minor QoL. Not worth a port on their own. |

If several Tier C items matter, the efficient move is one deliberate **rebase/merge of the
randomizer fork onto current upstream**, then wire them as Tier A — but that's the
licensing-sensitive decision flagged above, not a per-option task.

---

## Recommendation

1. Do **Tier A** as a single small PR (5 enemy sub-toggles, one regen). Immediate, low risk.
2. Pick off **Tier B** by value: Great Rune thresholds first, then early Mohgwyn / deathless.
3. Decide separately whether the **upstream rebase** is worth it; if yes, it unlocks all of
   Tier C (including "night bosses at all hours") at Tier-A cost. If no, park Tier C.

## Wiring recipe (Tier A, for reference)

1. `options.py`: add a `Toggle` per setting; include in the dataclass + an option group.
2. `__init__.py` `fill_slot_data`: add to `slot_data["options"]`.
3. `ArchipelagoForm.cs` ER case in `ConvertRandomizerOptions`: inside the
   `randomize_enemies` block, `opt["<key>"] = 