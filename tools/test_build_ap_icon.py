"""Tests for the parts of build_ap_icon.py that do NOT need Oodle, witchy or the game.

The atlas is DCX/KRAK, so nothing in a Linux sandbox can open the real input. What CAN be tested is
the pixel work and the guards -- and testing them found a real bug (see the clearing test).

Run: python tools/test_build_ap_icon.py
"""
import importlib.util
import hashlib
import os
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bai", os.path.join(HERE, "build_ap_icon.py"))
bai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bai)

try:
    from PIL import Image
except ImportError:                       # pragma: no cover
    Image = None

ART = os.path.join(HERE, "ap_icon_src", "ap_flower.png")
CELL = 160


@unittest.skipIf(Image is None, "Pillow not installed")
@unittest.skipUnless(os.path.isfile(ART), "flower art not present")
class Composite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sheet = os.path.join(self.tmp, "sheet.png")
        Image.new("RGBA", (CELL * 4, CELL * 4), (10, 20, 30, 255)).save(self.sheet)

    def _run(self, col, row):
        out = os.path.join(self.tmp, "out%d%d.png" % (col, row))
        bai.composite_rect(ART, self.sheet, col * CELL, row * CELL, CELL, CELL, out, False)
        return Image.open(out).convert("RGBA")

    def test_the_cell_is_cleared_so_the_vanilla_icon_cannot_bleed_through(self):
        """THE BUG THIS FILE CAUGHT. The flower is mostly transparent between its petals, so a plain
        alpha-composite left the vanilla Telescope visible in the gaps -- a flower with a telescope
        behind it, which is worse than either. Nothing would have errored; it would have shipped."""
        px = self._run(2, 1).load()
        opaque = [px[x, y][:3] for y in range(CELL, 2 * CELL, 3)
                  for x in range(2 * CELL, 3 * CELL, 3) if px[x, y][3] > 200]
        self.assertNotIn((10, 20, 30), opaque,
                         "the old cell contents survive between the petals -- clear the cell first")
        transparent = sum(1 for y in range(CELL, 2 * CELL, 3) for x in range(2 * CELL, 3 * CELL, 3)
                          if px[x, y][3] == 0)
        self.assertGreater(transparent, 0, "an icon cell with no transparency at all is suspicious")

    def test_it_writes_the_requested_cell_and_only_that_cell(self):
        img = self._run(2, 1)
        px = img.load()
        self.assertEqual(img.size, (CELL * 4, CELL * 4), "sheet geometry must not change")
        for probe in ((0, 0), (CELL * 3 + 5, CELL * 3 + 5), (5, CELL * 2 + 5)):
            self.assertEqual(px[probe][:3], (10, 20, 30),
                             "cell at %r was modified; only the target cell may change" % (probe,))

    def test_the_flower_actually_lands(self):
        px = self._run(0, 0).load()
        petals = {(218, 160, 125), (202, 149, 194), (118, 126, 189),
                  (117, 193, 117), (237, 228, 145), (202, 118, 130)}
        found = {px[x, y][:3] for y in range(0, CELL, 3) for x in range(0, CELL, 3)
                 if px[x, y][3] > 200}
        self.assertTrue(found & petals, "no AP petal colour in the target cell -- did the art load?")

    def test_the_art_is_letterboxed_not_stretched(self):
        """2034x2112 art into a square cell: uniform scale + centre, never non-uniform."""
        src = Image.open(ART)
        img = self._run(1, 1).load()
        # a stretched flower would fill the cell edge to edge; a letterboxed one leaves a margin on
        # the narrow axis. Assert the margin exists on the axis the aspect ratio demands.
        self.assertNotEqual(src.width, src.height, "fixture assumption: the art is not square")
        col = [img[CELL + CELL // 2, CELL + y][3] for y in range(CELL)]
        row = [img[CELL + x, CELL + CELL // 2][3] for x in range(CELL)]
        self.assertTrue(row[0] == 0 and row[-1] == 0,
                        "no horizontal margin: the art was stretched to the cell width")
        self.assertTrue(any(col), "the cell is empty")

    def test_out_of_range_refuses_instead_of_clipping(self):
        with self.assertRaises(SystemExit):
            bai.composite_rect(ART, self.sheet, 9 * CELL, 9 * CELL, CELL, CELL,
                               os.path.join(self.tmp, "bad.png"), False)

    def test_the_real_atlas_geometry_from_the_game(self):
        """The rect the game actually gave us: SB_Icon_00, 4096x2048, sprite at 2132,1148 160x160.

        2132 is NOT a multiple of 160 -- the atlas is arbitrarily packed. Any grid model is wrong
        here however the cell size is chosen, which is why the layout is read instead."""
        big = os.path.join(self.tmp, "atlas.png")
        Image.new("RGBA", (4096, 2048), (9, 9, 9, 255)).save(big)
        bai.composite_rect(ART, big, 2132, 1148, 160, 160, big, False)
        px = Image.open(big).convert("RGBA").load()
        petals = {(218, 160, 125), (202, 149, 194), (118, 126, 189),
                  (117, 193, 117), (237, 228, 145), (202, 118, 130)}
        inside = {px[x, y][:3] for y in range(1148, 1308, 3) for x in range(2132, 2292, 3)
                  if px[x, y][3] > 200}
        self.assertTrue(inside & petals, "flower did not land in the real rect")
        self.assertNotIn((9, 9, 9), inside, "vanilla icon bleeds through between the petals")
        self.assertEqual(px[2131, 1148][:3], (9, 9, 9), "wrote one pixel left of the rect")
        self.assertEqual(px[2292, 1307][:3], (9, 9, 9), "wrote past the rect")


class DdsFormat(unittest.TestCase):
    def test_it_reads_a_dx10_header(self):
        import struct
        d = tempfile.mkdtemp()
        p = os.path.join(d, "t.dds")
        h = bytearray(b"DDS " + b"\0" * 144)
        struct.pack_into("<I", h, 28, 11)
        h[84:88] = b"DX10"
        struct.pack_into("<I", h, 128, 98)
        with open(p, "wb") as fh:
            fh.write(bytes(h))
        self.assertEqual(bai.dds_format(p), ("DX10", 98, 11))


class DdsHeader(unittest.TestCase):
    def test_height_and_width_are_not_swapped(self):
        """DDS stores HEIGHT before WIDTH. Getting this backwards silently transposes the grid."""
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "t.dds")
        with open(p, "wb") as fh:
            fh.write(b"DDS " + struct.pack("<III", 124, 0, 256) + struct.pack("<I", 512) + b"\0" * 204)
        self.assertEqual(bai.dds_size(p), (512, 256))

    def test_a_non_dds_returns_none_rather_than_garbage(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "n.bin")
        with open(p, "wb") as fh:
            fh.write(b"NOPE" + b"\0" * 64)
        self.assertIsNone(bai.dds_size(p))


class InstalledGameInputs(unittest.TestCase):
    def test_oodle_is_discovered_beside_the_game_menu(self):
        root = tempfile.mkdtemp()
        menu = os.path.join(root, "menu")
        os.makedirs(menu)
        dll = os.path.join(root, "oo2core_6_win64.dll")
        with open(dll, "wb") as fh:
            fh.write(b"player-owned fixture")
        self.assertEqual(bai.find_oodle(menu), dll)

    def test_missing_installed_oodle_fails_before_witchy(self):
        root = tempfile.mkdtemp()
        menu = os.path.join(root, "menu")
        os.makedirs(menu)
        with self.assertRaises(SystemExit):
            bai.find_oodle(menu)


class DfltOutput(unittest.TestCase):
    def test_manifest_is_rewritten_from_krak_to_dflt(self):
        root = tempfile.mkdtemp()
        manifest = os.path.join(root, "_witchy-tpf.xml")
        with open(manifest, "w", encoding="utf-8") as fh:
            fh.write("<tpf><compression>DCX_KRAK</compression><compressionLevel>6</compressionLevel>"
                     "<oodleCompressorType>KRAK</oodleCompressorType></tpf>")
        self.assertEqual(bai.force_dflt_manifest(root), manifest)
        out = ET.parse(manifest).getroot()
        self.assertEqual(out.findtext("compression"), "DCX_DFLT")
        self.assertIsNone(out.find("compressionLevel"))
        self.assertIsNone(out.find("oodleCompressorType"))
        self.assertEqual(out.findtext("dfltUnk04"), "69632")
        self.assertEqual(out.findtext("dfltUnk38"), "21")

    def test_ambiguous_manifests_are_rejected(self):
        root = tempfile.mkdtemp()
        for name in ("a.xml", "b.xml"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
                fh.write("<tpf><compression>DCX_KRAK</compression></tpf>")
        with self.assertRaises(SystemExit):
            bai.force_dflt_manifest(root)

    def test_repacked_header_must_identify_dflt(self):
        root = tempfile.mkdtemp()
        dflt = os.path.join(root, "dflt.dcx")
        krak = os.path.join(root, "krak.dcx")
        raw = os.path.join(root, "raw.bin")
        with open(dflt, "wb") as fh:
            fh.write(b"DCX\0" + b"x" * 20 + b"DCP\0DFLT" + b"x" * 20)
        with open(krak, "wb") as fh:
            fh.write(b"DCX\0" + b"x" * 20 + b"DCP\0KRAK" + b"x" * 20)
        with open(raw, "wb") as fh:
            fh.write(b"not a dcx")
        self.assertEqual(bai.dcx_codec(dflt), "DFLT")
        self.assertEqual(bai.dcx_codec(krak), "KRAK")
        self.assertIsNone(bai.dcx_codec(raw))


class Bc7Splice(unittest.TestCase):
    def _dds(self, width=16, height=8, mips=1, dxgi=98):
        root = tempfile.mkdtemp()
        path = os.path.join(root, "atlas.dds")
        header = bytearray(b"DDS " + b"\0" * 144)
        struct.pack_into("<I", header, 12, height)
        struct.pack_into("<I", header, 16, width)
        struct.pack_into("<I", header, 28, mips)
        header[84:88] = b"DX10"
        struct.pack_into("<I", header, 128, dxgi)
        blocks = (width // 4) * (height // 4) * 16
        with open(path, "wb") as fh:
            fh.write(header)
            fh.write(b"V" * blocks)
        return path

    def test_only_the_requested_bc7_blocks_are_replaced(self):
        dds = self._dds()
        payload = os.path.join(os.path.dirname(dds), "flower.bc7")
        with open(payload, "wb") as fh:
            fh.write(b"F" * 64)  # 8x8 = 2x2 BC7 blocks
        self.assertEqual(bai.splice_bc7_payload(dds, payload, 4, 0, 8, 8), 64)
        with open(dds, "rb") as fh:
            data = fh.read()[148:]
        self.assertEqual(data[0:16], b"V" * 16)
        self.assertEqual(data[16:48], b"F" * 32)
        self.assertEqual(data[48:80], b"V" * 32)
        self.assertEqual(data[80:112], b"F" * 32)
        self.assertEqual(data[112:128], b"V" * 16)

    def test_wrong_format_mips_and_payload_size_fail_closed(self):
        root = tempfile.mkdtemp()
        payload = os.path.join(root, "bad.bc7")
        with open(payload, "wb") as fh:
            fh.write(b"x")
        for dds in (self._dds(dxgi=77), self._dds(mips=2), self._dds()):
            with self.assertRaises(SystemExit):
                bai.splice_bc7_payload(dds, payload, 4, 0, 8, 8)

    def test_committed_payload_is_exactly_the_owned_160px_cell(self):
        payload = os.path.join(HERE, "ap_icon_src", "ap_flower_160.bc7")
        with open(payload, "rb") as fh:
            data = fh.read()
        self.assertEqual(len(data), 40 * 40 * 16)
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "b26be52daaec18149470383e8f9fda60234a300617b596bfb15aa3c0373ec5e6")


class SpriteLookup(unittest.TestCase):
    """iconId -> texture+rect from the sprite layout, not from grid arithmetic.

    The first --probe run against the real game falsified the grid model: the atlases are 4096x2048,
    the default cell 160 divided neither axis, and the sheets are irregular (SB_Icon_02, _02_A,
    _02_B, _03, _03_A, _07_dlc, _07_dlc_A) so "icon N is at sheet N//per_sheet" cannot hold either.
    01_common.sblytbnd.dcx names each sprite's texture and rect, so we read it.
    """

    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, "01_common.layout"), "w") as fh:
            fh.write('<?xml version="1.0"?><Layout>'
                     '<SubTexture name="MENU_ItemIcon_00092.png" x="2132" y="1148" width="160" height="160"/>'
                     '<SubTexture name="MENU_ItemIcon_00920.png" x="0" y="0" width="160" height="160"/>'
                     '<SubTexture name="MENU_ItemIcon_00192.png" x="64" y="0" width="160" height="160"/>'
                     '<SubTexture name="MENU_ItemIcon_00093.png" x="384" y="512" width="160" height="160"/>'
                     '</Layout>')

    def test_it_finds_the_zero_padded_id(self):
        hits = bai.find_sprite(self.d, 92)
        self.assertEqual(len(hits), 1, "expected exactly one sprite for icon 92, got %r" % (hits,))
        self.assertEqual(hits[0][2]["name"], "MENU_ItemIcon_00092.png")

    def test_a_dimension_equal_to_the_id_is_not_a_match(self):
        """REAL DATA, real false positives. The first probe against the game matched
        MENU_MAP_DropSoul and MENU_FL_SlotBase_Shop -- because their HEIGHT is 92 -- and in the low
        bundle a dozen SB_BigRunes sprites (height 92) crowded the true entry past the truncation.
        An id lives in the NAME; a dimension that happens to equal it is noise."""
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "SB_MapCursor_02.layout"), "w") as fh:
            fh.write('<T><SubTexture half="0" height="92" name="MENU_MAP_DropSoul.png" '
                     'width="86" x="800" y="1921"/></T>')
        with open(os.path.join(d, "SB_Icon_00.layout"), "w") as fh:
            fh.write('<T><SubTexture half="0" height="160" name="MENU_ItemIcon_00092.png" '
                     'width="160" x="2132" y="1148"/></T>')
        hits = bai.find_sprite(d, 92)
        self.assertEqual([h[2]["name"] for h in hits], ["MENU_ItemIcon_00092.png"])
        self.assertTrue(hits[0][3], "the ItemIcon match must be flagged exact")

    def test_the_real_rect_from_the_game_is_parsed(self):
        """Pinned from the actual sblytbnd (hi bundle, 2026-07-29). If a future parse change stops
        producing THIS, the tool would silently target a different rect."""
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "SB_Icon_00.layout"), "w") as fh:
            fh.write('<T><SubTexture half="0" height="160" name="MENU_ItemIcon_00092.png" '
                     'width="160" x="2132" y="1148"/></T>')
        fn, _tag, a, exact = bai.find_sprite(d, 92)[0]
        self.assertEqual(fn, "SB_Icon_00.layout")
        self.assertEqual((a["x"], a["y"], a["width"], a["height"]), ("2132", "1148", "160", "160"))
        self.assertTrue(exact)

    def test_neighbouring_ids_do_not_false_match(self):
        """92 must not match 920, 192 or 093. A substring match here paints the flower over an
        unrelated item and nothing errors -- the exact silent-wrong-answer shape."""
        names = {h[2].get("name") for h in bai.find_sprite(self.d, 92)}
        for near in ("MENU_ItemIcon_00920.png", "MENU_ItemIcon_00192.png", "MENU_ItemIcon_00093.png"):
            self.assertNotIn(near, names, "%s false-matched icon 92" % near)

    def test_an_absent_id_returns_nothing_rather_than_the_nearest(self):
        self.assertEqual(bai.find_sprite(self.d, 4242), [])


if __name__ == "__main__":
    unittest.main()
