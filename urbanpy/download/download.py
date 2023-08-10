from warnings import warn
import requests
import geopandas as gpd
import pandas as pd
import numpy as np
import osmnx as ox
from shapely.geometry import Polygon, MultiPolygon
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from typing import Optional, Union, Tuple
from pandas import DataFrame
from geopandas import GeoDataFrame, GeoSeries
from urbanpy.utils import (
    to_overpass_query,
    overpass_to_gdf,
    get_hdx_label,
    HDX_POPULATION_TYPES,
)

__all__ = [
    "nominatim_osm",
    "overpass_pois",
    "overpass",
    "osmnx_graph",
    "search_hdx_dataset",
    "get_hdx_dataset",
    "hdx_fb_population",
    "hdx_dataset",
]

hdx_config = Configuration.create(
    hdx_site="prod", user_agent="urbanpy", hdx_read_only=True
)


def nominatim_osm(query: str, expected_position=0) -> GeoDataFrame:
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
    osm_url = "https://nominatim.openstreetmap.org/search.php"
    osm_parameters = {"polygon_geojson": "1", "format": "geojson"}
    osm_parameters["q"] = query

    response = requests.get(osm_url, params=osm_parameters)
    all_results = response.json()
    gdf = gpd.GeoDataFrame.from_features(all_results["features"], crs="EPSG:4326")
    city = gdf.iloc[expected_position : expected_position + 1, :]

    return city


