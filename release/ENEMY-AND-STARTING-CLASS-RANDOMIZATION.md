# Enemy and Starting Class Randomization -- Use matt's Randomizer. They Stack.

The short answer: this project does not randomize enemies or starting
classes, and it has no plans to -- because you can already have both,
**on top of your Archipelago seed**, by running **thefifthmatt's Elden Ring
Randomizer** alongside it. The two tools compose cleanly. You do not have
to choose.

matt's randomizer is excellent and long-established; enemy shuffle and
starting-class randomization are its territory, and it does them better
than we would by duplicating them. So instead of an apology, here is the
recipe.

Two rules before anything else, because they are the only ways to get this
wrong:

1. **In matt's randomizer, ITEM randomization must be OFF.** Items are this
   project's job. Enemies and starting class are matt's.
2. **Do NOT load `RandomizerHelper.dll`.** It breaks item RECEIVING outright --
   see [When receiving is dead](#when-receiving-is-dead-randomizerhelperdll)
   below. Its auto-equip and auto-upgrade are things we already ship as yaml
   settings, so you are not giving anything up.

## Get it from the author

**Elden Ring Item and Enemy Randomizer** -- thefifthmatt: <https://www.nexusmods.com/eldenring/mods/428>

Download it from that page and nowhere else. We deliberately do **not** bundle it, mirror it,
or ship any of its files: matt's terms ask that the randomizer and its config files not be
redistributed, and that is a request worth honouring. Linking you to the source is both the
correct thing and the safer thing -- you get the current version, with his install notes.

## The recipe: randomized enemies + starting class + Archipelago

1. **Generate your Archipelago seed** as usual (see
   [SETUP.md](SETUP.md), part A). Nothing about it changes.
2. **Run matt's Elden Ring Randomizer** and configure it:
   - Enemy randomization: **ON** (bosses too, if you like).
   - Starting-class randomization: **ON**, if you want it.
   - Item randomization: **OFF**. This is the critical one -- see the
     settings section below.
3. **Let matt's randomizer write its output** the way its own
   instructions describe. It works by rewriting the game's files
   (`regulation.bin` and friends).
4. **Launch the game with the Archipelago runtime client loaded**
   (see [SETUP.md](SETUP.md), part B) and connect to your seed.
5. **Play.** Enemies and your class come from matt's seed; every item
   pickup is still an Archipelago check, and Region Locks still arrive
   from the multiworld.

### Tarnished Edition 1.17: repair Torrent after randomizing

Matt v0.11.4's generated `regulation.bin` predates Elden Ring 1.17 and omits the four new
`RideParam` rows used by Spectral Steed appearances. That can leave Torrent unable to answer the
whistle. After randomizing, follow `TARNISHED-TORRENT-REPAIR.md` and import the bundled Smithbox
delta. It adds only rows `80020`, `80030`, `80040`, and `80050`; it does not replace the table or
touch Matt's randomization.

## Recommended matt's randomizer settings

Paste this into matt's randomizer (**Options -> Set options from string**):

```
bossbgm changestats dlc dlckeysilo earlylegacy earlymedal editnames enemy racemode_health racemode_key racemode_scadu racemode_upgrades v15 bias:0
```

**Note there is no `seed:` on the end.** That is deliberate. A blank seed box means the
randomizer rolls a fresh seed for you when you click **Randomize enemies** -- you get your own
enemy layout, not ours. If your seed box is not blank, clear it.

(With the box empty, matt's ticks "Reroll seed" for you and greys it out. You do not have to do
anything.)

![Item Randomizer OFF -- the tab is unticked and the whole panel is greyed out](screenshots/matt-01-item-randomizer-OFF.png)

**Read the tabs in that picture.** `Item Randomizer` is **unticked** and its entire panel is
greyed out. `Enemy Randomizer` and `DLC` are ticked. That is the configuration that matters, and
it is the one thing you must not get wrong.

The string contains tokens like `racemode_key` and `racemode_upgrades`, which look alarming -- they
are item-randomizer settings. They are **inert**: they are just the item tab's remembered state,
and the item randomizer is off (there is no `item` token in the string). Do not let them tempt
you into ticking the Item Randomizer box.

![Enemy Randomizer ON](screenshots/matt-02-enemy-randomizer-ON.png)

### Misc Options -- where the starting class actually comes from

Starting-class randomization is **not** part of the Item Randomizer. It sits in the **Misc
Options** tab, which is why you still get it with items off.

The string sets it. Confirm it looks like this:

![Misc Options: Randomize starting class loadouts is ticked](screenshots/matt-02b-misc-options-starting-class.png)

The one that matters is **Randomize starting class loadouts**. The others in that group
(starting keepsakes, NPC outfits, ambient music, gestures) are taste -- turn them off if you
would rather they stayed vanilla.

**The options string above sets these for you** -- paste it and Misc Options should already
look like the picture. Glance at it anyway: it costs ten seconds, and it is the one check that
catches a paste that did not take. A run that starts as a vanilla Wretch when you were promised
a random class is a bad way to find out.

## Load the Archipelago client through matt's launcher

You do not run two launchers. matt's randomizer will load our client for you as a dll mod, and
launch the game with both active.

1. Click **Add dll mod**.

   ![The Dll mods dialog](screenshots/matt-03-dll-mods-dialog.png)

2. **Add...** and pick `eldenring_archipelago.dll` **from inside the release's `me3\` folder,
   where it already sits. Point at it -- do not copy or move it.** The dll only works with its
   two data tables (`check_lots_table.json`, `shoplineup_flags.json`) beside it; a copied dll
   leaves them behind, and then checks double-pay the vanilla item and shop checks never fire.

   One habit saves you a broken upgrade later: unpack the release to a folder **without the
   version in its name** (say `ER-Archipelago\`) and overwrite it in place when you update.
   matt's launcher remembers the dll's full path -- if that path has `v0.4.10` in it, the
   launcher will still be loading the v0.4.10 client long after you have downloaded v0.4.11,
   and a mismatched client looks exactly like a broken mod.

   ![Selecting eldenring_archipelago.dll](screenshots/matt-04-select-client-dll.png)

3. It should now be listed, and the main window should read **"Using eldenring_archipelago.dll"**.

   ![The client dll, added](screenshots/matt-05-client-dll-added.png)

4. Click **Randomize enemies**.

   ![Randomize enemies](screenshots/matt-06-randomize-enemies.png)

5. Check the **Overall seed** box is **blank**, then **Launch Elden Ring**.

   ![A blank seed box -- Reroll seed is ticked and greyed out for you](screenshots/matt-07-blank-seed-and-launch.png)

The game starts with matt's enemy randomization baked into the files, and our client running in
memory on top of it. Connect to your Archipelago room as usual.

> ### Add our client to that list and NOTHING ELSE that touches items
>
> The **Dll mods** dialog will happily take more than one entry, and the obvious thing to add
> next is `RandomizerHelper.dll`. Do not. It is the single most common way to end up with a
> connected client that cannot give you anything.


## Your AP items wear a Telescope: the flower icon does not load here either

Same cause as the save, one line further down the same file. `ap.me3` says:

```
[[packages]]
path = 'ap-package'
```

Launch through matt's randomizer and that line is never read, because the profile
is never read. Here is why that is worth two minutes of your time.

**The AP flower is not an item.** It is icon cell 92 -- the vanilla **Telescope**
-- repainted by a texture generated locally under `ap-package\menu`. The client points every
foreign shop slot and every check placeholder at cell 92 whether or not the
repaint got loaded. So on this launcher the pointing still happens, the repaint
does not, and you get a shop full of literal telescopes. A player reported
exactly that on 2026-08-12, having assumed his shops had no AP items in them at
all.

**They did.** Nothing except the picture is affected, because the *names* are
written into memory at runtime and do not depend on the profile:

- A foreign item reads **`AP: <item>`**, with `For: <owner> (<game>)` under it.
  That is the reliable marker on this launcher -- **read the name, not the
  icon**.
- An item for your own world is sold as the real Elden Ring item, with its own
  real name and its own real icon. Those were never telescopes.

**The fix: run the installer against matt's output folder.** From the client bundle:

```powershell
.\install-ap-flower.ps1 -Destination "<matt's output folder>"
```

That locally derives the override from your installed game, so you end up with:

```
<matt's output folder>\menu\hi\01_common.tpf.dcx
<matt's output folder>\menu\low\01_common.tpf.dcx
```

Relaunch. The script refuses to overwrite an unmarked existing atlas unless you explicitly pass
`-Force`, so another loose-file mod cannot silently lose its own menu override.

The same DFLT hi/low override was confirmed in game through standalone ModEngine2 during the
2026-08-17 AP-flower experiment. The installer changes how those confirmed files are constructed,
not where the loader reads them.
> would settle the section.

> ⚠️ **Re-randomizing may undo it.** matt's randomizer writes that folder; if the
> telescopes come back after you click **Randomize enemies** again, copy `menu`
> in again.

**Not sure which folder is his output folder?** The client already tells you.
Open your newest `log\archipelago-<date>.log` and read the first few lines of the
last session:

```
mod stack: THIRD-PARTY DATA MOD at 1 level(s) up (C:\...\me3\randomizer) -- event/, map/, msg/, regulation.bin, script/, sfx/.
```

The path in the brackets is the folder. The client also says outright when the
icon override did not load, and names both folders for you.

## Your save: matt's launcher does not give you a separate one

**What happens.** Our own setup docs tell you the Archipelago run uses its own save file,
`AP_me3.sl2`. That is true, and it is nothing to do with the client -- it comes from one line in
the `me3` profile, `savefile = "AP_me3.sl2"`. Launch through matt's randomizer and you never read
that profile, so the redirection never happens: your Archipelago character is created in your
ordinary Elden Ring save, in a slot next to your real characters.

**Why this is worth acting on, and not just tidiness.** Two reasons.

The first is co-tenancy: from then on your real characters and an Archipelago character share one
file, one backup and one cloud sync, so anything that goes wrong for one goes wrong for all of
them.

The second is sharper. 🛑 **While the client is connected, do not load your ordinary characters.**
The client marks the character it is playing by stamping an identity into that character's save
data, and it uses the absence of a marker to recognise a brand-new Archipelago character. Your
existing characters have no marker either -- they predate the client entirely -- so a connected
client reads them as *fresh*, and a fresh character is owed every item the room has sent so far.
That is the same mechanism that correctly re-grants your start items on a new character; it simply
cannot tell your Limgrave main from a new save. The guard that does exist catches the *other* case:
a character belonging to a **different** Archipelago run is refused outright.

So the rule while you are set up this way is: in the modded launch, play the Archipelago character
and nothing else.

**How to check.** Open Elden Ring the normal way, without any mods, and look at the character
list. If the Archipelago character is in it, you are sharing.

**The fix a player found.** Reported by **boblerrr** (2026-08-03), who hit this and worked out the
remedy himself: add the **alt_saves** dll to your dll folder and hook it in matt's randomizer the
same way you added ours. He reports this worked.

🛑 **We have not tested it.** One player's "it worked" is a strong lead, not a test result. If you
try it, tell us how it went.

**The other approach**, which boblerrr also suggests and thinks is the better one, is to declare
each dll as a native in your own `me3` config and launch with me3 instead -- which puts you back on
a profile that can carry a `savefile` line. Also untested by us.

**If you would rather not bother:** back up your save first. It lives in
`%APPDATA%\EldenRing\<steam id>\`. Copy the folder somewhere before your first Archipelago
launch and the whole question becomes recoverable.


## When receiving is dead: RandomizerHelper.dll

**Symptom fingerprint.** All of these at once, and the combination is diagnostic:

- you connect to the room fine, and **sending works** -- your friends receive your checks;
- **you receive nothing** -- neither from friends nor from your own world;
- a check you open in the world hands you a literal item called **"Archipelago Item"**
  (it looks like a spyglass), and the game says you cannot hold more than one of it and it
  cannot go to storage;
- **you do not start with Torrent**, or with any of your other start items.

If that is what you are seeing, `RandomizerHelper.dll` is loaded. Turning off its auto-equip and
auto-upgrade options is not enough on some versions -- unload the dll.

**Why it happens.** Both mods want the same function. The game has one routine that puts an item
in your inventory, and our client installs a hook on it to deliver everything you receive. That
hook is **fail-closed on purpose**: if the routine's first bytes are not what we expect, we refuse
to install rather than patch something we do not recognise, because guessing wrong in the one
function that grants items is how saves get corrupted. When another dll hooks that routine first,
it overwrites exactly those bytes -- so our install refuses, and every grant afterwards fails.

Checks keep working because they do not use that hook at all: we detect them by watching your
inventory. **That is why the failure is one-directional, and why sending-but-not-receiving is the
fingerprint rather than a coincidence.** The "Archipelago Item" spyglass is the placeholder the
check pays out; normally the client swaps it for your real item, and with the hook refused it just
stays in your hands.

**This is not a bug we can fix from our side**, and it is not matt's fault either -- it is two
mods reaching for one function. Supporting it would mean chaining our hook through a foreign one,
in the routine where a mistake costs you your save. We are not doing that on a guess.

**You are not losing features.** `auto_upgrade` is already a yaml setting on our side, and
`auto_equip` is in progress -- both delivered by the client that is actually aware of your
Archipelago items, which is the part `RandomizerHelper.dll` cannot know about.

**Reporting it.** If you think you have hit this without `RandomizerHelper.dll` loaded, that is
worth a bug report -- send the client log. The line to look for is
`AddItemFunc detour install deferred: ... signature mismatch`.


## Why this composes at all

The two tools do different jobs in different places:

- **matt's randomizer** rewrites the game's files on disk --
  `regulation.bin` and related data -- before you play.
- **This project** is pure-runtime. It modifies **no game files**: it
  reads and writes params in memory while the game runs, through the
  runtime client. Remove the client and your install is exactly as
  matt's randomizer left it.

Because we are not fighting over the same bytes on disk, the two coexist
-- with the one overlap being items, which is why matt's item
randomization must stay off. The projects share no code or data; v0.2 is
a from-scratch, data-derived rebuild. We recommend matt's randomizer
because it is good, not because we depend on it.

## "reroll_enemy_drops" is not enemy randomization

One shipped option (on by default) has a misleading name, so let's be
plain about it: **`reroll_enemy_drops` changes what farmable enemies
drop** -- the repeatable farm drops -- not which enemies exist or where
they stand. Their one-time drops, the actual Archipelago checks, are
untouched. No enemy moves, changes, or gets replaced. It reshapes the
farming economy, nothing more.

Relatedly: **enemy and boss scaling is always on** and keyed to your
progression -- a region you unlock late is tuned tougher, even "early"
territory. That is scaling, not randomization; the enemies are still
whatever your game (vanilla or matt-shuffled) puts there.

## If you run matt's randomizer, leave his scaling boxes UNCHECKED

matt's randomizer has its own enemy scaling, and it exists for a good
reason: when it moves an enemy somewhere new, it adjusts that enemy for
where it now stands. Ours does something different -- it re-tiers every
enemy by how deep its region sits in *your unlock order*.

**Run both and they compound.** We measured this directly, per enemy, in
one session with his scaling off and one with it on:

- his scaling **off**: every enemy's health was exactly what our tier
  predicts from the game's own base values -- we are the only thing
  scaling them, and the numbers land on the unit digit.
- his scaling **on**: health no longer matched that prediction, by a
  factor that differed from enemy to enemy -- around half on the median,
  and much further out at the edges.

His adjustments are written into the game's data before the game starts,
so our client cannot see them or undo them. It applies your progression
tier on top of whatever is already there. Neither tool is wrong; they are
just both doing the job, to the same enemies, without knowing about each
other. The result is difficulty that is hard for anyone to predict --
including us, which is why we tune against the un-checked configuration.

**So: pick one.** If you want his enemy placement with our progression
curve -- the combination this project is built and tested around -- turn
his scaling options off and leave ours alone. If you would rather have his
scaling, that is a legitimate way to play; just know that the difficulty
you get is not the one this project's difficulty options describe, and
reports from that setup are hard for us to act on.

If you have already been playing with both on and the difficulty has felt
erratic -- two enemies side by side wildly apart, an ordinary NPC tougher
than a boss -- this is the most likely reason.

## What this project randomizes instead

- **The item and check layer.** Every item pickup -- corpse loot, chests,
  boss drops, shop slots -- is a check that pays out a shuffled item,
  possibly another player's, in a multiworld.
- **The progression graph itself, via `num_regions`.** The open world is
  carved into regions sealed behind Region Lock items you must *receive*
  from the multiworld; each Lock that arrives opens a region. This is
  the marquee feature -- it turns Elden Ring's go-anywhere map into an
  Archipelago progression puzzle.

For the full mental model of how a run plays, see the
[Player Guide](Elden-Ring-Archipelago-Player-Guide.md).

## See also

- [SETUP.md](SETUP.md) -- installing and generating a seed.
- [Player Guide](Elden-Ring-Archipelago-Player-Guide.md) -- how a run
  actually plays, start to finish.
- [KNOWN-ISSUES.md](KNOWN-ISSUES.md) -- current issues and by-design
  non-features.
