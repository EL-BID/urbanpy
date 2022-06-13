import unittest
import geopandas as gpd
import numpy as np

import sys
sys.path.append('../urbanpy')
import urbanpy as up

class RoutingTest(unittest.TestCase):
    #TODO implement tests for google distance matrix and ors distance matrix

    def test_osrm_matrix(self):
        '''
        Test OSRM distance and duration matrix
         * Test with normal values, where travel time and distance are available
         * Test without paths, resulting in np.nan values
        '''

        #Example test values

        #Sources
        lon, lat = [-77,-77.01,-77.02], [-12,-12.01,-12.02]

        #Valid 3x3 matrix
        lon_1, lat_1 = [-77,-77.01,-77.02], [-12,-12.01,-12.02]

        #Expected NaN columns
        lon_2, lat_2 = [0,-77.12,-77.32], [0,-12.25,-12.6]

        gdf = gpd.GeoDataFrame([], geometry=gpd.points_from_xy(lon, lat))
        gdf_1 = gpd.GeoDataFrame([], geometry=gpd.points_from_xy(lon_1, lat_1))
        gdf_2 = gpd.GeoDataFrame([], geometry=gpd.points_from_xy(lon_2, lat_2))

        #Start OSRM
        up.routing.start_osrm_server('peru', 'south-america', 'foot')

        #Test 3x3 matrix
        dur, dist = up.routing.compute_osrm_dist_matrix(gdf, gdf_1)

        self.assertIsNone(np.testing.assert_allclose(
            dur, np.array([[   0. , 1977.5, 3576.3],
                           [1977.5,    0. , 1761.7],
                           [3576.3, 1761.7,    0. ]])))

        self.assertIsNone(np.testing.assert_allclose(
            dist, np.array([[   0. , 1425.2, 2576.5],
                            [1425.2,    0. , 1268.6],
                            [2576.5, 1268.6,    0. ]])))

        #Testing with missing values
        dur, dist = up.routing.compute_osrm_dist_matrix(gdf, gdf_2)

        self.assertIsNone(np.testing.assert_allclose(
            dur, np.array([[np.nan, 26017.3, 26017.3],
                           [np.nan, 24372.5, 24372.5],
                           [np.nan, 23895.9, 23895.9]]), equal_nan=True))

        self.assertIsNone(np.testing.assert_allclose(
            dist, np.array([[np.nan, 18803.7, 18803.7],
                            [np.nan, 17619.8, 17619.8],
                            [np.nan, 17274.7, 17274.7]]), equal_nan=True))

        #Close OSRM routing Server
        up.routing.stop_osrm_server('peru', 'south-america', 'foot')

    def test_nx_route(self):
        '''
        Test path finding interface with networkx.

        * Download a small street network
        * Compute paths from known missing paths
        * Compute paths from known available paths

        '''

        #Create graph from point
        G = up.download.osmnx_graph('point', geom=(41.255676, -95.931338), distance=500)

        #Path exists
        source, target = 6564221455, 134104548
        
        #Test path length
        self.assertEqual(up.routing.nx_route(G, source, target, 'length'), 642.385)

        #Test number of nodes in path
        self.assertEqual(up.routing.nx_route(G, source, target, None), 5)

        #Test with no path
        source, target = 1418626943, 1985246159

        #Test length
        self.assertEqual(up.routing.nx_route(G, source, target, 'length'), -1)

        #Test number of nodes
        self.assertEqual(up.routing.nx_route(G, source, target, None), -1)

    def test_google_matrix(self): pass

    def test_ors_matrix(self): pass

if __name__ == '__main__':
    unittest.main()
