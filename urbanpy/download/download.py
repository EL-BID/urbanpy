import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from urbanpy.utils import shell_from_geometry

__all__ = [
    'download_osm',
    'download_hdx',
    'download_overpass_poi',
]

def download_osm(expected_position, query):
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

def download_hdx(resource):
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
    hdx_url = f'https://data.humdata.org/dataset/{resource}'
    population = pd.read_csv(hdx_url)
    return population

def download_overpass_poi(bounds, est_type):
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
