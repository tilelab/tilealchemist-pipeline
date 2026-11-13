"""Planning a run, once; see docs/explanation/architecture.md."""
import json
import os
import shutil
import sys
from collections.abc import Sequence
from typing import Any, TextIO

import requests
from pmtiles.tile import Entry, HeaderDict
from tilealchemist.archive.attribution import (
    compose_attribution,
    declared_attribution,
)
from tilealchemist.archive.directory import DirectoryEntry
from tilealchemist.archive.schema_check import check_schema
from tilealchemist.archive.zoom import ZoomLevel
from tilealchemist.config import plugins
from tilealchemist.config.run_config import (
    ConvertConfig,
    is_path_requirement,
    layer_names,
    schema_name,
)
from tilealchemist.console import log
from tilealchemist.conversion.partition import (
    count_blob_bytes,
    count_decoding_entries,
    share_bounds,
)
from tilealchemist.profiles.base import Profile
from tilealchemist.profiles.loader import load_profile

from tilealchemist_pipeline.fetch.batching import download_bytes
from tilealchemist_pipeline.fetch.pmtiles_index import (
    collect_entries,
    fetch_metadata,
)
from tilealchemist_pipeline.layout import (
    LAYERS_CONFIG_PATH,
    PLAN_DIR,
    PLUGINS_DIR,
    PROFILES_DIR,
    plan_dir_path,
)
from tilealchemist_pipeline.plan.gaps import compute_gaps
from tilealchemist_pipeline.plan.manifest import write_manifests
from tilealchemist_pipeline.plan.pipeline_config import PipelineConfig
from tilealchemist_pipeline.plan.run_plan import RunPlan, write_run_plan
from tilealchemist_pipeline.plan.source_metadata import SourceMetadata
from tilealchemist_pipeline.sources import resolve_source
from tilealchemist_pipeline.sources.base import ResolvedSource

# Left out of plugin copies: nothing pip reads.
PLUGIN_COPY_IGNORED: tuple[str, ...] = (
    ".git", "__pycache__", "*.egg-info", "build", "dist", ".venv")


def plan_run(*, config: PipelineConfig, shard_count: int,
             transform_processes: int | None) -> None:
    """Plans the run and writes `plan/`.

    Loads the profiles, walks the archive's directory, cuts the entries into
    `shard_count` shards of equal blob bytes, and writes the manifests,
    copies of the profiles and plugin directories, layers.toml, and plan.json
    last.

    Args:
        config: The checked config.
        shard_count: How many shards to split the run into.
        transform_processes: Processes per worker, or None for one per core.

    Raises:
        ValueError: If nothing would be credited, a profile lacks a
            dependency or `PROFILE`, or two profiles share a name.
    """
    layers: ConvertConfig = config.layers
    schema: str = schema_name(layers)
    profiles: list[Profile] = [load_profile(path)()
                               for path in layers.profiles]
    names: list[str] = layer_names(layers.profiles, profiles)

    resolved_source: ResolvedSource = resolve_source(config.source,
                                                     config.source_url)
    print(f"source={resolved_source.url} "
          f"(build {resolved_source.build or 'none'}, "
          f"schema {schema})", file=sys.stderr)

    min_zoom: ZoomLevel = layers.min_zoom
    max_zoom: ZoomLevel = layers.max_zoom
    session: requests.Session = requests.Session()
    header: HeaderDict
    entries: list[DirectoryEntry]
    header, entries = collect_entries(session, resolved_source.url,
                                      min_zoom, max_zoom)
    print(f"directory walk found {len(entries)} distinct tile entries "
          f"(min_zoom={min_zoom}, max_zoom={max_zoom})",
          file=sys.stderr)

    archive_metadata: Any = fetch_metadata(session, resolved_source.url,
                                           header)
    declared: str | None = declared_attribution(archive_metadata)
    print(f"source attribution: {declared or 'none declared by the archive'}",
          file=sys.stderr)
    # Every worker's `convert` does the same two; failing here is cheaper.
    attribution: str = compose_attribution(declared, layers.attribution)
    check_schema(plugins.schema(schema), archive_metadata,
                 resolved_source.url)

    gaps: list[Entry] = compute_gaps(entries, min_zoom, max_zoom)
    gap_tile_count: int = sum(gap.run_length for gap in gaps)
    print(f"{len(gaps)} gap entries covering {gap_tile_count} tiles with no "
          f"archive entry at all", file=sys.stderr)
    # At GAP_OFFSET, the gaps sort first, as one blob.
    entries = [*gaps, *entries]

    blob_count: int = count_decoding_entries(entries)
    if blob_count < shard_count:
        log.warning("shards", f"the run decodes only {blob_count} "
                    f"blobs, so {shard_count - blob_count} of its "
                    f"{shard_count} shards get nothing to do")
    # A blob's duplicates stay with it, so the shard with a Protomaps ocean
    # blob holds its millions of entries too.
    bounds: list[int] = share_bounds(entries, shard_count)
    shards: list[Sequence[DirectoryEntry]] = [
        entries[start:stop] for start, stop in zip(bounds, bounds[1:])]
    os.makedirs(PLAN_DIR)
    _write_layers_config(
        layers, schema,
        [_copy_profile(name, path)
         for name, path in zip(names, layers.profiles)],
        [_copy_plugin(spec) for spec in layers.plugins])
    write_manifests(shards)
    write_run_plan(RunPlan(
        shard_count=len(shards),
        layer_names=names,
        source=SourceMetadata(
            url=resolved_source.url,
            build=resolved_source.build,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            tile_data_offset=header["tile_data_offset"],
            archive_metadata=archive_metadata,
        ),
        transform_processes=transform_processes,
    ))

    print(f"wrote {PLAN_DIR}/ with plan.json and {len(shards)} manifests, "
          f"the {_format_bytes(count_blob_bytes(entries))} of "
          f"{blob_count} blobs ({len(entries)} entries) split evenly "
          f"between them", file=sys.stderr)
    downloads: list[int] = [download_bytes(shard) for shard in shards]
    _print_shard_shares(shards, downloads)
    print(f"fetching the shards downloads {_format_bytes(sum(downloads))}, "
          f"from {_format_bytes(min(downloads))} to "
          f"{_format_bytes(max(downloads))} per shard", file=sys.stderr)
    print(f"layer attribution: {attribution}", file=sys.stderr)


