# Workflows reference

Two reusable GitHub Actions workflows. Callers pin a release, such as
`@v1.0.0`.

## _pipeline.yml

```yaml
uses: tilelab/tilealchemist-pipeline/.github/workflows/_pipeline.yml@v1.0.0
```

Builds a run config's layers. All inputs are strings; empty means unset.

| Input | Default | Description |
| --- | --- | --- |
| `config` | Required | The run config's path in the calling repository, such as `layers.toml`. |
| `source`, `source_url` | `openfreemap`, none | `plan`'s `--source` and `--source-url`. |
| `min_zoom`, `max_zoom` | The run config's | The zoom range. |
| `shards` | `120` | Number of shards, one job each, at most 256. |
| `artifact_namespace` | None | A prefix for the internal artifacts, needed only when one workflow run calls the pipeline twice. |

The pipeline reads the run config and the files it names from the calling
commit, which needs the `contents: read` permission.

Each layer comes back as the artifact `<layer>-pmtiles` holding
`<layer>.pmtiles`, without the namespace prefix.

The jobs are `prepare-shards` (`setup`, `plan`), `build-shards` (`setup`,
`work`, one per shard) and `merge` (one per layer). Matrix jobs don't
cancel each other, so a failed shard can be rerun alone. Every job runs the
pipeline at the commit the caller pinned, and warnings show up as
annotations.

## _publish-release.yml

```yaml
publish-land:
  needs: build
  uses: tilelab/tilealchemist-pipeline/.github/workflows/_publish-release.yml@v1.0.0
  permissions:
    contents: write
  with:
    layer: land
    tag: land-latest
    title: "Global land layer"
    max_zoom: 14
```

Publishes one `<layer>-pmtiles` artifact as a GitHub Release of the calling
repository, with its own token. It uploads into the draft `<tag>-draft`,
retrying each asset and checking its size, and only then replaces the old
release under `tag`, and the tag. A failed upload leaves the old release
in place, and the next run replaces the draft.

| Input | Default | Description |
| --- | --- | --- |
| `layer` | Required | The layer's name. |
| `tag` | Required | The release tag, such as `land-latest`. |
| `title` | Required | The release title. |
| `min_zoom`, `max_zoom` | `0`, required | The zoom range, for the release notes. |

A layer over 2000 MiB is split into `<layer>.pmtiles.partNNN` assets, as
GitHub limits an asset to 2 GiB. The release notes give a
`gh release download` command that also joins the parts.
