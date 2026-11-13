"""CI's test plugin: OpenFreeMap and OpenMapTiles under names of its own.

It only renames, so test.yml exercises the plugin path, not new code. See
tilealchemist's docs/how-to-guides/write-a-schema-plugin.md.
"""
from tilealchemist.schemas.base import TileSchema
from tilealchemist.schemas.openmaptiles import OpenMapTilesSchema
from tilealchemist_pipeline.sources.openfreemap import OpenFreeMapSource


class TestPluginSchema(OpenMapTilesSchema):
    """OpenMapTiles, installed as `test-plugin`."""

    name: str = "test-plugin"


TEST_PLUGIN: TestPluginSchema = TestPluginSchema()


class TestPluginSource(OpenFreeMapSource):
    """OpenFreeMap, read with the `test-plugin` schema."""

    schema: TileSchema = TEST_PLUGIN
