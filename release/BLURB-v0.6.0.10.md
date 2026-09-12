# v0.6.0.10 — release blurb (draft)

Scadutree Avatar's sweep checks should complete when the final boss dies. This
fix replaces unreliable healthbar proxy triggers with the explicit defeat flag,
while preserving the checks assigned to the fight.

## Can I update the client during a run?

**Yes.** Existing v0.6.0.3 through v0.6.0.9 seeds remain compatible. Update the
client to receive this correction; no new seed or save migration is needed.
The contract hash is unchanged. Previous game-version and feature minimums remain.

## What you need to update

- **Client:** Required for the Scadutree Avatar sweep fix on existing seeds; otherwise optional.
- **APWorld:** Host-only, for newly generated rooms after this version ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** Reinstall or replace `eldenring_archipelago.dll` for this fix; no map asset changes.

## What carried over from v0.6.0.9

The map performance and missing-pin fixes remain included. This window adds the
Avatar completion correction and its existing-seed client support. The audit
confirmed no additional active instance among the other candidate sweep IDs.
Automated checks cover completion and ownership; no new live-game test is claimed.
