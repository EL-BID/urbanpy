import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from urbanpy.geofabrik import GeofabrikCatalog
from urbanpy.models import Coordinate, OSRMConfig, OSRMState, TravelProfile
from urbanpy.routing._docker import (
    DockerCommandError,
    DockerUnavailableError,
    SubprocessRunner,
)
from urbanpy.routing._download import DownloadError, download_pbf
from urbanpy.routing.osrm import (
    DATASET_LABEL,
    OWNER_LABEL,
    OWNER_VALUE,
    OSRMManager,
    OSRMOwnershipError,
    safe_resource_id,
)
from urbanpy.routing.osrm_client import OSRMClient, OSRMClientError
from urbanpy.routing import routing as legacy_routing


def _catalog():
    return GeofabrikCatalog.from_payload(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "properties": {
                        "id": "us/california",
                        "name": "us/california",
                        "parent": "north-america",
                        "iso3166-2": ["US-CA"],
                        "urls": {
                            "pbf": "https://download.geofabrik.de/north-america/us/california-latest.osm.pbf"
                        },
                    }
                }
            ],
        }
    )


def _config(tmp_path, **updates):
    values = {
        "region_id": "us/california",
        "profile": TravelProfile.WALKING,
        "data_dir": tmp_path,
        "port": 5017,
        "readiness_timeout_s": 1,
    }
    values.update(updates)
    return OSRMConfig(**values)


def test_config_defaults_to_loopback_and_requires_external_opt_in(tmp_path):
    config = _config(tmp_path)

    assert config.endpoint == "http://127.0.0.1:5017"
    assert "@sha256:" in config.image
    with pytest.raises(ValidationError, match="allow_external"):
        _config(tmp_path, bind_host="0.0.0.0")
    assert _config(tmp_path, bind_host="0.0.0.0", allow_external=True).allow_external


def test_plan_uses_safe_identity_catalog_url_and_correct_mld_extensions(tmp_path):
    plan = OSRMManager(_config(tmp_path), catalog=_catalog()).plan()

    assert "/" not in plan.container_name
    assert str(plan.pbf_url).endswith("/us/california-latest.osm.pbf")
    assert plan.prepare_commands[0][-4:] == (
        "osrm-extract",
        "-p",
        "/opt/foot.lua",
        "/data/data.osm.pbf",
    )
    assert plan.prepare_commands[1][-2:] == ("osrm-partition", "/data/data.osrm")
    assert plan.prepare_commands[2][-2:] == ("osrm-customize", "/data/data.osrm")
    assert plan.start_command[-4:] == (
        "osrm-routed",
        "--algorithm",
        "mld",
        "/data/data.osrm",
    )
    assert all(
        isinstance(part, str) for command in plan.prepare_commands for part in command
    )
    assert "127.0.0.1:5017:5000" in plan.start_command
    assert "readonly" in next(
        part for part in plan.start_command if "target=/data" in part
    )


def test_safe_resource_id_is_stable_and_collision_resistant():
    first = safe_resource_id("us/california", TravelProfile.WALKING)

    assert first == safe_resource_id("us/california", TravelProfile.WALKING)
    assert first != safe_resource_id("us-california", TravelProfile.WALKING)
    assert first != safe_resource_id("us/california", TravelProfile.DRIVING)
    assert "/" not in first


