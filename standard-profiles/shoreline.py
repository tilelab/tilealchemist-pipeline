"""Shoreline: where each tile's water meets land, as lines. See README.md.

A line layer on land or water polygons draws their whole outline, including
the straight edges where the source cut them off at the tile's buffer. This
layer holds only the real shore.
"""
import shapely
from shapely.geometry.base import BaseGeometry

from tilealchemist.profiles import water
from tilealchemist.profiles.base import Profile
from tilealchemist.profiles.mvt import OUTPUT_GRID_SIZE
from tilealchemist.profiles.tile import Tile

# The crop stays this far inside the buffered square, so clip edges, which
# lie on that square or just outside it, fall away. Shore lines leaving the
# tile end in the buffer, which renderers don't draw. A quarter cell: well
# above float noise, and under half a cell, so the encoder snaps the line
# ends back onto the buffered square.
CLIP_EDGE_MARGIN: float = OUTPUT_GRID_SIZE / 4


class ShorelineProfile(Profile):
    """The outline of the source's surface water, without the clip edges."""

    name: str = "shoreline"

    def transform(self, tile: Tile) -> BaseGeometry | None:
        union: BaseGeometry | None = water.surface_water_union(tile)
        if union is None:
            return None
        # Keeps the outline inside the crop: the shore, without clip edges.
        crop: BaseGeometry = tile.buffered_square.buffer(-CLIP_EDGE_MARGIN)
        shore: BaseGeometry = union.boundary.intersection(crop)
        # Rejoins rings the crop cut apart, so dashes run on.
        merged: BaseGeometry = shapely.line_merge(shore)
        return merged


PROFILE: type[Profile] = ShorelineProfile
