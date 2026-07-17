# -*- coding: utf-8 -*-
"""desc_sources.py -- build a human LOCATION DESCRIPTION for every check.

WHY: the in-client tracker (docs/history/SPEC-item-tracker.md) renders each check by its AP
location NAME. gen_data mints that name as ``{region} :: {item} [f{flag}]``. When a region holds
several checks of the SAME vanilla item -- e.g. four ``Scadutree Fragment`` -- the only thing that
separates them is the opaque ``[f<flag>]`` id, so a player staring at four identical rows has no idea
which one to go get. Alaric, 2026-07-17: "the locations need to have descriptions."

WHAT: a single description string, appended by gen_data so the tracker row reads
``{region} :: {item} -- {desc} [f{flag}]`` (the flag is KEPT as a stable, unique tiebreaker; the
description is the human-readable part). ``describe()`` returns that ``desc`` (no flag, no item),
or ``None`` when even the last-resort locale is unknown (then the name stays bare).

PURE + DATA-INJECTED: every source is passed in as a plain dict so this module imports and unit-tests
in the sandbox with NO elden_ring_artifacts and NO Archipelago (see eldenring/tests/test_gf_location_desc.py).
gen_data.py loads the real sources (committed tsvs + the datamined boss tables) and calls describe().

PRIORITY WATERFALL (first non-empty hit wins):
  1. override      location_descriptions.tsv  (flag -> English)     -- hand-authored, always wins
  2. boss          boss/remembrance drop       -> boss/enemy name    -- clean English, from boss tables
  3. spot          treasure_name_en.tsv        (flag -> English)     -- CURATED place phrase (opt-in)
  4. grace         nearest_grace.tsv           (flag -> grace name)  -- coord datamine (Windows regen)
  5. locale        method + map sub-tile                              -- always available, last resort

Layers 3 and 4 are the two that need extra data: layer 3 is a small curated file (most raw
``treasure_name`` values are asset-id noise -- ``award`` / ``c0000_9000`` / ``アイテム光000`` -- not places),
layer 4 needs per-flag coordinates that only exist after a Windows datamine (tools/datamine_item_grace_coords.py
-> tools/build_nearest_grace.py). Until either file exists, gen_data still gives every check a layer-5
locale, so nothing is ever bare.
"""

import re

# Method -> short human verb shown in the locale fallback. Unknown methods pass through verbatim.
_METHOD_HUMAN = {
    "map_lot": "world drop",
    "treasure": "treasure",
    "enemy": "enemy drop",
    "enemy_lot": "enemy drop",
    "shop": "shop",
    "shop_multi": "shop",
    "gesture": "gesture",
    "event": "event",
}

# Methods whose checks are unique + self-explanatory, so the layer-5 locale is suppressed for them
# (higher layers still apply if a source names them). Shops also skip, but naturally -- they carry no
# map, so layer 5 finds no tile. Gestures need to be named explicitly.
_NO_LOCALE_METHODS = {"gesture"}

# Raw map ids (mNN_SS...) -> readable area. Deliberately SMALL + coarse: the region prefix already
# names the area, so this only needs to split same-region sub-tiles apart (Belurat lower vs upper).
# Extend as needed; an unmapped id degrades to the raw ``mNN_SS`` token, which is still a stable
# discriminator. Legacy/DLC interior tiles are the ones worth naming.
_MAP_HUMAN = {}


def map_short(map_id):
    """A short sub-tile token from a raw map id: 'm20_01_00_00' -> 'm20_01'. Overworld m60/m61 tiles
    keep their two grid indices ('m60_41_53'). Returns '' for falsy/garbage so the locale layer can
    drop it cleanly."""
    if not map_id:
        return ""
    m = str(map_id).split(";")[0].strip()  # a multi-map row uses the first
    if not re.match(r"m\d\d", m):           # reject placeholders/non-tiles (PENDING, global, "") -> no locale
        return ""
    parts = m.split("_")
    if len(parts) >= 3 and parts[0][:3] in ("m60", "m61"):
        return "_".join(parts[:3])         # overworld: mNN_XX_YY grid
    if len(parts) >= 2:
        return "_".join(parts[:2])         # legacy/DLC: mNN_SS sub-tile
    return m


# ---- layer 3 helpers: is a raw treasure_name worth curating, and how to pull its place phrase -----
# These are used by tools/build_treasure_name_seed.py to PROPOSE curation candidates; describe()
# itself never reads a raw JP name -- it only reads the curated ENGLISH file. Kept here so the
# junk rule lives next to the waterfall it feeds and the test can pin it.