def _write_layers_config(layers: ConvertConfig, schema: str,
                         profiles: Sequence[str],
                         plugin_specs: Sequence[str]) -> None:
    """Writes `plan/layers.toml`, the run config every worker converts with.

    Args:
        layers: The run config.
        schema: The run's schema.
        profiles: The profiles' copies, relative to `plan/`.
        plugin_specs: The plugins, directories as copies relative to
            `plan/`.
    """
    lines: list[str] = [
        f"schema = {_toml_string(schema)}",
        f"min_zoom = {layers.min_zoom.value}",
        f"max_zoom = {layers.max_zoom.value}",
        f"profiles = {_toml_array(profiles)}",
        f"plugins = {_toml_array(plugin_specs)}",
    ]
    if layers.attribution is not None:
        lines.append(f"attribution = {_toml_string(layers.attribution)}")
    handle: TextIO
    with open(LAYERS_CONFIG_PATH, "w", encoding="utf-8") as handle:
        handle.write("".join(f"{line}\n" for line in lines))


def _toml_string(value: str) -> str:
    """Returns `value` as a TOML basic string, which JSON's strings are."""
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: Sequence[str]) -> str:
    """Returns `values` as a TOML array of strings."""
    return f"[{', '.join(_toml_string(value) for value in values)}]"


def _copy_profile(name: str, path: str) -> str:
    """Copies a profile into `plan/profiles/<name>/`.

    Returns:
        The copy's path relative to `plan/`.
    """
    relative: str = os.path.join(PROFILES_DIR, name, os.path.basename(path))
    os.makedirs(os.path.dirname(plan_dir_path(relative)))
    shutil.copyfile(path, plan_dir_path(relative))
    return relative


def _copy_plugin(spec: str) -> str:
    """Copies a plugin directory into `plan/plugins/`.

    Args:
        spec: A pip requirement; a path in it is absolute.

    Returns:
        The copy as a `./` path relative to `plan/`, or any other requirement
        unchanged.

    Raises:
        ValueError: If two plugin directories have the same name.
    """
    if not is_path_requirement(spec):
        return spec
    relative: str = f"./{PLUGINS_DIR}/{os.path.basename(spec)}"
    if os.path.exists(plan_dir_path(relative)):
        raise ValueError(f"two plugin directories are named "
                         f"{os.path.basename(spec)!r}; rename one")
    shutil.copytree(spec, plan_dir_path(relative),
                    ignore=shutil.ignore_patterns(*PLUGIN_COPY_IGNORED))
    return relative


def _print_shard_shares(shards: Sequence[Sequence[DirectoryEntry]],
                        downloads: Sequence[int]) -> None:
    """Logs each shard's share, in a folded group.

    Shards hold equal blob bytes, not equal work; these lines let an overrun
    be compared with its share.
    """
    shard_index: int
    shard: Sequence[DirectoryEntry]
    download: int
    with log.group(f"per shard ({len(shards)} manifests)"):
        for shard_index, (shard, download) in enumerate(zip(shards,
                                                             downloads)):
            print(f"shard-{shard_index:03d}: "
                  f"{count_decoding_entries(shard)} blobs, "
                  f"{len(shard)} entries, "
                  f"{_format_bytes(download)} to download",
                  file=sys.stderr)


def _format_bytes(count: int) -> str:
    """Returns `count` in its largest binary unit, such as `3.2 GiB`."""
    unit: str
    exponent: int
    for unit, exponent in (("T", 40), ("G", 30), ("M", 20), ("K", 10)):
        if count >= 2 ** exponent:
            return f"{count / 2 ** exponent:.1f} {unit}iB"
    return f"{count} B"
