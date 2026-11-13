"""Land: each tile's buffered square minus its water. See README.md."""
from shapely.geometry.base import BaseGeometry

from tilealchemist.profiles import water
from tilealchemist.profiles.base import Profile
from tilealchemist.profiles.tile import Tile


class LandProfile(Profile):
    """Land polygons, the inverse of the source's surface water."""

    name: str = "land"

    def transform(self, tile: Tile) -> BaseGeometry:
        return water.subtract_water(tile, tile.buffered_square)


PROFILE: type[Profile] = LandProfile
