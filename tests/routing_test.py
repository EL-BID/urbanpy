import unittest
import geopandas as gpd
import numpy as np

import sys

sys.path.append("../urbanpy")
import urbanpy as up


class RoutingTest(unittest.TestCase):
    # TODO implement tests for google distance matrix and ors distance matrix

    def test_osrm_matrix(self):
        """
        Test OSRM distance and duration matrix
         * Test with normal values, where travel time and distance are available
         * Test without paths, resulting in np.nan values
        """

        # Example test values

        # Sources
        lon, lat = [-77, -77.01, -77.02], [-12, -12.01, -12.02]

        # Valid 3x3 matrix
        lon_1, lat_1 = [-77, -77.01, -77.02], [-12, -12.01, -12.02]

        # Expected NaN columns
        lon_2, lat_2 = [0, -77.12, -77.32], [0, -12.25, -12.6]

        gdf = gpd.GeoDataFrame([], geometry=gpd.points_from_xy(lon, lat))
        gdf_1 = gpd.GeoDataFrame([], geometry=gpd.points_from_xy(lon_1, lat_1))
        gdf_2 = gpd.GeoDataFrame([], geometry=gpd.points_from_xy(lon_2, lat_2))

        # Start OSRM
        up.routing.start_osrm_server("peru", "south-america", "foot")

        # Test 3x3 matrix
        dur, dist = up.routing.compute_osrm_dist_matrix(gdf, gdf_1)

        self.assertIsNone(
            np.testing.assert_allclose(
                dur,
                np.array(
                    [
                        [0.0, 1976.8, 5726.5],
                        [1976.8, 0.0, 3912.9],
                        [5726.5, 3912.9, 0.0],
                    ]
                ),
            )
        )

        self.assertIsNone(
            np.testing.assert_allclose(
                dist,
                np.array(
                    [
                        [0.0, 1424.8, 4128.2],
                        [1424.8, 0.0, 2820.9],
                        [4128.2, 2820.9, 0.0],
                    ]
                ),
            )
        )

        # Testing with missing values
        dur, dist = up.routing.compute_osrm_dist_matrix(gdf, gdf_2)

        self.assertIsNone(
            np.testing.assert_allclose(
                dur,
                np.array(
                    [
                        [np.nan, 26018.2, 26018.2],
                        [np.nan, 24376.4, 24376.4],
                        [np.nan, 23156.7, 23156.7],
                    ]
                ),
                equal_nan=True,
            )
        )

        self.assertIsNone(
            np.testing.assert_allclose(
                dist,
                np.array(
                    [
                        [np.nan, 18816.5, 18816.5],
                        [np.nan, 17625.3, 17625.3],
                        [np.nan, 16761.7, 16761.7],
                    ]
                ),
                equal_nan=True,
            )
        )

        # Close OSRM routing Server
        up.routing.stop_osrm_server("peru", "south-america", "foot")

    def test_nx_route(self):
        """
        Test path finding interface with networkx.

        * Download a small street network
        * Compute paths from known missing paths
        * Compute paths from known available paths

        """
        import osmnx as ox

        # Create graph from point
        point = (41.255676, -95.931338)
        G = up.download.osmnx_graph("point", geom=point, distance=500)

        # Path exists
        source, target = ox.distance.nearest_nodes(
            G, [point[1], point[1] - 0.0025], [point[0], point[0] - 0.0025]
        )

        # Test path length
        self.assertEqual(up.routing.nx_route(G, source, target, "length"), 344.507)

        # Test number of nodes in path
        self.assertEqual(up.routing.nx_route(G, source, target, None), 3)

        # Test with no path
        source, target = 1418626943, 1985246159

        # Test length
        self.assertEqual(up.routing.nx_route(G, source, target, "length"), -1)

        # Test number of nodes
        self.assertEqual(up.routing.nx_route(G, source, target, None), -1)

    def test_google_matrix(self):
        pass

    def test_ors_matrix(self):
        pass


if __name__ == "__main__":
    unittest.main()
