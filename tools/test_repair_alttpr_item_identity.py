"""Package-preservation and equal-but-distinct item regressions for #1541."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools import repair_alttpr_item_identity as repair

SOURCE = b'''def pot(filleritempool, item):
    filleritempool.remove(item)
def local(filleritempool, item):
    filleritempool.remove(item)
def progression(progitempool, item):
    for i in range(len(progitempool)):
        if progitempool[i] == item and progitempool[i].location:
            progitempool.pop(i)
            break
'''


class Item:
    def __init__(self, name, location=None):
        self.name = name
        self.location = location

    def __eq__(self, other):
        return self.name == other.name


class RepairTests(unittest.TestCase):
    def test_equal_unplaced_copy_survives_both_filler_paths(self):
        before = {}
        exec(SOURCE, before)
        with patch.object(repair, "SOURCE_SHA256", hashlib.sha256(SOURCE).hexdigest()):
            after = {}
            exec(repair.repaired_source(SOURCE), after)
        for name in ("pot", "local", "progression"):
            a, b = Item("Small Heart"), Item("Small Heart", object())
            original = [a, b]
            before[name](original, b)
            if name != "progression":
                self.assertIs(original[0], b)  # witness: equality removed the unplaced copy
            fixed = [a, b]
            after[name](fixed, b)
            self.assertEqual(len(fixed), 1)
            self.assertIs(fixed[0], a)
            self.assertIsNone(fixed[0].location)

    def test_unknown_source_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            repair.repaired_source(SOURCE)

    def test_archive_members_and_original_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            src, dst = Path(temp) / "original.apworld", Path(temp) / "fixed.apworld"
            with ZipFile(src, "w") as z:
                z.comment = b"keep archive comment"
                z.writestr(repair.MEMBER, SOURCE)
                z.writestr("alttpr/unchanged.bin", b"\x00\xffpayload")
            original = src.read_bytes()
            with patch.object(repair, "SOURCE_SHA256", hashlib.sha256(SOURCE).hexdigest()):
                repair.repair(src, dst)
                with self.assertRaises(FileExistsError):
                    repair.repair(src, dst)
            self.assertEqual(src.read_bytes(), original)
            with ZipFile(dst) as z:
                self.assertEqual(z.comment, b"keep archive comment")
                self.assertEqual(z.read("alttpr/unchanged.bin"), b"\x00\xffpayload")
                self.assertNotEqual(z.read(repair.MEMBER), SOURCE)
            with self.assertRaisesRegex(ValueError, "differ"):
                repair.repair(src, src)


if __name__ == "__main__":
    unittest.main()
