"""Cross-platform Python-owned lifecycle for a local OSRM service."""

import hashlib
import json
import os
import shutil
import socket
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import requests
from filelock import FileLock, Timeout

from urbanpy.errors import UrbanPyError
from urbanpy.geofabrik import GeofabrikCatalog
from urbanpy.models import (
    OSRMConfig,
    OSRMManifest,
    OSRMPlan,
    OSRMState,
    OSRMStatus,
    TravelProfile,
)
from urbanpy.routing._docker import CommandRunner, SubprocessRunner, inspect_container
from urbanpy.routing._download import DownloadResult, download_pbf, sha256_file
from urbanpy.routing.osrm_client import OSRMClient

OWNER_LABEL: Final = "io.github.el-bid.urbanpy.owner"
DATASET_LABEL: Final = "io.github.el-bid.urbanpy.dataset"
REGION_LABEL: Final = "io.github.el-bid.urbanpy.region"
PROFILE_LABEL: Final = "io.github.el-bid.urbanpy.profile"
OWNER_VALUE: Final = "osrm"
CONTAINER_PLATFORM: Final = "linux/amd64"

PROFILE_SETTINGS: Final = {
    TravelProfile.DRIVING: ("car.lua", "driving"),
    TravelProfile.CYCLING: ("bicycle.lua", "cycling"),
    TravelProfile.WALKING: ("foot.lua", "walking"),
}


class OSRMLifecycleError(UrbanPyError):
    """A local OSRM lifecycle operation could not complete safely."""


class OSRMOwnershipError(OSRMLifecycleError):
    """A colliding Docker resource is not owned by this UrbanPy dataset."""


class OSRMReadinessError(OSRMLifecycleError):
    """The OSRM service did not become ready before its deadline."""


