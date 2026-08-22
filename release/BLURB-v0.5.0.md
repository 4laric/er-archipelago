# v0.5.0 — release blurb (draft)

_Draft, for a v0.5 integration branch — held until the ability-lock client build is validated._

You can take an ability away now. Roll, jump, either attack, guard — name it in `locked_abilities`
and the game simply will not do it, all run. It is not a keybind trick: the lock sits on the
character's own action layer, so rebinding does not dodge it, keyboard and mouse are covered the same
as a pad, and your menus are untouched. Lock roll and learn to space; lock jump and the world gets
taller; lock a hand and fight one-sided.

And then you can give them back. Set `ability_lock_mode: progressive` and every locked ability starts
off but turns into an item somewhere in the multiworld — your `Unlock: Roll` might be behind a boss,
or in a friend's game three worlds over. Find it, get it back. Nothing you need to finish is ever
locked behind one, so a run always ends; the abilities are the reward, not the gate.

## What you need to update

- **Client:** Required — a progressive seed needs a client that understands ability unlocks, and the
  version handshake moves to 0.5.0. A 0.4.x client still plays a 0.4.x seed.
- **APWorld:** Required to generate 0.5.0 seeds.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** `locked_abilities` and `ability_lock_mode` are new and default off.
  every existing YAML stays valid.
- **Existing seed/save:** Compatible — a seed that sets neither option plays exactly as before.
- **Profile/assets:** No action.

## What is in it

- **Ability lock (#945)** — `locked_abilities` (jump/crouch/roll/r1/r2/l1/l2), disabled at the logical
  action layer; keybind- and device-agnostic, menu-safe.
- **Progressive ability lock (#980)** — `ability_lock_mode: progressive` turns the locked set into
  findable `Unlock: X` items; reconnect-safe, never logic-required.

## Notes

`v0.5` is an integration branch: it does not ship to `main` yet, and `stable` stays on the 0.4.x
line until the ability-lock client build is confirmed in play. `CONTRACT_HASH` moved to `13db0b3a`
(the new `abilityUnlockItems` key); client half is v0.5 `d4f23eb`.
