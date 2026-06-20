# RegionLock: region-lock not enforced (DLC regions)

**Seed:** 97943139363536579023 · **Slot:** Alaric · **Mode:** Region Lock + DLC Only

## Confirmed gaps (this run)

| Region        | Log area | Lock item   | Lock received? | area_ids | reveal_flags |
|---------------|----------|-------------|----------------|----------|--------------|
| Abyssal Woods | 68600    | Abyssal Lock | no            | `[]`     | `[62084]`    |
| Castle Ensis  | 68200    | Ensis Lock   | no            | `[]`     | `[]`         |

Both entered freely without their lock; neither was kicked. Castle Ensis is worse — it has
**neither** `area_ids` nor a `reveal_flags` entry in `map_region_data.py`
(`"Castle Ensis": {"area_ids": [], "reveal_flags": []}`), so it's invisible to the lock system on
every axis. Same three root causes below apply to both.

---

## First report — Abyssal Woods (area=68600)

**Observed:** 2026-06-16, walked into Abyssal Woods without ever receiving the Abyssal Lock.

## Symptom

Client RegionLock logging shows area transitions but never acts:

```
RegionLock: area=-1       (title/menu)
RegionLock: area=0        (loading)
RegionLock: area=68600    (loaded into Abyssal Woods — no kick)
```

`region_lock` and `dlc_only` are both ON, and the Abyssal Lock was **never sent/received**
(absent from `Archipelago/logs/Server_2026_06_16_21_50_50.txt`). Per AP fill logic the player
should not be in Abyssal Woods, yet nothing removes them. RegionLock only *observes* the area;
it never gates, because it has nothing to gate against.

## Root cause (three independent gaps, any one is sufficient)

1. **No kick data in slot_data.** The active client config `apconfig.json` (slot Alaric, this
   seed) carries only `location_flags` and `sweep_flags` — `areaLockFlags`, `lockRevealFlags`,
   and `lockNotifyItems` are all absent. This is the known slot_data drop (fixed 2026-06-16) but
   the seed was generated 21:50 **without a regen+rebake** carrying the fix, so the client has no
   lock table to enforce.

2. **Abyssal Woods has empty area_ids.** `map_region_data.py`:
   `"Abyssal Woods": {"area_ids": [], "reveal_flags": [62084]}`. Overworld m61 tiles were never
   captured, so even a working kick can't recognize the player is in *locked* Abyssal Woods.
   `62084` is only the map-reveal flag. (`68600` is a location-flag area, not a mapped area_id.)

3. **Enforcement belongs in the baker.** Prior conclusion: physical region-lock walls should be
   EMEVD fog gates in the baker, not a client position/warp kick. The client can't reliably
   kick/warp; observation is all it does here.

## Fix checklist (Abyssal specifically)

- [ ] Regen + rebake this seed with the `areaLockFlags` / `lockRevealFlags` slot_data fix so the
      client actually receives a lock table.
- [ ] Capture Abyssal Woods `area_ids` (in-game place-name capture for the shared m61 overworld
      tiles) and wire them into `map_region_data.py`.
- [ ] Add baker-side fog-gate enforcement (EMEVD `NewEvent` gated on the region-open flag) for the
      real physical wall — client kick is a dead end.

## Takeaway

Free-roaming Abyssal Woods without the lock is a **coverage gap, not enforcement working**. The
`area=68600` log line is RegionLock noticing the area and doing nothing — expected for this
build/seed, not a regression.
