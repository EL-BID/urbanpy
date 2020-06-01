import requests
import geopandas as gpd
import pandas as pd
import numpy as np
import osmnx as ox
from shapely.geometry import Point, Polygon
from urbanpy.utils import shell_from_geometry

__all__ = [
    'nominatim_osm',
    'hdx_dataset',
    'overpass_pois',
    'osmnx_graph'
]

def nominatim_osm(query, expected_position=0):
    '''
    Download OpenStreetMaps data for a specific city

    Parameters
    ----------

    query: str
        Query for city polygon data to be downloaded

    expected_position: int 0:n
        Expected position of the polygon data within the Nominatim results. Default 0 (first result).

    Returns
    -------

    city: GeoDataFrame
        GeoDataFrame with the city's polygon as its geometry column


    Examples
    --------

    >>> lima = download_osm("Lima, Peru", 2)
    >>> lima.head()
    geometry	 | place_id	 | osm_type	| osm_id     | display_name	| place_rank  |  category | type	       | importance	| icon
    MULTIPOLYGON | 235480647 | relation	| 1944670.0  | Lima, Peru	| 12	      |  boundary |	administrative | 0.703484	| https://nominatim.openstreetmap.org/images/map...

    '''
    osm_url = 'https://nominatim.openstreetmap.org/search.php'
    osm_parameters = {
        'polygon_geojson': '1',
        'format': 'geojson'
    }
    osm_parameters['q'] = query

    response = requests.get(osm_url, params=osm_parameters)
    all_results = response.json()
    gdf = gpd.GeoDataFrame.from_features(all_results['features'])
    city = gdf.iloc[expected_position:expected_position+1, :]

    return city

def hdx_dataset(resource):
    '''
    Download the High Resolution Population Density maps from HDX.

    Parameters
    ----------

    resource : str
                  Specific address to the resource for each city. Since every dataset
                  is referenced to a diferent resource id, only the base url can be provided
                  by the library

    Returns
    -------

    population : DataFrame
                    DataFrame with lat, lon, and population columns. Coordinates
                    are in EPSG 4326.


    Examples
    --------

    >>> pop_lima = download_hdx_population_data("4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip")
    >>> pop_lima.head()
    latitude   | longitude  | population_2015 |	population_2020
    -18.339306 | -70.382361 | 11.318147	      | 12.099885
    -18.335694 | -70.393750 | 11.318147	      | 12.099885
    -18.335694 | -70.387361	| 11.318147	      | 12.099885
    -18.335417 | -70.394028	| 11.318147	      | 12.099885
    -18.335139 | -70.394306	| 11.318147	      | 12.099885

    '''
    hdx_url = f'https://data.humdata.org/dataset/{resource}'
    population = pd.read_csv(hdx_url)
    return population

def overpass_pois(bounds, facilities=None, custom_query=None):
    '''
    Download POIs using Overpass API

    Parameters
    ----------

    bounds: array_like
                Input bounds for query. Follows [minx,miny,maxx,maxy] pattern.

    facilities: {'food', 'health', 'education', 'financial'}
                Type of facilities to download according to HOTOSM types. Based on this a different type of query is constructed.

    custom_query: str (Optional)
                String with custom Overpass QL query (See https://wiki.openstreetmap.org/wiki/Overpass_API/Language_Guide). If this parameter is diferent than None, bounds and facilities values are ignored. Defaults to None.


    Returns
    -------

    gdf: GeoDataFrame containing all the POIs from the selected type of facility

    response: Only if 'custom_query' is given. Returns an HTTP response from the Overpass Server

    Examples
    --------

    '''
    minx, miny, maxx, maxy = bounds

    bbox_string = f'{minx},{miny},{maxx},{maxy}'

        # Definir consulta para instalaciones de oferta de alimentos en Lima
    overpass_url = "http://overpass-api.de/api/interpreter"

    facilities_opt = {
        'food': 'node["amenity"="marketplace"];\nnode["shop"~"supermarket|kiosk|mall|convenience|butcher|greengrocer"];',
        'health': 'node["amenity"~"doctors|dentist|clinic|hospital|pharmacy"];',
        'education': 'node["amenity"~"kindergarten|school|college|university"];',
        'finance': 'node["amenity"~"mobile_money_agent|bureau_de_change|bank|microfinance|atm|sacco|money_transfer|post_office"];',
    }

    if custom_query == None:
        overpass_query = f"""
            [timeout:120][out:json][bbox];
            (
                 {facilities_opt[facilities]}
            );
            out body geom;
            """
        # Request data
        response = requests.get(overpass_url, params={'data': overpass_query,
                                                      'bbox': bbox_string})
        data = response.json()
        df = pd.DataFrame.from_dict(data['elements'])
        df_geom = gpd.points_from_xy(df['lon'], df['lat'])
        gdf = gpd.GeoDataFrame(df, geometry=df_geom)

        gdf['poi_type'] = gdf['tags'].apply(lambda tag: tag['amenity'] if 'amenity' in tag.keys() else np.NaN)

        if facilities == 'food':
            # Food facilities also have its POI type wthin the shop tag (See query)
            also_poi_type = gdf['tags'].apply(lambda tag: tag['shop'] if 'shop' in tag.keys() else np.NaN)
            gdf['poi_type'] = gdf['poi_type'].fillna(also_poi_type)

        return gdf

    else:
        response = requests.get(overpass_url, params={'data': custom_query, 'bbox': bbox_string})
        return response

def osmnx_graph(download_type, network_type='drive', query_str=None,
                geom=None, distance=None, **kwargs):
    '''
    Download a graph from OSM using osmnx.

    Parameters
    ----------

    download_type: str. One of {'polygon', 'place', 'point'}
                   Input download type. If polygon, the polygon parameter must be
                   provided as a Shapely Polygon.
    network_type: str. One of {'drive', 'drive_service', 'walk', 'bike', 'all', 'all_private'}
                  Network type to download. Defaults to drive.

    query_str: str
               Optional. Only requiered for place type downloads. Query string to download a network.

    polygon: Shapely Polygon or Point
             Optional. Polygon requiered for polygon type downloads, Point for place downloads.
             Polygons are used as bounds for network download, points as the center with a distance buffer.

    distance: int
              Distance in meters to use as buffer from a point to download the network.

    Returns
    -------

    G: networkx MultiDiGraph
       Requested graph with simplyfied geometries

    Examples
    --------

    >>> poly = urbanpy.download.nominatim_osm('San Isidro, Peru')
    >>> G = urbanpy.download.osmnx_graph('polygon', geom=lima.loc[0,'geometry'])
    <networkx.classes.multidigraph.MultiDiGraph at 0x1a2ba08150>

    '''

    if (download_type == 'polygon') and (geom is not None) and (type(geom) == Polygon):
        G = ox.graph_from_polygon(geom)
        return G

    elif (download_type == 'point') and (geom is not None) and (distance is not None):
        G = ox.graph_from_point(geom, distance=distance)
        return G

    elif download_type == 'place' and query_str is not None:
        G = ox.graph_from_place(query_str)
        return G

    elif download_type == 'polygon' and geom is None:
        print('Please provide a polygon to download a network from.')

    elif download_type == 'place' and query_str is None:
        print('Please provide a query string to download a network from.')

    else:
        if distance is None and download_type == 'point':
            print('Please provide a distance buffer for the point download')

        if geom is None and distance is not None:
            print('Please provide a Point geometry.')
