# v0.6.0.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is the 0.6.0 line: a v0.6.0.3 client plays every seed
rolled by any 0.6.0-line apworld, your run included. What changed this window is the other
direction — the contract hash moved (#1463), so an OLDER 0.6.0-line client on a seed rolled by
the v0.6.0.3 apworld logs a version mismatch. Update the binary before you generate a new room;
you do not have to touch a run already going.

## What you need to update

- **Client:** Required for seeds rolled on v0.6.0.3 — an older 0.6.0-line client reports a
  version mismatch against one. Safe to take mid-run: the v0.6.0.3 client plays every
  0.6.0-line seed, so a run already going needs nothing but the new binary.
- **APWorld:** Host-only — install v0.6.0.3 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** No action — the MapForGoblins build and preset are unchanged from v0.6.0.2.

## What is in it so far

**The seed now says what it is.** (#1463) The client has always had two ways to work out which
event flag a check corresponds to — ours, and the one Matt's randomizer uses — and it decided
between them by looking to see whether a particular key happened to be in the slot data. That
guess was never checked against anything. When it landed wrong the game did not complain: checks
simply stopped firing, and you found out an hour into the run. The apworld now states which
contract the seed speaks, and the client validates the seed against the statement instead of
inferring it, naming the offending key at connect if the two disagree. Generation refuses the
same mismatch from the other side. If everything was already working for you, nothing about your
seeds changes — this is the failure that used to be invisible becoming a line in the log.

## What carried over from v0.6.0.2

Nothing is owed. v0.6.0.2 shipped with its notes complete and its client half landed before the
tag. Client #316 (received Great Runes unequippable at a grace) remains an open known issue, not a
debt of this window. The upstream-core proposal (#1459) is tracked as work, not as a release debt.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
