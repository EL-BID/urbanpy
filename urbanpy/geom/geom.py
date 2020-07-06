import pandas as pd
import geopandas as gpd
import osmnx as ox
from h3 import h3
from tqdm import tqdm
from urbanpy.utils import geo_boundary_to_polygon

__all__ = [
    'merge_geom_downloads',
    'filter_population',
    'remove_features',
    'gen_hexagons',
    'merge_shape_hex',
    'overlay_polygons_hexs',
    'resolution_downsampling',
    'osmnx_coefficient_computation',
]

def merge_geom_downloads(gdfs):
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

    Examples
    --------

    >>> lima = urbanpy.download.nominatim_osm("Lima, Peru", 2)
    >>> callao = urbanpy.download.nominatim_osm("Callao, Peru", 1)
    >>> lima = urbanpy.geom.merge_geom_downloads([lima, callao])
    >>> lima.head()
    geometry
    MULTIPOLYGON (((-76.80277 -12.47562, -76.80261...)))

    '''

    concat = gpd.GeoDataFrame(geometry=[pd.concat(gdfs).unary_union])
    return concat

def filter_population(pop_df, polygon_gdf):
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

    Examples
    --------

    >>> lima = urbanpy.download.nominatim_osm("Lima, Peru", 2)
    >>> callao = urbanpy.download.nominatim_osm("Callao, Peru", 1)
    >>> lima = urbanpy.geom.merge_geom_downloads([lima, callao])
    >>> pop = urbanpy.download.hdx_fb_population('peru', 'full')
    >>> urbanpy.geom.filter_population(pop, lima)
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

def remove_features(gdf, bounds):
    '''
    Remove a set of features based on bounds

    Parameters
    ----------

    gdf: GeoDataFrame
             Input GeoDataFrame containing the point features filtered with filter_population

    bounds: array_like
                Array input following [minx, miny, maxx, maxy] for filtering (GeoPandas total_bounds method output)


    Returns
    -------

    gdf: GeoDataFrame
             Input DataFrame but without the desired features

    Examples
    --------

    >>> lima = urbanpy.geom.filter_population(pop_lima, poly_lima)
    >>> removed = urbanpy.geom.remove_features(lima, [-12.2,-12, -77.2,-77.17]) #Remove San Lorenzo Island
    >>> print(lima.shape, removed.shape)
    (348434, 4) (348427, 4)

    '''
    minx, miny, maxx, maxy = bounds
    drop_ix = gdf.cx[minx:maxx, miny:maxy].index

    return gdf.drop(drop_ix)

def gen_hexagons(resolution, city):
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

    Examples
    --------

    >>> lima = urbanpy.geom.filter_population(pop_lima, poly_lima)
    >>> lima_hex = urbanpy.geom.gen_hexagons(8, lima)
    hex	            | geometry
    888e620e41fffff | POLYGON ((-76.80007 -12.46917, -76.80439 -12.4...))
    888e62c809fffff | POLYGON ((-77.22539 -12.08663, -77.22971 -12.0...))
    888e62c851fffff | POLYGON ((-77.20708 -12.08484, -77.21140 -12.0...))
    888e62c841fffff | POLYGON ((-77.22689 -12.07104, -77.23122 -12.0...))
    888e62c847fffff | POLYGON ((-77.23072 -12.07929, -77.23504 -12.0...))

    '''

    # Polyfill the city boundaries
    h3_polygons = list()
    h3_indexes = list()

    # Get every polygon in Multipolygon shape
    city_poly = city.explode().reset_index(drop=True)

    for _, geo in city_poly.iterrows():
        hexagons = h3.polyfill(geo['geometry'].__geo_interface__, res=resolution, geo_json_conformant=True)
        for hexagon in hexagons:
            h3_polygons.append(geo_boundary_to_polygon(hexagon))
            h3_indexes.append(hexagon)

    # Create hexagon dataframe
    city_hexagons = gpd.GeoDataFrame(h3_indexes, geometry=h3_polygons).drop_duplicates()
    city_hexagons.crs = 'EPSG:4326'
    city_hexagons = city_hexagons.rename(columns={0: 'hex'}) # Format column name for readability

    return city_hexagons

