docker pull osrm/osrm-backend;
mkdir -p ~/data/osrm/;
cd ~/data/osrm/;
wget https://download.geofabrik.de/south-america/peru-latest.osm.pbf;
docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/peru-latest.osm.pbf;
docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/peru-latest.osm.pbf;
docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/peru-latest.osm.pbf;
docker container rm osrm_extract osrm_partition osrm_customize;
docker run -t --name osrm_routing_server -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/peru-latest.osm.pbf;
