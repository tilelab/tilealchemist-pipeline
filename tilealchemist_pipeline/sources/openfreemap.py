"""OpenFreeMap's planet archive; see docs/reference/sources.md."""
import re

import requests
from tilealchemist.schemas.base import TileSchema
from tilealchemist.schemas.openmaptiles import OPENMAPTILES

from tilealchemist_pipeline.sources.base import ResolvedSource, Source

FILES_URL: str = "https://btrfs.openfreemap.com/files.txt"
BASE_URL: str = "https://btrfs.openfreemap.com/"
PLANET_RE: re.Pattern[str] = re.compile(
    r"^areas/planet/(\d{8}_\d{6})_pt/(.+)$")


class OpenFreeMapSource(Source):
    """The newest fully published OpenFreeMap planet build."""

    schema: TileSchema = OPENMAPTILES

    def resolve(self) -> ResolvedSource:
        """Returns the newest finished planet build, labelled by timestamp.

        Raises:
            RuntimeError: If no build has both `done` and `tiles.pmtiles`.
        """
        response: requests.Response = requests.get(FILES_URL, timeout=30)
        response.raise_for_status()

        by_timestamp: dict[str, set[str]] = {}
        line: str
        for line in response.text.splitlines():
            match: re.Match[str] | None = PLANET_RE.match(line.strip())
            if match:
                by_timestamp.setdefault(match.group(1), set()).add(
                    match.group(2))

        # The newest build listed may still be converting.
        ready: list[str] = [
            timestamp for timestamp, files in by_timestamp.items()
            if "done" in files and "tiles.pmtiles" in files]
        if not ready:
            raise RuntimeError(
                f"no fully-published planet build found in {FILES_URL}")
        latest: str = max(ready)
        return ResolvedSource(
            f"{BASE_URL}areas/planet/{latest}_pt/tiles.pmtiles", latest)
