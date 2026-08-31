# Elden Ring Archipelago -- Setup

This gets you from nothing to a running seed in about 15 minutes. Two halves:
**A. Make the seed** (Archipelago side) and **B. Install and play** (game side).

New to Archipelago? It is a **multiworld** randomizer platform: one or more
games are shuffled together, and items you find in your game can belong to
someone else's -- and theirs to you. It works solo too, and a solo base-game
run is the recommended way to play v0.2. Each player in a multiworld occupies
a **slot**, configured by a **yaml** -- a plain-text settings file.

The recommended configuration is **The Shattering**, solo, base game only: the
Lands Between is broken into regions, and each region's key arrives as a
randomized item. The included `EldenRing.yaml` is already set up for it. Change
`name:` and you have a valid seed.

🛑 **On the DLC.** `enable_dlc` is **on** in the apworld's own defaults, and the
shipped `EldenRing.yaml` turns it **off** (`enable_dlc: false`) because the base
game is the better-tested path. So: build from the template, or from a wizard
preset, and you get base game. A yaml that says nothing about it, such as an
empty `Elden Ring: {}` section or the wizard's blank **Defaults** card, enables
all 29 regions. Twelve of those regions need Shadow of the Erdtree.

---

## Upgrading from v0.1? Read this first.

**The game id changed.** In v0.1 the game was called `EldenRing`. In v0.2 it is
**`Elden Ring` (with a space)**. A v0.1 yaml will be rejected at generation
with:

```
No world found to handle game EldenRing. Did you mean 'Elden Ring'?
```

If you see that message, you are feeding v0.2 a v0.1 yaml.

**Start from the shipped `EldenRing.yaml` instead of repairing an old file.**
The option surface changed substantially after v0.1 and now has 56 tunable
options. Archipelago warns about each unrecognized option, drops it, and still
generates the seed with that option's default. Copy the current file and apply
your choices again. If you reuse an old yaml, read the generation output: it
names every option that was dropped.

**Mid-run on a v0.1 seed?** Because the game id changed, the v0.1 and v0.2
worlds can be installed side by side. You can finish your v0.1 seed first, no
rush.

---

## What's in this release

| File | What it is |
|---|---|
| `eldenring.apworld` | The Archipelago world -- the package that teaches Archipelago about Elden Ring. Goes in your Archipelago install. |
| `me3/` | The runtime client folder. Holds `eldenring_archipelago.dll`, `ap.me3`, `apconfig.json`, the AP Flower installer and two **required** data tables. After generating Matt's randomizer output, run `install-ap-flower.ps1 -Destination <randomizer-folder>` on Windows or `python3 install_ap_flower.py --destination <randomizer-folder>` on Linux/Proton, then restart Elden Ring. The installer only copies authenticated assets from `flower-package`; it never modifies or unpacks the base game. |
| `EldenRing.yaml` | The player config template (The Shattering). Copy it, set `name:`, generate. Or build one at <https://peliarch.ca/er/>. |
| `er-options-wizard.html` | An **offline copy of the yaml builder**. The live one at <https://peliarch.ca/er/> is the one to use -- it can hand your seed straight to a host -- but this file works with no network at all. |
| `SETUP.md` | This file. |
| `RELEASE-NOTES-v0.2.md` | What this project is and what v0.2 brings, in one read. |
| `CHANGELOG.md` | The per-release delta, newest first. |
| `KNOWN-ISSUES.md` | Current known issues and by-design non-features -- read it before filing a report. |
| `Elden-Ring-Archipelago-Player-Guide.md` | How a run actually plays once you press New Game. |
| `GETTING-UNSTUCK.md` | Rescue-console commands for a bad warp, missing grace, or goal that did not fire. |
| `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` | Stacking matt's randomizer for enemies and starting class (with items OFF). |
| `ATTRIBUTION.md` | Credits, licensing, and provenance. |
| `PROVENANCE.md` | Why this is a clean rebuild -- the five provenance non-negotiables and how CI enforces them. |
| `DISTRIBUTION.md` | How this release is packaged, and why the apworld and `.dll` must come from the same tag. |
| `SCREENSHOTS.md` | Index of the screenshots and what each one shows. |
| `screenshots/` | The images (10 PNGs) the docs above reference. |
| `LICENSE` | The MIT license text. |

