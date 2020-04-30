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
is implementes the Open Source Routing Machine (OSRM). To run OSRM you need to pull
[this docker container](https://hub.docker.com/r/osrm/osrm-backend/) and setup the
server with your city's graph. Urbanpy provides a simple approximation with nearest
neighbor search using a BallTree and haversine distance, but the difference between
real travel time and the approximation may vary from city to city.

To install, use

pip install urbanpy
