# v0.6.4 — Mario move randomization, experimentally

Mario can now collect his moves through Elden Ring Archipelago. Two Progressive
Jumps restore Double Jump then Triple Jump; Backflip, Side Flip, Long Jump, Wall
Kick, Dive, Ground Pound, Enemy Grab and Boss Swing unlock independently. Basic
movement and combat stay available, and these moves add no traversal or goal gates.

## Can I update the client during a run?

Existing non-Mario seed contracts and save formats are unchanged. Use the paired
release client and APWorld for new Mario seeds. Older Mario seeds retain their
original handshake, but replacing DLLs cannot add the newly reserved Law of
Regression to their pool: generate a new seed for that quest route.

## What you need to update

- **Client:** Required for new Mario seeds; use both paired DLLs.
- **APWorld:** Host-only update to generate new Mario seeds.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Mario Mode defaults off.
- **Existing seed/save:** Compatible for existing non-Mario seeds, with no save migration. Mario needs a new seed and its own separate save.
- **Profile/assets:** Reinstall or replace both paired DLLs through Mario's me3 setup and supply your own US SM64 ROM. Build combined icons locally; ROMs and generated game assets are not included.

The optional companion `ER-Mario-AP-v0.6.4.zip` supplies the compatible Mario DLL,
profiles, setup documentation, license notices and a local atlas-composition
helper. It uses the matching AP client from the standard release bundle and
requires your own ROM and installed game. Ordinary AP profiles remain unchanged.

Unusable equipment and spell rewards become runes while pickup identities and
progression keys remain. Law of Regression is the exception: a seed with Royal
Leyndell reserves one progression copy. Carry it and press Interact at Radagon's
statue to trigger the native reveal, then complete Goldmask's dialogue for the
original gesture check. This does not require a staff, seal or advanced Mario move.

The paired DLLs coordinate overlay startup and AP keyboard/mouse capture. Moves
replay from received-item history. Move reset and save protection are separate:
after changing rooms, ordinary item delivery requires restarting with the proper
save/room identity; a capability reset does not clear that guard.

## What is verified, and what remains experimental

The human passed all nine move families, randomized pickups, both overlays,
keyboard capture, reconnect preservation, ordinary fast travel, death/respawn
recovery and initial new-seed relocking. Further slot/history replay, region
kicks, healing, combined icons, the statue/Goldmask route, required special bosses
and ending completion remain untested live. Mario mode remains experimental. Automated tests and builds are separate
evidence; they do not establish those remaining live behaviors.

See [the integration specification](../docs/SPEC-er-mario-integration.md) for the
setup and acceptance record. Unsupported DeathLink, TrapLink, No Flask traps,
auto-equip, native ability locks, vanilla placement and disabled item shuffle
reject before generation.

