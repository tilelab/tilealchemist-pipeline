"""`tilealchemist-pipeline work`; the worker is in work/shard_worker.py."""
import argparse

from tilealchemist.cli import run_args

from tilealchemist_pipeline.work.shard_worker import build_shard

HELP: str = """Builds one shard's part of every layer.

Reads plan/, fetches shard N of the archive into shards/N.pmtiles, converts
it into parts/N/ (one part per layer it has tiles for), deletes it, and
writes an empty `done`. Run `tilealchemist setup plan/layers.toml` first.

    tilealchemist-pipeline work --shard 0
"""


def add_parser(subparsers: run_args.Subparsers) -> None:
    """Adds `work` to the steps."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "work", help="build one shard's part of every layer",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--shard", type=int, required=True,
        help="which of plan.json's shards to build, counted from 0")
    parser.set_defaults(run=run, parser=parser)


def run(args: argparse.Namespace) -> None:
    """Builds one shard."""
    build_shard(args.shard)
