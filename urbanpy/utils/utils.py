import pandas as pd
import numpy as np
from h3 import h3
from math import ceil
from shapely.geometry import Polygon
from sklearn.neighbors import BallTree

__all__ = [
    'swap_xy',
    'nn_search',
    'shell_from_geometry',
    'geo_boundary_to_polygon',
    'create_duration_labels'
]

def swap_xy(geom):
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

    Examples
    --------

    >>> p = Point(-77,-12)
    >>> p_ = urbanpy.utils.swap_xy(p)
    >>> print((p.x, p.y), (p_.x, p_.y))
    (-77.0, -12.0) (-12.0, -77.0)

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

def nn_search(tree_features, query_features, metric='haversine'):
    '''
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

    '''

    if metric == 'haversine':

        tf = np.radians(tree_features)
        tree = BallTree(tf, metric=metric)

        qf = np.radians(query_features)

        dist, ind = tree.query(qf)
        return dist * 6371000/1000, ind
    else:
        tree = BallTree(tree_features, metric=metric)
        dist, ind = tree.query(query_features)
        return dist, ind

def shell_from_geometry(geometry):
    '''
    Util function for park and pitch processing.
    '''

    shell = []
    for record in geometry:
        shell.append([record['lon'], record['lat']])
    return shell

def geo_boundary_to_polygon(x):
    '''
    Transform h3 geo boundary to shapely Polygon

    Parameters
    ----------

    x: str
        H3 hexagon index

    Returns
    -------

    polygon: Polygon
        Polygon representing H3 hexagon area

    '''
    return Polygon([bound[::-1] for bound in h3.h3_to_geo_boundary(x)]) # format as x,y (lon, lat)

def create_duration_labels(durations):
    '''
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

    '''
    default_bins = [0, 15, 30, 45, 60, 90, 120]
    default_labels = ["De 0 a 15", "De 15 a 30", "De 30 a 45", "De 45 a 60",
                      "De 60 a 90", "De 90 a 120", "Más de 120"]

    bins_ = default_bins.copy()

    max_duration_raw = durations.max()
    max_duration_asint = ceil(max_duration_raw)

    bins_.insert(0, max_duration_asint)
    bins_ = sorted(set(bins_))
    ix = bins_.index(max_duration_asint)

    if (ix + 1) >= len(default_bins) and max_duration_asint != default_bins[-1]:
        default_bins.append(max_duration_asint)

    custom_bins = default_bins[:ix + 1]
    custom_labels = default_labels[:ix]

    return custom_bins, custom_labels
