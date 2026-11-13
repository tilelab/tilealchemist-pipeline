"""The per-shard manifests `plan/shard-NNN.bin`."""
import struct
from collections.abc import Iterable, Sequence
from typing import BinaryIO

from pmtiles.tile import Entry
from tilealchemist.archive.directory import DirectoryEntry

from tilealchemist_pipeline.layout import manifest_path

# tile_id, offset, length, run_length. The offset is signed for GAP_OFFSET.
ENTRY_STRUCT: struct.Struct = struct.Struct("<QqII")

# A gap's offset in a manifest; no archive has it. Gaps alone have length 0,
# which batching tells them by. Shard archives point gaps at
# shard_archive.EMPTY_TILE instead.
GAP_OFFSET: int = -1


def write_manifest(path: str, entries: Iterable[DirectoryEntry]) -> None:
    """Writes entries to `path`, in the order a worker walks them."""
    file: BinaryIO
    entry: DirectoryEntry
    with open(path, "wb") as file:
        for entry in entries:
            file.write(ENTRY_STRUCT.pack(entry.tile_id, entry.offset,
                                         entry.length, entry.run_length))


def read_manifest(path: str) -> list[Entry]:
    """Returns the entries in the manifest at `path`."""
    file: BinaryIO
    with open(path, "rb") as file:
        data: bytes = file.read()
    return [Entry(*fields) for fields in ENTRY_STRUCT.iter_unpack(data)]


def write_manifests(shards: Sequence[Sequence[DirectoryEntry]]) -> None:
    """Writes one manifest per shard into `plan/`, empty shards included."""
    shard_index: int
    shard: Sequence[DirectoryEntry]
    for shard_index, shard in enumerate(shards):
        write_manifest(manifest_path(shard_index), shard)
