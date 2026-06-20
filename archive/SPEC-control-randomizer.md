# SPEC: Control Randomizer ("the Skumnut special")

Status: DRAFT 2026-06-19. A wacky challenge layer where the player's CONTROL SCHEME is the item pool:
you start gimped and receive capabilities as AP items. Lives almost entirely in the runtime client
(C++ input/action hooks); the apworld just mints the items + handles the (small) jump logic. Built
for a specific run (Skumnut), so default-OFF and ideally LOCAL to that slot.

## Scope (locked with Alaric)

IN, v1 (all start LOCKED, item RESTORES the capability):
- **Look Left / Free Camera** ("ZOOLANDER MODE" -- you are not an ambiturner) -- default: right-stick rotates the camera ONE direction only (clamp
  rstick-X to >= 0). To look left you orbit all the way around. Receiving the item frees the camera.
- **Dodge Roll** -- default: the roll/dodge is suppressed (sprint/backstep/walk still work). Receiving
  it restores rolling.
- **Torrent Double Jump** -- default: Torrent's mid-air SECOND jump is suppressed (ground jump + first
  mount jump + spiritsprings all still work). Receiving it restores the double jump.

IN, v2 (opt-in, has real logic):
- **Jump** (on-foot) -- default: player jump suppressed. Gates the curated JUMP_REQUIRED_LOCATIONS.

OUT (considered, cut): progressive movement chain; per-shoulder R1/R2/L1/L2 gating; crouch. Easy to
add later -- they're the same input-mask primitive.

## Logic classification (the important part)

- Look Left, Dodge Roll: **NON-LOGICAL**. You can reach every check in ER without rolling or looking
  left. Pure client gates; the items gate nothing in the fill.
- Torrent Double Jump: **tiny exclude-list**. Mainline verticality is single mount-jump + spiritsprings;
  the double jump only reaches a few optional high ledges. So a curated DOUBLE_JUMP_LOCATIONS set is
  either excluded from holding progression OR gated behind the Torrent Double Jump item. Start by hand;
  grow if a gen strands a check.
- Jump (v2): **curated JUMP_REQUIRED_LOCATIONS**, gated behind the Jump item. Jump almost never gates
  region-to-region mainline (overworld = Torrent, dungeons = walk/ladder) -- the dependency is item
  PICKUPS on ledges/gaps. So DON'T audit 2000 locations: tag the known jump-only pickups, grow the set
  through playtest/gen failures (same pattern as the curation cut-lists). HARD REQUIREMENT: verify no
  goal-critical location needs on-foot jump (expected true) so worst case is a side pickup waiting,
  never an unwinnable seed. Jump must not be placed behind a JUMP_REQUIRED_LOCATIONS check (falls out
  once those carry the rule).

## Client subsystem (the real work)

The client has NO game-input hook today (its only "input" is the stdin console reader). New subsystem:

**Per-frame input mask.** Hook ER's pad/input read (the manipulator that fills the player's button +
analog state each frame) and, for each still-locked capability, AND-out the bit / clamp the axis --
BUT only while the player has gameplay control.

**THE load-bearing piece: the gameplay-vs-menu guard.** Masking buttons globally bricks menu/UI nav
(R1/confirm/etc.). Every mask must gate on "player is in gameplay, not a menu/cutscene/load". Get this
one predicate right once (WorldChrMan player loaded + no menu/modal open + not in cutscene) and every
gate reuses it. This is the first thing to nail.

### Per-gate mechanism + RE target
- **Look Left / Free Camera (Zoolander Mode)** -- EASIEST, ship first as the prove-the-hook prototype. Clamp the
  right-stick X-axis to >= 0 in the input state when locked. Menu impact ~nil (right-stick rarely
  critical in menus), but still gate on gameplay for cleanliness. RE: the analog-stick fields in the
  pad/input struct.
- **Dodge Roll** -- the dodge button is SHARED (roll/backstep/sprint/jump are one button discriminated
  by context/hold), so a raw button mask kills sprint too. Gate at the ACTION level: suppress the roll
  behavior trigger when locked (block the roll EzState/behavior request, leave sprint/backstep). RE:
  the player roll/dodge action dispatch (TAE/behavior request).
- **Torrent Double Jump** -- suppress the SECOND jump while mounted + airborne, only. RE: the mounted
  jump action + the air-jump counter / mount air-state (distinct from ground jump and first mount jump).

**Item -> unlock wiring.** Mirror the existing receivedItemNames path (Core.h already tracks received
item names). On receipt of a control item, flip its live "unlocked" bool; the mask consults those bools
each frame. Default (no item) = locked.

## apworld side

- Items: "Look Left", "Dodge Roll", "Torrent Double Jump", "Jump" (GOODS-ish sentinel items the client
  recognizes by name, like the lock items; not real EquipParamGoods). Emitted only when their option is on.
- Options (toggles, default off): `no_dodge_roll`, `camera_right_only`, `no_torrent_double_jump`,
  `jump_randomized`. Each adds its item to the pool; jump_randomized also installs the location rules.
- Make them **local_items** for the Skumnut slot so they never burden other players' worlds.
- Logic: jump_randomized -> `_add_location_rule(loc, "Jump")` over JUMP_REQUIRED_LOCATIONS;
  no_torrent_double_jump -> DOUBLE_JUMP_LOCATIONS excluded-or-gated. Both lists start small in a new
  data module (control_logic.py), grow via playtest.
- slot_data: emit which control items are active so the client knows what to mask at load (a fresh
  save starts fully locked for the active set).

## Build order

1. **Prototype: Look Left** end-to-end (input hook + gameplay guard + item-unlock). Proves the whole
   subsystem on the lowest-risk gate. If the input hook + menu guard work here, the rest is variations.
2. Dodge Roll + Torrent Double Jump (action-level hooks) + the double-jump exclude-list.
3. v2: jump_randomized -- Jump item + JUMP_REQUIRED_LOCATIONS scaffold; gen-test for stranded checks,
   grow the list; confirm goal path never needs jump.

## Risks / notes

- Offline only (ER AP is offline; no anti-cheat concern with input hooking).
- Toggling a mask mid-roll / mid-air must not wedge the player (apply at input read, not by forcing
  animation state).
- Menu guard is the single biggest correctness risk -- prototype it hard.
- Softlock: only Jump has real softlock potential; the curated-list + no-goal-critical-jump rule
  contains it. Roll/camera/double-jump cannot softlock (non-logical / tiny exclude-list).
- These are a personal-gimp challenge layer; keep them local + default-off so normal/multi seeds are
  untouched.
