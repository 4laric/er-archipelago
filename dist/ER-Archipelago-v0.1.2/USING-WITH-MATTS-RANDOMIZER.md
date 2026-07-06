# Using Elden Ring Archipelago alongside matt's randomizer

**Short version:** you can run this Archipelago (AP) mod together with thefifthmatt's
randomizer, but only its **enemy shuffle** (which enemies spawn where). Its **item
randomizer must be OFF**, and you should also turn its **enemy scaling / rebalancing
OFF** — AP already scales enemies itself. AP *is* the item randomizer here, and in the
flagship Shattering seed it's also the difficulty-scaler.

---

## The symptom this prevents

> "It connects to Archipelago fine, and enemy/boss scaling works. But items in the
> world are unrandomized — I walk up to a location the spoiler log says holds
> another world's item, and it's just the vanilla item. No checks send to anyone."

That is what a **misconfigured combo looks like**. Scaling appearing to work while
items are vanilla usually means AP never received the server's slot_data (see
troubleshooting) — so both AP's item layer *and* AP's own scaling are inert, and the
scaling you're seeing is entirely matt's.

---

## What composes and what doesn't

| matt's feature | With AP? | Why |
|---|---|---|
| **Enemy shuffle** (who spawns where) | ✅ Supported | Independent layer. It reshuffles who you fight; AP never touches enemy *placement*. |
| **Enemy / boss scaling / rebalancing** | ⚠️ Turn OFF | AP does its own sphere-based enemy scaling (always on in the flagship Shattering seed). Running matt's too either gets overwritten by AP or compounds into over-tuned enemies — see below. |
| **Item randomizer** | ❌ Must be OFF | AP owns item placement. Two randomizers on the same pickups = no checks send and items read vanilla. |
| **Other item/shop/loot options** | ❌ Leave off | Anything that rewrites item lots, shop contents, or start gear collides with AP's placement. |

Rule of thumb: **AP handles items, progression, *and* difficulty scaling; matt's mod is
only there to shuffle *which enemies* appear.**

---

## About scaling specifically

AP's client scales enemies at runtime: every ~second it sweeps the loaded enemies,
strips any vanilla scaling SpEffect (the game's `7000-7999` ladder), and applies the
tier for your current region/sphere. This is **on by default in the Shattering seed**
(the difficulty curve *is* the region progression), controlled by `completion_scaling_floor`.

That has two consequences for matt's scaling:

- **If matt scales via the same `70xx` SpEffects**, AP will clear and overwrite it every
  tick. Matt's scaling simply does nothing (AP wins) — harmless, but pointless.
- **If matt scales by editing enemy base stats** (regulation param HP/attack), AP's
  multiplier stacks *on top*, so enemies end up scaled twice — over-tuned.

Either way there's no benefit to running both. Let AP own scaling and switch matt's
scaling/rebalancing off. If you'd rather matt drives difficulty, set AP's scaling to its
floor and accept that AP may still re-touch loaded enemies — cleaner to just let AP do it.

---

## Correct setup

1. **Generate and install the AP seed** as in `SETUP.md` (apworld + yaml + me3 bundle).
2. **In matt's randomizer:** turn **item randomization OFF**, turn **enemy scaling /
   rebalancing OFF**, and leave **enemy shuffle** on if you want the variety.
3. **Load order / injection:** matt's load-DLL host and the AP client both inject into
   the running game and coexist. The AP client finds its own files next to its DLL, so
   no matt profile changes are needed — just make sure both are actually loaded.
4. **Confirm the AP files are beside the AP client DLL** (`eldenring_archipelago.dll`):
   - `apconfig.json` — server / slot / password
   - `er_static_detection_table.json` — the seed-independent detection table
   The client reads both from the folder your me3 profile points its natives at.
5. **Connect to the exact slot name for this seed.** The per-location table arrives in
   the server's slot_data on connect; a wrong slot or a failed connect leaves it empty,
   which also produces vanilla-looking items.

---

## Troubleshooting: "items are vanilla, scaling works"

Work down this list — first likely cause first:

1. **Wrong slot / seed / failed connect.** Open the in-game tracker (**F6**). A healthy
   connection shows a real total (e.g. `12/340`). If it shows **0/0**, the client has no
   location table — it never got slot_data. Check your slot name matches the yaml `name:`
   for *this* generated seed, and that the connect actually succeeded (watch the overlay
   confirmation and the client log). This also explains why the scaling you see is matt's,
   not AP's: no slot_data means AP's own scaling is inert too.
2. **matt's item randomizer is still on.** Turn it off, regenerate matt's side if it
   bakes files, relaunch.
3. **`er_static_detection_table.json` isn't next to the DLL.** Confirm it sits in the
   same folder as `eldenring_archipelago.dll` (the me3 natives path).
4. **Version mismatch.** If your `apconfig.json` was written by an older client, the
   client will refuse with a version message — regenerate/reconnect with the current
   release.

If all four are clean and pickups still read vanilla, grab the **client log** and the
**spoiler log + yaml** and open an issue — that's a real bug, not a setup problem.

---

## Why item randomization can't be shared

Archipelago places an item at every location and tracks each one by the vanilla event
flag that guards it. When you grab that pickup, the flag fires, the client sends the
check, and you receive whatever the multiworld routed to you. If matt's item
randomizer has also rewritten those same lots/flags, the guard flags no longer line up
with what you physically pick up — so AP's checks never fire and the placement AP
computed is meaningless. There's only room for one item randomizer, and in a multiworld
it has to be Archipelago.
