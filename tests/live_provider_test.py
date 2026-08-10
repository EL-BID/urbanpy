import pytest

from urbanpy.download import osmnx_graph, search_hdx_dataset
from urbanpy.geofabrik import GeofabrikCatalog


@pytest.mark.live
def test_geofabrik_catalog_live_contract():
    region = GeofabrikCatalog.fetch().resolve("LI")

    assert region.id == "liechtenstein"
    assert str(region.pbf_url) == (
        "https://download.geofabrik.de/europe/liechtenstein-latest.osm.pbf"
    )


@pytest.mark.live
def test_hdx_population_search_live_contract():
    resources = search_hdx_dataset("peru")

    assert not resources.empty
    assert list(resources.columns) == [
        "created",
        "name",
        "population",
        "size_mb",
        "url",
    ]
    assert resources["url"].str.startswith("https://data.humdata.org/").all()


@pytest.mark.live
def test_overpass_osmnx_live_contract():
    graph = osmnx_graph(
        "point", geom=(47.1410, 9.5215), distance=100, network_type="walk"
    )

    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