def merge_shape_hex(hexs, shape, agg, how='inner', op='intersects'):
    '''
    Merges a H3 hexagon GeoDataFrame with a Point GeoDataFrame and aggregates the
    point gdf data.

    Parameters
    ----------

    hexs: GeoDataFrame
          Input GeoDataFrame containing hexagon geometries

    shape: GeoDataFrame
           Input GeoDataFrame containing points and features to be aggregated

    agg: dict
         A dictionary with column names as keys and values as aggregation
         operations. The aggregation must be one of {'sum', 'min', 'max'}.

    how: str. One of {'inner', 'left', 'right'}. Default 'inner'.
         Determines how to merge data:
             'left' uses keys from left and only retains geometry from left
             'right' uses keys from right and only retains geometry from right
             'inner': use intersection of keys from both dfs; retain only left geometry column

    op: str. One of {'intersects', 'contains', 'within'}. Default 'intersects'
        Determines how geometries are queried for merging.

    Returns
    -------

    hexs: GeoDataFrame
          Result of a spatial join within hex and points. All features are aggregated
          based on the input parameters

    Examples
    --------

    >>> lima = urbanpy.download.nominatim_osm('Lima, Peru', 2)
    >>> pop_lima = urbanpy.download.hdx_fb_population('peru', 'full')
    >>> pop_df = urbanpy.filter_population(pop_lima, lima)
    >>> hexs = urbanpy.geom.gen_hexagons(8, lima)
    >>> urbanpy.geom.merge_point_hex(hexs, pop_df, 'inner', 'within', {'population_2020':'sum'})
    0               | geometry                                          | population_2020
    888e628d8bfffff | POLYGON ((-76.66002 -12.20371, -76.66433 -12.2... | NaN
    888e62c5ddfffff | POLYGON ((-76.94564 -12.16138, -76.94996 -12.1... | 14528.039097
    888e62132bfffff | POLYGON ((-76.84736 -12.17523, -76.85167 -12.1... | 608.312696
    888e628debfffff | POLYGON ((-76.67982 -12.18998, -76.68413 -12.1... | NaN
    888e6299b3fffff | POLYGON ((-76.78876 -11.97286, -76.79307 -11.9... | 3225.658803

    '''

    joined = gpd.sjoin(shape, hexs, how=how, op=op)

    #Uses index right based on the order of points and hex. Right takes hex index
    hex_merge = joined.groupby('index_right').agg(agg)

    #Avoid SpecificationError by copying the DataFrame
    ret_hex = hexs.copy()

    for key in agg.keys():
        ret_hex.loc[hex_merge.index, key] = hex_merge[key].values

    return ret_hex

def overlay_polygons_hexs(polygons, hexs, hex_col, columns):
    '''
    Overlays a Polygon GeoDataFrame with a H3 hexagon GeoDataFrame and divide the 'columns' the values proportionally to the overlayed area.

    Parameters
    ----------
    polygons: GeoDataFrame
                Input GeoDataFrame containing polygons and columns to be processed

    hexs: GeoDataFrame
             Input GeoDataFrame containing desired output hexagon resolution geometries

    hex_col: str
            Determines the column with the hex id.

    columns: list
             A list with column names of the columns that are going to be proportionally adjusted

    Returns
    -------

    hexs: GeoDataFrame
           Result of a spatial join within hex and points. All columns are adjusted
           based on the overlayed area.

    Examples
    --------

    >>> urbanpy.geom.overlay_polygons_hexs(zonas_pob, hex_lima, 'hex', pob_vulnerable)
                hex |  POB_TOTAL |  geometry
    898e6200493ffff | 193.705376 |  POLYGON ((-76.80695 -12.35199, -76.80812 -12.3...
    898e6200497ffff | 175.749780 |  POLYGON ((-76.80412 -12.35395, -76.80528 -12.3...
    898e620049bffff |  32.231078 |  POLYGON ((-76.81011 -12.35342, -76.81127 -12.3...
    898e62004a7ffff |  74.154973 |  POLYGON ((-76.79911 -12.36468, -76.80027 -12.3...
    898e62004b7ffff |  46.989828 |  POLYGON ((-76.79879 -12.36128, -76.79995 -12.3...

    '''
    polygons_ = polygons.copy() # Preserve data state
    polygons_['poly_area'] = polygons_.geometry.area # Calc polygon area

    # Overlay intersection
    overlayed = gpd.overlay(polygons_, hexs, how='intersection')

    # Downsample indicators using proporional overlayed area w.r.t polygon area
    area_prop = overlayed.geometry.area / overlayed['poly_area']
    overlayed[columns] = overlayed[columns].apply(lambda col: col * area_prop)

    # Aggregate over Hex ID
    per_hexagon_data = overlayed.groupby(hex_col)[columns].sum()

    # Preserve data as GeoDataFrame
    hex_df = pd.merge(left=per_hexagon_data, right=hexs[[hex_col,'geometry']], on=hex_col)
    hex_gdf = gpd.GeoDataFrame(hex_df[[hex_col]+columns], geometry=hex_df['geometry'], crs=hexs.crs)

    return hex_gdf

