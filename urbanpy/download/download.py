import requests
import geopandas as gpd
import pandas as pd
import numpy as np
import osmnx as ox
from shapely.geometry import Polygon

__all__ = [
    'nominatim_osm',
    'hdx_dataset',
    'hdx_fb_population',
    'overpass_pois',
    'osmnx_graph'
]

def nominatim_osm(query, expected_position=0):
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

def hdx_dataset(resource):
    """
    Download a dataset from HDX. The allowed formats are CSV (.csv) and zipped
    CSV (.csv.zip).

    Parameters
    ----------
    resource: str
        Specific address to the HDX dataset resource. Since every dataset is
        referenced to a diferent resource id, only the base url can be provided
        by this library.

    Returns
    -------
    dataset: DataFrame
        Contains the requested HDX dataset resource.

    Examples
    --------
    >>> hdx_data = hdx_dataset('4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip')
    >>> hdx_data.head()
    latitude   | longitude  | population_2015 |	population_2020
    -18.339306 | -70.382361 | 11.318147	      | 12.099885
    -18.335694 | -70.393750 | 11.318147	      | 12.099885
    -18.335694 | -70.387361	| 11.318147	      | 12.099885
    -18.335417 | -70.394028	| 11.318147	      | 12.099885
    -18.335139 | -70.394306	| 11.318147	      | 12.099885

    """
    hdx_url = f'https://data.humdata.org/dataset/{resource}'
    dataset = pd.read_csv(hdx_url)
    return dataset

