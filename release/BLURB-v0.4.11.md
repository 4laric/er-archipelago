# v0.4.11 — release blurb

**The shelf finally tells you what it's selling.** Since the first shop rework, a merchant
holding more multiworld items than the game had spare name rows collapsed them into one shared
"Archipelago Items" label — you bought blind and checked the tracker afterward. That's over for
every regular merchant: the seed now assigns names so that no two items *on the same shelf* ever
share a row, and the client repaints the menu the moment it opens, so Kalé's stock, a nomad's, and
the Twin Maiden Husks' all read as exactly what they hold. The trick wasn't a bigger pool — it was
noticing that two slots only need different names if you can see them at the same time.

**Eight graces that lit for nobody light now.** Shadow Keep Main Gate, Main Academy Gate, Grand
Lift of Rold, Hidden Path to the Haligtree, Castleward Tunnel, both Limgrave Divine Tower graces,
and Wyndham Catacombs were orphans: a safety gate correctly refused to let the wrong region
force-light them, and nothing ever handed them to the right one. Each now lights with the region
whose ground it stands on. Under `region_grace_unlock: entrance`, Stormveil opens at Castleward
Tunnel and Raya Lucaria at Main Academy Gate — which also means the academy unlock no longer warps
you inside the seal.

**Updating stops being archaeology.** The client now checks the published release feed and tells
you, on screen, whether an update exists and whether it's safe mid-seed — a same-contract update
is a drop-in; a contract move waits for your seed to finish. When it says go, one command
(`update-er-archipelago.ps1`, shipped beside the dll) downloads the release, verifies it, swaps
the payload, backs up what it replaced, and never touches your config, saves, or logs. It is
deliberately never automatic: the banner decides, you run it.

**Playing through matt's randomizer is one command too.** `install-into-matts-rando.ps1` points
the launcher's dll list at the client where it sits — no copying files into anyone else's folders,
and re-running it after an update is the upgrade path. It refuses incomplete bundles and warns
about the one dll known to eat item deliveries.

**Quitting the game no longer risks a crash report.** Quit to menu, quit game — the most correct
exit there is — could abort the process if one of our callbacks read game data mid-teardown.
Every such read now degrades to a log line instead.

And the accumulated table stakes: the Four Belfries Imbued Sword Key chest is a real check again
(the third of four copies, not a phantom duplicate); the Serpent-Hunter's spectral waves belong to
the Rykard fight instead of your inventory; receiving the Crafting Kit actually unlocks crafting;
local pickups that resolve as AP checks play an audio cue; the client backs up your save once per
launch; the goal ledger is on the tracker overlay; the spare-name pool grew 62 → 79 for the menus
that still need every row; and "Region unlocked" says it once, on the edge, not once per tick.

## What you need to update

- **Client:** Required — use the v0.4.11 client with v0.4.11 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.4.11; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** No option was added or
  renamed; note only that `region_grace_unlock: entrance` now uses the canonical doors above.
- **Existing seed/save:** Compatible — keep an active v0.4.10 seed on its matched v0.4.10 pair.
  There is no save migration; just do not mix client and APWorld versions. (Contract unchanged at
  `dc0dc687`; the exact-version handshake still moves.)
- **Profile/assets:** No action.
