# v0.6.1.2 — release blurb (draft)

_Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** `CONTRACT_HASH` is unmoved at `2aa64f43`, so the v0.6.1.2 client and the v0.6.1 / v0.6.1.1 clients are interchangeable on each other's seeds, and all of them read every 0.4.13, 0.5.x and 0.6.0.x seed through the audited legacy-contract bridge. Swapping the `.dll` mid-run puts nothing at risk and needs no reroll or save migration. The standing version gates still apply and none are new.

## What you need to update

- **Client:** Optional -- two client-only additions (the `!scaling` command and a dismissible log legend). A v0.6.1.1 client still plays every v0.6.1.2 seed.
- **APWorld:** No -- unchanged apart from its version stamp; existing rooms keep theirs.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

**Enemies too tough, or not tough enough? Change it mid-run.** Type `!scaling` in the client
console to see where you stand, `!scaling 0` .. `!scaling 19` to pin every enemy to one rung of
the difficulty ladder, `!scaling off` to stop scaling, and `!scaling seed` to go back to the curve
your seed generated. It lasts until you reconnect, which puts you back on the seed's curve, and
`off` leaves enemies that are already scaled as they are until they reload. The command is the
client's, so it needs a v0.6.1.2 client -- on an older one the server answers "Could not find
command scaling".

**The log legend can be put away.** It has a "Hide this legend" button now; Settings ->
"Show log legend" brings it back.

## What carried over from v0.6.1.1

Nothing is owed. v0.6.1.1's release workflows were green, and its stable promotion was paid in this window's opening commit (stable and `latest.json` read v0.6.1.1). Two `bb-archipelago` logging tests fail locally on sandbox file-write permissions; they are Bloodborne-side, fail identically on client main, and do not touch this release.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
