# Handoff — 2026-07-27 (tag closures, honest labels, and a screen that was 84% blind)

**Read §6 first.** Its three predecessors each shipped a central claim that was wrong. This one is
no different in kind: I called a check "fine" after validating the wrong axis, I built a locator on a
premise that did not hold, and I shipped a rule that MEASURED as changing nothing. Everything below
is VERIFIED (and how) or INFERRED.

Heads at writing: world `16dbdb7`, CI **green**. Client unchanged today; gitlink current.
🛑 Do not trust those two lines — `git fetch && git log --oneline -1`, and read the run (§7).

---

## 0. What happened

A full day driven by Alaric playtesting while I worked. Nine of the ten items below came out of him
walking past something and saying "that's wrong". That loop is worth more than any screen I built.

**Landed:** `MajorBoss ⊆ Boss` (a player-facing option value was silently excluding every major
boss) · the arity fix that gave five majors their second drop · 506 guessed regions now SAY they are
guesses · the Twin Maiden Husks removed from 377 seller notes · eight more questline-gated checks
made missable · missable now beats important_locations · the cross-region gate screen given two more
locators · CONTRIBUTING rule 11 · the board reconciled and 13 issues filed.

**v0.2.11 is ready to tag off `16dbdb7`.** CHANGELOG has the entry, plus the v0.2.10 backfill that
was missing entirely. KNOWN-ISSUES refreshed.

## 1. `Boss` was not what a player thinks it is

`important_locations: [Boss]` is a **yaml value**, and it returned 95 checks with Godrick, Rennala,
Radahn, Rykard, Mohg and Malenia all absent. Root: `datamine_boss_drops.py` step (4) discards any
reward whose ITEM NAME contains "remembrance" or "great rune". **That filter is OURS, not the
game's** — `HandleBossDefeatAndDisplayBanner` fires for the majors and the tool finds them before
throwing them away. It is also leaky (Agheel, Magma Wyrm Makkar and Big Red Bear kept the tag purely
because their drop is named something else), which is the tell that a name match was the wrong
instrument.

Fixed as two definitional CLOSURES in `gen_data`, not hand lists, so a new Remembrance/GreatRune
check is picked up automatically. `Boss` 95 → 134, `MajorBoss` 37 → 42. Both gated.

🛑 **The datamine's name filter is still there.** The closure makes the subset hold whatever the
datamine does, but deleting `_is_excluded_item` is the root fix and needs the artifacts.

## 2. The arity bug underneath it

`MajorBoss` was keyed on `method == "boss_arena"` — and `method` records **how we recovered the row**,
not what the drop is. A boss with two drops got the tag on whichever one arrived through that path.
It split five bosses down the middle: Godrick's and Morgott's great runes missed it, Mohg's,
Malenia's and Radahn's remembrances missed it. Same shape as Messmer's Kindling: ONE BOSS, SEVERAL
CHECKS.

⭐ Alaric's mental model — great-rune boss ⊆ remembrance boss ⊆ major ⊆ boss — is right about
**bosses** and does not hold for **checks**, because the tags are on drops. Godrick's Great Rune and
Remembrance of the Grafted are siblings, not nested. Worth keeping straight before someone "fixes"
the sibling relationship.

## 3. The screen that found the bug and then dropped it

`f400191`, the Stormhill Shack Golden Seed, is not there until you have progressed past the
Roundtable. **We spent the previous day on exactly this check and still shipped it miscategorised.**

Nothing was broken. `datamine_lot_gates` found the gate and wrote all three flags to
`lot_gates.tsv`. `test_gf_lot_gates_cross_region` read that table. The screen then resolved a gate
flag's region by decoding its NUMBER — which only works for map-encoded flags — and `continue`d past
every pair it could not decode. `f400191`'s gates are bare 4-digit NPC state ids.

**That is CONTRIBUTING rule 11**, added this session: *the case that motivated the work is the
acceptance test; assert the finished pipeline still reports it, by name.* `f81c9ad` does exactly that
for `f400191`, stage by stage.

Coverage went 17/227 → **126/227** via three locators (map-setter, common call-site, test-site).
Eight new cross-region checks found and marked missable. 🛑 **91 pairs still have no handle**, so
absence from `_QUESTLINE_GATED` is not evidence of safety.

## 4. Labels that claimed more than we know

506 checks had a GUESSED region and displayed it as fact. Alaric hit it on the Tibia Mariner's
Deathroot: `m60_45_39` is a genuine BORDER tile (13 of its labelled checks are Caelid, every western
neighbour is Limgrave) and `tile_pr` answered with the majority. They now carry
`(region unconfirmed)`. The region PREFIX is deliberately untouched — the tracker groups on it and
the client's kick geometry uses the same value.

## 5. The Husks, and the disease behind them

Every bell bearing routes a merchant's stock to the Twin Maiden Husks, so they were a co-seller on
377 wares they do not stock until you find that bearing. Removed where another seller survives.

