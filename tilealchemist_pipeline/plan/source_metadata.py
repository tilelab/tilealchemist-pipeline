"""The source archive as plan.json describes it to every worker."""
from dataclasses import dataclass
from typing import Any, Self

from tilealchemist.archive.zoom import ZoomLevel


@dataclass(frozen=True)
class SourceMetadata:
    """The archive a run reads.

    Attributes:
        url: Absolute URL of the archive.
        build: Build label for logs, or None.
        min_zoom: Lowest zoom level the run builds.
        max_zoom: Highest zoom level the run builds.
        tile_data_offset: Start of the tile data; manifest offsets are
            relative to it.
        archive_metadata: The archive's PMTiles metadata, which every shard
            archive carries.
    """

    url: str
    build: str | None
    min_zoom: ZoomLevel
    max_zoom: ZoomLevel
    tile_data_offset: int
    archive_metadata: dict[str, Any]

    def as_json(self) -> dict[str, Any]:
        """Returns the fields as JSON values."""
        return {
            "url": self.url,
            "build": self.build,
            "min_zoom": self.min_zoom.value,
            "max_zoom": self.max_zoom.value,
            "tile_data_offset": self.tile_data_offset,
            "archive_metadata": self.archive_metadata,
        }

    @classmethod
    def from_json(cls, document: dict[str, Any]) -> Self:
        """Returns the metadata `as_json()` wrote."""
        return cls(
            url=document["url"],
            build=document["build"],
            min_zoom=ZoomLevel(document["min_zoom"]),
            max_zoom=ZoomLevel(document["max_zoom"]),
            tile_data_offset=document["tile_data_offset"],
            archive_metadata=document["archive_metadata"],
        )
