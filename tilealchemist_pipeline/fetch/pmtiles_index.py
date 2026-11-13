"""The source archive's directory entries and metadata, by range requests.

The walk itself is tilealchemist's archive/directory.py; the tile ids the
archive holds nothing for are plan/gaps.py's.
"""
import gzip
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import requests
from pmtiles.tile import HeaderDict
from tilealchemist.archive.directory import (
    HEADER_AND_ROOT_LENGTH,
    DirectoryEntry,
    entries_in_range,
    parse_header_and_root,
)
from tilealchemist.archive.zoom import ZoomLevel, tile_id_bounds

from tilealchemist_pipeline.fetch.batching import check_byte_ranges
from tilealchemist_pipeline.fetch.ranged_fetch import (
    DownloadProgress,
    fetch_bytes,
)

RETRY_LABEL: str = "plan"

# Seconds between progress lines of the leaf directories' download.
INDEX_REPORT_INTERVAL: float = 1.0


@dataclass(frozen=True)
class LeafWindow:
    """The slice of the leaf section a zoom range needs, fetched by range.

    Attributes:
        buffer: The slice's bytes.
        start: Offset in the leaf section where `buffer` begins.
    """

    buffer: bytes
    start: int

    def directory_bytes(self, entry: DirectoryEntry) -> bytes:
        """Returns the bytes of the leaf directory `entry` points at.

        Raises:
            RuntimeError: If the directory lies outside the window: the
                archive nests leaf directories outside those the root points
                at, or is damaged.
        """
        offset: int = entry.offset - self.start
        if offset < 0 or offset + entry.length > len(self.buffer):
            raise RuntimeError(
                f"directory at leaf-section offset {entry.offset} "
                f"(+{entry.length} bytes) lies outside the {len(self.buffer)} "
                f"bytes fetched from {self.start}. The window spans the leaf "
                f"directories the root points at; this archive nests another "
                f"level of them outside it, which PMTiles v3 discourages, or "
                f"it is damaged. Download it and run `tilealchemist convert` "
                f"on the file, which reads every leaf where it lies.")
        return self.buffer[offset:offset + entry.length]


def collect_entries(session: requests.Session, url: str, min_zoom: ZoomLevel,
                    max_zoom: ZoomLevel
                    ) -> tuple[HeaderDict, list[DirectoryEntry]]:
    """Reads the archive's directory down to the entries of a zoom range.

    Two requests: header and root, then the leaf slice they point into.

    Returns:
        The archive's header, and its entries in offset order, lowest tile id
        first within an offset.

    Raises:
        ValueError: If the archive's blobs overlap.
    """
    header: HeaderDict
    root_directory: list[DirectoryEntry]
    header, root_directory = parse_header_and_root(fetch_bytes(
        session, url, 0, HEADER_AND_ROOT_LENGTH, retry_label=RETRY_LABEL))
    leaf_window: LeafWindow = _fetch_leaf_window(
        session, url, header,
        *leaf_window_for(root_directory, *tile_id_bounds(min_zoom, max_zoom)))
    entries: list[DirectoryEntry] = entries_in_range(
        header, root_directory, leaf_window.directory_bytes,
        len(leaf_window.buffer), min_zoom, max_zoom)
    check_byte_ranges(entries)
    return header, entries


def fetch_metadata(session: requests.Session, url: str,
                   header: HeaderDict) -> Any:
    """Returns the archive's metadata as parsed JSON; {} if it has none."""
    length: int = header["metadata_length"]
    if not length:
        return {}
    # Gzipped like the directories, which deserialize_directory() has
    # already gunzipped.
    return json.loads(gzip.decompress(fetch_bytes(
        session, url, header["metadata_offset"], length,
        retry_label=RETRY_LABEL)))


def leaf_window_for(root_directory: Sequence[DirectoryEntry],
                    tile_id_start: int,
                    tile_id_limit: int) -> tuple[int, int]:
    """Returns `(start, length)` of the leaf section a range needs.

    Spans every leaf directory the root points at for the range, in whatever
    order they lie; `(0, 0)` if it needs none. Prunes by the rule of
    tilealchemist's walk_directory_tree(): a narrower window fails in
    LeafWindow.directory_bytes(), a wider one only fetches more.
    """
    # A leaf covers the tile ids up to the next root entry's.
    next_tile_ids: list[int] = [
        *(entry.tile_id for entry in root_directory[1:]), tile_id_limit]
    needed: list[DirectoryEntry] = [
        entry for entry, next_tile_id in zip(root_directory, next_tile_ids)
        if entry.run_length == 0 and entry.tile_id < tile_id_limit
        and next_tile_id > tile_id_start]
    if not needed:
        return 0, 0
    start: int = min(entry.offset for entry in needed)
    end: int = max(entry.offset + entry.length for entry in needed)
    return start, end - start


def _fetch_leaf_window(session: requests.Session, url: str,
                       header: HeaderDict, window_start: int,
                       window_length: int) -> LeafWindow:
    """Returns the leaf slice the walk descends into; empty for length 0."""
    if window_length == 0:
        return LeafWindow(b"", 0)

    print(f"starting download ({window_length} bytes of leaf directories, "
          f"{header['tile_entries_count']} entries in the archive)",
          file=sys.stderr)
    buffer: bytes = fetch_bytes(
        session, url, header["leaf_directory_offset"] + window_start,
        window_length, retry_label=RETRY_LABEL,
        on_progress=DownloadProgress(window_length, INDEX_REPORT_INTERVAL,
                                     "directory index").update)
    return LeafWindow(buffer, window_start)