🛑 **The Husks were the symptom.** `merchant_shops.tsv` over-attributes at BLOCK level: block 1000
claims Gostoc, Sellen and THREE name-states of Bernahl beside the Husks; block 1005 lists Kalé,
"Nomadic Merchant" and an EMPTY name. On block 1000 the shipped rule may be dropping the RIGHT
seller and keeping wrong ones. Filed as #220; root fix is in `datamine_merchant_shops.py`.

## 6. 🛑 What I got wrong. Read this before trusting anything above.

1. **I validated the wrong axis and said "it's fine".** Asked whether the Stormhill Golden Seed was
   correct, I checked its REGION, found it right, and said so. The bug was its REACHABILITY — the
   entire point of the gate work. The region being right is what makes the reachability claim
   dangerous, not what makes it safe.
2. **I shipped a rule that changed nothing.** The principled Husks fix — drop a seller whose row is
   RELEASE-GATED — measured as changing **0 of 548** lists, because the Husks mirror the same row_id
   at `release_flag 0`. I nearly committed it. An empty result is a failure, not a clean run; I only
   caught it because I measured before pushing.
3. **My "the weakest locator carries everything" warning was wrong**, and I gave it confidently. It
   came from an offline simulation that omitted the flag-number decode. The real split is 60 / 55 /
   15. Do not trust a number I derived from a partial reimplementation of a thing that already runs.
4. **The setter-map locator missed the case it was built for.** I assumed every flag is set by some
   map's EMEVD. `3708` is set in `common.emevd $Event(3719)` and tested only in `m11_10`. The
   evidence was in the TEST sites all along.
5. **The principled handle contributed zero.** Routing common-set flags through their
   `$InitializeCommonEvent` call site resolved **0** pairs — `$Event(3719)` is auto-run and has no
   call site. The weak fallback did the work. Build the cheap handle first and measure.
6. **My commit message closed an issue.** "The next sync will CLOSE #194" — GitHub read the keyword
   and shut #194 on push, attributed to Alaric. Outcome was intended; the mechanism was not.
7. **I broke a test by fixing a feature, twice in a row.** Making missable win over important
   flipped `test_reject_progression_accept_filler` green and `test_tagged_reject_filler` red — the
   two assert opposite halves of the same invariant. Check the mirror test before pushing.

## 7. Working notes

- ⭐⭐ **`/sessions` and `/tmp` were both 100% full and I could not free either** (`/sessions` is not
  writable by the agent uid; `/tmp` is sticky and everything is owned by `nobody`). The fix was the
  **outputs mount** — 196 GB free, host-backed — once `allow_cowork_file_delete` enabled unlink
  there. Git works on it; `git update-index --really-refresh` showed zero drift from HEAD, so no
  truncation on that path. **Writes are slow (6.4 MB/s), reads are fine (232 MB/s).**
- 🛑 `/dev/shm` is a 512 MB tmpfs but is **wiped between bash calls** — usable only inside a single
  45s call.
- ⭐ **The CI log needs the PAT and Alaric's session token is enough.** Read it FIRST. Every red run
  today was explained in one fetch.
- `sync_board.py` needs **more than 45s** for a first big sync. It got killed mid-run after all the
  API writes but before writing `cards.json`; recoverable only because it links by the
  `<!-- card:ID -->` marker it stamps. Re-running reported `created=0 updated=0`, which is also the
  idempotency proof.
- Cards may now set `"local": true` — board-only, never mirrored to GitHub.

## 8. Open

1. **Tag v0.2.11 off `16dbdb7`.** CHANGELOG and KNOWN-ISSUES are written. Not a patch release:
   location names changed, so in-flight seeds and trackers will not match.
2. **#217 / #218 — Roderika, and the 621 unplaced rows.** Her Spirit Jellyfish Ashes has a real lot
   and a real region_map row but region `unplaced`, so it never became a check; Sitting Sideways is
   absent from `GESTURE_AWARD_FLAGS` entirely. **`check_maps.tsv` already knows a map for 430 of the
   621.** Instrument that before acting — the earlier "wiring check_maps moves ~1-3 checks"
   measurement was about checks that ALREADY EXIST and does not apply to this set.
3. **#220 — merchant block over-attribution.** See §5.
4. **The 91 no-handle gate pairs.** The screen sees a bit over half the corpus.
5. **`f580600`** (Leda ← Messmer) — still the one real cross-region prerequisite, still unwired.
   Untouched today.
6. **`d4fc247` has still never been swept.** 445 checks left the progression surface and no one has
   run `run_fill_regression` on this tree. This is the largest UNKNOWN risk on the board.
7. **#221 — `f510280`'s co-lot.** The old comment called item `201000` "Banished Knight Oleg ash";
   `201000` is absent from `item_ids.py` and no location names Oleg. Unverified, left as a question.
