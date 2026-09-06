# v0.5.8 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes, if the run was made with v0.5.7.** v0.5.8 uses the same seed data and updating the client
will not break the run or delete the save. Runs from older releases need their own compatibility
ruling; the release notes must name those versions rather than treating every old run alike.

## What you need to update

- **Client:** Required for v0.5.8 seeds; keep existing runs on their matching client.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a v0.5.7 run can continue on the v0.5.8 client.
- **Profile/assets:** No action.

## What is in it so far

### Beta is the v0.6 preview

The beta pages now follow the `v0.6` development branch. The normal site remains the v0.5.7 stable
release, while `/er/beta/` shows the ongoing check-audit and logic work without mixing it into the
v0.5.x maintenance branch.

### Patch numbers advance one at a time

Maintenance releases will no longer skip a number by accident. After v0.5.8, the next patch is
v0.5.9. A deliberate new series such as v0.6.0 remains separate.

## What carried over from v0.5.7

Nothing is owed from v0.5.7. Its world/client pair, release blurb, changelog, immutable tag, assets,
stable-channel promotion, and updater metadata were all completed before this window opened.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