class _DownloadResponse:
    def __init__(self, content, *, status_code=200, headers=None, payload=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        del chunk_size
        yield self.content

    def json(self):
        return self._payload


def test_atomic_downloader_publishes_digest_and_resumes_partial_file(tmp_path):
    target = tmp_path / "data.osm.pbf"
    session = Mock()
    session.get.return_value = _DownloadResponse(b"abc", headers={"ETag": '"v1"'})

    result = download_pbf(
        "https://download.geofabrik.de/test-latest.osm.pbf",
        target,
        session=session,
    )

    assert target.read_bytes() == b"abc"
    assert (
        result.sha256
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert not target.with_name("data.osm.pbf.part").exists()

    target.unlink()
    target.with_name("data.osm.pbf.part").write_bytes(b"ab")
    target.with_name("data.osm.pbf.part.json").write_text(
        json.dumps(
            {
                "url": "https://download.geofabrik.de/test-latest.osm.pbf",
                "etag": '"v1"',
            }
        )
    )
    session.get.return_value = _DownloadResponse(b"c", status_code=206)
    resumed = download_pbf(
        "https://download.geofabrik.de/test-latest.osm.pbf",
        target,
        session=session,
    )
    assert target.read_bytes() == b"abc"
    assert resumed.size == 3
    assert session.get.call_args.kwargs["headers"]["Range"] == "bytes=2-"


def test_downloader_rejects_unofficial_sources_and_size_overflow(tmp_path):
    with pytest.raises(DownloadError, match="official"):
        download_pbf("https://example.org/data.osm.pbf", tmp_path / "data")
    session = Mock()
    session.get.return_value = _DownloadResponse(b"too-large")
    with pytest.raises(DownloadError, match="size limit"):
        download_pbf(
            "https://download.geofabrik.de/test-latest.osm.pbf",
            tmp_path / "data",
            session=session,
            max_bytes=2,
        )


class _Runner:
    def __init__(self):
        self.calls = []
        self.running = False
        self.labels = None

    def run(self, command, *, timeout, check=True):
        del timeout
        command = tuple(command)
        self.calls.append(command)
        if command[:3] == ("docker", "image", "inspect"):
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:3] == ("docker", "inspect", "--format"):
            if self.labels is None:
                return subprocess.CompletedProcess(command, 1, "", "missing")
            payload = {
                "Config": {"Labels": self.labels},
                "State": {"Running": self.running},
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "osrm-extract" in command:
            mount = command[command.index("--mount") + 1]
            source = mount.split(",source=", 1)[1].split(",target=", 1)[0]
            Path(source, "data.osrm").touch()
        if command[:3] == ("docker", "run", "--detach"):
            self.running = True
            self.labels = {
                command[index + 1].split("=", 1)[0]: command[index + 1].split("=", 1)[1]
                for index, value in enumerate(command)
                if value == "--label"
            }
        if command[:2] == ("docker", "stop"):
            self.running = False
        if check and False:  # pragma: no cover - protocol shape only
            raise AssertionError
        return subprocess.CompletedProcess(command, 0, "container-id", "")


class _Session:
    def get(self, url, **kwargs):
        del kwargs
        if url.endswith(".osm.pbf"):
            return _DownloadResponse(b"pbf-data")
        return _DownloadResponse(b'{"code":"NoSegment"}', payload={"code": "NoSegment"})


def test_manager_prepares_stages_publishes_starts_and_stops_owned_service(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "urbanpy.routing.osrm._require_port_available", lambda _config: None
    )
    runner = _Runner()
    manager = OSRMManager(
        _config(tmp_path), catalog=_catalog(), runner=runner, session=_Session()
    )

    prepared = manager.prepare()
    assert prepared.reusable
    assert (prepared.prepared_dir / "data.osrm").exists()
    assert (prepared.prepared_dir / "urbanpy-osrm-manifest.json").exists()
    extract, partition, customize = [
        command
        for command in runner.calls
        if any(
            tool in command
            for tool in ("osrm-extract", "osrm-partition", "osrm-customize")
        )
    ]
    assert extract[-1] == "/data/data.osm.pbf"
    assert partition[-1] == customize[-1] == "/data/data.osrm"

    status = manager.start()
    assert status.state is OSRMState.RUNNING
    assert runner.labels[OWNER_LABEL] == OWNER_VALUE
    assert runner.labels[DATASET_LABEL] == safe_resource_id(
        "us/california", TravelProfile.WALKING
    )
    assert manager.stop().state is OSRMState.STOPPED


def test_manager_refuses_colliding_unowned_container(tmp_path):
    runner = _Runner()
    runner.labels = {OWNER_LABEL: "someone-else", DATASET_LABEL: "other"}
    manager = OSRMManager(
        _config(tmp_path), catalog=_catalog(), runner=runner, session=_Session()
    )
    manager.prepare()

    with pytest.raises(OSRMOwnershipError):
        manager.start()


def test_legacy_start_adapter_resolves_catalog_and_warns(monkeypatch):
    manager = Mock()
    manager_type = Mock(return_value=manager)
    monkeypatch.setattr(
        legacy_routing.GeofabrikCatalog, "fetch", Mock(return_value=_catalog())
    )
    monkeypatch.setattr(legacy_routing, "OSRMManager", manager_type)

    with pytest.warns(FutureWarning, match="deprecated"):
        legacy_routing.start_osrm_server("US-CA", "north-america", "foot")

    config = manager_type.call_args.args[0]
    assert config.region_id == "us/california"
    assert config.profile is TravelProfile.WALKING
    manager.start.assert_called_once_with()


def test_legacy_adapter_rejects_wrong_catalog_parent(monkeypatch):
    monkeypatch.setattr(
        legacy_routing.GeofabrikCatalog, "fetch", Mock(return_value=_catalog())
    )

    with pytest.warns(FutureWarning), pytest.raises(ValueError, match="does not match"):
        legacy_routing.stop_osrm_server("US-CA", "south-america", "car")


def test_docker_runner_translates_missing_cli_and_nonzero(monkeypatch):
    runner = SubprocessRunner()
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=FileNotFoundError))
    with pytest.raises(DockerUnavailableError):
        runner.run(["docker", "version"], timeout=1)

    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess(["docker"], 2, "", "denied")),
    )
    with pytest.raises(DockerCommandError) as captured:
        runner.run(["docker", "version"], timeout=1)
    assert captured.value.returncode == 2
    assert captured.value.stderr == "denied"


def test_http_client_preserves_units_coordinates_and_matrix_nulls():
    session = Mock()
    route_response = _DownloadResponse(
        b"route",
        payload={
            "code": "Ok",
            "routes": [{"distance": 123.4, "duration": 56.7, "extra": True}],
        },
    )
    table_response = _DownloadResponse(
        b"table",
        payload={
            "code": "Ok",
            "distances": [[0.0, None]],
            "durations": [[0.0, None]],
        },
    )
    session.get.side_effect = [route_response, table_response]
    client = OSRMClient("http://127.0.0.1:5000", session=session)
    origin = Coordinate(longitude=-77.0, latitude=-12.0)
    destination = Coordinate(longitude=-77.1, latitude=-12.1)

    route = client.route(origin, destination, profile=TravelProfile.WALKING)
    table = client.table([origin], [origin, destination])

    assert route.distance_m == 123.4
    assert route.duration_s == 56.7
    assert table.distances_m == ((0.0, None),)
    assert (
        "/route/v1/walking/-77.00000000,-12.00000000;"
        in session.get.call_args_list[0].args[0]
    )
    assert session.get.call_args_list[1].kwargs["params"]["sources"] == "0"


def test_http_client_translates_invalid_or_oversized_responses():
    session = Mock()
    session.get.return_value = _DownloadResponse(b"x" * 4, payload={"code": "Ok"})
    client = OSRMClient("http://localhost:5000", session=session, max_response_bytes=2)

    with pytest.raises(OSRMClientError, match="size limit"):
        client.route(
            Coordinate(longitude=0, latitude=0), Coordinate(longitude=1, latitude=1)
        )