class OSRMManager:
    """Prepare and operate exactly one region/profile OSRM service."""

    def __init__(
        self,
        config: OSRMConfig,
        *,
        catalog: GeofabrikCatalog | None = None,
        runner: CommandRunner | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.catalog = catalog
        self.runner = runner or SubprocessRunner()
        self.session = session
        self._started_here = False

    def __enter__(self) -> OSRMStatus:
        return self.start()

    def __exit__(self, *_exception: object) -> None:
        if self._started_here:
            self.stop()

    def plan(self) -> OSRMPlan:
        catalog = self.catalog or GeofabrikCatalog.fetch(session=self.session)
        region = catalog.resolve(self.config.region_id)
        identity = safe_resource_id(region.id, self.config.profile)
        pbf_path = (
            self.config.data_dir
            / "downloads"
            / safe_resource_id(region.id)
            / "data.osm.pbf"
        )
        prepared_dir = self.config.data_dir / "prepared" / identity
        container_name = f"urbanpy-osrm-{identity}"[:120]
        prepare_commands = _prepare_commands(self.config, prepared_dir, identity)
        start_command = _start_command(
            self.config, prepared_dir, container_name, identity, region.id
        )
        return OSRMPlan(
            region_id=region.id,
            profile=self.config.profile,
            pbf_url=region.pbf_url,
            pbf_path=pbf_path,
            prepared_dir=prepared_dir,
            container_name=container_name,
            endpoint=self.config.endpoint,
            prepare_commands=prepare_commands,
            start_command=start_command,
            reusable=_manifest_matches(
                prepared_dir / "urbanpy-osrm-manifest.json", self.config, region.id
            ),
        )

    def prepare(self) -> OSRMPlan:
        plan = self.plan()
        lock_path = (
            self.config.data_dir
            / "locks"
            / f"{safe_resource_id(plan.region_id, plan.profile)}.lock"
        )
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(lock_path, timeout=self.config.lock_timeout_s):
                return self._prepare_locked(plan)
        except Timeout as error:
            raise OSRMLifecycleError(
                f"Another process is preparing {plan.region_id}/{plan.profile.value}."
            ) from error

    def _prepare_locked(self, plan: OSRMPlan) -> OSRMPlan:
        if plan.reusable and (plan.prepared_dir / "data.osrm").exists():
            return plan

        download = _existing_download(plan.pbf_path)
        if download is None:
            download = download_pbf(
                str(plan.pbf_url),
                plan.pbf_path,
                session=self.session,
                timeout=(5.0, self.config.download_timeout_s),
            )

        plan.prepared_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{plan.prepared_dir.name}-", dir=plan.prepared_dir.parent
            )
        )
        try:
            shutil.copy2(download.path, stage / "data.osm.pbf")
            self._ensure_image()
            for command in _prepare_commands(
                self.config, stage, safe_resource_id(plan.region_id, plan.profile)
            ):
                self.runner.run(
                    command, timeout=self.config.command_timeout_s, check=True
                )
            if not (stage / "data.osrm").exists():
                raise OSRMLifecycleError(
                    "osrm-extract completed without producing data.osrm."
                )
            manifest = OSRMManifest(
                region_id=plan.region_id,
                profile=plan.profile,
                algorithm=self.config.algorithm,
                pbf_url=plan.pbf_url,
                pbf_sha256=download.sha256,
                pbf_size=download.size,
                image=self.config.image,
                created_at=datetime.now(UTC),
            )
            _atomic_write(
                stage / "urbanpy-osrm-manifest.json",
                manifest.model_dump_json(indent=2),
            )
            _publish_directory(stage, plan.prepared_dir)
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        return plan.model_copy(update={"reusable": True})

    def start(self) -> OSRMStatus:
        plan = self.prepare()
        existing = inspect_container(
            self.runner, plan.container_name, timeout=self.config.command_timeout_s
        )
        created = False
        if existing is not None:
            _require_ownership(existing, plan)
            if _is_running(existing):
                return self._wait_until_ready(plan, created=False)
            _require_port_available(self.config)
            self.runner.run(
                ["docker", "start", plan.container_name],
                timeout=self.config.command_timeout_s,
            )
        else:
            _require_port_available(self.config)
            self.runner.run(plan.start_command, timeout=self.config.command_timeout_s)
            created = True
            self._started_here = True
        return self._wait_until_ready(plan, created=created)

    def _wait_until_ready(self, plan: OSRMPlan, *, created: bool) -> OSRMStatus:
        client = OSRMClient(
            plan.endpoint,
            session=self.session,
            timeout=(1.0, min(5.0, self.config.readiness_timeout_s)),
        )
        deadline = time.monotonic() + self.config.readiness_timeout_s
        while time.monotonic() < deadline:
            if client.ready(profile=plan.profile):
                return _status(plan, OSRMState.RUNNING)
            time.sleep(0.25)
        if created:
            self.runner.run(
                ["docker", "stop", plan.container_name],
                timeout=self.config.command_timeout_s,
                check=False,
            )
        raise OSRMReadinessError(
            f"OSRM did not become ready at {plan.endpoint} within "
            f"{self.config.readiness_timeout_s:g} seconds."
        )

    def status(self) -> OSRMStatus:
        plan = self.plan()
        container = inspect_container(
            self.runner, plan.container_name, timeout=self.config.command_timeout_s
        )
        if container is None:
            state = OSRMState.PREPARED if plan.reusable else OSRMState.MISSING
            return _status(plan, state)
        _require_ownership(container, plan)
        return _status(
            plan, OSRMState.RUNNING if _is_running(container) else OSRMState.STOPPED
        )

    def stop(self) -> OSRMStatus:
        plan = self.plan()
        container = inspect_container(
            self.runner, plan.container_name, timeout=self.config.command_timeout_s
        )
        if container is None:
            return _status(
                plan, OSRMState.PREPARED if plan.reusable else OSRMState.MISSING
            )
        _require_ownership(container, plan)
        if _is_running(container):
            self.runner.run(
                ["docker", "stop", plan.container_name],
                timeout=self.config.command_timeout_s,
            )
        self._started_here = False
        return _status(plan, OSRMState.STOPPED)

    def logs(self, *, tail: int = 200) -> str:
        if tail < 1:
            raise ValueError("tail must be positive")
        plan = self.plan()
        container = inspect_container(
            self.runner, plan.container_name, timeout=self.config.command_timeout_s
        )
        if container is None:
            raise OSRMLifecycleError("OSRM container does not exist.")
        _require_ownership(container, plan)
        result = self.runner.run(
            ["docker", "logs", "--tail", str(tail), plan.container_name],
            timeout=self.config.command_timeout_s,
        )
        return result.stdout

    def clean(
        self,
        *,
        container: bool = False,
        prepared: bool = False,
        pbf: bool = False,
        dry_run: bool = True,
    ) -> tuple[Path | str, ...]:
        if not any((container, prepared, pbf)):
            raise ValueError("Select at least one clean scope.")
        plan = self.plan()
        targets: list[Path | str] = []
        if container:
            existing = inspect_container(
                self.runner, plan.container_name, timeout=self.config.command_timeout_s
            )
            if existing is not None:
                _require_ownership(existing, plan)
                targets.append(plan.container_name)
                if not dry_run:
                    self.runner.run(
                        ["docker", "rm", "--force", plan.container_name],
                        timeout=self.config.command_timeout_s,
                    )
        for enabled, path in ((prepared, plan.prepared_dir), (pbf, plan.pbf_path)):
            if enabled and path.exists():
                targets.append(path)
                if not dry_run:
                    shutil.rmtree(path) if path.is_dir() else path.unlink()
        return tuple(targets)

    def _ensure_image(self) -> None:
        self.runner.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            timeout=self.config.command_timeout_s,
        )
        present = self.runner.run(
            ["docker", "image", "inspect", self.config.image],
            timeout=self.config.command_timeout_s,
            check=False,
        )
        if present.returncode != 0:
            self.runner.run(
                ["docker", "pull", "--platform", CONTAINER_PLATFORM, self.config.image],
                timeout=self.config.command_timeout_s,
            )


