import geopandas as gpd
import pandas as pd
import numpy as np
from h3 import h3
from math import ceil
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
from sklearn.neighbors import BallTree
from typing import Optional, Union, Tuple
from pandas import DataFrame
from geopandas import GeoDataFrame, GeoSeries

__all__ = [
    "swap_xy",
    "nn_search",
    "shell_from_geometry",
    "geo_boundary_to_polygon",
    "create_duration_labels",
    "to_overpass_query",
    "overpass_to_gdf",
    "get_hdx_label",
    "HDX_POPULATION_TYPES",
]


def swap_xy(geom):
    """
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

    Examples
    --------

    >>> p = Point(-77,-12)
    >>> p_ = urbanpy.utils.swap_xy(p)
    >>> print((p.x, p.y), (p_.x, p_.y))
    (-77.0, -12.0) (-12.0, -77.0)

    """
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
    if geom.geom_type in ("Point", "LineString", "LinearRing"):
        return type(geom)(list(swap_xy_coords(geom.coords)))
    elif geom.geom_type == "Polygon":
        ring = geom.exterior
        shell = type(ring)(list(swap_xy_coords(ring.coords)))
        holes = list(geom.interiors)
        for pos, ring in enumerate(holes):
            holes[pos] = type(ring)(list(swap_xy_coords(ring.coords)))
        return type(geom)(shell, holes)
    elif geom.geom_type.startswith("Multi") or geom.type == "GeometryCollection":
        # Recursive call
        return type(geom)([swap_xy(part) for part in geom.geoms])
    else:
        raise ValueError("Type %r not recognized" % geom.geom_type)


def nn_search(tree_features, query_features, metric="haversine"):
    """
    Build a BallTree for nearest neighbor search based on selected distance.

    Parameters
    ----------

    tree_features: array_like
                   Input features to create the search tree. Features are in
                   lat, lon format.

    query_features: array_like
                    Points to which calculate the nearest neighbor within the tree.
                    lat, lon coordinates expected.

    metric: str
            Distance metric for neighorhood search. Default haversine for latlon coordinates.
            If haversine is selected lat, lon coordinates are converted to radians.

    Returns
    -------

    dist: array_like
          Array with the corresponding distance in km (if haversine then distance * earth radius)

    ind: array_like
         Array with the corresponding index of the tree_features values.

    Examples
    --------

    >>> x = np.random.uniform(-78,-79, 20)
    >>> y = np.random.uniform(-12, -11, 20)
    >>> features = np.vstack([x,y]).T
    >>> query = [[-77,-12]]
    >>> urbanpy.utils.nn_search(features, query)

    """

    if metric == "haversine":
        tf = np.radians(tree_features)
        tree = BallTree(tf, metric=metric)

        qf = np.radians(query_features)

        dist, ind = tree.query(qf)
        return dist * 6371000 / 1000, ind
    else:
        tree = BallTree(tree_features, metric=metric)
        dist, ind = tree.query(query_features)
        return dist, ind


def shell_from_geometry(geometry):
    """
    Util function for park and pitch processing.
    """

    shell = []
    for record in geometry:
        shell.append([record["lon"], record["lat"]])
    return shell


def geo_boundary_to_polygon(x):
    """
    Transform h3 geo boundary to shapely Polygon

    Parameters
    ----------

    x: str
        H3 hexagon index

    Returns
    -------

    polygon: Polygon
        Polygon representing H3 hexagon area

    """
    return Polygon(
        [bound[::-1] for bound in h3.h3_to_geo_boundary(x)]
    )  #  format as x,y (lon, lat)


