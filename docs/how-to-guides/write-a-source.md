# Write a source

A source tells `plan` where the archive is. Write one to read an archive the
shipped sources don't find, such as your own mirror. A source is a plugin,
like tilealchemist's schemas; see its
[Write a schema plugin](https://github.com/tilelab/tilealchemist/blob/main/docs/how-to-guides/write-a-schema-plugin.md).

## Step 1: Write the source

Subclass `Source`, return the archive from `resolve()`, and optionally set
the schema its archives are in:

```python
# my_source.py
from tilealchemist.schemas.base import TileSchema
from tilealchemist.schemas.openmaptiles import OPENMAPTILES

from tilealchemist_pipeline.sources.base import ResolvedSource, Source


class MirrorSource(Source):
    schema: TileSchema = OPENMAPTILES

    def resolve(self) -> ResolvedSource:
        return ResolvedSource("https://tiles.example.org/planet.pmtiles", None)
```

`resolve()` runs once per run and returns the URL and a build label for the
log, or `None`. To take the URL from `--source-url` instead, set
`takes_url = True` and accept `url` in the constructor. `schema` is
optional; without it, the run config's `schema` decides.

## Step 2: Declare the entry point

```toml
# pyproject.toml
[project]
name = "my-source"
version = "1.0.0"
dependencies = ["tilealchemist-pipeline"]

[project.entry-points."tilealchemist.sources"]
mirror = "my_source:MirrorSource"
```

## Step 3: Use it

List the package in the run config's `plugins`, then:

```sh
tilealchemist setup layers.toml
tilealchemist-pipeline plan layers.toml --source mirror
```

`plan` copies plugin directories into `plan/`, and `setup plan/layers.toml`
installs them on every worker.
