import time
import sys
import requests
import subprocess

CONTAINER_NAME = "osrm_routing_server"


class RoutingServer(object):
    def __init__(self, country, continent):
        self.country = country
        self.continent = continent
        self.url = "http://localhost:5000/route/v1/{profile}/{orig};{dest}"

    def __enter__(self):
        self.start_osrm_server(self.country, self.continent)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.stop_osrm_server(self.country, self.continent)

    def start_osrm_server(self, country, continent):
        """
        Download data for OSRM, process it and start local osrm server

        Parameters
        ----------

        country: str
                Which country to download data from. Expected in lower case & dashes replace spaces.
        continent: str
                Which continent of the given country. Expected in lower case & dashes replace spaces.

        Examples
        --------

        >>> urbanpy.routing.start_osrm_server('peru', 'south-america')
        Starting server ...
        Server was started succesfully.

        """

        # Download, process and run server command sequence
        dwn_str_unix = f"""
        docker pull osrm/osrm-backend;
        mkdir -p ~/data/osrm/;
        cd ~/data/osrm/;
        wget https://download.geofabrik.de/{continent}/{country}-latest.osm.pbf;
        docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/{country}-latest.osm.pbf;
        docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/{country}-latest.osm.pbf;
        docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/{country}-latest.osm.pbf;
        docker container rm osrm_extract osrm_partition osrm_customize;
        docker run -t --name {CONTAINER_NAME}_{continent}_{country} -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/{country}-latest.osm.pbf;
        """

        container_running = self.check_container_is_running(
            CONTAINER_NAME + f"_{continent}_{country}"
        )

        # Check platform
        if sys.platform in ["darwin", "linux"]:
            container_check = [
                "docker",
                "inspect",
                CONTAINER_NAME + f"_{continent}_{country}",
            ]
            container_start = [
                "docker",
                "start",
                CONTAINER_NAME + f"_{continent}_{country}",
            ]
            download_command = dwn_str_unix
        else:
            container_check = [
                "powershell.exe",
                "docker",
                "inspect",
                CONTAINER_NAME + f"_{continent}_{country}",
            ]
            container_start = [
                "powershell.exe",
                "docker",
                "start",
                CONTAINER_NAME + f"_{continent}_{country}",
            ]
            download_command = [
                "powershell.exe",
                "./download_script_windows.ps1",
                CONTAINER_NAME,
                country,
                continent,
            ]

        # Check if container exists:
        if subprocess.run(container_check).returncode == 0:
            if container_running:
                print("Server is already running.")
            else:
                try:
                    print("Starting server ...")
                    subprocess.run(container_start, check=True)
                    time.sleep(5)  # Wait server to be prepared to receive requests
                    print("Server was started succesfully")
                except subprocess.CalledProcessError as error:
                    print(
                        f"Something went wrong. Please check if port 5000 is being used or check your docker installation.\nError: {error}"
                    )

        else:
            try:
                print(
                    "This is the first time you used this function.\nInitializing server setup. This may take several minutes..."
                )
                subprocess.Popen(download_command, shell=True)

                # Verify container is running
                while container_running == False:
                    container_running = self.check_container_is_running(
                        CONTAINER_NAME + f"_{continent}_{country}"
                    )

                print("Server was started succesfully")
                time.sleep(5)  # Wait server to be prepared to receive requests

            except subprocess.CalledProcessError as error:
                print(
                    f"Something went wrong. Please check your docker installation.\nError: {error}"
                )

        time.sleep(5)

    def stop_osrm_server(self, country, continent):
        """
        Run docker stop on the server's container.

        Parameters
        ----------

        country: str
                Which country osrm to stop. Expected in lower case & dashes replace spaces.
        continent: str
                Continent of the given country. Expected in lower case & dashes replace spaces.

        Examples
        --------

        >>> urbanpy.routing.stop_osrm_server('peru', 'south-america')
        Server stopped succesfully

        """

        if sys.platform in ["darwin", "linux"]:
            docker_top = ["docker", "top", CONTAINER_NAME + f"_{continent}_{country}"]
            docker_stop = ["docker", "stop", CONTAINER_NAME + f"_{continent}_{country}"]
        else:
            docker_top = [
                "powershell.exe",
                "docker",
                "top",
                CONTAINER_NAME + f"_{continent}_{country}",
            ]
            docker_stop = [
                "powershell.exe",
                "docker",
                "stop",
                CONTAINER_NAME + f"_{continent}_{country}",
            ]

        # Check if container exists:
        if subprocess.run(docker_top).returncode == 0:
            if (
                self.check_container_is_running(
                    CONTAINER_NAME + f"_{continent}_{country}"
                )
                == True
            ):
                try:
                    subprocess.run(docker_stop, check=True)
                    # subprocess.run(['docker', 'container', 'rm', 'osrm_routing_server'])
                    print("Server was stoped succesfully")
                except subprocess.CalledProcessError as error:
                    print(
                        f"Something went wrong. Please check your docker installation.\nError: {error}"
                    )
            else:
                print("Server is not running.")

        else:
            print("Server does not exist.")

    def get_distance(self, origin, destination, profile):
        """
        Query an OSRM routing server for routes between an origin and a destination
        using a specified profile.

        Parameters
        ----------

        origin: DataFrame with columns x and y or Point geometry
                Input origin in lat lon pairs (y, x) to pass into the routing engine

        destination: DataFrame with columns x and y or Point geometry
                    Input destination in lat lon pairs (y,x) to pass to the routing engine

        profile: str. One of {'foot', 'car', 'bicycle'}
                Behavior to use when routing and estimating travel time.

        Returns
        -------

        distance: float
                Total travel distance from origin to destination in meters
        duration: float
                Total travel time in minutes

        """
        orig = f"{origin.x},{origin.y}"
        dest = f"{destination.x},{destination.y}"
        url = self.url.format(profile=profile, orig=orig, dest=dest)
        # url = f'http://localhost:5000/route/v1/{profile}/{orig};{dest}' # Local osrm server
        response = requests.get(url, params={"overview": "false"})

        try:
            data = response.json()["routes"][0]
            distance, duration = data["distance"], data["duration"]
            return distance, duration
        except Exception as err:
            # print(err)
            return None, None

    def check_container_is_running(self, container_name):
        """
        Checks if a container is running

        Parameters
        ----------

        container_name: str
            Name of container to check

        Returns
        -------

        container_running: bool
            True if container is running, False otherwise.

        """
        completed_process = subprocess.run(
            ["docker", "ps"], check=True, capture_output=True
        )
        stdout_str = completed_process.stdout.decode("utf-8")
        container_running = container_name in stdout_str

        return container_running


if __name__ == "__main__":
    print("Hello")

    from shapely.geometry import Point

    with RoutingServer("peru", "south-america") as server:
        orig = Point(-77, -12)
        destin = Point(-77.95, -12.43)
        print(server.get_distance(orig, destin, "foot"))
