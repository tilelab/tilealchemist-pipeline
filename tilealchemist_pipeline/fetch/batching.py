"""Grouping a shard's entries into range requests."""
from collections.abc import Iterator, Sequence
from typing import NamedTuple

from pmtiles.tile import tileid_to_zxy
from tilealchemist.archive.directory import DirectoryEntry

# Below 8 MiB, reading through a hole beats another round trip.
MAX_FETCH_HOLE: int = 8 * 1024 * 1024


class Batch(NamedTuple):
    """One range request's entries; a batch of gaps requests nothing."""

    offset: int
    length: int
    entries: Sequence[DirectoryEntry]


def plan_fetch_batches(entries: Sequence[DirectoryEntry]) -> list[Batch]:
    """Returns one Batch per range request, in offset order.

    Gaps get a batch of their own, of length zero.

    Args:
        entries: The shard's entries, gaps included, in offset order.
    """
    return [_batch(entries[start:end])
            for start, end in _split_on_wide_holes(entries)]


def download_bytes(entries: Sequence[DirectoryEntry]) -> int:
    """Returns the bytes a worker downloads for `entries`, holes included."""
    return sum(batch.length for batch in plan_fetch_batches(entries))


def check_byte_ranges(entries: Sequence[DirectoryEntry]) -> None:
    """Rejects an archive whose blobs overlap.

    Batches take their end from their last entry, which needs every blob in
    a byte range of its own. Writers do that, but the format doesn't
    require it.

    Args:
        entries: The archive's entries, in offset order.

    Raises:
        ValueError: If an entry starts inside another blob.
    """
    previous_key: tuple[int, int] | None = None
    previous_end: int = 0
    entry: DirectoryEntry
    for entry in entries:
        key: tuple[int, int] = (entry.offset, entry.length)
        if key == previous_key:
            continue
        if entry.offset < previous_end:
            zoom: int
            column: int
            row: int
            zoom, column, row = tileid_to_zxy(entry.tile_id)
            raise ValueError(
                f"tile {zoom}/{column}/{row} reads bytes {entry.offset}.."
                f"{entry.offset + entry.length}, which start inside another "
                f"blob ending at {previous_end}; tilealchemist-pipeline needs "
                f"every blob in its own byte range, while `tilealchemist "
                f"convert` reads such an archive from a local copy")
        previous_key, previous_end = key, entry.offset + entry.length


def _split_on_wide_holes(entries: Sequence[DirectoryEntry]
                         ) -> Iterator[tuple[int, int]]:
    """Yields each batch's `(start, end)` slice of `entries`.

    Batches split at holes wider than MAX_FETCH_HOLE, and where the gaps end:
    a batch reaching from GAP_OFFSET would ask for bytes no archive has.

    Args:
        entries: The shard's entries, gaps included, in offset order.
    """
    start: int = 0
    reach: int = 0
    index: int
    entry: DirectoryEntry
    for index, entry in enumerate(entries):
        # Blobs don't overlap (see check_byte_ranges()), so the previous
        # entry's end is the batch's.
        wide_hole: bool = entry.offset - reach > MAX_FETCH_HOLE
        gap_edge: bool = (entry.length == 0) != (entries[start].length == 0)
        if index > start and (wide_hole or gap_edge):
            yield start, index
            start = index
        reach = entry.offset + entry.length
    if start < len(entries):
        yield start, len(entries)


def _batch(batch_entries: Sequence[DirectoryEntry]) -> Batch:
    """Returns the Batch spanning `batch_entries`, in offset order."""
    first: DirectoryEntry = batch_entries[0]
    last: DirectoryEntry = batch_entries[-1]
    return Batch(first.offset, last.offset + last.length - first.offset,
                 batch_entries)

