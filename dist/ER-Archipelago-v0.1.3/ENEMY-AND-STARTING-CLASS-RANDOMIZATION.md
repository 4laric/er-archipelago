# Enemy & starting-class randomization

Your Archipelago (AP) seed already owns item placement, progression, and (in the flagship
Shattering seed) difficulty scaling. Two kinds of randomization stack cleanly on top for extra
variety, because neither touches world item placement:

- **Starting-class / loadout randomization** — built into AP, nothing to install.
- **Enemy randomization** — via thefifthmatt's optional external randomizer.

The one hard rule: if you use matt's randomizer, its **item randomizer must stay OFF** (and its
enemy scaling off too). AP is the only item randomizer in the room.

---

## Starting-class randomization (built into AP — nothing to install)

AP's **`random_start`** option (*Randomize Starting Loadout*) randomizes the equipment your
character begins with. It's a `DefaultOnToggle`, and the flagship `EldenRing-Shattering.yaml`
doesn't override it — so **the Shattering seed already randomizes your starting loadout** with no
external tool. It only affects your own starting gear; it doesn't change checks or anyone else's
world.

To turn it off, add to your yaml before generating:

```yaml
random_start: false
```

(Note: *where* you start is a separate option, `random_start_region`, tied to the region modes —
not the same as the starting loadout.)

---

## Enemy randomization (thefifthmatt's randomizer — optional external mod)

matt's *Elden Ring Item and Enemy Randomizer* can shuffle which enemies and bosses spawn where,
and it composes with AP **as long as you use only its enemy shuffle**. The AP client loads into
matt's randomizer as a DLL mod. Walkthrough:

### 1. Enemy Randomizer on, Item Randomizer off, scaling off

Open matt's randomizer. Leave the **Item Randomizer** tab unchecked, and check the **Enemy
Randomizer** tab. In **Game progression**, leave **"Scale up/down enemy health/damage" UNCHECKED** —
AP does its own sphere-based enemy scaling (always on in the Shattering seed). Running matt's on top
either gets overwritten by AP every tick or compounds into over-tuned enemies.

![Enemy Randomizer tab enabled; Item Randomizer and enemy scaling both off](<Screenshot 2026-07-05 104254.png>)

### 2. Add the AP client as a DLL mod

Click **Add dll mod** (bottom-right).

![Add dll mod button](<Screenshot 2026-07-05 104323.png>)

### 3. In the "Dll mods" dialog, click Add…

![Dll mods dialog with Add highlighted](<Screenshot 2026-07-05 104344.png>)

### 4. Select the AP client DLL

