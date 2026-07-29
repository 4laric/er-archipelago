"""Tests for the parts of build_ap_icon.py that do NOT need Oodle, witchy or the game.

The atlas is DCX/KRAK, so nothing in a Linux sandbox can open the real input. What CAN be tested is
the pixel work and the guards -- and testing them found a real bug (see the clearing test).

Run: python tools/test_build_ap_icon.py
"""
import importlib.util
import os
import struct
import sys
import tempfile
import unittest

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
        bai.composite(ART, self.sheet, CELL, col, row, out, False)
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
            bai.composite(ART, self.sheet, CELL, 9, 9, os.path.join(self.tmp, "bad.png"), False)


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


if __name__ == "__main__":
    unittest.main()
