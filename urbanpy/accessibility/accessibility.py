import geopandas as gpd
import pandas as pd
import numpy as np
from osmnx import project_gdf
from tqdm.auto import tqdm

__all__ = [
    'pressure_map',
    'hu_access_map',
]

#Gaussian friction function for distance decay
def friction(dm, d0):
    if dm > d0:
        return 0
    else:
        return np.exp(-0.5 * (dm/d0)**2) / (1 - np.exp(-0.5))


def hu_access_map(units, pois, population_column, weight=1, d0=1250):
    '''
    Create accessibility surface from Hu et al. 2019. The authors provide an accessibility to healthy foods indicator that contemplates both the catchment area of a store and the access from a city block/district/county (denoted as E2SFCA).

    Parameters
    ----------
    units: GeoDataFrame
        Input spatial units to calculate access.

    pois: GeoDataFrame
        Input points of interest for access calculations

    population_column: str
        Key for population values in each spatial unit

    weight: int
        Weight for final indicator computation. Defaults to 1

    d0: int
        Buffer size. Defaults to 1250


    Returns
    -------
    access_map: GeoDataFrame
        Input unit dataframe with accessibility values.

    Examples
    --------
    >>> surface = urbanpy.accessibility.hu_access_map(blocks, pois, 'pop_2020')
    >>> surface.head()
    geometry	 | place_id	 | osm_type	| osm_id     | display_name	| place_rank  |  category | type	       | importance	| icon
    MULTIPOLYGON | 235480647 | relation	| 1944670.0  | Lima, Peru	| 12	      |  boundary |	administrative | 0.703484	| https://nominatim.openstreetmap.org/images/map...

    References
    ----------

    Hu, L., Zhao, C., Wang, M., Su, S., Weng, M., & Wang, W. (2020). Dynamic healthy food accessibility in a rapidly urbanizing metropolitan area: socioeconomic inequality and relative contribution of local factors. Cities, 105, 102819.

    '''

    #Setup
    tqdm.pandas()

    #Check if input POIs and units are on EPSG:32718. If False, reproject
    if units.crs.to_string() != 'EPSG:32718':
        units = units.to_crs(epsg=32718)

    if pois.crs.to_string() != 'EPSG:32718':
        pois = pois.to_crs(epsg=32718)

    #Create indices for join handling
    units['idx'] = 'unit_' + units.index.astype(str)
    pois['idx'] = 'POI_' + pois.index.astype(str)

    #Create buffers
    units['buffer'] = units.geometry.buffer(d0)
    pois['buffer'] = pois.geometry.buffer(d0)

    #Calculate block centroids
    units['centroid'] = units.geometry.centroid

    #Create buffer GeoDataFrame
    buffers_poi = gpd.GeoDataFrame(pois['idx'], geometry=pois['buffer'])
    buffers_units = gpd.GeoDataFrame(units['idx'], geometry=units['buffer'])

    #Compute catchment area (Rj) for each poi
    join = gpd.sjoin(buffers_poi, units[['idx', 'geometry']], op='intersects', how='left')
    join = join.rename(columns={'idx_left': 'idx_poi', 'idx_right': 'idx_unit'})
    merge = pd.merge(join, units[['idx', 'centroid', population_column]], how='left', left_on='idx_unit', right_on='idx')

    #Calculate buffer centroids
    merge['poi_geom'] = merge['geometry'].centroid
    merge = merge[~merge['centroid'].isna() | ~merge['centroid'].isnull()]

    #Compute friction
    merge['friction'] = merge.progress_apply(lambda r: friction(r['poi_geom'].distance(r['centroid']), d0), axis=1)

    #Remove 0 population values
    merge = merge[merge[population_column] > 0]

    #Compute Rj
    merge['Rj'] = merge['friction'] * merge[population_column]

    #Aggregate into a single df
    df_rj = merge.groupby('idx_poi').agg({'Rj': sum}).reset_index()

    #Complete rj values
    df_rj['Rj'] = weight/df_rj['Rj']

    #Compute block accesibility
    join = gpd.sjoin(buffers_units, pois[['idx', 'geometry']], op='intersects', how='left')
    join = join.rename(columns={'idx_left': 'idx_unit', 'idx_right':'idx_poi'})

    #Merge with POI data
    merge = pd.merge(join, df_rj, how='left')
    merge = pd.merge(merge, pois[['idx', 'geometry']], how='left', left_on='idx_poi', right_on='idx')
    merge['centroid'] = merge['geometry_x'].centroid

    #Eliminate null geometries
    merge = merge[~merge['geometry_y'].isna() | ~merge['geometry_y'].isnull()]

    #Compute friction
    merge['friction'] = merge.progress_apply(lambda r: friction(r['centroid'].distance(r['geometry_y']), d0), axis=1)

    #Compute accesibility Ai
    df_ai = merge[['idx_unit', 'idx_poi', 'friction', 'Rj']]
    df_ai = pd.merge(df_ai, units[['idx', population_column]], how='left', left_on='idx_unit', right_on='idx')
    df_ai = df_ai[df_ai[population_column] > 0]

    df_ai['Ai'] = df_ai['friction'] * df_ai['Rj']
    df_ai = df_ai.groupby('idx_unit').agg({'Ai': sum})

    df_ai = pd.merge(df_ai, units[['idx', population_column, 'geometry']], how='left', left_on='idx_unit', right_on='idx')

    del df_ai['idx']

    access_map = gpd.GeoDataFrame(df_ai, geometry=df_ai['geometry'])

    return access_map

