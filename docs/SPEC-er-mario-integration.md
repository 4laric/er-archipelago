# ER Mario capability integration

Status: experimental implementation; live compatibility has not been established.
Requested by Alaric on 2026-10-01; tracked in issue #1619.

## Scope

An Elden Ring Archipelago seed can opt into Mario's libsm64 movement and combat.
Basic walking, jumping, punching, kicking and stomping remain available. Ten
received items restore advanced moves: two Progressive Jumps, Backflip, Side Flip,
Long Jump, Wall Kick, Dive, Ground Pound, Enemy Grab and Boss Swing. Moves do not introduce traversal rules
or become requirements for the goal in this first implementation.

The integration targets the owned fork https://github.com/4laric/er-mario, based on
upstream commit `91fdec06ce6e817ae538d609d6819e08554a1b4a`. It does not patch
upstream releases or redistribute a ROM. The player supplies the US SM64 ROM
and uses Mario's separate offline save/profile. Elden Ring online play is outside
the supported launch configuration.

## Experimental setup

Use a fresh copy of upstream's ER Mario release folder and complete its ordinary
ROM setup first. Replace `er_mario.dll` with this fork's CI artifact. Keep the
Mario profile's savefile, packages and Mario native entry intact. Add the paired
AP client as an additional native in the same `er-mario.me3` profile:

```toml
[[natives]]
path = 'C:\path\to\AP\eldenring_archipelago.dll'
```

Generate a new seed with `mario_mode: true`, `auto_equip: false`,
`death_link: false`, `trap_link: false`, an empty `locked_abilities` set, item
shuffle on and vanilla placement off. Remove `no_flask` from the configured
traps. Do not use upstream's unpatched Mario DLL for a Mario seed. The AP client
must report applied mask acknowledgment before any check/delivery is accepted.
These are experimental setup steps, not a verified compatibility recipe.

Both paired DLLs serialize their complete graphics-hook construction and
application through `Local\ERArchipelagoHudhookInstall.v1`. Independently linked
MinHook registries can otherwise capture the same original prologue before either
hook is enabled, silently leaving only one overlay active. A native two-DLL
regression demonstrates the lost callback and its preservation with serialized
installation. Updating only one DLL cannot provide this coordination. The AP
renderer uses hudhook 0.9.3, matching Mario, and logs hook installation, render
initialization and its first frame separately. Capability acknowledgments log
the exact managed and unlocked masks when they change.

The local playtest server uses Archipelago 0.6.7's pinned `websockets==13.1`;
newer WebSocket server APIs are incompatible with this AP version. Verify a
connected slot before testing randomized rewards or vanilla suppression. Loading
both DLLs alone does not apply the seed's pickup rules.

Mario and AP both replace `menu/{hi,low}/01_common.tpf.dcx`. Build one combined
atlas from Mario's generated menu textures, using the game's sprite layouts as
a separate input, rather than loading two competing atlas overrides:

```powershell
python tools/build_ap_icon.py --menu '<Mario>\package\menu' --layout-menu '<local-layouts>\menu' --out '<combined>\menu' --witchy '<WitchyBND.exe>' --oodle '<Game>\oo2core_6_win64.dll'
```

The layout input supplies `hi/01_common.sblytbnd.dcx` and its `low` counterpart
from the player's installed game. The output only replaces AP icon 92 in
`SB_Icon_00`; Mario's icons in `SB_Icon_04` and all other textures are preserved.
Use those two combined atlas files in Mario's package and keep its other assets.
Regenerate the combined atlas if Mario rebuilds its assets. Generated atlases
remain local game data and must not be redistributed. The local candidate has
passed byte comparisons for both qualities; its in-game icons remain a live gate.

The local server also requires AP's pinned `jellyfish==1.2.1` for item-name
commands. A missing dependency causes `!getitem` to fail before sending a receipt.

## Wire and ownership

The optional `options.mario_mode` boolean selects the Mario adapter. The existing
optional `abilityUnlockItems` map carries AP item IDs to Mario capability names;
native ability locks and Mario mode cannot be combined. `requiresClientFeatures`
contains `mario_capabilities_v1` and `mario_regression_v1`. The existing top-level wire shapes and contract
hash remain unchanged; an older client refuses the new feature token.

