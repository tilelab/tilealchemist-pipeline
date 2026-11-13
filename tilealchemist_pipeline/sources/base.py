"""The Source contract: which archive to read."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from tilealchemist.schemas.base import TileSchema


@dataclass(frozen=True)
class ResolvedSource:
    """The archive a run reads.

    Attributes:
        url: Absolute URL of the archive.
        build: Build label for logs, or None.
    """

    url: str
    build: str | None


class Source(ABC):
    """A provider of PMTiles archives, installed as an entry point.

    See docs/reference/sources.md. With `takes_url` False, `__init__`
    gets no arguments; `pipeline_config.checked_config()` enforces it.

    Attributes:
        takes_url: Whether `__init__` gets `plan`'s --source-url as `url`.
        schema: The schema the archive's tiles are in, which a config
            without `schema` takes; `plan` refuses a config naming another.
            None leaves it to the config.
    """

    takes_url: ClassVar[bool] = False
    schema: TileSchema | None = None

    @abstractmethod
    def resolve(self) -> ResolvedSource:
        """Returns the archive to read; called once, before the walk."""
