import time
import subprocess
import sys
import requests
import googlemaps
import numpy as np
import networkx as nx
import osmnx as ox
import geopandas as gpd
from tqdm.auto import tqdm
from shapely.geometry import Point

__all__ = [
    'start_osrm_server',
    'stop_osrm_server',
    'osrm_route',
    'google_maps_dist_matrix',
    'ors_api',
    'compute_osrm_dist_matrix',
    'google_maps_dir_matrix',
    'nx_route',
    'isochrone_from_api',
    'isochrone_from_graph'
]

CONTAINER_NAME = 'osrm_routing_server'

def check_container_is_running(container_name):
    '''
    Checks if a container is running

    Parameters
    ----------

    container_name: str
        Name of container to check

    Returns
    -------

    container_running: bool
        True if container is running, False otherwise.

    '''
    completed_process = subprocess.run(['docker', 'ps'], check=True, capture_output=True)
    stdout_str = completed_process.stdout.decode('utf-8')
    container_running = container_name in stdout_str

    return container_running

def start_osrm_server(country, continent, profile):
    '''
    Download data for OSRM, process it and start a local osrm server

    Parameters
    ----------

    country: str
             Which country to download data from. Expected in lower case & dashes replace spaces.
             
    continent: str
             Which continent of the given country. Expected in lower case & dashes replace spaces.
             
    profile: str. One of {'foot', 'car', 'bicycle'}
             Travel mode to use when routing and estimating travel time.

    Examples
    --------

    >>> urbanpy.routing.start_osrm_server('peru', 'south-america', 'foot')
    Starting server ...
    Server was started succesfully.

    '''

    container_name = CONTAINER_NAME + f"_{continent}_{country}_{profile}"

    # Download, process and run server command sequence
    dwn_str = f'''
    docker pull osrm/osrm-backend;
    mkdir -p ~/data/osrm/;
    cd ~/data/osrm/;
    wget https://download.geofabrik.de/{continent}/{country}-latest.osm.pbf;
    docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/{profile}.lua /data/{country}-latest.osm.pbf;
    docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/{country}-latest.osm.pbf;
    docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/{country}-latest.osm.pbf;
    docker container rm osrm_extract osrm_partition osrm_customize;
    docker run -t --name {CONTAINER_NAME}_{continent}_{country}_{profile} -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/{country}-latest.osm.pbf;
    '''

    container_running = check_container_is_running(CONTAINER_NAME + f"_{continent}_{country}_{profile}")

    # Check platform
    if sys.platform in ['darwin', 'linux']:
        # Check if container exists:
        if subprocess.run(['docker', 'inspect', CONTAINER_NAME + f"_{continent}_{country}_{profile}"]).returncode == 0:
            if container_running:
                print('Server is already running.')
            else:
                try:
                    print('Starting server ...')
                    subprocess.run(['docker', 'start', container_name], check=True)
                    time.sleep(5) # Wait server to be prepared to receive requests
                    print('Server was started succesfully')
                except subprocess.CalledProcessError as error:
                    print(f'Something went wrong. Please check if port 5000 is being used or check your docker installation.\nError: {error}')

        else:
            try:
                print('This is the first time you used this function.\nInitializing server setup. This may take several minutes...')
                subprocess.Popen(dwn_str, shell=True)

                # Verify container is running
                while container_running == False:
                    container_running = check_container_is_running(container_name)

                print('Server was started succesfully')
                time.sleep(5) # Wait server to be prepared to receive requests

            except subprocess.CalledProcessError as error:
                print(f'Something went wrong. Please check your docker installation.\nError: {error}')

    elif sys.platform == 'win32':
        print('Still working on windows support')
        #subprocess.Popen(dwn_str.replace(';', '&'))

    else:
        print('Platform not supported')

