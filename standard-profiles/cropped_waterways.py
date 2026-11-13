"""Cropped waterways: waterway lines outside water polygons. See README.md.

Keeps a style built on the land layer from stroking rivers over water.
"""
from tilealchemist.profiles import water
from tilealchemist.profiles.base import Profile
from tilealchemist.profiles.features import WATERWAYS, Feature
from tilealchemist.profiles.tile import Tile
from tilealchemist.schemas.base import TileSchema


class CroppedWaterwaysProfile(Profile):
    """The source's waterways, with the parts inside water cut away."""

    name: str = "cropped-waterways"

    def layer_fields(self, schema: TileSchema) -> dict[str, str]:
        # The properties pass through unchanged.
        return schema.fields_for(WATERWAYS)

    def transform(self, tile: Tile) -> list[Feature]:
        return [waterway.with_geometry(
                    water.subtract_water(tile, waterway.geometry))
                for waterway in tile.features(WATERWAYS)]


PROFILE: type[Profile] = CroppedWaterwaysProfile
