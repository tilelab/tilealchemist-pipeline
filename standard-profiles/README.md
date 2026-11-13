# Standard profiles

Three profiles for any source. `.github/workflows/standard-layers.yml`
builds them monthly from the OpenFreeMap planet and publishes them as
GitHub Releases.

| Profile | Layer | Example style |
| --- | --- | --- |
| `land.py` | `land`: each tile minus its surface water; gaps become full squares. | [`examples/land.json`](examples/land.json) |
| `cropped_waterways.py` | `cropped-waterways`: waterway lines minus the same water, with their properties. | [`examples/cropped-waterways.json`](examples/cropped-waterways.json) |
| `shoreline.py` | `shoreline`: the outline of the same water as lines, without the edges each tile clipped it at. | [`examples/shoreline.json`](examples/shoreline.json) |

Protomaps' `earth` layer still contains lakes and rivers, and OpenMapTiles
has no land layer at all. A style that treats land as a layer of its own
needs the water cut out, and waterways that stop at the shore. A line
layer on `land` draws its whole outline, including the straight edges
where each tile is cut off; wide lines show them as a grid. `shoreline`
holds only the shore.

## Use the published layers

Download them from
[`land-latest`](https://github.com/tilelab/tilealchemist-pipeline/releases/tag/land-latest),
[`cropped-waterways-latest`](https://github.com/tilelab/tilealchemist-pipeline/releases/tag/cropped-waterways-latest)
and
[`shoreline-latest`](https://github.com/tilelab/tilealchemist-pipeline/releases/tag/shoreline-latest);
the release notes have the command that downloads and joins split files.
Nothing is hosted for you: serve the files from anything that answers HTTP
range requests, and load them with the
[PMTiles protocol](https://github.com/protomaps/PMTiles):

```js
import { Protocol } from "pmtiles";

const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      land: { type: "vector", url: "pmtiles://https://example.com/land.pmtiles" },
    },
    layers: [
      { id: "land", type: "fill", source: "land", "source-layer": "land" },
    ],
  },
});
```

## Build them yourself

`layers.toml` builds all three and names no schema, so you choose the source:
`tilealchemist-pipeline plan` takes the schema of its `--source`, as in
[Run the pipeline on one machine](../docs/tutorials/run-the-pipeline-on-one-machine.md).
For `tilealchemist convert`, add the `schema` of your archive. Protomaps has
no waterway lines below zoom level 9, so from Protomaps `cropped-waterways`
needs `max_zoom` 9 or higher.

## License

The code is [MIT](../LICENSE)-licensed. A layer's data keeps the license of
the archive it was built from, and its attribution carries the archive's
own through `{source}` in `layers.toml`.
