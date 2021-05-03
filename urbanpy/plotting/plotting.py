# import pydeck as pdk
import pandas as pd
import plotly.express as px
# import matplotlib.pyplot as plt
# from urbanpy.utils import tuples_to_lists

__all__ = [
    # 'pydeck_df',
    # 'gen_pydeck_layer',
    'choropleth_map',
]


# def gen_pydeck_layer(layer_type, data, **kwargs):
#     if layer_type == 'H3HexagonLayer':
#         return pdk.Layer("H3HexagonLayer", data, **kwargs)
#     else:
#         return pdk.Layer('PolygonLayer', data, **kwargs)

def choropleth_map(gdf, color_column, df_filter=None, **kwargs):
    '''
    Produce a Choroplethmap using plotly by passing a GeoDataFrame.

    Parameters
    ----------

    gdf: GeoDataFrame
             Input data containing a geometry column and features

    color_column: str
                      Column from gdf to use as color


    df_filter: pd.Series, default to None
                   Pandas Series containing true/false values that satisfy a
                   condition (e.g. (df['population'] > 100))

    **kargs: Any parameter of plotly.px.choroplethmapbox.

    Examples
    --------

    >>> hex_lima = urbanpy.geom.gen_hexagons(8, lima)
    >>> hex_lima['pop_2020'] = population_2020
    >>> urbanpy.plotting.choropleth_map(hex_lima, 'pop_2020', [-12, -77])

    '''


    if df_filter is not None:
        gdff = gdf[df_filter].copy()
    else:
        gdff = gdf.copy()

    gdff = gdff.reset_index()[['index', color_column, 'geometry']].dropna()
    lon, lat = gdff.geometry.unary_union.centroid.xy

    fig = px.choropleth_mapbox(gdff, geojson=gdff[['geometry']].__geo_interface__,
                               color=color_column, locations="index",
                               center={"lat": lat[0], "lon": lon[0]},
                               mapbox_style="carto-positron", **kwargs)
    return fig

# def pydeck_df(gdf, features, cmap, bins, color_feature):
#     '''
#     Prepare a DataFrame for Polygon plotting in PyDeck
#
#     Parameters
#     ----------
#
#     gdf : GeoDataFrame with the geometries to plot
#
#     features : list
#                   List of features to add to the polygon df
#
#     cmap : str
#               Matplotlib colormap to use for plotting
#
#     bins : list
#               Bins to aggregate data into
#
#     color_feature : str
#                        Column name for data to transform into bins and color features
#
#     Returns
#     -------
#
#     polygon_df : DataFrame
#                     df with the coordinates in a list as a column and the selected features
#
#     '''
#
#     cmap = plt.get_cmap(name='magma')
#     json = gdf.__geo_interface__
#
#     json_ = tuples_to_lists(json)
#
#     del json_['bbox']
#
#     df = pd.DataFrame.from_dict(json_)
#
#     polygon_df = pd.DataFrame()
#     polygon_df['coordinates'] = df['features'].apply(lambda row: row['geometry']['coordinates'])
#
#     for feature in features:
#         polygon_df[feature] = df['features'].apply(lambda row: row['properties'][feature])
#
#     polygon_df['bins'] = pd.cut(
#         polygon_df[color_feature],
#         bins = bins
#     )
#
#     bins_labels = polygon_df['bins'].unique().categories.values
#     bins_replace = {label: i  for i, label in enumerate(bins_labels)}
#     polygon_df['count'] = polygon_df['bins'].replace(bins_replace)
#
#     cmap_ixs = [int(round(255 / (i+1))) for i in polygon_df['count'].fillna(0).values]
#     rgb_values = [[color * 255 for color in cmap.colors[cmap_ix]] for cmap_ix in cmap_ixs]
#     rgb_count_df = pd.DataFrame(rgb_values, columns=['r','g','b'])
#
#     polygon_df = pd.concat((polygon_df, rgb_count_df), axis=1)
#
#     polygon_df['r'] = polygon_df['r'].round(0)
#     polygon_df['g'] = polygon_df['g'].round(0)
#     polygon_df['b'] = polygon_df['b'].round(0)
#
#     return polygon_df
