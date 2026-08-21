# v0.4.11 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.4.11 client with v0.4.11 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.4.11; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** The window is empty.
- **Existing seed/save:** Compatible — keep an active v0.4.10 seed on its matched v0.4.10 pair.
  There is no save migration; just do not mix client and APWorld versions.
- **Profile/assets:** No action — no profile or packaged asset changed when the window opened.

## What is in it so far

Nothing yet. This window was opened at the v0.4.10 tag with zero commits past it, so the notes
exist before the first change does. That is the point of opening it now.

**The graces that lit for nobody light now.** Eight Sites of Grace were orphans: a safety gate
correctly refused to let the wrong region force-light them, but nothing ever handed them to the
right one — so Shadow Keep Main Gate stayed dark even after Scadu Altus opened, and so did Main
Academy Gate, Grand Lift of Rold, Hidden Path to the Haligtree, Castleward Tunnel, both Limgrave
Divine Tower graces, and Wyndham Catacombs. Each now lights with the region whose ground it
actually stands on. If you play `region_grace_unlock: entrance`, two entrances move to the
canonical doors: Stormveil opens at Castleward Tunnel and Raya Lucaria at Main Academy Gate —
which also means the academy unlock no longer warps you inside the seal.

**Shop previews keep their real names past 62 slots.** Locked and foreign-item shop slots show
you what is actually in them, but the pool of spare goods rows those preview names are written
into ran dry at 62 — past that, slots fell back to the `?GoodsName?` placeholder. The pool now
carries 79 rows: the same safe 62 first, so seeds under the old ceiling draw the identical names,
then 17 rows that have no vanilla text at all, named by the client creating brand-new text
entries in the game's own tables. A seed that needs the extra rows says so, and a client too old
to create entries is told to update at connect instead of silently showing placeholders.

**The Four Belfries key chest joins the pool.** The Imbued Sword Key chest at The Four Belfries
had been mislabeled as a duplicate of a key that already existed elsewhere, so it paid out its
vanilla key and could never hold a real item. It is the genuine third base-game copy — alongside
Raya Lucaria and Sellia, with Castle Ensis the fourth in the DLC — and it now works like any other
check, regioned to Liurnia.

## What carried over from v0.4.10

No player-facing work is carried over. The v0.4.10 tag is exactly the `main` commit this window
started from, and that release's notes are complete. The only housekeeping paid here is promoting
the stable channel to the already-published v0.4.10 tag while beta remains on `main`.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
