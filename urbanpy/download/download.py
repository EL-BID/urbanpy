import requests 
import geopandas as gpd
import pandas as pd
import numpy as np
import osmnx as ox
from shapely.geometry import Polygon, MultiPolygon
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from typing import Optional, Union, Tuple, Sequence
from pandas import DataFrame
from geopandas import GeoDataFrame, GeoSeries
from urbanpy.utils import to_overpass_query, overpass_to_gdf

__all__ = [
    'nominatim_osm',
    'overpass_pois',
    'overpass',
    'osmnx_graph',
    'search_hdx_dataset',
    'download_hdx_dataset'
]

hdx_config = Configuration.create(hdx_site='prod', user_agent='urbanpy', hdx_read_only=True)

def nominatim_osm(query:str, expected_position=0) -> GeoDataFrame:
    """
    Download OpenStreetMaps data for a specific city.

    Parameters
    ----------
    query: str
        Query for city polygon data to be downloaded.
    expected_position: int 0:n
        Expected position of the polygon data within the Nominatim results.
        Default 0 (first result).

    Returns
    -------
    city: GeoDataFrame
        GeoDataFrame with the city's polygon as its geometry column.

    Examples
    --------
    >>> lima = nominatim_osm('Lima, Peru', 2)
    >>> lima.head()
    geometry	 | place_id	 | osm_type	| osm_id     | display_name	| place_rank  |  category | type	       | importance	| icon
    MULTIPOLYGON | 235480647 | relation	| 1944670.0  | Lima, Peru	| 12	      |  boundary |	administrative | 0.703484	| https://nominatim.openstreetmap.org/images/map...

    """
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


def overpass_pois(bounds, facilities=None, custom_query=None):
    '''
    Download POIs using Overpass API.

    Parameters
    ----------
    bounds: array_like
        Input bounds for query. Follows [minx,miny,maxx,maxy] pattern.
    facilities: str. One of {'food', 'health', 'education', 'finance'}
        Type of facilities to download according to HOTOSM types. Based on this
        a different type of query is constructed.
    custom_query: str (Optional). Default None.
        String with custom Overpass QL query (See https://wiki.openstreetmap.org/wiki/Overpass_API/Language_Guide).
        If this parameter is diferent than None, bounds and facilities values
        are ignored.

    Returns
    -------
    gdf: GeoDataFrame
        POIs from the selected type of facility. If 'custom_query' is given
        response is returned instead of gdf.
    response: request.Response
        Returned only if 'custom_query' is given. Contains the server's response
        to the HTTP request from the Overpass API Server.

    Examples
    --------
    >>> lima = nominatim_osm('Lima, Peru', 2)
    >>> urbanpy.download.overpass_pois(lima.total_bounds, 'health')
    type |  id	      | lat	      | lon	       | tags	                                           | geometry                   | poi_type
    node |	367826732 |	-0.944005 |	-80.733941 | {'amenity': 'pharmacy', 'name': 'Fybeca'}         | POINT (-80.73394 -0.94401)	| pharmacy
    node |	367830051 |	-0.954086 |	-80.742420 | {'amenity': 'hospital', 'emergency': 'yes', 'n... | POINT (-80.74242 -0.95409)	| hospital
    node |	367830065 |	-0.954012 |	-80.741554 | {'amenity': 'hospital', 'name': 'Clínica del S... | POINT (-80.74155 -0.95401)	| hospital
    node |	367830072 |	-0.953488 |	-80.740739 | {'amenity': 'hospital', 'name': 'Clínica Cente... | POINT (-80.74074 -0.95349)	| hospital
    node |	3206491590|	-1.040708 |	-80.665107 | {'amenity': 'hospital', 'name': 'Clínica Monte... | POINT (-80.66511 -1.04071)	| hospital

    '''
    minx, miny, maxx, maxy = bounds

    bbox_string = f'{minx},{miny},{maxx},{maxy}'

    overpass_url = "https://overpass-api.de/api/interpreter"

    facilities_opt = {
        'food': 'node["amenity"="marketplace"];\nnode["shop"~"supermarket|kiosk|mall|convenience|butcher|greengrocer"];',
        'health': 'node["amenity"~"doctors|dentist|clinic|hospital|pharmacy"];',
        'education': 'node["amenity"~"kindergarten|school|college|university"];',
        'finance': 'node["amenity"~"mobile_money_agent|bureau_de_change|bank|microfinance|atm|sacco|money_transfer|post_office"];',
    }

    if custom_query is None:
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


