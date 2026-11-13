"""Every path the steps read and write, relative to the working directory.

    plan/                written once by `plan`
      plan.json          see run_plan.py
      layers.toml        the run config `convert` reads
      shard-NNN.bin      one manifest per shard; see manifest.py
      profiles/          copies of the run's profiles
      plugins/           copies of the plugins given by path
    shards/N.pmtiles     shard N's archive, while it converts
    parts/N/             written by shard N's worker
      <layer>.pmtiles    its part of each layer
      done               empty, written last
    layers/              written by `merge`, unless given --output
      <layer>.pmtiles    the layer

See docs/reference/cli.md "Run directory".
"""
import os

PLAN_DIR: str = "plan"
SHARDS_DIR: str = "shards"
PARTS_DIR: str = "parts"
LAYERS_DIR: str = "layers"

PLAN_PATH: str = os.path.join(PLAN_DIR, "plan.json")
LAYERS_CONFIG_PATH: str = os.path.join(PLAN_DIR, "layers.toml")

# Inside plan/.
PROFILES_DIR: str = "profiles"
PLUGINS_DIR: str = "plugins"

DONE_FILENAME: str = "done"


def plan_dir_path(path: str) -> str:
    """Returns a path from layers.toml, which is relative to `plan/`."""
    return os.path.join(PLAN_DIR, path)


def manifest_path(shard_index: int) -> str:
    """Returns `plan/shard-NNN.bin`."""
    return os.path.join(PLAN_DIR, f"shard-{shard_index:03d}.bin")


def shard_path(shard_index: int) -> str:
    """Returns `shards/N.pmtiles`."""
    return os.path.join(SHARDS_DIR, f"{shard_index}.pmtiles")


def part_dir(shard_index: int) -> str:
    """Returns `parts/N`."""
    return os.path.join(PARTS_DIR, str(shard_index))


def part_path(shard_index: int, layer: str) -> str:
    """Returns `parts/N/<layer>.pmtiles`."""
    return os.path.join(part_dir(shard_index), f"{layer}.pmtiles")


def done_path(shard_index: int) -> str:
    """Returns `parts/N/done`."""
    return os.path.join(part_dir(shard_index), DONE_FILENAME)


def layer_path(layer: str) -> str:
    """Returns `layers/<layer>.pmtiles`."""
    return os.path.join(LAYERS_DIR, f"{layer}.pmtiles")
