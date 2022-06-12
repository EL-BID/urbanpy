import unittest
import geopandas as gpd
import numpy as np
import networkx as nx
from shapely.geometry import Polygon

import sys
sys.path.append('../urbanpy')
import urbanpy as up

class GeomTest(unittest.TestCase):
    #TODO: implement test for overlay_polygons_hexs and osmnx_coefficient_computation

    def test_merge_geom_download(self):
        '''
        Test Merge several GeoDataFrames from OSM download_osm
        '''

        # Example test values
        gdf1 = up.download.nominatim_osm(query='Jesús María, Lima, Peru')
        gdf2 = up.download.nominatim_osm(query='Lince, Lima, Peru')

        # Merged
        merged_geom = up.geom.merge_geom_downloads([gdf1, gdf2])

        # Difference merged geom with sources
        empty_polygon = merged_geom.difference(gdf1).difference(gdf2)[0]

        # Test empty polygon
        self.assertEqual(Polygon(), empty_polygon)

    def test_filter_population(self):
        '''
        Test filtering of population dataframe with a GeoDataFrame with a polygon geometry.

        * Download population data
        * Download city limits
        * Filter population data within the city limits

        '''

        # Example test values
        datasets_df = up.download.search_hdx_dataset('bolivia')
        pop_df = up.download.get_hdx_dataset(datasets_df, 0)
        polygon_gdf = up.download.nominatim_osm('La Paz, Bolivia', 1)

        # Filter pop
        filtered_points_gdf = up.geom.filter_population(pop_df, polygon_gdf)

        # Get bounding box to test the result
        minx, miny, maxx, maxy = polygon_gdf.geometry.total_bounds

        # Test path length
        self.assertEqual(filtered_points_gdf.shape, filtered_points_gdf.cx[minx:maxx, miny:maxy].shape)

    def test_remove_features(self):
        '''
        Test the removal of a set of features based on bounds.

        * Download population data
        * Download city limits
        * Filter population data within the city limits

        '''

        # Download city limits
        polygon_gdf = up.download.nominatim_osm('La Paz, Bolivia', 1)

        # Example test values
        bounds = polygon_gdf.geometry.centroid.buffer(0.1).total_bounds
        datasets_df = up.download.search_hdx_dataset('bolivia')
        pop_df = up.download.get_hdx_dataset(datasets_df, 0)
        filtered_points_gdf = up.geom.filter_population(pop_df, polygon_gdf)

        # Remove features from bounding box
        features_removed = up.geom.remove_features(filtered_points_gdf, bounds)

        # Bounding box for validation
        minx, miny, maxx, maxy = bounds

        # Test path length
        self.assertEqual(True, features_removed.cx[minx:maxx, miny:maxy].empty)

    def test_gen_hexagons(self):
        '''
        Test the generation of H3 hexagons for a given input GeoDataFrame with a polygon or multipolygon geometry.

        * Download city limits
        * Generate H3 hexagons to fill the city limits

        '''

        # Download city limits
        polygon_gdf = up.download.nominatim_osm('La Paz, Bolivia', 1)

        # Generate hexs
        hex_gdf = up.geom.gen_hexagons(resolution=6, city=polygon_gdf)

        # Test the number of hexagons generated
        self.assertEqual((51, 2), hex_gdf.shape)

    def test_merge_shape_hex(self):
        '''
        Test the aggregation of a metric from a smaller shapes (e.g. Points) with a H3 hexagon GeoDataFrame.

        * Download city limits
        * Download population data
        * Merge data

        '''

        # Download city limits
        polygon_gdf = up.download.nominatim_osm('La Paz, Bolivia', 1)

        # Example test values
        datasets_df = up.download.search_hdx_dataset('bolivia')
        pop_df = up.download.get_hdx_dataset(datasets_df, 0)
        filtered_points_gdf = up.geom.filter_population(pop_df, polygon_gdf)
        hex_gdf = up.geom.gen_hexagons(resolution=6, city=polygon_gdf)

        # Aggregate pop metric
        merged_hex = up.geom.merge_shape_hex(hex_gdf, filtered_points_gdf, agg={'bol_general_2020':'sum'})

        # Sum aggregated metric with hexagons
        population_hexs_sum = merged_hex['bol_general_2020'].sum()

        # Sum metric with spatial filter
        spatial_filter = filtered_points_gdf.geometry.intersects(hex_gdf.geometry.unary_union)
        population_points_sum = filtered_points_gdf[spatial_filter]['bol_general_2020'].sum()

        # Delta
        delta = population_hexs_sum - population_points_sum
        print(delta)

        # Test the diff of aggregated population
        self.assertAlmostEqual(0, delta)

    def test_resolution_downsampling(self):
        '''
        Test downsampling hexagon resolution and aggregating indicated metrics.

        * Download city limits
        * Download population data
        * Merge data

        '''
        # Download city limits
        polygon_gdf = up.download.nominatim_osm('La Paz, Bolivia', 1)

        # Example test values
        datasets_df = up.download.search_hdx_dataset('bolivia')
        pop_df = up.download.get_hdx_dataset(datasets_df, 0)
        filtered_points_gdf = up.geom.filter_population(pop_df, polygon_gdf)
        hex_gdf = up.geom.gen_hexagons(resolution=6, city=polygon_gdf)

        # Aggregate pop metric
        merged_hex = up.geom.merge_shape_hex(hex_gdf, filtered_points_gdf, agg={'bol_general_2020':'sum'})

        # Downsample data
        hex_downsampled = up.geom.resolution_downsampling(merged_hex, 'hex', 5, {'bol_general_2020':'sum'})

        # Test the number of hexagons and indicators generated
        self.assertEqual((14, 3), hex_downsampled.shape)

if __name__ == '__main__':
    unittest.main()
