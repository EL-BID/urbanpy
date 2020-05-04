import pandas as pd
from math import radians
from sklearn.neighbors import BallTree
from numba import jit

__all__ = [
    'swap_xy',
    'nn_search',
    'tuples_to_lists',
    'shell_from_geometry',
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

def nn_search(tree_features, query_features, metric='haversine', convert_radians=False):
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
        tf = pd.DataFrame(tree_features)
        tf[0] = tf[0].apply(radians)
        tf[1] = tf[1].apply(radians)
        tree = BallTree(tf, metric=metric)
    else:
        tree = BallTree(tree_features, metric=metric)


    return tree.query(query_features)[0] * 6371000/1000

@jit
def tuples_to_lists(json):
    '''
    Util function to convert the geo interface of a GeoDataFrame to PyDeck GeoJSON format.

    Parameters
    ----------

    json: GeoJSON from a GeoDataFrame.__geo_interface__


    Returns
    -------

    json: dict
              GeoJSON with the corrected features

    Example
    -------

    >> json = {
        'type': 'FeatureCollection'
        'features': [
            {
                'id': 0,
                'geometry': {
                    'coordinates' = (((-77, -12), (-77.1, -12.1)))
                }
            }
        ]
    }

    >> tuples_to_lists(json)

    {
        'type': 'FeatureCollection'
        'features': [
            {
                'id': 0,
                'geometry': {
                    'coordinates' = [[[-77, -12], [-77.1, -12.1]]]
                }
            }
        ]
    }
    '''

    for i in range(len(json['features'])):
        t = [list(x) for x in json['features'][i]['geometry']['coordinates']]
        poly = [[list(x) for x in t[0]]]

        json['features'][i]['geometry']['coordinates'] = poly

    return json

def shell_from_geometry(geometry):
    '''
    Util function for park and pitch processing.
    '''

    shell = []
    for record in geometry:
        shell.append([record['lon'], record['lat']])
    return shell
