"""`plan/plan.json`, which every step after `plan` reads.

It says how many shards there are, the layers, the archive, and the shared
worker settings; what `convert` reads is in `plan/layers.toml`. It may
change in any release; see docs/reference/cli.md.
"""
import importlib.metadata
import json
from dataclasses import dataclass
from typing import Any, Self, TextIO

from tilealchemist_pipeline.layout import PLAN_PATH
from tilealchemist_pipeline.plan.source_metadata import SourceMetadata

# The tilealchemist-pipeline that writes and reads plan.json. Its key never
# changes, so every version can tell that another wrote a plan/.
VERSION: str = importlib.metadata.version("tilealchemist-pipeline")


@dataclass(frozen=True)
class RunPlan:
    """What every step after `plan` needs.

    Attributes:
        shard_count: How many shards there are, numbered from zero.
        layer_names: The layers, one merge each, in the config's order.
        source: The archive.
        transform_processes: Processes per worker, or None for one per core.
    """

    shard_count: int
    layer_names: list[str]
    source: SourceMetadata
    transform_processes: int | None

    def as_json(self) -> dict[str, Any]:
        """Returns the plan as plan.json holds it."""
        return {
            "version": VERSION,
            "shard_count": self.shard_count,
            "layers": [{"name": name} for name in self.layer_names],
            "source": self.source.as_json(),
            "transform_processes": self.transform_processes,
        }

    @classmethod
    def from_json(cls, document: dict[str, Any]) -> Self:
        """Returns the plan `as_json()` wrote.

        Raises:
            ValueError: If another tilealchemist-pipeline version wrote it.
        """
        version: Any = document.get("version")
        if version != VERSION:
            raise ValueError(f"tilealchemist-pipeline {version} wrote "
                             f"{PLAN_PATH}, but this is {VERSION}; run every "
                             f"step of a run with the same "
                             f"tilealchemist-pipeline")
        return cls(
            shard_count=document["shard_count"],
            layer_names=[layer["name"] for layer in document["layers"]],
            source=SourceMetadata.from_json(document["source"]),
            transform_processes=document["transform_processes"],
        )


def write_run_plan(plan: RunPlan) -> None:
    """Writes `plan/plan.json`, last of everything in `plan/`."""
    plan_file: TextIO
    with open(PLAN_PATH, "w", encoding="utf-8") as plan_file:
        json.dump(plan.as_json(), plan_file)


def read_run_plan() -> RunPlan:
    """Returns the plan in `plan/plan.json`.

    Raises:
        OSError: If the file cannot be read.
        KeyError: If a key is missing.
        ValueError: If it is not JSON, another tilealchemist-pipeline version
            wrote it, or it holds an unknown zoom level.
    """
    plan_file: TextIO
    with open(PLAN_PATH, encoding="utf-8") as plan_file:
        return RunPlan.from_json(json.load(plan_file))
