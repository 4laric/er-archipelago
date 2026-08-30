# v0.5.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.5.3 client with v0.5.3 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.5.3; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active v0.5.2 seed on its matched v0.5.2 pair.
  There is no save migration; just do not mix client and APWorld versions.
- **Profile/assets:** No action.

## What is in it so far

**The questline-DAG rebuild no longer trips over its existing table on Windows.** The #1085
extractor completed all of its semantic checks, then one local full regen failed while reopening
`questline_dag.tsv` for output. The generator now writes a complete sibling temporary file and
atomically replaces the old table, so it neither opens that destination directly nor leaves a
half-written corpus when replacement fails (#1110).

**The website's update verdict is now a reviewed repository artifact.** `release/latest.json` is
generated from the stable-channel and contract ledgers, checked for drift in CI, and deployed only
after its version, contract, and release URL are verified. The served file remains atomic, but its
exact bytes are now visible in the promotion commit instead of being composed only on the host.

**Tarnished Pack owners can opt its new gear into the pool.** The eight verified player weapons
and shields plus all 18 pieces across the four armor families join as honorary S-tier pool-builder
gear. The toggle defaults off for non-owners; NPC-only weapon bases, Spectral Steed attire unlocks,
and the still-unverified invasion grants remain outside this first #1096 slice. Enabling
the toggle also adds 11 verified limited-stock merchant checks: the Hefty Scimitar, Steel set,
Silver Grooved Shield and set, and Reverse-Bladed Sword. Those checks stay separate from the
Shadow of the Erdtree ownership gate.

The same toggle now adds three verified corpse pickups: Idus Sword near Liurnia Lake Shore, Ritual
Thrusting Shield near the Isolated Merchant's Shack, and Reed Great Katana near Fort Faroth. Their
live 1.17 lot and MSB placements are fully joined; the uncertain invasion rewards and Spectral
Steed attire remain excluded.

**Matt's randomizer can summon Torrent again on Elden Ring 1.17.** Matt's current
`regulation.bin` predates the four new `RideParam` rows and replaces the complete table, which
leaves Torrent unable to answer the whistle. The installer now offers an explicit Torrent-repair
mode that restores only those verified vanilla 1.17 rows. Run it after each randomization, because
Matt rewrites `regulation.bin` whenever it produces a new seed. The same repair is also published
as the standalone `torrent-repair-v1.0.0` utility for players stacking the randomizer without AP.

**Two progression dead ends now explain or prevent themselves.** Sellia's Secret requires the
Unalloyed Gold Needle after Gowry consumes it, so logic no longer permits that same Needle to be
placed behind the route it opens (#1085). In the F6 tracker, the deliberately withheld finale-region
Lock now says that it is automatic and not in the pool, lists the exact requirements still owed,
and confirms when the region opens. Leyndell gets its own compound-gate line showing both
`Leyndell Lock` held/missing and AP Great Runes received/required, followed by open/closed.

**A game update no longer strands the last supported pre-0.5 seed.** The client accepts v0.4.13
only when its exact historical `dc0dc687` contract is present. Every other mismatched version or
contract keeps the existing refusal, so this is a narrow audited bridge for players whose game
updated mid-seed rather than a weakening of paired releases.

Several corpus corrections remove misleading or unreachable work: five worldless Shaded Castle
lots and Stormveil's unsettable Neutralizing Boluses award leave the check list; the Forbidden
Lands pickup trio moves to Mountaintops; thirteen Seethewater/Campsite checks move to Mt. Gelmir;
and 53 unattributed hub-filed checks become filler-only instead of carrying progression from the
always-open Roundtable. The me3 guide also explains that the first `AP_me3.sl2` is copied from the
vanilla save and how to verify that later saves remain separate.

This window opened at the v0.5.2 tag. `CONTRACT_HASH` stays at `13db0b3a` —
`abilityUnlockItems` remains the newest slot-data shape — while the exact-version handshake moves
to 0.5.3. Client half: clients#469.

Final client pin for this draft: `7e18a819` (clients#473, #475, and #476 after the window-opening
clients#469).

## For whoever writes the real one

Keep this about the player-visible work that fills the window. The atomic writer is release
infrastructure: important because it keeps the shipped corpus reproducible, but not the eventual
headline unless the window remains a narrow maintenance release.