def create_duration_labels(durations):
    """
    Creates inputs for pd.cut function (bins and labels) especifically for the trip durations columns.

    Parameters
    ----------

    durations: Pandas Series
        Series containing trip durations in minutes.

    Returns
    -------

    custom_bins: list
        List of numbers with the inputs for the bins parameter of pd.cut function

    custom_labels: list
        List of numbers with the inputs for the labels parameter of pd.cut function

    """
    default_bins = [0, 15, 30, 45, 60, 90, 120]
    default_labels = [f"{default_bins[i]}-{default_bins[i+1]}" for i in range(len(default_bins) - 1)]
    default_labels.append(f">{default_bins[-1]}")

    bins_ = default_bins.copy()

    max_duration_raw = durations.max()
    max_duration_asint = ceil(max_duration_raw)

    bins_.insert(0, max_duration_asint)
    bins_ = sorted(set(bins_))
    ix = bins_.index(max_duration_asint)

    if (ix + 1) >= len(default_bins) and max_duration_asint != default_bins[-1]:
        default_bins.append(max_duration_asint)

    custom_bins = default_bins[: ix + 1]
    custom_labels = default_labels[:ix]

    return custom_bins, custom_labels


def to_overpass_query(type_of_data: str, query: dict) -> str:
    """
    Parse query dict to build Overpass QL query.

    Parameters
    ----------
    type_of_data: str
        OSM type of data (One of: relation, node, way).
    query: dict
        OSM keys and values to be queried

    Returns
    -------
    overpass_query: str
        Formatted query string to be passed to Overpass QL.
    """

    if len(query) == 0:
        ov_body = f"{type_of_data};"
    else:
        ov_body = ""

        for key, values in query.items():
            if values is None:
                operator = ""
                values_str = ""

            if type(values) == str:
                operator = "="
                values_str = f'"{values}"'

            if type(values) == list:
                n_values = len(values)

                if n_values == 0:
                    operator = ""
                    values_str = ""
                if n_values >= 1:
                    operator = "~"
                    values_str = f'"{"|".join(v for v in values)}"'

            ov_body += f"""{type_of_data}[\"{key}\"{operator}{values_str}];\n"""

    overpass_query = f"""[timeout:120][out:json][bbox];
    ({ov_body});
    out body geom;"""

    return overpass_query


def process_overpass_relations(
    data: dict,
    mask: Optional[Union[GeoDataFrame, GeoSeries, Polygon, MultiPolygon]] = None,
) -> Tuple[DataFrame, GeoDataFrame]:
    """
    Process relation data structure from an Overpass API response.

    Parameters
    ----------
    data: dict
        Overpass API response payload.
    mask: GeoDataFrame, GeoSeries, (Multi)Polygon
        Polygon vector layer used to clip the final gdf. See geopandas.clip().

    Returns
    -------
    gdf_members: GeoDataFrame
        All geometries from relations members with relation ID
    df_relations: DataFrame
        Relations metadata such as ID and tags.
    """

    df_relations = pd.DataFrame.from_dict(data["elements"]).drop("members", axis=1)

    # Separate nodes from ways members
    rels_nodes, rels_ways = [], []
    for elem in data["elements"]:
        for mem in elem["members"]:
            mem["relation_id"] = elem["id"]  # Set member-relation key
            if mem["type"] == "node":
                rels_nodes.append(mem)
            if mem["type"] == "way":
                rels_ways.append(mem)

    # Process node members
    df_nodes = pd.DataFrame.from_dict(rels_nodes)
    df_nodes["geometry"] = gpd.points_from_xy(df_nodes["lon"], df_nodes["lat"])
    gdf_nodes = gpd.GeoDataFrame(df_nodes, crs="EPSG:4326")

    #  Process way members
    df_ways = pd.DataFrame.from_dict(rels_ways)
    df_ways["shell"] = df_ways["geometry"].apply(shell_from_geometry)
    df_ways = df_ways[df_ways["shell"].apply(len) > 2]
    df_ways["geometry"] = df_ways["shell"].apply(Polygon)
    gdf_ways = gpd.GeoDataFrame(df_ways, crs="EPSG:4326")
    # buffer(0) is faster but shapely recommends make_valid()
    gdf_ways.geometry = gdf_ways.geometry.apply(make_valid)

    # Merge members and return gdf
    gdf_members = gpd.GeoDataFrame(pd.concat([gdf_nodes, gdf_ways]), crs="EPSG:4326")
    if mask is not None:
        # Using hexs is ~100x faster than adm boundaries
        gdf_members = gdf_members.clip(mask=mask)

    return gdf_members, df_relations


