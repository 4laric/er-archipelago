# PR B1 — SoulsIds: pad omitted trailing args in ParseAdd

**Target:** `thefifthmatt/SoulsIds` (base `master`)
**Source:** `4laric/SoulsIds` commit `32f6282`
**Files:** `SoulsIds/Events.cs` (two call sites)
**Size:** +14 lines, no API change, no new dependency.

This is the lowest-friction PR in the set — generic library correctness, nothing
AP- or Elden-Ring-specific. Good first contribution to open a channel with the maintainer.

---

## Suggested PR title

`Events: pad omitted trailing args in ParseAdd to match raw EMEVD padding`

## Suggested PR description

> ### Problem
> `Events.ParseAdd` (both the init-arg path and the doc-driven path) requires the number of
> arguments in an instruction edit to exactly match the instruction's documented arg count, and
> throws otherwise:
>
> ```
> Expected {argTypes.Count} arguments for {cmd}, given {addArgs.Count} in {add}
> ```
>
> This is stricter than the game's own encoding. EMEVD instructions allow optional trailing
> arguments — when omitted, the raw event simply pads the tail with zeros. Event configs that are
> translated from symbolic/DarkScript-style sources legitimately write only the documented leading
> args (e.g. a `c4_14` call carrying 6 of its 9 raw slots), and currently fail to parse even though
> the intended encoding is unambiguous.
>
> ### Fix
> Before the count-equality check, if fewer args were supplied than the instruction declares, pad
> the remainder with `"0"` — mirroring the game's raw zero-padding. The existing strict check is
> retained, so over-supplying arguments (a real error) still throws as before.
>
> ```csharp
> if (addArgs.Count < argTypes.Count)
> {
>     // Optional trailing arguments: some configs write only the documented leading args;
>     // the omitted tail defaults to 0, matching the game's raw padding.
>     addArgs.AddRange(Enumerable.Repeat("0", argTypes.Count - addArgs.Count));
> }
> if (addArgs.Count != argTypes.Count) throw new Exception(...); // unchanged: over-supply still errors
> ```
>
> Applied at both `ParseAdd` sites (the `isInit` branch and the `docByName` branch) so behavior is
> consistent regardless of how the instruction doc is resolved.
>
> ### Why it's safe
> - Only triggers when args are *under*-supplied; the equality assertion that follows is unchanged,
>   so the over-supply error path is preserved.
> - Padding value `"0"` matches the documented default for omitted trailing EMEVD args.
> - No public signature change; purely a relaxation of an over-strict precondition.
>
> ### Testing
> - Parses event edits that previously threw on omitted trailing args (e.g. `c4_14` with 6/9 slots).
> - Existing edits that supply the full arg list are unaffected (count already equal → no padding).
> - Over-supplying args still throws the original exception.

---

## Pre-submit checklist

- [ ] Branch off `thefifthmatt/SoulsIds@master`, cherry-pick `32f6282` (Events.cs hunks only).
- [ ] Confirm the commit doesn't drag along the unrelated `tests, compiler warnings` changes
      (`ca938e8`) — keep this PR to the two Events.cs hunks.
- [ ] Drop the ER-specific phrasing from the inline comment (current comment names "v0.11.4 events";
      generalize to "some configs" as shown above) so it reads as a library-level fix.
- [ ] Sign commit with your GitHub-linked email (already `alaric.mckenzie.boone@gmail.com`).
- [ ] If the maintainer wants a repro test, add one under the SoulsIds test project before opening.

## Notes
- `thefifthmatt/SoulsIds` is a permissive library that already merges external PRs, so this is the
  right venue (unlike `SoulsRandomizers`, the licensing-landmine repo we're parking).
- This PR is self-contained — it has no dependency on any apworld or randomizer change and can go
  out first, independent of the lBedrockl work.
