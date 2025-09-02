import unittest
import geopandas as gpd
from shapely.geometry import Polygon

import sys

sys.path.append("../urbanpy")

# Direct module reference to patch internals
import urbanpy.download.download as dl


class FakeGeometry:
    def __init__(self, geojson):
        self.geojson = geojson


class FakeFeatureCollection:
    def __init__(self, features):
        # features is a list of GeoJSON-like feature dicts
        self._features = features
        self._type = "FeatureCollection"
        self._columns = features[0]["properties"].keys() if features else []

    def getInfo(self):
        return {
            "features": self._features,
            "type": "FeatureCollection",
            "columns": self._columns,
        }


class FakeImage:
    def __init__(self, bands):
        self._bands = bands

    def select(self, bands):
        # In real EE, select returns a new image; here keep same
        self._bands = bands
        return self

    def reduceRegions(
        self, collection, reducer, scale, tileScale
    ):  # noqa: N802 (match EE signature)
        # Enrich each feature with synthetic band stats
        enriched = []
        for idx, feat in enumerate(collection._features):
            props = feat["properties"].copy()
            for i, b in enumerate(self._bands):
                # Deterministic numeric value per band & feature
                props[b] = float(idx + i)
            enriched.append(
                {
                    "type": "Feature",
                    "geometry": feat["geometry"],
                    "properties": props,
                }
            )
        return FakeFeatureCollection(enriched)


class FakeImageCollection:
    def __init__(self, bands):
        self._bands = bands

    def filterDate(self, start, end):  # noqa: N802
        return self

    def filterBounds(self, roi):  # noqa: N802
        return self

    def mosaic(self):
        return FakeImage(self._bands)


class FakeReducer:
    @staticmethod
    def mean():
        return "mean"

    @staticmethod
    def median():
        return "median"

    @staticmethod
    def first():
        return "first"


class FakeEE:
    Reducer = FakeReducer

    @staticmethod
    def ImageCollection(name):  # noqa: N802
        # Return collection with all 64 bands by default
        return FakeImageCollection(dl.VALID_EMBEDDING_BANDS.copy())

    @staticmethod
    def Feature(geometry, properties):  # noqa: N802
        return {
            "type": "Feature",
            "geometry": geometry.geojson,
            "properties": properties,
        }

    @staticmethod
    def FeatureCollection(features):  # noqa: N802
        return FakeFeatureCollection(features)

    class Geometry:
        def __init__(self, geojson):
            self.geojson = geojson

        @staticmethod
        def Rectangle(coords):  # mimic ee.Geometry.Rectangle
            return FakeGeometry(
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [coords[0], coords[1]],
                            [coords[2], coords[1]],
                            [coords[2], coords[3]],
                            [coords[0], coords[3]],
                            [coords[0], coords[1]],
                        ]
                    ],
                }
            )


class GoogleEmbeddingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch module with fake EE
        dl.ee = FakeEE
        dl.EE_AVAILABLE = True

        # Simple square polygon GeoDataFrame with two features
        poly1 = Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01)])
        poly2 = Polygon([(0.02, 0.02), (0.03, 0.02), (0.03, 0.03), (0.02, 0.03)])
        cls.gdf = gpd.GeoDataFrame(
            {"name": ["a", "b"]}, geometry=[poly1, poly2], crs="EPSG:4326"
        )

    def test_happy_path_mean(self):
        bands_subset = ["A00", "A01", "A02"]
        result = dl.google_satellite_embeddings(
            self.gdf,
            year=dl.ALPHAEARTH_DEFAULT_YEAR,
            bands=bands_subset,
            reducer="mean",
        )
        # Expect same number of rows
        self.assertEqual(len(result), len(self.gdf))
        # Expect all requested bands present
        for b in bands_subset:
            self.assertIn(b, result.columns)

    def test_invalid_year(self):
        with self.assertRaises(ValueError):
            dl.google_satellite_embeddings(self.gdf, year=dl.ALPHAEARTH_YEAR_MAX + 1)

    def test_invalid_reducer(self):
        with self.assertRaises(ValueError):
            dl.google_satellite_embeddings(self.gdf, reducer="std")

    def test_invalid_band(self):
        with self.assertRaises(ValueError):
            dl.google_satellite_embeddings(
                self.gdf, bands=["A00", "A99"]
            )  # A99 out of range

    def test_too_many_features(self):
        big_gdf = gpd.GeoDataFrame(
            {"id": list(range(dl.GEE_MAX_FEATURES_PER_REQUEST + 1))},
            geometry=[self.gdf.geometry.iloc[0]]
            * (dl.GEE_MAX_FEATURES_PER_REQUEST + 1),
            crs="EPSG:4326",
        )
        with self.assertRaises(ValueError):
            dl.google_satellite_embeddings(big_gdf)

    def test_format_results_empty(self):
        # Directly test _format_ee_embedding_results with empty FeatureCollection
        class EmptyFC:
            def getInfo(self):
                return {"features": []}

        returned = dl._format_ee_embedding_results(
            self.gdf, EmptyFC(), ["A00"], dl.ALPHAEARTH_DEFAULT_YEAR
        )
        # Should be identical to original (no added bands)
        self.assertEqual(list(returned.columns), list(self.gdf.columns))
        self.assertTrue(returned.equals(self.gdf))

    def test_default_all_bands_and_median(self):
        # Use default bands (None) and median reducer path
        result = dl.google_satellite_embeddings(self.gdf, reducer="median")
        # Expect all 64 bands
        for b in dl.VALID_EMBEDDING_BANDS:
            self.assertIn(b, result.columns)
        self.assertEqual(len(result), len(self.gdf))

    def test_gdf_to_ee_fc_feature_count(self):
        # Build EE FC via helper and ensure feature count matches
        fc = dl._gdf_to_ee_fc(self.gdf)
        self.assertEqual(len(fc.getInfo()["features"]), len(self.gdf))

    def test_ee_unavailable_import_error(self):
        # Temporarily mark EE unavailable and ensure ImportError raised
        prev_flag = dl.EE_AVAILABLE
        dl.EE_AVAILABLE = False
        try:
            with self.assertRaises(ImportError):
                dl.google_satellite_embeddings(self.gdf)
        finally:
            dl.EE_AVAILABLE = prev_flag


if __name__ == "__main__":
    unittest.main()