Browse to your `er-archipelago\me3\` folder and pick **`eldenring_archipelago.dll`**, then **Open**.

![Selecting eldenring_archipelago.dll from the me3 folder](<Screenshot 2026-07-05 104403.png>)

### 5. Randomize enemies, then launch

Confirm the footer reads **"Using eldenring_archipelago.dll"**, click **Randomize enemies**, then
**Launch Elden Ring**.

![Randomize enemies with the AP DLL loaded](<Screenshot 2026-07-05 104432.png>)

### What success looks like

On launch, the AP client overlay connects and the tracker starts registering checks as you pick
items up — enemies are shuffled, the items are AP's.

![AP client connected in-game, tracker registering checks](<Screenshot 2026-07-04 181900.png>)

---

## What composes and what doesn't

| matt's feature | With AP? | Why |
|---|---|---|
| **Enemy shuffle** (who spawns where) | ✅ Supported | Independent layer. It reshuffles who you fight; AP never touches enemy *placement*. |
| **Enemy / boss scaling / rebalancing** | ⚠️ Turn OFF | AP does its own sphere-based enemy scaling (always on in the flagship Shattering seed). Running matt's too either gets overwritten by AP or compounds into over-tuned enemies — see below. |
| **Item randomizer** | ❌ Must be OFF | AP owns item placement. Two randomizers on the same pickups = no checks send and items read vanilla. |
| **Other item/shop/loot options** | ❌ Leave off | Anything that rewrites item lots, shop contents, or start gear collides with AP's placement. |

Rule of thumb: **AP handles items, progression, *and* difficulty scaling; matt's mod is only there
to shuffle *which enemies* appear.**

---

## About scaling specifically

AP's client scales enemies at runtime: every ~second it sweeps the loaded enemies, strips any
vanilla scaling SpEffect (the game's `7000-7999` ladder), and applies the tier for your current
region/sphere. This is **on by default in the Shattering seed** (the difficulty curve *is* the
region progression), controlled by `completion_scaling_floor`.

That has two consequences for matt's scaling:

- **If matt scales via the same `70xx` SpEffects**, AP will clear and overwrite it every tick.
  Matt's scaling simply does nothing (AP wins) — harmless, but pointless.
- **If matt scales by editing enemy base stats** (regulation param HP/attack), AP's multiplier
  stacks *on top*, so enemies end up scaled twice — over-tuned.

Either way there's no benefit to running both. Let AP own scaling and switch matt's
scaling/rebalancing off.

---

## Correct setup checklist

1. **Generate and install the AP seed** as in `SETUP.md` (apworld + yaml + me3 bundle).
2. **In matt's randomizer:** turn **item randomization OFF**, turn **enemy scaling / rebalancing
   OFF**, leave **enemy shuffle** on, and load `eldenring_archipelago.dll` as a DLL mod (steps
   above).
3. **Load order / injection:** matt's load-DLL host and the AP client both inject into the running
   game and coexist. The AP client finds its own files next to its DLL, so no matt profile changes
   are needed — just make sure both are actually loaded.
4. **Confirm the AP files are beside the AP client DLL** (`eldenring_archipelago.dll`):
   - `apconfig.json` — server / slot / password
   - `er_static_detection_table.json` — the seed-independent detection table
5. **Connect to the exact slot name for this seed.** The per-location table arrives in the server's
   slot_data on connect; a wrong slot or a failed connect leaves it empty, which produces
   vanilla-looking items.

---

## Troubleshooting: "items are vanilla, scaling works"

This is what a **misconfigured combo looks like**: enemy/boss scaling appears to work, but items in
the world are unrandomized — you walk up to a location the spoiler log says holds another world's
item and it's just the vanilla item, and no checks send. Scaling working while items are vanilla
usually means AP never received the server's slot_data — so both AP's item layer *and* AP's own
scaling are inert, and the scaling you're seeing is entirely matt's.

Work down this list — first likely cause first:

1. **Wrong slot / seed / failed connect.** Open the in-game tracker (**F6**). A healthy connection
   shows a real total (e.g. `12/340`). If it shows **0/0**, the client has no location table — it
   never got slot_data. Check your slot name matches the yaml `name:` for *this* generated seed, and
   that the connect actually succeeded (watch the overlay confirmation and the client log).
2. **matt's item randomizer is still on.** Turn it off, regenerate matt's side if it bakes files,
   relaunch.
3. **`er_static_detection_table.json` isn't next to the DLL.** Confirm it sits in the same folder as
   `eldenring_archipelago.dll` (the me3 natives path).
4. **Version mismatch.** If your `apconfig.json` was written by an older client, the client will
   refuse with a version message — regenerate/reconnect with the current release.

If all four are clean and pickups still read vanilla, grab the **client log** and the **spoiler log
+ yaml** and open an issue — that's a real bug, not a setup problem.

---

## Why item randomization can't be shared

Archipelago places an item at every location and tracks each one by the vanilla event flag that
guards it. When you grab that pickup, the flag fires, the client sends the check, and you receive
whatever the multiworld routed to you. If matt's item randomizer has also rewritten those same
lots/flags, the guard flags no longer line up with what you physically pick up — so AP's checks
never fire and the placement AP computed is meaningless. There's only room for one item randomizer,
and in a multiworld it has to be Archipelago.
