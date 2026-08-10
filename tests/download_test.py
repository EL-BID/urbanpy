from datetime import date

import geopandas as gpd
import pytest
import responses
from shapely.geometry import Polygon

from urbanpy import download
from urbanpy.download import download as download_module


def test_nominatim_requires_contact_email():
    with pytest.raises(ValueError, match="provide an email"):
        download.nominatim_osm("Lima, Peru")


def test_nominatim_parses_captured_geojson():
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"display_name": "Lima, Peru"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-77.1, -12.2],
                            [-76.9, -12.2],
                            [-76.9, -12.0],
                            [-77.1, -12.2],
                        ]
                    ],
                },
            }
        ],
    }
    with responses.RequestsMock() as captured:
        captured.get(
            "https://nominatim.openstreetmap.org/search.php", json=payload
        )
        result = download.nominatim_osm("Lima, Peru", email="dev@example.org")

    assert list(result["display_name"]) == ["Lima, Peru"]
    assert result.crs.to_string() == "EPSG:4326"


def test_search_hdx_dataset_uses_captured_provider_records(monkeypatch):
    records = [
        {
            "created": "2024-01-02T00:00:00",
            "name": "population_per_2024.csv",
            "size": 2**20,
            "download_url": "https://example.org/population.csv",
            "url": "https://example.org/population.csv",
        },
        {
            "created": "2024-01-02T00:00:00",
            "name": "metadata.pdf",
            "size": 100,
            "download_url": "https://example.org/metadata.pdf",
            "url": "https://example.org/metadata.pdf",
        },
    ]
    monkeypatch.setattr(
        download_module.Dataset, "search_in_hdx", lambda _query: [object()]
    )
    monkeypatch.setattr(
        download_module.Dataset, "get_all_resources", lambda _datasets: records
    )

    result = download.search_hdx_dataset("Peru")

    assert len(result) == 1
    assert result.iloc[0].to_dict() == {
        "created": date(2024, 1, 2),
        "name": "population_per_2024.csv",
        "population": "Overall population density",
        "size_mb": 1.0,
        "url": "https://example.org/population.csv",
    }


def test_osmnx_graph_validates_required_arguments(capsys):
    assert download.osmnx_graph("polygon") is None
    assert "provide a polygon" in capsys.readouterr().out.lower()


def test_overpass_accepts_a_local_polygon_mask(monkeypatch):
    class Response:
        status_code = 200
        reason = "OK"

        @staticmethod
        def json():
            return {"elements": []}

    monkeypatch.setattr(
        download_module.requests, "get", lambda *_args, **_kwargs: Response()
    )
    monkeypatch.setattr(
        download_module, "overpass_to_gdf", lambda *_args: ("gdf", None)
    )
    mask = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])], crs="EPSG:4326"
    )

    assert download.overpass("node", {"amenity": "school"}, mask) == ("gdf", None)
