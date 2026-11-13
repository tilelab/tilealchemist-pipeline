"""A fixed archive URL, read with whichever schema the config names."""
from typing import ClassVar

from tilealchemist_pipeline.sources.base import ResolvedSource, Source


class StaticUrlSource(Source):
    """A fixed archive URL; nothing but the config can say its schema.

    Attributes:
        url: Absolute URL of the archive.
    """

    takes_url: ClassVar[bool] = True
    url: str

    def __init__(self, url: str) -> None:
        self.url = url

    def resolve(self) -> ResolvedSource:
        """Returns the fixed URL, without a build label."""
        return ResolvedSource(self.url, None)
