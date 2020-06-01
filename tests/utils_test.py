import unittest
import numpy as np
from shapely.geometry import Point, Polygon, LineString

import sys
sys.path.append('..')
import urbanpy as up

class UtilTest(unittest.TestCase):
    def test_xy_swap(self):
        '''
        Test coordinate switch for GeoDataFrame, Series, Points, Polygons and LineStrings
        '''

        p = Point(-77.,-12.)
        l = LineString([[-77.,-12.], [-78., -13.]])
        poly = Polygon([(-77., -12.), (-78., -11.), (-77., -11.)])

        swapped_p = up.utils.swap_xy(p)
        swapped_l = up.utils.swap_xy(l)
        swapped_poly = up.utils.swap_xy(poly)

        self.assertEqual(list(swapped_p.coords), [(-12.0, -77.0)])
        self.assertEqual(list(swapped_l.coords), [(-12.0, -77.0), (-13.0, -78.0)])
        self.assertEqual(list(swapped_poly.exterior.coords), \
                        [(-12.0, -77.0), (-11.0, -78.0), (-11.0, -77.0), (-12.0, -77.0)])

    def test_nn_search(self):
        '''
        Test NN BallTree implementation

        * Test with haversine distance
        * Test with euclidean distance
        * Test empty series
        '''

        #Input features
        tree_features = np.array([[-77,-12],[-78,-15],[0,0],[45,23],[2,5]])
        query_features = np.array([[0,-1],[-76,-11],[-1,-1],[200,23]])

        #Haversine
        dist, idx = up.utils.nn_search(tree_features, query_features)

        self.assertEqual(dist.all(), np.array([[111.19492664],[114.18057105],[157.24938127],[8850.65659794]]).all())
        self.assertEqual(idx.all(), np.array([[2],[0],[2],[1]]).all())

        #Euclidean
        dist, idx = up.utils.nn_search(tree_features, query_features, 'euclidean')
        self.assertEqual(dist.all(), np.array([[1.],[1.41421356],[1.41421356],[155.]]).all())
        self.assertEqual(idx.all(), np.array([[2],[0],[2],[3]]).all())

        try:
            up.utils.nn_search([],[])
        except Exception as err:
            self.assertEqual(type(err), ValueError)

    def test_t2l(self):
        '''
        Tests tuples to list function.

        * Test within a JSON
        * Test using __geo_interface__

        '''

        json = {'type': 'FeatureCollection', 'features': [{'id': 0, 'geometry': {'coordinates': (((-77, -12), (-77.1, -12.1)))}}]}

        expected_json = {'type': 'FeatureCollection', 'features': [{'id': 0, 'geometry': {'coordinates': [[[-77, -12], [-77.1, -12.1]]]}}]}

        self.assertEqual(up.utils.tuples_to_lists(json), expected_json)
if __name__ == '__main__':
    unittest.main()
