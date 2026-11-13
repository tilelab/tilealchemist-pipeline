"""`tilealchemist-pipeline plan`; the planning is in plan/planning.py."""
import argparse
import os

from tilealchemist.cli import run_args

from tilealchemist_pipeline.layout import PARTS_DIR, PLAN_DIR, SHARDS_DIR
from tilealchemist_pipeline.plan.pipeline_config import (
    DEFAULT_SOURCE,
    PipelineConfig,
    checked_config,
)
from tilealchemist_pipeline.plan.planning import plan_run

DEFAULT_SHARDS: int = 1

HELP: str = """Plans the run, once, before any worker starts.

Walks the directory of the archive --source finds and splits its entries,
plus the gaps, into --shards shards of equal blob bytes. Writes plan/: a
manifest per shard, copies of the profiles and plugin directories,
layers.toml for `convert`, and plan.json. Every later step runs beside the
same plan/. Run `tilealchemist setup` first.

    tilealchemist-pipeline plan land.toml --max-zoom 6 --shards 60
    tilealchemist-pipeline plan land.toml --source protomaps
"""


def add_parser(subparsers: run_args.Subparsers) -> None:
    """Adds `plan` to the steps."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "plan", help="walk the archive and split the run into shards",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    run_args.add_config_arguments(parser)
    group: argparse._ArgumentGroup = parser.add_argument_group("the archive")
    group.add_argument(
        "--source",
        help=f"the installed source that finds the archive (default "
             f"{DEFAULT_SOURCE}); a config without `schema` takes its "
             f"schema")
    group.add_argument(
        "--source-url",
        help="the archive's URL, for a source that takes one, such as "
             "static-url")
    group = parser.add_argument_group("planning the run")
    group.add_argument(
        "--shards",
        help="how many shards to split the run into, each given equally "
             f"many of its blob bytes (default {DEFAULT_SHARDS})")
    group.add_argument(run_args.PROCESSES_FLAG[0],
                       help=run_args.PROCESSES_FLAG[1])
    parser.set_defaults(run=run, parser=parser)


def run(args: argparse.Namespace) -> None:
    """Plans the run, checking every value before the walk."""
    parser: argparse.ArgumentParser = args.parser
    # Or a later step would read another run's files.
    leftover: list[str] = [path for path in (PLAN_DIR, SHARDS_DIR, PARTS_DIR)
                           if os.path.exists(path)]
    if leftover:
        parser.error(f"the working directory holds {', '.join(leftover)} "
                     f"from another run; delete "
                     f"{'it' if len(leftover) == 1 else 'them'} first")
    config: PipelineConfig
    shard_count: int
    transform_processes: int | None
    try:
        config = checked_config(run_args.read_config(args),
                                args.source or DEFAULT_SOURCE,
                                args.source_url or None)
        shard_count = (run_args.count(args.shards, "--shards") if args.shards
                       else DEFAULT_SHARDS)
        transform_processes = run_args.read_processes(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    plan_run(config=config, shard_count=shard_count,
             transform_processes=transform_processes)