def hdx_fb_population(country, map_type):
    '''
    Download population density maps from Facebook HDX.

    Parameters
    ----------
    country: str. One of {'argentina', 'bolivia', 'brazil', 'chile', 'colombia', 'ecuador', 'paraguay', 'peru', 'uruguay'}
        Input country to download data from.
    map_type: str. One of {'full', 'children', 'youth', 'elderly'}
        Input population map to download.

    Returns
    -------
    population: DataFrame
        DataFrame with lat, lon, and population columns. Coordinates are in
        EPSG 4326.

    Examples
    --------
    >>> urbanpy.download.hdx_fb_population('peru', 'full')
    latitude   | longitude  | population_2015 |	population_2020
    -18.339306 | -70.382361 | 11.318147	      | 12.099885
    -18.335694 | -70.393750 | 11.318147	      | 12.099885
    -18.335694 | -70.387361	| 11.318147	      | 12.099885
    -18.335417 | -70.394028	| 11.318147	      | 12.099885
    -18.335139 | -70.394306	| 11.318147	      | 12.099885

    '''
    dataset_dict = {
        'argentina': {
            'full': 'https://data.humdata.org/dataset/6cf49080-1226-4eda-8700-a0093cbdfe4d/resource/5737d87f-e17f-4c82-b1bd-d589ed631318/download/population_arg_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/6cf49080-1226-4eda-8700-a0093cbdfe4d/resource/1795ad97-e06a-4ca4-83aa-32ab612f55ba/download/arg_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/6cf49080-1226-4eda-8700-a0093cbdfe4d/resource/dff11b02-a356-4a4f-948c-5a7722ad7365/download/arg_youth_15_24_2019-06-01_csv.zip',
            'elderly':'https://data.humdata.org/dataset/6cf49080-1226-4eda-8700-a0093cbdfe4d/resource/8f1d9473-90f0-441f-b464-c76960e9e130/download/arg_elderly_60_plus_2019-06-01_csv.zip'
        },
        'bolivia': {
            'full': 'https://data.humdata.org/dataset/64f916a6-2f35-4399-8971-25e18fdb09bd/resource/d5fc8980-f3f2-4523-ac4d-f188201518d5/download/population_bol_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/64f916a6-2f35-4399-8971-25e18fdb09bd/resource/4fe96e38-3895-4f5e-b3f9-df6317a9752f/download/bol_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/64f916a6-2f35-4399-8971-25e18fdb09bd/resource/7c5fba5b-cdb6-49f2-8ae5-5337734444d2/download/bol_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/64f916a6-2f35-4399-8971-25e18fdb09bd/resource/8acccec8-a1a4-42d7-b301-fb734324960e/download/bol_elderly_60_plus_2019-06-01_csv.zip'
        },
        'brazil': {
            'full': [
                'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/957218ee-c740-44c0-88e5-7faeef813a0c/download/population_bra_northeast_2018-10-01.csv.zip',
                'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/1e1f271b-1055-4365-b391-f6fdf3093fe2/download/population_bra_northwest_2018-10-01.csv.zip',
                'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/eb17516f-3c84-4626-95e4-df1f342f3d82/download/population_bra_southeast_2018-10-01.csv.zip',
                'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/5cb55d1a-9f11-4004-82f3-0c27e878495a/download/population_bra_southwest_2018-10-01.csv.zip'
            ],
            'children': 'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/54964df0-8d6a-4f65-ac10-bcf11499a9fe/download/bra_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/0e4af4ff-e4e5-4686-a17c-c8b326d98d76/download/bra_youth_15_24_2019-06-01_csv.zip',
            'elderly':'https://data.humdata.org/dataset/c17003d1-47f4-4ec5-8229-2f77aeb114be/resource/6d6f1ea3-c8d3-4dc0-b0ea-af9c92b14b48/download/bra_elderly_60_plus_2019-06-01_csv.zip'
        },
        'chile': {
            'full': 'https://data.humdata.org/dataset/dd47e052-02cc-4a3f-972a-421d600b3d85/resource/bb560451-9c50-4d57-8ff3-872fa260c102/download/population_chl_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/dd47e052-02cc-4a3f-972a-421d600b3d85/resource/33b43b9a-9f47-4f25-8bdc-568e8850fde8/download/chl_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/dd47e052-02cc-4a3f-972a-421d600b3d85/resource/2c4083b5-e682-4ae5-8df8-b2934c4eef9c/download/chl_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/dd47e052-02cc-4a3f-972a-421d600b3d85/resource/056a5832-1490-41e4-8ee1-7c90ff1389ff/download/chl_elderly_60_plus_2019-06-01_csv.zip'
        },
        'colombia': {
            'full': 'https://data.humdata.org/dataset/2f865527-b7bf-466c-b620-c12b8d07a053/resource/357c91e0-c5fb-4ae2-ad9d-00805e5a075d/download/population_col_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/2f865527-b7bf-466c-b620-c12b8d07a053/resource/e8422e0d-0c1a-4aff-b790-76fffa8e09a6/download/col_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/2f865527-b7bf-466c-b620-c12b8d07a053/resource/f458dcfc-3441-4bec-b45f-d91081801501/download/col_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/2f865527-b7bf-466c-b620-c12b8d07a053/resource/3e871e9d-d9fa-4d52-af47-43cae54c7a6d/download/col_elderly_60_plus_2019-06-01_csv.zip'
        },
        'ecuador': {
            'full': 'https://data.humdata.org/dataset/58c3ac3f-febd-4222-8969-59c0fe0e7a0d/resource/c05a3c81-a78c-4e6c-ac05-de1316d4ba12/download/population_ecu_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/58c3ac3f-febd-4222-8969-59c0fe0e7a0d/resource/80e46cf3-1906-41a9-a779-8f501cab48a5/download/ecu_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/58c3ac3f-febd-4222-8969-59c0fe0e7a0d/resource/57362a78-e2fa-4f71-8876-1a6d67e27fe5/download/ecu_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/58c3ac3f-febd-4222-8969-59c0fe0e7a0d/resource/904d8988-d18d-41a5-a7f7-22668204cefe/download/ecu_elderly_60_plus_2019-06-01_csv.zip'
        },
        'paraguay': {
            'full': 'https://data.humdata.org/dataset/318c589b-9091-4aa4-b384-351208be71e9/resource/6c21c73c-05ba-4818-9574-cb56fa04b210/download/population_pry_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/318c589b-9091-4aa4-b384-351208be71e9/resource/7ff05dd3-61f0-40a5-90ee-7262b4190ac2/download/pry_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/318c589b-9091-4aa4-b384-351208be71e9/resource/226e0efe-73b1-4d4b-96f1-06cb3ffd165a/download/pry_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/318c589b-9091-4aa4-b384-351208be71e9/resource/8cb53c32-b8f9-4f6f-9d22-50478040fafc/download/pry_elderly_60_plus_2019-06-01_csv.zip'
        },
        'peru': {
            'full': 'https://data.humdata.org/dataset/4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/ed2712e7-4668-45a2-b76f-eb819df9e0c1/download/per_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/86daf899-8e63-4262-be92-15934e59cabf/download/per_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/8cc100cf-68a4-4fda-a8e6-a63b99ad5b00/download/per_elderly_60_plus_2019-06-01_csv.zip'
        },
        'uruguay': {
            'full': 'https://data.humdata.org/dataset/61e8075b-5c42-495a-98eb-01b3e819dcb5/resource/69900b71-8d0b-49d5-a235-f9b5cc5b820a/download/population_ury_2018-10-01.csv.zip',
            'children': 'https://data.humdata.org/dataset/61e8075b-5c42-495a-98eb-01b3e819dcb5/resource/90d47ee3-5e5f-4aa5-a999-69b1f3e82061/download/ury_children_under_five_2019-06-01_csv.zip',
            'youth': 'https://data.humdata.org/dataset/61e8075b-5c42-495a-98eb-01b3e819dcb5/resource/8ed64dfe-449c-4026-9b48-0416f67c3f38/download/ury_youth_15_24_2019-06-01_csv.zip',
            'elderly': 'https://data.humdata.org/dataset/61e8075b-5c42-495a-98eb-01b3e819dcb5/resource/b9cfa194-b097-4611-a96e-254014990d8a/download/ury_elderly_60_plus_2019-06-01_csv.zip'
        }
    }

    #Brazil is split into 4 maps
    if isinstance(type(dataset_dict[country][map_type]), list):
        return pd.concat([pd.read_csv(file) for file in dataset_dict[country][map_type]])
    else:
        return pd.read_csv(dataset_dict[country][map_type])

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

    overpass_url = "http://overpass-api.de/api/interpreter"

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

def osmnx_graph(download_type, network_type='drive', query_str=None,
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
        G = ox.graph_from_polygon(geom)
        return G

    elif (download_type == 'point') and (geom is not None) and (distance is not None):
        G = ox.graph_from_point(geom, dist=distance)
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
