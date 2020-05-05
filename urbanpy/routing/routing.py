import subprocess
import requests
import googlemaps
import sys
import numpy as np
from tqdm import tqdm

__all__ = [
    'setup_osrm_server',
    'stop_osrm_server',
    'osrm_routes',
    'google_maps_dist_matrix',
    'ors_api'
]

def setup_osrm_server(country, downloaded=False):
    '''
    Download data for OSRM, process it and

    Parameters
    ----------

    country : str
             Which country to download data from. Expected in lower case
    downloaded : bool
                 Boolean to decide if data needs to be downloaded and processed,
                 or just a container run is needed.

    '''

    #Download, process and run server command sequence
    dwn_str = f'''
    docker pull osrm/osrm-backend;
    mkdir -p ~/data/osrm/;
    cd ~/data/osrm/;
    wget https://download.geofabrik.de/south-america/{country}-latest.osm.pbf;
    docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/{country}-latest.osm.pbf;
    docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/{country}-latest.osm.pbf;
    docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/{country}-latest.osm.pbf;
    docker container rm osrm_extract osrm_partition osrm_customize;
    docker run -t --name osrm_routing_server -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/{country}-latest.osm.pbf;
    '''

    non_dwn_str = f'''
    cd ~/data/osrm/;
    docker run -t --name osrm_routing_server -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/{country}-latest.osm.pbf;
    '''


    if not downloaded:
        if sys.platform in ['darwin', 'linux']:
            subprocess.Popen(dwn_str, shell=True)
        elif sys.platform == 'win32':
            print('Still working on windows support')
            #subprocess.Popen(dwn_str.replace(';', '&'))
        else:
            print('Platform not supported')
    else:
      if sys.platform in ['darwin', 'linux']:
          subprocess.Popen(non_dwn_str, shell=True)
      elif sys.platform == 'win32':
          print('Still working on windows support')
          #subprocess.Popen(non_dwn_str.replace(';', '&'))
      else:
          print('Platform not supported')


def stop_osrm_server():
    '''
    Run docker stop on the server's container.
    '''

    subprocess.run(['docker', 'stop', 'osrm_routing_server'])
    subprocess.run(['docker', 'container', 'rm', 'osrm_routing_server'])

def osrm_route(origin, destination, profile):
    '''
    Query an OSRM routing server for routes between an origin and a destination
    using a specified profile.

    Parameters
    ----------

    origin : DataFrame with columns x and y or Point geometry
                Input origin in lat lon pairs (y, x) to pass into the routing engine

    destination : DataFrame with columns x and y or Point geometry
                     Input destination in lat lon pairs (y,x) to pass to the routing engine

    profile : str. One of {'foot', 'car', 'bicycle'}
                 Behavior to use when routing and estimating travel time.

    Returns
    -------

    distance : float
                  Total travel distance from origin to destination in meters
    duration : float
                  Total travel time in minutes

    '''

    try:
        orig = f'{origin.x},{origin.y}'
        dest = f'{destination.x},{destination.y}'
        url = f'http://localhost:5000/route/v1/{profile}/{orig};{dest}' # Local osrm server
        response = requests.get(url, params={'overview': 'false'})
        data = response.json()['routes'][0]
        distance, duration = data['distance'], data['duration']
        return distance, duration
    except Exception as err:
        print(err)
        print(response.reason)
        print(response.url)
        pass

def google_maps_dist_matrix(origin, destination, mode, api_key, **kwargs):
    '''
    Google Maps distance matrix support.

    Parameters
    ----------

    origin : tuple, list or str
            Origin for distance calculation. If tuple or list, a matrix for all
            lat-lon pairs will be computed (origin as rows). If str, google_maps
            will georeference and then compute.

    destination : tuple, list or str
                 Origin for distance calculation. If tuple or list, a matrix for all
                 lat-lon pairs will be computed (origin as rows). If str, google_maps
                 will georeference and then compute.

    mode : str. One of {"driving", "walking", "transit", "bicycling"}
          Mode for travel time calculation

    api_key : str
              Google Maps API key

    **kwargs
        Additional keyword arguments for the distance matrix API. See
        https://github.com/googlemaps/google-maps-services-python/blob/master/googlemaps/distance_matrix.py

    Returns
    -------

    dist : int
           Distance for the o/d pair. Depends on metric parameter

    time : int
           Travel time duration

    Examples
    --------

    See also
    --------



    '''

    client = googlemaps.Client(key=api_key)

    try:
        r = client.distance_matrix(origin, destination, mode=mode, **kwargs)
        dist = r["rows"][0]["elements"][0]["distance"]["value"]
        time = r["rows"][0]["elements"][0]["duration"]["value"]
    except Exception as err:
        print('')
        dist = None
        time = None

    return dist, time

def ors_api(locations, origin, destination, profile, metrics, api_key):
    '''
    Interface with OpenRoute Service API for distance matrix computation.

    Parameters
    ----------

    origin : list
            Input origin(s) indices in the location array to compute travel times and distances

    destination : list
                 Input destination(s) indices in the location array to compute travel times and distances

    profile : str. One of {'driving-car', 'foot-walking', 'cycling-regular'}

    metrics: list
             Combination of metrics to compute (distance and travel time, or one of them)

    api_key : str
             Authorization API key for OpenRouteService (see API limits)

    Returns
    -------

    dist : list
           Distance matrix

    dur : list
          Travel time matrix

    Examples
    --------

    import requests

    >>> locations = [[9.70093,48.477473],[9.207916,49.153868],[37.573242,55.801281],[115.663757,38.106467]]
    >>> metrics = ["distance","duration"]
    >>> sources = [0]
    >>> destinations = [1,2,3]
    >>> api_key = ...
    >>> up.routing.ors_api(locations, sources, destinations, metrics, 'driving-car', api_key)
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

@jit
def compute_osrm_dist_matrix(origins, destinations, profile):
    '''
    Compute distance and travel time origin-destination matrices

    Parameters
    ----------

    origins : GeoDataFrame
              Input Point geometries corresponding to the starting points of a route.

    destinations : GeoDataFrame
                   Point geometries corresponding to the end points of a route.

    Returns
    -------

    dist_matrix : array_like
                  Array with origins as rows and destinations as columns. Distance in meters.

    dur_matrix : array_like
                 Array with origins as rows and destinations as columns. Duration in minutes.

    Examples
    --------

    >>> hex, centroids = gen_hexagons(8, lima)
    >>> fs = download_overpass_poi(hex.total_bounds, 'food_supply')
    >>> setup_osrm_server('peru', True)
    >>> dist, dur = compute_osrm_dist_matrix(points.head(), fs.head(), 'walking')
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
    
    dist_matrix = []
    dur_matrix = []

    for ix, row in tqdm(origins.iterrows()):
        dist_row = []
        dur_row = []
        for i, r in destinations.iterrows():
            dist, dur = osrm_route(row.geometry, r.geometry, profile)
            dist_row.append(dist)
            dur_row.append(dur)
        dist_matrix.append(dist_row)
        dur_matrix.append(dur_row)

    return np.array(dist_matrix), np.array(dur_matrix)