def overpass_to_gdf(
    type_of_data: str,
    data: dict,
    mask: Optional[Union[GeoDataFrame, GeoSeries, Polygon, MultiPolygon]] = None,
    ov_keys: Optional[list] = None,
) -> Tuple[GeoDataFrame, Optional[DataFrame]]:
    """
    Process overpass response data according to type_of_data and clip to mask if given.

    Parameters
    ----------
    type_of_data: str. One of {'node', 'way', 'relation', 'rel'}
        OSM Data structure to be queried from Overpass API.
    data: dict
        Response object's json result from Overpass API.
    mask: dict. Optional
        Dict contaning OSM tag filters. Dict keys can take OSM tags
        and Dict values can be list of strings, str or None.
        Check keys [OSM Map Features](https://wiki.openstreetmap.org/wiki/Map_features).
        Example: {
            'key0': ['v0a', 'v0b','v0c'],
            'key1': 'v1',
            'key2': None
        }
    ov_keys: list. Optional
        Unique OSM keys used in Overpass query (e.g. "amenity", "shop", etc) to fill "poi_type" df column.


    Returns
    -------
    gdf: GeoDataFrame
        POIs from the selected type of facility.
    df: DataFrame. Optional
        Relations metadata such as ID and tags. Returns None if 'type_of_data' other than 'relation'.
    """

    if type_of_data == "relation":
        return process_overpass_relations(data, mask)
    else:
        df = pd.DataFrame.from_dict(data["elements"])

        if type_of_data == "node":
            df["geometry"] = gpd.points_from_xy(df["lon"], df["lat"])

        if type_of_data == "way":
            df["geometry"] = df["geometry"].apply(
                lambda x: Polygon(shell_from_geometry(x))
            )

        gdf = gpd.GeoDataFrame(df, crs=4326)
        if mask is not None:
            gdf = gdf.clip(mask=mask)

        if ov_keys is not None:
            #  Extract relevant data from osm tags
            gdf["poi_type"] = gdf["tags"].apply(
                lambda tag: tag[ov_keys[0]] if ov_keys[0] in tag.keys() else np.NaN
            )
            for k in ov_keys:
                # Use other keys to complete NaNs
                gdf["poi_type"].fillna(
                    value=gdf["tags"].apply(
                        lambda tag: tag[k] if k in tag.keys() else np.NaN
                    )
                )
                if gdf["poi_type"].isna().sum() == 0:
                    break

        return gdf, None


HDX_POPULATION_TYPES = {
    "overall": "Overall population density",
    "women": "Women",
    "_men_": "Men",
    "children": "Children (ages 0-5)",
    "youth": "Youth (ages 15-24) ",
    "elderly": "Elderly (ages 60+)",
    "women_of_reproductive_age": "Women of reproductive age (ages 15-49)",
}


def get_hdx_label(name):
    """
    Get a human readable label from a HDX Facebook population density dataset filename.

    Parameters
    ----------
    name: str.
        HDX Facebook population density dataset filename.

    Returns
    -------
    labels str: GeoDataFrame
        POIs from the selected type of facility.
    df: DataFrame. Optional
        Relations metadata such as ID and tags. Returns None if 'type_of_data' other than 'relation'.
    """

    for keys, labels in HDX_POPULATION_TYPES.items():
        if keys in name:
            # Avoid assigning "women of reproductive age" label
            # to the general women dataset
            if (keys == "women") and ("reproductive" in name):
                continue

            return labels

    return HDX_POPULATION_TYPES["overall"]
