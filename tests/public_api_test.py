import urbanpy


EXPECTED_EXPORTS = {
    "accessibility": {"hu_access_map", "pressure_map", "travel_times"},
    "download": {
        "HDXProviderError",
        "get_hdx_dataset",
        "hdx_dataset",
        "hdx_fb_population",
        "nominatim_osm",
        "osmnx_graph",
        "overpass",
        "overpass_pois",
        "search_hdx_dataset",
    },
    "geom": {
        "filter_population",
        "gen_hexagons",
        "merge_geom_downloads",
        "merge_shape_hex",
        "osmnx_coefficient_computation",
        "overlay_polygons_hexs",
        "remove_features",
        "resolution_downsampling",
    },
    "plotting": {"choropleth_map"},
    "utils": {
        "HDX_POPULATION_TYPES",
        "create_duration_labels",
        "geo_boundary_to_polygon",
        "get_hdx_label",
        "nn_search",
        "overpass_to_gdf",
        "shell_from_geometry",
        "swap_xy",
        "to_overpass_query",
    },
}


def test_public_feature_exports_are_explicit_and_stable():
    for module_name, expected in EXPECTED_EXPORTS.items():
        module = getattr(urbanpy, module_name)
        assert set(module.__all__) == expected
        assert all(hasattr(module, name) for name in expected)


def test_internal_transport_names_are_not_exported():
    for module_name in EXPECTED_EXPORTS:
        module = getattr(urbanpy, module_name)
        assert not any(name.startswith("_") for name in module.__all__)
        assert "requests" not in module.__all__
        assert "pd" not in module.__all__
