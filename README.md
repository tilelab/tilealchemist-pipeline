# tilealchemist-pipeline

tilealchemist-pipeline builds [tilealchemist](https://github.com/tilelab/tilealchemist)
layers from a remote PMTiles archive, such as the OpenFreeMap or Protomaps
planet, across many machines and without downloading the archive. It reads
only the tile data each worker needs over HTTP range requests, merges each
layer from the workers' output, and also builds tiles where the archive has
none. It uses the same run configs and profiles as `tilealchemist convert`.

It adds the command `tilealchemist-pipeline` and a reusable GitHub
Actions workflow that runs it as jobs.

## Getting started

```sh
pip install tilealchemist-pipeline
```

Requires Python 3.11 or later. Then follow
[Run the pipeline on one machine](https://github.com/tilelab/tilealchemist-pipeline/blob/main/docs/tutorials/run-the-pipeline-on-one-machine.md)
and [Build layers on GitHub Actions](https://github.com/tilelab/tilealchemist-pipeline/blob/main/docs/tutorials/build-layers-on-github-actions.md).
The
[documentation](https://github.com/tilelab/tilealchemist-pipeline/blob/main/docs/README.md)
covers the rest. To work on the pipeline, see
[CONTRIBUTING.md](https://github.com/tilelab/tilealchemist-pipeline/blob/main/CONTRIBUTING.md).

Ready-made `land`, `cropped-waterways` and `shoreline` layers of the
whole world are published monthly as GitHub Releases; see
[standard profiles](https://github.com/tilelab/tilealchemist-pipeline/blob/main/standard-profiles/README.md).

## License and attribution

The code is
[MIT](https://github.com/tilelab/tilealchemist-pipeline/blob/main/LICENSE)-licensed.
Layers carry the attribution of the archive they were built from; see
tilealchemist's
[`attribution`](https://github.com/tilelab/tilealchemist/blob/main/docs/reference/run-config.md#attribution).
