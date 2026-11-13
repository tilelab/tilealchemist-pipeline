"""The `tilealchemist-pipeline` command; each step parses, then hands off."""
import argparse
import importlib.metadata
import subprocess
import sys
from collections.abc import Sequence
from types import ModuleType

from tilealchemist.cli import run_args

from tilealchemist_pipeline.cli import merge, plan, work

HELP: str = """Builds tilealchemist layers from a remote PMTiles archive in
steps that may run on different machines: `plan` once, `work` once per
shard, `merge` once per layer, each after `tilealchemist setup`.

See https://github.com/tilelab/tilealchemist-pipeline/blob/main/docs/reference/cli.md.
"""


def parser() -> argparse.ArgumentParser:
    """Returns the command's parser with every step."""
    top: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="tilealchemist-pipeline", description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument(
        "--version", action="version",
        version=(f"%(prog)s "
                 f"{importlib.metadata.version('tilealchemist-pipeline')}"))
    steps: run_args.Subparsers = top.add_subparsers(
        title="steps", metavar="STEP", dest="step", required=True)
    step: ModuleType
    for step in (plan, work, merge):
        step.add_parser(steps)
    return top


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the command with `argv`, or the command line's arguments."""
    args: argparse.Namespace = parser().parse_args(argv)
    try:
        args.run(args)
    except (OSError, RuntimeError, ValueError,
            subprocess.CalledProcessError) as error:
        # The message, or the tool's output above it, says what went wrong.
        sys.exit(f"tilealchemist-pipeline {args.step}: {error}")
