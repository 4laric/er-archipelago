#!/usr/bin/env python3
"""Add Elden Ring 1.17's four Spectral Steed RideParam rows to a regulation.bin.

Only the RideParam binder entry is decoded and rewritten. Every other binder entry stays as
the original raw bytes; this matters for randomizer regulations, which can contain duplicate
row IDs that a whole-regulation typed round trip would collapse.
"""
from __future__ import annotations

import datetime
import shutil
import struct
import sys
import tempfile
from pathlib import Path


REGULATION_NAME = "regulation.bin"
BASE_ROW_ID = 80000
TARNISHED_ROWS = {80020: 8002, 80030: 8003, 80040: 8004, 80050: 8005}
ROW_STRUCT = struct.Struct("<7i6f12s")
EXPECTED_BASE_BYTES = ROW_STRUCT.pack(
    0, 8000, 3010, 0, 0, 900, -1, 180.0, 5.0, 5.0, 5.0, -180.0, 180.0, b"\0" * 12
)
HEADER_SIZE = 64
POINTER_STRUCT = struct.Struct("<i4xqq")


class TorrentRepairError(RuntimeError):
    pass


def _expected_row(def_chr_id: int) -> bytes:
    row = bytearray(EXPECTED_BASE_BYTES)
    struct.pack_into("<i", row, 4, def_chr_id)
    return bytes(row)


def classify_rows(rows: dict[int, bytes]) -> str:
    """Return missing/current, or refuse partial/conflicting input."""
    present = {row_id for row_id in TARNISHED_ROWS if row_id in rows}
    if not present:
        return "missing"
    if present != set(TARNISHED_ROWS):
        raise TorrentRepairError(
            "RideParam has only some Tarnished rows (%s); refusing a mixed-state repair."
            % ", ".join(map(str, sorted(present)))
        )
    for row_id, def_chr_id in TARNISHED_ROWS.items():
        if rows[row_id] != _expected_row(def_chr_id):
            raise TorrentRepairError(
                "RideParam row %d already exists but conflicts with the verified 1.17 row" % row_id
            )
    return "current"


def _load_soulstruct():
    install_hint = (
        "--with-torrent-repair requires Soulstruct 2.3.2 with its ParamCrypt metadata. "
        "The PyPI 2.3.2 wheel omitted that metadata; install the fixed source commit with:\n"
        "  py -m pip install \"soulstruct @ "
        "git+https://github.com/Grimrukh/soulstruct.git@d59dc41e\""
    )
    try:
        from soulstruct.base.params.ParamCrypt import ParamCrypt
        from soulstruct.containers import Binder
    except ImportError as exc:
        raise TorrentRepairError(install_hint) from exc
    paramcrypt_dir = Path(sys.modules[ParamCrypt.__module__].__file__).parent
    metadata = ("ParamCrypt.deps.json", "ParamCrypt.runtimeconfig.json")
    if any(not (paramcrypt_dir / name).is_file() for name in metadata):
        raise TorrentRepairError(install_hint)
    return ParamCrypt, Binder


def _read_rows(data: bytes) -> tuple[list[tuple[int, int, int]], dict[int, bytes]]:
    """Read this one known ER long-offset PARAM shape without interpreting its row fields."""
    if len(data) < HEADER_SIZE:
        raise TorrentRepairError("RideParam is shorter than its 64-byte header")
    row_names_offset = struct.unpack_from("<I", data, 0)[0]
    row_count = struct.unpack_from("<H", data, 10)[0]
    row_data_offset = struct.unpack_from("<q", data, 48)[0]
    if row_data_offset != HEADER_SIZE + row_count * POINTER_STRUCT.size:
        raise TorrentRepairError("RideParam does not use the verified Elden Ring long-offset shape")
    pointers = [
        POINTER_STRUCT.unpack_from(data, HEADER_SIZE + index * POINTER_STRUCT.size)
        for index in range(row_count)
    ]
    offsets = [pointer[1] for pointer in pointers]
    if offsets != sorted(offsets) or len(set(offsets)) != len(offsets):
        raise TorrentRepairError("RideParam row data offsets are not strictly increasing")
    ends = offsets[1:] + [row_names_offset]
    if any(end - start != ROW_STRUCT.size for start, end in zip(offsets, ends)):
        raise TorrentRepairError("RideParam rows are not the verified 64-byte shape")
    rows = {row_id: data[start:end] for (row_id, start, _), end in zip(pointers, ends)}
    if len(rows) != row_count:
        raise TorrentRepairError("RideParam contains duplicate row IDs; refusing to rewrite it")
    return pointers, rows


