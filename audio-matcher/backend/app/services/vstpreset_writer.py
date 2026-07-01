"""Writes Steinberg VST3 .vstpreset files directly, without needing a DAW.

Binary format confirmed against Steinberg's own source (not reconstructed
from memory): steinbergmedia/vst3_public_sdk, source/vst/vstpresetfile.h
and vstpresetfile.cpp.

    Header (48 bytes):
        "VST3"          4 bytes   magic
        version         int32 LE  = 1
        class id        32 bytes  ASCII uppercase hex of the plugin's 16-byte FUID
        chunk list off. int64 LE  byte offset of the chunk list below

    Data area:
        raw bytes for each chunk (e.g. "Comp" = component state), back to back,
        starting right after the header

    Chunk list (at the offset stored in the header):
        "List"          4 bytes   magic
        entry count     int32 LE
        per entry:
            chunk id    4 bytes   e.g. "Comp", "Cont"
            offset      int64 LE
            size        int64 LE

    No trailing footer -- the file ends after the last chunk list entry.

CAVEAT: this has been round-trip tested against read_vstpreset() in this same
module (see tests/test_vstpreset_writer.py), which confirms internal
self-consistency, but there was no compiled JUCE plugin or real DAW available
in the environment that wrote this to confirm a real host actually accepts
the resulting file. Treat as experimental; the fallback that IS fully
verified is: load container-plugin's chain manifest via its dev-only "Load
Chain Manifest..." button inside any DAW, then use the DAW's own "save
preset" to produce a .vstpreset the traditional way.
"""
from __future__ import annotations

import struct
from pathlib import Path

HEADER_MAGIC = b"VST3"
LIST_MAGIC = b"List"
FORMAT_VERSION = 1
CLASS_ID_HEX_SIZE = 32
HEADER_SIZE = 4 + 4 + CLASS_ID_HEX_SIZE + 8

CHUNK_COMPONENT_STATE = b"Comp"
CHUNK_CONTROLLER_STATE = b"Cont"


def class_id_from_hex(cid_hex: str) -> bytes:
    """moduleinfo.json's Classes[].CID is already the 32-char uppercase hex
    string this format wants -- this just validates and normalizes it."""
    cid_hex = cid_hex.strip().upper()
    if len(cid_hex) != CLASS_ID_HEX_SIZE:
        raise ValueError(f"class id hex must be {CLASS_ID_HEX_SIZE} chars, got {len(cid_hex)}: {cid_hex!r}")
    bytes.fromhex(cid_hex)  # raises if not valid hex
    return cid_hex.encode("ascii")


def write_vstpreset(
    output_path: str | Path,
    class_id_hex: str,
    component_state: bytes,
    controller_state: bytes | None = None,
) -> None:
    class_id_ascii = class_id_from_hex(class_id_hex)

    chunks: list[tuple[bytes, int, int]] = []
    with open(output_path, "wb") as f:
        f.write(HEADER_MAGIC)
        f.write(struct.pack("<i", FORMAT_VERSION))
        f.write(class_id_ascii)
        chunk_list_offset_pos = f.tell()
        f.write(struct.pack("<q", 0))  # patched once we know the real offset

        offset = HEADER_SIZE
        f.write(component_state)
        chunks.append((CHUNK_COMPONENT_STATE, offset, len(component_state)))
        offset += len(component_state)

        if controller_state:
            f.write(controller_state)
            chunks.append((CHUNK_CONTROLLER_STATE, offset, len(controller_state)))
            offset += len(controller_state)

        chunk_list_offset = offset
        f.write(LIST_MAGIC)
        f.write(struct.pack("<i", len(chunks)))
        for chunk_id, chunk_offset, chunk_size in chunks:
            f.write(chunk_id)
            f.write(struct.pack("<qq", chunk_offset, chunk_size))

        f.seek(chunk_list_offset_pos)
        f.write(struct.pack("<q", chunk_list_offset))


def read_vstpreset(input_path: str | Path) -> dict:
    """Reads back what write_vstpreset wrote. Exists mainly so the writer can
    be round-trip tested without a real VST3 host available."""
    with open(input_path, "rb") as f:
        data = f.read()

    if data[0:4] != HEADER_MAGIC:
        raise ValueError("not a VST3 preset file (bad header magic)")
    version = struct.unpack_from("<i", data, 4)[0]
    class_id_hex = data[8 : 8 + CLASS_ID_HEX_SIZE].decode("ascii")
    chunk_list_offset = struct.unpack_from("<q", data, 8 + CLASS_ID_HEX_SIZE)[0]

    if data[chunk_list_offset : chunk_list_offset + 4] != LIST_MAGIC:
        raise ValueError("chunk list offset doesn't point at a 'List' marker")
    entry_count = struct.unpack_from("<i", data, chunk_list_offset + 4)[0]

    chunks = {}
    cursor = chunk_list_offset + 8
    for _ in range(entry_count):
        chunk_id = data[cursor : cursor + 4]
        chunk_offset, chunk_size = struct.unpack_from("<qq", data, cursor + 4)
        chunks[chunk_id.decode("ascii")] = data[chunk_offset : chunk_offset + chunk_size]
        cursor += 4 + 8 + 8

    return {"version": version, "class_id_hex": class_id_hex, "chunks": chunks}
