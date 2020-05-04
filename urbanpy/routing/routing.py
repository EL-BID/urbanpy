import subprocess
import requests

__all__ = [
    'setup_osrm_server',
    'stop_osrm_server',
    'osrm_routes',
]

def setup_osrm_server(country):
    '''
    Download data for OSRM, process it and

    Parameters
    ----------

    country : str
             Which country to download data from. Expected in lower case
    dir : str
         Directory in which to save the file. Defaults to ../data/osrm/

    '''

    subprocess.Popen(['bash', '../../bin/pull_osrm.sh', f'{country}-latest.osm.pbf'])

def stop_osrm_server():
    '''
    Run docker stop on the server's container.
    '''

    subprocess.run(['docker', 'stop', 'osrm_routing_server'])

def osrm_routes(origin, destination, profile):
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
