"""Pure board decisions. AP IDs below reserve new synthetic locations, never game flags."""
import hashlib
import random

BINGO_LOCATION_BASE = 7786000
LOCATION_NAMES = {f"Bingo Square {i + 1:02d}": BINGO_LOCATION_BASE + i for i in range(25)}
LINES = tuple(tuple(r * 5 + c for c in range(5)) for r in range(5)) + \
    tuple(tuple(r * 5 + c for r in range(5)) for c in range(5)) + \
    (tuple(i * 6 for i in range(5)), tuple((i + 1) * 4 for i in range(5)))


def has_line(done):
    return any(all(done[i] for i in line) for line in LINES)


def is_complete(done, goal, count):
    return has_line(done) if goal == "line" else sum(done) >= (25 if goal == "blackout" else count)


def select_board(candidates, seed, *, region_limit=None, parents=None, start_pool=(), starts=1):
    """Separate RNG; stable candidates and unique encounter flags, independent of fill calls."""
    candidates = sorted(candidates, key=lambda c: c["flag"])
    if len({c["flag"] for c in candidates}) != len(candidates):
        raise ValueError("bingo candidate encounter flags must be unique")
    if len(candidates) < 25:
        raise ValueError(f"bingo needs 25 eligible boss encounters; only {len(candidates)} remain")
    rng = random.Random(hashlib.sha256(str(seed).encode()).digest())
    if region_limit is None:
        selected = rng.sample(candidates, 25)
    else:
        parents = parents or {}
        def closure(region):
            result = {region}
            while region in parents:
                region = parents[region]
                if region in result:
                    raise ValueError("bingo region parents contain a cycle")
                result.add(region)
            return result
        for _attempt in range(128):
            order = rng.sample(candidates, len(candidates))
            opening = []
            if start_pool:
                for cell in order:
                    if cell["region"] in start_pool and cell["region"] not in {c["region"] for c in opening}:
                        opening.append(cell)
                        if len(opening) == starts:
                            break
                if len(opening) < starts:
                    raise ValueError("bingo start_region_pool needs enough distinct regions with eligible objectives")
            selected, regions = [], set()
            for cell in opening + [c for c in order if c not in opening]:
                needed = regions | closure(cell["region"])
                if len(needed) <= region_limit:
                    selected.append(cell)
                    regions = needed
                if len(selected) == 25:
                    break
            if len(selected) == 25 and all(c in selected for c in opening):
                rng.shuffle(selected)
                break
        else:
            raise ValueError(f"bingo cannot fit 25 objectives in {region_limit} regions; increase bingo_region_limit")
    return [dict(c, location=BINGO_LOCATION_BASE + i) for i, c in enumerate(selected)]