def pressure_map(blocks, pois, demand_column, operation='intersects', buffer_size=1250):
    '''
    Create the unaggregated pressure map from Ritsema van Eck & de Jong, 1999.

    Parameters
    ----------
    blocks: GeoDataFrame
        Input spatial units to calculate pressure. As per the paper these are city blocks.

    pois: GeoDataFrame
        Input points of interest for pressure calculations

    demand_column: str
                   Key for demand values in each spatial unit.

    operation: str
               Spatial operation to use. One of the operations supported by GeoPandas

    buffer_size: int
                 Buffer size. Defaults to 1250


    Returns
    -------
    blocks: GeoDataFrame
            Input blocks dataframe with pressure values (ds). Unaggregated, if grouped into a higher resolution, sum 'ds'.

    Examples
    --------
    >>> surface = urbanpy.accessibility.pressure_map(blocks, pois, 'pop_2020')
    >>> surface.head()
    POB16  | ds        |    geometry
	69	   | 0.784091  |	POLYGON ((301151.794 8670216.675, 301167.165 8...
	84	   | 0.617647  |	POLYGON ((282595.509 8677560.543, 282627.393 8...
	117	   | 2.785714  |	POLYGON ((279276.449 8681335.243, 279323.599 8...
	41	   | 20.500000 |    POLYGON ((313155.536 8677088.663, 313180.700 8...
	59	   | 1.404762  |	POLYGON ((280125.735 8684068.209, 280098.318 8..


    References
    ----------

    Van Eck, J. R., & de Jong, T. (1999). Accessibility analysis and spatial competition effects in the context of GIS-supported service location planning. Computers, environment and urban systems, 23(2), 75-89.

    '''

    if not pois.crs.is_projected:
        pois_proj = project_gdf(pois)

    if not blocks.crs.is_projected:
        blocks_proj = project_gdf(blocks)

    idx_blocks = [f'block_{i}' for i in blocks.index]
    blocks_proj['idx'] = idx_blocks

    buffers = gpd.GeoDataFrame(idx_blocks, columns=['idx'], geometry=blocks_proj.geometry.buffer(buffer_size))

    merge = gpd.sjoin(buffers, pois_proj, op=operation)
    nj = merge.groupby('idx').count()['index_right']
    nj.name = 'nj'
    nj = nj.reset_index()

    blocks = pd.merge(blocks, nj, how='left')
    blocks['ds'] = blocks[demand_column] / (blocks_proj['nj'] + 1)

    return blocks
