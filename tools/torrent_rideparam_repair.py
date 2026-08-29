#!/usr/bin/env python3
"""Add Elden Ring 1.17's four Spectral Steed RideParam rows to a regulation.bin.

Only the RideParam binder entry is decoded and rewritten. Every other binder entry stays as
the original raw bytes; this matters for randomizer regulations, which can contain duplicate
row IDs that a whole-regulation typed round trip would collapse.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import shutil
import struct
import sys
import tempfile
from pathlib import Path


REGULATION_NAME = "regulation.bin"
BASE_ROW_ID = 80000
TARNISHED_ROWS = {80020: 8002, 80030: 8003, 80040: 8004, 80050: 8005}
TARNISHED_NPC_ROWS = (80020000, 80030000, 80040000, 80050000)
ROW_STRUCT = struct.Struct("<7i6f12s")
EXPECTED_BASE_BYTES = ROW_STRUCT.pack(
    0, 8000, 3010, 0, 0, 900, -1, 180.0, 5.0, 5.0, 5.0, -180.0, 180.0, b"\0" * 12
)
HEADER_SIZE = 64
POINTER_STRUCT = struct.Struct("<i4xqq")
NPC_ROW_SIZE = 736
NPC_BASE_ROW_ID = 80000000
NPC_BASE_SHA256 = "2a1d3329d74380882af14c37061939a3214775cbb939c3d4e286c1538f4ff3d8"
NPC_NORMAL_CHANGE_ANIM_OFFSET = 460


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
        "git+https://github.com/Grimrukh/soulstruct.git@d59dc41e\"\n"
        "Or use install-into-matts-rando.ps1 for guided setup."
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


def _read_fixed_rows(
    data: bytes, row_size: int, param_name: str
) -> tuple[list[tuple[int, int, int]], dict[int, bytes]]:
    """Read this one known ER long-offset PARAM shape without interpreting its row fields."""
    if len(data) < HEADER_SIZE:
        raise TorrentRepairError("%s is shorter than its 64-byte header" % param_name)
    row_names_offset = struct.unpack_from("<I", data, 0)[0]
    row_count = struct.unpack_from("<H", data, 10)[0]
    row_data_offset = struct.unpack_from("<q", data, 48)[0]
    if row_data_offset != HEADER_SIZE + row_count * POINTER_STRUCT.size:
        raise TorrentRepairError(
            "%s does not use the verified Elden Ring long-offset shape" % param_name
        )
    pointers = [
        POINTER_STRUCT.unpack_from(data, HEADER_SIZE + index * POINTER_STRUCT.size)
        for index in range(row_count)
    ]
    offsets = [pointer[1] for pointer in pointers]
    if offsets != sorted(offsets) or len(set(offsets)) != len(offsets):
        raise TorrentRepairError("%s row data offsets are not strictly increasing" % param_name)
    ends = offsets[1:] + [row_names_offset]
    if any(end - start != row_size for start, end in zip(offsets, ends)):
        raise TorrentRepairError(
            "%s rows are not the verified %d-byte shape" % (param_name, row_size)
        )
    rows = {row_id: data[start:end] for (row_id, start, _), end in zip(pointers, ends)}
    if len(rows) != row_count:
        raise TorrentRepairError(
            "%s contains duplicate row IDs; refusing to rewrite it" % param_name
        )
    return pointers, rows


def _read_rows(data: bytes) -> tuple[list[tuple[int, int, int]], dict[int, bytes]]:
    return _read_fixed_rows(data, ROW_STRUCT.size, "RideParam")


def patch_rideparam_bytes(data: bytes) -> tuple[str, bytes]:
    """Return missing/current and a byte-preserving RideParam payload."""
    pointers, rows = _read_rows(data)
    state = classify_rows(rows)
    if state == "current":
        base_name = next(pointer[2] for pointer in pointers if pointer[0] == BASE_ROW_ID)
        if all(
            next(pointer[2] for pointer in pointers if pointer[0] == row_id) == base_name
            for row_id in TARNISHED_ROWS
        ):
            return state, data
        repaired = bytearray(data)
        for index, pointer in enumerate(pointers):
            if pointer[0] in TARNISHED_ROWS:
                POINTER_STRUCT.pack_into(
                    repaired, HEADER_SIZE + index * POINTER_STRUCT.size,
                    pointer[0], pointer[1], base_name,
                )
        return "pointer-repair", bytes(repaired)
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
    base_name_offset = adjusted[base_index][2]
    new_pointers = [
        (row_id, base_new_offset + (index + 1) * ROW_STRUCT.size, base_name_offset)
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


def _expected_npc_row(base: bytes) -> bytes:
    row = bytearray(base)
    struct.pack_into("<h", row, NPC_NORMAL_CHANGE_ANIM_OFFSET, 8000)
    return bytes(row)


def patch_npcparam_bytes(data: bytes) -> tuple[str, bytes]:
    """Add c8002-c8005's NpcParam rows, cloned from verified vanilla c8000."""
    pointers, rows = _read_fixed_rows(data, NPC_ROW_SIZE, "NpcParam")
    base = rows.get(NPC_BASE_ROW_ID)
    if base is None:
        raise TorrentRepairError("NpcParam base Torrent row 80000000 is absent")
    if hashlib.sha256(base).hexdigest() != NPC_BASE_SHA256:
        raise TorrentRepairError("NpcParam base Torrent row 80000000 is not the verified 1.17 row")
    expected = _expected_npc_row(base)
    present = {row_id for row_id in TARNISHED_NPC_ROWS if row_id in rows}
    if present and present != set(TARNISHED_NPC_ROWS):
        raise TorrentRepairError("NpcParam has only some Tarnished Torrent rows; refusing repair")
    if present:
        conflicts = [row_id for row_id in TARNISHED_NPC_ROWS if rows[row_id] != expected]
        if conflicts:
            raise TorrentRepairError("NpcParam has conflicting Tarnished rows: %s" % conflicts)
        return "current", data

    base_index = next(
        index for index, pointer in enumerate(pointers) if pointer[0] == NPC_BASE_ROW_ID
    )
    base_offset = pointers[base_index][1]
    pointer_growth = len(TARNISHED_NPC_ROWS) * POINTER_STRUCT.size
    row_growth = len(TARNISHED_NPC_ROWS) * NPC_ROW_SIZE
    total_growth = pointer_growth + row_growth

    header = bytearray(data[:HEADER_SIZE])
    struct.pack_into("<H", header, 10, len(pointers) + len(TARNISHED_NPC_ROWS))
    struct.pack_into("<I", header, 0, struct.unpack_from("<I", header, 0)[0] + total_growth)
    struct.pack_into("<q", header, 16, struct.unpack_from("<q", header, 16)[0] + total_growth)
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
    base_name_offset = adjusted[base_index][2]
    new_pointers = [
        (row_id, base_new_offset + (index + 1) * NPC_ROW_SIZE, base_name_offset)
        for index, row_id in enumerate(TARNISHED_NPC_ROWS)
    ]
    adjusted[base_index + 1:base_index + 1] = new_pointers
    packed_pointers = b"".join(POINTER_STRUCT.pack(*pointer) for pointer in adjusted)

    payload_start = HEADER_SIZE + len(pointers) * POINTER_STRUCT.size
    insert_at = base_offset + NPC_ROW_SIZE - payload_start
    payload = data[payload_start:]
    patched = (
        bytes(header) + packed_pointers + payload[:insert_at]
        + expected * len(TARNISHED_NPC_ROWS) + payload[insert_at:]
    )
    _, verified = _read_fixed_rows(patched, NPC_ROW_SIZE, "NpcParam")
    for row_id, row in rows.items():
        if verified[row_id] != row:
            raise TorrentRepairError("existing NpcParam row %d changed during repair" % row_id)
    if any(verified[row_id] != expected for row_id in TARNISHED_NPC_ROWS):
        raise TorrentRepairError("NpcParam Torrent rows failed post-insert verification")
    return "missing", patched


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
        original_entries = {e.entry_id: e.data for e in binder.entries}
        try:
            ride_entry = next(e for e in binder.entries if e.name.endswith("RideParam.param"))
            npc_entry = next(e for e in binder.entries if e.name.endswith("NpcParam.param"))
        except StopIteration as exc:
            raise TorrentRepairError(
                "RideParam or NpcParam is absent from %s" % regulation_path
            ) from exc
        ride_state, patched_ride = patch_rideparam_bytes(ride_entry.data)
        npc_state, patched_npc = patch_npcparam_bytes(npc_entry.data)
        if ride_state == "current" and npc_state == "current":
            return "current", None
        ride_entry.set_uncompressed_data(patched_ride)
        npc_entry.set_uncompressed_data(patched_npc)
        changed_ids = [e.entry_id for e in binder.entries if e.data != original_entries[e.entry_id]]
        expected_changed = {
            entry.entry_id for entry, state in ((ride_entry, ride_state), (npc_entry, npc_state))
            if state != "current"
        }
        if set(changed_ids) != expected_changed:
            raise TorrentRepairError(
                "Soulstruct changed unexpected binder entries: %s" % changed_ids
            )

        binder.write(decrypted_out)
        ParamCrypt(decrypted_out, "encrypt", "er", encrypted_out)

        verify_dcx = temp / "verify.parambnd.dcx"
        ParamCrypt(encrypted_out, "decrypt", "er", verify_dcx)
        verified = Binder.from_path(verify_dcx)
        verified_entries = {e.entry_id: e for e in verified.entries}
        for entry_id, data in original_entries.items():
            if entry_id not in expected_changed and verified_entries[entry_id].data != data:
                raise TorrentRepairError(
                    "verification found an unrelated binder entry changed (ID %d)" % entry_id
                )
        verified_ride_state, verified_ride = patch_rideparam_bytes(
            verified_entries[ride_entry.entry_id].data
        )
        verified_npc_state, verified_npc = patch_npcparam_bytes(
            verified_entries[npc_entry.entry_id].data
        )
        if verified_ride_state != "current" or verified_ride != patched_ride:
            raise TorrentRepairError("written regulation did not retain the exact RideParam patch")
        if verified_npc_state != "current" or verified_npc != patched_npc:
            raise TorrentRepairError("written regulation did not retain the exact NpcParam patch")

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
        return "missing", backup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regulation", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        state, backup = repair_regulation(args.regulation)
    except TorrentRepairError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 1
    if state == "current":
        print("Already current: all Elden Ring 1.17 Torrent rows are present")
        return 2
    print("Patched Elden Ring 1.17 Spectral Steed RideParam/NpcParam rows")
    print("  backup: %s" % backup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