def overpass(type_of_data: str, query: dict, 
             mask: Union[GeoDataFrame, GeoSeries, Polygon, MultiPolygon]) -> Tuple[GeoDataFrame, Optional[DataFrame]]:
    '''
    Download geographic data using Overpass API.

    Parameters
    ----------
    type_of_data: str. One of {'node', 'way', 'relation', 'rel'}
        OSM Data structure to be queried from Overpass API.
    query: dict
        Dict contaning OSM tag filters. Dict keys can take OSM tags 
        and Dict values can be list of strings, str or None. 
        Check keys [OSM Map Features](https://wiki.openstreetmap.org/wiki/Map_features).
        Example: {
            'key0': ['v0a', 'v0b','v0c'], 
            'key1': 'v1', 
            'key2': None
        }
    mask: 
    
    Returns
    -------
    gdf: GeoDataFrame
        POIs from the selected type of facility.
    df: DataFrame
        Relations metadata such as ID and tags. Returns None if 'type_of_data' other than 'relation'. 
    '''
    minx, miny, maxx, maxy = mask.total_bounds
    bbox_string = f'{minx},{miny},{maxx},{maxy}'
    
    # Request data
    overpass_url = "https://overpass-api.de/api/interpreter"
    params = {
        'data': to_overpass_query(type_of_data, query), # Parse query dict to build Overpass QL query
        'bbox': bbox_string
    }
    response = requests.get(overpass_url, params=params)
    try:
        data = response.json()
    except Exception as e:
        print(e)
        print(response.status_code)
        print(response.reason)
        return response
    
    ov_keys = list(set(query.keys())) # get unique keys used in query (e.g. "amenity", "shop", etc)

    return overpass_to_gdf(type_of_data, data, mask, ov_keys)


def osmnx_graph(download_type:str, network_type='drive', query_str=None,
                geom=None, distance=None, **kwargs):
    '''
    Download a graph from OSM using osmnx.

    Parameters
    ----------
    download_type: str. One of {'polygon', 'place', 'point'}
        Input download type. If polygon, the polygon parameter must be provided
        as a Shapely Polygon.
    network_type: str. One of {'drive', 'drive_service', 'walk', 'bike', 'all', 'all_private'}
        Network type to download. Defaults to drive.
    query_str: str (Optional).
        Only requiered for place type downloads. Query string to download a network.
    polygon: Shapely Polygon or Point (Optional).
        Polygon requiered for polygon type downloads, Point for place downloads.
        Polygons are used as bounds for network download, points as the center.
        with a distance buffer.
    distance: int
        Distance in meters to use as buffer from a point to download the network.

    Returns
    -------
    G: networkx.MultiDiGraph
        Requested graph with simplyfied geometries.

    Examples
    --------
    >>> poly = urbanpy.download.nominatim_osm('San Isidro, Peru')
    >>> G = urbanpy.download.osmnx_graph('polygon', geom=lima.loc[0,'geometry'])
    >>> G
    <networkx.classes.multidigraph.MultiDiGraph at 0x1a2ba08150>
    
    '''
    if (download_type == 'polygon') and (geom is not None) and isinstance(geom, Polygon):
        G = ox.graph_from_polygon(geom, network_type=network_type)
        return G
    elif (download_type == 'point') and (geom is not None) and (distance is not None):
        G = ox.graph_from_point(geom, dist=distance, network_type=network_type)
        return G

    elif download_type == 'place' and query_str is not None:
        G = ox.graph_from_place(query_str, network_type=network_type)
        return G

    elif download_type == 'polygon' and geom is None:
        print('Please provide a polygon to download a network from.')

    elif download_type == 'place' and query_str is None:
        print('Please provide a query string to download a network from.')

    else:
        if distance is None and download_type == 'point':
            print('Please provide a distance buffer for the point download')

        if geom is None and distance is not None: print('Please provide a Point geometry.')


def search_hdx_dataset(country:str, repository="high-resolution-population-density-maps-demographic-estimates"):
    '''
    Dataset search within HDX repositories. Defaults to population density maps.

    Parameters
    ----------

    country: str
             Country to search datasets

    resource: str
              Resource type within the HDX database

    Returns
    -------

    datasets: list
              List of available datasets within HDX

    Examples
    --------

    '''
    #Get dataset list
    datasets = Dataset.search_in_hdx(f"title:{country.lower()}-{repository}")

    return Dataset.get_all_resources(datasets)

def download_hdx_dataset(country: str, dataset_id=None, resource="high-resolution-population-density-maps-demographic-estimates") -> Union[DataFrame, None]:
    '''
    HDX dataset download.
    
    Parameters
    ----------

    country: str
             The country to download the dataset from.

    dataset_id: int
                Position of the dataset in the search list (see search_hdx_dataset)


    Returns
    -------

    data: pd.DataFrame
          The corresponding datset in DataFrame format

    Examples
    --------
    >>> urbanpy.download.download_hdx_dataset('peru', 0)
    latitude   | longitude  | population_2015 |	population_2020
    -18.339306 | -70.382361 | 11.318147	      | 12.099885
    -18.335694 | -70.393750 | 11.318147	      | 12.099885
    -18.335694 | -70.387361	| 11.318147	      | 12.099885
    -18.335417 | -70.394028	| 11.318147	      | 12.099885
    -18.335139 | -70.394306	| 11.318147	      | 12.099885

    '''

    if dataset_id is None:
        print('Please run a seach for the hdx dataset you need and pass the correct dataset_id')

    else:
        datasets = search_hdx_dataset(country)
        data = pd.read_csv(datasets[dataset_id]['url'])

        return data