def stop_osrm_server(country, continent, profile):
    '''
    Run docker stop on the server's container.

    Parameters
    ----------

    country: str
             Which country the osrm to stop is routing. Expected in lower case & dashes replace spaces.

    continent: str
             Continent of the given country. Expected in lower case & dashes replace spaces.

    profile: str. One of {'foot', 'car', 'bicycle'}
             Travel mode to use when routing and estimating travel time.

    Examples
    --------

    >>> urbanpy.routing.stop_osrm_server('peru', 'south-america', 'foot')
    Server stopped succesfully

    '''

    container_name = CONTAINER_NAME + f"_{continent}_{country}_{profile}"

    # Check platform
    if sys.platform in ['darwin', 'linux']:
        # Check if container exists:
        if subprocess.run(['docker', 'top', container_name]).returncode == 0:
            if check_container_is_running(container_name) == True:
                try:
                    subprocess.run(['docker', 'stop', container_name], check=True)
                    #subprocess.run(['docker', 'container', 'rm', 'osrm_routing_server'])
                    print('Server was stoped succesfully')
                except subprocess.CalledProcessError as error:
                    print(f'Something went wrong. Please check your docker installation.\nError: {error}')
            else:
                print('Server is not running.')

        else:
            print('Server does not exist.')

    elif sys.platform == 'win32':
        print('Still working on windows support')
        #subprocess.Popen(dwn_str.replace(';', '&'))

    else:
        print('Platform not supported')

def osrm_route(origin, destination):
    '''
    Query an OSRM routing server for routes between an origin and a destination
    using a specified profile.

    Travel mode ("foot", "bicycle", or "car") is determined by the profile
    selected when starting the OSRM server

    Parameters
    ----------

    origin: DataFrame with columns x and y or Point geometry
            Input origin in lat lon pairs (y, x) to pass into the routing engine

    destination: DataFrame with columns x and y or Point geometry
                 Input destination in lat lon pairs (y,x) to pass to the routing engine


    Returns
    -------

    distance: float
              Total travel distance from origin to destination in meters
    duration: float
              Total travel time in minutes

    '''
    orig = f'{origin.x},{origin.y}'
    dest = f'{destination.x},{destination.y}'
    # If "profile" is passed in the url the default profile is used by the local osrm server
    url = f'http://localhost:5000/route/v1/profile/{orig};{dest}'
    response = requests.get(url, params={'overview': 'false'})

    try:
        data = response.json()['routes'][0]
        distance, duration = data['distance'], data['duration']
        return distance, duration
    except Exception as err:
        #print(err)
        return np.nan, np.nan

def google_maps_dist_matrix(origin, destination, mode, api_key, **kwargs):
    '''
    Google Maps distance matrix support.

    Parameters
    ----------

    origin: tuple, list or str
            Origin for distance calculation. If tuple or list, a matrix for all
            lat-lon pairs will be computed (origin as rows). If str, google_maps
            will georeference and then compute.

    destination: tuple, list or str
                 Origin for distance calculation. If tuple or list, a matrix for all
                 lat-lon pairs will be computed (origin as rows). If str, google_maps
                 will georeference and then compute.

    mode: str. One of {"driving", "walking", "transit", "bicycling"}
          Mode for travel time calculation

    api_key: str
             Google Maps API key

    **kwargs
        Additional keyword arguments for the distance matrix API. See
        https://github.com/googlemaps/google-maps-services-python/blob/master/googlemaps/distance_matrix.py

    Returns
    -------

    dist: int
          Distance for the o/d pair. Depends on metric parameter

    time: int
          Travel time duration

    Examples
    --------

    >>> API_KEY = 'example-key'
    >>> urbanpy.routing.google_maps_dist_matrix('San Juan de Lurigancho', 'Miraflores', 'walking', API_KEY)
        (18477, 13494)
    >>> urbanpy.routing.google_maps_dist_matrix((-12,-77), (-12.01,-77.01), 'walking', API_KEY)
        (2428, 1838)
    >>> urbanpy.routing.google_maps_dist_matrix([(-12,-77),(-12.11,-77.01)], [(-12.11,-77.01),(-12,-77)], 'walking', API_KEY)
        ([[13743, 0], [0, 13720]], [[10232, 0], [0, 10674]])

    '''

    client = googlemaps.Client(key=api_key)

    try:
        r = client.distance_matrix(origin, destination, mode=mode, **kwargs)

        rows = r['rows']

        dist, dur = [], []

        if len(rows) > 1:
            for row in rows:
                dist.append([element['distance']['value'] for element in row['elements']])
                dur.append([element['duration']['value'] for element in row['elements']])
        else:
            dist = r["rows"][0]["elements"][0]["distance"]["value"]
            dur = r["rows"][0]["elements"][0]["duration"]["value"]
    except Exception as err:
        print(err)
        dist = None
        dur = None

    return dist, dur

