import pytest

from urbanpy.models import Coordinate, OSRMConfig, TravelProfile
from urbanpy.routing import OSRMClient, OSRMManager


@pytest.mark.docker
def test_small_canonical_osrm_service_end_to_end(tmp_path):
    config = OSRMConfig(
        region_id="liechtenstein",
        profile=TravelProfile.DRIVING,
        data_dir=tmp_path,
        readiness_timeout_s=180,
    )
    manager = OSRMManager(config)
    try:
        with manager as status:
            route = OSRMClient(status.endpoint).route(
                Coordinate(longitude=9.5215, latitude=47.1410),
                Coordinate(longitude=9.5108, latitude=47.1320),
            )
            assert route.distance_m > 0
            assert route.duration_s > 0
    finally:
        manager.clean(container=True, prepared=True, pbf=True, dry_run=False)
