# v0.3.3 — release blurb (draft, window OPEN)

> Opened 2026-08-03 on the first change of the window (rule 14). Two data fixes and two client
> fixes so far. `CONTRACT_HASH` is unmoved from v0.3.0, so the handshake is unchanged — but the
> `data/` hash moves, so this rolls different seeds than 0.3.2, and the client changed too, so this
> one needs a new DLL.

**Your gear stopped going stale.** If you have been playing with auto-equip on, you may have noticed
that after a while only one talisman slot ever seemed to change — everything you got later kept
landing in the same place while three slots sat on whatever you happened to receive early. Same story
with the physick flask. Both now rotate, so the gear you are wearing is the gear you most recently
earned.

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
- **Talismans rotate instead of freezing.** Once all four slots were full, slots 2, 3 and 4 kept the
  2nd, 3rd and 4th talismans you were ever sent, permanently — only slot 1 ever changed again. New
  talismans now take each slot in turn. This holds across reconnects: the client works out how many
  slots you had earned from your item history rather than from the moment it happens to look, so
  logging back in does not shuffle your loadout.
- **Physick tears rotate too.** The same thing two slots wide — the 3rd tear and the 4th both landed
  in the same half of the flask, so the other half froze on whatever went in second.
- **D, Hunter of the Dead sells real checks again.** He stands at two points on that same border,
  and a merchant straddling two regions has his stock quarantined. Litany of Proper Death and
  Order's Blade are ordinary Limgrave shop checks.

- **Every Golden Seed and Sacred Tear now tells you where it actually is.** All 56 were walked and
  described by hand. "Golden Seed - around War-Dead Catacombs" is now "Putrid Tree-Spirit drop in
  War-Dead Catacombs"; the Stormhill Shack seed says it is what Roderika leaves behind when she moves
  to the Roundtable; the churches are named as churches. Nine of them stopped saying "(region
  unconfirmed)" and can now hold progression.

## Upgrading

**This one needs the new DLL** — the auto-equip fixes are client-side. (The window opened as an
apworld-only change and was described that way; the client fixes landed afterwards.) The handshake is
unchanged from v0.3.0, so an older client still connects — it just keeps the frozen-slot behaviour.

Seeds already in progress are fine. The region fixes only change what a NEW seed rolls; the auto-equip
fixes take effect on the seed you are already playing as soon as you load the new DLL.