def ors_api(locations, origin, destination, profile, metrics, api_key):
    '''
    Interface with OpenRoute Service API for distance matrix computation.

    Parameters
    ----------

    origin: list
            Input origin(s) indices in the location array to compute travel times and distances

    destination: list
            Input destination(s) indices in the location array to compute travel times and distances

    profile: str. One of {'driving-car', 'foot-walking', 'cycling-regular'}

    metrics: list
             Combination of metrics to compute (distance and travel time, or one of them)

    api_key: str
             Authorization API key for OpenRouteService (see API limits)

    Returns
    -------

    dist: list
           Distance matrix

    dur: list
          Travel time matrix

    Examples
    --------

    >>> locations = [[9.70093,48.477473],[9.207916,49.153868],[37.573242,55.801281],[115.663757,38.106467]]
    >>> metrics = ["distance","duration"]
    >>> sources = [0]
    >>> destinations = [1,2,3]
    >>> api_key = ...
    >>> urbanpy.routing.ors_api(locations, sources, destinations, metrics, 'driving-car', api_key)
    [[5753.86,88998.08,399003.44]]
    [[140861.31,2434228.75,1.0262603E7]]

    '''

    body = {
        "locations": locations,
        "sources": origin,
        "destinations": destination,
        "metrics": metrics
        }

    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': api_key,
        'Content-Type': 'application/json; charset=utf-8'
    }

    r = requests.post(f'https://api.openrouteservice.org/v2/matrix/{profile}', json=body, headers=headers)

    if r.status_code == 200:
        result = r.json()
        return result['distances'], result['durations']
    else:
        return -1, -1

def compute_osrm_dist_matrix(origins, destinations):
    '''
    Compute distance and travel time origin-destination matrices

    Parameters
    ----------

    origins: GeoDataFrame or GeoSeries
             Input Point geometries corresponding to the starting points of a route.

    destinations: GeoDataFrame or GeoSeries
                  Point geometries corresponding to the end points of a route.

    Returns
    -------

    dist_matrix: array_like
                 Array with origins as rows and destinations as columns. Distance in meters.

    dur_matrix: array_like
                Array with origins as rows and destinations as columns. Duration in minutes.

    Examples
    --------

    >>> hex = urbanpy.geom.gen_hexagons(8, lima)
    >>> fs = urbanpy.download.overpass_pois(hex.total_bounds, 'food_supply')
    >>> urbanpy.routing.start_osrm_server('peru', 'south-america')
    >>> dist, dur = urbanpy.routing.compute_osrm_dist_matrix(points.head(), fs.head(), 'walking')
    array([[ 82012.4,  93899.9,  88964.6, 111839.8,  87844. ],
       [ 26346.3,  23725.6,  19618.9,  38607.9,  22725.6],
       [ 26504.4,  23883.7,  19777. ,  38766. ,  22883.7],
       [ 33314.3,  30693.6,  26586.9,  45575.9,  29693.5],
       [ 26659.3,  24038.7,  19931.9,  38920.9,  23038.6]])
    array([[59093.7, 67666.8, 64123.1, 80592.8, 63331.5],
       [19027.5, 17094.6, 14152.3, 27797.6, 16402.8],
       [19141.5, 17208.6, 14266.3, 27911.6, 16516.8],
       [24044.9, 22112. , 19169.7, 32815. , 21420.2],
       [19253.1, 17320.2, 14377.9, 28023.2, 16628.4]])

    '''

    dist_matrix = np.zeros_like([], shape=(origins.shape[0], destinations.shape[0]))
    dur_matrix = np.zeros_like([], shape=(origins.shape[0], destinations.shape[0]))

    if type(origins) == gpd.GeoSeries:
        origins = origins.to_frame()

    if type(destinations) == gpd.GeoSeries:
        destinations = destinations.to_frame()

    for ix, row in tqdm(origins.iterrows(), total=origins.shape[0]):
        for i, r in tqdm(destinations.iterrows(), total=destinations.shape[0]):
            dist, dur = osrm_route(row.geometry, r.geometry)
            dist_matrix[ix, i] = dist
            dur_matrix[ix, i] = dur

    return dist_matrix, dur_matrix

