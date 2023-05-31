import sys

sys.path.append("..")
import urbanpy as up
import geopandas as gpd
import numpy as np

lima = up.download.download_osm(2, "Lima, Peru")

callao = up.download.download_osm(1, "Callao, Peru")

lima_ = up.geom.merge_geom_downloads([lima, callao])

pop_lima = up.download.download_hdx(
    "4e74db39-87f1-4383-9255-eaf8ebceb0c9/resource/317f1c39-8417-4bde-a076-99bd37feefce/download/population_per_2018-10-01.csv.zip"
)

pop_lima = up.geom.filter_population(pop_lima, lima_)

hex_lima, hex_lima_centroids = up.geom.gen_hexagons(8, lima_)

hex_lima = up.geom.merge_shape_hex(
    hex_lima, pop_lima, how="inner", op="intersects", agg={"population_2020": "sum"}
)

hex_lima["longitude"] = hex_lima.geometry.centroid.x
hex_lima["latitude"] = hex_lima.geometry.centroid.y

hex_lima_ = up.geom.remove_features(hex_lima, [-12.2, -12, -77.201, -77.17])

hex_lima_ = hex_lima_[hex_lima_["longitude"] > -77.2]

lima_.bounds

minx, miny, maxx, maxy = (
    hex_lima_.bounds["minx"].min(),
    hex_lima_.bounds["miny"].min(),
    hex_lima_.bounds["maxx"].max(),
    hex_lima_.bounds["maxy"].max(),
)

fs = up.download.download_overpass_poi([minx, miny, maxx, maxy], "food_supply")

centroids = hex_lima_.geometry.centroid

centroids = gpd.GeoDataFrame(centroids, columns=["geometry"])

dist, dur = up.routing.compute_osrm_dist_matrix(centroids, fs, "walking")

np.save("duration_matrix.npy", dur)
np.save("distance_matrix.npy", dist)
