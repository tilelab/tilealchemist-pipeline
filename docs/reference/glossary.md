# Glossary

Terms shared with tilealchemist, such as archive, blob, entry and layer, are
in its [glossary](https://github.com/tilelab/tilealchemist/blob/main/docs/reference/glossary.md).

| Term | Meaning |
| --- | --- |
| gap | A tile ID the archive has no tile for. A shard archive points it at one empty tile. |
| manifest | A shard's entries as `plan` writes them, `plan/shard-NNN.bin`. |
| orchestrator | Whatever starts the steps, such as `_pipeline.yml` or a shell script. |
| part | One shard's output for one layer, `parts/N/<layer>.pmtiles`. |
| run | One plan, its shards and its merges. |
| run config | The TOML file listing a run's profiles, schema, zoom range, attribution and plugins. `plan` writes the workers' copy, `plan/layers.toml`. |
| shard | One of the plan's equal shares of the run's entries, numbered from 0. |
| shard archive | A shard fetched into a PMTiles file, `shards/N.pmtiles`. |
| source | The plugin that finds the URL of the archive a run reads. |
| worker | A machine or job running `work`, for one shard or several in turn. |