def google_maps_dir_matrix(origin, destination, mode, api_key, **kwargs):
    '''
    Google Maps distance matrix support.

    Parameters
    ----------

    origin: tuple, list or str
            Origin for distance calculation. If tuple or list, a matrix for all
            lat-lon pairs will be computed (origin as rows). If str, google_maps
            will georeference and then compute.

    destination: tuple, list or str
                 Origin for distance calculation. If tuple or list, a matrix for all
                 lat-lon pairs will be computed (origin as rows). If str, google_maps
                 will georeference and then compute.

    mode: str. One of {"driving", "walking", "transit", "bicycling"}
          Mode for travel time calculation

    api_key: str
             Google Maps API key

    **kwargs
        Additional keyword arguments for the distance matrix API. See
        https://github.com/googlemaps/google-maps-services-python/blob/master/googlemaps/directions.py

    Returns
    -------

    dist: int
          Distance for the o/d pair. Depends on metric parameter

    dur: int
          Travel time duration, depends on units kwargs

    Examples
    --------

    >>> API_KEY = 'example-key'
    >>> urbanpy.routing.google_maps_dir_matrix('San Juan de Lurigancho', 'Miraflores', 'walking', API_KEY)
        (18477, 13494)

    '''

    client = googlemaps.Client(key=api_key)

    try:
        r = client.directions(origin, destination, mode=mode, **kwargs)

        legs = r[0]['legs']

        dist, dur = 0, 0

        if len(legs) > 1:
            for leg in legs:
                dist += leg['distance']['value']
                dur += leg['duration']['value']
        else:
            dist = legs[0]['distance']['value']
            dur = legs[0]['duration']['value']

    except Exception as err:
        print(err)
        dist = None
        dur = None

    return dist, dur

def nx_route(graph, source, target, weight, length=True):
    '''
    Compute shortest path from a source and target node.

    Parameters
    ----------

    graph: NetworkX Graph
           Input graph from which to calculate paths

    source: str or int
            ID of the source node from which to calculate path. Depending on the graph,
            this may be a string or integer or a combination of both as tuples.

    target: str or int
            ID of the target node. Type corresponds to node id types in the input graph.

    weight: str
            Attribute to be used as weights in the path. If None returns the sequence of nodes
            or the number of nodes to travel as length.

    length: bool
            Flag for whether to calculate the path lenght or the sequence of nodes to follow.
            If weight is none and length is true, the number of nodes in the path will be returned.

    Returns
    -------

    path: list
          Sequence of node ids in a list.

    path_length: float or int
                 Length of the path according to the weight attribute.

    Examples
    --------

    >>> import osmnx as ox
    >>> import urbanpy as up
    >>> from random import choices
    >>> G = ox.graph_from_place('Lima, Peru')
    >>> source, target = choices(list(G.nodes), k=2)
    >>> up.routing.nx_route(G, source, target, 'length')
    8348.236999999996

    '''
    if length:
        try:
            path_length = nx.shortest_path_length(graph,
                         source,
                         target,
                         weight=weight)
            return path_length
        except:
            #If there is no path within the graph
            return -1
    else:
        try:
            path = nx.shortest_path(graph,
                         source,
                         target,
                         weight=weight)
            return path
        except:
            #If there is no path within the graph
            return -1

