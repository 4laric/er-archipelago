# v0.3.2 — release blurb (draft)

> Drafted 2026-08-03. A bugfix release, mostly client-side. Three defects that were silently
> taking items off players, plus the auto-equip ruleset. `CONTRACT_HASH` is unmoved from v0.3.0.

**The item-loss release.** Three separate defects were quietly taking items off players — one of them
had been doing it since the id-keyed suppressor shipped. All three are fixed. Update both halves.

---

## Items you were losing

**Vanilla items were being eaten from every source, not just from checks.**
The client suppresses a check's vanilla ware so the randomizer can hand you what the seed actually
placed there. But it matched by *item ID*, and it could not tell where an item came from — so mining
an ore node, farming a drop, or picking up any copy of an item that happened to back some check
elsewhere in the seed made it vanish. Goods were fixed in July; weapons and armour were left on the
old mechanism on the grounds that "a weapon is essentially never farmable." That was wrong.

Now that every check's item lot is neutralised at its source, **1,078 of the 1,289 armed item IDs had
nothing left to protect** — including every goods entry and 285 of 367 weapons. They're gone. What
remains is the 211 checks that have no item lot to neutralise, and those now release as soon as the
check itself fires rather than waiting on a server round-trip.

**Auto-equip never worked on weapons if you also had auto-upgrade on.**
Armour equipped fine, weapons never did — and the reason is that auto-upgrade rewrites a weapon's ID
on its way into your inventory, while auto-equip was still looking for the ID it had *before* the
upgrade. It never found it, and retried for the rest of the session. If you run both options, weapons
now equip on arrival as intended.

**Crossbow bolts were replacing your main hand.** Ammunition is not a held weapon. It goes in the
quiver now.

**The Hefty Cracked Pot cap was one too low**, so the tenth one the DLC gives you was reported
delivered and never arrived. You can hold the full set.

## Auto-equip, sharpened

Shields, staves, seals, bows and crossbows now go to the **left hand**, following the community
French Challenge ruleset, instead of disarming you by landing in your main hand. Everything else
still goes right. The point of the format is that you don't get to choose — but you shouldn't be
punished for picking up a staff either.

## Quality of life

- Items with no name entry rendered as `?GoodsName?` or `[ERROR]`. They're named now.
- Minimising the game wrote **612,842 error lines** to the log in one session. Repeats collapse.
- Getting kicked out of a sealed region now tells you *which* region, *which* Lock opens it, and why
  your vanilla key didn't.
- Several systems that re-arm on a world edge were missing it, so their effects silently lapsed after
  a warp or a reload. All of them re-arm now.
- 256 checks used to refuse plain filler from **every** world in the multiworld, not just this one.
  That's gone — an Elden Ring slot is easier on a big async now.

## Compatibility

The slot_data contract is **unchanged** (`5e8b11c9`), so seeds rolled on 0.3.1 still connect. As
always, **the client and the apworld must match** — a 0.3.1 DLL against a 0.3.2 apworld is not a
configuration anyone has tested.

## Still open

Being straight about this: the item-loss fix above is a **cap, not a cure**. For the 211 checks that
have no item lot, a vanilla copy picked up *before* that check's award fires is still withheld. It
needs a way for the client to tell where a pickup came from, which the game does not currently give
us. If you see an item disappear, the log line starts with `vanilla-suppress:` — please send it.

Also still open and being worked: the grace-skip validation oracle, a Deeproot soft-lock report, a
Liurnia merchant report, and an economy report against 0.3.0. Reports with a log attached are worth
several without one.
