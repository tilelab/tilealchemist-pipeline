# Build layers on GitHub Actions

You add a workflow to your own repository that builds a land layer of the
whole world across many GitHub Actions jobs and returns it as an artifact.
You need a GitHub repository where you can run workflows.

## Step 1: Commit the run config and profile

Commit the `land.py` profile from tilealchemist's
[tutorial](https://github.com/tilelab/tilealchemist/blob/main/docs/tutorials/build-your-first-layer.md#step-3-write-a-profile)
and this run config. `max_zoom = 8` keeps the first run short; 14 is full
detail.

```toml
# layers.toml
max_zoom = 8
profiles = ["land.py"]
```

## Step 2: Add the workflow

```yaml
# .github/workflows/land.yml
on: workflow_dispatch

jobs:
  build:
    uses: tilelab/tilealchemist-pipeline/.github/workflows/_pipeline.yml@v1.0.0
    with:
      config: layers.toml
      source: protomaps
```

`build` calls the pipeline's release `v1.0.0`. The pipeline reads
`layers.toml` and `land.py` from your commit. The run config names no
`schema`, so the run takes the `protomaps` source's.

## Step 3: Run it

Start the workflow from your repository's Actions tab. The pipeline's jobs
appear as `prepare-shards` (plan), `build-shards` (120 shards by default)
and `merge`. When they finish, the run's summary lists the artifact
`land-pmtiles` with `land.pmtiles`. A later job can download it:

```yaml
  use:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v8
        with:
          name: land-pmtiles
```

## Next steps

- To publish the layer as a GitHub Release, see
  [`_publish-release.yml`](../reference/workflows.md#_publish-releaseyml).
- To size the run, see
  [Choose the number of shards](../how-to-guides/choose-the-number-of-shards.md).
