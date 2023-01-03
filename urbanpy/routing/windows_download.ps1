$container_name = $args[0]
$country = $args[1]
$continent = $args[2]

docker pull osrm/osrm-backend;

if (!(Test-Path -Path \data\osrm\)){
    mkdir  \data\osrm\;
}

Set-Location \data\osrm\;
Invoke-WebRequest -URI https://download.geofabrik.de/$continent/$country-latest.osm.pbf -OutFile $country-latest.osm.pbf;
docker run -t --name osrm_extract -v ${PWD}:/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/$country-latest.osm.pbf;
docker run -t --name osrm_partition -v ${PWD}:/data osrm/osrm-backend osrm-partition /data/$country-latest.osm.pbf;
docker run -t --name osrm_customize -v ${PWD}:/data osrm/osrm-backend osrm-customize /data/$country-latest.osm.pbf;
docker container rm osrm_extract osrm_partition osrm_customize;
docker run -t --name "$($CONTAINER_NAME)_$($continent)_$($country)" -p 5000:5000 -v ${PWD}:/data osrm/osrm-backend osrm-routed --algorithm mld /data/$country-latest.osm.pbf;

# Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser
