import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import pydeck as pdk
from h3 import h3
from sklearn.neighbors import BallTree
from shapely.geometry import Point, Polygon
from math import radians
from numba import jit

# - Generar métricas de acceso
# - Generar mapas y visualizaciones con los resultados

class Urbanpy(object):

    def __init__(self):
        self.hdx_url = 'https://data.humdata.org/dataset/{}'
        self.overpass_url = "http://overpass-api.de/api/interpreter"
        self.osm_url = 'https://nominatim.openstreetmap.org/search.php'
        self.osm_parameters = {
            'polygon_geojson': '1',
            'format': 'geojson'
        }

    def download_osm(self, expected_position, query):
        '''
        Download OpenStreetMaps data for a specific city

        Parameters
        ----------

        expected_position: int
                           Expected position of the polygon data within the Nominatim results

        query: str
               Query for city polygon data to be downloaded

        Returns
        -------

        city: GeoDataFrame
              GeoDataFrame with the city's polygon as its geometry column


        Example
        -------

        >> lima = download_osm(2, "Lima, Peru")
        >> lima.head()
        geometry	 | place_id	 | osm_type	| osm_id     | display_name	| place_rank  |  category | type	       | importance	| icon
        MULTIPOLYGON | 235480647 | relation	| 1944670.0  | Lima, Peru	| 12	      |  boundary |	administrative | 0.703484	| https://nominatim.openstreetmap.org/images/map...


        '''
        self.osm_parameters['q'] = query

        response = requests.get(self.osm_url, params=self.osm_parameters)
        all_results = response.json()
        gdf = gpd.GeoDataFrame.from_features(all_results['features'])
        city = gdf.iloc[expected_position:expected_position+1, :]

        return city

    def merge_geom_downloads(self, gdfs):
        '''
        Merge several GeoDataFrames from OSM download_osm

        Parameters
        ----------

        dfs: array_like
             Array of GeoDataFrames to merge

        Returns
        -------

        concat: GeoDataFrame
                Output from concatenation and unary union of geometries, providing
                a single geometry database for the city

        Example
        -------

        >> lima = download_osm(2, "Lima, Peru")
        >> callao = download_osm(1, "Lima, Peru")
        >> lima_ = merge_geom_downloads([lima, callao])
        >> lima_.head()
        geometry
        MULTIPOLYGON (((-76.80277 -12.47562, -76.80261...

        '''

        concat = gpd.GeoDataFrame(geometry=[pd.concat(gdfs).unary_union])
        return concat

    def download_hdx(self, resource):
        '''
        Download the High Resolution Population Density maps from HDX.

        Parameters
        ----------

        resource: str
                  Specific address to the resource for each city. Since every dataset
                  is referenced to a diferent resource id, only the base url can be provided
                  by the library

        Returns
        -------
        population: DataFrame
                    DataFrame with lat, lon, and population columns. Coordinates
                    are in EPSG 4326.


        Example
        -------

        >> pop_lima = download_hdx_population_data("4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip")
        >> pop_lima.head()

        latitude   | longitude  | population_2015 |	population_2020
        -18.339306 | -70.382361 | 11.318147	      | 12.099885
        -18.335694 | -70.393750 | 11.318147	      | 12.099885
        -18.335694 | -70.387361	| 11.318147	      | 12.099885
        -18.335417 | -70.394028	| 11.318147	      | 12.099885
        -18.335139 | -70.394306	| 11.318147	      | 12.099885

        '''

        population = pd.read_csv(self.hdx_url.format(resource))
        return population

    def filter_population(self, pop_df, polygon_gdf):
        '''
        Filter an HDX database download to the polygon bounds

        Parameters
        ----------

        pop_df: DataFrame
                Result from download_hdx

        polygon_gdf: GeoDataFrame
                     Result from download_osm or merge_geom_downloads

        Returns
        -------

        filtered_points_gdf: GeoDataFrame
                         Population DataFrame filtered to polygon bounds

        Example
        -------

        >> lima_ = merge_geom_downloads([lima, callao])
        >> pop = pop_lima = download_hdx_population_data("4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip")
        >> filter_population(pop, lima_)
        	latitude   | longitude  | population_2015 | population_2020 | geometry
            -12.519861 | -76.774583 | 2.633668        | 2.644757        | POINT (-76.77458 -12.51986)
            -12.519861 | -76.745972 | 2.633668        | 2.644757        | POINT (-76.74597 -12.51986)
            -12.519861 | -76.745694 | 2.633668        | 2.644757        | POINT (-76.74569 -12.51986)
            -12.519861 | -76.742639 | 2.633668        | 2.644757        | POINT (-76.74264 -12.51986)
            -12.519861 | -76.741250 | 2.633668        | 2.644757        | POINT (-76.74125 -12.51986)

        '''

        minx, miny, maxx, maxy = polygon_gdf.geometry.total_bounds
        limits_filter = pop_df['longitude'].between(minx, maxx) & pop_df['latitude'].between(miny, maxy)
        filtered_points = pop_df[limits_filter]

        geometry_ = gpd.points_from_xy(filtered_points['longitude'], filtered_points['latitude'])
        filtered_points_gdf = gpd.GeoDataFrame(filtered_points, geometry=geometry_, crs='EPSG:4326')

        return filtered_points_gdf

    def remove_features(self, gdf, bounds):
        '''
        Remove a set of features based on bounds

        Parameters
        ----------

        gdf: GeoDataFrame
             Input GeoDataFrame containing the point features filtered with filter_population

        bounds: array_like
                Array input following [miny, maxy, minx, maxx] for filtering


        Returns
        -------
        gdf: GeoDataFrame
             Input DataFrame but without the desired features

        Example
        -------

        >> lima = filter_population(pop_lima, poly_lima)
        >> removed = remove_features(lima, [-12.2,-12, -77.2,-77.17]) #Remove San Lorenzo Island
        >> print(lima.shape, removed.shape)
        (348434, 4) (348427, 4)
        '''
        miny, maxy, minx, maxx = bounds
        filter = gdf['latitude'].between(miny,maxy) & gdf['longitude'].between(minx,maxx)
        drop_ix = gdf[filter].index

        return gdf.drop(drop_ix)

    def download_overpass_poi(self, bounds, est_type):
        '''
        Download POIs using Overpass API

        Parameters
        ----------

        bounds: array_like
                Input bounds for query. Follows [minx,miny,maxx,maxy] pattern.

        est_type: {'food_supply', 'healthcare_facilities', 'parks_pitches'}
                  Type of establishment to download. Based on this a different type of query
                  is constructed.

        Returns
        -------

        gdf: GeoDataFrame containing all de POIs from the desired query

        gdf_nodes: Only if 'parks_pitches' selected. Returns point geometry POI GeoDataFrame
        gdf_ways: Only if 'parks_pitches' selected. Returns polygon geometry POI GeoDataFrame

        Example
        -------

        '''
        minx, miny, maxx, maxy = bounds

        bbox_string = f'{minx},{miny},{maxx},{maxy}'

        # Definir consulta para instalaciones de oferta de alimentos en Lima
        overpass_url = "http://overpass-api.de/api/interpreter"

        if est_type == 'food_supply':
            overpass_query = f"""
                [timeout:120][out:json][bbox];
                (
                  node["amenity"="market_place"];
                  node["shop"~"supermarket|kiosk|mall|convenience|butcher|greengrocer"];
                );
                out body geom;
                """
        elif est_type == 'healthcare_facilities':
            overpass_query = f"""
                [timeout:120][out:json][bbox];
                (
                  node["amenity"~"clinic|hospital"];
                );
                out body geom;
                """
        else:
            overpass_query = f"""
                [timeout:120][out:json][bbox];
                (
                  way["leisure"~"park|pitch"];
                  node["leisure"="pitch"];
                );
                out body geom;
                """

        # Request data
        response = requests.get(overpass_url, params={'data': overpass_query,
                                                      'bbox': bbox_string})
        data = response.json()

        if est_type != 'parks_pitches':
            df = pd.DataFrame.from_dict(data['elements'])
            df_geom = gpd.points_from_xy(df['lon'], df['lat'])
            gdf = gpd.GeoDataFrame(df, geometry=df_geom)

            return gdf

        else:
            df = pd.DataFrame.from_dict(data['elements'])

            #Process nodes
            nodes = df[df['type'] == 'node'].drop(['bounds', 'nodes', 'geometry'], axis=1)
            node_geom = gpd.points_from_xy(nodes['lon'], nodes['lat'])
            node_gdf = gpd.GeoDataFrame(nodes, geometry=node_geom)

            #Process ways
            ways = df[df['type'] == 'way'].drop(['lat', 'lon'], axis=1)
            ways['shell'] = ways['geometry'].apply(shell_from_geometry)
            way_geom = ways['shell'].apply(Polygon)
            way_gdf = gpd.GeoDataFrame(ways, geometry=way_geom)

            return node_gdf, way_gdf

    def shell_from_geometry(self, geometry):
        '''
        Util function for park and pitch processing.
        '''

        shell = []
        for record in geometry:
            shell.append([record['lon'], record['lat']])
        return shell

    def gen_hexagons(self, resolution, city):
        '''
        Converts an input multipolygon layer to H3 hexagons given a resolution.

        Parameters
        ----------

        resolution: int, 0:15
                    Hexagon resolution, higher values create smaller hexagons.

        city: GeoDataFrame
              Input city polygons to transform into hexagons.

        Returns
        -------

        city_hexagons: GeoDataFrame
                       Hexagon geometry GeoDataFrame (hex_id, geom).

        city_centroids: GeoDataFrame
                        Hexagon centroids for the specified city (hex_id, geom).

        Example
        -------

        >> lima = filter_population(pop_lima, poly_lima)
        >> lima_hex = gen_hexagons(8, lima)

        	0	            | geometry
	        888e620e41fffff | POLYGON ((-76.80007 -12.46917, -76.80439 -12.4...
	        888e62c809fffff | POLYGON ((-77.22539 -12.08663, -77.22971 -12.0...
	        888e62c851fffff | POLYGON ((-77.20708 -12.08484, -77.21140 -12.0...
	        888e62c841fffff | POLYGON ((-77.22689 -12.07104, -77.23122 -12.0...
	        888e62c847fffff | POLYGON ((-77.23072 -12.07929, -77.23504 -12.0...

            0	            | geometry
            888e620e41fffff | POINT (-76.79956 -12.47436)
            888e62c809fffff | POINT (-77.22488 -12.09183)
            888e62c851fffff | POINT (-77.20658 -12.09004)
            888e62c841fffff | POINT (-77.22639 -12.07624)
            888e62c847fffff | POINT (-77.23021 -12.08448)

        '''

        # Polyfill the city boundaries
        h3_centroids = list()
        h3_polygons = list()
        h3_indexes = list()

        # Get every polygon in Multipolygon shape
        city_poly = city.explode().reset_index(drop=True)

        for ix, geo in city_poly.iterrows():
            hexagons = h3.polyfill(geo['geometry'].__geo_interface__, res=resolution, \
                                    geo_json_conformant=True)
            for hexagon in hexagons:
                centroid_lat, centroid_lon = h3.h3_to_geo(hexagon) # format as x,y (lon, lat)
                h3_centroids.append(Point(centroid_lon, centroid_lat))

                h3_geo_boundary = h3.h3_to_geo_boundary(hexagon)
                [bound.reverse() for bound in h3_geo_boundary] # format as x,y (lon, lat)
                h3_polygons.append(Polygon(h3_geo_boundary))

                h3_indexes.append(hexagon)

        # Create hexagon dataframe
        city_hexagons = gpd.GeoDataFrame(h3_indexes, geometry=h3_polygons).drop_duplicates()
        city_hexagons.crs = 'EPSG:4326'
        city_centroids = gpd.GeoDataFrame(h3_indexes, geometry=h3_centroids).drop_duplicates()
        city_centroids.crs = 'EPSG:4326'

        return city_hexagons, city_centroids

    def merge_shape_hex(self, hex, shape, how, op, agg):
        '''
        Merges a H3 hexagon GeoDataFrame with a Point GeoDataFrame and aggregates the
        point gdf data.

        Parameters
        ----------
        hex: GeoDataFrame
             Input GeoDataFrame containing hexagon geometries

        shape: GeoDataFrame
                Input GeoDataFrame containing points and features to be aggregated

        how: str. One of {'inner', 'left', 'right'}. Determines how to merge data.
             'left' uses keys from left and only retains geometry from left
             'right' uses keys from right and only retains geometry from right
             'inner': use intersection of keys from both dfs; retain only left geometry column

        op: str. One of {'intersects', 'contains', 'within'}. Determines how
                 geometries are queried for merging.

        agg: dict. A dictionary with column names as keys and values as aggregation
             operations. The aggregation must be one of {'sum', 'min', 'max'}.

        Returns
        -------

        hex: GeoDataFrame
                   Result of a spatial join within hex and points. All features are aggregated
                   based on the input parameters

        Example
        -------

        >> lima = download_osm(2, 'Lima, Peru')
        >> pop_lima = download_hdx(...)
        >> pop_df = filter_population(pop_lima, lima)
        >> hex = gen_hexagons(8, lima)
        >> merge_point_hex(hex, pop_df, 'inner', 'within', {'population_2020':'sum'})

        0               | geometry                                          | population_2020
        888e628d8bfffff | POLYGON ((-76.66002 -12.20371, -76.66433 -12.2... | NaN
        888e62c5ddfffff | POLYGON ((-76.94564 -12.16138, -76.94996 -12.1... | 14528.039097
        888e62132bfffff | POLYGON ((-76.84736 -12.17523, -76.85167 -12.1... | 608.312696
        888e628debfffff | POLYGON ((-76.67982 -12.18998, -76.68413 -12.1... | NaN
        888e6299b3fffff | POLYGON ((-76.78876 -11.97286, -76.79307 -11.9... | 3225.658803
        '''
        joined = gpd.sjoin(shape, hex, how=how, op=op)

        #Uses index right based on the order of points and hex. Right takes hex index
        hex_merge = joined.groupby('index_right').agg(agg)

        #Avoid SpecificationError by copying the DataFrame
        ret_hex = hex.copy()

        for key in agg.keys():
            ret_hex.loc[hex_merge.index, key] = hex_merge[key].values

        return ret_hex

    def swap_xy(self, geom):
        '''
        Util function in case an x,y coordinate needs to be switched

        Parameters
        ----------

        geom: GeoSeries
              Input series containing the geometries needing a coordinate swap

        Returns
        -------

        shell: list
               List containing the exterior borders of the geometry
        holes: list
               Array of all holes within a geometry. Only for Polygon and Multipolygon
        coords: list
                List of geomerty type with the swapped x,y coordinates
        '''
        if geom.is_empty:
            return geom

        if geom.has_z:
            def swap_xy_coords(coords):
                for x, y, z in coords:
                    yield (y, x, z)
        else:
            def swap_xy_coords(coords):
                for x, y in coords:
                    yield (y, x)

        # Process coordinates from each supported geometry type
        if geom.type in ('Point', 'LineString', 'LinearRing'):
            return type(geom)(list(swap_xy_coords(geom.coords)))
        elif geom.type == 'Polygon':
            ring = geom.exterior
            shell = type(ring)(list(swap_xy_coords(ring.coords)))
            holes = list(geom.interiors)
            for pos, ring in enumerate(holes):
                holes[pos] = type(ring)(list(swap_xy_coords(ring.coords)))
            return type(geom)(shell, holes)
        elif geom.type.startswith('Multi') or geom.type == 'GeometryCollection':
            # Recursive call
            return type(geom)([swap_xy(part) for part in geom.geoms])
        else:
            raise ValueError('Type %r not recognized' % geom.type)

    def nn_search(self, tree_features, query_features, metric='haversine', convert_radians=False):
        '''
        Build a BallTree for nearest neighbor search based on haversine distance.

        Parameters
        ----------

        tree_features: array_like
                       Input features to create the search tree. Features are in
                       lat, lon format, in radians

        query_features: array_like
                        Points to which calculate the nearest neighbor within the tree.
                        latlon coordinates expected in radians for distance calculation

        metric: str
                Distance metric for neighorhood search. Default haversine for latlon coordinates.

        convert_radians: bool
                         Flag in case features are not in radians and need to be converted

        Returns
        -------

        distances: array_like
                   Array with the corresponding distance in km (haversine distance * earth radius)

        '''

        if convert_radians:
            pass

        tree = BallTree(tree_features, metric=metric)
        return tree.query(query_features)[0] * 6371000/1000

    @jit
    def tuples_to_lists(self, json):
        '''
        Util function to convert the geo interface of a GeoDataFrame to PyDeck GeoJSON format.

        Parameters
        ----------

        json: GeoJSON from a GeoDataFrame.__geo_interface__


        Returns
        -------

        json: dict
              GeoJSON with the corrected features

        '''

        for i in range(len(json['features'])):
            t = [list(x) for x in json['features'][i]['geometry']['coordinates']]
            poly = [[list(x) for x in t[0]]]

            json['features'][i]['geometry']['coordinates'] = poly

        return json

    def pydeck_df(self, gdf, features, cmap, bins, color_feature):
        '''
        Prepare a DataFrame for Polygon plotting in PyDeck

        Parameters
        ----------

        gdf: GeoDataFrame with the geometries to plot
        features: list
                  List of features to add to the polygon df

        cmap: str
              Matplotlib colormap to use for plotting
        bins: list
              Bins to aggregate data into
        color_feature: str
                       Column name for data to transform into bins and color features

        Returns
        -------

        polygon_df: DataFrame
                    df with the coordinates in a list as a column and the selected features
        '''

        cmap = plt.get_cmap(name='magma')
        json = gdf.__geo_interface__

        json_ = self.tuples_to_lists(json)

        del json_['bbox']

        df = pd.DataFrame.from_dict(json_)

        polygon_df = pd.DataFrame()
        polygon_df['coordinates'] = df['features'].apply(lambda row: row['geometry']['coordinates'])

        for feature in features:
            polygon_df[feature] = df['features'].apply(lambda row: row['properties'][feature])

        print()
        polygon_df['bins'] = pd.cut(
            polygon_df[color_feature],
            bins = bins
        )

        bins_labels = polygon_df['bins'].unique().categories.values
        bins_replace = {label: i  for i, label in enumerate(bins_labels)}
        polygon_df['count'] = polygon_df['bins'].replace(bins_replace)

        cmap_ixs = [int(round(255 / (i+1))) for i in polygon_df['count'].fillna(0).values]
        rgb_values = [[color * 255 for color in cmap.colors[cmap_ix]] for cmap_ix in cmap_ixs]
        rgb_count_df = pd.DataFrame(rgb_values, columns=['r','g','b'])

        polygon_df = pd.concat((polygon_df, rgb_count_df), axis=1)

        polygon_df['r'] = polygon_df['r'].round(0)
        polygon_df['g'] = polygon_df['g'].round(0)
        polygon_df['b'] = polygon_df['b'].round(0)

        return polygon_df

    def gen_pydeck_layer(self, layer_type, data, **kwargs):
        if layer_type == 'H3HexagonLayer':
            return pdk.Layer("H3HexagonLayer", data, **kwargs)
        else:
            return pdk.Layer('PolygonLayer', data, **kwargs)
