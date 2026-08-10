from importlib.metadata import version

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, Polygon

from urbanpy import accessibility, geom, routing


def test_h3_v4_public_api_generates_valid_crs_aware_hexagons():
    assert int(version("h3").split(".", 1)[0]) >= 4
    city = gpd.GeoDataFrame(
        geometry=[
            Polygon(
                [
                    (-77.05, -12.10),
                    (-77.00, -12.10),
                    (-77.00, -12.05),
                    (-77.05, -12.05),
                ]
            )
        ],
        crs="EPSG:4326",
    )

    result = geom.gen_hexagons(8, city)

    assert not result.empty
    assert result.crs == city.crs
    assert result["hex"].is_unique


def test_osmnx_v2_nearest_nodes_uses_longitude_then_latitude(monkeypatch):
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:4326"
    graph.add_node(1, x=-77.04, y=-12.08)
    graph.add_node(2, x=-77.03, y=-12.07)
    graph.add_edge(1, 2, length=100.0)
    nearest = []

    def fake_nearest(_graph, x, y):
        nearest.append((x, y))
        return 1

    monkeypatch.setattr(routing.routing.ox, "nearest_nodes", fake_nearest)

    result = routing.isochrone_from_graph(graph, [(-77.04, -12.08)], [5], "walking")

    assert nearest == [(-77.04, -12.08)]
    assert result.crs.to_string() == "EPSG:4326"
    assert result.geometry.notna().all()


def test_pressure_map_preserves_crs_for_already_projected_inputs():
    blocks = gpd.GeoDataFrame(
        {"demand": [10]},
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 0)])],
        crs="EPSG:3857",
    )
    pois = gpd.GeoDataFrame(
        geometry=[Point(25, 25)],
        crs="EPSG:3857",
    )

    result = accessibility.pressure_map(blocks, pois, "demand", buffer_size=200)

    assert result.crs == blocks.crs
    assert result.loc[0, "ds"] == 5