def safe_resource_id(region_id: str, profile: TravelProfile | None = None) -> str:
    readable = "".join(
        character if character.isalnum() else "-" for character in region_id.casefold()
    ).strip("-")
    readable = "-".join(filter(None, readable.split("-")))[:48] or "region"
    raw = f"{region_id}\0{profile.value if profile else ''}"
    digest = hashlib.blake2s(raw.encode(), digest_size=5).hexdigest()
    suffix = f"-{profile.value}" if profile else ""
    return f"{readable}{suffix}-{digest}"


def _prepare_commands(
    config: OSRMConfig, directory: Path, identity: str
) -> tuple[tuple[str, ...], ...]:
    profile_file, _api_profile = PROFILE_SETTINGS[config.profile]
    mount = f"type=bind,source={directory.resolve()},target=/data"
    labels = _label_arguments(identity, config.region_id, config.profile)
    base = (
        "docker",
        "run",
        "--rm",
        "--platform",
        CONTAINER_PLATFORM,
        *labels,
        "--mount",
        mount,
        config.image,
    )
    return (
        (*base, "osrm-extract", "-p", f"/opt/{profile_file}", "/data/data.osm.pbf"),
        (*base, "osrm-partition", "/data/data.osrm"),
        (*base, "osrm-customize", "/data/data.osrm"),
    )


def _start_command(
    config: OSRMConfig,
    directory: Path,
    container_name: str,
    identity: str,
    region_id: str,
) -> tuple[str, ...]:
    mount = f"type=bind,source={directory.resolve()},target=/data,readonly"
    return (
        "docker",
        "run",
        "--detach",
        "--name",
        container_name,
        "--platform",
        CONTAINER_PLATFORM,
        *_label_arguments(identity, region_id, config.profile),
        "--publish",
        f"{config.bind_host}:{config.port}:5000",
        "--mount",
        mount,
        config.image,
        "osrm-routed",
        "--algorithm",
        config.algorithm,
        "/data/data.osrm",
    )


def _label_arguments(
    identity: str, region_id: str, profile: TravelProfile
) -> tuple[str, ...]:
    labels = {
        OWNER_LABEL: OWNER_VALUE,
        DATASET_LABEL: identity,
        REGION_LABEL: region_id,
        PROFILE_LABEL: profile.value,
    }
    return tuple(
        part for key, value in labels.items() for part in ("--label", f"{key}={value}")
    )


def _manifest_matches(path: Path, config: OSRMConfig, region_id: str) -> bool:
    try:
        manifest = OSRMManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        manifest.region_id == region_id
        and manifest.profile == config.profile
        and manifest.algorithm == config.algorithm
        and manifest.image == config.image
    )


def _existing_download(path: Path) -> DownloadResult | None:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    digest = sha256_file(path)
    return DownloadResult(path, path.stat().st_size, digest, None, None)


def _publish_directory(stage: Path, destination: Path) -> None:
    backup = destination.with_name(f".{destination.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        os.replace(destination, backup)
    try:
        os.replace(stage, destination)
    except BaseException:
        if backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    shutil.rmtree(backup, ignore_errors=True)


def _atomic_write(path: Path, value: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def _require_port_available(config: OSRMConfig) -> None:
    family = socket.AF_INET6 if config.bind_host.version == 6 else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((str(config.bind_host), config.port))
        except OSError as error:
            raise OSRMLifecycleError(
                f"Port {config.port} is unavailable on {config.bind_host}."
            ) from error


def _require_ownership(container: dict[str, object], plan: OSRMPlan) -> None:
    config = container.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    expected = safe_resource_id(plan.region_id, plan.profile)
    owned = (
        isinstance(labels, dict)
        and labels.get(OWNER_LABEL) == OWNER_VALUE
        and labels.get(DATASET_LABEL) == expected
    )
    if not owned:
        raise OSRMOwnershipError(
            f"Container {plan.container_name} is not owned by this UrbanPy dataset."
        )


def _is_running(container: dict[str, object]) -> bool:
    state = container.get("State")
    return bool(state.get("Running")) if isinstance(state, dict) else False


def _status(plan: OSRMPlan, state: OSRMState) -> OSRMStatus:
    return OSRMStatus(
        state=state,
        region_id=plan.region_id,
        profile=plan.profile,
        endpoint=plan.endpoint,
        container_name=plan.container_name,
        prepared_dir=plan.prepared_dir,
    )


__all__ = [
    "OSRMLifecycleError",
    "OSRMManager",
    "OSRMOwnershipError",
    "OSRMReadinessError",
    "safe_resource_id",
]
