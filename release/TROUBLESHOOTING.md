# Troubleshooting -- Elden Ring Archipelago

Current as of **v0.6.1.6** (2026-09-29). The stable channel is **v0.6.1.5**. Every client on the
0.6.1 line connects to every 0.6.1.x seed (contract `2aa64f43`, unchanged since v0.6.0.11).

This page gathers the problems players have actually hit, sorted by symptom. Each entry names
the cause and the fix. The longer guides remain the reference, and each entry links to one:

- [SETUP.md](SETUP.md) -- first install through me3
- [ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md](ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md) --
  playing on top of thefifthmatt's randomizer
- [GETTING-UNSTUCK.md](GETTING-UNSTUCK.md) -- the in-game rescue console (warps, flags, graces)
- [KNOWN-ISSUES.md](KNOWN-ISSUES.md) -- what is known and not yet fixed

**Before anything else, answer two questions.** Most reports come down to one of them.

1. **Which launcher are you using?** Either **me3** with `ap.me3`, or **matt's randomizer** with
   **Add dll mod**. The two paths differ in where the save goes, where the log goes, and whether
   the AP flower icon loads. Follow the section for the launcher you use.
2. **Do your apworld and your client come from the same release?** The host's apworld and your DLL
   must share a contract. See [VERSION MISMATCH](#version-mismatch-in-the-log).

---

## The ten most common problems

| you see | what it almost always is | go to |
|---|---|---|
| "I can't find the DLL", or a folder of thousands of files | You downloaded **Source code (zip)**, not the release bundle | [1](#wrong-download-source-code-instead-of-the-bundle) |
| The game launches vanilla: no overlay, no menu bar | The zip was never extracted, or the game was not launched through `ap.me3` | [1](#the-game-launches-vanilla-no-overlay) |
| "Unsupported game version" after a Steam update | Your client is older than the game. Update the client; do not downgrade the game | [5](#5-the-game-will-not-start-or-crashes) |
| "Version is wrong" right after updating, launching through matt's | Matt's launcher still points at the old DLL | [4](#updating-our-client-when-you-launch-through-matts) |
| Torrent does not come to the whistle | Your copy of matt's randomizer is out of date | [4](#updating-matts-randomizer-itself) |
| Checks send but nothing arrives; items say "can't hold more" | `RandomizerHelper.dll` is loaded | [4](#checks-send-but-nothing-ever-arrives) |
| Every pickup also gives the vanilla item | The DLL was separated from its two `.json` tables | [1](#do-not-move-the-dll-out-of-me3) |
| The browser or antivirus deletes the download as a virus | A false positive on an unsigned DLL | [1](#the-download-is-deleted-as-a-virus) |
| Connection refused or timing out | Wrong port, a sleeping room, or a firewall rule on `eldenring.exe` | [6](#6-connecting) |
| Generation fails although the apworld is installed | An older `eldenring.apworld` in `worlds\` beside the new one in `custom_worlds\` | [9](#9-generating-the-seed) |

---

## Contents

1. [Downloading and extracting the zip](#1-downloading-and-extracting-the-zip)
2. [Running the bundled .ps1 scripts](#2-running-the-bundled-ps1-scripts)
3. [Updating the client](#3-updating-the-client)
4. [Matt's randomizer](#4-matts-randomizer)
5. [The game will not start, or crashes](#5-the-game-will-not-start-or-crashes)
6. [Connecting](#6-connecting)
7. [Items, checks, icons and the map](#7-items-checks-icons-and-the-map)
8. [Saves, Seamless Co-op and other mods](#8-saves-seamless-co-op-and-other-mods)
9. [Generating the seed](#9-generating-the-seed)
10. [Reporting a problem](#10-reporting-a-problem)

---

## 1. Downloading and extracting the zip

**Which file do I download?** Each release on
[GitHub Releases](https://github.com/4laric/er-archipelago/releases) has four assets:

| asset | who needs it |
|---|---|
| `ER-Archipelago-v<ver>-<timestamp>.zip` | **Players.** Contains the client, the apworld, and the docs. |
| `eldenring.apworld` | **Room hosts** who only generate seeds. |
| `eldenring.apworld.cat` | Signature catalogue for the apworld. You can ignore it. |
| `Optional-Offline-Tools.zip` | Optional HTML tools. **It contains no DLL**, so it cannot be used to play. |

**Prefer GitHub to Nexus.** Nexus sometimes lags a release or two behind. A copy passed around
Discord may be from any release.

### Wrong download: source code instead of the bundle

Every GitHub release page also lists **Source code (zip)** and **Source code (tar.gz)** at the
bottom. GitHub adds those automatically, and they are the developer repository: thousands of files,
**no DLL**, and no `me3\` folder. The repository's front page has a green **Code > Download ZIP**
button that gets you the same thing. If you are looking for the DLL and cannot find it, check which
zip you downloaded. You want the asset whose name starts with **`ER-Archipelago-v`**.

### The download is deleted as a virus

Chrome, Edge, or Windows Defender sometimes flags the zip or the DLL and deletes it. The client is
an unsigned DLL that hooks a game process, which is the kind of file heuristic scanners dislike.
Releases are published by GitHub's build pipeline from the public source, and code signing is being
added. If this happens:

- download from the GitHub release page itself, not a mirror or a Discord re-upload;
- restore the file from the browser's download list or from Defender's **Protection history**;
- if you want a second opinion first, upload the zip to <https://www.virustotal.com/>.

Only allow a file you downloaded from the official release page. If a scanner deletes files from
the extracted folder later, the symptom is the one below: missing files.

### Missing files after extracting

If `me3\` lacks `eldenring_archipelago.dll` or either `.json` table, the download or the extraction
was incomplete, or a scanner removed a file. Delete the folder, download the zip again, and extract
it again. Compare the folder with the layout below.

### Extract it first

**Extract the whole zip before you run anything.** Double-clicking into a zip in Explorer only
previews it. A DLL or script run from that preview runs from a temporary folder, without the files
beside it. Right-click the zip, choose **Extract All...**, then work in the folder that creates.
Downloading and extracting are two separate steps.

**What the extracted folder should look like.** The zip has no top-level folder. Its contents
unpack straight into the folder you extract to:

```
<your folder>\
  eldenring.apworld          <- goes to Archipelago\custom_worlds\ (the host's copy)
  EldenRing.yaml             <- your settings template
  SETUP.md, KNOWN-ISSUES.md, ...
  me3\
    eldenring_archipelago.dll
    check_lots_table.json    <- must stay beside the DLL
    shoplineup_flags.json    <- must stay beside the DLL
    MapForGoblins.dll
    MapForGoblins.ini
    MapForGoblins.upstream.dll   <- fallback only; do not load it
    ap.me3
    apconfig.json
    install-ap-flower.ps1, install-into-matts-rando.ps1, update-er-archipelago.ps1 (+ .py twins)
    flower-package\
```

If you see a second folder with the same name inside the first, the zip was extracted twice.
That is harmless as long as `me3\` is complete.

**Explorer hides file extensions by default.** In the Explorer window, `ap.me3` may appear as just
**`ap`** with the me3 icon, and `apconfig.json` as **`apconfig`**. They are the same files. To see
the full names, turn on **View > Show > File name extensions**.

### The game launches vanilla, no overlay

When the client is loaded, an overlay **menu bar** is visible in-game. If it is missing:

- **With me3: double-click `ap.me3`**, the profile inside the extracted `me3\` folder, or run
  `me3 launch --profile "<your folder>\me3\ap.me3"`. Launching Elden Ring from Steam, or from the
  me3 manager window without choosing this profile, starts the game unmodded. If the me3 manager
  lists only a "flower package" and the game looks vanilla, you are not running the extracted
  `ap.me3`. Extract the zip, then double-click `ap.me3` in `me3\`.
- If double-clicking `ap.me3` does nothing, **me3 itself is not installed**. Install it first
  ([SETUP.md](SETUP.md) part B).
- **With matt's randomizer:** the main window must read **"Using eldenring_archipelago.dll"**.
  See [section 4](#4-matts-randomizer).

**Editing `apconfig.json`.** You do not have to edit it. Launch the game and use **Connection** in
the overlay menu bar. If you would rather edit the file, right-click it and choose
**Open with > Notepad**. Any plain-text editor works, and you do not need Visual Studio or any other
code editor.

**Choose a folder name without the version in it.** By default, Windows' **Extract All** names the
folder after the zip, for example `ER-Archipelago-v0.6.1.6-20260927-171608`. Rename it to something
stable such as `C:\Games\ER-Archipelago\` before you point anything at it. Matt's launcher
remembers the DLL by its full path. A versioned path keeps it loading the old client after you
upgrade (see [section 3](#3-updating-the-client)). The me3 path is less sensitive to this, but a
stable folder still makes every later upgrade a matter of extracting over it.

### Do not move the DLL out of me3

`eldenring_archipelago.dll` needs its two data tables beside
it. A DLL copied elsewhere leaves them behind, and then:

- every check pays out **both** the vanilla item and the AP item (`check_lots_table.json` missing);
- shop purchases never register as checks (`shoplineup_flags.json` missing).

Point your loader at the DLL where it is. The log confirms both tables loaded: look for the lines
starting `check-lots:` and `shoplineup_flags:`.

**Avoid protected folders.** Do not extract into `C:\Program Files\` or into the Elden Ring `Game\`
folder. The client and the updater write files such as the log, `apconfig.json`, and backups
beside the DLL, and protected folders make those writes fail.

---

## 2. Running the bundled .ps1 scripts

The bundle ships three PowerShell launchers: `install-ap-flower.ps1`, `install-into-matts-rando.ps1`
and `update-er-archipelago.ps1`. **Each is a thin wrapper around a Python script** of the same name
(`install_ap_flower.py`, and so on). Two things commonly stop them.

**"...cannot be loaded because running scripts is disabled on this system" or "...is not digitally
signed".** This is Windows' PowerShell execution policy, and it matters more for files unpacked from
a downloaded zip. Run the script for this one invocation without changing any system setting:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-ap-flower.ps1 -Destination "<matt's output folder>"
```

Or skip PowerShell and call the Python script directly. The flags are the same, spelled
`--kebab-case`:

```powershell
py .\install_ap_flower.py --destination "<matt's output folder>"
```

**"Python is required to ..." or a Microsoft Store window opens.** The scripts need Python 3,
standard library only. Install it from <https://www.python.org/downloads/> and tick
**Add python.exe to PATH**, or install the **py launcher**. The `python` that ships with Windows
is a Store shortcut, not Python: if typing `python` opens the Store, install real Python, or turn
the shortcut off under **Settings > Apps > Advanced app settings > App execution aliases**.

**Run them from inside `me3\`**, where they sit next to the files they install. Close the game
first. Close matt's app first as well when a script edits its folder.

---

## 3. Updating the client

**Do I need to update?** Each release's CHANGELOG entry opens with a **What you need to update**
block that answers this separately for the client, the apworld, your YAML and a running save. Within
the 0.6.1 line, client updates are optional for connecting. They still carry fixes, so take them.

**The easy way: the updater.** With the game closed, from your existing `me3\` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\update-er-archipelago.ps1
```

It reads the latest version, downloads the matching zip, and backs up every file before replacing
it. It replaces only the shipped `me3\` payload. It never touches `apconfig.json`, an existing
`MapForGoblins.ini`, saves, or logs. If the contract changed, it stops and asks for
`-AcceptContractChange`. **Do not pass that flag in the middle of a seed** unless the release notes
say the new client still accepts your seed. The updater does not update the apworld (that belongs
to the room host) and does not touch matt's folder. If you launch through matt's, re-run
`install-into-matts-rando` afterwards (see [section 4](#4-matts-randomizer)).

**The manual way.** Extract the new zip **over the same folder**, overwriting. Keep your
`apconfig.json` and `MapForGoblins.ini`, or re-enter them. MapForGoblins 2.1.5 arrived in v0.6.1.5:
replace both map DLLs with the ones from the zip and keep your INI.

**"I updated and nothing changed."** You are still loading the old DLL from its old folder. With
me3, check which folder your `me3 launch --profile` command points at. With matt's, see
[Updating our client](#updating-our-client-when-you-launch-through-matts) below. The log's
`SESSION START` line names the client build that actually loaded.

**The v0.6.1.4 zip was built from an older client.** Its notes list clients #716, #718 and #719
(including map-pin sync across a shared slot), but those fixes are not in that zip. They ship in
**v0.6.1.5**. If you are on v0.6.1.4, update.

---

## 4. Matt's randomizer

The full walkthrough, with screenshots, is
[ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md](ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md). These are
the points players miss.

### The three rules

1. **Item Randomizer OFF** in matt's app. Items are ours. Enemies and starting class are his.
2. **Do not load `RandomizerHelper.dll`.** It breaks receiving (see below).
3. **No me3 on this path.** Matt's launcher loads the DLLs itself and never reads `ap.me3`. That is
   why the separate save, the flower icon, and the profile's MapForGoblins entry do not apply here
   automatically. The reverse also holds: **enemies are not randomized if you launch with
   `ap.me3`**. Randomized enemies come only from launching through matt's app, with our DLLs added
   to it.

### Updating matt's randomizer itself

**Use his current, patched release from Nexus**
(<https://www.nexusmods.com/eldenring/mods/428>, and nowhere else). It includes the Torrent fix for
Elden Ring 1.17+. On older versions, **Torrent does not come when you whistle** after randomizing.
Older guides mention a "Tarnished Torrent Repair" script. It is gone; updating matt's app is the
whole fix.

When you install a new version of matt's app into a **new folder**, it starts empty. Redo these,
in this order:

1. Paste the options string again (**Options > Set options from string**). The string is in the
   walkthrough. Confirm **Item Randomizer** is unticked and **Randomize starting class loadouts**
   is ticked.
2. With matt's app **closed**, wire our DLLs into the new folder:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install-into-matts-rando.ps1 -Randomizer "<new folder containing EldenRingRandomizer.exe>" -WithFlower
   ```

   This writes matt's DLL list (`config_eldenringrandomizer_dll.toml`) to point at
   `eldenring_archipelago.dll` **and** `MapForGoblins.dll` inside your `me3\` folder. It creates
   that file if the new install does not have one yet, and backs up anything it changes. It refuses
   with a reason if matt's app is running, if the folder has no `EldenRingRandomizer.exe`, or if
   the DLL's data tables are missing.
3. Open matt's app, click **Randomize enemies**, confirm the **Overall seed** box is blank, then
   **Launch Elden Ring**.
4. If AP items show as Telescopes, run the flower installer against the new output folder (below).

If you updated matt's app **in place**, in the same folder, his DLL list survives. You only need
to re-randomize, and to re-run the flower installer if the Telescopes come back.

### Updating our client when you launch through matt's

Matt's launcher remembers each DLL by its full path.

- **You extracted the new release over the old folder:** nothing to do.
- **You extracted into a new folder:** the launcher is still loading the old client, so you keep
  seeing "unsupported game version" or a version warning after you have updated. Close matt's
  app, then run from the **new** `me3\` folder:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install-into-matts-rando.ps1 -Randomizer "<folder containing EldenRingRandomizer.exe>"
  ```

  It repoints both DLLs. Running it again is harmless: it exits "already current" when nothing
  needs to change. To do it by hand instead, open **Add dll mod**, remove the old entries, and add
  both DLLs from the new `me3\` folder.

### No map pins, or no MapForGoblins, under matt's

Add **`MapForGoblins.dll`** to matt's DLL list as well as our client, using **Add dll mod** a
second time or the install script above. Add `MapForGoblins.dll` only, **not**
`MapForGoblins.upstream.dll`. Like the client, it must stay inside `me3\` beside its INI.

### AP items and shop slots show a Telescope icon

The AP flower is a repaint of the vanilla Telescope icon, loaded from `ap.me3`, which matt's
launcher never reads. The items are still real. Read the name: a foreign item says
**`AP: <item>`**. To get the flower icon:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-ap-flower.ps1 -Destination "<matt's output folder>"
```

Not sure which folder is matt's output folder? The first lines of your latest client log say
`mod stack: THIRD-PARTY DATA MOD at ... (<path>)`, and that path is it. **Re-randomizing can
overwrite the icon.** If the Telescopes come back after **Randomize enemies**, run the installer
again. It will not overwrite an atlas it did not install unless you add `-ReplaceExisting`, so a
different menu mod does not lose its files silently.

### Checks send, but nothing ever arrives

All of these together: sending works, **you receive nothing**, a check hands you a literal
**"Archipelago Item"**, the game says you **cannot hold any more** of it, and you start **without
Torrent** or your start items. The cause is
`RandomizerHelper.dll`. It hooks the same routine our client uses to give you items, and our hook
refuses to install on top of it (on purpose; guessing in that routine can corrupt a save). Remove
the DLL from matt's list. Turning its options off is not enough on some versions. The log line is
`AddItemFunc detour install deferred: ... signature mismatch`.

If you see that line **without** RandomizerHelper loaded, report it with the log.

### The run starts as a vanilla class

The options string did not take. Check **Misc Options > Randomize starting class loadouts**, then
re-randomize before you create the character.

---

## 5. The game will not start, or crashes

**"Unsupported game version", or the mod stopped working after a Steam update.** Elden Ring
**2.7.1.0** (Steam, 2026-09-08) needs client **v0.6.0.6 or later**. Older clients refuse that exe.
**Do not try to downgrade the game.** Update the client instead (section 3). Your seed keeps
working: a current client connects to seeds generated on 0.5 or later. If you launch through
matt's, also make sure his launcher points at the **new** DLL
([section 4](#updating-our-client-when-you-launch-through-matts)).

To avoid being surprised mid-week, set Elden Ring in Steam to **Properties > Updates > Only update
this game when I launch it**. After a game patch, check the Discord or the release page for a
compatible client before playing.

**It crashes on every launch after an earlier crash.** Take the other parts out one at a time to
find which one is crashing. Close the game, open `ap.me3` in Notepad, and put a `#` in front of each
line of the MapForGoblins entry:

```
# [[natives]]
# path = "MapForGoblins.dll"
```

Then launch again. If it still crashes, restore those lines and try with no Archipelago DLL at all.
If the game crashes even without our DLL, the problem is outside this mod, and the client cannot
write a crash report because it is not loaded. Either way, send the `crash-<pid>.txt` files and the
client log. If you are stuck somewhere that crashes on load, the console's `!warp 11102950` works
while disconnected ([GETTING-UNSTUCK.md](GETTING-UNSTUCK.md#escape-anywhere)).

**"Could not translate RVA to VA" at startup.** On Windows this is a startup race: quit and launch
again, and it usually works. If it happens on every launch, send the log and a list of your other DLL
mods. On Linux/Proton it happens on every launch, because Proton is not supported yet.

**Crashes on 2.7.1.0 (open, clients #671).** Reported so far: heap corruption when quitting to the
main menu, an access violation before connecting, and a crash on a catacomb or boss load. These are
not fixed in any version yet. If it happens, keep the `crash-<pid>.txt` the client writes beside
itself and send it with the log.

**Crash starting a new game after loading a large save on the same seed (open, clients #668).**
Workaround: restart the game before you create a new character for a seed you have already been
playing.

**Crash inside `amdxc64.dll` on AMD graphics (open, #411).** It happens in the overlay's
draw path. Send `crash-<pid>.txt`.

**The log says "LuaWarp ... pinned 2.6.2.0 RVA stale" (open, clients #697).** We have not yet
confirmed whether region-kick warps actually fail on 2.7.1.0, or whether only the message is out of
date. If a kick fails, [GETTING-UNSTUCK.md](GETTING-UNSTUCK.md) `!warp 11102950` takes you back to
the Roundtable. Tell us whether the warp worked.

**The log says the client crashed, but nothing crashed.** Before v0.6.1.5, the log reported a
guarded memory probe as a crash (clients #719). Update to fix it. It was harmless.

**No overlay, nothing connects.** The client is not loaded. With me3, launch through the profile:
`me3 launch --profile "<your folder>\me3\ap.me3"`. With matt's, confirm the main window says
**"Using eldenring_archipelago.dll"**. Either way, the log's `SESSION START` block shows whether the
DLL loaded. If you previously patched the game with UXM, restore vanilla files first. The client
needs the retail exe.

---

## 6. Connecting

**The port is not 38281.** Each room on archipelago.gg gets its own port, printed on the room page.
The shipped `apconfig.json` contains the placeholder `archipelago.gg:PORT`. The client will not
connect until you replace `PORT`, either in the file or in the in-game **Connection** form.

**It worked yesterday and now it will not connect.** archipelago.gg puts a room to sleep after about
two hours without activity. Open the room page to wake it, then **copy the port again**, because a
restarted room can get a new one.

**Refused or timing out.** Test the same address in Archipelago's stock **Text Client**
(`/connect host:port`).

- **The Text Client fails too:** the problem is the room or the network, not the mod.
- **The Text Client connects and the game does not:** something is blocking `eldenring.exe`
  specifically. Elden Ring modding guides often recommend a firewall rule that blocks the exe to keep
  it off FromSoftware's servers, and that rule blocks Archipelago as well. Other candidates are
  antivirus network protection, VPN split tunnelling, and other mods that hook networking. To find a
  Defender rule:

  ```powershell
  Get-NetFirewallApplicationFilter -All | Where-Object { $_.Program -like "*eldenring*" } | Get-NetFirewallRule
  ```

**Typing in the connect box moved your character.** Fixed in v0.6.0.6. On any version, open the
overlay from a menu rather than while moving.

### VERSION MISMATCH in the log

Your client DLL and the host's apworld are from different contracts. The game will still connect,
but the two sides can read the seed data differently. That produces bugs that look real and are not.
Ask the host which apworld version generated the room, then use a client from a compatible release.
Within the 0.6.1 line, any client works with any seed. **Do not report bugs from a mismatched
pair.** A client at v0.6.0.10 or older refuses seeds from v0.6.0.11 and later.

---

## 7. Items, checks, icons and the map

**Every check also gives the vanilla item, or shop checks never fire.** The DLL is not next to its
data tables. See [Do not move the DLL](#1-downloading-and-extracting-the-zip).

**Nothing arrives, but sending works.** `RandomizerHelper.dll`
([section 4](#checks-send-but-nothing-ever-arrives)).

**A pickup, drop or boss did not register.** Enemy and boss drops can fail to set their flag,
especially with enemy randomization, when the enemy that owns the flag never spawns. In the overlay
**Console**, `!check <name>` finds the check and prints a ready-made `!setflag`
([GETTING-UNSTUCK.md](GETTING-UNSTUCK.md#a-check-never-registered)).

**Wrong Tarnished weapon icons, or missing starter-class previews.** You have the old flower atlases
from before 2.7.1.0. They were rebuilt in v0.6.0.6. Reinstall the flower with the bundled installer,
replacing the old atlases. Do not delete a whole shared mod package to get rid of them.

**Shop shelves show the vanilla item's name for someone else's item.** This is known and harmless.
You receive the correct item when you buy it. Only the shelf display is wrong.

**The map shows few pins.** That is the fresh-install default: **F10 > Archipelago > In logic
only** is on, so only checks in regions you can currently reach are pinned. Turn it off to see every
matched check. Unmatched checks are still listed in **F6**. Changes to hidden categories take effect
the next time you open the map.

**Linux: the game loses focus when you hover a map marker.** Turn off **F10 > Marker hover info**
in the MapForGoblins settings. Linux and Proton are not officially supported.

**The tracker says a region is in logic but its graces are dark.** The tracker is optimistic about
Great Rune and Glintstone Key gates (#297). Trust the graces.

**Stuck, out of bounds, missing grace, or the Leyndell gate will not open.** See
[GETTING-UNSTUCK.md](GETTING-UNSTUCK.md). Back up your save before you use it.

---

## 8. Saves, Seamless Co-op and other mods

**With me3:** `ap.me3` saves to a separate file, `AP_me3.sl2`. The first time, me3 fills it with a
**copy** of your normal save, so your vanilla characters appear in the list. That is expected.
Create a **new** character for the seed.

**With matt's launcher:** there is **no** separate save. The AP character goes into your normal
`ER0000.sl2`, alongside your real characters. Back up `%APPDATA%\EldenRing\<steam id>\` before your
first AP launch.

**Either way, do not load a non-AP character while connected.** A character without an Archipelago
marker looks like a fresh AP character, so the client gives it the room's whole item backlog.

### Seamless Co-op, alt saves, and other DLL mods

me3 loads only what `ap.me3` lists. A second profile does not merge with ours, so launching the
Seamless profile gives you Seamless alone, and launching `ap.me3` gives you Archipelago alone.
Add the other mod to **`ap.me3`** as another `[[natives]]` entry, with its files inside `me3\`.
Paths are relative to `ap.me3`.
Seamless Co-op must come **first** and load early:

```
[[natives]]
path = "SeamlessCoop/ersc.dll"
load_early = true

[[natives]]
path = 'eldenring_archipelago.dll'

[[natives]]
path = "MapForGoblins.dll"
```

Copy Seamless's `SeamlessCoop` folder, including its settings `.ini`, next to `ap.me3` so that path
resolves. Community members run this setup, and the pinned Seamless video walks through it. We do
not test it ourselves. When co-op players each have their own slot, set **`region_sync: true` in every co-op player's
yaml** before generating. Without it, a region that only one player has unlocked kicks the others
out. The option is decided at generation and cannot be added to a room that is already running.
`coop_difficulty` is the matching option for enemy toughness.
Two players sharing **one** slot need neither option.

The same pattern loads the **alt saves** DLL (`eldenring_alt_saves.dll`) on matt's path, where you
add it with **Add dll mod** like ours. On the me3 path, `ap.me3` already keeps a separate save.

**Mods that change items are not supported.** That includes item randomizers, item-adding overhauls,
and `RandomizerHelper.dll`. The client keeps a registry of the items it manages, and a mod that adds
or grants items outside it breaks receiving or suppression.

---

## 9. Generating the seed

**"No world found to handle game EldenRing".** This is a v0.1 yaml. The game name is `Elden Ring`,
with a space.

**The seed ignores options I set.** Your yaml uses retired option names. Archipelago warns about
each one, drops it, and uses the default. Start again from this release's `EldenRing.yaml`, or from
<https://peliarch.ca/er/>, and apply your choices again. Read the generation log for "unknown
option" warnings.

**Where is the apworld?** It is an asset on the GitHub release (`eldenring.apworld`), and it is
also inside the player zip. It is not in the repository's file list.

**The apworld will not load, or generation fails even with default settings.** Use
**Archipelago 0.6.7**, and put `eldenring.apworld` in `Archipelago\custom_worlds\`. **Check
`Archipelago\lib\worlds\` and `Archipelago\worlds\` for an older `eldenring.apworld` and delete
it.** An old copy there beside the new one in `custom_worlds\` makes generation fail. Only one
Elden Ring apworld can be installed at a time, because they all register the game as `Elden Ring`.

**Generation fails only when another game is in the multiworld.** Several of these were fixed in
early September on our side, and one needed a repair to the partner's apworld (ALttPR). The
**host** needs the current apworld. Send the generation log, every yaml, and the host's
`custom_worlds` list with your report.

**"I don't see an Elden Ring client in the Archipelago Launcher."** There isn't one, by design.
The client is the DLL in the zip, and it runs inside the game. Generate and host with the normal
Archipelago tools, then connect from the in-game overlay.

**Hints say "Item doesn't exist in multiworld", or a Lock name is rejected.** The room was
generated with an older apworld than your client expects. Hint names follow the apworld that
generated the room. In the overlay, use **F6 > Hint next lock** instead of typing the name.

**The DLC appeared although I did not want it.** `enable_dlc` is **on** by default in the apworld.
The shipped `EldenRing.yaml` turns it off. A blank `Elden Ring: {}` section gets the DLC.

---

## 10. Reporting a problem

Bring these:

- **the client log**, `archipelago-YYYY-MM-DD.log`. It appends launches, so send the whole file and
  say which `=== SESSION START` block is the relevant one.
  - me3: `%LocalAppData%\Programs\garyttierney\me3\log`
  - matt's launcher or another loader: the `log` folder beside `eldenring_archipelago.dll`
- `crash-<pid>.txt`, if the game crashed
- your **yaml** and the **spoiler log**
- **which launcher** you use, and which other DLL mods are loaded
- what you did, what you expected, and what happened

File it at <https://github.com/4laric/er-archipelago/issues>, or post it in the Discord thread.
