# Contributing to tilealchemist-pipeline

Code and documentation follow tilealchemist's
[CONTRIBUTING.md](https://github.com/tilelab/tilealchemist/blob/main/CONTRIBUTING.md).
Pipeline terms go into this repository's
[glossary](docs/reference/glossary.md), and the pipeline imports from
tilealchemist only what
[its boundary](docs/explanation/architecture.md#the-boundary-with-tilealchemist)
allows.

## Set up

Clone tilealchemist next to the pipeline and install both editable:

```sh
git clone https://github.com/tilelab/tilealchemist.git
git clone https://github.com/tilelab/tilealchemist-pipeline.git && cd tilealchemist-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../tilealchemist -e . --config-settings editable_mode=compat
pip install pylint==4.1.2 mypy==2.4.1 types-requests types-shapely
```

`editable_mode=compat` installs plain path entries, which mypy can follow.

## Run the checks

```sh
pylint tilealchemist_pipeline
mypy
```

CI's `lint.yml` runs both and `test.yml` the real `_pipeline.yml` with two
shards, both with the tilealchemist release from PyPI that users get. To
try a change locally, follow
[Run the pipeline on one machine](docs/tutorials/run-the-pipeline-on-one-machine.md).

## Release

Set `version` in `pyproject.toml` and push the tag `v<version>`.
`release.yml` checks that they match, runs `lint.yml` and `test.yml`, and
publishes to PyPI. The tilealchemist version it needs must be on PyPI
first. Raise the major version when a command, option, run directory name,
or workflow input or output changes.

Each version can be published only once, so try a release as a candidate
such as `1.0.0rc1` first and retry a failed one as `rc2`. pip takes a
candidate only when it is named, or while no final release exists:

```sh
pip install tilealchemist-pipeline==1.0.0rc1
```
