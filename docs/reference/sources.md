# Sources reference

A **source** finds the URL of the archive a run reads. `plan` picks it with
`--source`, never from the run config, so one run config serves both
`convert` and the pipeline.

| Source | Archive | Schema |
| --- | --- | --- |
| `openfreemap` (default) | The newest completely published OpenFreeMap planet. | `openmaptiles` |
| `protomaps` | The newest Protomaps daily planet. Builds expire after about a week. | `protomaps` |
| `static-url` | The archive at `--source-url`. Use it for your own copy. | The run config's `schema` |

A run config without `schema` takes the source's; one that names another
fails `plan`. Protomaps discourages hotlinking its builds from maps; a
pipeline run reads each byte once, which is fine.

## Source

`tilealchemist_pipeline.sources.base.Source`, installed as an entry point
in the `tilealchemist.sources` group; see
[Write a source](../how-to-guides/write-a-source.md).

| Member | Default | Description |
| --- | --- | --- |
| `resolve()` | Required | Returns `ResolvedSource(url, build)`: the archive's URL and a build label or `None`. `plan` calls it once per run. |
| `schema` | `None` | The `TileSchema` of the source's archives. `None` leaves the schema to the run config. |
| `takes_url` | `False` | Whether the constructor gets `--source-url` as `url`. |
