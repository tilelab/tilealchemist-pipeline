"""`work`: one shard, fetched, then converted."""
import os
import subprocess
import sys

from pmtiles.tile import Entry
from tilealchemist.conversion.partition import count_decoding_entries

from tilealchemist_pipeline.layout import (
    LAYERS_CONFIG_PATH,
    PLAN_PATH,
    done_path,
    manifest_path,
    part_dir,
    shard_path,
)
from tilealchemist_pipeline.plan.manifest import read_manifest
from tilealchemist_pipeline.plan.run_plan import RunPlan, read_run_plan
from tilealchemist_pipeline.work.shard_archive import write_shard_archive


def build_shard(shard_index: int) -> None:
    """Builds shard `shard_index`'s part of every layer into `parts/N/`.

    Fetches the shard into `shards/N.pmtiles`, runs `tilealchemist convert`
    on it, and deletes it. Writes `done` last.

    Raises:
        ValueError: If the plan has no such shard.
        subprocess.CalledProcessError: If `convert` fails.
    """
    plan: RunPlan = read_run_plan()
    if not 0 <= shard_index < plan.shard_count:
        raise ValueError(f"shard {shard_index}: {PLAN_PATH} has "
                         f"shards 0 to {plan.shard_count - 1}")
    print(f"source={plan.source.url} (build {plan.source.build or 'none'})",
          file=sys.stderr)
    entries: list[Entry] = read_manifest(manifest_path(shard_index))
    gap_count: int = sum(1 for entry in entries if not entry.length)
    print(f"{len(entries)} entries assigned, {gap_count} of them gaps, "
          f"{count_decoding_entries(entries)} blobs",
          file=sys.stderr)
    os.makedirs(part_dir(shard_index), exist_ok=True)
    if entries:
        shard: str = shard_path(shard_index)
        write_shard_archive(shard, entries, plan.source, shard_index)
        command: list[str] = [
            sys.executable, "-m", "tilealchemist", "convert", shard,
            LAYERS_CONFIG_PATH, "-o", part_dir(shard_index)]
        if plan.transform_processes:
            command += ["--transform-processes",
                        str(plan.transform_processes)]
        subprocess.run(command, check=True)
        os.remove(shard)
    with open(done_path(shard_index), "wb"):
        pass
