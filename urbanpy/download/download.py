from typing import Optional, Tuple, Union, List
from warnings import warn

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import requests
from geopandas import GeoDataFrame, GeoSeries
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from pandas import DataFrame
from shapely.geometry import MultiPolygon, Polygon, Point
from hdx.api.configuration import ConfigurationError

try:
    import ee

    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False

from urbanpy.utils import (
    HDX_POPULATION_TYPES,
    get_hdx_label,
    overpass_to_gdf,
    to_overpass_query,
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
    "google_satellite_embeddings",
]

# Module-level constants for GEE/AlphaEarth
GEE_MAX_FEATURES_PER_REQUEST = 5000
ALPHAEARTH_YEAR_MIN = 2017
ALPHAEARTH_YEAR_MAX = 2024
ALPHAEARTH_DEFAULT_YEAR = 2024
ALPHAEARTH_NUM_BANDS = 64
VALID_EMBEDDING_BANDS = [f"A{i:02d}" for i in range(ALPHAEARTH_NUM_BANDS)]

# Initialize HDX configuration only if not already created
try:
    hdx_config = Configuration.read()
except ConfigurationError:
    hdx_config = Configuration.create(
        hdx_site="prod", user_agent="urbanpy", hdx_read_only=True
    )


def nominatim_osm(
    query: str, expected_position: "int | None" = 0, email: str = ""
) -> GeoDataFrame:
    """
    Download OpenStreetMaps data for a specific city.

    Parameters
    ----------
    query: str
        Query string for OSM data to be downloaded (e.g. "Lima, Peru").
    expected_position: int 0:n
        Expected position of the polygon data within the Nominatim results.
        Default 0 returns the first result.
        If set to None, all the results are returned.

    Returns
    -------
    gdf: GeoDataFrame
        GeoDataFrame with the fetched OSM data.

    Examples
    --------
    >>> lima = nominatim_osm('Lima, Peru', 2)
    >>> lima.head()
    geometry	 | place_id	 | osm_type	| osm_id     | display_name	| place_rank  |  category | type	       | importance	| icon
    MULTIPOLYGON | 235480647 | relation	| 1944670.0  | Lima, Peru	| 12	      |  boundary |	administrative | 0.703484	| https://nominatim.openstreetmap.org/images/map...
    """
    if email == "":
        raise ValueError(
            "Please provide an email to avoid violating Nominatim API rules."
        )
    osm_url = "https://nominatim.openstreetmap.org/search.php"
    osm_parameters = {
        "q": query,
        "polygon_geojson": "1",
        "format": "geojson",
        "email": email,
    }

    response = requests.get(osm_url, params=osm_parameters)
    all_results = response.json()
    gdf = gpd.GeoDataFrame.from_features(all_results["features"], crs="EPSG:4326")
    if expected_position is None:
        return gdf

    return gdf.iloc[expected_position : expected_position + 1]


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
    type_of_data : str
        One of {'node', 'way', 'relation', 'rel'}. OSM Data structure to be queried from Overpass API.
    query : dict
        Dict containing OSM tag filters. Dict keys can take OSM tags and Dict values can be a list of strings, str, or None.
        Example: { 'key0': ['v0a', 'v0b', 'v0c'], 'key1': 'v1', 'key2': None }
        Check keys [OSM Map Features](https://wiki.openstreetmap.org/wiki/Map_features).
    mask : GeoDataFrame, GeoSeries, Polygon, or MultiPolygon
        Total bounds of mask to be used for the query.

    Returns
    -------
    gdf : GeoDataFrame
        POIs from the selected type of facility.
    df : DataFrame
        Relations metadata such as ID and tags. Returns None if 'type_of_data' is other than 'relation'.

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


def get_hdx_dataset(
    resources_df: DataFrame,
    ids: Union[int, list],
    mask: Union[GeoDataFrame, Polygon, MultiPolygon] = None,
) -> DataFrame:
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

    print(urls)
    if isinstance(ids, list) and len(ids) > 1:
        df = pd.concat([pd.read_csv(url) for url in urls])
    else:
        df = pd.read_csv(urls)

    if mask:
        if isinstance(mask, GeoDataFrame):
            mask = mask.unary_union
        minx, miny, maxx, maxy = mask.bounds

        df_filtered = df[
            (df["longitude"] >= minx)
            & (df["longitude"] <= maxx)
            & (df["latitude"] >= miny)
            & (df["latitude"] <= maxy)
        ]
        df_filtered.loc[:, "geometry"] = df_filtered.apply(
            lambda row: Point(row["longitude"], row["latitude"]), axis=1
        )
        gdf = gpd.GeoDataFrame(df_filtered)

        return gdf[gdf.geometry.intersects(mask)]
    else:
        return df


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

    if not resource.ends_with(".csv"):
        raise AttributeError("This function only expects a CSV file.")

    if not resource.starts_with("https://data.humdata.org/dataset/"):
        hdx_url = f"https://data.humdata.org/dataset/{resource}"
    else:
        hdx_url = hdx_url

    dataset = pd.read_csv(hdx_url)

    return dataset


# GEE Downloads


def google_satellite_embeddings(
    gdf: gpd.GeoDataFrame,
    year: int = ALPHAEARTH_DEFAULT_YEAR,
    bands: Optional[List[str]] = None,
    reducer: str = "mean",
    scale: int = 10,
    tile_scale: int = 1,
) -> gpd.GeoDataFrame:
    """
    Download Google Earth Engine satellite embeddings for geometries.

    Uses Google's AlphaEarth Foundations satellite embedding dataset to extract
    64-dimensional learned representations that encode temporal trajectories of
    surface conditions. Each embedding captures spectral, spatial, and temporal
    context from multi-sensor Earth observation data.
    Reduces each geometry to a single embedding vector using the specified reducer.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input geometries (H3 hexagons, admin areas, etc.)
    year : int, default ALPHAEARTH_DEFAULT_YEAR
        Year for satellite data (ALPHAEARTH_YEAR_MIN-ALPHAEARTH_YEAR_MAX available)
    bands : list, optional
        Embedding bands to download (A00-A63). If None, uses all 64 bands.
    reducer : str, default 'mean'
        Reduction method for pixels within each geometry: 'mean', 'median', 'first'
    scale : int, default 10
        Pixel resolution in meters (native is 10m)
    tile_scale : int, default 1
        Tile scale factor for memory management (increase for large areas)

    Returns
    -------
    GeoDataFrame
        Input geometries with embedding columns (A00, A01, ...) added.
        If no satellite data is found, returns original GeoDataFrame unchanged.

    Examples
    --------
    >>> # Download city and create hexagons
    >>> lima = up.download.nominatim_osm("Lima, Peru", email="user@email.com")
    >>> hexes = up.geom.gen_hexagons(8, lima)
    >>>
    >>> # Download all 64 embedding bands
    >>> embeddings = up.download.google_satellite_embeddings(hexes, year=2023)
    >>>
    >>> # Use with different reducer methods
    >>> embeddings_median = up.download.google_satellite_embeddings(
    ...     hexes, year=2023, reducer='median'
    ... )

    Notes
    -----
    Requires Earth Engine authentication. Run `ee.Authenticate()` and `ee.Initialize()`
    before using this function.

    **GEE Limitations**: Maximum GEE_MAX_FEATURES_PER_REQUEST geometries per request due to Earth Engine's
    "Collection query aborted after accumulating over 5000 elements" limit when
    retrieving results. For larger datasets, process in batches.

    The embeddings are "linearly composable", meaning they can be aggregated
    while retaining semantic meaning. Use `up.geom.resolution_downsampling()`
    to aggregate fine H3 hexagons to coarser resolutions.
    """

    if not EE_AVAILABLE:
        raise ImportError(
            "Earth Engine not available. Install with: pip install earthengine-api"
        )

    # GEE system limitation: getInfo() fails with > GEE_MAX_FEATURES_PER_REQUEST features
    if len(gdf) > GEE_MAX_FEATURES_PER_REQUEST:
        raise ValueError(
            f"Too many geometries ({len(gdf)}). Maximum {GEE_MAX_FEATURES_PER_REQUEST:,} supported due to "
            f"Earth Engine's 'Collection query aborted after accumulating over 5000 elements' "
            f"limitation. Process in batches or use fewer geometries."
        )

    if year < ALPHAEARTH_YEAR_MIN or year > ALPHAEARTH_YEAR_MAX:
        raise ValueError(
            f"Year {year} not supported. Available years: {ALPHAEARTH_YEAR_MIN}-{ALPHAEARTH_YEAR_MAX}"
        )

    if reducer not in ["mean", "median", "first"]:
        raise ValueError(
            f"Unsupported reducer: {reducer}. Use 'mean', 'median', or 'first'"
        )

    if scale < 1:
        raise ValueError(f"Scale must be positive, got {scale}")

    # Use all embedding bands by default
    if bands is None:
        bands = VALID_EMBEDDING_BANDS.copy()

    # Validate bands
    invalid_bands = [b for b in bands if b not in VALID_EMBEDDING_BANDS]
    if invalid_bands:
        raise ValueError(
            f"Invalid bands: {invalid_bands}. Valid bands are A00-A{ALPHAEARTH_NUM_BANDS-1:02d}"
        )

    # Load collection and filter
    collection = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # Filter by date and bounds
    bounds = gdf.total_bounds
    roi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])

    filtered = collection.filterDate(start_date, end_date).filterBounds(roi)

    # Create mosaic and select bands
    # Note: If collection is empty, mosaic() will create an empty image
    # and reduceRegions will return empty results, which we handle downstream
    image = filtered.mosaic().select(bands)

    # Convert GeoDataFrame to EE FeatureCollection
    fc = _gdf_to_ee_fc(gdf)

    # Set up reducer
    if reducer == "mean":
        ee_reducer = ee.Reducer.mean()
    elif reducer == "median":
        ee_reducer = ee.Reducer.median()
    elif reducer == "first":
        ee_reducer = ee.Reducer.first()

    # Use reduceRegions for efficient computation
    result_fc = image.reduceRegions(
        collection=fc, reducer=ee_reducer, scale=scale, tileScale=tile_scale
    )

    # Convert back to GeoDataFrame and join with original
    return _format_ee_embedding_results(gdf, result_fc, bands, year)


