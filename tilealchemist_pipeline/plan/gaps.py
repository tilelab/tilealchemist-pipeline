"""The tile id ranges an archive holds nothing for.

OpenFreeMap omits empty tiles; Protomaps has none.
"""
import operator
from collections.abc import Iterable

from pmtiles.tile import Entry
from tilealchemist.archive.directory import DirectoryEntry
from tilealchemist.archive.zoom import ZoomLevel, tile_id_bounds

from tilealchemist_pipeline.plan.manifest import GAP_OFFSET


def compute_gaps(entries: Iterable[DirectoryEntry], min_zoom: ZoomLevel,
                 max_zoom: ZoomLevel) -> list[Entry]:
    """Returns gap entries for every tile id in range no entry covers.

    A gap is one entry at the shared empty blob, however many tiles it spans.

    Args:
        entries: The run's entries, in any order. None starts past the range,
            though a run may reach past its edges.
        min_zoom: Lowest zoom level of the run.
        max_zoom: Highest zoom level of the run.

    Returns:
        The gaps in tile id order, all inside the range.
    """
    tile_id_start: int
    tile_id_limit: int
    tile_id_start, tile_id_limit = tile_id_bounds(min_zoom, max_zoom)
    gaps: list[Entry] = []
    expected: int = tile_id_start
    entry: DirectoryEntry
    for entry in sorted(entries, key=operator.attrgetter("tile_id")):
        if entry.tile_id > expected:
            gaps.append(_gap(expected, entry.tile_id))
        expected = max(expected, entry.tile_id + entry.run_length)
    if expected < tile_id_limit:
        gaps.append(_gap(expected, tile_id_limit))
    return gaps


def _gap(start: int, end: int) -> Entry:
    """Returns the gap entry for tile ids `[start, end)`."""
    return Entry(tile_id=start, offset=GAP_OFFSET, length=0,
                 run_length=end - start)
