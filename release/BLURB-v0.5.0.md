# v0.5.0 — release blurb

You can take an ability away now. Roll, jump, either attack, guard — name it in `locked_abilities`
and the game simply will not do it, all run. It is not a keybind trick: the lock sits on the
character's own action layer, so rebinding does not dodge it, keyboard and mouse are covered the same
as a pad, and your menus are untouched. Lock roll and learn to space; lock jump and the world gets
taller; lock a hand and fight one-sided. Heal is lockable too — it owns no action bit, so locking it
disables the flask instead, and the flask heals nothing until it comes back.

And then you can give them back. Set `ability_lock_mode: progressive` and every locked ability starts
off but turns into an item somewhere in the multiworld — your `Unlock: Roll` might be behind a boss,
or in a friend's game three worlds over. Find it, get it back. By default those unlocks are
goal-required, exactly like a required Great Rune: your abilities can land in a partner's world, and
you cannot finish until they send them home. That mutual dependency is the point of playing in an
Archipelago — set `ability_unlocks_required: false` if you'd rather the unlocks never gate
completion. Roll is forced to show up early either way (thanks bobler), so you're never dodgeless
for hours.

## What you need to update

- **Client:** Required — a progressive seed needs a client that understands ability unlocks, and the
  version handshake moves to 0.5.0. A 0.4.x client still plays a 0.4.x seed.
- **APWorld:** Required to generate 0.5.0 seeds.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** `locked_abilities` and
  `ability_lock_mode` are new and default off; every existing YAML stays valid.
- **Existing seed/save:** Compatible — a seed that sets neither option plays exactly as before.
- **Profile/assets:** No action.

## What else is in it

- **Co-op difficulty (#993)** — `coop_difficulty` adds enemy-scaling tiers per seamless co-op
  partner, so a duo isn't facing half the threat. Off by default; needs `enemy_scaling` on.
- **Remove merchant checks (#994)** — `shop_checks: false` takes all ~562 merchant purchase slots
  out of the check pool. Merchants still sell their vanilla wares.
- **Armor bundles are a YAML option (#986)** — `armor_bundles: false` restores the classic pool
  where every helm, chest, gauntlet and greave is its own item.
- **Leyndell's capital gate no longer fights itself (clients#409)** — the reconciler was clearing
  the two fog-wall flags every tick while the key-item backstop re-set them, holding the wall shut
  with two Great Runes received. Fixed.
- **Great Runes from boss drops arrive as-sent (clients#393)** — the restored-row rewrite that
  could leave a received rune inert is gone.
- **129 more checks pay retroactively from the corpse-award sweep (#984)** — `death_award_pairs`
  grows 179 → 308 pairs, and it works on existing seeds.
- **`!check <name>` (#1008)** — look up a check's flag by name and get a ready `!setflag` for
  anything that "didn't fire". GETTING-UNSTUCK grew matching walkthroughs (#1007).
- Two Dryleaf Dane sweeps re-keyed to the real defeat flags, 41 checks (#1015). Updater errors
  finally name the URL they tried (#978).

## Notes

`v0.5` was cut as an integration branch and merged to `main` on 08-24 once the ability-lock client
build checked out in play. `stable` stays on v0.4.13 until this window is tagged. `CONTRACT_HASH`
moved to `13db0b3a` (the new `abilityUnlockItems` key); an older client reports incompatible for a
progressive seed rather than silently leaving abilities locked. Client half is `3797563` on client
main, pinned by the gitlink.
