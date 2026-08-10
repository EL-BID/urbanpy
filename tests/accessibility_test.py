import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from urbanpy.accessibility import accessibility as accessibility_module


def test_friction_is_vectorized_and_zero_beyond_catchment():
    result = accessibility_module.friction(np.array([0.0, 500.0, 1500.0]), 1000)

    assert result.shape == (3,)
    assert result[0] > result[1] > result[2]
    assert result[2] == 0


def test_travel_times_uses_cached_centroids_and_explicit_units(monkeypatch):
    inputs = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 0)])],
        crs="EPSG:3857",
    )
    pois = gpd.GeoDataFrame(
        {"lat": [1.5], "lon": [1.5]}, geometry=[Point(1.5, 1.5)], crs="EPSG:3857"
    )
    calls = []

    def fake_nn_search(*, tree_features, query_features, metric):
        calls.append((tree_features.copy(), query_features.copy(), metric))
        return np.array([[0.5]]), np.array([[0]])

    monkeypatch.setattr(accessibility_module, "nn_search", fake_nn_search)
    monkeypatch.setattr(
        accessibility_module, "osrm_route", lambda origin, destination: (2500, 120)
    )

    result = accessibility_module.travel_times(inputs, pois, col_label="clinic")

    assert len(calls) == 1
    assert calls[0][2] == "haversine"
    assert result.loc[0, "nearest_clinic_ix"] == 0
    assert result.loc[0, "distance_to_nearest_clinic"] == 2.5
    assert result.loc[0, "duration_to_nearest_clinic"] == 2
    assert str(result.loc[0, "duration_to_nearest_clinic_label"]) == "0-15"
