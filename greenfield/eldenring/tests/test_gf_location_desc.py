# -*- coding: utf-8 -*-
"""Pure tests for greenfield/desc_sources.py -- the location-description waterfall.

No elden_ring_artifacts, no Archipelago: desc_sources is data-injected, so every layer is
exercised with fixtures. Run directly:  python3 eldenring/tests/test_gf_location_desc.py
(Also import-safe under pytest: bare asserts, functions prefixed test_.)
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(HERE)                 # .../eldenring
GREENFIELD = os.path.dirname(GF)           # .../greenfield


def _load():
    p = os.path.join(GREENFIELD, "desc_sources.py")
    spec = importlib.util.spec_from_file_location("desc_sources", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ds = _load()


def test_map_short():
    assert ds.map_short("m20_01_00_00") == "m20_01"
    assert ds.map_short("m60_41_53_00") == "m60_41_53"
    assert ds.map_short("m61_50") == "m61_50"
    assert ds.map_short("m20_00_00_00;m20_01_00_00") == "m20_00"   # multi-map -> first
    assert ds.map_short("") == ""
    assert ds.map_short(None) == ""


def test_clean_treasure_name_keeps_real_places():
    # post-colon place phrase survives
    assert ds.clean_treasure_name("宝箱000：魔術師の塔") == "魔術師の塔"
    assert ds.clean_treasure_name("アイテム光000：星見台") == "星見台"
    # decoration tags + trailing day-tags stripped, phrase kept
    assert ds.clean_treasure_name("【宝死体】0015 ガーゴイル部屋①【day1追加】") == "ガーゴイル部屋①"


def test_clean_treasure_name_drops_noise():
    for junk in ("宝死体062", "c0000_9000", "common90005300", "award",
                 "trigflag9280", "アイテム光000", "貴人_宝死体000", "市民_宝死体001",
                 "宝死体", "", "  ", "0035"):
        assert ds.clean_treasure_name(junk) == "", junk


def test_waterfall_precedence():
    flag = 20007620
    srcs = dict(
        overrides={flag: "East of the smithing table"},
        boss_names={flag: "Dancing Lion"},
        spot_names={flag: "Sorcerer's Tower"},
        nearest_grace={flag: "Belurat, Tower Settlement"},
    )
    # override wins over everything
    assert ds.describe(flag, "treasure", "m20_00_00_00", is_boss=True, **srcs) == "East of the smithing table"
    # remove override -> boss wins (only when tagged boss/remembrance)
    del srcs["overrides"]
    assert ds.describe(flag, "treasure", "m20_00_00_00", is_remembrance=True, **srcs) == "Dancing Lion"
    # not a boss/remembrance -> boss layer skipped, spot wins
    assert ds.describe(flag, "treasure", "m20_00_00_00", **srcs) == "Sorcerer's Tower"
    # remove spot -> nearest grace, prefixed "near "
    del srcs["spot_names"]
    assert ds.describe(flag, "treasure", "m20_00_00_00", **srcs) == "near Belurat, Tower Settlement"
    # remove grace -> locale fallback
    del srcs["nearest_grace"]
    assert ds.describe(flag, "treasure", "m20_01_00_00", **srcs) == "treasure · m20_01"


def test_scadutree_x4_all_distinguishable():
    # the motivating case: 4 Scadutree Fragments, indistinguishable by item name. With grace data
    # each resolves to a different, human descriptor; with none, the map sub-tile still splits them.
    graces = {20007620: "Belurat, Tower Settlement", 20007820: "Belurat, Stagefront",
              20017350: "Belurat, Theatre", 20017470: "Belurat, Walkway"}
    maps = {20007620: "m20_00_00_00", 20007820: "m20_00_00_00",
            20017350: "m20_01_00_00", 20017470: "m20_01_00_00"}
    descs = [ds.describe(f, "treasure", maps[f], nearest_grace=graces) for f in graces]
    assert len(set(descs)) == 4, descs
    # with NO grace data, layer 5 still discriminates by sub-tile (2 tiles here)
    descs2 = [ds.describe(f, "treasure", maps[f]) for f in graces]
    assert set(descs2) == {"treasure · m20_00", "treasure · m20_01"}


def test_locale_always_present_when_map_known():
    # every check with a known map gets *something* even with all sources empty
    assert ds.describe(999, "map_lot", "m12_03_00_00") == "world drop · m12_03"
    # unknown method passes through; unknown map degrades to raw token
    assert ds.describe(999, "weird", "m99_09") == "weird · m99_09"
    # truly nothing known -> None (name stays bare)
    assert ds.describe(999, "", "") is None
    # a shop/hub row (method present, but NO map) stays bare -- self-explanatory, no locale noise
    assert ds.describe(999, "shop", "") is None
    assert ds.describe(999, "shop_multi", None) is None
    # gestures are unique + self-explanatory: no locale even with a map (keeps their exact-name test)
    assert ds.describe(60822, "gesture", "m11_00_00_00") is None
    # ...but a higher layer still names a gesture if one is supplied
    assert ds.describe(60822, "gesture", "m11_00_00_00", overrides={60822: "By the ramparts"}) == "By the ramparts"


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"\n{len(fns)} tests passed")
    sys.exit(0)