def overpass_pois(bounds, facilities=None, custom_query=None):
    """
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
    """
    minx, miny, maxx, maxy = bounds

    bbox_string = f"{minx},{miny},{maxx},{maxy}"

    overpass_url = "https://overpass-api.de/api/interpreter"

    facilities_opt = {
        "food": 'node["amenity"="marketplace"];\nnode["shop"~"supermarket|kiosk|mall|convenience|butcher|greengrocer"];',
        "health": 'node["amenity"~"doctors|dentist|clinic|hospital|pharmacy"];',
        "education": 'node["amenity"~"kindergarten|school|college|university"];',
        "finance": 'node["amenity"~"mobile_money_agent|bureau_de_change|bank|microfinance|atm|sacco|money_transfer|post_office"];',
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
        response = requests.get(
            overpass_url, params={"data": overpass_query, "bbox": bbox_string}
        )
        data = response.json()
        df = pd.DataFrame.from_dict(data["elements"])
        df_geom = gpd.points_from_xy(df["lon"], df["lat"])
        gdf = gpd.GeoDataFrame(df, geometry=df_geom, crs="EPSG:4326")

        gdf["poi_type"] = gdf["tags"].apply(
            lambda tag: tag["amenity"] if "amenity" in tag.keys() else np.NaN
        )

        if facilities == "food":
            # Food facilities also have its POI type wthin the shop tag (See query)
            also_poi_type = gdf["tags"].apply(
                lambda tag: tag["shop"] if "shop" in tag.keys() else np.NaN
            )
            gdf["poi_type"] = gdf["poi_type"].fillna(also_poi_type)

        return gdf

    else:
        response = requests.get(
            overpass_url, params={"data": custom_query, "bbox": bbox_string}
        )
        return response


def overpass(
    type_of_data: str,
    query: dict,
    mask: Union[GeoDataFrame, GeoSeries, Polygon, MultiPolygon],
) -> Tuple[GeoDataFrame, Optional[DataFrame]]:
    """
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
    """
    minx, miny, maxx, maxy = mask.total_bounds
    bbox_string = f"{minx},{miny},{maxx},{maxy}"

    # Request data
    overpass_url = "https://overpass-api.de/api/interpreter"
    params = {
        "data": to_overpass_query(
            type_of_data, query
        ),  # Parse query dict to build Overpass QL query
        "bbox": bbox_string,
    }
    response = requests.get(overpass_url, params=params)
    try:
        data = response.json()
    except Exception as e:
        print(e)
        print(response.status_code)
        print(response.reason)
        return response

    ov_keys = list(
        set(query.keys())
    )  # get unique keys used in query (e.g. "amenity", "shop", etc)

    return overpass_to_gdf(type_of_data, data, mask, ov_keys)


def osmnx_graph(
    download_type: str,
    network_type="drive",
    query_str=None,
    geom=None,
    distance=None,
    **kwargs,
):
    """
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
    """
    if (
        (download_type == "polygon")
        and (geom is not None)
        and isinstance(geom, Polygon)
    ):
        G = ox.graph_from_polygon(geom, network_type=network_type)
        return G
    elif (download_type == "point") and (geom is not None) and (distance is not None):
        G = ox.graph_from_point(geom, dist=distance, network_type=network_type)
        return G

    elif download_type == "place" and query_str is not None:
        G = ox.graph_from_place(query_str, network_type=network_type)
        return G

    elif download_type == "polygon" and geom is None:
        print("Please provide a polygon to download a network from.")

    elif download_type == "place" and query_str is None:
        print("Please provide a query string to download a network from.")

    else:
        if distance is None and download_type == "point":
            print("Please provide a distance buffer for the point download")

        if geom is None and distance is not None:
            print("Please provide a Point geometry.")


def search_hdx_dataset(
    country: str,
    repository="high-resolution-population-density-maps-demographic-estimates",
):
    """
    Dataset search within HDX repositories. Defaults to population density maps.

    Parameters
    ----------
    country: str
        Country to search datasets

    resource: str
        Resource type within the HDX database

    Returns
    -------
    datasets: DataFrame
        DataFrame of available datasets within HDX

    Examples
    --------
    >>> resources_df = urbanpy.download.search_hdx_dataset('peru')
    >>> resources_df
       | created	| name	                                            | population	                            | size_mb |	url
    id |			| 	                                                |                                           |         |
    0  | 2019-06-11	| population_per_2018-10-01.csv.zip	                | Overall population density	            | 19.36	  | https://data.humdata.org/dataset/4e74db39-87f1...
    2  | 2019-06-11	| PER_children_under_five_2019-06-01_csv.zip	    | Children (ages 0-5)	                    | 16.60	  | https://data.humdata.org/dataset/4e74db39-87f1...
    4  | 2019-06-11	| PER_elderly_60_plus_2019-06-01_csv.zip	        | Elderly (ages 60+)	                    | 16.59	  | https://data.humdata.org/dataset/4e74db39-87f1...
    6  | 2019-06-11	| PER_men_2019-06-01_csv.zip	                    | Men	                                    | 16.64	  | https://data.humdata.org/dataset/4e74db39-87f1...
    8  | 2019-06-11	| PER_women_2019-06-01_csv.zip	                    | Women	                                    | 16.63	  | https://data.humdata.org/dataset/4e74db39-87f1...
    10 | 2019-06-11	| PER_women_of_reproductive_age_15_49_2019-06-01... | Women of reproductive age (ages 15-49)    | 16.62	  | https://data.humdata.org/dataset/4e74db39-87f1...
    12 | 2019-06-11	| PER_youth_15_24_2019-06-01_csv.zip	            | Youth (ages 15-24)	                    | 16.61	  | https://data.humdata.org/dataset/4e74db39-87f1...
    """
    # Get dataset list
    datasets = Dataset.search_in_hdx(f"title:{country.lower()}-{repository}")

    resources_records = Dataset.get_all_resources(datasets)
    resources_df = pd.DataFrame.from_records(resources_records)
    if resources_df.shape[0] == 0:
        print("No datasets found")

    else:
        resources_csv_df = resources_df[
            resources_df["download_url"].str.contains("csv")
        ]

        resources_csv_df = resources_csv_df.assign(
            created=pd.to_datetime(resources_csv_df["created"]).dt.date,
            size_mb=(resources_csv_df["size"] / 2**20).round(2),
        )

        if (
            repository
            == "high-resolution-population-density-maps-demographic-estimates"
        ):
            resources_csv_df = resources_csv_df.assign(
                population=resources_csv_df["name"].apply(get_hdx_label)
            )

        resources_csv_df.index.name = "id"

        return resources_csv_df[["created", "name", "population", "size_mb", "url"]]


def get_hdx_dataset(resources_df: DataFrame, ids: Union[int, list]) -> DataFrame:
    """
    HDX dataset download.

    Parameters
    ----------
    resources_df: pd.DataFrame
        Resources dataframe from returned by search_hdx_dataset

    ids: int or list
        IDs in the resources dataframe

    Returns
    -------
    data: pd.DataFrame
        The corresponding dataset in DataFrame format

    Examples
    --------
    >>> resources_df = urbanpy.download.search_hdx_dataset('peru')
    >>> population_df = urbanpy.download.get_hdx_dataset(resources_df, 0)
    >>> population_df
    latitude   | longitude  | population_2015 |	population_2020
    -18.339306 | -70.382361 | 11.318147	      | 12.099885
    -18.335694 | -70.393750 | 11.318147	      | 12.099885
    -18.335694 | -70.387361	| 11.318147	      | 12.099885
    -18.335417 | -70.394028	| 11.318147	      | 12.099885
    -18.335139 | -70.394306	| 11.318147	      | 12.099885
    """
    urls = resources_df.loc[ids, "url"]

    if isinstance(ids, list) and len(ids) > 1:
        return pd.concat([pd.read_csv(url) for url in urls])
    else:
        return pd.read_csv(urls)


def hdx_fb_population(country, map_type):
    """
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
    """

    resources_df = search_hdx_dataset(country)

    # Rename older "full" map_type to "overall"
    if map_type == "full":
        map_type = "overall"

    # Get correct dataset/s index
    dataset_ix = resources_df[
        resources_df["population"] == HDX_POPULATION_TYPES[map_type]
    ].index.tolist()

    population = get_hdx_dataset(resources_df, dataset_ix)

    return population


# Added for backwards compatibility
def hdx_dataset(resource):
    """
    Download a dataset from HDX. The allowed formats are CSV (.csv) and zipped
    CSV (.csv.zip). To run our function we would only copy what is after "https://data.humdata.org/dataset/"
    to the 'resource' parameter.

    For example: '4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip'.

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
    warn(
        "This function will be deprecated. Please use search_hdx_dataset and get_hdx_dataset instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    hdx_url = f"https://data.humdata.org/dataset/{resource}"
    dataset = pd.read_csv(hdx_url)
    return dataset
