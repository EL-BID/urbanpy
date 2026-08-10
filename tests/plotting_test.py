import geopandas as gpd
from shapely.geometry import Polygon

from urbanpy import plotting


def test_choropleth_map_builds_filtered_figure_without_mutating_input():
    source = gpd.GeoDataFrame(
        {"value": [1.0, 2.0]},
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]),
            Polygon([(2, 0), (3, 0), (3, 1), (2, 0)]),
        ],
        crs="EPSG:4326",
    )
    original = source.copy()

    figure = plotting.choropleth_map(source, "value", source["value"] > 1)

    assert len(figure.data) == 1
    assert list(figure.data[0].locations) == [1]
    assert source.equals(original)
