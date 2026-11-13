"""Protomaps' daily planet builds; see docs/reference/sources.md."""
from typing import Any

import requests
from tilealchemist.schemas.base import TileSchema
from tilealchemist.schemas.protomaps import PROTOMAPS

from tilealchemist_pipeline.sources.base import ResolvedSource, Source

BUILDS_URL: str = "https://build-metadata.protomaps.dev/builds.json"
BASE_URL: str = "https://build.protomaps.com/"


class ProtomapsSource(Source):
    """The newest planet build in the Protomaps build index."""

    schema: TileSchema = PROTOMAPS

    def resolve(self) -> ResolvedSource:
        """Returns the newest listed build, labelled by key and version.

        Raises:
            RuntimeError: If the index lists no .pmtiles build.
        """
        response: requests.Response = requests.get(BUILDS_URL, timeout=30)
        response.raise_for_status()

        builds: list[dict[str, Any]] = [
            build for build in response.json()
            if str(build.get("key", "")).endswith(".pmtiles")]
        if not builds:
            raise RuntimeError(f"no .pmtiles build listed in {BUILDS_URL}")

        # By the date in the key: old basemap versions stay listed.
        latest: dict[str, Any] = max(builds, key=lambda build: build["key"])
        key: str = latest["key"]
        version: str = latest.get("version", "unknown")
        build: str = f"{key.removesuffix('.pmtiles')} (basemap {version})"
        return ResolvedSource(BASE_URL + key, build)