def isochrone_from_api(locations, time_range, profile, api, api_key):
    '''
    Get isochrones from either the OpenRouteService or MapBox API

    Parameters
    ----------

    locations: array_like (float, float)
               Set of locations from which to calculate the isochrones in lon, lat pairs.
               Larger sets may exceed API limits.

    time_range: array_like (int)
                Time intervals to compute i.e. the travel time ranges for the
                isochrones. Depends on the API

    profile: str. Depends on the API.
             Mobility profile to compute the isochrones

    api: str. One of {"ors", "mapbox"}
         API to request the isochrones from.

    api_key: str
             API auth key

    Returns
    -------

    isochrones: GeoDataFrame
                GeoPandas GeoDataFrame containing the isochrone polygons with columns:
                contour (time range), group index (isochrone-location matcher) and geometry

    Examples
    --------

    >>> import urbanpy as up
    >>> API_KEY = "some_key"
    >>> up.routing.isochrone_from_api([[8.681495,49.41461],[8.686507,49.41943]], [300,900], 'foot-walking', 'ors', API_KEY)
     contour |  group_index |                                           geometry
       300.0 |           0  | POLYGON ((8.67640 49.41485, 8.67643 49.41461, ...
       900.0 |           0  | POLYGON ((8.66750 49.41169, 8.66755 49.41164, ...
       300.0 |           1  | POLYGON ((8.68103 49.41902, 8.68167 49.41815, ...
       900.0 |           1  | POLYGON ((8.67108 49.41982, 8.67109 49.41946, ...
    >>> up.routing.isochrone_from_api([[8.681495,49.41461],[8.686507,49.41943]], [5,10], 'driving', 'mapbox', API_KEY)
    contour | group_index |                                            geometry
       10   |         0   | POLYGON ((8.68149 49.43661, 8.68100 49.43461, ...
        5   |         0   | POLYGON ((8.67850 49.42361, 8.67621 49.42190, ...
       10   |         1   | POLYGON ((8.67258 49.44751, 8.67138 49.44743, ...
        5   |         1   | POLYGON ((8.68265 49.42957, 8.68151 49.42846, ...

    '''

    if api == 'ors':
        body = {
            "locations": locations,
            "range": time_range
        }

        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': api_key,
            'Content-Type': 'application/json; charset=utf-8'
        }

        call = requests.post(f'https://api.openrouteservice.org/v2/isochrones/{profile}', json=body, headers=headers)

        if call.status_code == 200:
            isochrones = gpd.GeoDataFrame.from_features(call.json())
            isochrones.crs = 'EPSG:4326'
            isochrones.rename(columns={'value': 'contour'}, inplace=True)
            return isochrones[['contour', 'group_index', 'geometry']]
        else:
            print(f'Request error with HTTP code {call.status_code}: {call.reason}')

    else:
        contour_min = ','.join([str(time) for time in time_range])
        features = {}
        #There may be a better solution. Mapbox does not support multiple points in one go
        for ix, (lon, lat) in enumerate(locations):
            pair = ','.join([str(lon), str(lat)])
            url = f'https://api.mapbox.com/isochrone/v1/mapbox/{profile}/{pair}?contours_minutes={contour_min}&polygons=true&access_token={api_key}'
            call = requests.get(url)
            if call.status_code == 200:
                if features == {}:
                    features_ = call.json()
                    #Assing a group index for the request number (id for the location-contour match)
                    for feature in features_['features']:
                        feature['properties']['group_index'] = ix
                    features = features_
                else:
                    features_ = call.json()['features']
                    for feature in features_:
                        feature['properties']['group_index'] = ix
                    features['features'].extend(features_)
            else:
                pass

        isochrones = gpd.GeoDataFrame.from_features(features)
        isochrones.crs = 'EPSG:4326'

        return isochrones[['contour', 'group_index', 'geometry']]

def isochrone_from_graph(graph, locations, time_range, profile):
    '''
    Create isochrones from a network graph.

    Parameters
    ----------

    graph: NetworkX or OSMnx graph.
        Input graph to compute isochrones from.

    locations: array_like
        Locations (lon, lat) from which to trace the isochrones.

    time_range: int
        Travel time from which to construct the isochrones

    profile: str or int
        If str,  a default avg. speed will be used to compute the travel time.
        If int, this value will be used as the avg. speed to compute the isochrones.

    Returns
    -------

    isochrones: GeoDataFrame
                GeoDataFrame containing the isochrones for the set of locations and time_ranges.

    Examples
    --------

    >>> import urbanpy as up
    >>> import osmnx as ox
    >>> G = ox.graph_from_place('Berkeley, CA, USA', network_type='walking')
    >>> up.routing.isochrone_from_graph(G, [[],[]], [5, 10], 'walking')


    '''

    profiles = {
        'driving': 20,
        'walking': 5,
        'cycling': 10,
    }

    if profile not in profiles and type(profile) == int:
        travel_speed = profile
    else:
        travel_speed = profiles[profile]

    center_nodes = [ox.get_nearest_node(graph, (y, x)) for x, y in locations]
    G = ox.project_graph(graph)

    meters_per_minute = travel_speed * 1000 / 60 #km per hour to m per minute
    for u, v, k, data in G.edges(data=True, keys=True):
        data['time'] = data['length'] / meters_per_minute

    data = []

    for ix, center_node in enumerate(center_nodes):
        for trip_time in sorted(time_range, reverse=True):
            subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance='time')
            node_points = [Point((data['x'], data['y'])) for node, data in subgraph.nodes(data=True)]
            bounding_poly = gpd.GeoSeries(node_points).unary_union.convex_hull
            data.append([ix, trip_time, bounding_poly])

    isochrones = gpd.GeoDataFrame(data, columns=['group_index', 'contour', 'geometry'])
    isochrones.crs = 'EPSG:32718'

    return isochrones
