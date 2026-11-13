"""A pipeline run: a run config, and the source its archive comes from.

The source is `plan`'s --source and --source-url, never the config's, as
the archive is `convert`'s `input`. A config without `schema` takes the
source's.
"""
import dataclasses

from tilealchemist.config import run_config
from tilealchemist.config.run_config import ConvertConfig

from tilealchemist_pipeline.sources import source
from tilealchemist_pipeline.sources.base import Source

DEFAULT_SOURCE: str = "openfreemap"


@dataclasses.dataclass(frozen=True)
class PipelineConfig:
    """What a pipeline run builds, and from which archive.

    Attributes:
        layers: The run config, naming the source's schema if it named none.
        source: The installed source to read.
        source_url: The archive URL, for a source that takes one.
    """

    layers: ConvertConfig
    source: str
    source_url: str | None


def checked_config(layers: ConvertConfig, source_name: str,
                   source_url: str | None) -> PipelineConfig:
    """Returns the run, checked, with its schema settled.

    Raises:
        ValueError: If the run config doesn't hold together, the source is
            not installed, it gets a URL it doesn't take or lacks one it
            needs, or the config names another schema than it serves, or
            neither names one.
    """
    source_class: type[Source] = source(source_name)
    if source_class.takes_url and not source_url:
        raise ValueError(f"source {source_name} reads the archive at "
                         f"--source-url, which is missing")
    if source_url and not source_class.takes_url:
        raise ValueError(f"source {source_name} finds its own archive; "
                         f"leave --source-url off")
    served: str | None = (source_class.schema.name
                          if source_class.schema is not None else None)
    if served is not None and layers.schema not in (None, served):
        raise ValueError(f"source {source_name} serves {served} tiles, not "
                         f"{layers.schema}; leave schema out of the config "
                         f"to take the source's")
    layers = dataclasses.replace(layers, schema=layers.schema or served)
    run_config.check(layers)
    return PipelineConfig(layers, source_name, source_url)
