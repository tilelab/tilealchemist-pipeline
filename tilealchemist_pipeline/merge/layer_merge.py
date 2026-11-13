"""Joining a layer's parts with `pmtiles merge`.

It copies tile data without decoding, and doesn't deduplicate across parts.
It needs clustered parts, which `convert` writes; the same header and
metadata in each, since it keeps the first part's (see
work/shard_archive.py); and disjoint parts, as a tile in two is a
partitioning bug.
"""
import os
import shutil
import subprocess
import sys

from tilealchemist_pipeline.layout import (
    DONE_FILENAME,
    LAYERS_DIR,
    PLAN_PATH,
    done_path,
    layer_path,
    part_dir,
    part_path,
)
from tilealchemist_pipeline.merge.pmtiles_binary import pmtiles_command
from tilealchemist_pipeline.merge.redraws import run_throttled
from tilealchemist_pipeline.plan.run_plan import RunPlan, read_run_plan

# Seconds between printed redraws of `pmtiles merge`'s progress bar, and
# between lines while it prints nothing.
REDRAW_INTERVAL: float = 15.0


def layer_parts(plan: RunPlan, layer: str) -> list[str]:
    """Returns the layer's existing parts, in shard order.

    A shard without tiles for a layer has no part for it.
    """
    paths: list[str] = [part_path(shard, layer)
                        for shard in range(plan.shard_count)]
    return [path for path in paths if os.path.isfile(path)]


def _check_complete(plan: RunPlan) -> None:
    """Raises RuntimeError naming the shards that haven't written `done`."""
    unfinished: list[str] = [
        part_dir(shard) for shard in range(plan.shard_count)
        if not os.path.isfile(done_path(shard))]
    if unfinished:
        raise RuntimeError(f"not every shard is built: {', '.join(unfinished)} "
                           f"{'lacks' if len(unfinished) == 1 else 'lack'} "
                           f"{DONE_FILENAME}; run `tilealchemist-pipeline "
                           f"work` for each")


def merge_layer(layer: str, output_path: str | None = None) -> None:
    """Merges a layer's parts into its `.pmtiles` file.

    The result is renamed into place once complete, so an interrupted merge
    never replaces an existing layer. The parts already carry the metadata.

    Args:
        layer: The layer's name.
        output_path: Where to write it; None for `layers/<layer>.pmtiles`.

    Raises:
        ValueError: If the plan has no such layer.
        RuntimeError: If a shard isn't built, or none has a part for it.
        subprocess.CalledProcessError: If `pmtiles merge` fails.
    """
    plan: RunPlan = read_run_plan()
    names: list[str] = plan.layer_names
    if layer not in names:
        raise ValueError(f"{layer}: {PLAN_PATH} builds no such layer, only "
                         f"{', '.join(names) or 'none'}")
    _check_complete(plan)
    parts: list[str] = layer_parts(plan, layer)
    if not parts:
        raise RuntimeError(f"no shard has a part for {layer}")
    if output_path is None:
        os.makedirs(LAYERS_DIR, exist_ok=True)
        output_path = layer_path(layer)
    temporary: str = f"{output_path}.tmp"
    # Left over from an interrupted merge.
    if os.path.exists(temporary):
        os.remove(temporary)
    # `pmtiles merge` refuses a single input, which is the layer already.
    if len(parts) == 1:
        _place_part(parts[0], temporary)
    else:
        _merge_parts(pmtiles_command(), parts, temporary)
    os.replace(temporary, output_path)


def _place_part(part: str, path: str) -> None:
    """Hard-links a lone part to `path`, or copies it across disks.

    The part stays in `parts/`, so an interrupted merge can be rerun.
    """
    try:
        os.link(part, path)
    except OSError:
        shutil.copyfile(part, path)


def _merge_parts(pmtiles: str, parts: list[str], path: str) -> None:
    r"""Runs `pmtiles merge` with its \r progress bar throttled.

    Raises:
        subprocess.CalledProcessError: If the merge fails.
    """
    command: list[str] = [pmtiles, "merge", *parts, path]
    # Before its first line it reads every part's entries to check that no
    # tile is in two.
    print(f"merging {len(parts)} parts with pmtiles merge, which checks all "
          f"their tiles before printing anything", file=sys.stderr)
    status: int = run_throttled(command, REDRAW_INTERVAL, "pmtiles merge")
    if status:
        raise subprocess.CalledProcessError(status, command)
