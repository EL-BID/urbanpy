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

    def test_shell_from_geometry(self):
        '''
        Test conversion from array of dicts to list of coordinates
        '''

        #Sample polygon
        inp = [{'lat': -12.1057161, 'lon': -77.0453355},
               {'lat': -12.1046923, 'lon': -77.0451272},
               {'lat': -12.1048769, 'lon': -77.0442775},
               {'lat': -12.1059175, 'lon': -77.0445076},
               {'lat': -12.1057161, 'lon': -77.0453355}]

        self.assertEqual(up.utils.shell_from_geometry(inp), [[-77.0453355, -12.1057161],
                                                             [-77.0451272, -12.1046923],
                                                             [-77.0442775, -12.1048769],
                                                             [-77.0445076, -12.1059175],
                                                             [-77.0453355, -12.1057161]])

    def test_duration_labels(self):
        '''
        Test the custom duration label creation with random integer sampling.

        * Test from 0-10
        * Test from 0-20
        * Test from 10-100

        '''
        inp_1 = np.array([ 1.47499837,  4.44655595,  6.58557897,  8.96218615,  9.21594168])
        inp_2 = np.array([ 7.28246721, 11.57711221,  2.3046021 , 16.37945587, 14.53965395])
        inp_3 = np.array([38.78371215, 91.68736876, 51.42509596, 35.00861296, 52.06796523])

        #Case 0-10
        bins, test = up.utils.create_duration_labels(inp_1)
        self.assertEqual(bins, [0, 15])
        self.assertEqual(test, ['De 0 a 15'])

        #Case 0-20
        bins, test = up.utils.create_duration_labels(inp_2)
        self.assertEqual(bins, [0, 15, 30])
        self.assertEqual(test, ['De 0 a 15', 'De 15 a 30'])

        #Case 10-100
        bins, test = up.utils.create_duration_labels(inp_3)
        self.assertEqual(bins, [0, 15, 30, 45, 60, 90, 120])
        self.assertEqual(test, ['De 0 a 15', 'De 15 a 30', 'De 30 a 45', 'De 45 a 60', 'De 60 a 90', 'De 90 a 120'])

    # def test_t2l(self):
    #     '''
    #     Tests tuples to list function.
    #
    #     * Test within a JSON
    #     * Test using __geo_interface__
    #
    #     '''
    #
    #     json = {'type': 'FeatureCollection', 'features': [{'id': 0, 'geometry': {'coordinates': (((-77, -12), (-77.1, -12.1)))}}]}
    #
    #     expected_json = {'type': 'FeatureCollection', 'features': [{'id': 0, 'geometry': {'coordinates': [[[-77, -12], [-77.1, -12.1]]]}}]}
    #
    #     self.assertEqual(up.utils.tuples_to_lists(json), expected_json)
if __name__ == '__main__':
    unittest.main()
