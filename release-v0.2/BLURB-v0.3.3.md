# v0.3.3 — release blurb (draft, window OPEN)

> Opened 2026-08-03 on the first change of the window (rule 14). One data fix so far.
> `CONTRACT_HASH` is unmoved from v0.3.0 — the client is unchanged — but the `data/` hash moves,
> so this rolls different seeds than 0.3.2 and the apworld version moves with it.

**The two tiles that fell the wrong way.** If you killed the boss at Summonwater Village and got nothing
at all, it was not your imagination and it was not a missed drop: the ground he stands on was filed
under Caelid, so on any seed without Caelid neither he nor his twelve neighbouring checks existed.
Fixed — and its mirror with it: Fort Gael was filed under Limgrave for the same reason, in the
other direction.

---

## What changed

- **Summonwater Village pays out.** The Tibia Mariner's sweep, his Deathroot, and twelve checks
  around Summonwater Village and the Third Church of Marika were filed under Caelid.
- **Fort Gael is in Caelid again.** Fifteen checks there — including Lion's Claw and Flame, Grant Me
  Strength — were filed under Limgrave. Two "Smoldering Butterfly" checks beside them belonged to no
  sweep at all, because the only boss near enough stood across the seam. They have one now.
- **D, Hunter of the Dead sells real checks again.** He stands at two points on that same border,
  and a merchant straddling two regions has his stock quarantined. Litany of Proper Death and
  Order's Blade are ordinary Limgrave shop checks.

## Upgrading

The client is unchanged from v0.3.2 — no DLL update needed. Seeds already in progress are unaffected;
this only changes what a NEW seed rolls.
