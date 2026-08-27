# v0.5.1 — release blurb

## Tarnished Edition, first

Elden Ring updated to 2.7.0.0 on August 27th, and it moved the executable out from under every
address this client reads. Two things about that, and both are good news.

If you don't update, nothing changes: 2.6.2.0 and the Japanese 2.6.2.1 keep working exactly as
they did. If Steam updates you anyway, the old client doesn't crash or eat your save — it puts up
one message box naming your version and both supported ones, then launches the game vanilla with
the mod switched off. That box was built months ago for exactly this morning, and the first
player screenshot of it arrived before we'd even finished patching.

The client that ships with v0.5.1 goes further: it carries a 2.7.0.0 arm derived offline the same
day the patch dropped — 93 addresses re-derived in the engine crate plus 8 of our own — and it has
now survived one real session on the new executable: attach, connect, five items received and read
back, a warp, traps, scaling, and a merchant selling the shuffled wares with the AP flower sitting
in the lineup. One session is one session. The build logs a warning at attach saying the offsets
are derived rather than verified, and every log you send from a 2.7.0.0 run is what retires that
warning. The Japanese Tarnished executable isn't supported yet, and the client says so by name
rather than failing at you.

If you're mid-run and it's going well, the safe play is still to hold Steam off and finish the
run on the version you started it on.

## What you need to update

- **Client:** Required — use the v0.5.1 client with v0.5.1 seeds.
- **APWorld:** Host-only — the room host or generator installs v0.5.1; joining players only need
  the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** Two new options are opt-in
  (`region_sync`, `full_area_sweeps`) and one default moved (`ability_lock_mode`).
- **Existing seed/save:** Compatible — keep an active v0.5.0 seed on its matched v0.5.0 pair.
  There's no save migration, and you shouldn't mix client and APWorld versions.
- **Profile/assets:** No action — no profile or packaged asset changed in this window.
- 🛑 **Check ids moved.** Enia's 100 shop checks left the pool, so every AP id after hers shifts
  down by 100. A spoiler log or an external tracker from a v0.5.0 seed will point at the wrong
  check. Your in-flight seed is fine — it stays on the v0.5.0 pair it was generated for.

## What is in it

**Two of you can share one world now.** Turn on `region_sync` and every Elden Ring slot in the
room unlocks regions together, so the seamless co-op partner riding along in your world stops
getting kicked out of ground you just opened. It's off by default, because in a normal multiworld
two people opening each other's map is the opposite of what you signed up for.

**A boss can hand you the whole area.** siffrin asked whether killing a boss gives you every item
in its region, which it didn't, and `full_area_sweeps` is that question answered yes. It's a big
lever — a legacy dungeon's boss paying out its entire check list changes what a seed feels like
from top to bottom — so it's opt-in and it stays opt-in.

**A locked-attack seed hands you an attack early.** Ability Lock now defaults to `progressive`,
so a run that takes your abilities away gives them back as items you find instead of leaving them
gone for good. And a seed that locks every attack no longer starts you weaponless against the
tutorial — one attack comes back early, up front, so the opening ten minutes are a game rather
than a standoff. A YAML that locks nothing is unaffected, and `ability_lock_mode: static` puts
the old behaviour back.

**You can ask for a Basilisk by writing `Basilisk`.** Spawn Traps took bare character model
numbers and nothing else, sitting right next to an option that takes words, which is how
SwiftyTaco ended up writing ids into the wrong list. It takes names now, in any casing, alongside
the ids it always took; misspell one and it tells you which name you were probably reaching for,
and put a number in the wrong list and it says which list numbers go in. Only 35 enemies have a
name to give — Elden Ring never writes an enemy's name on screen, so for most of the 390 models
there's no name in the game to use, and those stay as numbers rather than as something we made up.

**Enia sells her own wares again.** Her 100 shop rows are out of the randomization pool. They
released on ceremony flags and on holding the right remembrance, so the tracker called them
sphere-1 — reachable from the first minute — while her menu was empty at the start of the run: 100
checks you could see and couldn't buy. That's the shift in check ids, and it's the reason it was
worth paying for.

**Checks are filed by the ground you stand on.** This window ran a full region audit, and the big
piece of it is an instrument: a scan that reads the exact play-region volume a pickup physically
sits inside — the same id the game checks when it kicks you out of a locked region — instead of
guessing from the nearest lit grace. It disagreed with 114 of the 679 checks it can answer
exactly, and 30 of those were real misfilings that moved. J hit one of the symptoms live:
Demi-Human Queen Marigga and the Jagged Peak Drake were promising Gravesite payouts for fights
Gravesite can't reach, and the game kicked him out when he went to collect. Both bosses re-home to
the ground they're fought on, and their own drops came with them. NovahDango caught the other
shape of it: five Abyssal checks crediting a boss you fight in Scadu Altus. A boss handing you
checks from a region you never had to enter is a hard generation failure now, not a hope.

**The wizard's filler percentages track your edits.** Editing a `curated_filler` weight left all
seventeen percentages and the footer describing the recipe you had before the edit, and zeroing
every weight — the empty recipe, no gear and no upgrade economy — kept quoting the shipped
default's shares. It re-shares per keystroke now, and an all-zero recipe reads `--` with a
warning. Thanks to NovahDango for the report.

## What carried over from v0.5.0

Nothing — v0.5.0 shipped everything it documented (the ability lock and its progressive unlocks,
co-op difficulty, `shop_checks`, `armor_bundles`, the Leyndell capital-gate and as-sent Great
Rune fixes, the wider corpse-award sweep, `!check`).

`stable` moved to v0.5.0 when this window opened — the promotion v0.5.0 held back while it was
still an integration branch. Players on the stable channel have the ability lock now.