def resolution_downsampling(gdf, hex_col, coarse_resolution, agg):
    '''
    Downsample hexagon resolution aggregating indicated metrics (e.g. Transform hexagon resolution from 9 to 6).

    Parameters
    ----------

    gdf: GeoDataFrame
         GeoDataFrame with hexagon geometries (output from gen_hexagons).

    hex_col: str
             Determines the column with the hex id.

    coarse_resolution: int, 0:15
                       Hexagon resolution lower than gdf actual resolution (higher values create smaller hexagons).

    Returns
    -------

    gdfc: GeoDataFrame
          GeoDataFrame with lower resolution hexagons geometry and metrics aggregated as indicated.

    '''

    gdf_coarse = gdf.copy()
    coarse_hex_col = 'hex_{}'.format(coarse_resolution)
    gdf_coarse[coarse_hex_col] = gdf_coarse[hex_col].apply(lambda x: h3.h3_to_parent(x,coarse_resolution))
    dfc = gdf_coarse.groupby([coarse_hex_col]).agg(agg).reset_index()
    gdfc_geometry = dfc[coarse_hex_col].apply(geo_boundary_to_polygon)

    return gpd.GeoDataFrame(dfc, geometry=gdfc_geometry, crs=gdf.crs)

def osmnx_coefficient_computation(gdf, net_type, basic_stats, extended_stats, connectivity=False, anc=False, ecc=False, bc=False, cc=False):
    '''
    Apply osmnx's graph from polygon to query a city's street network within a geometry.
    This may be a long procedure given the hexagon layer resolution.

    Parameters
    ----------

    gdf: GeoDataFrame
         GeoDataFrame with geometries to download graphs contained within them.

    net_type: str
              Network type to download. One of {'drive', 'drive_service', 'walk', 'bike', 'all', 'all_private'}

    basic_stats: list
                 List of basic stats to compute from downloaded graph

    extended_stats: list
                    List of extended stats to compute from graph

    connectivity: bool. Default False.
                  Compute node and edge connectivity

    anc: bool. Default False.
         Compute avg node connectivity

    ecc: bool. Default False.
         Compute shortest paths, eccentricity and topological metric

    bc: bool. Default False.
        Compute node betweeness centrality

    cc: bool. Default False.
        Compute node closeness centrality

    For more detail about these parameters, see https://osmnx.readthedocs.io/en/stable/osmnx.html#module-osmnx.stats

    Returns
    -------

    gdf: Input GeoDataFrame with updated columns containing the selected metrics

    Examples
    --------

    >>> hexagons = urbanpy.geom.gen_hexagons(8, lima)
    >>> urbanpy.geom.osmnx_coefficient_computation(hexagons.head(), 'walk', ['circuity_avg'], [])
    On record 1:  There are no nodes within the requested geometry
    On record 3:  There are no nodes within the requested geometry
                hex	| geometry	                                        | circuity_avg
	888e62c64bfffff	| POLYGON ((-76.89763 -12.03869, -76.90194 -12.0... | 1.021441
	888e6212e1fffff	| POLYGON ((-76.75291 -12.19727, -76.75722 -12.2... | NaN
	888e62d333fffff	| POLYGON ((-77.09253 -11.83762, -77.09685 -11.8... | 1.025313
	888e666c2dfffff	| POLYGON ((-76.93109 -11.79031, -76.93540 -11.7... | NaN
	888e62d4b3fffff	| POLYGON ((-76.87935 -12.03688, -76.88366 -12.0... | 1.044654

    '''

    #May be a lengthy download depending on the amount of features
    for index, row in tqdm(gdf.iterrows()):
        try:
            graph = ox.graph_from_polygon(row['geometry'], net_type)
            b_stats = ox.basic_stats(graph)
            ext_stats = ox.extended_stats(graph, connectivity, anc, ecc, bc, cc)

            for stat in basic_stats:
                gdf.loc[index, stat] = b_stats.get(stat)
            for stat in extended_stats:
                gdf.loc[index, stat] = ext_stats.get(stat)
        except Exception as err:
            print(f'On record {index}: ', err)

    return gdf
