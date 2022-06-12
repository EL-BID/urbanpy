# Download, process and run server command sequence
mkdir -p ~/data/osrm/$3/$2;
cd ~/data/osrm/$3/$2;
mkdir -p logs;
docker pull osrm/osrm-backend > $(pwd)/logs/$4.txt;
# container 1 country 2 continent 3 profile 4
echo "Downloading osm data from geofabrik ... (1/5)"
wget https://download.geofabrik.de/$3/$2-latest.osm.pbf -a $(pwd)/logs/$4.txt;
echo "Done (1/5)"
echo "Running osrm extract process ... (2/5)"
docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/$4.lua /data/$2-latest.osm.pbf >> $(pwd)/logs/$4.txt ;
echo "Done (2/5)"
echo "Running osrm partition process ... (3/5)"
docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/$2-latest.osm.pbf >> $(pwd)/logs/$4.txt;
echo "Done (3/5)"
echo "Running osrm customize process ... (4/5)"
docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/$2-latest.osm.pbf >> $(pwd)/logs/$4.txt;
echo "Done (4/5)"
echo "Removing osrm processing containers ... (5/5)"
docker container rm osrm_extract osrm_partition osrm_customize >> $(pwd)/logs/$4.txt;
echo "Done (5/5)"
echo "Starting osrm server ..."
CONTAINER_ID=$(docker run -d -t --name $1_$3_$2_$4 -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/$2-latest.osm.pbf);
echo "Docker Container ID: ${CONTAINER_ID}"