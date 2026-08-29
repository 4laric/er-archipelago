import importlib.util
import hashlib
import struct
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "torrent_rideparam_repair", HERE / "torrent_rideparam_repair.py"
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


class ClassificationTests(unittest.TestCase):
    def test_no_new_rows_is_missing(self):
        self.assertEqual(repair.classify_rows({80000: repair.EXPECTED_BASE_BYTES}), "missing")

    def test_exact_rows_are_current(self):
        rows = {
            row_id: repair._expected_row(def_id)
            for row_id, def_id in repair.TARNISHED_ROWS.items()
        }
        self.assertEqual(repair.classify_rows(rows), "current")

    def test_partial_rows_refuse(self):
        with self.assertRaises(repair.TorrentRepairError):
            repair.classify_rows({80020: repair._expected_row(8002)})

    def test_conflicting_row_refuses(self):
        rows = {
            row_id: repair._expected_row(def_id)
            for row_id, def_id in repair.TARNISHED_ROWS.items()
        }
        rows[80040] = b"x" * repair.ROW_STRUCT.size
        with self.assertRaises(repair.TorrentRepairError) as ctx:
            repair.classify_rows(rows)
        self.assertIn("80040", str(ctx.exception))


def synthetic_param():
    rows = {
        0: bytes(range(repair.ROW_STRUCT.size)),
        80000: repair.EXPECTED_BASE_BYTES,
        300081001: b"z" * repair.ROW_STRUCT.size,
    }
    header = bytearray(repair.HEADER_SIZE)
    row_data_offset = repair.HEADER_SIZE + len(rows) * repair.POINTER_STRUCT.size
    row_names_offset = row_data_offset + len(rows) * repair.ROW_STRUCT.size
    struct.pack_into("<I", header, 0, row_names_offset)
    struct.pack_into("<HHH", header, 6, 1, 1, len(rows))
    struct.pack_into("<q", header, 16, row_names_offset)
    struct.pack_into("<q", header, 48, row_data_offset)
    pointers = b"".join(
        repair.POINTER_STRUCT.pack(row_id, row_data_offset + index * repair.ROW_STRUCT.size, 0)
        for index, row_id in enumerate(rows)
    )
    return bytes(header) + pointers + b"".join(rows.values()) + b"RIDE_PARAM_ST\0"


def synthetic_npc_param(base):
    rows = {
        0: b"a" * repair.NPC_ROW_SIZE,
        repair.NPC_BASE_ROW_ID: base,
        90000000: b"z" * repair.NPC_ROW_SIZE,
    }
    header = bytearray(repair.HEADER_SIZE)
    row_data_offset = repair.HEADER_SIZE + len(rows) * repair.POINTER_STRUCT.size
    row_names_offset = row_data_offset + len(rows) * repair.NPC_ROW_SIZE
    struct.pack_into("<I", header, 0, row_names_offset)
    struct.pack_into("<HHH", header, 6, 1, 1, len(rows))
    struct.pack_into("<q", header, 16, row_names_offset)
    struct.pack_into("<q", header, 48, row_data_offset)
    pointers = b"".join(
        repair.POINTER_STRUCT.pack(
            row_id, row_data_offset + index * repair.NPC_ROW_SIZE, row_names_offset
        )
        for index, row_id in enumerate(rows)
    )
    return bytes(header) + pointers + b"".join(rows.values()) + b"NPC_PARAM_ST\0"


class RawPatchTests(unittest.TestCase):
    def test_adds_exact_rows_and_preserves_existing_bytes(self):
        original = synthetic_param()
        _, old_rows = repair._read_rows(original)
        state, patched = repair.patch_rideparam_bytes(original)
        self.assertEqual(state, "missing")
        _, rows = repair._read_rows(patched)
        for row_id, row in old_rows.items():
            self.assertEqual(rows[row_id], row)
        for row_id, def_id in repair.TARNISHED_ROWS.items():
            self.assertEqual(rows[row_id], repair._expected_row(def_id))

    def test_second_patch_is_byte_identical(self):
        _, once = repair.patch_rideparam_bytes(synthetic_param())
        state, twice = repair.patch_rideparam_bytes(once)
        self.assertEqual(state, "current")
        self.assertEqual(twice, once)

    def test_npc_patch_adds_four_exact_clones_and_is_idempotent(self):
        base = bytearray(b"b" * repair.NPC_ROW_SIZE)
        struct.pack_into("<h", base, repair.NPC_NORMAL_CHANGE_ANIM_OFFSET, -1)
        original_hash = repair.NPC_BASE_SHA256
        repair.NPC_BASE_SHA256 = hashlib.sha256(base).hexdigest()
        try:
            state, once = repair.patch_npcparam_bytes(synthetic_npc_param(bytes(base)))
            self.assertEqual(state, "missing")
            _, rows = repair._read_fixed_rows(once, repair.NPC_ROW_SIZE, "NpcParam")
            expected = repair._expected_npc_row(bytes(base))
            self.assertTrue(all(rows[row_id] == expected for row_id in repair.TARNISHED_NPC_ROWS))
            state, twice = repair.patch_npcparam_bytes(once)
            self.assertEqual(state, "current")
            self.assertEqual(twice, once)
        finally:
            repair.NPC_BASE_SHA256 = original_hash


if __name__ == "__main__":
    unittest.main()
