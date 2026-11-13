"""A shard of the source archive, as a PMTiles file of its own.

`convert` reads it like any archive. Gaps become entries at EMPTY_TILE, so
the shards hold every tile id of the run.
"""
import gzip
import json
import os
import sys
from collections.abc import Sequence
from typing import BinaryIO

import requests
from pmtiles.tile import (
    Compression,
    Entry,
    HeaderDict,
    TileType,
    serialize_header,
)
from pmtiles.writer import optimize_directories
from tilealchemist.archive.directory import (
    HEADER_AND_ROOT_LENGTH,
    HEADER_LENGTH,
    DirectoryEntry,
)
from tilealchemist.archive.zoom import tile_id_bounds
from tilealchemist.conversion.partition import count_decoding_entries

from tilealchemist_pipeline.fetch.batching import Batch, plan_fetch_batches
from tilealchemist_pipeline.fetch.ranged_fetch import (
    DownloadProgress,
    fetch_range,
)
from tilealchemist_pipeline.plan.source_metadata import SourceMetadata

ROOT_DIRECTORY_LIMIT: int = HEADER_AND_ROOT_LENGTH - HEADER_LENGTH

# Seconds between progress lines of the tile data's download.
DOWNLOAD_REPORT_INTERVAL: float = 15.0

# A gzipped MVT without layers: what every gap's tile is.
EMPTY_TILE: bytes = gzip.compress(b"", mtime=0)

# The whole Web Mercator world as header bounds: min lon, min lat, max lon,
# max lat, each times 10^7.
WORLD_BOUNDS_E7: tuple[int, int, int, int] = (
    -180 * 10_000_000, -850_511_287, 180 * 10_000_000, 850_511_287)


def write_shard_archive(path: str, entries: Sequence[DirectoryEntry],
                        source: SourceMetadata, shard_index: int) -> None:
    """Fetches a shard into a PMTiles file at `path`.

    Its tile data is each batch in turn: EMPTY_TILE for the gaps, the
    fetched bytes, holes included, for the rest. Every offset is known before
    the first fetch, so header and directories go first and the batches
    stream in behind them. The file is renamed into place once complete.

    Args:
        path: Where to write it.
        entries: The shard's entries, gaps included, in offset order.
        source: The archive.
        shard_index: The shard's number, for retry warnings.
    """
    batches: list[Batch] = plan_fetch_batches(entries)
    shard_entries: list[Entry]
    tile_data_length: int
    shard_entries, tile_data_length = _shard_entries(batches, source)
    root_bytes: bytes
    leaves_bytes: bytes
    root_bytes, leaves_bytes, _ = optimize_directories(shard_entries,
                                                       ROOT_DIRECTORY_LIMIT)
    metadata_bytes: bytes = gzip.compress(
        json.dumps(source.archive_metadata, separators=(",", ":")).encode(),
        mtime=0)

    metadata_offset: int = HEADER_LENGTH + len(root_bytes)
    leaf_offset: int = metadata_offset + len(metadata_bytes)
    header: HeaderDict = {
        # HeaderDict requires it; serialize_header() writes 3 regardless.
        "version": 3,
        "root_offset": HEADER_LENGTH,
        "root_length": len(root_bytes),
        "metadata_offset": metadata_offset,
        "metadata_length": len(metadata_bytes),
        "leaf_directory_offset": leaf_offset,
        "leaf_directory_length": len(leaves_bytes),
        "tile_data_offset": leaf_offset + len(leaves_bytes),
        "tile_data_length": tile_data_length,
        "addressed_tiles_count": sum(entry.run_length
                                     for entry in shard_entries),
        "tile_entries_count": len(shard_entries),
        "tile_contents_count": count_decoding_entries(entries),
        # Laid out in source offset order, not tile id order.
        "clustered": False,
        "internal_compression": Compression.GZIP,
        "tile_compression": Compression.GZIP,
        "tile_type": TileType.MVT,
        # The run's, in every shard: `convert` builds this range.
        "min_zoom": source.min_zoom.value,
        "max_zoom": source.max_zoom.value,
        # The same in every shard, and `convert` keeps them: `pmtiles merge`
        # takes the union of the parts' bounds and the first part's center,
        # so the layer doesn't depend on part order.
        "min_lon_e7": WORLD_BOUNDS_E7[0],
        "min_lat_e7": WORLD_BOUNDS_E7[1],
        "max_lon_e7": WORLD_BOUNDS_E7[2],
        "max_lat_e7": WORLD_BOUNDS_E7[3],
        "center_zoom": source.min_zoom.value,
        "center_lon_e7": 0,
        "center_lat_e7": 0,
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary_path: str = path + ".tmp"
    shard: BinaryIO
    with open(temporary_path, "wb") as shard:
        shard.write(serialize_header(header))
        shard.write(root_bytes)
        shard.write(metadata_bytes)
        shard.write(leaves_bytes)
        _fetch_tile_data(shard, batches, source, shard_index)
    os.replace(temporary_path, path)


def _shard_entries(batches: Sequence[Batch], source: SourceMetadata
                   ) -> tuple[list[Entry], int]:
    """Returns the shard's directory entries and its tile data's length.

    Entries are clipped to the run's zoom range and sorted by tile id.
    """
    tile_id_start: int
    tile_id_limit: int
    tile_id_start, tile_id_limit = tile_id_bounds(source.min_zoom,
                                                  source.max_zoom)
    shard_entries: list[Entry] = []
    position: int = 0
    batch: Batch
    entry: DirectoryEntry
    for batch in batches:
        for entry in batch.entries:
            start: int = max(entry.tile_id, tile_id_start)
            end: int = min(entry.tile_id + entry.run_length, tile_id_limit)
            if batch.length:
                shard_entries.append(Entry(
                    start, position + entry.offset - batch.offset,
                    entry.length, end - start))
            else:
                shard_entries.append(Entry(start, position, len(EMPTY_TILE),
                                           end - start))
        position += batch.length or len(EMPTY_TILE)
    shard_entries.sort(key=lambda shard_entry: shard_entry.tile_id)
    return shard_entries, position


def _fetch_tile_data(shard: BinaryIO, batches: Sequence[Batch],
                     source: SourceMetadata, shard_index: int) -> None:
    """Writes each batch's tile data into `shard`, in _shard_entries() order."""
    session: requests.Session = requests.Session()
    index: int
    batch: Batch
    for index, batch in enumerate(batches, start=1):
        if not batch.length:
            shard.write(EMPTY_TILE)
            continue
        label: str = f" {index}/{len(batches)}" if len(batches) > 1 else ""
        print(f"starting download{label} ({batch.length} bytes, "
              f"{len(batch.entries)} entries in a single range request)",
              file=sys.stderr)
        fetch_range(
            session, source.url, source.tile_data_offset + batch.offset,
            batch.length, shard, retry_label=f"shard {shard_index}",
            on_progress=DownloadProgress(batch.length,
                                         DOWNLOAD_REPORT_INTERVAL,
                                         f"tile data{label}").update)