def patch_rideparam_bytes(data: bytes) -> tuple[str, bytes]:
    """Return missing/current and a byte-preserving RideParam payload."""
    pointers, rows = _read_rows(data)
    state = classify_rows(rows)
    if state == "current":
        return state, data
    if rows.get(BASE_ROW_ID) != EXPECTED_BASE_BYTES:
        raise TorrentRepairError("RideParam base row 80000 is not the verified 1.17 shape")

    base_index = next(index for index, pointer in enumerate(pointers) if pointer[0] == BASE_ROW_ID)
    base_offset = pointers[base_index][1]
    pointer_growth = len(TARNISHED_ROWS) * POINTER_STRUCT.size
    row_growth = len(TARNISHED_ROWS) * ROW_STRUCT.size
    total_growth = pointer_growth + row_growth

    header = bytearray(data[:HEADER_SIZE])
    struct.pack_into("<H", header, 10, len(pointers) + len(TARNISHED_ROWS))
    row_names_offset = struct.unpack_from("<I", header, 0)[0]
    struct.pack_into("<I", header, 0, row_names_offset + total_growth)
    param_type_offset = struct.unpack_from("<q", header, 16)[0]
    struct.pack_into("<q", header, 16, param_type_offset + total_growth)
    struct.pack_into("<q", header, 48, struct.unpack_from("<q", header, 48)[0] + pointer_growth)

    adjusted = []
    for row_id, original_data_offset, name_offset in pointers:
        data_offset = original_data_offset + pointer_growth
        if original_data_offset > base_offset:
            data_offset += row_growth
        if name_offset:
            name_offset += total_growth
        adjusted.append((row_id, data_offset, name_offset))

    base_new_offset = base_offset + pointer_growth
    new_pointers = [
        (row_id, base_new_offset + (index + 1) * ROW_STRUCT.size, 0)
        for index, row_id in enumerate(TARNISHED_ROWS)
    ]
    adjusted[base_index + 1:base_index + 1] = new_pointers
    packed_pointers = b"".join(POINTER_STRUCT.pack(*pointer) for pointer in adjusted)

    base_end = base_offset + ROW_STRUCT.size
    new_rows = b"".join(_expected_row(def_chr_id) for def_chr_id in TARNISHED_ROWS.values())
    payload = data[HEADER_SIZE + len(pointers) * POINTER_STRUCT.size:]
    insert_at = base_end - (HEADER_SIZE + len(pointers) * POINTER_STRUCT.size)
    patched = bytes(header) + packed_pointers + payload[:insert_at] + new_rows + payload[insert_at:]
    _, verified_rows = _read_rows(patched)
    classify_rows(verified_rows)
    for row_id, row in rows.items():
        if verified_rows[row_id] != row:
            raise TorrentRepairError("existing RideParam row %d changed during repair" % row_id)
    return state, patched


def repair_regulation(regulation_path: Path) -> tuple[str, Path | None]:
    """Patch one regulation atomically. Returns (missing/current result, backup path)."""
    regulation_path = regulation_path.resolve()
    if not regulation_path.is_file():
        raise TorrentRepairError("regulation.bin not found at %s" % regulation_path)

    ParamCrypt, Binder = _load_soulstruct()
    with tempfile.TemporaryDirectory(prefix="ap-torrent-repair-") as temp_name:
        temp = Path(temp_name)
        decrypted_in = temp / "input.parambnd.dcx"
        decrypted_out = temp / "output.parambnd.dcx"
        encrypted_out = temp / REGULATION_NAME
        ParamCrypt(regulation_path, "decrypt", "er", decrypted_in)
        binder = Binder.from_path(decrypted_in)
        try:
            entry = next(e for e in binder.entries if e.name.endswith("RideParam.param"))
        except StopIteration as exc:
            raise TorrentRepairError("RideParam.param is absent from %s" % regulation_path) from exc

        original_entries = {e.entry_id: e.data for e in binder.entries}
        state, patched_ride = patch_rideparam_bytes(entry.data)
        if state == "current":
            return state, None
        entry.set_uncompressed_data(patched_ride)
        changed_ids = [e.entry_id for e in binder.entries if e.data != original_entries[e.entry_id]]
        if changed_ids != [entry.entry_id]:
            raise TorrentRepairError(
                "Soulstruct changed binder entries besides RideParam: %s" % changed_ids
            )

        binder.write(decrypted_out)
        ParamCrypt(decrypted_out, "encrypt", "er", encrypted_out)

        verify_dcx = temp / "verify.parambnd.dcx"
        ParamCrypt(encrypted_out, "decrypt", "er", verify_dcx)
        verified = Binder.from_path(verify_dcx)
        verified_entries = {e.entry_id: e for e in verified.entries}
        for entry_id, data in original_entries.items():
            if entry_id != entry.entry_id and verified_entries[entry_id].data != data:
                raise TorrentRepairError(
                    "verification found an unrelated binder entry changed (ID %d)" % entry_id
                )
        verified_state, verified_ride = patch_rideparam_bytes(verified_entries[entry.entry_id].data)
        if verified_state != "current" or verified_ride != patched_ride:
            raise TorrentRepairError("written regulation did not retain the exact RideParam patch")

        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = regulation_path.with_name(regulation_path.name + ".bak-ap-torrent-" + stamp)
        shutil.copy2(regulation_path, backup)
        staged = regulation_path.with_name(regulation_path.name + ".ap-torrent-new")
        try:
            shutil.copy2(encrypted_out, staged)
            staged.replace(regulation_path)
        finally:
            if staged.exists():
                staged.unlink()
        return state, backup