_ASSET_NOISE = re.compile(
    r"^(?:"
    r"award"                       # enemy-drop award marker
    r"|c\d{4}_\d+"                 # cXXXX_9000 enemy model id
    r"|common\d+"                  # common90005300 shared asset
    r"|trigflag\d+"               # trigflag9280 raw flag echo
    r"|OBJ\d+"                     # object ids
    r")$", re.IGNORECASE)

# Label prefixes that carry no place info on their own (a bare one + digits is noise; anything AFTER
# a colon may still be a real place, handled below).
_BARE_LABELS = ("宝死体", "アイテム光", "宝箱", "貴人", "市民", "異邦人", "宝", "死体")  # 宝死体/アイテム光/宝箱/貴人/市民/異邦人/宝/死体


def clean_treasure_name(raw):
    """Return a candidate place phrase from a raw datamined treasure_name, or '' if it is pure
    asset/numbering noise. This does NOT translate -- it only isolates the human part (usually the
    text after a Japanese full-width colon) so a curator/translator sees signal, not soup.

    '宝箱000：魔術師の塔' -> '魔術師の塔'  (chest 000: Sorcerer's Tower -> Sorcerer's Tower)
    '宝死体062'          -> ''            (treasure-corpse 062 -> noise)
    'c0000_9000'        -> ''            (enemy model id -> noise)
    """
    if not raw:
        return ""
    s = str(raw)
    # drop 【...】 decoration tags and [...]/bracket asides
    s = re.sub(r"【[^】]*】", "", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = s.strip(" 　")
    if not s or _ASSET_NOISE.match(s):
        return ""
    # if there's a colon (full or half width), the place phrase is after it
    for sep in ("：", ":"):
        if sep in s:
            s = s.split(sep)[-1].strip(" 　")
            break
    # strip a leading bare label + any digits/spaces around it
    changed = True
    while changed:
        changed = False
        for lab in _BARE_LABELS:
            if s.startswith(lab):
                s = s[len(lab):].strip(" 　")
                changed = True
        s2 = s.strip("0123456789０１２３４５６７８９ 　_→⇒")
        if s2 != s:
            s = s2
            changed = True
    # left with nothing, or a residual asset token, or only ascii digits/underscores -> noise
    if not s or _ASSET_NOISE.match(s) or re.fullmatch(r"[\W\d_]+", s):
        return ""
    # require at least one CJK ideograph or kana -- a real place phrase has one; leftover latin
    # tokens ('day1', 'OBJ') do not.
    if not re.search(r"[぀-ヿ一-鿿]", s):
        return ""
    return s


def _clean(v):
    return v.strip() if isinstance(v, str) else ""


def describe(flag, method, map_id, *, is_boss=False, is_remembrance=False,
             overrides=None, boss_names=None, spot_names=None,
             nearest_grace=None, map_names=None):
    """Return the human description for a check (no flag, no item), or None.

    ``flag`` is an int. All source args are dicts keyed by that int (except map_names, keyed by the
    short map token). Missing/empty sources are treated as absent, so a partially-populated repo
    (no grace tsv yet, no curated spot names yet) still produces a layer-5 locale for every check.
    """
    overrides = overrides or {}
    boss_names = boss_names or {}
    spot_names = spot_names or {}
    nearest_grace = nearest_grace or {}
    map_names = map_names if map_names is not None else _MAP_HUMAN

    # 1. hand-authored override -- absolute priority
    d = _clean(overrides.get(flag))
    if d:
        return d

    # 2. boss / remembrance -> boss (enemy) name
    if is_boss or is_remembrance:
        d = _clean(boss_names.get(flag))
        if d:
            return d

    # 3. curated English spot name (from the good post-colon place phrases)
    d = _clean(spot_names.get(flag))
    if d:
        return d

    # 4. nearest Site of Grace (coord datamine)
    d = _clean(nearest_grace.get(flag))
    if d:
        return "near " + d

    # 5. locale fallback -- method + map sub-tile. REQUIRES a real map token: it only earns its place
    # when it adds a spatial discriminator. Rows with no map (shop/hub checks, which are self-locating
    # by their merchant/region prefix) get no locale and stay bare -- "some are self-explanatory".
    # Gestures are the same: the seven gesture pickups are unique, named, and self-explanatory, so they
    # skip the locale too (also keeps their exact-name test invariant intact).
    if (method or "").strip() in _NO_LOCALE_METHODS:
        return None
    tok = map_short(map_id)
    if not tok:
        return None
    area = _clean(map_names.get(tok)) or tok
    verb = _METHOD_HUMAN.get((method or "").strip(), (method or "").strip())
    return (verb + " · " + area) if verb else area   # e.g. "treasure · m20_01"
