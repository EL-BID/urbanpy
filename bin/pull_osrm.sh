if [ $2 == true ]
  docker pull osrm/osrm-backend
  mkdir -p ~/data/osrm/
  cd ~/data/osrm/
  wget https://download.geofabrik.de/south-america/$1
  docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/$1
  docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/$1
  docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/$1
  docker prune osrm
  docker run -t --name osrm_routing_server -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/$1
fi

cd ~/data/osrm
docker run -r --name osrm_routing_server -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/$1
