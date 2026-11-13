# Run the pipeline on one machine

You build a land layer of the whole world, up to zoom level 4, from the
newest Protomaps planet without downloading it, by running the pipeline's
three steps by hand. It takes about 10 minutes and downloads about 6 MB.
You need Python 3.11 or later.

## Step 1: Install and write the run config

```sh
mkdir world-land && cd world-land
python3 -m venv .venv && source .venv/bin/activate
pip install tilealchemist-pipeline
```

Save the `land.py` profile from tilealchemist's
[tutorial](https://github.com/tilelab/tilealchemist/blob/main/docs/tutorials/build-your-first-layer.md#step-3-write-a-profile),
and next to it:

```toml
# layers.toml
profiles = ["land.py"]
```

## Step 2: Plan

```sh
tilealchemist setup layers.toml
tilealchemist-pipeline plan layers.toml --source protomaps --max-zoom 4 --shards 2
```

`plan` asks the `protomaps` **source** for the newest build and takes its
schema, as the run config names none. It reads only the part of the
archive's directory that zoom levels 0 to 4 need and splits the entries
into two **shards**. Its log ends with each shard's share, about 3 MB
each. It writes `plan/`: the plan, one manifest per shard, and copies of
the run config and profile.

## Step 3: Build the shards

```sh
tilealchemist setup plan/layers.toml
tilealchemist-pipeline work --shard 0
tilealchemist-pipeline work --shard 1
```

`work` fetches only the shard's entries in as few range requests as
possible, runs `convert` on them, and writes the shard's **part** of the
layer to `parts/0/land.pmtiles` or `parts/1/land.pmtiles`. Here your
machine is the one **worker**; the shards don't depend on each other, so on
a real run many workers build them at once.

## Step 4: Merge

```sh
tilealchemist-pipeline merge --layer land
```

`merge` joins the parts into `layers/land.pmtiles` without decoding a
tile. On first use it downloads the pinned go-pmtiles release. To see the
layer, drop it onto [pmtiles.io](https://pmtiles.io).

## Next steps

- [Build layers on GitHub Actions](build-layers-on-github-actions.md) runs
  the same steps as jobs.
- To spread the shards over machines, copy `plan/` to each, run step 3
  there, and collect every `parts/N/` under `parts/` for the merge. The
  [run directory](../reference/cli.md#run-directory) says what each step
  reads and writes.
- [How the pipeline works](../explanation/architecture.md) explains why.