You also need, separately:

- **Elden Ring** on PC (Steam). **We** bake nothing into the game files: no
  `regulation.bin` edit, no file patching. Everything this randomizer does
  happens at runtime, while the game runs.

  That is also why it **stacks with thefifthmatt's Elden Ring randomizer**. If
  you want randomized enemies or a randomized starting class, run matt's for
  those and play your Archipelago seed on top -- with **item randomization
  turned OFF in matt's**, since that part is our job. See
  `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md`.
- **Archipelago 0.6.7** -- download from [archipelago.gg](https://archipelago.gg).
  0.6.7 is what this release is built and tested against, and it is what we
  recommend. The apworld's declared minimum is 0.6.6 and players have reported
  it working there, but 0.6.6 is not what we test, so if anything looks wrong,
  move to 0.6.7 before reporting it.
- **ModEngine3 (me3)** -- the mod loader that loads the client into the game.

---

## A. Make the seed (Archipelago side)

1. **Install the apworld.** Double-click `eldenring.apworld` so Archipelago
   registers it, *or* drop it into `Archipelago/custom_worlds/`. Either way,
   you should end up with `eldenring.apworld` sitting in
   `Archipelago/custom_worlds/`.

2. **Build your config.** The fastest way is the **yaml builder** at
   **<https://peliarch.ca/er/>**. It is a web page -- nothing to install --
   that walks you through every option in seven tabs, tells you **how big your
   seed will be** before you generate it (exact check counts, how many can hold
   progression, how much of your pool travels to other players), and hands you
   a finished yaml to download. It stamps which apworld version it wrote for
   into the file, so a host can always see which build a yaml came from.

   🛑 **The page can be ahead of the apworld you installed.** `/er/` tracks the
   released build and `/er/beta/` tracks what is being built right now, and the
   banner on each says which. This matters because Archipelago does **not**
   error on an option your installed apworld has never heard of -- it prints one
   line among fifty and generates the seed without it. If the builder offers you
   an option and your seed ignores it, you are on an older apworld: take the
   newest release.

   Prefer to edit a file? Copy `EldenRing.yaml` into `Archipelago/Players/`,
   open it and set `name:` to the slot name you want. That is the only edit you
   *need* -- the defaults are a tuned solo Shattering run. Leave
   `game: Elden Ring` and the `Elden Ring:` section header exactly as they
   are (the options must stay indented under it). Every option is explained in a
   comment right next to it in the yaml; `KNOWN-ISSUES.md` lists the by-design
   no-ops.

3. **Generate.** Run **Generate** from the Archipelago Launcher (or
   `ArchipelagoGenerate`). When it works, an `AP_<...>.zip` appears in
   Archipelago's `output/` folder. If it fails naming the game `EldenRing`,
   see the upgrade section above.

4. **Host it.** For a solo game, host the zip locally with the Archipelago
   server in the same install. For a multiworld, upload it to
   [archipelago.gg](https://archipelago.gg) and note the **room address** and
   **port** -- you will enter them in-game in part B.

---

## B. Install and play (game side)

1. **Install ModEngine3.** Follow its own install instructions until the
   `me3` launcher works.

2. **Drop in the runtime client.** The release ships a ready-to-run `me3/`
   folder. Launch Elden Ring with its profile:
   `me3 launch --profile "<path to me3>\ap.me3"`. Keep the folder intact: the two
   data tables (`check_lots_table.json`, `shoplineup_flags.json`) must sit next to
   the DLL, or checks double-pay the vanilla item and shop checks never fire. When
   the client is loaded, its overlay **menu bar** is visible in-game.

   **Start a new character.** When you use this profile, the game writes to a
   separate save file (`AP_me3.sl2`). The first time it
   creates that file, me3 copies your existing `ER0000.sl2`, so the character
   list initially includes copies of all your vanilla characters. That is
   expected: seeing those names does **not** mean the two launches still share
   a save. A new character created through `ap.me3` is written only to
   `AP_me3.sl2` and will not appear when you launch vanilla Elden Ring.

   Do not load one of the copied vanilla characters while the Archipelago
   client is connected. A character with no Archipelago identity marker looks
   like a fresh AP character and may receive the room's item backlog. Create
   and use a new character for the seed.

   This separation is the profile's doing: it comes from the
   `savefile = "AP_me3.sl2"` line in `ap.me3`, **not** from the client, and it
   does not require the Alt Saves DLL. Launch our dll any other way and it does
   not apply. See the next step.

   **Also running Matt's randomizer?** Add `eldenring_archipelago.dll` to Matt's
   **Add dll mod** list, then use his **Launch Elden Ring** button. Point the list
   at the DLL inside this release's `me3/` folder and leave it there. Its two data
   tables must remain beside it. For easier upgrades, unpack each release over a
   folder whose name does not contain the version; Matt can keep using the same
   path. See `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` for the illustrated
   walkthrough.

   **Matt's launcher does not select the separate AP save.** It never reads
   `ap.me3`, so the `savefile` line above does not apply. Your Archipelago
   character is created in your ordinary Elden Ring save, next to your real
   ones. Nothing of yours is overwritten, but the two share one file and one
   backup from then on. If you want them apart, set that up **before** you
   start -- `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` has the options.

3. **Connect.** Open the **Connection** entry in the overlay menu bar and
   enter your server address, slot name, and password.

   **The port is not 38281.** If you are playing on archipelago.gg, your room
   gets its own port when it is created -- it is printed on the room page,
   next to the server address, and it changes for every room. `38281` is only
   the default for a server you are running yourself, where the address is
   `localhost:38281`.

   The shipped `apconfig.json` says `archipelago.gg:PORT` for that reason: it
   is a placeholder, and the client will not try to connect until you replace
   `PORT` with your room's number (or fill the form in-game, which does the
   same thing). An `apconfig.json` kept from v0.1 still works:

   ```json
   {"url":"archipelago.gg:12345","slot":"YourName","seed":"","client_version":null,"password":null}
   ```

   Open the overlay from a menu, not while moving, so stray keys don't leak
   into the game.

   **This is what "it worked" looks like.** The overlay title reads
   **[Connected]**, and the log line names your slot and the game:

   ![The Archipelago overlay, connected](screenshots/overlay-connected.png)

   `Tester_A2 (Team #1) playing Elden Ring has joined.`

   Note the game name in that line: **`Elden Ring`**, with the space.

   **If the connection fails**, first read the specific error. Wrong slot,
   password, game, or seed values each produce their own message. The steps
   below are for a refusal or a timeout.

   1. Note the timing. An immediate red line is a refusal. A wait of roughly
      20 seconds is a timeout. The Elden Ring client currently uses the same
      sentence for both, so include the timing and client log in a bug report.
   2. Open Archipelago's stock **Text Client** and enter
      `/connect <host>:<port>`, using the exact address from the Elden Ring
      form.
   3. If the Text Client also fails, refresh the hosted room page.
      archipelago.gg pauses an inactive room after two hours; loading the page
      wakes it. Re-copy the displayed port because a restarted room may have a
      different one. If it still fails, investigate the room or network.
   4. If the Text Client connects, the address and network path work. Check
      software that can filter `eldenring.exe` specifically: outbound firewall
      rules, third-party antivirus network protection, VPN split tunnelling,
      and other mods in the active Mod Engine 3 profile that hook WinSock.
      Elden Ring modding guides sometimes recommend blocking the executable to
      keep it off FromSoftware's servers. That rule also blocks Archipelago.
      In Windows Defender, match the program path rather than the rule name:

      ```powershell
      Get-NetFirewallApplicationFilter -All |
        Where-Object { $_.Program -like "*eldenring*" } |
        Get-NetFirewallRule
      ```

      Antivirus rules do not necessarily appear in Defender's list.

4. **Play.** In The Shattering you begin at Roundtable Hold with one region
   already open. Find a region's Lock, fast-travel in, clear its checks, and
   work toward the goal region. Received items appear in the game's own
   bottom-center event banner; every check you find is sent to the server.

   One thing to internalize before you start: **Region Locks are the only way
   into a region.** When a Lock arrives, that region's graces light up and
   you warp in. Vanilla key items and routes gate nothing -- no Rold
   Medallion for the Mountaintops, no Mohg fight for the DLC -- and entering
   a region whose Lock you don't hold gets you warped back out. The Player
   Guide covers this model (and its two vanilla-flavored exceptions) in
   detail.

### Handy in-game tools

- **Tracker** -- press **F6** or use the **Tracker** entry in the overlay menu
  bar. Shows your checks grouped by region with done/total, dims locked
  regions and names their gate item, and highlights your current region.
- `/warp <id>` -- teleport (e.g. into a freshly unlocked region if a grace
  hasn't lit yet).
- **Connection** -- re-enter server / slot / password any time, even while
  connected, to switch rooms.

---

## Variants

The defaults are the recommended run. If you want to stray:

- **Shorter runs:** the shipped `num_regions: 6` keeps six regions. `0` keeps
  every eligible region in play -- the full Shattering, which is 17 base-game
  regions as shipped, or all 28 with the DLC on. Set something small like `4`
  for a tight evening run.
- **Which regions:** `num_regions_order` decides. `rolled` (the default) draws
  N regions at random from the eligible pool; `vanilla_order` takes the first N
  along the region spine instead and is fully deterministic. Neither decides
  where you *start* -- the opening region is always an independent draw,
  weighted by region size, over whatever ends up kept.
- **Great-Rune goal:** `ending_condition: great_runes` +
  `goal_great_runes: N`.
- **DeathLink:** `death_link: true` -- shared deaths in a multiworld, both
  directions.
- **DLC:** `enable_dlc: true` (DLC regions become eligible -- this is the
  apworld default, and the shipped template overrides it to `false`) or
  `dlc_only: true` (only the Land of Shadow). DLC regions unlock exactly like
  base ones -- their Lock arrives and you warp in; you never fight Mohg
  first. Base game is the recommended, supported way to play v0.2 -- see
  `KNOWN-ISSUES.md` for DLC caveats.

---

## If something went wrong

**For any yaml problem, start from the current template.** Copy this release's
`EldenRing.yaml`, or make a fresh file at <https://peliarch.ca/er/>, then apply
your choices again. Archipelago warns about unknown options but ignores them
and continues with their defaults. Editing an old file until it generates can
therefore produce a valid seed with different settings than you intended.

**`VERSION MISMATCH` in the client log.**
Your apworld and your client `.dll` are from different builds. The game will
still boot and connect, but the two sides can interpret seed data differently.
**Redownload both from the same release tag.** In a multiworld, ask the host
which apworld version generated the room; your DLL must match that version.

**"No world found to handle game EldenRing. Did you mean 'Elden Ring'?"**
You generated with a v0.1 yaml. The game id is now `Elden Ring`, with a
space. Use the current-template remedy above. Changing only the `game:` line
can leave old option names that Archipelago ignores.

**The seed generated, but the game ignores settings I chose.**
The yaml probably uses retired option names. Use the current-template remedy
above and check the generation log for warnings about unknown options.

**Generation fails, or the apworld won't load, and it isn't the game-id message.**
Check your Archipelago version: this release is built and tested against
**0.6.7**, and that is what we recommend running. Also confirm
`eldenring.apworld` is in `Archipelago/custom_worlds/`.

**The game launches but there's no overlay / nothing connects.**
The client isn't loaded. Make sure you launched Elden Ring through
ModEngine3 and that your profile loads `eldenring_archipelago.dll`. A vanilla
install works; Matt's randomizer is supported with item randomization off.
Other mods that rewrite item lots or parameters are not supported.

**Checks send fine, but nothing ever arrives.**
`RandomizerHelper.dll` is loaded. It and our client both hook the routine that
puts an item in your inventory, and ours fails closed when it finds that routine
already patched -- so receiving dies, while sending, which does not use that
hook, carries on looking perfectly healthy. Unload the dll; turning off its
auto-equip and auto-upgrade options is not enough on some versions. The Player
Guide and `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` both cover this, and the
client log line is `AddItemFunc detour install deferred`.

Still stuck, or a seed looks broken? Bring your yaml and the spoiler log when
you ask for help.