| Bit | Wire name | Restored behavior |
| --- | --- | --- |
| 1 | progressive_jump (first copy) | Double Jump |
| 128 | progressive_jump (second copy) | Triple Jump |
| 256 | backflip | Backflip |
| 512 | side_flip | Side Flip |
| 2 | long_jump | Long jump |
| 4 | wall_kick | Wall kick |
| 8 | dive | Dive and slide attacks |
| 16 | ground_pound | Ground pound |
| 32 | enemy_grab | Regular enemy pickup and throw |
| 64 | boss_swing | Eligible staggered boss grab and swing |

Move names follow the existing Super Mario 64 APWorld. At upstream Archipelago
commit `0a601afbf575a4660077304a18ecb521ff1886c4`, `worlds/sm64ex/Items.py` defines
separate Double Jump and Triple Jump items, while `Options.py` excludes Double
Jump from the move-randomizer selection. A progressive jump item is this
integration's requested extension: first copy grants Double Jump, second grants
Triple Jump. Backflip and Side Flip remain independent. Kick, Climb and Ledge
Grab stay available in this initial ER adaptation to preserve baseline combat
and ordinary traversal. Enemy Grab and Boss Swing are ER Mario extensions.

The world owns item identities, option validation and pool construction. The AP
client owns received-item history and computes the complete unlocked set. The
Mario DLL owns input, movement, animation, combat and worker-thread execution.
Synthetic unlocks are consumed by the adapter, never delivered as game goods.
Neither player movement nor Mario's simulated state may be mutated by an AP
networking callback.

## ABI v1

Export names are unmangled C functions, using 32-bit unsigned masks:

```c
uint32_t er_mario_ap_abi_version(void); /* returns 1 */
uint32_t er_mario_ap_set_capabilities(uint32_t managed, uint32_t unlocked);
struct ErMarioApState {
    uint32_t abi_version;
    uint32_t flags;
    uint32_t managed;
    uint32_t unlocked;
};
uint32_t er_mario_ap_get_state(struct ErMarioApState *out);
```

Setter/query return 1 on acceptance/success, 0 on invalid arguments. Unknown mask
bits and unlocked bits outside managed are invalid. State flag bits: 1 means
assets/libsm64 ready; 2 means Mario enabled; 4 means the requested snapshot was
applied; 8 means the native statue interaction is supported. New seeds require
flag 8 through `mario_regression_v1`; older Mario seeds without that token retain
their existing handshake. The setter queues an atomic snapshot. The worker applies it before
libsm64 execution; the query exposes actual applied state. A successful setter
alone does not establish that a lock is enforced.

Without AP configuration, upstream Mario behavior remains available. An active
Mario seed requires compatible exports and observable application of its mask.
Transient disconnection retains the last seed's restriction. Reconnecting folds
the complete received history. Changing seed/slot replaces the capability state
and cannot inherit another slot's unlocks. This capability reset is separate from
the existing save-identity protection: switching rooms can reset moves while
ordinary item delivery remains refused by `RoomChangedMidSession`. Resume ordinary
play after a restart with the proper save/room identity; changing back in the same
process does not clear that guard.

## Enforcement

Filter requested SM64 actions before action initialization changes velocity.
Blocked advanced jumps use ordinary jump behavior; airborne attack fallback
must preserve safe freefall. Also govern alternate action entry paths and combat
effects. Natural slope sliding must remain possible while its locked attack
damage is suppressed. Menu navigation and game-forced actions must remain usable.

Regular enemy pickup and boss grab are separately gated in the Rust combat
adapter. Logging/readback must distinguish request acceptance, mask application,
and a blocked move. No new Elden Ring numeric flag/param IDs are invented.

Mario reads keyboard and mouse buttons through `GetAsyncKeyState`. The AP input blocker hooks this path as well: keyboard capture suppresses movement keys, mouse capture suppresses mouse buttons, and overlay modifiers keep their original state. Typing in the AP console must not move or attack with Mario.

## Rewards and compatibility