def _gdf_to_ee_fc(gdf: gpd.GeoDataFrame) -> "ee.FeatureCollection":
    """Convert GeoDataFrame to Earth Engine FeatureCollection."""

    return ee.FeatureCollection(
        gdf.reset_index(names="urbanpy_index")
        .apply(
            lambda row: ee.Feature(
                ee.Geometry(row.geometry.__geo_interface__),
                row.drop("geometry").to_dict(),
            ),
            axis=1,
        )
        .to_list()
    )


def _format_ee_embedding_results(
    original_gdf: gpd.GeoDataFrame,
    result_fc: "ee.FeatureCollection",
    bands: List[str],
    year: int,
) -> gpd.GeoDataFrame:
    """Format Earth Engine results into a GeoDataFrame."""

    try:
        # Get the results as a list of dictionaries
        result_list = result_fc.getInfo()["features"]
        print(f"Retrieved {len(result_list)} features from Earth Engine")
        print(result_list[0])
        print(result_list[5])
    except Exception as e:
        # Handle case where no data is available
        warn(
            f"No satellite embedding data found for year {year}. "
            f"Returning original GeoDataFrame unchanged."
        )
        return original_gdf.copy()

    # Check if we got any results
    if not result_list or len(result_list) == 0:
        warn(
            f"No satellite embedding data found for year {year}. "
            f"Returning original GeoDataFrame unchanged."
        )
        return original_gdf.copy()

    result_gdf = gpd.GeoDataFrame.from_features(result_list, crs=original_gdf.crs)
    result_gdf = result_gdf.set_index("urbanpy_index")
    result_gdf.index.name = original_gdf.index.name

    return result_gdf
