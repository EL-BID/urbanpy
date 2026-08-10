"""Geometry operations exposed by UrbanPy."""

from .geom import (
    filter_population,
    gen_hexagons,
    merge_geom_downloads,
    merge_shape_hex,
    osmnx_coefficient_computation,
    overlay_polygons_hexs,
    remove_features,
    resolution_downsampling,
)

__all__ = [
    "filter_population",
    "gen_hexagons",
    "merge_geom_downloads",
    "merge_shape_hex",
    "osmnx_coefficient_computation",
    "overlay_polygons_hexs",
    "remove_features",
    "resolution_downsampling",
]