Weapon, armor and spell acquisition locations remain checks. Mario enforces his own
bare-fist/costume equipment, so unusable local equipment and spell rewards are replaced
without removing location identities or progression keys. Pool counts remain
exact. Keep Mario off by default. Unsupported option combinations must raise a
specific `OptionError` before fill.

Law of Regression is preserved as a quest key when Royal Leyndell is in the seed.
One progression copy uses the ordinary pool budget; extra copies become runes.
At Radagon's statue, press the normal Interact button while carrying the spell.
The Mario game thread applies native SpEffect 1673014 only within four metres of
entity 11000716 while the statue is waiting and unrevealed. The game performs the
statue reveal; the player must then tell Goldmask that Radagon is Marika to collect
Golden Order Totality. No advanced move, staff, seal or direct check award is used.
The original check 7774610 / f60848 requires Law and Royal Leyndell access, cannot
hold its own key, and retains the existing missable policy. When Royal Leyndell
is absent, the existing physical-route scoping omits that check without changing
its reserved dataset ID.

This quest route requires a newly generated seed and both updated DLLs. Existing
Mario seeds did not reserve Law of Regression; a DLL update cannot add it to their
pool retrospectively. Existing seeds remain playable under their old handshake.

Spells are identified through the existing item taxonomy, preserving key goods
and consumables that share their game item category. Mario combat currently removes percentages of target max HP. HP scaling therefore
does not increase hits-to-kill in the usual way; weapon upgrades and levels do
not increase Mario's ordinary attack strength. Coin, grace and boss-star healing
use SM64 health rather than ordinary flasks. Do not advertise damage upgrades,
cap powerups, normal healing locks, or DeathLink compatibility until implemented
and measured. Source: upstream `src/combat.rs`, `src/equip.rs`, `src/lib.rs`.

## Acceptance gates

Automated: parse malformed active configurations loudly; prove all nine unlock
identities and masks; replay reconnect/new-slot changes; test disabled action
families and alternate combat paths; prove count-neutral pool generation and
unchanged behavior with Mario off; sweep compatible/incompatible options; compile
both Windows DLLs and regenerate the contract mirrors.

Live game, required before release:

The human playtest has passed all nine move families and observed initial new-seed
relocking with basic movement available. Further slot/history replay, combined
icons and the statue/Goldmask quest path remain unverified live. The human ended
the manual session; the remaining checks below are future release gates.

1. Load both DLLs in one Mario me3 profile; verify input, camera and both overlays.
2. Collect a native pickup; prove the AP check and incoming reward complete once.
3. Attempt Long Jump while locked, receive its item, then prove it works. Repeat
   across death, save reload and reconnect; switch slots and prove it re-locks.
4. Repeat each move family, including alternate inputs, slope attacks, pickups,
   throws, and wall-kick velocity. Test a safe fallback near a ledge.
5. Warp by grace and by region kick. Prove Mario and Tarnished relocate together,
   and locked regions remain enforced after wall kicks/long jumps.
6. Verify real boss defeat/reward flags, required special encounters including
   Rykard, multi-phase fights, shops, NPC interaction and ending completion. Test
   the statue without Law, then with Law and Interact, and collect Goldmask's
   original gesture check through dialogue.
7. Verify health, healing, death, respawn and any supported traps against SM64
   health. Unsupported features remain rejected, not silently ineffective.
8. Exercise upstream unstuck behavior (F7 and automatic lift). It currently grants
   vertical movement independently of move unlocks; document or constrain it
   before making any move-based traversal guarantee.

Each live result records both commit SHAs, game version, profile/packages, seed
and date. A compiled build is not a live-tested build.

## Build validation

The private `game-build-ci` runner currently allowlists Linux Bloodborne/Pikmin
jobs and cannot validate these Windows DLLs. AP client Windows CI is used for
the client; the Mario fork has a dedicated Windows workflow. It checks out
`vswarte/fromsoftware-rs` at `59fbd3b3b7daaf14aca47c9f73530493dba6bc79`, imports
public model source, compiles libsm64 with clang-cl and archives the DLL. No ROM
or game assets are needed for compilation. No installer/release artifact is
declared playable before the live acceptance gates above pass.
