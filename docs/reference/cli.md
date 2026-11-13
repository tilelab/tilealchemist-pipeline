# Command-line reference

`tilealchemist-pipeline` runs the pipeline's three steps in a shared
working directory: `plan` once, `work` once per shard, `merge` once per
layer. `--version` prints the version, and `-h` prints help for any step.
Exit status: `0` on success, `1` when a step fails, `2` for invalid
arguments or an invalid run config. `setup` and `convert` are in
tilealchemist's [command-line reference](https://github.com/tilelab/tilealchemist/blob/main/docs/reference/cli.md).

## tilealchemist-pipeline plan

```sh
tilealchemist-pipeline plan CONFIG [OPTIONS]
```

Run once, after `tilealchemist setup CONFIG`. It resolves the source, walks
the archive's directory, splits the entries and gaps into shards of equal
blob bytes, and writes `plan/`. The workers take the archive's URL and
metadata from there, so every shard reads the same build.

| Option | Default | Description |
| --- | --- | --- |
| `--source NAME` | `openfreemap` | The [source](sources.md) that finds the archive. A run config without `schema` takes the source's. |
| `--source-url URL` | None | The archive's URL, for a source that takes one. |
| `--shards N` | `1` | How many shards to split the run into. No upper limit; keep to your orchestrator's. |
| `--transform-processes N` | One per CPU core | Processes for each worker's `convert`. |
| `--min-zoom N`, `--max-zoom N` | The run config's | The zoom range. |

An empty value counts as not given. Before it writes `plan/`, `plan` fails
if:

- the working directory already holds `plan/`, `shards/` or `parts/`;
- the source isn't installed, or gets a `--source-url` it doesn't take or
  lacks one it needs;
- the source and the run config name different schemas, or neither names
  one;
- the run config is invalid, a profile can't be loaded, or two profiles
  share a `name`;
- the
  [attribution](https://github.com/tilelab/tilealchemist/blob/main/docs/reference/run-config.md#attribution)
  can't be composed, or the archive fails the
  [schema check](https://github.com/tilelab/tilealchemist/blob/main/docs/reference/schemas.md#the-schema-check).

## tilealchemist-pipeline work

```sh
tilealchemist-pipeline work --shard N
```

Run once per shard, after `tilealchemist setup plan/layers.toml`. It fetches
shard `N` into `shards/N.pmtiles`, converts it into one part per layer it
has tiles for, deletes the shard archive, and writes `parts/N/done` last. It
reads only `plan/` and writes only shard `N`'s files.

## tilealchemist-pipeline merge

```sh
tilealchemist-pipeline merge --layer NAME [--output PATH]
```

Run once per layer, after all shards. It joins `parts/*/<layer>.pmtiles`
with `pmtiles merge` and moves the result to `PATH`, by default
`layers/<layer>.pmtiles`. It fails if a shard hasn't written
`parts/N/done` or no shard has a part for the layer; a shard without a part
is fine. On first use it downloads the pinned go-pmtiles release into the
user cache, unless `TILEALCHEMIST_PMTILES` names another `pmtiles` binary.
`pmtiles merge` checks all parts before it prints anything; until then an
`update:` line every 15 seconds says how long it has run.

## Run directory

```
plan/                 written by plan
  plan.json           the settings every later step reads
  layers.toml         the run config the workers use, paths relative to plan/
  shard-NNN.bin       one manifest per shard
  profiles/, plugins/ copies of the run's profiles and plugin directories
shards/N.pmtiles      shard N's archive, while it converts
parts/N/              written by shard N's worker
  <layer>.pmtiles     its part of each layer
  done                empty, written last
layers/               written by merge, unless given --output
  <layer>.pmtiles     the layer
```

Every step after `plan` refuses a `plan/` that another
tilealchemist-pipeline version wrote, so a run uses one version throughout.
