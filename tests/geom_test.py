import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon

from urbanpy import geom


def _city():
    polygon = Polygon(
        [(-77.05, -12.10), (-77.00, -12.10), (-77.00, -12.05), (-77.05, -12.05)]
    )
    return gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326")


def test_merge_geom_downloads_unions_local_polygons():
    left = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])], crs="EPSG:4326"
    )
    right = gpd.GeoDataFrame(
        geometry=[Polygon([(1, 0), (2, 0), (2, 1), (1, 0)])], crs="EPSG:4326"
    )

    merged = geom.merge_geom_downloads([left, right])

    assert len(merged) == 1
    assert merged.geometry.iloc[0].covers(left.geometry.iloc[0])
    assert merged.geometry.iloc[0].covers(right.geometry.iloc[0])


def test_filter_and_remove_population_points():
    population = pd.DataFrame(
        {
            "longitude": [-77.03, -77.01, -78.0],
            "latitude": [-12.08, -12.06, -13.0],
            "population": [10, 20, 30],
        }
    )

    filtered = geom.filter_population(population, _city())
    remaining = geom.remove_features(filtered, [-77.04, -12.09, -77.02, -12.07])

    assert list(filtered["population"]) == [10, 20]
    assert list(remaining["population"]) == [20]


def test_hexagon_generation_merge_and_downsampling():
    hexagons = geom.gen_hexagons(8, _city())
    points = gpd.GeoDataFrame(
        {"population": [3, 7]},
        geometry=[Point(-77.03, -12.08), Point(-77.01, -12.06)],
        crs="EPSG:4326",
    )

    merged = geom.merge_shape_hex(
        hexagons, points, {"population": "sum"}, predicate="within"
    )
    coarse = geom.resolution_downsampling(
        merged.fillna({"population": 0}), "hex", 7, {"population": "sum"}
    )

    assert not hexagons.empty
    assert merged["population"].sum() == 10
    assert coarse["population"].sum() == 10
    assert coarse.crs == hexagons.crs


def test_merge_shape_hex_can_be_rerun_on_its_own_result():
    hexagons = geom.gen_hexagons(8, _city())
    points = gpd.GeoDataFrame(
        {"population": [3, 7]},
        geometry=[Point(-77.03, -12.08), Point(-77.01, -12.06)],
        crs="EPSG:4326",
    )

    first = geom.merge_shape_hex(
        hexagons, points, {"population": "sum"}, predicate="within"
    )
    second = geom.merge_shape_hex(
        first, points, {"population": "sum"}, predicate="within"
    )

    assert second["population"].equals(first["population"])
    assert second.crs == first.crs
