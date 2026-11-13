"""`tilealchemist-pipeline merge`; the merge is in merge/layer_merge.py."""
import argparse

from tilealchemist.cli import run_args

from tilealchemist_pipeline.merge.layer_merge import merge_layer

HELP: str = """Merges one layer's parts from parts/N/ with `pmtiles merge`,
after every shard is built. Fails if a shard lacks parts/N/done. The pinned
go-pmtiles release is downloaded on first use, unless TILEALCHEMIST_PMTILES
names another binary.

    tilealchemist-pipeline merge --layer land
"""


def add_parser(subparsers: run_args.Subparsers) -> None:
    """Adds `merge` to the steps."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "merge", help="join one layer's parts into the layer",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--layer", required=True,
        help="which of the plan's layers to merge, by name")
    parser.add_argument(
        "--output", default=None,
        help="where to write the layer (default: layers/<layer>.pmtiles)")
    parser.set_defaults(run=run, parser=parser)


def run(args: argparse.Namespace) -> None:
    """Merges one layer."""
    merge_layer(args.layer, args.output)
