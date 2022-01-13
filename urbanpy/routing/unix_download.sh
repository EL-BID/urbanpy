# Download, process and run server command sequence
docker pull osrm/osrm-backend;
mkdir -p ~/data/osrm/;
cd ~/data/osrm/;
# container 1 country 2 continent 3 profile 4
wget https://download.geofabrik.de/$3/$2-latest.osm.pbf;
docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/$4.lua /data/$2-latest.osm.pbf;
docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/$2-latest.osm.pbf;
docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/$2-latest.osm.pbf;
docker container rm osrm_extract osrm_partition osrm_customize;
docker run -t --name $1_$3_$2_$4 -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/$2-latest.osm.pbf;
