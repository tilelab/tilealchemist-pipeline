"""Installed sources, found through entry points.

See docs/how-to-guides/write-a-source.md.
"""
from typing import Any

from tilealchemist.config import plugins

from tilealchemist_pipeline.sources.base import ResolvedSource, Source

SOURCE_GROUP: str = "tilealchemist.sources"


def source(name: str) -> type[Source]:
    """Returns the Source class installed as `name`.

    Raises:
        ValueError: If no such source is installed.
    """
    source_class: type[Source] = plugins.load(SOURCE_GROUP, "source", name)
    return source_class


def resolve_source(source_name: str,
                   source_url: str | None = None) -> ResolvedSource:
    """Returns the archive the named Source resolves to.

    `pipeline_config.checked_config()` has already held the URL to what the
    source takes; a URL it does not take is dropped here.

    Raises:
        ValueError: If the source is not installed.
    """
    source_class: type[Source] = source(source_name)
    given: dict[str, Any] = {}
    if source_class.takes_url:
        given["url"] = source_url
    return source_class(**given).resolve()
