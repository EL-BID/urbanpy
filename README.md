# urbanpy
A library to download, process and visualize high resolution urban data.

### Datasources

* OpenStreetMaps
* HDX
* Overpass API

### Dependencies

* pandas
* geopandas
* shapely
* numpy
* requests
* h3
* numba
* matplotlib

It is important to note that for travel time computation, if needed, a method
is implements the Open Source Routing Machine (OSRM). This method pulls, extracts and
add graph weights to the downloaded network and runs the routing server. Make sure
to have docker installed for the library to work correctly. Urbanpy provides a
simple approximation with nearest neighbor search using a
BallTree and haversine distance, but the difference between
real travel time and the approximation may vary from city to city. <br>

Additionally, the use of spatial libraries like osmnx, geopandas and h3 require certain extra packages.
Specifically, for rtree (spatial indexing to allow spatial joins) libspatialindex is required.
OSMnx and Geopandas requiere GDAL as well. If not handled by installing geopandas's dependencies, installing
fiona, pyproj and shapely should satisfy the requirements.
H3 requires cc, make, and cmake in your $PATH when installing, otherwise installation will not be successful

To install, use

pip install urbanpy
